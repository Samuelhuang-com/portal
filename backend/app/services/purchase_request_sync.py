"""
核准請購單同步服務：Ragic → SQLite

架構：Master + Detail 雙層同步
  Step 1：清單 API × 9 部門 → approved_purchase_requests（主單）
  Step 2：Detail API × 每筆主單 → approved_purchase_request_items（品項）
           + 補入 amount_tax / vendor1~3 / detail_synced=True

【N+1 優化策略】
  1. 增量同步：只重抓 last_updated_at > 上次 detail 同步時間 的記錄
  2. 速率限制：Detail API 呼叫間加入 100ms 延遲
  3. 分批處理：每批 50 筆，批次間休眠 3 秒（首次全量時保護 Ragic）
  4. detail_synced 旗標：中斷後可從未完成的記錄續傳

【欄位 mapping 策略】
  - 清單 API：欄位直接以中文顯示名稱為 key（由 Ragic naming 設定決定）
  - 透過 FIELD_CANDIDATES 候選清單容錯（同一欄位可能有不同 key 名）
  - 完整原始 JSON 存入 raw_data_json，供日後補正

【停管部特別處理】
  Ragic 部門值=「客服」，顯示名稱=「停管部」
  透過 DEPT_DISPLAY_MAP 自動對照
"""
import asyncio
import json
import logging
import re
from datetime import date, datetime
from typing import Any

from app.core.database import SessionLocal
from app.core.time import twnow
from app.models.purchase_request import (
    ApprovedPurchaseRequest,
    ApprovedPurchaseRequestItem,
    DEPT_DISPLAY_MAP,
    DEPT_SHEETS,
)
from app.services.ragic_adapter import RagicAdapter

logger = logging.getLogger(__name__)

# ── Ragic 連線設定（ap12 / soutlet001）────────────────────────────────────────
RAGIC_SERVER  = "ap12.ragic.com"
RAGIC_ACCOUNT = "soutlet001"

# ── 同步調速設定 ───────────────────────────────────────────────────────────────
DETAIL_CALL_DELAY_SEC = 0.1    # Detail API 呼叫間隔（100ms，避免 Ragic 429）
BATCH_SIZE            = 50     # 每批 Detail API 呼叫數量
BATCH_SLEEP_SEC       = 3.0    # 批次間休眠秒數

# ── 欄位候選清單（按優先序取第一個有值的）────────────────────────────────────
# 清單欄位 key
LIST_FIELD_CANDIDATES: dict[str, list[str]] = {
    "purchase_no":      ["編號", "請購單號", "單號", "工請編號", "專請編號", "財請編號", "採購編號"],
    "department_raw":   ["部門", "申請部門", "請購部門", "簽呈部門"],
    "account_category": ["會科", "金科", "費用科目"],
    "applicant":        ["申請人", "請購人"],
    "description":      ["說明", "請購事由", "摘要", "事由", "用途說明", "主旨"],
    "amount":           ["全案小計", "小計", "金額"],
    "status":           ["簽核狀態", "狀態"],
    "last_updated":     ["最後更新日期", "更新日期", "最後修改日期"],
    # 以下欄位清單 API 通常也直接提供，無需 Detail API
    "vendor1":          ["廠商(一)", "廠商一", "廠商1", "擬定廠商"],
    "vendor2":          ["廠商(二)", "廠商二", "廠商2"],
    "vendor3":          ["廠商(三)", "廠商三", "廠商3"],
    "amount_tax":       ["稅", "營業稅", "稅額", "稅金"],
    "amount_total":     ["全案總計", "含稅總額", "全案合計"],
    "remark":           ["備註", "補充"],
}

