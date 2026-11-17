"""
Ragic 採購單同步服務：Ragic → PostgreSQL（庫存管理 Phase 1，2026-11-17）
規格：docs/SPEC_stock_management.md §4.3、§4.4、§11

來源表單：ragic_sheet_config
  purchase_po  → 樂群
  nichiyo_po   → 日曜
  taichung_po  → 台中
（表單清單見 ragic_sheet_config_service._SEED_DATA；改部門或換表單直接改設定，不用改程式）

流程（每張表單獨立 session，避免長期持鎖）：
  1. 清單 API 一次取回主單＋子表（Phase 0 實測清單 API 已含 _subtable_*，不需 Detail API）
  2. 以 (ragic_sheet_path, ragic_record_id) upsert 主單；來源雜湊有變才重寫品項
  3. 這張表單本次沒出現的舊紀錄標 is_ragic_deleted=True（不刪除，之後進貨匯入要追溯）
     ⚠️ 只在「該表單讀取成功」時才做，讀取失敗不可把整張表標成已刪除
"""
import hashlib
import json
import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.database import SessionLocal
from app.core.time import twnow
from app.models.ragic_purchase_order import RagicPurchaseOrder, RagicPurchaseOrderItem
from app.services.ragic_adapter import RagicAdapter
from app.services.ragic_sheet_config_service import get_sheet_configs

logger = logging.getLogger(__name__)

RAGIC_SERVER = "ap12.ragic.com"
RAGIC_ACCOUNT = "soutlet001"

# module → 公司別（與既有請購／請款表的 company 字串一致）
PO_MODULES: list[tuple[str, str]] = [
    ("purchase_po", "樂群"),
    ("nichiyo_po", "日曜"),
    ("taichung_po", "台中"),
]


# ── 解析工具 ──────────────────────────────────────────────────────────────────

