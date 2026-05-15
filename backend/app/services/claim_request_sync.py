"""
核准請款單同步服務：Ragic → SQLite

架構：Master + Detail 雙層同步
  Step 1（每 15 分鐘）：清單 API × 8 部門 → approved_claim_requests（主單）
  Step 2（每 45 分鐘）：subtable 解析 or 內頁 API → approved_claim_request_items（品項）
                        + detail_synced=True

【欄位映射策略】
  - 以中文欄位標籤為候選清單，容錯各部門命名差異
  - 付款種類（payment_type）決定匯款欄位是否必填
  - 部門請款編號（department_request_no）各部門有不同標籤

【流程模板差異】
  零用金型：執董室、客服部、管理部（領款簽名欄）
  比價型：  營業部、行銷部、設計部（三家廠商比價欄）
  匯款型：  財務部、資訊部（銀行帳號必填）
"""
import json
import logging
import re
from datetime import date, datetime
from typing import Any

from app.core.database import SessionLocal
from app.core.time import twnow
from app.models.claim_request import (
    ApprovedClaimRequest,
    ApprovedClaimRequestItem,
    CLAIM_DEPT_DISPLAY_MAP,
    CLAIM_DEPT_SHEETS,
)
from app.services.ragic_adapter import RagicAdapter

logger = logging.getLogger(__name__)

# ── Ragic 連線設定 ─────────────────────────────────────────────────────────────
RAGIC_SERVER  = "ap12.ragic.com"
RAGIC_ACCOUNT = "soutlet001"

# ── 同步調速設定 ───────────────────────────────────────────────────────────────
DETAIL_CALL_DELAY_SEC = 0.1
BATCH_SIZE            = 50
BATCH_SLEEP_SEC       = 3.0

# ── 欄位候選清單（按優先序取第一個有值的）────────────────────────────────────
LIST_FIELD_CANDIDATES: dict[str, list[str]] = {
    # 請款單號（系統唯一編號）
    # 命名規律：各部門前綴 + "請編號"
    #   執董室 → 職請編號 / 執董請編號
    #   行銷部 → 行請編號 / 樂行購編號
    #   管理部 → 管請編號
    #   財務部 → 財請編號
    #   客服部 → 客請編號
    #   營業部 → 營請編號
    #   資訊部 → 資請編號
    #   設計部 → 設請編號
    "request_no":         [
        "編號", "請款單號", "單號",
        # 各部門短標籤
        "管請編號", "財請編號", "客請編號", "營請編號",
        "資請編號", "設請編號", "行請編號",
        # 執董室（Ragic 實際欄位標籤為「職請編號」）
        "職請編號", "執董請編號",
        # 行銷部（帶「樂」前綴舊值保留相容）
        "樂行購編號",
    ],
    # 部門請款編號（各部門不同標籤）
    "department_request_no": [
        "部門請款編號",
        # 各部門短標籤
        "管請編號", "財請編號", "客請編號", "營請編號",
        "資請編號", "設請編號", "行請編號",
        # 執董室
        "職請編號", "執董請編號",
        # 行銷部
        "樂行購編號",
    ],
    "department_raw":     ["部門", "申請部門", "請款部門"],
    "account_subject":    ["會科", "費用科目", "科目"],
    "applicant":          ["申請人", "請款人"],
    "purchase_no":        ["採購編號", "請購編號"],
    "payment_no":         ["付款編號"],
    "voucher_no":         ["傳票號碼", "傳票"],
    "payment_type":       ["付款種類", "付款方式"],
    "purpose_description":["事由", "說明", "事由/說明", "摘要", "主旨"],
    "subtotal":           ["小計", "未稅小計"],
    "tax":                ["營業稅", "稅額", "稅金", "稅"],
    "total":              ["總計", "含稅總計", "合計"],
    "payable_amount":     ["應付(繳)款", "應付款", "應繳款", "付款金額"],
    "payee":              ["受款者", "付款對象", "受款人"],
    "bank_name":          ["受款銀行", "銀行"],
    "bank_branch":        ["受款銀行分行", "分行"],
    "bank_account":       ["匯款帳號", "帳號", "銀行帳號"],
    "payment_date":       ["付款日期", "預計付款日"],
    "status":             ["簽核狀態", "狀態"],
    "last_updated":       ["最後更新日期", "更新日期"],
}