# 內頁欄位 key
DETAIL_FIELD_CANDIDATES: dict[str, list[str]] = {
    "request_date":     ["申請日期", "填單日期", "日期"],
    # 核准日期：內頁若有明確欄位優先使用；否則保留 list 同步時的 last_updated_at 代理值
    "approved_date":    ["核准日期", "簽核完成日期", "最終核准日期", "完成日期", "核准完成日期"],
    "amount_tax":       ["營業稅", "稅額", "稅金"],
    "amount_total":     ["全案總計", "含稅總額", "總計"],
    # 廠商欄位：各部門命名不同，財務/資訊部用「擬定廠商」（單一廠商）
    "vendor1":          ["廠商(一)", "廠商一", "廠商1", "擬定廠商"],
    "vendor2":          ["廠商(二)", "廠商二", "廠商2"],
    "vendor3":          ["廠商(三)", "廠商三", "廠商3"],
    "remark":           ["備註", "補充"],
    "description":      ["說明", "請購事由", "事由", "用途說明", "主旨"],
}

# 品項子表格欄位 key（子表格的 key 格式：有時帶前綴數字）
ITEM_FIELD_CANDIDATES: dict[str, list[str]] = {
    "seq":              ["項次", "序號"],
    "product_name":     ["產品名稱", "品名", "品項名稱", "名稱"],
    "qty":              ["數量"],
    "unit":             ["單位"],
    "item_remark":      ["品項備註", "備註"],
    "vendor1_price":    ["廠商(一)金額", "廠商一金額", "廠商1金額"],
    "vendor2_price":    ["廠商(二)金額", "廠商二金額", "廠商2金額"],
    "vendor3_price":    ["廠商(三)金額", "廠商三金額", "廠商3金額"],
    "selected_vendor":  ["擬定廠商", "選定廠商"],
    "selected_unit_price": ["擬定單價"],
    "selected_amount":  ["擬定金額"],
    "is_confirmed":     ["勾選"],
}


# ── 工具函式 ──────────────────────────────────────────────────────────────────

def _pick(data: dict, candidates: list[str], default="") -> Any:
    """從 dict 中按優先序取第一個有值的欄位。"""
    for key in candidates:
        val = data.get(key)
        if val is not None and str(val).strip():
            return val
    return default


def _to_int(val: Any) -> int | None:
    """將各種格式的金額字串轉為整數（去除 $、,、空白）。"""
    if val is None or str(val).strip() in ("", "-", "0"):
        return None
    try:
        cleaned = re.sub(r"[$,\s]", "", str(val))
        return int(float(cleaned)) if cleaned else None
    except (ValueError, TypeError):
        return None


def _to_date(val: Any) -> date | None:
    """將 Ragic 日期字串（YYYY/MM/DD 或 YYYY-MM-DD 或含時間）轉為 date 物件。"""
    if not val or str(val).strip() in ("", "0", "0/0/0"):
        return None
    s = str(val).strip()
    # 取前 10 字元（去除時間部分）
    s = s[:10].replace("/", "-")
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _to_bool(val: Any) -> bool | None:
    """將勾選欄位值轉為 bool（✓、Y、1、true 視為 True）。"""
    if val is None:
        return None
    s = str(val).strip().lower()
    return s in ("✓", "v", "y", "yes", "1", "true", "是")


def _dept_display(raw: str) -> str:
    """Ragic 部門值 → Portal 顯示名稱（停管部=客服→停管部）。"""
    return DEPT_DISPLAY_MAP.get(str(raw).strip(), str(raw).strip())


def _find_subtable(raw: dict) -> list[dict]:
    """
    從內頁 raw JSON 中找出品項子表格資料。
    Ragic 子表格格式：key 為數字字串，值為含有「項次」或「產品名稱」等欄位的 dict。
    回傳 list of row dicts（已排序）。
    """
    rows = []
    for k, v in raw.items():
        if not isinstance(v, dict):
            continue
        # 跳過明顯是主表欄位的非子表格 key
        if not k.lstrip("-").isdigit():
            continue
        # 子表格行：通常含有「項次」或「產品名稱」等
        has_item_field = any(
            cand in v
            for cands in ITEM_FIELD_CANDIDATES.values()
            for cand in cands
        )
        if has_item_field:
            rows.append(v)
    # 依「項次」排序
    rows.sort(key=lambda r: int(str(_pick(r, ["項次", "序號"], "0") or "0")))
    return rows


