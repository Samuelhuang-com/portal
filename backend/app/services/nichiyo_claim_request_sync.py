"""
日曜核准請款單同步服務：Ragic → SQLite

架構：Master + Detail 雙層同步
  Step 1（每 15 分鐘）：清單 API × 8 部門 → nichiyo_claim_requests（主單）
  Step 2（每 45 分鐘）：subtable 解析 or 內頁 API → nichiyo_claim_request_items（品項）
                        + detail_synced=True

【SPEC B 系列防護（RAGIC_REPORT_MODULE_SPEC.md Section 10）】
  B02：sorted() 加 key=lambda x: x or "" 防 None crash
  B04：func.sum() 比較前加 isnot(None) 過濾
  B05/B06：_pick_claim_no() 含 regex fallback
  B07：approved_date 三層 fallback，絕不用 last_updated_dt
  B08：Excel 匯出用 RFC 5987 filename*= 編碼（在 router 層處理）
"""
import asyncio
import json
import logging
import re
from datetime import date, datetime
from typing import Any

from app.core.database import SessionLocal
from app.core.time import twnow
from app.models.nichiyo_claim_request import (
    NichiyoClaimRequest,
    NichiyoClaimRequestItem,
    NICHIYO_CLAIM_DEPT_DISPLAY_MAP,
    NICHIYO_CLAIM_DEPT_SHEETS,
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

# ── 請款單號 regex（B05/B06：fallback 掃全欄位值）────────────────────────────
# 日曜請款單號格式範例：日執請2026032500X、日行請2026050100X 等
_CLAIM_NO_RE = re.compile(r"^[日樂].+請\d{8,}")

# ── 欄位候選清單 ──────────────────────────────────────────────────────────────
LIST_FIELD_CANDIDATES: dict[str, list[str]] = {
    "claim_no":          [
        "編號", "請款單號", "單號",
        "工請編號", "專請編號", "財請編號",
        "管請編號", "執董請編號", "資請編號",
        "客請編號", "行請編號", "設請編號", "營請編號",
        "日請編號", "執請編號",
    ],
    "department_raw":    ["部門", "申請部門", "請款部門"],
    "account_category":  ["會科", "費用科目", "金科"],
    "applicant":         ["申請人", "請款人", "填表人"],
    "purpose_description": ["事由", "說明", "用途說明", "摘要", "主旨", "請款說明"],
    "payment_type":      ["付款種類", "付款方式", "匯款種類"],
    "subtotal":          ["小計", "未稅小計", "金額小計"],
    "tax":               ["稅額", "營業稅", "稅金"],
    "total":             ["合計", "含稅合計", "總計", "含稅總額"],
    "payable_amount":    ["應付款", "應付金額", "應繳金額", "付款金額"],
    "payee":             ["受款者", "受款人", "收款人", "廠商名稱"],
    "status":            ["簽核狀態", "狀態"],
    "last_updated":      ["最後更新日期", "更新日期", "最後修改日期"],
}

DETAIL_FIELD_CANDIDATES: dict[str, list[str]] = {
    "request_date":      ["申請日期", "填單日期", "日期"],
    "approved_date":     ["核准日期", "簽核完成日期", "最終核准日期", "完成日期"],
    "subtotal":          ["小計", "未稅小計"],
    "tax":               ["稅額", "營業稅"],
    "total":             ["合計", "含稅合計", "總計"],
    "payable_amount":    ["應付款", "應付金額", "付款金額"],
    "payee":             ["受款者", "受款人", "收款人"],
    "payment_date":      ["付款日期", "預計付款日"],
    "purpose_description": ["事由", "說明", "用途說明"],
}

ITEM_FIELD_CANDIDATES: dict[str, list[str]] = {
    "seq":          ["項次", "序號"],
    "product_name": ["品名", "品項名稱", "名稱", "摘要", "說明"],
    "qty":          ["數量"],
    "unit":         ["單位"],
    "unit_price":   ["單價"],
    "amount":       ["金額", "小計", "品項金額"],
    "item_remark":  ["備註", "品項備註"],
}


# ── 工具函式 ──────────────────────────────────────────────────────────────────

def _pick(data: dict, candidates: list[str], default="") -> Any:
    for key in candidates:
        val = data.get(key)
        if val is not None and str(val).strip():
            return val
    return default


def _pick_claim_no(data: dict, candidates: list[str]) -> str:
    """B05/B06：候選清單 → regex fallback 掃全欄位值"""
    for key in candidates:
        val = data.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    for key, val in data.items():
        if isinstance(val, str) and _CLAIM_NO_RE.match(val.strip()):
            logger.debug("claim_no regex fallback: key=%r val=%r", key, val)
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


def _dept_display(raw: str) -> str:
    return NICHIYO_CLAIM_DEPT_DISPLAY_MAP.get(str(raw).strip(), str(raw).strip())


def _parse_approved_date(data: dict, status: str) -> date | None:
    """B07：三層 fallback，絕不用 last_updated_dt 作為 approved_date"""
    if status != "F":
        return None
    # 層 1：工作流日期欄位
    sign_dates = []
    for key, val in data.items():
        if key.startswith("日期") and val and str(val).strip():
            d = _to_date(val)
            if d:
                sign_dates.append(d)
    if sign_dates:
        return max(sign_dates)
    # 層 2：語意明確的核准日期欄位
    for key in ["核准日期", "簽核完成日期", "最終核准日期", "完成日期", "付款日期"]:
        if d := _to_date(data.get(key)):
            return d
    # 層 3：申請日期（最後手段，NOT last_updated_dt）
    for key in ["申請日期", "填單日期"]:
        if d := _to_date(data.get(key)):
            return d
    return None


def _find_subtable(raw: dict) -> list[dict]:
    rows = []
    for k, v in raw.items():
        if not isinstance(v, dict) or not k.lstrip("-").isdigit():
            continue
        if any(cand in v for cands in ITEM_FIELD_CANDIDATES.values() for cand in cands):
            rows.append(v)
    rows.sort(key=lambda r: int(str(_pick(r, ["項次", "序號"], "0") or "0")))
    return rows


def _find_subtable_from_list_raw(raw: dict) -> list[dict]:
    """從清單 API raw JSON 的 _subtable_* 欄位解析品項"""
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


# ── 清單記錄解析 ──────────────────────────────────────────────────────────────

def _parse_list_record(record_id: str, data: dict, sheet_path: str, dept_config: dict) -> dict:
    raw_dept = str(_pick(data, LIST_FIELD_CANDIDATES["department_raw"], "")).strip()

    # last_updated_at
    last_updated_str = _pick(data, LIST_FIELD_CANDIDATES["last_updated"])
    last_updated_dt  = None
    if last_updated_str:
        s = str(last_updated_str).replace("/", "-").strip()
        for fmt, length in [("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d %H:%M", 16), ("%Y-%m-%d", 10)]:
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
            except Exception:
                pass

    status_raw = str(_pick(data, LIST_FIELD_CANDIDATES["status"], "N")).strip().upper()
    status     = status_raw if status_raw in ("F", "N", "REJ") else "N"

    return {
        "company":             "日曜",
        "department_raw":      raw_dept or dept_config["ragic_dept"],
        "department_display":  _dept_display(raw_dept or dept_config["ragic_dept"]),
        "ragic_sheet_path":    sheet_path,
        "ragic_record_id":     str(record_id),
        "claim_no":            _pick_claim_no(data, LIST_FIELD_CANDIDATES["claim_no"]),
        "account_category":    str(_pick(data, LIST_FIELD_CANDIDATES["account_category"], "")).strip() or None,
        "applicant":           str(_pick(data, LIST_FIELD_CANDIDATES["applicant"], "")).strip() or None,
        "purpose_description": str(_pick(data, LIST_FIELD_CANDIDATES["purpose_description"], "")).strip()[:500] or None,
        "payment_type":        str(_pick(data, LIST_FIELD_CANDIDATES["payment_type"], "")).strip() or None,
        "subtotal":            _to_int(_pick(data, LIST_FIELD_CANDIDATES["subtotal"])),
        "tax":                 _to_int(_pick(data, LIST_FIELD_CANDIDATES["tax"])),
        "total":               _to_int(_pick(data, LIST_FIELD_CANDIDATES["total"])),
        "payable_amount":      _to_int(_pick(data, LIST_FIELD_CANDIDATES["payable_amount"])),
        "payee":               str(_pick(data, LIST_FIELD_CANDIDATES["payee"], "")).strip() or None,
        "status":              status,
        "approved_date":       _parse_approved_date(data, status),
        "last_updated_at":     last_updated_dt,
        "raw_data_json":       json.dumps(data, ensure_ascii=False),
        "detail_synced":       False,
    }


# ── Step 1：清單同步 ──────────────────────────────────────────────────────────

async def _sync_list_for_dept(dept_config: dict, db) -> dict:
    sheet_path = dept_config["list_path"]
    adapter = RagicAdapter(sheet_path=sheet_path, server_url=RAGIC_SERVER, account=RAGIC_ACCOUNT)

    fetched = upserted = 0
    errors  = []

    try:
        records = await adapter.fetch_all()
    except Exception as exc:
        logger.error("[NichiyoClaimSync][List] %s 失敗：%s", dept_config["display_name"], exc)
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    now = twnow()

    for record_id, data in records.items():
        fetched += 1
        try:
            with db.begin_nested():
                fields = _parse_list_record(record_id, data, sheet_path, dept_config)

                existing = (
                    db.query(NichiyoClaimRequest)
                    .filter_by(ragic_sheet_path=sheet_path, ragic_record_id=str(record_id))
                    .first()
                )

                if existing:
                    new_updated = fields.get("last_updated_at")
                    if new_updated and existing.last_updated_at != new_updated:
                        fields["detail_synced"] = False
                    for k, v in fields.items():
                        setattr(existing, k, v)
                    existing.sync_at    = now
                    existing.updated_at = now
                    order_obj = existing
                else:
                    order_obj = NichiyoClaimRequest(**fields, sync_at=now, created_at=now, updated_at=now)
                    db.add(order_obj)

                # 嘗試從清單 _subtable_* 直接解析品項
                if not fields.get("detail_synced", False):
                    item_rows = _find_subtable_from_list_raw(data)
                    if item_rows:
                        db.flush()
                        db.query(NichiyoClaimRequestItem).filter_by(order_id=order_obj.id).delete(synchronize_session=False)
                        for row in item_rows:
                            item = NichiyoClaimRequestItem(
                                order_id     = order_obj.id,
                                seq          = int(str(_pick(row, ["項次", "序號"], "0") or "0")),
                                product_name = str(_pick(row, ITEM_FIELD_CANDIDATES["product_name"], "")).strip() or None,
                                qty          = str(_pick(row, ITEM_FIELD_CANDIDATES["qty"], "")).strip() or None,
                                unit         = str(_pick(row, ITEM_FIELD_CANDIDATES["unit"], "")).strip() or None,
                                unit_price   = _to_int(_pick(row, ITEM_FIELD_CANDIDATES["unit_price"])),
                                amount       = _to_int(_pick(row, ITEM_FIELD_CANDIDATES["amount"])),
                                item_remark  = str(_pick(row, ITEM_FIELD_CANDIDATES["item_remark"], "")).strip() or None,
                                sync_at      = now,
                            )
                            db.add(item)
                        order_obj.detail_synced = True

                upserted += 1
        except Exception as exc:
            logger.error("[NichiyoClaimSync][List] id=%s 失敗：%s", record_id, exc, exc_info=True)
            errors.append(str(exc))

    db.commit()
    return {"fetched": fetched, "upserted": upserted, "errors": errors}


# ── Step 2：Detail 品項同步 ───────────────────────────────────────────────────

async def _sync_detail_for_order(order: NichiyoClaimRequest, db) -> bool:
    dept_cfg = next(
        (d for d in NICHIYO_CLAIM_DEPT_SHEETS if d["list_path"] == order.ragic_sheet_path),
        None,
    )
    if not dept_cfg:
        return False

    detail_path = dept_cfg["detail_path"]
    adapter = RagicAdapter(
        sheet_path=f"{detail_path}/{order.ragic_record_id}",
        server_url=RAGIC_SERVER,
        account=RAGIC_ACCOUNT,
    )

    try:
        records = await adapter.fetch_all()
    except Exception as exc:
        logger.error("[NichiyoClaimSync][Detail] order_id=%s 失敗：%s", order.id, exc)
        return False

    if not records:
        return False

    data = next(iter(records.values()))
    now  = twnow()

    # 補入主單欄位
    for field, candidates in DETAIL_FIELD_CANDIDATES.items():
        val = _pick(data, candidates)
        if not val:
            continue
        if field in ("subtotal", "tax", "total", "payable_amount"):
            setattr(order, field, _to_int(val))
        elif field in ("approved_date", "request_date", "payment_date"):
            setattr(order, field, _to_date(val))
        elif field in ("purpose_description", "payee"):
            existing = getattr(order, field)
            if not existing:
                setattr(order, field, str(val).strip()[:500] if field == "purpose_description" else str(val).strip())

    # 品項子表格
    item_rows = _find_subtable(data)
    if item_rows:
        db.query(NichiyoClaimRequestItem).filter_by(order_id=order.id).delete(synchronize_session=False)
        for row in item_rows:
            item = NichiyoClaimRequestItem(
                order_id     = order.id,
                seq          = int(str(_pick(row, ["項次", "序號"], "0") or "0")),
                product_name = str(_pick(row, ITEM_FIELD_CANDIDATES["product_name"], "")).strip() or None,
                qty          = str(_pick(row, ITEM_FIELD_CANDIDATES["qty"], "")).strip() or None,
                unit         = str(_pick(row, ITEM_FIELD_CANDIDATES["unit"], "")).strip() or None,
                unit_price   = _to_int(_pick(row, ITEM_FIELD_CANDIDATES["unit_price"])),
                amount       = _to_int(_pick(row, ITEM_FIELD_CANDIDATES["amount"])),
                item_remark  = str(_pick(row, ITEM_FIELD_CANDIDATES["item_remark"], "")).strip() or None,
                sync_at      = now,
            )
            db.add(item)

    order.detail_synced = True
    order.sync_at       = now
    order.updated_at    = now
    return True


# ── 公開 Sync 入口 ────────────────────────────────────────────────────────────

async def sync_list_only() -> dict:
    """清單同步（每 15 分鐘，APScheduler 呼叫）"""
    db = SessionLocal()
    results = {"total_fetched": 0, "total_upserted": 0, "errors": [], "departments": []}
    try:
        for dept in NICHIYO_CLAIM_DEPT_SHEETS:
            r = await _sync_list_for_dept(dept, db)
            results["total_fetched"]   += r["fetched"]
            results["total_upserted"]  += r["upserted"]
            results["errors"]          += r["errors"]
            results["departments"].append({"dept": dept["display_name"], **r})
            await asyncio.sleep(0.5)
    finally:
        db.close()
    logger.info("[NichiyoClaimSync] sync_list_only 完成：%s", results)
    return results


async def sync_detail_batch() -> dict:
    """Detail 品項批次同步（每 45 分鐘，APScheduler 呼叫）"""
    db = SessionLocal()
    synced = failed = 0
    try:
        pending = (
            db.query(NichiyoClaimRequest)
            .filter(
                NichiyoClaimRequest.company == "日曜",
                NichiyoClaimRequest.status  == "F",
                NichiyoClaimRequest.detail_synced == False,
            )
            .limit(BATCH_SIZE)
            .all()
        )
        for i, order in enumerate(pending):
            ok = await _sync_detail_for_order(order, db)
            if ok:
                synced += 1
            else:
                failed += 1
            if (i + 1) % BATCH_SIZE == 0:
                db.commit()
                await asyncio.sleep(BATCH_SLEEP_SEC)
            else:
                await asyncio.sleep(DETAIL_CALL_DELAY_SEC)
        db.commit()
    finally:
        db.close()
    logger.info("[NichiyoClaimSync] sync_detail_batch 完成：synced=%s failed=%s", synced, failed)
    return {"synced": synced, "failed": failed}


async def sync_all() -> dict:
    """全量同步（清單 + Detail 全部重抓）"""
    db = SessionLocal()
    try:
        # 重設所有 detail_synced 旗標
        db.query(NichiyoClaimRequest).filter(
            NichiyoClaimRequest.company == "日曜"
        ).update({"detail_synced": False})
        db.commit()
    finally:
        db.close()

    list_result   = await sync_list_only()
    detail_result = await sync_detail_batch()
    return {"list": list_result, "detail": detail_result}