DETAIL_FIELD_CANDIDATES: dict[str, list[str]] = {
    "apply_date":         ["申請日期", "填單日期", "日期"],
    "approved_date":      ["核准日期", "簽核完成日期", "最終核准日期", "完成日期"],
    "payment_type":       ["付款種類", "付款方式"],
    "payee":              ["受款者", "付款對象"],
    "bank_name":          ["受款銀行", "銀行"],
    "bank_branch":        ["受款銀行分行", "分行"],
    "bank_account":       ["匯款帳號", "帳號"],
    "payment_date":       ["付款日期"],
    "subtotal":           ["小計"],
    "tax":                ["營業稅", "稅額"],
    "total":              ["總計", "含稅總計"],
    "payable_amount":     ["應付(繳)款", "應付款"],
    "purpose_description":["事由", "說明", "事由/說明"],
    "voucher_no":         ["傳票號碼"],
}

ITEM_FIELD_CANDIDATES: dict[str, list[str]] = {
    "seq":                    ["項次", "序號"],
    "item_name":              ["產品名稱", "品名", "品項名稱", "名稱", "項目"],
    "quantity":               ["數量"],
    "unit":                   ["單位"],
    "item_note":              ["品項備註", "備註"],
    "proposed_vendor_amount": ["擬定廠商金額", "廠商金額", "金額", "請款金額"],
    "invoice_no":             ["發票號碼", "發票"],
    "receipt_no":             ["憑證號碼", "收據號碼", "憑單號碼"],
}


# ── 請款單號 regex pattern ────────────────────────────────────────────────────
# 格式：樂 + 任意中文/英文 + 請 + 8位日期 + 3位流水號
# 例：樂執請20260325002、樂資請20260414001、樂行購20260301001
_REQUEST_NO_RE = re.compile(r"^樂.+請\d{8,}")


# ── 工具函式 ──────────────────────────────────────────────────────────────────

def _pick(data: dict, candidates: list[str], default="") -> Any:
    """從 data 中按候選清單優先序取第一個有值的欄位。
    若候選清單全部找不到，使用 regex fallback 掃描全部欄位，
    找出值符合「樂X請YYYYMMXXX」格式的欄位（適用 request_no）。
    """
    for key in candidates:
        val = data.get(key)
        if val is not None and str(val).strip():
            return val
    return default


def _pick_request_no(data: dict, candidates: list[str]) -> str:
    """專用於 request_no 的取值函式：候選清單 → regex fallback。
    fallback 會掃描 data 所有欄位，取第一個值符合「樂X請YYYYMMXXX」格式的值。
    """
    # Step 1：候選清單
    for key in candidates:
        val = data.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()

    # Step 2：regex fallback — 掃全部欄位找單號格式
    for key, val in data.items():
        if isinstance(val, str) and _REQUEST_NO_RE.match(val.strip()):
            logger.debug("request_no regex fallback: key=%r val=%r", key, val)
            return val.strip()

    return ""


def _to_int(val: Any) -> int | None:
    if val is None or str(val).strip() in ("", "-", "0"):
        return None
    try:
        cleaned = re.sub(r"[$,\s]", "", str(val))
        return int(float(cleaned)) if cleaned else None
    except (ValueError, TypeError):
        return None


def _to_date(val: Any) -> date | None:
    if not val or str(val).strip() in ("", "0", "0/0/0"):
        return None
    s = str(val).strip()[:10].replace("/", "-")
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _to_bool(val: Any) -> bool | None:
    if val is None:
        return None
    s = str(val).strip().lower()
    return s in ("✓", "v", "y", "yes", "1", "true", "是")


def _dept_display(raw: str) -> str:
    return CLAIM_DEPT_DISPLAY_MAP.get(str(raw).strip(), str(raw).strip())


