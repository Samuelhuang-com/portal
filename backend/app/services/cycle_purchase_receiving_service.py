"""
週期採購 — 驗收單 Service 層（第四期：驗收單＋進貨數量報表）

分批驗收與差異計算的完整規則說明見 models/cycle_purchase_receiving.py 開頭
docstring。這裡只重述關鍵點：
  - 只有 issued／partial_received 狀態的採購單可以建立驗收單；received（已
    全部驗收完）與 draft／cancelled 不行。
  - 驗收明細的 is_final_for_item=True（預設）才會在送出時計算差異；
    False 代表「這只是部分到貨，之後還會再驗收」，不計算差異。
  - 驗收單送出後，系統自動依全部明細行的累計已驗收數量，重算對應採購單的
    狀態（issued -> partial_received -> received），不能人工指定。

2026-07-11（第五期新增）：送出時若有明細行差異數量≠0，系統自動為每一筆
有差異的明細行寫一筆稽核紀錄（見 cycle_purchase_audit_service.record_audit），
操作人員沿用這張驗收單的 receiver_name（建立這張驗收單時記錄的驗收人員），
不需要另外傳入 current_user（避免變動這個已經部署測試過的 function 簽章）。
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.cycle_purchase_receiving import CyclePurchaseReceiving, CyclePurchaseReceivingItem
from app.models.cycle_purchase_po import CyclePurchasePO, CyclePurchasePOItem
from app.models.cycle_purchase_vendor import CyclePurchaseVendor
from app.services.cycle_purchase_audit_service import record_audit


class ReceivingServiceError(Exception):
    """給 router 轉成適當 HTTP 錯誤用的一般性例外。"""
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 顯示欄位 / 共用小工具
# ═══════════════════════════════════════════════════════════════════════════

def _attach_receiving_display_fields(db: Session, receiving: CyclePurchaseReceiving) -> CyclePurchaseReceiving:
    po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == receiving.po_id).first()
    receiving.po_no = po.po_no if po else None
    receiving.company = po.company if po else None
    receiving.vendor_name = None
    if po and po.vendor_id:
        vendor = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.id == po.vendor_id).first()
        receiving.vendor_name = vendor.vendor_name if vendor else None
    return receiving


def _next_receiving_no(db: Session, on_date: date) -> str:
    prefix = f"RC-{on_date.strftime('%Y%m')}-"
    count = (
        db.query(func.count(CyclePurchaseReceiving.id))
        .filter(CyclePurchaseReceiving.receiving_no.like(f"{prefix}%"))
        .scalar()
        or 0
    )
    return f"{prefix}{count + 1:04d}"


def _cumulative_received_qty(db: Session, po_item_id: int, exclude_receiving_id: Optional[int] = None) -> int:
    """這個採購明細行，在「已送出」（completed/discrepancy）的驗收單裡累計已驗收數量。
    exclude_receiving_id 用於送出當下重算時排除自己（避免把自己算兩次）。"""
    query = (
        db.query(func.coalesce(func.sum(CyclePurchaseReceivingItem.received_qty), 0))
        .join(CyclePurchaseReceiving, CyclePurchaseReceivingItem.receiving_id == CyclePurchaseReceiving.id)
        .filter(
            CyclePurchaseReceivingItem.po_item_id == po_item_id,
            CyclePurchaseReceiving.status.in_(("completed", "discrepancy")),
        )
    )
    if exclude_receiving_id is not None:
        query = query.filter(CyclePurchaseReceiving.id != exclude_receiving_id)
    return query.scalar() or 0


def _recompute_po_status(db: Session, po_id: int) -> None:
    """驗收單送出後呼叫：依採購單底下每個明細行的累計已驗收數量，重算採購單狀態。"""
    po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == po_id).first()
    if not po or po.status not in ("issued", "partial_received", "received"):
        return  # draft/cancelled 不該走到這裡，防呆略過不處理

    po_items = db.query(CyclePurchasePOItem).filter(CyclePurchasePOItem.po_id == po_id).all()
    if not po_items:
        return

    any_received = False
    all_complete = True
    for item in po_items:
        received = _cumulative_received_qty(db, item.id)
        if received > 0:
            any_received = True
        if received < item.ordered_qty:
            all_complete = False

    if all_complete:
        po.status = "received"
    elif any_received:
        po.status = "partial_received"
    db.flush()


# ═══════════════════════════════════════════════════════════════════════════
# 驗收單 CRUD
# ═══════════════════════════════════════════════════════════════════════════

def create_receiving(db: Session, po_id: int, received_date: date, notes: Optional[str], user) -> CyclePurchaseReceiving:
    po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == po_id).first()
    if not po:
        raise ReceivingServiceError("採購單不存在")
    if po.status not in ("issued", "partial_received"):
        status_label = {
            "draft": "草稿（尚未發出）", "received": "已全部驗收完成", "cancelled": "已取消",
        }.get(po.status, po.status)
        raise ReceivingServiceError(f"這張採購單目前狀態是「{status_label}」，不能建立驗收單")

    receiving = CyclePurchaseReceiving(
        receiving_no=_next_receiving_no(db, date.today()),
        po_id=po_id,
        receiver_user_id=user.id,
        receiver_name=user.full_name,
        received_date=received_date,
        status="draft",
        notes=notes,
    )
    db.add(receiving)
    db.flush()
    return _attach_receiving_display_fields(db, receiving)


def list_receiving(
    db: Session,
    po_id: Optional[int] = None,
    status: Optional[str] = None,
    company: Optional[str] = None,
):
    query = db.query(CyclePurchaseReceiving)
    if po_id is not None:
        query = query.filter(CyclePurchaseReceiving.po_id == po_id)
    if status:
        query = query.filter(CyclePurchaseReceiving.status == status)
    if company:
        query = query.join(CyclePurchasePO, CyclePurchaseReceiving.po_id == CyclePurchasePO.id).filter(
            CyclePurchasePO.company == company
        )
    rows = query.order_by(CyclePurchaseReceiving.receiving_no.desc()).all()
    for r in rows:
        _attach_receiving_display_fields(db, r)
    return rows


def get_receiving(db: Session, receiving_id: int) -> Optional[CyclePurchaseReceiving]:
    """回傳驗收單詳情。CyclePurchaseReceiving model 沒有設定 items relationship
    （比照 PO model 的作法），所以這裡手動查詢明細後掛在物件上的 .items 屬性，
    給 ReceivingDetail schema（from_attributes=True）序列化用。"""
    receiving = db.query(CyclePurchaseReceiving).filter(CyclePurchaseReceiving.id == receiving_id).first()
    if not receiving:
        return None
    _attach_receiving_display_fields(db, receiving)
    receiving.items = (
        db.query(CyclePurchaseReceivingItem)
        .filter(CyclePurchaseReceivingItem.receiving_id == receiving_id)
        .order_by(CyclePurchaseReceivingItem.id)
        .all()
    )
    return receiving


def get_receivable_items(db: Session, receiving_id: int):
    """給「新增驗收單明細」畫面用：這張驗收單所屬採購單的每個明細行，附累計已
    驗收量／剩餘量，以及這張（草稿）驗收單目前已經填的值（若有）。"""
    receiving = db.query(CyclePurchaseReceiving).filter(CyclePurchaseReceiving.id == receiving_id).first()
    if not receiving:
        raise ReceivingServiceError("驗收單不存在")

    po_items = db.query(CyclePurchasePOItem).filter(CyclePurchasePOItem.po_id == receiving.po_id).all()
    existing_by_po_item = {
        ri.po_item_id: ri
        for ri in db.query(CyclePurchaseReceivingItem)
        .filter(CyclePurchaseReceivingItem.receiving_id == receiving_id)
        .all()
    }

    result = []
    for poi in po_items:
        previously = _cumulative_received_qty(db, poi.id, exclude_receiving_id=receiving_id)
        existing = existing_by_po_item.get(poi.id)
        result.append(
            {
                "po_item_id": poi.id,
                "item_id": poi.item_id,
                "item_code": poi.item_code,
                "item_name": poi.item_name,
                "unit": poi.unit,
                "ordered_qty": poi.ordered_qty,
                "previously_received_qty": previously,
                "remaining_qty": poi.ordered_qty - previously,
                "receiving_item_id": existing.id if existing else None,
                "received_qty": existing.received_qty if existing else None,
                "is_final_for_item": existing.is_final_for_item if existing else None,
                "variance_reason": existing.variance_reason if existing else None,
            }
        )
    return result


def upsert_receiving_item(db: Session, receiving_id: int, payload) -> CyclePurchaseReceivingItem:
    receiving = db.query(CyclePurchaseReceiving).filter(CyclePurchaseReceiving.id == receiving_id).first()
    if not receiving:
        raise ReceivingServiceError("驗收單不存在")
    if receiving.status != "draft":
        raise ReceivingServiceError("只有草稿狀態的驗收單可以編輯明細")

    poi = (
        db.query(CyclePurchasePOItem)
        .filter(CyclePurchasePOItem.id == payload.po_item_id, CyclePurchasePOItem.po_id == receiving.po_id)
        .first()
    )
    if not poi:
        raise ReceivingServiceError("這個採購明細行不屬於這張驗收單所屬的採購單")

    previously = _cumulative_received_qty(db, poi.id, exclude_receiving_id=receiving_id)

    existing = (
        db.query(CyclePurchaseReceivingItem)
        .filter(
            CyclePurchaseReceivingItem.receiving_id == receiving_id,
            CyclePurchaseReceivingItem.po_item_id == payload.po_item_id,
        )
        .first()
    )
    if existing:
        existing.received_qty = payload.received_qty
        existing.is_final_for_item = payload.is_final_for_item
        existing.variance_reason = payload.variance_reason
        existing.previously_received_qty = previously
        db.flush()
        return existing

    row = CyclePurchaseReceivingItem(
        receiving_id=receiving_id,
        po_item_id=poi.id,
        item_id=poi.item_id,
        item_code=poi.item_code,
        item_name=poi.item_name,
        unit=poi.unit,
        ordered_qty=poi.ordered_qty,
        previously_received_qty=previously,
        received_qty=payload.received_qty,
        is_final_for_item=payload.is_final_for_item,
        variance_reason=payload.variance_reason,
    )
    db.add(row)
    db.flush()
    return row


def delete_receiving_item(db: Session, receiving_id: int, receiving_item_id: int) -> bool:
    receiving = db.query(CyclePurchaseReceiving).filter(CyclePurchaseReceiving.id == receiving_id).first()
    if not receiving:
        return False
    if receiving.status != "draft":
        raise ReceivingServiceError("只有草稿狀態的驗收單可以刪除明細")

    row = (
        db.query(CyclePurchaseReceivingItem)
        .filter(
            CyclePurchaseReceivingItem.id == receiving_item_id,
            CyclePurchaseReceivingItem.receiving_id == receiving_id,
        )
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.flush()
    return True


def submit_receiving(db: Session, receiving_id: int) -> CyclePurchaseReceiving:
    receiving = db.query(CyclePurchaseReceiving).filter(CyclePurchaseReceiving.id == receiving_id).first()
    if not receiving:
        raise ReceivingServiceError("驗收單不存在")
    if receiving.status != "draft":
        raise ReceivingServiceError("只有草稿狀態的驗收單可以送出")

    items = (
        db.query(CyclePurchaseReceivingItem)
        .filter(CyclePurchaseReceivingItem.receiving_id == receiving_id)
        .all()
    )
    if not items or all((it.received_qty or 0) <= 0 for it in items):
        raise ReceivingServiceError("請至少填寫一筆驗收數量大於 0 的料號才能送出")

    has_variance = False
    for it in items:
        if not it.is_final_for_item:
            continue
        previously = _cumulative_received_qty(db, it.po_item_id, exclude_receiving_id=receiving_id)
        variance = previously + (it.received_qty or 0) - it.ordered_qty
        if variance != 0 and not (it.variance_reason and it.variance_reason.strip()):
            raise ReceivingServiceError(
                f"料號「{it.item_code} {it.item_name}」驗收數量與訂購數量有差異"
                f"（差異 {variance:+d}），送出前必須填寫差異原因"
            )
        it.previously_received_qty = previously
        it.variance_qty = variance
        if variance != 0:
            has_variance = True
            record_audit(
                db,
                document_type="receiving",
                document_id=receiving.id,
                document_no=receiving.receiving_no,
                event_type="receiving_variance",
                description=(
                    f"料號「{it.item_code} {it.item_name}」驗收數量與訂購數量有差異"
                    f"（差異 {variance:+d}）。原因：{it.variance_reason}"
                ),
                operator_name=receiving.receiver_name,
                operator_user_id=receiving.receiver_user_id,
                old_value=str(it.ordered_qty),
                new_value=str(previously + (it.received_qty or 0)),
            )

    receiving.status = "discrepancy" if has_variance else "completed"
    db.flush()

    _recompute_po_status(db, receiving.po_id)
    db.flush()

    return _attach_receiving_display_fields(db, receiving)


# ═══════════════════════════════════════════════════════════════════════════
# 進貨數量報表
# ═══════════════════════════════════════════════════════════════════════════

def get_receiving_report(
    db: Session,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    company: Optional[str] = None,
    vendor_id: Optional[int] = None,
):
    """依月份＋公司＋供應商＋料號彙總已送出（completed/discrepancy）驗收單的驗收數量。
    草稿驗收單不算（還沒確定的數字不該出現在報表上）。"""
    query = (
        db.query(CyclePurchaseReceivingItem, CyclePurchaseReceiving, CyclePurchasePO, CyclePurchasePOItem)
        .join(CyclePurchaseReceiving, CyclePurchaseReceivingItem.receiving_id == CyclePurchaseReceiving.id)
        .join(CyclePurchasePO, CyclePurchaseReceiving.po_id == CyclePurchasePO.id)
        .join(CyclePurchasePOItem, CyclePurchaseReceivingItem.po_item_id == CyclePurchasePOItem.id)
        .filter(CyclePurchaseReceiving.status.in_(("completed", "discrepancy")))
    )
    if date_from:
        query = query.filter(CyclePurchaseReceiving.received_date >= date_from)
    if date_to:
        query = query.filter(CyclePurchaseReceiving.received_date <= date_to)
    if company:
        query = query.filter(CyclePurchasePO.company == company)
    if vendor_id is not None:
        query = query.filter(CyclePurchasePO.vendor_id == vendor_id)

    groups: dict[tuple, dict] = {}
    for ri, r, po, poi in query.all():
        period = r.received_date.strftime("%Y-%m")
        key = (period, po.company, po.vendor_id, ri.item_id)
        g = groups.setdefault(
            key,
            {
                "period": period,
                "company": po.company,
                "vendor_id": po.vendor_id,
                "item_id": ri.item_id,
                "item_code": ri.item_code,
                "item_name": ri.item_name,
                "unit": ri.unit,
                "total_received_qty": 0,
                "total_amount": Decimal("0"),
                "_receiving_ids": set(),
            },
        )
        g["total_received_qty"] += ri.received_qty
        g["total_amount"] += (poi.unit_price or Decimal("0")) * ri.received_qty
        g["_receiving_ids"].add(r.id)

    result = []
    for g in groups.values():
        vendor_name = None
        if g["vendor_id"]:
            vendor = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.id == g["vendor_id"]).first()
            vendor_name = vendor.vendor_name if vendor else None
        row = {k: v for k, v in g.items() if k != "_receiving_ids"}
        row["vendor_name"] = vendor_name
        row["receiving_count"] = len(g["_receiving_ids"])
        result.append(row)

    result.sort(key=lambda r: (r["period"], r["company"], r["vendor_name"] or "", r["item_code"]))
    return result
