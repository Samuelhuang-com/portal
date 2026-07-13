"""
週期採購 — 請款單 Service 層（第五期：請款單＋費用分攤明細＋異常稽核紀錄）

分攤金額怎麼算（建立請款單當下計算一次，之後不再自動變動）：
  對這張採購單的每一個採購明細行，回頭找它的來源彙整列（同週期＋期別＋
  公司＋料號），再找當初彙整進去的全部已核准（approved）請購明細，依
  request.department_id ＋ request.cost_center_id ＋ request_item.account_code_id
  分組加總 request_qty，算出各組的原始請購數量占比，再依這個占比把這個
  採購明細行的小計（subtotal）拆給各組。所有採購明細行的拆分結果，依
  （部門，成本中心，會計科目）合併加總，就是這張請款單的分攤建議
  （suggested_amount）。如果某個採購明細行完全找不回原始請購資料（正常
  情況不會發生，是防呆），整筆小計會歸到 department_id=NULL 那一組，代表
  「系統無法自動歸屬，需要財務人員手動指定」。

  這個試算基礎是「採購金額」（未稅、不含實際發票上的稅金／折讓等），跟
  財務人員輸入的發票金額本來就不一定會完全對上，所以送出時才會另外檢查
  分攤總額是否等於發票金額（見 submit_payment）。
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.cycle_purchase_payment import (
    CyclePurchasePayment, CyclePurchasePaymentReceiving, CyclePurchasePaymentAllocation,
)
from app.models.cycle_purchase_po import CyclePurchasePO, CyclePurchasePOItem
from app.models.cycle_purchase_receiving import CyclePurchaseReceiving, CyclePurchaseReceivingItem
from app.models.cycle_purchase_summary import CyclePurchaseSummary
from app.models.cycle_purchase_request import CyclePurchaseRequest, CyclePurchaseRequestItem
from app.models.cycle_purchase_vendor import CyclePurchaseVendor
from app.models.cycle_purchase_reference import (
    CyclePurchaseDepartment, CyclePurchaseCostCenter, CyclePurchaseAccountCode,
)
from app.services.cycle_purchase_audit_service import record_audit

TWO_PLACES = Decimal("0.01")


class PaymentServiceError(Exception):
    """給 router 轉成適當 HTTP 錯誤用的一般性例外。"""
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 顯示欄位 / 共用小工具
# ═══════════════════════════════════════════════════════════════════════════

def _attach_payment_display_fields(db: Session, payment: CyclePurchasePayment) -> CyclePurchasePayment:
    po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == payment.po_id).first()
    payment.po_no = po.po_no if po else None
    payment.company = po.company if po else None
    payment.vendor_name = None
    if po and po.vendor_id:
        vendor = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.id == po.vendor_id).first()
        payment.vendor_name = vendor.vendor_name if vendor else None

    total = (
        db.query(func.coalesce(func.sum(CyclePurchasePaymentAllocation.allocated_amount), 0))
        .filter(CyclePurchasePaymentAllocation.payment_id == payment.id)
        .scalar()
    )
    payment.total_allocated = total
    return payment


def _attach_allocation_display_fields(db: Session, row: CyclePurchasePaymentAllocation) -> CyclePurchasePaymentAllocation:
    row.department_name = None
    if row.department_id:
        dept = db.query(CyclePurchaseDepartment).filter(CyclePurchaseDepartment.id == row.department_id).first()
        row.department_name = dept.dept_name if dept else None
    row.cost_center_name = None
    if row.cost_center_id:
        cc = db.query(CyclePurchaseCostCenter).filter(CyclePurchaseCostCenter.id == row.cost_center_id).first()
        row.cost_center_name = cc.cc_name if cc else None
    row.account_code_label = None
    if row.account_code_id:
        ac = db.query(CyclePurchaseAccountCode).filter(CyclePurchaseAccountCode.id == row.account_code_id).first()
        row.account_code_label = f"{ac.code} {ac.name}" if ac else None
    return row


def _attach_payment_receiving_display_fields(db: Session, row: CyclePurchasePaymentReceiving) -> CyclePurchasePaymentReceiving:
    r = db.query(CyclePurchaseReceiving).filter(CyclePurchaseReceiving.id == row.receiving_id).first()
    row.receiving_no = r.receiving_no if r else None
    row.received_date = r.received_date if r else None
    row.status = r.status if r else None
    return row


def _next_payment_no(db: Session, on_date: date) -> str:
    prefix = f"PAY-{on_date.strftime('%Y%m')}-"
    count = (
        db.query(func.count(CyclePurchasePayment.id))
        .filter(CyclePurchasePayment.payment_no.like(f"{prefix}%"))
        .scalar()
        or 0
    )
    return f"{prefix}{count + 1:04d}"


def _compute_suggested_allocation(db: Session, po: CyclePurchasePO):
    """回傳 dict：(department_id, cost_center_id, account_code_id) -> Decimal 分攤建議金額"""
    buckets: dict = defaultdict(lambda: Decimal("0"))
    po_items = db.query(CyclePurchasePOItem).filter(CyclePurchasePOItem.po_id == po.id).all()

    for poi in po_items:
        item_subtotal = poi.subtotal or Decimal("0")
        summary = db.query(CyclePurchaseSummary).filter(CyclePurchaseSummary.id == poi.summary_id).first()
        if not summary:
            buckets[(None, None, None)] += item_subtotal
            continue

        rows = (
            db.query(CyclePurchaseRequest, CyclePurchaseRequestItem)
            .join(CyclePurchaseRequestItem, CyclePurchaseRequestItem.request_id == CyclePurchaseRequest.id)
            .filter(
                CyclePurchaseRequest.cycle_id == summary.cycle_id,
                CyclePurchaseRequest.period_label == summary.period_label,
                CyclePurchaseRequest.company == summary.company,
                CyclePurchaseRequestItem.item_id == summary.item_id,
                CyclePurchaseRequest.status == "approved",
            )
            .all()
        )

        dept_qty: dict = defaultdict(int)
        total_qty = 0
        for req, ritem in rows:
            key = (req.department_id, req.cost_center_id, ritem.account_code_id)
            qty = ritem.request_qty or 0
            dept_qty[key] += qty
            total_qty += qty

        if total_qty <= 0:
            # 防呆：找不回原始請購資料，整筆歸到「未歸屬」讓財務人員手動處理
            buckets[(None, None, None)] += item_subtotal
            continue

        keys = list(dept_qty.keys())
        allocated_so_far = Decimal("0")
        for idx, key in enumerate(keys):
            qty = dept_qty[key]
            if idx == len(keys) - 1:
                # 最後一組吃剩下的金額，避免四捨五入造成加總對不起來
                amount = item_subtotal - allocated_so_far
            else:
                amount = (item_subtotal * qty / total_qty).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                allocated_so_far += amount
            buckets[key] += amount

    return buckets


# ═══════════════════════════════════════════════════════════════════════════
# 請款單 CRUD
# ═══════════════════════════════════════════════════════════════════════════

def get_payable_receivings(db: Session, po_id: int):
    """給「建立請款單」畫面用：這張採購單底下還沒被任何請款單涵蓋、且已送出
    （completed／discrepancy）的驗收單，附上估算金額（驗收數量 × 採購單價）。"""
    po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == po_id).first()
    if not po:
        raise PaymentServiceError("採購單不存在")

    unit_price_by_po_item = {
        poi.id: (poi.unit_price or Decimal("0"))
        for poi in db.query(CyclePurchasePOItem).filter(CyclePurchasePOItem.po_id == po_id).all()
    }
    linked_ids = {
        row.receiving_id
        for row in db.query(CyclePurchasePaymentReceiving)
        .join(CyclePurchaseReceiving, CyclePurchasePaymentReceiving.receiving_id == CyclePurchaseReceiving.id)
        .filter(CyclePurchaseReceiving.po_id == po_id)
        .all()
    }

    receivings = (
        db.query(CyclePurchaseReceiving)
        .filter(
            CyclePurchaseReceiving.po_id == po_id,
            CyclePurchaseReceiving.status.in_(("completed", "discrepancy")),
        )
        .order_by(CyclePurchaseReceiving.receiving_no)
        .all()
    )

    result = []
    for r in receivings:
        if r.id in linked_ids:
            continue
        items = (
            db.query(CyclePurchaseReceivingItem)
            .filter(CyclePurchaseReceivingItem.receiving_id == r.id)
            .all()
        )
        amount = sum(
            (it.received_qty or 0) * unit_price_by_po_item.get(it.po_item_id, Decimal("0"))
            for it in items
        ) or Decimal("0")
        result.append({
            "receiving_id": r.id,
            "receiving_no": r.receiving_no,
            "received_date": r.received_date,
            "status": r.status,
            "estimated_amount": amount,
        })
    return result


def create_payment(
    db: Session, po_id: int, receiving_ids: list, invoice_no: str, invoice_date: date,
    invoice_amount: Decimal, notes: Optional[str], user,
) -> CyclePurchasePayment:
    po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == po_id).first()
    if not po:
        raise PaymentServiceError("採購單不存在")
    if not receiving_ids:
        raise PaymentServiceError("請至少選擇一張驗收單才能建立請款單")
    if not invoice_no or not invoice_no.strip():
        raise PaymentServiceError("發票號碼不能是空白")

    unique_ids = list(dict.fromkeys(receiving_ids))  # 去重，保留順序
    receivings = (
        db.query(CyclePurchaseReceiving)
        .filter(CyclePurchaseReceiving.id.in_(unique_ids))
        .all()
    )
    found_ids = {r.id for r in receivings}
    missing = set(unique_ids) - found_ids
    if missing:
        raise PaymentServiceError(f"驗收單不存在：{sorted(missing)}")

    for r in receivings:
        if r.po_id != po_id:
            raise PaymentServiceError(f"驗收單「{r.receiving_no}」不屬於這張採購單，不能一起請款")
        if r.status not in ("completed", "discrepancy"):
            raise PaymentServiceError(f"驗收單「{r.receiving_no}」尚未送出，不能請款")
        existing_link = (
            db.query(CyclePurchasePaymentReceiving, CyclePurchasePayment)
            .join(CyclePurchasePayment, CyclePurchasePaymentReceiving.payment_id == CyclePurchasePayment.id)
            .filter(CyclePurchasePaymentReceiving.receiving_id == r.id)
            .first()
        )
        if existing_link:
            _, existing_payment = existing_link
            raise PaymentServiceError(
                f"驗收單「{r.receiving_no}」已經被請款單「{existing_payment.payment_no}」涵蓋，不能重複請款"
            )

    payment = CyclePurchasePayment(
        payment_no=_next_payment_no(db, date.today()),
        po_id=po_id,
        invoice_no=invoice_no.strip(),
        invoice_date=invoice_date,
        invoice_amount=invoice_amount,
        status="draft",
        processor_user_id=user.id,
        processor_name=user.full_name,
        notes=notes,
    )
    db.add(payment)
    db.flush()

    for r in receivings:
        db.add(CyclePurchasePaymentReceiving(payment_id=payment.id, receiving_id=r.id))
    db.flush()

    buckets = _compute_suggested_allocation(db, po)
    for (dept_id, cc_id, acct_id), amount in buckets.items():
        db.add(CyclePurchasePaymentAllocation(
            payment_id=payment.id,
            company=po.company,
            department_id=dept_id,
            cost_center_id=cc_id,
            account_code_id=acct_id,
            suggested_amount=amount,
            allocated_amount=amount,
        ))
    db.flush()

    return _attach_payment_display_fields(db, payment)


def list_payments(
    db: Session,
    po_id: Optional[int] = None,
    status: Optional[str] = None,
    company: Optional[str] = None,
):
    query = db.query(CyclePurchasePayment)
    if po_id is not None:
        query = query.filter(CyclePurchasePayment.po_id == po_id)
    if status:
        query = query.filter(CyclePurchasePayment.status == status)
    if company:
        query = query.join(CyclePurchasePO, CyclePurchasePayment.po_id == CyclePurchasePO.id).filter(
            CyclePurchasePO.company == company
        )
    rows = query.order_by(CyclePurchasePayment.payment_no.desc()).all()
    for p in rows:
        _attach_payment_display_fields(db, p)
    return rows


def get_payment(db: Session, payment_id: int) -> Optional[CyclePurchasePayment]:
    payment = db.query(CyclePurchasePayment).filter(CyclePurchasePayment.id == payment_id).first()
    if not payment:
        return None
    _attach_payment_display_fields(db, payment)

    allocations = (
        db.query(CyclePurchasePaymentAllocation)
        .filter(CyclePurchasePaymentAllocation.payment_id == payment_id)
        .order_by(CyclePurchasePaymentAllocation.id)
        .all()
    )
    for a in allocations:
        _attach_allocation_display_fields(db, a)
    payment.allocations = allocations

    receivings = (
        db.query(CyclePurchasePaymentReceiving)
        .filter(CyclePurchasePaymentReceiving.payment_id == payment_id)
        .order_by(CyclePurchasePaymentReceiving.id)
        .all()
    )
    for pr in receivings:
        _attach_payment_receiving_display_fields(db, pr)
    payment.receivings = receivings

    return payment


def update_payment(db: Session, payment_id: int, payload) -> Optional[CyclePurchasePayment]:
    payment = db.query(CyclePurchasePayment).filter(CyclePurchasePayment.id == payment_id).first()
    if not payment:
        return None
    if payment.status != "draft":
        raise PaymentServiceError("只有草稿狀態的請款單可以編輯發票資訊")

    if payload.invoice_no is not None:
        if not payload.invoice_no.strip():
            raise PaymentServiceError("發票號碼不能是空白")
        payment.invoice_no = payload.invoice_no.strip()
    if payload.invoice_date is not None:
        payment.invoice_date = payload.invoice_date
    if payload.invoice_amount is not None:
        payment.invoice_amount = payload.invoice_amount
    if payload.notes is not None:
        payment.notes = payload.notes
    if payload.amount_diff_reason is not None:
        payment.amount_diff_reason = payload.amount_diff_reason

    db.flush()
    return _attach_payment_display_fields(db, payment)


def update_allocation_item(db: Session, payment_id: int, allocation_id: int, payload) -> CyclePurchasePaymentAllocation:
    payment = db.query(CyclePurchasePayment).filter(CyclePurchasePayment.id == payment_id).first()
    if not payment:
        raise PaymentServiceError("請款單不存在")
    if payment.status != "draft":
        raise PaymentServiceError("只有草稿狀態的請款單可以調整分攤明細")

    row = (
        db.query(CyclePurchasePaymentAllocation)
        .filter(
            CyclePurchasePaymentAllocation.id == allocation_id,
            CyclePurchasePaymentAllocation.payment_id == payment_id,
        )
        .first()
    )
    if not row:
        raise PaymentServiceError("分攤明細列不存在")

    if payload.allocated_amount != row.suggested_amount and not (payload.adjust_reason and payload.adjust_reason.strip()):
        raise PaymentServiceError("分攤金額與系統試算值不同時，必須填寫調整原因")

    row.allocated_amount = payload.allocated_amount
    row.adjust_reason = payload.adjust_reason
    db.flush()
    return _attach_allocation_display_fields(db, row)


def submit_payment(db: Session, payment_id: int) -> CyclePurchasePayment:
    payment = db.query(CyclePurchasePayment).filter(CyclePurchasePayment.id == payment_id).first()
    if not payment:
        raise PaymentServiceError("請款單不存在")
    if payment.status != "draft":
        raise PaymentServiceError("只有草稿狀態的請款單可以送出")

    allocations = (
        db.query(CyclePurchasePaymentAllocation)
        .filter(CyclePurchasePaymentAllocation.payment_id == payment_id)
        .all()
    )
    if not allocations:
        raise PaymentServiceError("沒有分攤明細，無法送出")

    total_allocated = sum((a.allocated_amount or Decimal("0")) for a in allocations)
    diff = total_allocated - payment.invoice_amount
    if diff != 0:
        if not (payment.amount_diff_reason and payment.amount_diff_reason.strip()):
            raise PaymentServiceError(
                f"分攤金額加總（{total_allocated}）與發票金額（{payment.invoice_amount}）不符"
                f"（差異 {diff:+}），送出前必須填寫差異原因"
            )
        record_audit(
            db,
            document_type="payment",
            document_id=payment.id,
            document_no=payment.payment_no,
            event_type="payment_variance",
            description=(
                f"請款單分攤總額 {total_allocated} 與發票金額 {payment.invoice_amount} 不符"
                f"（差異 {diff:+}）。原因：{payment.amount_diff_reason}"
            ),
            operator_name=payment.processor_name,
            operator_user_id=payment.processor_user_id,
            old_value=str(payment.invoice_amount),
            new_value=str(total_allocated),
        )

    payment.status = "submitted"
    db.flush()
    return _attach_payment_display_fields(db, payment)


def set_payment_status(db: Session, payment_id: int, status: str) -> CyclePurchasePayment:
    payment = db.query(CyclePurchasePayment).filter(CyclePurchasePayment.id == payment_id).first()
    if not payment:
        raise PaymentServiceError("請款單不存在")

    transitions = {"submitted": "paying", "paying": "paid"}
    if status not in ("paying", "paid"):
        raise PaymentServiceError(f"不支援的狀態：{status}")
    expected_next = transitions.get(payment.status)
    if expected_next != status:
        status_label = {
            "draft": "草稿（尚未送出）", "submitted": "已送出", "paying": "付款中", "paid": "已付款",
        }.get(payment.status, payment.status)
        raise PaymentServiceError(f"請款單目前狀態是「{status_label}」，不能直接變更為「{status}」")

    payment.status = status
    db.flush()
    return _attach_payment_display_fields(db, payment)