def _find_subtable_from_list_raw(raw: dict) -> list[dict]:
    """從清單 API raw JSON 找出 _subtable_* 品項資料。"""
    import ast
    rows = []
    for k, v in raw.items():
        if not k.startswith("_subtable_"):
            continue
        if isinstance(v, str):
            try:
                v = ast.literal_eval(v)
            except Exception:
                continue
        if not isinstance(v, dict):
            continue
        for row_key, row_data in v.items():
            if isinstance(row_data, dict) and not str(row_key).startswith("_"):
                rows.append(row_data)

    if not rows:
        return rows

    def _sort_key(r: dict) -> int:
        raw_seq = _pick(r, ["項次", "序號"], "0") or "0"
        try:
            return int(str(raw_seq))
        except (ValueError, TypeError):
            return 0

    rows.sort(key=_sort_key)
    return rows


def _find_subtable_from_detail(raw: dict) -> list[dict]:
    """從內頁 API raw JSON 中找出品項子表格資料。"""
    rows = []
    for k, v in raw.items():
        if not isinstance(v, dict):
            continue
        if not k.lstrip("-").isdigit():
            continue
        has_item_field = any(
            cand in v
            for cands in ITEM_FIELD_CANDIDATES.values()
            for cand in cands
        )
        if has_item_field:
            rows.append(v)
    rows.sort(key=lambda r: int(str(_pick(r, ["項次", "序號"], "0") or "0")))
    return rows


def _parse_item_row(row_data: dict, claim_id: int, seq_override: int | None = None) -> dict:
    # seq 固定使用 seq_override（呼叫端傳入的迴圈 idx+1 或 idx），不採用 Ragic「項次」欄位。
    # 原因與 purchase_request_sync 相同：合併多個 _subtable_* 後「項次」會重複，
    # 用迴圈位置作為 seq 才能確保同一筆主單內唯一。
    seq = seq_override if seq_override is not None else 0

    return {
        "claim_id":               claim_id,
        "seq":                    seq,
        "item_name":              str(_pick(row_data, ITEM_FIELD_CANDIDATES["item_name"], "")).strip() or None,
        "quantity":               str(_pick(row_data, ITEM_FIELD_CANDIDATES["quantity"], "")).strip() or None,
        "unit":                   str(_pick(row_data, ITEM_FIELD_CANDIDATES["unit"], "")).strip() or None,
        "item_note":              str(_pick(row_data, ITEM_FIELD_CANDIDATES["item_note"], "")).strip() or None,
        "proposed_vendor_amount": _to_int(_pick(row_data, ITEM_FIELD_CANDIDATES["proposed_vendor_amount"])),
        "invoice_no":             str(_pick(row_data, ITEM_FIELD_CANDIDATES["invoice_no"], "")).strip() or None,
        "receipt_no":             str(_pick(row_data, ITEM_FIELD_CANDIDATES["receipt_no"], "")).strip() or None,
    }


# ── 清單記錄解析 ──────────────────────────────────────────────────────────────

