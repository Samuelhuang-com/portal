"""
庫存管理 Phase 7（2026-11-17）加值分析 — docs/SPEC_stock_management.md §10

  abc_suggest()      依近 N 天「領用淨額」（領用＋退料）建議 ABC 分類：累計佔比 ≤80%＝A、≤95%＝B、其餘＝C；
                     沒有領用＝C。只建議，按「套用」才寫入料號庫存設定（循環盤點用）。
  replenishment()    補貨建議：可用量（帳上－保留）低於料號安全量（min_stock）的 倉×料號；
                     建議補到上限（max_stock，沒有上限時補到安全量），換算成採購單位（無條件進位）。
                     2026-11-17 Samuel 裁示：只做建議清單＋匯出，週採請購單仍由人開（不動週採程式）。
周轉天數在 stock_count_service.monthly_report() 一併計算。
"""
import math
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cycle_purchase_item import CyclePurchaseItem
from app.models.cycle_purchase_vendor import CyclePurchaseVendor
from app.models.stock import StockBalance, StockItemSetting, StockMove, StockWarehouse
from app.services.stock_service import _d

CONSUME_TYPES = ("issue", "return", "return_void")
ABC_A, ABC_B = Decimal("0.80"), Decimal("0.95")


def _consumption(db: Session, code: str, since: date, warehouse_ids: Optional[list[int]] = None):
    """各料號（或 倉×料號）自 since 起的領用淨數量與淨金額（正數＝用掉）。"""
    q = db.query(StockMove.warehouse_id, StockMove.item_id, func.sum(StockMove.qty), func.sum(StockMove.amount)) \
          .filter(StockMove.company_code == code, StockMove.moved_at >= since, StockMove.move_type.in_(CONSUME_TYPES))
    if warehouse_ids is not None:
        q = q.filter(StockMove.warehouse_id.in_(warehouse_ids or [0]))
    return {(w, i): (-_d(qty), -_d(amt)) for w, i, qty, amt in q.group_by(StockMove.warehouse_id, StockMove.item_id).all()}


def abc_suggest(db: Session, code: str, days: int = 90) -> list[dict]:
    since = date.today() - timedelta(days=days)
    by_item: dict[int, Decimal] = {}
    for (_w, i), (_q, a) in _consumption(db, code, since).items():
        by_item[i] = by_item.get(i, Decimal(0)) + max(a, Decimal(0))
    rows = (db.query(CyclePurchaseItem, StockItemSetting)
            .outerjoin(StockItemSetting, StockItemSetting.item_id == CyclePurchaseItem.id)
            .filter(CyclePurchaseItem.company_code == code, CyclePurchaseItem.is_active.is_(True)).all())
    rows = [(it, st) for it, st in rows if st is None or st.is_stock_item]
    stocked = {i for (i,) in db.query(StockBalance.item_id).join(StockWarehouse, StockWarehouse.id == StockBalance.warehouse_id)
               .filter(StockWarehouse.company_code == code).distinct()}
    rows = [(it, st) for it, st in rows if it.id in stocked or it.id in by_item]   # 只列有庫存紀錄的料號
    total = sum(by_item.values(), Decimal(0))
    ranked = sorted(rows, key=lambda r: by_item.get(r[0].id, Decimal(0)), reverse=True)
    out, cum = [], Decimal(0)
    for it, st in ranked:
        amt = by_item.get(it.id, Decimal(0))
        if amt <= 0 or total <= 0:
            cls, share = "C", Decimal(0)
        else:
            cum += amt
            share = cum / total
            cls = "A" if share - amt / total < ABC_A else ("B" if share - amt / total < ABC_B else "C")
        out.append({"item_id": it.id, "item_code": it.item_code, "item_name": it.item_name, "spec": it.spec, "unit": it.unit,
                    "consume_amount": float(amt), "share": float(amt / total) if total > 0 else 0.0,
                    "cum_share": float(share), "current": st.abc_class if st else None, "suggested": cls})
    return out


def apply_abc(db: Session, code: str, mapping: list[tuple[int, Optional[str]]], user_name: str) -> int:
    ids = [i for i, _ in mapping]
    items = {i.id: i for i in db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id.in_(ids or [0])).all()}
    settings = {s.item_id: s for s in db.query(StockItemSetting).filter(StockItemSetting.item_id.in_(ids or [0])).all()}
    n = 0
    for item_id, cls in mapping:
        it = items.get(item_id)
        if not it or it.company_code != code:
            continue
        st = settings.get(item_id)
        if st is None:
            st = StockItemSetting(item_id=item_id, is_stock_item=True, unit_ratio=1)
            db.add(st)
        st.abc_class, st.updated_by = (cls or None), user_name
        n += 1
    return n


def replenishment(db: Session, code: str, warehouse_ids: list[int], days: int = 90) -> list[dict]:
    since = date.today() - timedelta(days=days)
    use = _consumption(db, code, since, warehouse_ids)
    rows = (db.query(StockBalance, CyclePurchaseItem, StockItemSetting, StockWarehouse)
            .join(CyclePurchaseItem, CyclePurchaseItem.id == StockBalance.item_id)
            .join(StockWarehouse, StockWarehouse.id == StockBalance.warehouse_id)
            .outerjoin(StockItemSetting, StockItemSetting.item_id == CyclePurchaseItem.id)
            .filter(StockBalance.warehouse_id.in_(warehouse_ids or [0]), CyclePurchaseItem.min_stock.isnot(None),
                    StockWarehouse.status != "inactive").all())
    vids = {it.default_vendor_id for _b, it, _s, _w in rows if it.default_vendor_id}
    vname = dict(db.query(CyclePurchaseVendor.id, CyclePurchaseVendor.vendor_name)
                 .filter(CyclePurchaseVendor.id.in_(vids or {0})).all())
    out = []
    for b, it, st, w in rows:
        if st is not None and not st.is_stock_item:
            continue
        avail = _d(b.qty) - _d(b.reserved_qty)
        mn = Decimal(it.min_stock)
        if avail >= mn:
            continue
        target = Decimal(it.max_stock) if it.max_stock is not None and it.max_stock > it.min_stock else mn
        need = target - avail
        ratio = _d(st.unit_ratio) if st and st.unit_ratio else Decimal(1)
        p_unit = (st.purchase_unit if st and st.purchase_unit else None) or it.unit
        p_qty = math.ceil(need / ratio) if ratio > 0 else math.ceil(need)
        uq, ua = use.get((w.id, it.id), (Decimal(0), Decimal(0)))
        monthly = uq / Decimal(days) * Decimal(30)
        out.append({
            "warehouse_id": w.id, "warehouse_name": w.name, "department_name": w.department_name,
            "item_id": it.id, "item_code": it.item_code, "item_name": it.item_name, "spec": it.spec, "unit": it.unit,
            "qty": float(b.qty), "reserved_qty": float(b.reserved_qty), "available": float(avail),
            "min_stock": it.min_stock, "max_stock": it.max_stock, "suggest_qty": float(need),
            "purchase_unit": p_unit, "unit_ratio": float(ratio), "suggest_purchase_qty": p_qty,
            "monthly_use": float(round(monthly, 2)),
            "days_left": None if uq <= 0 else float(round(avail / (uq / Decimal(days)), 1)),
            "avg_cost": float(b.avg_cost), "est_amount": float(round(need * _d(b.avg_cost), 0)),
            "vendor_name": vname.get(it.default_vendor_id),
        })
    out.sort(key=lambda r: (r["days_left"] if r["days_left"] is not None else 1e9, r["warehouse_name"], r["item_code"]))
    return out
