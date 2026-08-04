"""
OPERA 匯入服務 — 驗證、寫入、去重、版本管理與對帳

規格書：docs/SPEC_opera_analytics.md §6、§7、§8

流程重點
  validate()：只解析與檢查，完全不寫入資料庫。
  commit()  ：整批交易，任一步失敗 rollback 並記錄 FAILED 批次。

⚠️ 本模組全部是同步函式（def），由 router 透過 run_in_threadpool 呼叫。
   不可改成 async def 後直接呼叫 db.query()（會凍結整站，見 CLAUDE.md）。
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.sync_lock import sync_lock
from app.core.time import twnow
from app.models.audit_log import AuditLog
from app.models.opera_departure import OperaDepartureRaw, OperaDepartureStay
from app.models.opera_import import (
    OperaImportBatch,
    OperaImportError,
    QUALITY_FAIL,
    QUALITY_PASS,
    QUALITY_PASS_WITH_WARNINGS,
    SOURCE_DEPARTURE,
    SOURCE_HISTORY_FORECAST,
    STATUS_COMMITTED,
    STATUS_FAILED,
    STATUS_PENDING,
)
from app.models.opera_revenue import (
    OperaHistoryForecastRaw,
    OperaRevenueDaily,
    RECORD_TYPE_HISTORY,
)
from app.services import opera_parser as P

logger = logging.getLogger(__name__)

PROGRAM_VERSION = "1.0.0"
BULK_CHUNK = 2_000
MAX_UPLOAD_BYTES = 50 * 1024 * 1024   # 50 MB（規格書 §13.3）

SOURCE_LABELS = {
    SOURCE_DEPARTURE: "Departure All",
    SOURCE_HISTORY_FORECAST: "History and Forecast",
}


class OperaImportError_(Exception):
    """匯入流程可預期的失敗（會轉成 HTTP 400）。"""


# ══════════════════════════════════════════════════════════════════════════════
# 解析入口
# ══════════════════════════════════════════════════════════════════════════════

def parse_content(source_type: str, content: bytes, property_code: str = "") -> P.ParseResult:
    if source_type == SOURCE_DEPARTURE:
        return P.parse_departure(content)
    if source_type == SOURCE_HISTORY_FORECAST:
        return P.parse_history_forecast(content, property_code=property_code)
    raise OperaImportError_(f"不支援的來源類型：{source_type}")


def reconcile(source_type: str, result: P.ParseResult) -> dict:
    if source_type == SOURCE_DEPARTURE:
        return P.reconcile_departure(result)
    return P.reconcile_history_forecast(result)


def detect_source_type(file_name: str, content: bytes) -> str | None:
    """依表頭第一欄判定來源類型（檔名不可靠，OPERA 匯出檔名是流水號）。"""
    text_head, _ = P.detect_encoding(content[:4096])
    first_line = text_head.split("\n", 1)[0]
    header = [c.strip().upper() for c in first_line.split("\t")]
    if not header:
        return None
    if header[0] == "DEPARTURE":
        return SOURCE_DEPARTURE
    if header[0] == "GPAGEID" or "CONSIDERED_DATE" in header:
        return SOURCE_HISTORY_FORECAST
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 品質判定（規格書 §8）
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_quality(result: P.ParseResult, recon: dict) -> tuple[str, list[dict]]:
    """回傳 (PASS / PASS_WITH_WARNINGS / FAIL, 檢查明細)。"""
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str, fatal: bool = True) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail, "fatal": fatal})

    fatal_issue_codes = {
        P.ERR_MISSING_REQUIRED, P.ERR_BAD_DATE, P.ERR_BAD_WIDTH,
        P.ERR_DUPLICATE_KEY,
    }
    fatal_issues = [i for i in result.issues if i.severity == "ERROR" and i.error_code in fatal_issue_codes]
    warn_issues = [i for i in result.issues if i.severity == "WARNING"]

    add("有效列數", len(result.records) > 0, f"{len(result.records):,} 列")
    add("必要欄位／日期解析",
        not any(i.error_code in (P.ERR_MISSING_REQUIRED, P.ERR_BAD_DATE) for i in fatal_issues),
        f"錯誤 {len([i for i in fatal_issues if i.error_code in (P.ERR_MISSING_REQUIRED, P.ERR_BAD_DATE)]):,} 列")
    add("Footer 對帳", bool(recon.get("ok")),
        "；".join(f"{i['label']} 差異 {i['diff']:,.2f}" for i in recon.get("items", [])) or "無 footer")
    add("批次對帳",
        result.row_count_source == len(result.records) + result.row_count_rejected,
        f"raw {result.row_count_source:,} = fact {len(result.records):,} + rejected {result.row_count_rejected:,}")

    if result.source_type == SOURCE_DEPARTURE:
        add("續行合併",
            all(len(r.raw) == 52 for r in result.records),
            f"合併 {result.merged_pairs:,} 對")
        add("零房數列", result.stats.get("zero_room_rows", 0) == 0,
            f"{result.stats.get('zero_room_rows', 0):,} 列 NO_OF_ROOMS=0（語意待確認）", fatal=False)
    else:
        add("History 唯一性",
            not any(i.error_code == P.ERR_DUPLICATE_KEY for i in result.issues),
            "同日期同類型無重複")
        add("日期連續性", result.stats.get("date_gaps", 0) == 0,
            f"缺口 {result.stats.get('date_gaps', 0):,} 天", fatal=False)
        add("營收合理性",
            not any(i.error_code == P.WARN_NEGATIVE_REVENUE for i in result.issues),
            f"負營收 {len([i for i in result.issues if i.error_code == P.WARN_NEGATIVE_REVENUE]):,} 天", fatal=False)
        add("超賣檢查",
            not any(i.error_code == P.WARN_OVERSOLD for i in result.issues),
            f"超賣 {len([i for i in result.issues if i.error_code == P.WARN_OVERSOLD]):,} 天", fatal=False)

    if any(not c["ok"] and c["fatal"] for c in checks):
        return QUALITY_FAIL, checks
    if warn_issues or any(not c["ok"] for c in checks):
        return QUALITY_PASS_WITH_WARNINGS, checks
    return QUALITY_PASS, checks


# ══════════════════════════════════════════════════════════════════════════════
# validate — 不寫入
# ══════════════════════════════════════════════════════════════════════════════

def validate(
    db: Session,
    file_name: str,
    content: bytes,
    source_type: str | None = None,
    property_code_hint: str = "",
) -> dict:
    if len(content) > MAX_UPLOAD_BYTES:
        raise OperaImportError_(
            f"檔案過大（{len(content) / 1024 / 1024:.1f} MB），上限 {MAX_UPLOAD_BYTES // 1024 // 1024} MB"
        )

    resolved = source_type or detect_source_type(file_name, content)
    if not resolved:
        raise OperaImportError_(
            "無法判定報表類型。請確認上傳的是 OPERA 匯出的 Departure All 或 "
            "History and Forecast TXT（以 Tab 分隔，第一列為欄位名稱）。"
        )

    sha = P.sha256_bytes(content)
    _, encoding = P.detect_encoding(content[:8192])

    # 檔案層去重（§6.1）
    existing = (
        db.query(OperaImportBatch)
        .filter(
            OperaImportBatch.file_sha256 == sha,
            OperaImportBatch.status == STATUS_COMMITTED,
        )
        .order_by(OperaImportBatch.id.desc())
        .first()
    )

    prop = property_code_hint or _latest_property_code(db) or ""
    result = parse_content(resolved, content, property_code=prop)
    if result.property_code:
        prop = result.property_code
    recon = reconcile(resolved, result)
    quality, checks = evaluate_quality(result, recon)

    # 內容是否有更新：比對 fact 層現有版本
    delta = _preview_delta(db, resolved, result)

    return {
        "source_type":       resolved,
        "source_label":      SOURCE_LABELS.get(resolved, resolved),
        "file_name":         file_name,
        "file_size":         len(content),
        "file_sha256":       sha,
        "encoding":          encoding,
        "property_code":     prop,
        "report_start_date": result.report_start_date,
        "report_end_date":   result.report_end_date,
        "row_count_source":  result.row_count_source,
        "row_count_valid":   len(result.records),
        "row_count_rejected": result.row_count_rejected,
        "merged_pairs":      result.merged_pairs,
        "stats":             result.stats,
        "footer":            result.footer,
        "reconcile":         recon,
        "quality_result":    quality,
        "quality_checks":    checks,
        "duplicate": None if not existing else {
            "batch_id":    existing.id,
            "file_name":   existing.source_file_name,
            "imported_at": existing.completed_at.strftime("%Y/%m/%d %H:%M") if existing.completed_at else "",
        },
        "file_state": (
            "DUPLICATE" if existing
            else "UPDATED" if delta["will_update"]
            else "NEW"
        ),
        "delta":  delta,
        "issues": [i.as_dict() for i in result.issues[:100]],
        "issue_total": len(result.issues),
        "can_commit": quality != QUALITY_FAIL and existing is None,
        "needs_warning_ack": quality == QUALITY_PASS_WITH_WARNINGS,
    }


def _latest_property_code(db: Session) -> str:
    row = (
        db.query(OperaImportBatch.property_code)
        .filter(OperaImportBatch.property_code != "")
        .order_by(OperaImportBatch.id.desc())
        .first()
    )
    return row[0] if row else ""


def _preview_delta(db: Session, source_type: str, result: P.ParseResult) -> dict:
    """預估新增／更新／略過筆數（不寫入）。"""
    current = _load_current_hashes(db, source_type, result.property_code)
    new = upd = same = 0
    for rec in result.records:
        old_hash = current.get(rec.record_key)
        if old_hash is None:
            new += 1
        elif old_hash == rec.row_hash:
            same += 1
        else:
            upd += 1
    return {
        "will_insert": new,
        "will_update": upd,
        "will_skip":   same,
    }


def _load_current_hashes(db: Session, source_type: str, property_code: str) -> dict[str, str]:
    """載入目前有效版本的 record_key → row_hash。"""
    if source_type == SOURCE_DEPARTURE:
        q = (
            db.query(OperaDepartureStay.record_key, OperaDepartureStay.row_hash)
            .filter(OperaDepartureStay.is_current == 1)
        )
        if property_code:
            q = q.filter(OperaDepartureStay.property_code == property_code)
    else:
        q = (
            db.query(
                OperaRevenueDaily.property_code,
                OperaRevenueDaily.record_type,
                OperaRevenueDaily.business_date,
                OperaRevenueDaily.row_hash,
            )
            .filter(OperaRevenueDaily.is_current == 1)
        )
        if property_code:
            q = q.filter(OperaRevenueDaily.property_code == property_code)
        return {f"{p}|{rt}|{bd}": h for p, rt, bd, h in q.all()}
    return {k: h for k, h in q.all()}


# ══════════════════════════════════════════════════════════════════════════════
# commit — 整批交易
# ══════════════════════════════════════════════════════════════════════════════

def commit(
    db: Session,
    file_name: str,
    content: bytes,
    source_type: str | None = None,
    session_id: str = "",
    user_id: str | None = None,
    user_name: str = "",
    ip_address: str | None = None,
    allow_warnings: bool = False,
    progress: Callable[[str, int], None] | None = None,
) -> dict:
    """整批匯入。任一步驟失敗 → rollback + 記錄 FAILED 批次（規格書 §7.2）。"""
    def _tick(stage: str, pct: int) -> None:
        if progress:
            try:
                progress(stage, pct)
            except Exception:      # 進度回報不得影響匯入
                pass

    resolved = source_type or detect_source_type(file_name, content)
    if not resolved:
        raise OperaImportError_("無法判定報表類型，請確認檔案來源。")

    sha = P.sha256_bytes(content)
    _, encoding = P.detect_encoding(content[:8192])
    session_id = session_id or str(uuid.uuid4())

    dup = (
        db.query(OperaImportBatch)
        .filter(OperaImportBatch.file_sha256 == sha, OperaImportBatch.status == STATUS_COMMITTED)
        .first()
    )
    if dup:
        raise OperaImportError_(
            f"此檔案已於批次 #{dup.id} 匯入過（{dup.source_file_name}），不重複匯入。"
        )

    _tick("解析檔案", 10)
    prop = _latest_property_code(db)
    result = parse_content(resolved, content, property_code=prop)
    prop = result.property_code or prop
    result.property_code = prop
    recon = reconcile(resolved, result)
    quality, checks = evaluate_quality(result, recon)

    if quality == QUALITY_FAIL:
        raise OperaImportError_("資料品質檢查未通過（FAIL），請先修正來源檔案。")
    if quality == QUALITY_PASS_WITH_WARNINGS and not allow_warnings:
        raise OperaImportError_("資料品質檢查為 PASS WITH WARNINGS，需確認警示後才能匯入。")

    batch = OperaImportBatch(
        session_id=session_id,
        source_type=resolved,
        property_code=prop,
        source_file_name=file_name,
        file_sha256=sha,
        file_size=len(content),
        encoding=encoding,
        report_start_date=result.report_start_date,
        report_end_date=result.report_end_date,
        row_count_source=result.row_count_source,
        row_count_rejected=result.row_count_rejected,
        status=STATUS_PENDING,
        quality_result=quality,
        footer_json=json.dumps(result.footer, ensure_ascii=False),
        started_at=twnow(),
        uploaded_by_user_id=user_id,
        uploaded_by_name=user_name,
        program_version=PROGRAM_VERSION,
    )
    db.add(batch)
    db.flush()          # 取得 batch.id，尚未 commit
    batch_id = batch.id

    try:
        # 跨行程鎖：避免與 Ragic 同步同時大量寫入 SQLite（規格書 §14）
        with sync_lock(f"OPERA 匯入 #{batch_id}"):
            _tick("寫入原始資料層", 30)
            raw_id_map = _insert_raw(db, resolved, batch_id, result)

            _tick("更新事實表版本", 60)
            if resolved == SOURCE_DEPARTURE:
                counts = _upsert_departure_stay(db, batch_id, result, raw_id_map)
            else:
                counts = _upsert_revenue_daily(db, batch_id, result, raw_id_map)

            _tick("寫入錯誤明細", 85)
            _insert_issues(db, batch_id, result)

            batch.row_count_inserted = counts["inserted"]
            batch.row_count_updated = counts["updated"]
            batch.row_count_skipped = counts["skipped"]
            batch.status = STATUS_COMMITTED
            batch.completed_at = twnow()
            batch.reconcile_json = json.dumps(
                {"footer": recon, "quality_checks": checks, "stats": result.stats},
                ensure_ascii=False,
            )
            db.add(AuditLog(
                user_id=user_id,
                action="opera_import",
                resource_type="opera_import_batch",
                resource_id=str(batch_id),
                ip_address=ip_address,
                extra={
                    "source_type": resolved,
                    "file_name": file_name,
                    "file_sha256": sha,
                    "report_start_date": result.report_start_date,
                    "report_end_date": result.report_end_date,
                    "row_count_source": result.row_count_source,
                    "inserted": counts["inserted"],
                    "updated": counts["updated"],
                    "skipped": counts["skipped"],
                    "rejected": result.row_count_rejected,
                    "quality_result": quality,
                },
            ))
            db.flush()
    except Exception as exc:
        logger.exception("[OPERA] 匯入失敗，整批 rollback（batch=%s）", batch_id)
        db.rollback()
        _record_failed_batch(db, session_id, resolved, prop, file_name, sha,
                             len(content), encoding, user_id, user_name, str(exc))
        raise

    _tick("完成", 100)
    return {
        "batch_id":       batch_id,
        "session_id":     session_id,
        "source_type":    resolved,
        "source_label":   SOURCE_LABELS.get(resolved, resolved),
        "quality_result": quality,
        "quality_checks": checks,
        "reconcile":      recon,
        "stats":          result.stats,
        "inserted":       counts["inserted"],
        "updated":        counts["updated"],
        "skipped":        counts["skipped"],
        "rejected":       result.row_count_rejected,
        "issue_total":    len(result.issues),
        "report_start_date": result.report_start_date,
        "report_end_date":   result.report_end_date,
    }


def _record_failed_batch(
    db: Session, session_id: str, source_type: str, property_code: str,
    file_name: str, sha: str, size: int, encoding: str,
    user_id: str | None, user_name: str, message: str,
) -> None:
    """在獨立交易中記錄失敗批次，讓使用者在匯入紀錄看得到。"""
    try:
        db.add(OperaImportBatch(
            session_id=session_id,
            source_type=source_type,
            property_code=property_code,
            source_file_name=file_name,
            file_sha256=sha,
            file_size=size,
            encoding=encoding,
            status=STATUS_FAILED,
            quality_result=QUALITY_FAIL,
            started_at=twnow(),
            completed_at=twnow(),
            uploaded_by_user_id=user_id,
            uploaded_by_name=user_name,
            program_version=PROGRAM_VERSION,
            error_message=message[:2000],
        ))
        db.commit()
    except Exception:
        logger.exception("[OPERA] 連 FAILED 批次都寫不進去")
        db.rollback()


# ── 原始層寫入 ────────────────────────────────────────────────────────────────

def _insert_raw(
    db: Session, source_type: str, batch_id: int, result: P.ParseResult
) -> dict[int, int]:
    """批次寫入 raw 表，回傳 source_row_no → raw_id 對照。"""
    model = OperaDepartureRaw if source_type == SOURCE_DEPARTURE else OperaHistoryForecastRaw
    now = twnow()
    rows: list[dict[str, Any]] = []

    for rec in result.records:
        row: dict[str, Any] = {
            "batch_id":      batch_id,
            "source_row_no": rec.source_row_no,
            "row_hash":      rec.row_hash,
            "record_key":    rec.record_key,
            "imported_at":   now,
        }
        if source_type == SOURCE_DEPARTURE:
            row["source_row_no_end"] = rec.source_row_no_end
        for col, value in rec.raw.items():
            row[col.lower()] = value
        rows.append(row)

    for i in range(0, len(rows), BULK_CHUNK):
        db.bulk_insert_mappings(model, rows[i:i + BULK_CHUNK])
    db.flush()

    pairs = (
        db.query(model.source_row_no, model.id)
        .filter(model.batch_id == batch_id)
        .all()
    )
    return {int(no): int(rid) for no, rid in pairs}


# ── Departure 事實表 upsert（規格書 §6.3）─────────────────────────────────────

def _upsert_departure_stay(
    db: Session, batch_id: int, result: P.ParseResult, raw_id_map: dict[int, int]
) -> dict[str, int]:
    current = _load_current_hashes(db, SOURCE_DEPARTURE, result.property_code)
    now = twnow()
    to_insert: list[dict[str, Any]] = []
    superseded_keys: list[str] = []
    inserted = updated = skipped = 0

    for rec in result.records:
        old_hash = current.get(rec.record_key)
        if old_hash == rec.row_hash:
            skipped += 1
            continue
        if old_hash is not None:
            superseded_keys.append(rec.record_key)
            updated += 1
        else:
            inserted += 1

        fact = dict(rec.fact)
        fact.update({
            "batch_id":    batch_id,
            "raw_id":      raw_id_map.get(rec.source_row_no, 0),
            "is_current":  1,
            "imported_at": now,
        })
        to_insert.append(fact)

    _mark_superseded(db, OperaDepartureStay, "record_key", superseded_keys)

    for i in range(0, len(to_insert), BULK_CHUNK):
        db.bulk_insert_mappings(OperaDepartureStay, to_insert[i:i + BULK_CHUNK])
    db.flush()
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


# ── 每日營收事實表 upsert（規格書 §6.4）───────────────────────────────────────

def _upsert_revenue_daily(
    db: Session, batch_id: int, result: P.ParseResult, raw_id_map: dict[int, int]
) -> dict[str, int]:
    current = _load_current_hashes(db, SOURCE_HISTORY_FORECAST, result.property_code)
    now = twnow()
    to_insert: list[dict[str, Any]] = []
    superseded: list[tuple[str, str, str]] = []
    inserted = updated = skipped = 0

    for rec in result.records:
        old_hash = current.get(rec.record_key)
        if old_hash == rec.row_hash:
            skipped += 1
            continue
        if old_hash is not None:
            superseded.append((
                rec.fact["property_code"], rec.fact["record_type"], rec.fact["business_date"],
            ))
            updated += 1
        else:
            inserted += 1

        fact = {k: v for k, v in rec.fact.items() if k != "record_key"}
        fact.update({
            "batch_id":    batch_id,
            "raw_id":      raw_id_map.get(rec.source_row_no, 0),
            "is_current":  1,
            "imported_at": now,
        })
        to_insert.append(fact)

    # History 不得被 Forecast 覆蓋：record_type 不同即不同業務鍵，
    # 故只需把「同 property + 同 record_type + 同日期」的舊版本下架。
    for chunk_start in range(0, len(superseded), 500):
        chunk = superseded[chunk_start:chunk_start + 500]
        for prop, rtype, bdate in chunk:
            (
                db.query(OperaRevenueDaily)
                .filter(
                    OperaRevenueDaily.property_code == prop,
                    OperaRevenueDaily.record_type == rtype,
                    OperaRevenueDaily.business_date == bdate,
                    OperaRevenueDaily.is_current == 1,
                )
                .update({"is_current": 0}, synchronize_session=False)
            )

    for i in range(0, len(to_insert), BULK_CHUNK):
        db.bulk_insert_mappings(OperaRevenueDaily, to_insert[i:i + BULK_CHUNK])
    db.flush()
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


def _mark_superseded(db: Session, model, key_field: str, keys: list[str]) -> None:
    """把舊版本 is_current 設為 0（分批避免 SQL 參數上限）。"""
    if not keys:
        return
    column = getattr(model, key_field)
    for i in range(0, len(keys), 500):
        chunk = keys[i:i + 500]
        (
            db.query(model)
            .filter(column.in_(chunk), model.is_current == 1)
            .update({"is_current": 0}, synchronize_session=False)
        )


def _insert_issues(db: Session, batch_id: int, result: P.ParseResult) -> None:
    rows = [
        {
            "batch_id":      batch_id,
            "source_row_no": i.source_row_no,
            "field_name":    i.field_name[:50],
            "raw_value":     i.raw_value[:500],
            "error_code":    i.error_code[:30],
            "error_message": i.error_message[:500],
            "severity":      i.severity,
        }
        for i in result.issues
    ]
    for i in range(0, len(rows), BULK_CHUNK):
        db.bulk_insert_mappings(OperaImportError, rows[i:i + BULK_CHUNK])


# ══════════════════════════════════════════════════════════════════════════════
# 匯入狀態（規格書 §9.1 get_import_status）
# ══════════════════════════════════════════════════════════════════════════════

def get_import_status(db: Session) -> dict:
    """資料庫涵蓋範圍與各來源最新日，供 Dashboard 與匯入頁顯示。"""
    stay_range = db.execute(text(
        "SELECT MIN(departure_date), MAX(departure_date), COUNT(*) "
        "FROM opera_departure_stay WHERE is_current = 1"
    )).first() or (None, None, 0)

    hist_range = db.execute(text(
        "SELECT MIN(business_date), MAX(business_date), COUNT(*) "
        "FROM opera_revenue_daily WHERE is_current = 1 AND record_type = :rt"
    ), {"rt": RECORD_TYPE_HISTORY}).first() or (None, None, 0)

    fc_range = db.execute(text(
        "SELECT MIN(business_date), MAX(business_date), COUNT(*) "
        "FROM opera_revenue_daily WHERE is_current = 1 AND record_type <> :rt"
    ), {"rt": RECORD_TYPE_HISTORY}).first() or (None, None, 0)

    last_batch = (
        db.query(OperaImportBatch)
        .filter(OperaImportBatch.status == STATUS_COMMITTED)
        .order_by(OperaImportBatch.id.desc())
        .first()
    )

    # 每年 × 來源的涵蓋天數（供 §11.9 C14 圖表與「缺哪一年」提示）
    coverage_rows = db.execute(text(
        "SELECT substr(business_date, 1, 4) AS y, record_type, COUNT(*) AS days "
        "FROM opera_revenue_daily WHERE is_current = 1 "
        "GROUP BY y, record_type ORDER BY y"
    )).all()
    coverage: dict[str, dict[str, int]] = {}
    for year, rtype, days in coverage_rows:
        coverage.setdefault(year, {})[rtype] = int(days)

    stay_years = db.execute(text(
        "SELECT substr(departure_date, 1, 4) AS y, COUNT(*) FROM opera_departure_stay "
        "WHERE is_current = 1 GROUP BY y ORDER BY y"
    )).all()
    for year, cnt in stay_years:
        coverage.setdefault(year, {})["Departure"] = int(cnt)

    # 有 Departure 但沒有 History 的年度 → 提醒補匯入（規格書 §17.2 D6）
    missing_history_years = sorted(
        y for y, m in coverage.items()
        if m.get("Departure") and not m.get(RECORD_TYPE_HISTORY)
    )

    return {
        "departure": {
            "start": stay_range[0] or "", "end": stay_range[1] or "", "rows": int(stay_range[2] or 0),
        },
        "history": {
            "start": hist_range[0] or "", "end": hist_range[1] or "", "rows": int(hist_range[2] or 0),
        },
        "forecast": {
            "start": fc_range[0] or "", "end": fc_range[1] or "", "rows": int(fc_range[2] or 0),
        },
        "coverage_by_year":      coverage,
        "missing_history_years": missing_history_years,
        "last_batch":            last_batch.to_dict() if last_batch else None,
        "has_data":              bool(stay_range[2] or hist_range[2]),
    }
