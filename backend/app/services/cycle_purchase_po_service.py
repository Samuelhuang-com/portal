"""
週期採購 — 採購單 Service 層（查詢／編輯／狀態變更）

採購單本身由 cycle_purchase_summary_service.convert_to_po() 建立，這裡只處理
建立之後的查詢、編輯（預計到貨日／備註）、狀態變更（draft -> issued /
draft-or-issued -> cancelled）。

2026-07-11 提醒（尚未跟 Samuel 確認，先照最保守的方式實作，之後如需要再調整）：
取消（cancelled）一張採購單，目前「不會」自動把對應的彙整列狀態從 converted
改回 draft、也不會清空彙整列的 po_id——避免自動改動資料造成誤解。如果之後
需要「取消採購單後彙整列自動解鎖可以重轉」的行為，需要另外實作，目前這是
刻意先不做、之後要 Samuel 確認的地方。
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.cycle_purchase_po import CyclePurchasePO
from app.models.cycle_purchase_cycle import CyclePurchaseCycle
from app.models.cycle_purchase_vendor import CyclePurchaseVendor


class POServiceError(Exception):
    """給 router 轉成適當 HTTP 錯誤用的一般性例外。"""
    pass


def _attach_po_display_fields(db: Session, po: CyclePurchasePO) -> CyclePurchasePO:
    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == po.cycle_id).first()
    po.cycle_name = cycle.cycle_name if cycle else None
    vendor = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.id == po.vendor_id).first()
    po.vendor_name = vendor.vendor_name if vendor else None
    return po


def list_pos(
    db: Session,
    cycle_id: Optional[int] = None,
    period_label: Optional[str] = None,
    company: Optional[str] = None,
    vendor_id: Optional[int] = None,
    status: Optional[str] = None,
):
    query = db.query(CyclePurchasePO)
    if cycle_id is not None:
        query = query.filter(CyclePurchasePO.cycle_id == cycle_id)
    if period_label:
        query = query.filter(CyclePurchasePO.period_label == period_label)
    if company:
        query = query.filter(CyclePurchasePO.company == company)
    if vendor_id is not None:
        query = query.filter(CyclePurchasePO.vendor_id == vendor_id)
    if status:
        query = query.filter(CyclePurchasePO.status == status)
    rows = query.order_by(CyclePurchasePO.po_no.desc()).all()
    for r in rows:
        _attach_po_display_fields(db, r)
    return rows


def get_po(db: Session, po_id: int) -> Optional[CyclePurchasePO]:
    po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == po_id).first()
    if po:
        _attach_po_display_fields(db, po)
    return po


def update_po(db: Session, po_id: int, payload) -> Optional[CyclePurchasePO]:
    po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == po_id).first()
    if not po:
        return None
    if po.status != "draft":
        raise POServiceError("只有草稿狀態的採購單可以編輯預計到貨日／備註")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(po, k, v)
    db.flush()
    return _attach_po_display_fields(db, po)


def set_po_status(db: Session, po_id: int, new_status: str) -> Optional[CyclePurchasePO]:
    po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == po_id).first()
    if not po:
        return None
    if new_status not in ("issued", "cancelled"):
        raise POServiceError("狀態只能是 issued 或 cancelled")
    if new_status == "issued":
        if po.status != "draft":
            raise POServiceError("只有草稿狀態的採購單可以發出")
        po.status = "issued"
    else:  # cancelled
        if po.status not in ("draft", "issued"):
            raise POServiceError("只有草稿或已發出狀態的採購單可以取消")
        po.status = "cancelled"
    db.flush()
    return _attach_po_display_fields(db, po)