def _parse_list_record(
    record_id: str,
    data: dict,
    sheet_path: str,
    dept_config: dict,
) -> dict:
    """將清單 API 單筆記錄解析為 approved_claim_requests 欄位 dict。"""
    raw_dept   = str(_pick(data, LIST_FIELD_CANDIDATES["department_raw"], "")).strip()
    last_updated_str = _pick(data, LIST_FIELD_CANDIDATES["last_updated"])
    last_updated_dt  = None

    if last_updated_str:
        s = str(last_updated_str).replace("/", "-").strip()
        for fmt, length in [
            ("%Y-%m-%d %H:%M:%S", 19),
            ("%Y-%m-%d %H:%M",    16),
            ("%Y-%m-%d",          10),
        ]:
            try:
                last_updated_dt = datetime.strptime(s[:length], fmt)
                break
            except ValueError:
                continue

    if last_updated_dt is None:
        ts = data.get("_dataTimestamp")
        if ts:
            try:
                last_updated_dt = datetime.fromtimestamp(int(ts) / 1000)
            except (ValueError, TypeError, OSError):
                pass

    # 簽核狀態
    status_raw = str(_pick(data, LIST_FIELD_CANDIDATES["status"], "N")).strip().upper()
    status     = status_raw if status_raw in ("F", "N", "REJ") else "N"

    # 核准日期（三層候選，不 fallback 到 last_updated_dt 以避免被同步時間污染）
    # 1. Ragic 工作流「日期N」欄位（數位簽核每步驟的時間戳記）
    # 2. 明確命名的核准/付款日期欄位
    # 3. 最終備援：申請日期（比最後更新更接近實際審核時間）
    approved_dt = None
    if status == "F":
        date_vals = []
        # 第一層：日期 / 日期1 / 日期2 … 工作流簽核時間戳
        for k, v in data.items():
            if re.match(r"^日期\d*$", k) and v:
                d = _to_date(v)
                if d:
                    date_vals.append(d)
        if date_vals:
            approved_dt = max(date_vals)
        else:
            # 第二層：明確命名的核准/付款日期候選
            for cand in ["核准日期", "簽核完成日期", "最終核准日期", "完成日期", "付款日期", "預計付款日"]:
                val = data.get(cand)
                if val:
                    d = _to_date(val)
                    if d:
                        approved_dt = d
                        break
        if approved_dt is None:
            # 第三層：申請日期（永遠存在，比 last_updated_dt 更穩定）
            apply_raw = _pick(data, ["申請日期", "填單日期"])
            if apply_raw:
                approved_dt = _to_date(apply_raw)

    dept_display = _dept_display(raw_dept or dept_config.get("ragic_dept", ""))
    if not dept_display:
        dept_display = dept_config.get("display_name", "")

    return {
        "company":                "樂群",
        "department_raw":         raw_dept or dept_config.get("ragic_dept", ""),
        "department_display":     dept_display,
        "ragic_sheet_path":       sheet_path,
        "ragic_record_id":        str(record_id),
        "request_no":             _pick_request_no(data, LIST_FIELD_CANDIDATES["request_no"]) or None,
        "department_request_no":  str(_pick(data, LIST_FIELD_CANDIDATES["department_request_no"], "")).strip() or None,
        "purchase_no":            str(_pick(data, LIST_FIELD_CANDIDATES["purchase_no"], "")).strip() or None,
        "payment_no":             str(_pick(data, LIST_FIELD_CANDIDATES["payment_no"], "")).strip() or None,
        "voucher_no":             str(_pick(data, LIST_FIELD_CANDIDATES["voucher_no"], "")).strip() or None,
        "account_subject":        str(_pick(data, LIST_FIELD_CANDIDATES["account_subject"], "")).strip() or None,
        "apply_date":             _to_date(_pick(data, ["申請日期"])),
        "approved_date":          approved_dt,
        "applicant":              str(_pick(data, LIST_FIELD_CANDIDATES["applicant"], "")).strip() or None,
        "payment_type":           str(_pick(data, LIST_FIELD_CANDIDATES["payment_type"], "")).strip() or None,
        "purpose_description":    str(_pick(data, LIST_FIELD_CANDIDATES["purpose_description"], "")).strip()[:500] or None,
        "subtotal":               _to_int(_pick(data, LIST_FIELD_CANDIDATES["subtotal"])),
        "tax":                    _to_int(_pick(data, LIST_FIELD_CANDIDATES["tax"])),
        "total":                  _to_int(_pick(data, LIST_FIELD_CANDIDATES["total"])),
        "payable_amount":         _to_int(_pick(data, LIST_FIELD_CANDIDATES["payable_amount"])),
        "payee":                  str(_pick(data, LIST_FIELD_CANDIDATES["payee"], "")).strip() or None,
        "bank_name":              str(_pick(data, LIST_FIELD_CANDIDATES["bank_name"], "")).strip() or None,
        "bank_branch":            str(_pick(data, LIST_FIELD_CANDIDATES["bank_branch"], "")).strip() or None,
        "bank_account":           str(_pick(data, LIST_FIELD_CANDIDATES["bank_account"], "")).strip() or None,
        "payment_date":           _to_date(_pick(data, LIST_FIELD_CANDIDATES["payment_date"])),
        "status":                 status,
        "last_updated_at":        last_updated_dt,
        "raw_data_json":          json.dumps(data, ensure_ascii=False, default=str),
        "detail_synced":          False,
    }