def _find_subtable_from_list_raw(raw: dict) -> list[dict]:
    """
    從清單 API raw JSON 中找出品項子表格（_subtable_XXXXXX 欄位）。

    清單 API 格式：
      {"_subtable_1010217": {"145": {_ragicId, 項次, 產品名稱, ...}, "146": {...}}}

    _subtable_* value 可能已是 dict（json.loads 後），
    或在舊版資料庫記錄中以 Python repr 字串儲存。

    回傳已排序的 row dict list；找不到時回傳空 list。
    """
    import ast

    rows = []
    for k, v in raw.items():
        if not k.startswith("_subtable_"):
            continue
        # 舊記錄可能把 dict 以 str 儲存（ast.literal_eval 解析）
        if isinstance(v, str):
            try:
                v = ast.literal_eval(v)
            except Exception:
                continue
        if not isinstance(v, dict):
            continue
        # v = {row_id: {fields}, ...}
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

def _parse_list_record(
    record_id: str,
    data: dict,
    sheet_path: str,
    dept_config: dict,
) -> dict:
    """將清單 API 單筆記錄解析為 approved_purchase_requests 欄位 dict。"""
    raw_dept    = str(_pick(data, LIST_FIELD_CANDIDATES["department_raw"], "")).strip()
    last_updated_str = _pick(data, LIST_FIELD_CANDIDATES["last_updated"])
    last_updated_dt  = None
    if last_updated_str:
        # Ragic 可能回傳以下格式（按優先序嘗試）：
        #   "YYYY/MM/DD HH:MM:SS"（19 chars）
        #   "YYYY/MM/DD HH:MM"   （16 chars，最常見）
        #   "YYYY/MM/DD"         （10 chars）
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
        # Fallback：Ragic 清單 API 實際回傳 _dataTimestamp（Unix 毫秒時戳）
        # 而非「最後更新日期」文字欄位
        ts = data.get("_dataTimestamp")
        if ts:
            try:
                last_updated_dt = datetime.fromtimestamp(int(ts) / 1000)
            except (ValueError, TypeError, OSError):
                pass

    # status
    status_raw   = str(_pick(data, LIST_FIELD_CANDIDATES["status"], "N")).strip().upper()
    status       = status_raw if status_raw in ("F", "N", "REJ") else "N"

    # approved_date：
    #   Ragic 簽核日期存在 "日期"/"日期2"/"日期3"... 等編號欄位
    #   已核准（status=F）時，取所有非空的 日期N 欄位最大值 = 最後簽核完成日
    approved_dt = None
    if status == "F":
        sign_dates = []
        for key, val in data.items():
            if key.startswith("日期") and val and str(val).strip():
                d = _to_date(val)
                if d:
                    sign_dates.append(d)
        if sign_dates:
            approved_dt = max(sign_dates)
        elif last_updated_dt:
            # 無簽核日期欄位時，退而求其次用 _dataTimestamp
            approved_dt = last_updated_dt.date()

    return {
        "company":            "樂群",
        "department_raw":     raw_dept or dept_config["ragic_dept"],
        "department_display": _dept_display(raw_dept or dept_config["ragic_dept"]),
        "ragic_sheet_path":   sheet_path,
        "ragic_record_id":    str(record_id),
        "purchase_no":        str(_pick(data, LIST_FIELD_CANDIDATES["purchase_no"], "")).strip(),
        "account_category":   str(_pick(data, LIST_FIELD_CANDIDATES["account_category"], "")).strip() or None,
        "applicant":          str(_pick(data, LIST_FIELD_CANDIDATES["applicant"], "")).strip() or None,
        "description":        str(_pick(data, LIST_FIELD_CANDIDATES["description"], "")).strip()[:500] or None,
        "amount":             _to_int(_pick(data, LIST_FIELD_CANDIDATES["amount"], "0")) or 0,
        "status":             status,
        "approved_date":      approved_dt,
        "last_updated_at":    last_updated_dt,
        # ── 清單 API 通常也含廠商 / 稅額 / 備註（有值才寫，None = 留給 Detail sync 補）
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
    """單一部門：從清單 API 同步主單資料。"""
    sheet_path = dept_config["list_path"]
    adapter = RagicAdapter(
        sheet_path=sheet_path,
        server_url=RAGIC_SERVER,
        account=RAGIC_ACCOUNT,
    )

    fetched = 0
    upserted = 0
    errors = []

    try:
        records = await adapter.fetch_all()
    except Exception as exc:
        logger.error("[PurchaseSync][List] %s 清單 API 失敗：%s", dept_config["display_name"], exc)
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    now = twnow()

    for record_id, data in records.items():
        fetched += 1
        try:
            with db.begin_nested():  # SAVEPOINT：單筆失敗只 rollback 該筆，不影響其他記錄
                fields = _parse_list_record(record_id, data, sheet_path, dept_config)

                existing = (
                    db.query(ApprovedPurchaseRequest)
                    .filter_by(
                        ragic_sheet_path=sheet_path,
                        ragic_record_id=str(record_id),
                    )
                    .first()
                )

                if existing:
                    # 更新（若 last_updated_at 有改變，重置 detail_synced 以便重新同步品項）
                    new_updated = fields.get("last_updated_at")
                    if new_updated and existing.last_updated_at != new_updated:
                        fields["detail_synced"] = False

                    for k, v in fields.items():
                        setattr(existing, k, v)
                    existing.sync_at    = now
                    existing.updated_at = now
                    order_obj = existing
                else:
                    order_obj = ApprovedPurchaseRequest(**fields, sync_at=now, created_at=now, updated_at=now)
                    db.add(order_obj)

                # ── 嘗試從清單 API raw data 直接解析品項（_subtable_* 欄位）──────
                # 若清單 API 已含子表格，無需等 Detail API；直接寫入並標記 detail_synced=True
                if not fields.get("detail_synced", False):
                    item_rows = _find_subtable_from_list_raw(data)
                    if item_rows:
                        # flush 確保 order_obj.id 已分配（新增記錄需要 PK）
                        db.flush()
                        # synchronize_session=False：確保 DELETE 立即反映在 DB
                        db.query(ApprovedPurchaseRequestItem).filter_by(
                            order_id=order_obj.id
                        ).delete(synchronize_session=False)
                        db.flush()  # DELETE 先 flush，再 INSERT，避免 UNIQUE constraint
                        for idx, row_data in enumerate(item_rows):
                            item_fields = _parse_item_row(row_data, order_obj.id, idx)
                            db.add(ApprovedPurchaseRequestItem(**item_fields))
                        order_obj.detail_synced = True
                        logger.debug(
                            "[PurchaseSync][List] record %s 從清單資料解析到 %d 筆品項",
                            record_id, len(item_rows),
                        )

            upserted += 1

        except Exception as exc:
            logger.warning("[PurchaseSync][List] record %s 解析失敗：%s", record_id, exc)
            errors.append(f"record {record_id}: {exc}")

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("[PurchaseSync][List] commit 失敗：%s", exc)
        errors.append(f"commit: {exc}")

    return {"fetched": fetched, "upserted": upserted, "errors": errors}


# ── Step 2：Detail 同步 ───────────────────────────────────────────────────────

def _parse_detail_record(raw: dict) -> dict:
    """從 Detail API 回傳解析額外欄位（稅額、廠商、備註、申請日期、核准日期）。"""
    # 核准日期：若內頁有明確欄位就用，沒有則回傳 None（保留 list 同步的 last_updated_at 代理值）
    approved_date_val = _pick(raw, DETAIL_FIELD_CANDIDATES["approved_date"])
    return {
        "request_date":  _to_date(_pick(raw, DETAIL_FIELD_CANDIDATES["request_date"])),
        "approved_date": _to_date(approved_date_val) if approved_date_val else None,
        "amount_tax":    _to_int(_pick(raw, DETAIL_FIELD_CANDIDATES["amount_tax"])),
        "amount_total":  _to_int(_pick(raw, DETAIL_FIELD_CANDIDATES["amount_total"])),
        "vendor1":       str(_pick(raw, DETAIL_FIELD_CANDIDATES["vendor1"], "")).strip() or None,
        "vendor2":       str(_pick(raw, DETAIL_FIELD_CANDIDATES["vendor2"], "")).strip() or None,
        "vendor3":       str(_pick(raw, DETAIL_FIELD_CANDIDATES["vendor3"], "")).strip() or None,
        "remark":        str(_pick(raw, DETAIL_FIELD_CANDIDATES["remark"], "")).strip() or None,
        "description":   str(_pick(raw, DETAIL_FIELD_CANDIDATES["description"], "")).strip()[:500] or None,
    }


def _parse_item_row(row: dict, order_id: int, idx: int) -> dict:
    """從子表格單行解析品項欄位。

    seq 固定使用 idx+1（迴圈位置），不採用 Ragic 的「項次」欄位值。
    原因：_find_subtable_from_list_raw 會合併多個 _subtable_* 子表格，
    各子表格的「項次」各自從 1 開始，合併後必然重複，導致 UNIQUE constraint。
    idx 在合併後的 list 內全域唯一，用來作為 seq 安全可靠。
    """
    seq = idx + 1

    return {
        "order_id":           order_id,
        "seq":                seq,
        "product_name":       str(_pick(row, ITEM_FIELD_CANDIDATES["product_name"], "")).strip() or None,
        "qty":                str(_pick(row, ITEM_FIELD_CANDIDATES["qty"], "")).strip() or None,
        "unit":               str(_pick(row, ITEM_FIELD_CANDIDATES["unit"], "")).strip() or None,
        "item_remark":        str(_pick(row, ITEM_FIELD_CANDIDATES["item_remark"], "")).strip() or None,
        "vendor1_price":      _to_int(_pick(row, ITEM_FIELD_CANDIDATES["vendor1_price"])),
        "vendor2_price":      _to_int(_pick(row, ITEM_FIELD_CANDIDATES["vendor2_price"])),
        "vendor3_price":      _to_int(_pick(row, ITEM_FIELD_CANDIDATES["vendor3_price"])),
        "selected_vendor":    str(_pick(row, ITEM_FIELD_CANDIDATES["selected_vendor"], "")).strip() or None,
        "selected_unit_price": _to_int(_pick(row, ITEM_FIELD_CANDIDATES["selected_unit_price"])),
        "selected_amount":    _to_int(_pick(row, ITEM_FIELD_CANDIDATES["selected_amount"])),
        "is_confirmed":       _to_bool(_pick(row, ITEM_FIELD_CANDIDATES["is_confirmed"])),
        "sync_at":            twnow(),
    }


async def _sync_detail_batch(orders: list[ApprovedPurchaseRequest], db) -> dict:
    """
    對一批主單呼叫 Detail API，更新品項子表 + 額外欄位。
    N+1 + 100ms 延遲。
    """
    fetched = 0
    upserted = 0
    errors = []
    now = twnow()

    # 找出對應的 dept_config（用 list_path 比對）
    sheet_to_detail: dict[str, str] = {
        d["list_path"]: d["detail_path"] for d in DEPT_SHEETS
    }

    for order in orders:
        detail_path = sheet_to_detail.get(order.ragic_sheet_path)
        if not detail_path:
            logger.warning("[PurchaseSync][Detail] 找不到 detail_path for %s", order.ragic_sheet_path)
            errors.append(f"no detail_path for {order.ragic_sheet_path}")
            continue

        adapter = RagicAdapter(
            sheet_path=detail_path,
            server_url=RAGIC_SERVER,
            account=RAGIC_ACCOUNT,
        )

        try:
            raw = await adapter.fetch_one(order.ragic_record_id)
            fetched += 1
        except Exception as exc:
            logger.warning("[PurchaseSync][Detail] record %s fetch 失敗：%s",
                           order.ragic_record_id, exc)
            errors.append(f"record {order.ragic_record_id}: {exc}")
            await asyncio.sleep(DETAIL_CALL_DELAY_SEC)
            continue

        try:
            # ── Ragic 單筆 Detail API 回傳 {record_id: {fields}}，需先 unwrap ──
            # 例：fetch_one("39") 回傳 {"39": {"申請日期": ..., "小計": ...}}
            # 直接用 raw 呼叫 _pick() 會因找不到中文 key 而全部 None
            rid_str = str(order.ragic_record_id)
            if rid_str in raw and isinstance(raw[rid_str], dict):
                record_data = raw[rid_str]
            else:
                # fallback：取第一個數字 key 的 dict 值
                numeric_vals = [v for k, v in raw.items()
                                if k.lstrip("-").isdigit() and isinstance(v, dict)]
                record_data = numeric_vals[0] if numeric_vals else raw

            with db.begin_nested():  # SAVEPOINT：單筆失敗不污染外層 transaction
                # ① 更新主單額外欄位
                extra = _parse_detail_record(record_data)
                for k, v in extra.items():
                    if v is not None:  # 不覆蓋清單已有的有效值
                        setattr(order, k, v)
                order.detail_synced = True
                order.sync_at       = now
                order.updated_at    = now

                # ② 刪除舊品項，重新寫入（確保品項數量正確）
                db.query(ApprovedPurchaseRequestItem).filter_by(
                    order_id=order.id
                ).delete(synchronize_session=False)
                db.flush()  # DELETE 先 flush，再 INSERT，避免 UNIQUE constraint
                item_rows = _find_subtable(record_data)   # 在 unwrapped 資料中找子表格
                for idx, row_data in enumerate(item_rows):
                    item_fields = _parse_item_row(row_data, order.id, idx)
                    db.add(ApprovedPurchaseRequestItem(**item_fields))

            upserted += 1

        except Exception as exc:
            logger.warning("[PurchaseSync][Detail] record %s 解析失敗：%s",
                           order.ragic_record_id, exc)
            errors.append(f"parse {order.ragic_record_id}: {exc}")

        await asyncio.sleep(DETAIL_CALL_DELAY_SEC)  # 速率限制

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("[PurchaseSync][Detail] commit 失敗：%s", exc)
        errors.append(f"commit: {exc}")

    return {"fetched": fetched, "upserted": upserted, "errors": errors}


# ── 主入口 ────────────────────────────────────────────────────────────────────

async def sync_list_only() -> dict:
    """
    請購單清單同步（每 15 分鐘執行）：
    只更新主單欄位，若 subtable 存在也一併寫入品項。
    """
    list_result = {"fetched": 0, "upserted": 0, "errors": []}
    for dept in DEPT_SHEETS:
        db = SessionLocal()
        try:
            result = await _sync_list_for_dept(dept, db)
        finally:
            db.close()
        list_result["fetched"]  += result["fetched"]
        list_result["upserted"] += result["upserted"]
        list_result["errors"].extend(result["errors"])
    logger.info("[PurchaseSync] 清單同步完成：%s", list_result)
    return list_result


async def sync_from_ragic(full_resync: bool = False) -> dict:
    """
    核准請購單雙層同步主入口。

    Args:
        full_resync: True=全量重新同步所有記錄的 Detail；
                     False=增量（只重抓 detail_synced=False 的記錄）

    Returns:
        {
            "master": { fetched, upserted, errors },
            "detail": { fetched, upserted, errors },
        }

    【Session 管理策略】
    每個 Step / 批次結束後立即 close session，避免長期持鎖
    造成 APScheduler 寫 sync_log 時 "database is locked"。
    """
    list_result   = {"fetched": 0, "upserted": 0, "errors": []}
    detail_result = {"fetched": 0, "upserted": 0, "errors": []}

    try:
        # ════════════════════════════════════════════════════
        # Step 1：清單 API（9 個部門）— 每部門獨立 session
        # ════════════════════════════════════════════════════
        logger.info("[PurchaseSync] Step 1 開始：清單同步（9 部門）")
        for dept in DEPT_SHEETS:
            db = SessionLocal()
            try:
                result = await _sync_list_for_dept(dept, db)
            finally:
                db.close()   # ← 每部門同步完成後立即釋放鎖
            list_result["fetched"]  += result["fetched"]
            list_result["upserted"] += result["upserted"]
            list_result["errors"].extend(result["errors"])
            logger.info(
                "[PurchaseSync][List] %s：fetched=%d upserted=%d errors=%d",
                dept["display_name"],
                result["fetched"],
                result["upserted"],
                len(result["errors"]),
            )

        # ════════════════════════════════════════════════════
        # Step 2：Detail API（增量或全量）
        # ════════════════════════════════════════════════════
        logger.info("[PurchaseSync] Step 2 開始：Detail 同步（full_resync=%s）", full_resync)

        if full_resync:
            db = SessionLocal()
            try:
                db.query(ApprovedPurchaseRequest).update({"detail_synced": False})
                db.commit()
            finally:
                db.close()

        # 取出所有尚未完成 Detail 同步的記錄 IDs（只取 ID，立即關閉 session）
        db = SessionLocal()
        try:
            pending_ids = [
                r.id
                for r in db.query(ApprovedPurchaseRequest.id)
                .filter(ApprovedPurchaseRequest.detail_synced == False)
                .all()
            ]
        finally:
            db.close()

        logger.info("[PurchaseSync][Detail] 待同步筆數：%d", len(pending_ids))
        total_batches = (len(pending_ids) + BATCH_SIZE - 1) // BATCH_SIZE

        # 分批執行（BATCH_SIZE 筆一批）— 每批獨立 session
        for i in range(0, len(pending_ids), BATCH_SIZE):
            batch_ids = pending_ids[i : i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            logger.info(
                "[PurchaseSync][Detail] 批次 %d/%d（%d 筆）",
                batch_num, total_batches, len(batch_ids),
            )

            # 每批重新開 session，避免長期持鎖
            db = SessionLocal()
            try:
                batch = (
                    db.query(ApprovedPurchaseRequest)
                    .filter(ApprovedPurchaseRequest.id.in_(batch_ids))
                    .all()
                )
                result = await _sync_detail_batch(batch, db)
            finally:
                db.close()   # ← 批次完成後立即釋放鎖

            detail_result["fetched"]  += result["fetched"]
            detail_result["upserted"] += result["upserted"]
            detail_result["errors"].extend(result["errors"])

            # 批次間休眠（非最後批次）
            if i + BATCH_SIZE < len(pending_ids):
                await asyncio.sleep(BATCH_SLEEP_SEC)

    except Exception as exc:
        logger.error("[PurchaseSync] 同步失敗：%s", exc)
        list_result["errors"].append(str(exc))

    logger.info(
        "[PurchaseSync] 完成 list=(%d/%d) detail=(%d/%d) errors=%d",
        list_result["fetched"],  list_result["upserted"],
        detail_result["fetched"], detail_result["upserted"],
        len(list_result["errors"]) + len(detail_result["errors"]),
    )

    # 回傳格式相容 main.py _parse_sync_result（master/detail 格式）
    return {
        "master": list_result,
        "detail": detail_result,
    }