def _s(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return ",".join(_s(x) for x in v)
    return str(v).strip()


def _first(data: dict, *keys: str) -> str:
    for k in keys:
        v = _s(data.get(k))
        if v:
            return v
    return ""


def _startswith(data: dict, prefix: str, keep_label: bool = False) -> str:
    """欄位名稱各部門不同（如「1.付款條件」「1.付款條件：月結」），取第一個以 prefix 開頭且有值的欄位。

    keep_label=True 時保留欄位名稱多出來的部分：台中「1.付款條件：月結」值為「60」→ 回傳「月結 60」。
    """
    for k, v in data.items():
        if k.startswith(prefix) and _s(v):
            extra = k[len(prefix):].strip().lstrip("：:").strip()
            return f"{extra} {_s(v)}" if keep_label and extra else _s(v)
    return ""


def _num(v: Any) -> Decimal | None:
    t = re.sub(r"[^\d.\-]", "", _s(v))
    if not t or t in ("-", ".", "-."):
        return None
    try:
        return Decimal(t)
    except InvalidOperation:
        return None


def _date(v: Any) -> date | None:
    m = re.match(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", _s(v))
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None


def _int(v: Any) -> int | None:
    t = re.sub(r"[^\d]", "", _s(v))
    return int(t) if t else None


def _hash(data: dict) -> str:
    clean = {k: v for k, v in data.items() if k not in ("_star", "_dataTimestamp")}
    return hashlib.sha256(json.dumps(clean, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _subtable_rows(data: dict) -> list[dict]:
    rows: list[dict] = []
    for k, v in data.items():
        if k.startswith("_subtable_") and isinstance(v, dict):
            for rid, row in v.items():
                if isinstance(row, dict):
                    rows.append({**row, "_ragicId": _s(row.get("_ragicId")) or _s(rid)})
    rows.sort(key=lambda r: (_int(r.get("項次")) or 0, _int(r.get("_ragicId")) or 0))
    return rows


def _parse_order(data: dict, company: str, module: str, cfg: dict, record_id: str) -> dict:
    return {
        "company":            company,
        "sheet_module":       module,
        "department_display": cfg["display_name"],
        "department_raw":     _first(data, "請購部門", "部門") or None,
        "ragic_sheet_path":   cfg["list_path"],
        "ragic_record_id":    str(record_id),
        "po_no":              _first(data, "採購編號", "採購單號", "編號"),
        "source_pr_no":       _first(data, "來源請購單號") or None,
        "requester":          _first(data, "申請人") or None,
        "apply_date":         _date(_first(data, "申請日期")),
        "arrival_date":       _date(_first(data, "到貨日期")),
        "purpose":            _first(data, "用途說明", "31事由", "事由") or None,
        "vendor_name":        _first(data, "擬定廠商", "25擬定廠商名稱")[:200] or None,
        "vendor_code":        _first(data, "24最終擬定廠商編號")[:50] or None,
        "subtotal":           _num(data.get("小計")),
        "tax":                _num(data.get("營業稅")),
        "total":              _num(data.get("總計")),
        "payment_terms":      _startswith(data, "1.付款條件", keep_label=True)[:200] or None,
        "receiver":           _startswith(data, "收貨人")[:100] or None,
        "ragic_data_ts":      _int(data.get("_dataTimestamp")),
        "raw_data_json":      json.dumps(data, ensure_ascii=False, default=str),
        "source_hash":        _hash(data),
        "is_ragic_deleted":   False,
    }


def _parse_item(row: dict, order_id: int) -> dict:
    return {
        "order_id":     order_id,
        "ragic_row_id": _s(row.get("_ragicId")),
        "seq":          _int(row.get("項次")),
        "item_code":    _first(row, "料號")[:50] or None,
        "product_name": _first(row, "產品名稱", "品名", "品項名稱") or None,
        "qty":          _num(row.get("數量")),
        "qty_raw":      _s(row.get("數量"))[:50] or None,
        "unit":         _first(row, "單位")[:50] or None,
        "remark":       _first(row, "品項備註") or None,
        "unit_price":   _num(_first(row, "擬定廠商單價", "單價")),
        "amount":       _num(_first(row, "擬定廠商金額", "金額")),
        "item_dept":    _first(row, "部門")[:50] or None,
    }


# ── 同步 ──────────────────────────────────────────────────────────────────────

async def _sync_sheet(company: str, module: str, cfg: dict) -> dict:
    path = cfg["list_path"]
    adapter = RagicAdapter(sheet_path=path, server_url=RAGIC_SERVER, account=RAGIC_ACCOUNT)
    try:
        records = await adapter.fetch_all()
    except Exception as exc:
        logger.error("[RagicPOSync] %s/%s 清單 API 失敗：%s", company, cfg["display_name"], exc)
        return {"fetched": 0, "upserted": 0, "deleted": 0, "errors": [f"{path}: {exc}"]}

    fetched, upserted, errors = 0, 0, []
    now = twnow()
    db = SessionLocal()
    try:
        existing = {
            o.ragic_record_id: o
            for o in db.query(RagicPurchaseOrder).filter(RagicPurchaseOrder.ragic_sheet_path == path).all()
        }
        for record_id, data in records.items():
            fetched += 1
            try:
                with db.begin_nested():
                    fields = _parse_order(data, company, module, cfg, record_id)
                    order = existing.get(str(record_id))
                    rewrite_items = True
                    if order:
                        rewrite_items = order.source_hash != fields["source_hash"]
                        for k, v in fields.items():
                            setattr(order, k, v)
                        order.sync_at = now
                    else:
                        order = RagicPurchaseOrder(**fields, sync_at=now, created_at=now, updated_at=now)
                        db.add(order)
                        db.flush()
                    if rewrite_items:
                        # 依 ragic_row_id upsert：保留既有品項的 id（之後進貨匯入會引用它）
                        old = {i.ragic_row_id: i for i in db.query(RagicPurchaseOrderItem)
                               .filter(RagicPurchaseOrderItem.order_id == order.id).all()}
                        seen = set()
                        for row in _subtable_rows(data):
                            f = _parse_item(row, order.id)
                            if not f["ragic_row_id"] or f["ragic_row_id"] in seen:
                                continue
                            seen.add(f["ragic_row_id"])
                            item = old.get(f["ragic_row_id"])
                            if item:
                                for k, v in f.items():
                                    setattr(item, k, v)
                                item.sync_at = now
                            else:
                                db.add(RagicPurchaseOrderItem(**f, sync_at=now))
                        for rid, item in old.items():
                            if rid not in seen:
                                db.delete(item)
                upserted += 1
            except Exception as exc:
                logger.warning("[RagicPOSync] %s record %s 解析失敗：%s", path, record_id, exc)
                errors.append(f"{path}/{record_id}: {exc}")

        fetched_ids = {str(k) for k in records}
        deleted = 0
        for rid, order in existing.items():
            if rid not in fetched_ids and not order.is_ragic_deleted:
                order.is_ragic_deleted = True
                order.sync_at = now
                deleted += 1
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("[RagicPOSync] %s commit 失敗：%s", path, exc)
        errors.append(f"{path} commit: {exc}")
        deleted = 0
    finally:
        db.close()
    return {"fetched": fetched, "upserted": upserted, "deleted": deleted, "errors": errors}


async def sync_from_ragic() -> dict:
    """三家公司所有採購單表單同步主入口（回傳標準格式 {fetched, upserted, errors}）。"""
    total = {"fetched": 0, "upserted": 0, "deleted": 0, "errors": []}
    for module, company in PO_MODULES:
        for cfg in get_sheet_configs(module):
            r = await _sync_sheet(company, module, cfg)
            for k in ("fetched", "upserted", "deleted"):
                total[k] += r[k]
            total["errors"].extend(r["errors"])
            logger.info("[RagicPOSync] %s/%s：fetched=%d upserted=%d deleted=%d errors=%d",
                        company, cfg["display_name"], r["fetched"], r["upserted"], r["deleted"], len(r["errors"]))
    logger.info("[RagicPOSync] 完成：%s", {k: v for k, v in total.items() if k != "errors"})
    return total