# ── 部門清單同步 ──────────────────────────────────────────────────────────────

async def _sync_list_for_dept(
    dept_config: dict,
    db,
    full_resync: bool = False,
) -> dict:
    """同步單一部門的請款單清單（async，對應 purchase_request_sync 的做法）。"""
    sheet_path = dept_config["list_path"]
    display    = dept_config["display_name"]
    fetched    = 0
    upserted   = 0
    errors     = []

    # 每部門建立專屬 adapter（sheet_path 嵌入 URL）
    adapter = RagicAdapter(
        sheet_path=sheet_path,
        server_url=RAGIC_SERVER,
        account=RAGIC_ACCOUNT,
    )

    try:
        records = await adapter.fetch_all()
    except Exception as exc:
        logger.error("[ClaimSync][List] %s 清單 API 失敗：%s", display, exc)
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    now = twnow()

    for record_id, data in records.items():
        fetched += 1
        try:
            with db.begin_nested():  # SAVEPOINT：單筆失敗只 rollback 該筆，不影響其他記錄
                fields = _parse_list_record(record_id, data, sheet_path, dept_config)

                existing = (
                    db.query(ApprovedClaimRequest)
                    .filter_by(ragic_sheet_path=sheet_path, ragic_record_id=str(record_id))
                    .first()
                )

                if existing:
                    # 若 last_updated_at 有變，重置 detail_synced 以便重新補全品項
                    new_updated = fields.get("last_updated_at")
                    if new_updated and existing.last_updated_at != new_updated:
                        fields["detail_synced"] = False
                    for k, v in fields.items():
                        setattr(existing, k, v)
                    existing.sync_at = now
                    obj = existing
                else:
                    obj = ApprovedClaimRequest(**fields, sync_at=now)
                    db.add(obj)

                # 需要 flush 確保新增記錄取得 PK
                db.flush()

                # 嘗試從清單 API subtable 提取品項（_subtable_* 欄位）
                if not fields.get("detail_synced", False):
                    subtable_rows = _find_subtable_from_list_raw(data)
                    if subtable_rows:
                        # synchronize_session=False：確保 DELETE 立即反映在 DB
                        db.query(ApprovedClaimRequestItem).filter_by(
                            claim_id=obj.id
                        ).delete(synchronize_session=False)
                        db.flush()  # DELETE 先 flush，再 INSERT，避免 UNIQUE constraint
                        for idx, row in enumerate(subtable_rows, start=1):
                            item_fields = _parse_item_row(row, obj.id, idx)
                            db.add(ApprovedClaimRequestItem(**item_fields))
                        obj.detail_synced = True
                        logger.debug("[ClaimSync][List] record %s 從清單解析到 %d 筆品項",
                                     record_id, len(subtable_rows))

            upserted += 1
        except Exception as exc:
            errors.append(f"{display}[{record_id}]: {exc}")
            logger.warning("[ClaimSync][List] %s[%s] 解析失敗: %s", display, record_id, exc)

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("[ClaimSync][List] %s commit 失敗: %s", display, exc)
        errors.append(f"commit: {exc}")

    return {"fetched": fetched, "upserted": upserted, "errors": errors}


# ── 公開同步入口 ──────────────────────────────────────────────────────────────

async def sync_list_only() -> dict:
    """
    清單同步（每 15 分鐘執行）：
    只更新主單欄位，若 subtable 存在也一併寫入品項。
    """
    db = SessionLocal()
    total = {"fetched": 0, "upserted": 0, "errors": []}
    try:
        for dept in CLAIM_DEPT_SHEETS:
            result = await _sync_list_for_dept(dept, db)
            total["fetched"]  += result["fetched"]
            total["upserted"] += result["upserted"]
            total["errors"]   += result["errors"]
    finally:
        db.close()
    logger.info("[ClaimSync] 清單同步完成：%s", total)
    return total


