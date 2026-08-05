"""
金旭 PMS 分析 — 匯入流程服務

規格書：docs/SPEC_jinxu_analytics.md §8、§9、§10

⚠️ 本模組全部是同步函式（def），由 router 透過 run_in_threadpool 呼叫。
   絕不可在 async def 內直接呼叫 db.query()（見 CLAUDE.md 與
   project_async_def_blocking_fix 事故）。

覆蓋規則（§8.2，業主 J3 決定）：
    業務鍵不存在        → INSERT
    存在且 row_hash 相同 → SKIP（內容沒變，不寫 DB）
    存在且 row_hash 不同 → UPDATE 全欄 + 記錄 WARNING
  RESV_DETAIL 的 INSERT/UPDATE 都要**整組重建**子表 jinxu_reservation_stay，
  不做逐段 UPDATE（段數會因延住／改房型而變動，逐段比對易留孤兒列）。
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
from datetime import datetime

import openpyxl
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.jinxu_import import (
    PROGRAM_VERSION,
    QUALITY_FAIL,
    QUALITY_PASS,
    QUALITY_PASS_WITH_WARNINGS,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    SOURCE_FCR02_LEDGER,
    SOURCE_LABELS,
    SOURCE_RESV_DETAIL,
    SOURCE_TYPES,
    STATUS_COMMITTED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_ROLLED_BACK,
    STATUS_VALIDATED,
    JinxuImportBatch,
    JinxuImportError,
)
from app.models.jinxu_ledger import (
    GROUP_UNCLASSIFIED,
    JinxuFcr02Raw,
    JinxuLedgerEntry,
    JinxuSubjectMap,
)
from app.models.jinxu_reservation import (
    JinxuReservation,
    JinxuReservationStay,
    JinxuResvRaw,
)
from app.services import jinxu_parser as P
from app.services.jinxu_seed import ensure_jinxu_seed

logger = logging.getLogger(__name__)

BULK_CHUNK = 1000

# 整批 FAIL 的錯誤碼（規格書 §10）—— 這些代表資料本身對不上，不可放行
FATAL_ERROR_CODES = {
    P.ERR_SUBTOTAL_MISMATCH,
    P.ERR_GRANDTOTAL_MISMATCH,
    P.ERR_ROOM_NIGHTS_MISMATCH,
    P.ERR_UNKNOWN_ROW_TYPE,
}


# ══════════════════════════════════════════════════════════════════════════════
#  檔案讀取與來源判定
# ══════════════════════════════════════════════════════════════════════════════

def sha256_of(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def read_sheet(content: bytes) -> tuple[str, list[tuple]]:
    """讀取 xlsx 的第一個工作表，回傳 (工作表名稱, 逐列 tuple)。

    ⚠️ 用 openpyxl read-only 模式，不可用 pandas——欄型別推斷會把
       「建檔時間」「訂房號碼」這類字串鍵變成數字（規格書 §6.2）。
    """
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = [tuple(r) for r in ws.iter_rows(values_only=True)]
    name = ws.title
    wb.close()
    return name, rows


def detect_source_type(rows: list[tuple]) -> str | None:
    """由前幾列的標題判定來源類型。無法判定回 None（由使用者手動指定）。"""
    for row in rows[:8]:
        first = P.norm_text(row[0] if row else None)
        if first == P.FCR02_TITLE:
            return SOURCE_FCR02_LEDGER
        if first == P.RESV_TITLE:
            return SOURCE_RESV_DETAIL
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  對帳
# ══════════════════════════════════════════════════════════════════════════════

def reconcile_fcr02(result: P.Fcr02ParseResult) -> dict:
    """FCR02 對帳：分組小計 + 全檔總計（規格書 §4.4）。"""
    bad = [s for s in result.subtotals if not s["matched"]]
    grand_ok = (
        result.grand_total is not None
        and abs(result.computed_total - result.grand_total) < 0.01
    )
    return {
        "subtotal_groups": len(result.subtotals),
        "subtotal_mismatch": len(bad),
        "subtotal_mismatch_detail": bad[:20],
        "grand_total_reported": result.grand_total,
        "grand_total_computed": result.computed_total,
        "grand_total_matched": grand_ok,
        "matched": grand_ok and not bad,
    }


def reconcile_resv(result: P.ResvParseResult) -> dict:
    """RV_detail 對帳：只用「夜次」。

    ⚠️ 合計列的「間」（實測 9,484）**不對帳也不顯示**——試過 6 種公式無一
       吻合，定義未明（J11 / 規格書 §5.7）。這裡只把原文存下來供日後查證。
    """
    reported = result.reported_room_nights
    ok = reported is not None and reported == result.computed_room_nights
    return {
        "room_nights_reported": reported,
        "room_nights_computed": result.computed_room_nights,
        "room_nights_matched": ok,
        "segment_count": result.segment_count,
        # J11：僅留存原文，不參與判定
        "rooms_text_unused": result.reported_rooms_text,
        "rooms_note": "「間」定義未明（試過 6 種公式無一吻合），不對帳、不顯示",
        "matched": ok,
    }


def evaluate_quality(issues: list[P.ParseIssue], recon: dict) -> tuple[str, list[dict]]:
    """判定 quality_result 並產生摘要。

    規則（§10）：任一「整批 FAIL」條件成立 → FAIL；
                 有其他 ERROR 或 WARNING → PASS_WITH_WARNINGS；否則 PASS。
    """
    counts: dict[str, dict[str, int]] = {}
    for it in issues:
        d = counts.setdefault(it.error_code, {"severity": it.severity, "count": 0})
        d["count"] += 1

    summary = [
        {"error_code": k, "severity": v["severity"], "count": v["count"]}
        for k, v in sorted(counts.items(), key=lambda x: -x[1]["count"])
    ]

    if not recon.get("matched", False):
        return QUALITY_FAIL, summary
    if any(c in FATAL_ERROR_CODES for c in counts):
        return QUALITY_FAIL, summary
    has_issue = any(
        v["severity"] in (SEVERITY_ERROR, SEVERITY_WARNING) for v in counts.values()
    )
    return (QUALITY_PASS_WITH_WARNINGS if has_issue else QUALITY_PASS), summary


# ══════════════════════════════════════════════════════════════════════════════
#  科目分類（查 jinxu_subject_map）
# ══════════════════════════════════════════════════════════════════════════════

def load_subject_map(db: Session) -> dict[str, dict]:
    rows = db.query(JinxuSubjectMap).filter(JinxuSubjectMap.is_active == 1).all()
    return {
        r.subject_code: {
            "side": r.side,
            "group_code": r.group_code,
            "name": r.subject_name,
            "is_memo_only": r.is_memo_only,
        }
        for r in rows
    }


# ══════════════════════════════════════════════════════════════════════════════
#  validate（不寫入）
# ══════════════════════════════════════════════════════════════════════════════

def validate(
    db: Session,
    *,
    content: bytes,
    file_name: str,
    source_type: str | None = None,
) -> dict:
    """解析並驗證。回傳前端驗證報告所需的全部資訊。

    「不寫入」指的是不寫入任何**匯入資料**（raw／事實表／錯誤明細）。
    科目對照表 seed 例外——它是參考資料，且若不先確保存在，空 DB 上第一次
    驗證會誤報全部 35 個科目「未知」，把使用者嚇跑。冪等且成本極低。
    """
    ensure_jinxu_seed(db)

    digest = sha256_of(content)
    sheet_name, rows = read_sheet(content)

    detected = detect_source_type(rows)
    stype = source_type or detected
    if stype not in SOURCE_TYPES:
        return {
            "ok": False,
            "error": "無法判定來源類型，請手動選擇（客帳帳目明細表／訂房狀況表）",
            "detected_source_type": detected,
        }
    if source_type and detected and source_type != detected:
        return {
            "ok": False,
            "error": (
                f"選擇的來源類型（{SOURCE_LABELS.get(source_type)}）與檔案內容"
                f"（{SOURCE_LABELS.get(detected)}）不符"
            ),
            "detected_source_type": detected,
        }

    # 檔案層去重（§8.1）
    dup = (
        db.query(JinxuImportBatch)
        .filter(
            JinxuImportBatch.file_sha256 == digest,
            JinxuImportBatch.status == STATUS_COMMITTED,
        )
        .first()
    )

    subject_map = load_subject_map(db)

    if stype == SOURCE_FCR02_LEDGER:
        result = P.parse_fcr02(rows)
        recon = reconcile_fcr02(result)
        issues = list(result.issues)
        # 未知科目檢查（§7.8：不拒絕該列，發 WARNING）
        unknown = sorted({r.subject_code for r in result.rows} - set(subject_map))
        for code in unknown:
            issues.append(P.ParseIssue(
                0, "科目", code, P.WARN_UNKNOWN_SUBJECT,
                f"科目 {code} 未登錄於分類對照表，將歸為未分類", SEVERITY_WARNING))
        delta = _preview_delta_ledger(db, result)
        detail = {
            "row_counts": result.row_counts,
            "data_rows": len(result.rows),
            "child_rows": 0,
            "report_start_date": result.report_start_date,
            "report_end_date": result.report_end_date,
            "printed_at": result.printed_at,
            "property_name": "",
            "unknown_subjects": unknown,
        }
    else:
        result = P.parse_resv_detail(rows)
        recon = reconcile_resv(result)
        issues = list(result.issues)
        if not recon["room_nights_matched"]:
            issues.append(P.ParseIssue(
                0, "夜次",
                f'{recon["room_nights_computed"]} vs {recon["room_nights_reported"]}',
                P.ERR_ROOM_NIGHTS_MISMATCH,
                "程式彙總的房晚數與報表合計列「夜次」不符", SEVERITY_ERROR))
        delta = _preview_delta_resv(db, result)
        detail = {
            "row_counts": result.row_counts,
            "data_rows": len(result.rows),
            "child_rows": result.segment_count,
            "report_start_date": result.report_start_date,
            "report_end_date": result.report_end_date,
            "printed_at": result.printed_at,
            "property_name": result.property_name,
            "unknown_subjects": [],
        }

    quality, summary = evaluate_quality(issues, recon)

    return {
        "ok": True,
        "source_type": stype,
        "source_label": SOURCE_LABELS.get(stype, stype),
        "file_name": file_name,
        "file_sha256": digest,
        "file_size": len(content),
        "sheet_name": sheet_name,
        "total_source_rows": len(rows),
        "duplicate_batch": None if not dup else {
            "id": dup.id,
            "file_name": dup.source_file_name,
            "completed_at": dup.completed_at.isoformat(sep=" ") if dup.completed_at else "",
            "uploaded_by": dup.uploaded_by_name,
        },
        "quality_result": quality,
        "can_commit": quality != QUALITY_FAIL and dup is None,
        "reconcile": recon,
        "issue_summary": summary,
        "issue_samples": [
            {
                "source_row_no": i.source_row_no,
                "field_name": i.field_name,
                "raw_value": i.raw_value,
                "error_code": i.error_code,
                "error_message": i.error_message,
                "severity": i.severity,
            }
            for i in issues[:200]
        ],
        "delta": delta,
        **detail,
    }


def _preview_delta_ledger(db: Session, result: P.Fcr02ParseResult) -> dict:
    existing = {
        k: h for k, h in db.query(JinxuLedgerEntry.create_seq, JinxuLedgerEntry.row_hash).all()
    }
    ins = upd = skip = 0
    for r in result.rows:
        old = existing.get(r.create_seq)
        if old is None:
            ins += 1
        elif old == r.row_hash:
            skip += 1
        else:
            upd += 1
    return {"insert": ins, "update": upd, "skip": skip}


def _preview_delta_resv(db: Session, result: P.ResvParseResult) -> dict:
    existing = {
        k: h for k, h in db.query(JinxuReservation.booking_no, JinxuReservation.row_hash).all()
    }
    ins = upd = skip = 0
    for r in result.rows:
        old = existing.get(r.booking_no)
        if old is None:
            ins += 1
        elif old == r.row_hash:
            skip += 1
        else:
            upd += 1
    return {"insert": ins, "update": upd, "skip": skip}


# ══════════════════════════════════════════════════════════════════════════════
#  commit（正式匯入）
# ══════════════════════════════════════════════════════════════════════════════

def commit(
    db: Session,
    *,
    content: bytes,
    file_name: str,
    source_type: str | None = None,
    session_id: str = "",
    user_id: str | None = None,
    user_name: str = "",
    property_code: str = "",
) -> dict:
    """正式匯入。步驟 1～6 在同一個 transaction；任一步失敗即 rollback 並標 FAILED。"""
    # 科目對照表必須先存在，否則 40,706 筆全部會被歸為未分類
    ensure_jinxu_seed(db)

    digest = sha256_of(content)
    sheet_name, rows = read_sheet(content)
    detected = detect_source_type(rows)
    stype = source_type or detected
    if stype not in SOURCE_TYPES:
        raise ValueError("無法判定來源類型")

    dup = (
        db.query(JinxuImportBatch)
        .filter(
            JinxuImportBatch.file_sha256 == digest,
            JinxuImportBatch.status == STATUS_COMMITTED,
        )
        .first()
    )
    if dup:
        raise ValueError(f"此檔案已於批次 #{dup.id} 匯入過（SHA-256 相同）")

    batch = JinxuImportBatch(
        session_id=session_id,
        source_type=stype,
        property_code=property_code,
        source_file_name=file_name,
        file_sha256=digest,
        file_size=len(content),
        sheet_name=sheet_name,
        row_count_source=len(rows),
        status=STATUS_PENDING,
        uploaded_by_user_id=user_id,
        uploaded_by_name=user_name,
        program_version=PROGRAM_VERSION,
        started_at=twnow(),
    )
    db.add(batch)
    db.flush()

    try:
        if stype == SOURCE_FCR02_LEDGER:
            out = _commit_fcr02(db, batch, rows, property_code)
        else:
            out = _commit_resv(db, batch, rows, property_code)
    except Exception as exc:                       # noqa: BLE001
        db.rollback()
        _record_failed_batch(db, batch, digest, stype, file_name, len(content), str(exc))
        logger.exception("金旭匯入失敗：%s", file_name)
        raise

    if batch.quality_result == QUALITY_FAIL:
        # 對帳不符或有致命錯誤 → 整批不寫入（§10）
        db.rollback()
        _record_failed_batch(
            db, batch, digest, stype, file_name, len(content),
            "資料品質檢查未通過（對帳不符或有致命錯誤），整批未匯入",
            quality=QUALITY_FAIL, reconcile=out.get("reconcile"),
        )
        return {
            "ok": False,
            "quality_result": QUALITY_FAIL,
            "reconcile": out.get("reconcile"),
            "message": "資料品質檢查未通過，整批未匯入",
        }

    batch.status = STATUS_COMMITTED
    batch.completed_at = twnow()
    db.commit()

    return {
        "ok": True,
        "batch_id": batch.id,
        "source_type": stype,
        "source_label": SOURCE_LABELS.get(stype, stype),
        "quality_result": batch.quality_result,
        "row_count_data": batch.row_count_data,
        "row_count_inserted": batch.row_count_inserted,
        "row_count_updated": batch.row_count_updated,
        "row_count_skipped": batch.row_count_skipped,
        "row_count_rejected": batch.row_count_rejected,
        "row_count_child": batch.row_count_child,
        "reconcile": batch.get_reconcile(),
    }


def _record_failed_batch(
    db: Session,
    old_batch: JinxuImportBatch,
    digest: str,
    stype: str,
    file_name: str,
    size: int,
    message: str,
    *,
    quality: str = "",
    reconcile: dict | None = None,
) -> None:
    """rollback 之後另開一筆 FAILED 批次留痕（原 batch 已隨 rollback 消失）。"""
    failed = JinxuImportBatch(
        session_id=old_batch.session_id,
        source_type=stype,
        source_file_name=file_name,
        file_sha256=digest,
        file_size=size,
        status=STATUS_FAILED,
        quality_result=quality or QUALITY_FAIL,
        uploaded_by_user_id=old_batch.uploaded_by_user_id,
        uploaded_by_name=old_batch.uploaded_by_name,
        program_version=PROGRAM_VERSION,
        started_at=old_batch.started_at,
        completed_at=twnow(),
        error_message=message[:2000],
    )
    if reconcile:
        failed.set_reconcile(reconcile)
    db.add(failed)
    db.commit()


# ── FCR02 ────────────────────────────────────────────────────────────────────

def _commit_fcr02(
    db: Session, batch: JinxuImportBatch, rows: list[tuple], property_code: str
) -> dict:
    result = P.parse_fcr02(rows)
    recon = reconcile_fcr02(result)
    issues = list(result.issues)
    subject_map = load_subject_map(db)

    batch.report_start_date = result.report_start_date
    batch.report_end_date = result.report_end_date
    batch.printed_at = result.printed_at
    batch.row_count_data = len(result.rows)
    batch.row_count_rejected = sum(1 for i in issues if i.severity == SEVERITY_ERROR)
    batch.set_totals({
        "subtotals": result.subtotals[:50],
        "grand_total": result.grand_total,
        "row_counts": result.row_counts,
    })
    batch.set_reconcile(recon)

    quality, _ = evaluate_quality(issues, recon)
    batch.quality_result = quality
    if quality == QUALITY_FAIL:
        return {"reconcile": recon}

    # 1) 原始層（永不覆蓋，每批次完整寫入）
    raw_rows = []
    for r in result.rows:
        v = r.raw_values
        raw_rows.append({
            "batch_id": batch.id, "source_row_no": r.source_row_no,
            "row_hash": r.row_hash, "create_seq": r.create_seq,
            "date_text": v[0], "create_seq_text": v[1], "shift_text": v[2],
            "operator_text": v[3], "room_no_text": v[4], "folio_name_text": v[5],
            "subject_text": v[6], "amount_text": v[7], "document_no_text": v[8],
            "ar_code_text": v[9], "remark_text": v[10], "transfer_text": v[11],
            "booking_no_text": v[12], "folio_type_text": v[13],
        })
    raw_ids = _bulk_insert_returning_ids(db, JinxuFcr02Raw, raw_rows, "create_seq")

    # 2) 事實層 INSERT / UPDATE / SKIP（§8.2）
    existing = {
        e.create_seq: e
        for e in db.query(JinxuLedgerEntry)
        .filter(JinxuLedgerEntry.create_seq.in_([r.create_seq for r in result.rows]))
        .all()
    } if result.rows else {}

    now = twnow()
    to_insert = []
    ins = upd = skip = 0
    for r in result.rows:
        meta = subject_map.get(r.subject_code)
        group_code = meta["group_code"] if meta else GROUP_UNCLASSIFIED
        memo = meta["is_memo_only"] if meta else r.is_memo_only
        if not meta:
            issues.append(P.ParseIssue(
                r.source_row_no, "科目", r.subject_code, P.WARN_UNKNOWN_SUBJECT,
                f"科目 {r.subject_code} 未登錄，歸為未分類", SEVERITY_WARNING))

        payload = {
            "batch_id": batch.id,
            "raw_id": raw_ids.get(r.create_seq, 0),
            "create_seq": r.create_seq,
            "row_hash": r.row_hash,
            "business_date": r.business_date,
            "created_at_text": r.created_at_text,
            "created_date": r.created_date,
            "shift": r.shift,
            "is_manual_shift": r.is_manual_shift,
            "operator_id": r.operator_id,
            "room_no": r.room_no,
            "room_kind": r.room_kind,
            "folio_name": r.folio_name,
            "folio_seq": r.folio_seq,
            "folio_type": r.folio_type,
            "subject_code": r.subject_code,
            "subject_name": r.subject_name,
            "subject_side": r.subject_side,
            "subject_group": group_code,
            "amount": r.amount,
            "is_reversal": r.is_reversal,
            "is_memo_only": memo,
            "booking_no": r.booking_no,
            "document_no": r.document_no,
            "ar_code": r.ar_code,
            "transfer_no": r.transfer_no,
            "remark": r.remark,          # J17：存但 API 不得回傳
            "property_code": property_code,
        }

        old = existing.get(r.create_seq)
        if old is None:
            payload["first_imported_at"] = now
            payload["last_updated_at"] = now
            to_insert.append(payload)
            ins += 1
        elif old.row_hash == r.row_hash:
            skip += 1
        else:
            # ⚠️ 先擷取舊值再覆蓋——稽核軌跡的重點就是「變更前是什麼」
            before = f"{old.business_date} {old.subject_code} {old.amount}"
            for k, val in payload.items():
                setattr(old, k, val)
            old.last_updated_at = now
            upd += 1
            issues.append(P.ParseIssue(
                r.source_row_no, "建檔時間", r.create_seq, P.WARN_ENTRY_UPDATED,
                f"既有分錄內容變更，已覆蓋。變更前：{before} → "
                f"變更後：{r.business_date} {r.subject_code} {r.amount}",
                SEVERITY_WARNING))

    _bulk_insert(db, JinxuLedgerEntry, to_insert)

    batch.row_count_inserted = ins
    batch.row_count_updated = upd
    batch.row_count_skipped = skip
    _insert_issues(db, batch.id, issues)
    return {"reconcile": recon}


# ── RESV_DETAIL ──────────────────────────────────────────────────────────────

def _commit_resv(
    db: Session, batch: JinxuImportBatch, rows: list[tuple], property_code: str
) -> dict:
    result = P.parse_resv_detail(rows, property_code=property_code)
    recon = reconcile_resv(result)
    issues = list(result.issues)
    if not recon["room_nights_matched"]:
        issues.append(P.ParseIssue(
            0, "夜次",
            f'{recon["room_nights_computed"]} vs {recon["room_nights_reported"]}',
            P.ERR_ROOM_NIGHTS_MISMATCH,
            "程式彙總的房晚數與報表合計列「夜次」不符", SEVERITY_ERROR))

    batch.property_name = result.property_name
    batch.report_start_date = result.report_start_date
    batch.report_end_date = result.report_end_date
    batch.printed_at = result.printed_at
    batch.row_count_data = len(result.rows)
    batch.row_count_child = result.segment_count
    batch.row_count_rejected = sum(1 for i in issues if i.severity == SEVERITY_ERROR)
    batch.set_totals({
        "room_nights_reported": result.reported_room_nights,
        "rooms_text_unused": result.reported_rooms_text,
        "row_counts": result.row_counts,
    })
    batch.set_reconcile(recon)

    quality, _ = evaluate_quality(issues, recon)
    batch.quality_result = quality
    if quality == QUALITY_FAIL:
        return {"reconcile": recon}

    # 1) 原始層（guest_name_text 已是遮罩後版本，parser 保證）
    raw_rows = []
    for r in result.rows:
        v = r.raw_values
        raw_rows.append({
            "batch_id": batch.id, "source_row_no": r.source_row_no,
            "row_hash": r.row_hash, "booking_no": r.booking_no,
            "status_text": v[0], "arrival_text": v[1], "departure_text": v[2],
            "booking_no_text": v[3], "guest_name_text": v[4], "company_text": v[5],
            "rate_code_text": v[6], "source_text": v[7], "resv_type_text": v[8],
            "stay_detail_text": v[9],
        })
    raw_ids = _bulk_insert_returning_ids(db, JinxuResvRaw, raw_rows, "booking_no")

    # 2) 事實層
    keys = [r.booking_no for r in result.rows]
    existing = {
        e.booking_no: e
        for e in db.query(JinxuReservation)
        .filter(JinxuReservation.booking_no.in_(keys))
        .all()
    } if keys else {}

    now = twnow()
    ins = upd = skip = 0
    rebuild_ids: list[int] = []          # 需要重建子表的 reservation_id
    segments_by_booking: dict[str, list] = {}

    for r in result.rows:
        payload = {
            "batch_id": batch.id,
            "raw_id": raw_ids.get(r.booking_no, 0),
            "booking_no": r.booking_no,
            "row_hash": r.row_hash,
            "status_code": r.status_code,
            "status_main": r.status_main,
            "status_kind": r.status_kind,
            "is_cancelled": r.is_cancelled,
            "is_dummy": r.is_dummy,
            "is_no_show": r.is_no_show,
            "arrival_date": r.arrival_date,
            "departure_date": r.departure_date,
            "nights": r.nights,
            "billable_nights": r.billable_nights,
            "is_day_use": r.is_day_use,
            "guest_name_masked": r.guest_name_masked,
            "guest_identity_hash": r.guest_identity_hash,
            "guest_is_placeholder": r.guest_is_placeholder,
            "guest_has_cjk": r.guest_has_cjk,
            "company_name": r.company_name,
            "rate_code": r.rate_code,
            "source_name": r.source_name,
            "resv_type": r.resv_type,
            "is_group": r.is_group,
            "stay_segment_count": r.stay_segment_count,
            "total_room_nights": r.total_room_nights,
            "total_quoted_amount": r.total_quoted_amount,
            "room_type_codes": r.room_type_codes,
            "has_nights_mismatch": r.has_nights_mismatch,
            "property_code": property_code,
        }

        old = existing.get(r.booking_no)
        if old is None:
            obj = JinxuReservation(**payload, first_imported_at=now, last_updated_at=now)
            db.add(obj)
            db.flush()
            segments_by_booking[r.booking_no] = (obj.id, r.segments)
            ins += 1
        elif old.row_hash == r.row_hash:
            # 內容沒變 → 連子表都不動（row_hash 已涵蓋「住宿資料」欄）
            skip += 1
        else:
            # ⚠️ 先擷取舊值再覆蓋。訂房狀態變化（CNFM→ACTV→CXNL）正是取消分析
            #    最有價值的軌跡，覆蓋後就查不到了。
            old_status = old.status_code
            old_rn = old.total_room_nights
            old_segs = old.stay_segment_count
            for k, val in payload.items():
                setattr(old, k, val)
            old.last_updated_at = now
            rebuild_ids.append(old.id)
            segments_by_booking[r.booking_no] = (old.id, r.segments)
            upd += 1
            changes = []
            if old_status != r.status_code:
                changes.append(f"狀態 {old_status}→{r.status_code}")
            if old_rn != r.total_room_nights:
                changes.append(f"房晚 {old_rn}→{r.total_room_nights}")
            if old_segs != r.stay_segment_count:
                changes.append(f"段數 {old_segs}→{r.stay_segment_count}")
            issues.append(P.ParseIssue(
                r.source_row_no, "訂房號碼", r.booking_no, P.WARN_ENTRY_UPDATED,
                "既有訂房內容變更，已覆蓋並重建住宿明細"
                + ("：" + "、".join(changes) if changes else "（欄位值變動）"),
                SEVERITY_WARNING))

    # 3) 子表：UPDATE 的先整組刪除，再與 INSERT 一併重建（§8.2）
    if rebuild_ids:
        for i in range(0, len(rebuild_ids), BULK_CHUNK):
            chunk = rebuild_ids[i:i + BULK_CHUNK]
            db.query(JinxuReservationStay).filter(
                JinxuReservationStay.reservation_id.in_(chunk)
            ).delete(synchronize_session=False)

    stay_rows = []
    for booking_no, (resv_id, segs) in segments_by_booking.items():
        for s in segs:
            stay_rows.append({
                "reservation_id": resv_id,
                "booking_no": booking_no,
                "seq_no": s.seq_no,
                "room_type_code": s.room_type_code,
                "rooms": s.rooms,
                "nights": s.nights,
                "amount_per_night": s.amount_per_night,
                "unit_rate": s.unit_rate,
                "room_nights": s.room_nights,
                "segment_amount": s.segment_amount,
                "has_n_suffix": s.has_n_suffix,
                "raw_segment": s.raw_segment,
            })
    _bulk_insert(db, JinxuReservationStay, stay_rows)

    batch.row_count_inserted = ins
    batch.row_count_updated = upd
    batch.row_count_skipped = skip
    _insert_issues(db, batch.id, issues)
    return {"reconcile": recon}


# ── 共用寫入 helper ──────────────────────────────────────────────────────────

def _bulk_insert(db: Session, model, rows: list[dict]) -> None:
    for i in range(0, len(rows), BULK_CHUNK):
        db.bulk_insert_mappings(model, rows[i:i + BULK_CHUNK])
    if rows:
        db.flush()


def _bulk_insert_returning_ids(
    db: Session, model, rows: list[dict], key_field: str
) -> dict[str, int]:
    """bulk_insert 後回查本批次的 id，供事實表的 raw_id 對應。"""
    if not rows:
        return {}
    _bulk_insert(db, model, rows)
    batch_id = rows[0]["batch_id"]
    pairs = db.query(getattr(model, key_field), model.id).filter(
        model.batch_id == batch_id
    ).all()
    return {k: v for k, v in pairs}


def _insert_issues(db: Session, batch_id: int, issues: list[P.ParseIssue]) -> None:
    rows = [{
        "batch_id": batch_id,
        "source_row_no": i.source_row_no,
        "field_name": i.field_name[:50],
        "raw_value": (i.raw_value or "")[:500],
        "error_code": i.error_code[:30],
        "error_message": i.error_message[:500],
        "severity": i.severity,
        "created_at": twnow(),
    } for i in issues]
    _bulk_insert(db, JinxuImportError, rows)


# ══════════════════════════════════════════════════════════════════════════════
#  rollback / status
# ══════════════════════════════════════════════════════════════════════════════

def rollback_batch(db: Session, batch_id: int) -> dict:
    """回捲批次：刪除該批次的 raw 列。

    ⚠️ 事實表的 UPDATE **無法自動回捲**（舊值已被覆蓋）。本函式會列出該批次
       曾 UPDATE 過的業務鍵清單，由財務人工判斷（§8.4）。
    """
    batch = db.get(JinxuImportBatch, batch_id)
    if not batch:
        raise ValueError(f"批次 #{batch_id} 不存在")
    if batch.status != STATUS_COMMITTED:
        raise ValueError(f"批次 #{batch_id} 狀態為 {batch.status}，只有 COMMITTED 可回捲")

    updated_keys = [
        e.raw_value
        for e in db.query(JinxuImportError)
        .filter(
            JinxuImportError.batch_id == batch_id,
            JinxuImportError.error_code == P.WARN_ENTRY_UPDATED,
        )
        .all()
    ]

    if batch.source_type == SOURCE_FCR02_LEDGER:
        deleted = db.query(JinxuFcr02Raw).filter(
            JinxuFcr02Raw.batch_id == batch_id
        ).delete(synchronize_session=False)
    else:
        deleted = db.query(JinxuResvRaw).filter(
            JinxuResvRaw.batch_id == batch_id
        ).delete(synchronize_session=False)

    batch.status = STATUS_ROLLED_BACK
    batch.error_message = (
        f"已回捲，刪除原始列 {deleted} 筆。"
        f"注意：本批次曾覆蓋 {len(updated_keys)} 筆既有資料，舊值無法還原。"
    )
    db.commit()

    return {
        "ok": True,
        "batch_id": batch_id,
        "deleted_raw_rows": deleted,
        "updated_keys_count": len(updated_keys),
        "updated_keys": updated_keys[:500],
        "warning": (
            "事實表的 UPDATE 無法自動回捲，舊值已被覆蓋。"
            "上列業務鍵需人工確認是否要以舊檔重新匯入。"
        ) if updated_keys else "",
    }


def get_import_status(db: Session) -> dict:
    """兩個來源各自的資料涵蓋範圍（§12.1 /status）。"""
    out: dict = {"sources": {}}

    led = db.query(
        func.count(JinxuLedgerEntry.id),
        func.min(JinxuLedgerEntry.business_date),
        func.max(JinxuLedgerEntry.business_date),
    ).one()
    out["sources"][SOURCE_FCR02_LEDGER] = {
        "label": SOURCE_LABELS[SOURCE_FCR02_LEDGER],
        "row_count": led[0] or 0,
        "date_start": led[1] or "",
        "date_end": led[2] or "",
        "has_data": bool(led[0]),
    }

    rv = db.query(
        func.count(JinxuReservation.id),
        func.min(JinxuReservation.arrival_date),
        func.max(JinxuReservation.arrival_date),
    ).one()
    stay_count = db.query(func.count(JinxuReservationStay.id)).scalar() or 0
    out["sources"][SOURCE_RESV_DETAIL] = {
        "label": SOURCE_LABELS[SOURCE_RESV_DETAIL],
        "row_count": rv[0] or 0,
        "child_count": stay_count,
        "date_start": rv[1] or "",
        "date_end": rv[2] or "",
        "has_data": bool(rv[0]),
    }

    # 兩邊都有資料時，交叉分析（訂價 vs 實收）才可用
    out["cross_analysis_available"] = (
        out["sources"][SOURCE_FCR02_LEDGER]["has_data"]
        and out["sources"][SOURCE_RESV_DETAIL]["has_data"]
    )

    # YoY 需跨年度資料
    years = set()
    for key in ("date_start", "date_end"):
        for src in out["sources"].values():
            if src.get(key):
                years.add(src[key][:4])
    out["years_covered"] = sorted(years)
    out["yoy_available"] = len(years) > 1

    last = (
        db.query(JinxuImportBatch)
        .filter(JinxuImportBatch.status == STATUS_COMMITTED)
        .order_by(JinxuImportBatch.completed_at.desc())
        .first()
    )
    out["last_batch"] = None if not last else {
        "id": last.id,
        "source_type": last.source_type,
        "source_label": last.source_label,
        "file_name": last.source_file_name,
        "completed_at": last.completed_at.isoformat(sep=" ") if last.completed_at else "",
        "uploaded_by": last.uploaded_by_name,
    }
    return out
