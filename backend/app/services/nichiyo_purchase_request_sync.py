"""
日曜核准請購單同步服務：Ragic → SQLite

架構：Master + Detail 雙層同步
  Step 1（每 15 分鐘）：清單 API × 9 部門 → nichiyo_purchase_requests（主單）
  Step 2（每 45 分鐘）：subtable 解析 or 內頁 API → nichiyo_purchase_request_items（品項）
                        + detail_synced=True

【SPEC B 系列防護（RAGIC_REPORT_MODULE_SPEC.md Section 10）】
  B02：sorted() 加 key=lambda x: x or "" 防 None crash
  B04：func.sum() 比較前加 isnot(None) 過濾
  B05/B06：_pick_purchase_no() 含 regex fallback
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
from app.models.nichiyo_purchase_request import (
    NichiyoPurchaseRequest,
    NichiyoPurchaseRequestItem,
    NICHIYO_DEPT_DISPLAY_MAP,
    NICHIYO_DEPT_SHEETS,
)
from app.services.ragic_adapter import RagicAdapter
from app.services.ragic_sheet_config_service import get_sheet_configs

logger = logging.getLogger(__name__)

# ── Ragic 連線設定 ─────────────────────────────────────────────────────────────
RAGIC_SERVER  = "ap12.ragic.com"
RAGIC_ACCOUNT = "soutlet001"

# ── 同步調速設定 ───────────────────────────────────────────────────────────────
DETAIL_CALL_DELAY_SEC = 0.1
BATCH_SIZE            = 50
BATCH_SLEEP_SEC       = 3.0

# ── 請購單號 regex（B05/B06：fallback 掃全欄位值）────────────────────────────
# 日曜請購單號格式範例：日執購2026032500X、日行購2026050100X 等
# 同時相容樂群格式（樂X購...）
_PURCHASE_NO_RE = re.compile(r"^[日樂].+購\d{8,}")

# ── 欄位候選清單 ──────────────────────────────────────────────────────────────
LIST_FIELD_CANDIDATES: dict[str, list[str]] = {
    "purchase_no":      [
        "編號", "請購單號", "單號",
        "工請編號", "專請編號", "財請編號",
        "採購編號", "日請編號", "執購編號",
    ],
    "department_raw":   ["部門", "申請部門", "請購部門", "簽呈部門"],
    "account_category": ["會科", "金科", "費用科目"],
    "applicant":        ["申請人", "請購人"],
    "description":      ["說明", "請購事由", "摘要", "事由", "用途說明", "主旨"],
    "amount":           ["全案小計", "小計", "金額"],
    "status":           ["簽核狀態", "狀態"],
    "last_updated":     ["最後更新日期", "更新日期", "最後修改日期"],
    "vendor1":          ["廠商(一)", "廠商一", "廠商1", "擬定廠商"],
    "vendor2":          ["廠商(二)", "廠商二", "廠商2"],
    "vendor3":          ["廠商(三)", "廠商三", "廠商3"],
    "amount_tax":       ["稅", "營業稅", "稅額", "稅金"],
    "amount_total":     ["全案總計", "含稅總額", "全案合計"],
    "remark":           ["備註", "補充"],
}

DETAIL_FIELD_CANDIDATES: dict[str, list[str]] = {
    "request_date":  ["申請日期", "填單日期", "日期"],
    "approved_date": ["核准日期", "簽核完成日期", "最終核准日期", "完成日期"],
    "amount_tax":    ["營業稅", "稅額", "稅金"],
    "amount_total":  ["全案總計", "含稅總額", "總計"],
    "vendor1":       ["廠商(一)", "廠商一", "廠商1", "擬定廠商"],
    "vendor2":       ["廠商(二)", "廠商二", "廠商2"],
    "vendor3":       ["廠商(三)", "廠商三", "廠商3"],
    "remark":        ["備註", "補充"],
    "description":   ["說明", "請購事由", "事由", "用途說明", "主旨"],
}

ITEM_FIELD_CANDIDATES: dict[str, list[str]] = {
    "seq":               ["項次", "序號"],
    "product_name":      ["產品名稱", "品名", "品項名稱", "名稱"],
    "qty":               ["數量"],
    "unit":              ["單位"],
    "item_remark":       ["品項備註", "備註"],
    "vendor1_price":     ["廠商(一)金額", "廠商一金額", "廠商1金額"],
    "vendor2_price":     ["廠商(二)金額", "廠商二金額", "廠商2金額"],
    "vendor3_price":     ["廠商(三)金額", "廠商三金額", "廠商3金額"],
    "selected_vendor":   ["擬定廠商", "選定廠商"],
    "selected_unit_price": ["擬定單價"],
    "selected_amount":   ["擬定金額"],
    "is_confirmed":      ["勾選"],
}


# ── 工具函式 ──────────────────────────────────────────────────────────────────

def _pick(data: dict, candidates: list[str], default="") -> Any:
    for key in candidates:
        val = data.get(key)
        if val is not None and str(val).strip():
            return val
    return default


def _pick_purchase_no(data: dict, candidates: list[str]) -> str:
    """B05/B06：候選清單 → regex fallback 掃全欄位值"""
    for key in candidates:
        val = data.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    for key, val in data.items():
        if isinstance(val, str) and _PURCHASE_NO_RE.match(val.strip()):
            logger.debug("purchase_no regex fallback: key=%r val=%r", key, val)
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
    return str(val).strip().lower() in ("✓", "v", "y", "yes", "1", "true", "是")


def _dept_display(raw: str) -> str:
    return NICHIYO_DEPT_DISPLAY_MAP.get(str(raw).strip(), str(raw).strip())


def _parse_approved_date(data: dict, status: str) -> date | None:
    """B07：三層 fallback，絕不用 last_updated_dt 作為 approved_date"""
    if status != "F":
        return None
    # 層 1：工作流日期欄位（最多取到 日期5）
    sign_dates = []
    for key, val in data.items():
        if key.startswith("日期") and val and str(val).strip():
            d = _to_date(val)
            if d:
                sign_dates.append(d)
    if sign_dates:
        return max(sign_dates)
    # 層 2：語意明確的核准日期欄位
    for key in ["核准日期", "簽核完成日期", "最終核准日期", "完成日期"]:
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


def _is_empty_item_row(row: dict) -> bool:
    """判斷 subtable row 是否為全空白列（所有 content 欄位都是 None / 空字串）。"""
    content_keys = (
        list(ITEM_FIELD_CANDIDATES.get("product_name", []))
        + list(ITEM_FIELD_CANDIDATES.get("qty", []))
        + list(ITEM_FIELD_CANDIDATES.get("selected_amount", []))
        + list(ITEM_FIELD_CANDIDATES.get("vendor1_price", []))
    )
    return all(
        not str(row.get(k, "") or "").strip()
        for k in content_keys
        if k in row
    )


def _find_subtable_from_list_raw(raw: dict) -> list[dict]:
    """從清單 API raw JSON 的 _subtable_* 欄位解析品項，過濾全空白列。"""
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
                # ★ 過濾全空白列，避免寫入無意義的空品項
                if not _is_empty_item_row(row_data):
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
        "company":            "日曜",
        "department_raw":     raw_dept or dept_config["ragic_dept"],
        "department_display": _dept_display(raw_dept or dept_config["ragic_dept"]),
        "ragic_sheet_path":   sheet_path,
        "ragic_record_id":    str(record_id),
        "purchase_no":        _pick_purchase_no(data, LIST_FIELD_CANDIDATES["purchase_no"]),
        "account_category":   str(_pick(data, LIST_FIELD_CANDIDATES["account_category"], "")).strip() or None,
        "applicant":          str(_pick(data, LIST_FIELD_CANDIDATES["applicant"], "")).strip() or None,
        "description":        str(_pick(data, LIST_FIELD_CANDIDATES["description"], "")).strip()[:500] or None,
        "amount":             _to_int(_pick(data, LIST_FIELD_CANDIDATES["amount"], "0")) or 0,
        "status":             status,
        "approved_date":      _parse_approved_date(data, status),
        "last_updated_at":    last_updated_dt,
        "vendor1":            str(_pick(data, LIST_FIELD_CANDIDATES["vendor1"], "")).strip() or None,
        "vendor2":            str(_pick(data, LIST_FIELD_CANDIDATES["vendor2"], "")).strip() or None,
        "vendor3":            str(_pick(data, LIST_FIELD_CANDIDATES["vendor3"], "")).strip() or None,
        "amount_tax":         _to_int(_pick(data, LIST_FIELD_CANDIDATES["amount_tax"])),
        "amount_total":       _to_int(_pick(data, LIST_FIELD_CANDIDATES["amount_total"])),
        "remark":             str(_pick(data, LIST_FIELD_CANDIDATES["remark"], "")).strip()[:2000] or None,
        "raw_data_json":      json.dumps(data, ensure_ascii=False),
        "detail_synced":      False,
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
        logger.error("[NichiyoSync][List] %s 失敗：%s", dept_config["display_name"], exc)
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    now = twnow()
    # ★ 每 20 筆 commit 一次：縮短 SQLite 寫鎖持有時間，
    #    避免 APScheduler 與 sync_tool 同時執行時造成 database is locked
    COMMIT_EVERY = 20

    for idx, (record_id, data) in enumerate(records.items()):
        fetched += 1
        try:
            with db.begin_nested():
                fields = _parse_list_record(record_id, data, sheet_path, dept_config)

                existing = (
                    db.query(NichiyoPurchaseRequest)
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
                    order_obj = NichiyoPurchaseRequest(**fields, sync_at=now, created_at=now, updated_at=now)
                    db.add(order_obj)

                # 嘗試從清單 _subtable_* 直接解析品項
                if not fields.get("detail_synced", False):
                    item_rows = _find_subtable_from_list_raw(data)
                    if item_rows:
                        db.flush()   # 確保 order_obj.id 已取得
                        db.query(NichiyoPurchaseRequestItem).filter_by(
                            order_id=order_obj.id
                        ).delete(synchronize_session=False)
                        db.flush()   # ★ 強制 DELETE 先送出，避免 INSERT 排序在前

                        # ★ seq 去重：若 Ragic 回傳多列皆無「項次」，全都是 0 → UNIQUE 違反
                        seen_seqs: set[int] = set()
                        for loop_idx, row in enumerate(item_rows):
                            try:
                                seq = int(str(_pick(row, ["項次", "序號"], "0") or "0"))
                            except (ValueError, TypeError):
                                seq = loop_idx
                            if seq in seen_seqs:
                                seq = loop_idx
                                while seq in seen_seqs:
                                    seq += 1
                            seen_seqs.add(seq)

                            item = NichiyoPurchaseRequestItem(
                                order_id    = order_obj.id,
                                seq         = seq,
                                product_name= str(_pick(row, ITEM_FIELD_CANDIDATES["product_name"], "")).strip() or None,
                                qty         = str(_pick(row, ITEM_FIELD_CANDIDATES["qty"], "")).strip() or None,
                                unit        = str(_pick(row, ITEM_FIELD_CANDIDATES["unit"], "")).strip() or None,
                                item_remark = str(_pick(row, ITEM_FIELD_CANDIDATES["item_remark"], "")).strip() or None,
                                vendor1_price= _to_int(_pick(row, ITEM_FIELD_CANDIDATES["vendor1_price"])),
                                vendor2_price= _to_int(_pick(row, ITEM_FIELD_CANDIDATES["vendor2_price"])),
                                vendor3_price= _to_int(_pick(row, ITEM_FIELD_CANDIDATES["vendor3_price"])),
                                selected_vendor    = str(_pick(row, ITEM_FIELD_CANDIDATES["selected_vendor"], "")).strip() or None,
                                selected_unit_price= _to_int(_pick(row, ITEM_FIELD_CANDIDATES["selected_unit_price"])),
                                selected_amount    = _to_int(_pick(row, ITEM_FIELD_CANDIDATES["selected_amount"])),
                                is_confirmed= _to_bool(_pick(row, ITEM_FIELD_CANDIDATES["is_confirmed"])),
                                sync_at     = now,
                            )
                            db.add(item)
                        order_obj.detail_synced = True

                upserted += 1
        except Exception as exc:
            logger.error("[NichiyoSync][List] id=%s 失敗：%s", record_id, exc, exc_info=True)
            errors.append(str(exc))

        # ★ 每 COMMIT_EVERY 筆提交一次，釋放寫鎖供其他 writer 競爭
        if (idx + 1) % COMMIT_EVERY == 0:
            db.commit()

    db.commit()   # 最後一批
    return {"fetched": fetched, "upserted": upserted, "errors": errors}


# ── Step 2：Detail 品項同步 ───────────────────────────────────────────────────

async def _sync_detail_for_order(order: NichiyoPurchaseRequest, db) -> bool:
    dept_cfg = next(
        (d for d in get_sheet_configs("nichiyo_purchase") if d["list_path"] == order.ragic_sheet_path),
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
        logger.error("[NichiyoSync][Detail] order_id=%s 失敗：%s", order.id, exc)
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
        if field in ("amount_tax", "amount_total"):
            setattr(order, field, _to_int(val))
        elif field in ("approved_date", "request_date"):
            setattr(order, field, _to_date(val))
        elif field in ("vendor1", "vendor2", "vendor3", "remark", "description"):
            existing = getattr(order, field)
            if not existing:
                setattr(order, field, str(val).strip()[:500] if field == "description" else str(val).strip())

    # 品項子表格
    item_rows = _find_subtable(data)
    if item_rows:
        db.query(NichiyoPurchaseRequestItem).filter_by(order_id=order.id).delete(synchronize_session=False)
        for row in item_rows:
            item = NichiyoPurchaseRequestItem(
                order_id    = order.id,
                seq         = int(str(_pick(row, ["項次", "序號"], "0") or "0")),
                product_name= str(_pick(row, ITEM_FIELD_CANDIDATES["product_name"], "")).strip() or None,
                qty         = str(_pick(row, ITEM_FIELD_CANDIDATES["qty"], "")).strip() or None,
                unit        = str(_pick(row, ITEM_FIELD_CANDIDATES["unit"], "")).strip() or None,
                item_remark = str(_pick(row, ITEM_FIELD_CANDIDATES["item_remark"], "")).strip() or None,
                vendor1_price= _to_int(_pick(row, ITEM_FIELD_CANDIDATES["vendor1_price"])),
                vendor2_price= _to_int(_pick(row, ITEM_FIELD_CANDIDATES["vendor2_price"])),
                vendor3_price= _to_int(_pick(row, ITEM_FIELD_CANDIDATES["vendor3_price"])),
                selected_vendor    = str(_pick(row, ITEM_FIELD_CANDIDATES["selected_vendor"], "")).strip() or None,
                selected_unit_price= _to_int(_pick(row, ITEM_FIELD_CANDIDATES["selected_unit_price"])),
                selected_amount    = _to_int(_pick(row, ITEM_FIELD_CANDIDATES["selected_amount"])),
                is_confirmed= _to_bool(_pick(row, ITEM_FIELD_CANDIDATES["is_confirmed"])),
                sync_at     = now,
            )
            db.add(item)

    order.detail_synced = True
    order.sync_at       = now
    order.updated_at    = now
    return True


# ── 公開 Sync 入口 ────────────────────────────────────────────────────────────

async def sync_list_only() -> dict:
    """清單同步（每 15 分鐘）— main.py APScheduler 呼叫"""
    db = SessionLocal()
    total_fetched = total_upserted = 0
    all_errors: list[str] = []
    try:
        for dept in get_sheet_configs("nichiyo_purchase"):
            result = await _sync_list_for_dept(dept, db)
            total_fetched  += result["fetched"]
            total_upserted += result["upserted"]
            all_errors.extend(result.get("errors", []))
            await asyncio.sleep(0.5)
    finally:
        db.close()
    return {"fetched": total_fetched, "upserted": total_upserted, "errors": all_errors}


async def sync_detail_batch() -> dict:
    """Detail 品項同步（每 45 分鐘）— 處理未同步的主單"""
    db = SessionLocal()
    total = updated = 0
    errors: list[str] = []
    try:
        pending = (
            db.query(NichiyoPurchaseRequest)
            .filter(
                NichiyoPurchaseRequest.status == "F",
                NichiyoPurchaseRequest.detail_synced == False,
            )
            .all()
        )
        total = len(pending)
        for i, order in enumerate(pending):
            try:
                ok = await _sync_detail_for_order(order, db)
                if ok:
                    updated += 1
                if (i + 1) % BATCH_SIZE == 0:
                    db.commit()
                    await asyncio.sleep(BATCH_SLEEP_SEC)
                else:
                    await asyncio.sleep(DETAIL_CALL_DELAY_SEC)
            except Exception as exc:
                errors.append(f"order_id={order.id}: {exc}")
        db.commit()
    finally:
        db.close()
    return {"fetched": total, "upserted": updated, "errors": errors}


async def sync_all() -> dict:
    """清單 + Detail 完整同步（手動觸發用）

    步驟：
      1. 取得目前有效的 ragic_sheet_path 清單
      2. 刪除 ragic_sheet_path 不在有效清單中的舊記錄（路徑變更後的殘留孤兒）
      3. 清單同步 + Detail 同步
    """
    valid_paths = {d["list_path"] for d in get_sheet_configs("nichiyo_purchase")}

    db = SessionLocal()
    try:
        orphan_ids = [
            row.id
            for row in db.query(NichiyoPurchaseRequest.id)
            .filter(
                NichiyoPurchaseRequest.company == "日曜",
                ~NichiyoPurchaseRequest.ragic_sheet_path.in_(valid_paths),
            )
            .all()
        ]
        if orphan_ids:
            db.query(NichiyoPurchaseRequestItem).filter(
                NichiyoPurchaseRequestItem.order_id.in_(orphan_ids)
            ).delete(synchronize_session=False)
            db.query(NichiyoPurchaseRequest).filter(
                NichiyoPurchaseRequest.id.in_(orphan_ids)
            ).delete(synchronize_session=False)
            logger.info("[NichiyoPurchaseSync] 清除孤兒記錄 %d 筆（路徑已失效）", len(orphan_ids))
            db.commit()
    finally:
        db.close()

    list_result   = await sync_list_only()
    detail_result = await sync_detail_batch()
    return {
        "list":   list_result,
        "detail": detail_result,
        "fetched":   list_result["fetched"],
        "upserted":  list_result["upserted"] + detail_result["upserted"],
        "errors":    list_result["errors"] + detail_result["errors"],
    }