async def sync_from_ragic(full_resync: bool = False) -> dict:
    """
    完整同步（每 45 分鐘執行）：
    1. 清單同步（主單 + 嘗試 subtable 品項）
    2. 對尚未取得品項的記錄嘗試內頁 API
    """
    import asyncio

    db = SessionLocal()
    total = {"fetched": 0, "upserted": 0, "errors": []}

    # 建立 sheet_path → detail_path 對照表
    sheet_to_detail: dict[str, str] = {
        d["list_path"]: d.get("detail_path", d["list_path"])
        for d in CLAIM_DEPT_SHEETS
    }

    try:
        # Step 1: 清單同步（每部門各自建立 adapter）
        for dept in CLAIM_DEPT_SHEETS:
            result = await _sync_list_for_dept(dept, db, full_resync=full_resync)
            total["upserted"] += result["upserted"]
            total["errors"]   += result["errors"]

        # Step 2: Detail API 補全品項（detail_synced=False 的記錄）
        pending = (
            db.query(ApprovedClaimRequest)
            .filter(ApprovedClaimRequest.detail_synced == False)  # noqa: E712
            .limit(BATCH_SIZE * 5)
            .all()
        )

        now = twnow()
        for i, order in enumerate(pending):
            detail_path = sheet_to_detail.get(order.ragic_sheet_path)
            if not detail_path:
                logger.warning("[ClaimSync][Detail] 找不到 detail_path for %s", order.ragic_sheet_path)
                continue

            detail_adapter = RagicAdapter(
                sheet_path=detail_path,
                server_url=RAGIC_SERVER,
                account=RAGIC_ACCOUNT,
            )

            try:
                detail_raw = await detail_adapter.fetch_one(order.ragic_record_id)
                if not isinstance(detail_raw, dict):
                    await asyncio.sleep(DETAIL_CALL_DELAY_SEC)
                    continue

                # Ragic Detail API 回傳 {record_id: {fields}}，需 unwrap
                rid_str = str(order.ragic_record_id)
                if rid_str in detail_raw and isinstance(detail_raw[rid_str], dict):
                    record_data = detail_raw[rid_str]
                else:
                    numeric_vals = [v for k, v in detail_raw.items()
                                    if k.lstrip("-").isdigit() and isinstance(v, dict)]
                    record_data = numeric_vals[0] if numeric_vals else detail_raw

                with db.begin_nested():  # SAVEPOINT：單筆失敗不汙染外層 transaction
                    for field, candidates in DETAIL_FIELD_CANDIDATES.items():
                        val = _pick(record_data, candidates)
                        if val:
                            if field in ("apply_date", "approved_date", "payment_date"):
                                val = _to_date(val)
                            elif field in ("subtotal", "tax", "total", "payable_amount"):
                                val = _to_int(val)
                            else:
                                val = str(val).strip()[:200] if val else None
                            if val is not None:
                                setattr(order, field, val)

                    item_rows = _find_subtable_from_detail(record_data)
                    if item_rows:
                        db.query(ApprovedClaimRequestItem).filter_by(
                            claim_id=order.id
                        ).delete(synchronize_session=False)
                        db.flush()
                        for idx, row in enumerate(item_rows, start=1):
                            item_fields = _parse_item_row(row, order.id, idx)
                            db.add(ApprovedClaimRequestItem(**item_fields))

                    order.detail_synced = True
                    order.sync_at       = now

                if (i + 1) % 10 == 0:
                    db.commit()

            except Exception as exc:
                logger.warning("[ClaimSync][Detail] record %s fetch/parse 失敗：%s",
                               order.ragic_record_id, exc)
                total["errors"].append(f"detail {order.ragic_record_id}: {exc}")

            await asyncio.sleep(DETAIL_CALL_DELAY_SEC)

        db.commit()
    except Exception as exc:
        db.rollback()
        total["errors"].append(str(exc))
        logger.error("[ClaimSync] 完整同步失敗: %s", exc, exc_info=True)
    finally:
        db.close()

    logger.info("[ClaimSync] 完整同步完成：%s", total)
    return total
