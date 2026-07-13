"""
週期採購 — 彙整單 Service 層（第三期：彙整＋轉採購單）

2026-07-11（與 Samuel 確認之設計，見 models/cycle_purchase_summary.py 開頭說明）：
  - 「產生彙整」只彙總 status == approved 的請購單明細（草稿／已送出／已退回
    一律不算）。同一 cycle_id+period_label+company+item_id 冪等：已經存在的
    彙整列不會被覆寫，只會新增這次才第一次出現的組合。
  - 彙整列的供應商一律來自料號對照表（cycle_purchase_item_mappings）的
    vendor_id，不是料號主檔的 default_vendor_id（見 models/cycle_purchase_item.py
    開頭說明，兩公司合併料號的 default_vendor_id 只會記到單一公司）。
  - 「轉採購單」＝一個公司＋一個供應商（同一週期＋期別內）合成一張採購單。
    只有 status=="draft" 的彙整列才能被轉單；調整量 > 0 的列變成採購明細，
    調整量 == 0 的列（代表「本期決定不訂這個料號」）一併鎖定為 converted、
    回填 po_id，但不會出現在採購明細裡。若這個公司＋供應商在本期完全沒有
    調整量 > 0 的列，不建立採購單（避免產生空的採購單）。
    轉單前會先驗證好所有條件（是否已經轉過、是否有可訂購的列）才動手，
    不會先建立採購單再中途失敗留下半殘資料。
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.cycle_purchase_summary import CyclePurchaseSummary
from app.models.cycle_purchase_po import CyclePurchasePO, CyclePurchasePOItem
from app.models.cycle_purchase_cycle import CyclePurchaseCycle
from app.models.cycle_purchase_vendor import CyclePurchaseVendor
from app.models.cycle_purchase_item import CyclePurchaseItem, CyclePurchaseItemMapping
from app.models.cycle_purchase_request import CyclePurchaseRequest, CyclePurchaseRequestItem


class SummaryServiceError(Exception):
    """給 router 轉成適當 HTTP 錯誤用的一般性例外。"""
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 顯示欄位
# ═══════════════════════════════════════════════════════════════════════════

def _attach_summary_display_fields(db: Session, row: CyclePurchaseSummary) -> CyclePurchaseSummary:
    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == row.cycle_id).first()
    row.cycle_name = cycle.cycle_name if cycle else None

    row.vendor_name = None
    if row.vendor_id:
        vendor = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.id == row.vendor_id).first()
        if vendor:
            row.vendor_name = vendor.vendor_name

    row.po_no = None
    if row.po_id:
        po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == row.po_id).first()
        if po:
            row.po_no = po.po_no
    return row


# ═══════════════════════════════════════════════════════════════════════════
# 產生彙整
# ═══════════════════════════════════════════════════════════════════════════

def generate_summary(db: Session, cycle_id: int, period_label: str) -> list[CyclePurchaseSummary]:
    period_label = (period_label or "").strip()
    if not period_label:
        raise SummaryServiceError("期別標籤不能是空白")

    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == cycle_id).first()
    if not cycle:
        raise SummaryServiceError("週期設定不存在")

    rows = (
        db.query(CyclePurchaseRequest, CyclePurchaseRequestItem)
        .join(CyclePurchaseRequestItem, CyclePurchaseRequestItem.request_id == CyclePurchaseRequest.id)
        .filter(
            CyclePurchaseRequest.cycle_id == cycle_id,
            CyclePurchaseRequest.period_label == period_label,
            CyclePurchaseRequest.status == "approved",
        )
        .all()
    )
    if not rows:
        raise SummaryServiceError("這個週期＋期別目前沒有已核准（approved）的請購單，沒有東西可以彙整")

    demand_by_key: dict[tuple[str, int], int] = {}
    for req, item in rows:
        key = (req.company, item.item_id)
        demand_by_key[key] = demand_by_key.get(key, 0) + (item.request_qty or 0)

    result = []
    for (company, item_id), demand_qty in demand_by_key.items():
        if demand_qty <= 0:
            continue

        existing = (
            db.query(CyclePurchaseSummary)
            .filter(
                CyclePurchaseSummary.cycle_id == cycle_id,
                CyclePurchaseSummary.period_label == period_label,
                CyclePurchaseSummary.company == company,
                CyclePurchaseSummary.item_id == item_id,
            )
            .first()
        )
        if existing:
            result.append(existing)
            continue

        item_obj = db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id == item_id).first()
        if not item_obj:
            continue

        mapping = (
            db.query(CyclePurchaseItemMapping)
            .filter(
                CyclePurchaseItemMapping.item_id == item_id,
                CyclePurchaseItemMapping.company == company,
            )
            .first()
        )

        summary = CyclePurchaseSummary(
            cycle_id=cycle_id,
            period_label=period_label,
            company=company,
            item_id=item_id,
            item_mapping_id=mapping.id if mapping else None,
            vendor_id=mapping.vendor_id if mapping else None,
            item_code=item_obj.item_code,
            item_name=item_obj.item_name,
            unit=item_obj.unit,
            unit_price=mapping.original_unit_price if mapping else item_obj.unit_price,
            demand_qty=demand_qty,
            adjusted_qty=demand_qty,
            adjust_reason=None,
            status="draft",
        )
        db.add(summary)
        db.flush()
        result.append(summary)

    for r in result:
        _attach_summary_display_fields(db, r)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# 彙整單查詢 / 調整
# ═══════════════════════════════════════════════════════════════════════════

def list_summary(
    db: Session,
    cycle_id: Optional[int] = None,
    period_label: Optional[str] = None,
    company: Optional[str] = None,
    vendor_id: Optional[int] = None,
    status: Optional[str] = None,
):
    query = db.query(CyclePurchaseSummary)
    if cycle_id is not None:
        query = query.filter(CyclePurchaseSummary.cycle_id == cycle_id)
    if period_label:
        query = query.filter(CyclePurchaseSummary.period_label == period_label)
    if company:
        query = query.filter(CyclePurchaseSummary.company == company)
    if vendor_id is not None:
        query = query.filter(CyclePurchaseSummary.vendor_id == vendor_id)
    if status:
        query = query.filter(CyclePurchaseSummary.status == status)
    rows = query.order_by(CyclePurchaseSummary.company, CyclePurchaseSummary.item_code).all()
    for r in rows:
        _attach_summary_display_fields(db, r)
    return rows


def get_summary(db: Session, summary_id: int) -> Optional[CyclePurchaseSummary]:
    row = db.query(CyclePurchaseSummary).filter(CyclePurchaseSummary.id == summary_id).first()
    if row:
        _attach_summary_display_fields(db, row)
    return row


def update_summary_item(db: Session, summary_id: int, payload) -> Optional[CyclePurchaseSummary]:
    row = db.query(CyclePurchaseSummary).filter(CyclePurchaseSummary.id == summary_id).first()
    if not row:
        return None
    if row.status != "draft":
        raise SummaryServiceError("只有草稿狀態的彙整列可以調整（已轉採購單的列不能再改）")

    data = payload.model_dump(exclude_unset=True)
    new_adjusted = data.get("adjusted_qty", row.adjusted_qty)
    new_reason = data.get("adjust_reason", row.adjust_reason)
    if (new_adjusted or 0) != row.demand_qty and not (new_reason and new_reason.strip()):
        raise SummaryServiceError("調整量與需求總量不同時，必須填寫調整原因")

    if "adjusted_qty" in data:
        row.adjusted_qty = data["adjusted_qty"] or 0
    if "adjust_reason" in data:
        row.adjust_reason = data["adjust_reason"]
    db.flush()
    return _attach_summary_display_fields(db, row)


def list_vendor_groups(db: Session, cycle_id: int, period_label: str, company: Optional[str] = None):
    """給「轉採購單」畫面用：某週期＋期別下還沒轉單（draft）的彙整列，依公司＋供應商分組統計。"""
    query = db.query(CyclePurchaseSummary).filter(
        CyclePurchaseSummary.cycle_id == cycle_id,
        CyclePurchaseSummary.period_label == period_label,
        CyclePurchaseSummary.status == "draft",
    )
    if company:
        query = query.filter(CyclePurchaseSummary.company == company)
    rows = query.all()

    groups: dict[tuple[str, Optional[int]], dict] = {}
    for r in rows:
        key = (r.company, r.vendor_id)
        g = groups.setdefault(
            key,
            {
                "company": r.company,
                "vendor_id": r.vendor_id,
                "vendor_name": None,
                "item_count": 0,
                "total_amount": Decimal("0"),
                "has_missing_vendor": r.vendor_id is None,
            },
        )
        g["item_count"] += 1
        g["total_amount"] += (r.unit_price or Decimal("0")) * (r.adjusted_qty or 0)

    result = []
    for (company_, vendor_id_), g in groups.items():
        if vendor_id_:
            vendor = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.id == vendor_id_).first()
            g["vendor_name"] = vendor.vendor_name if vendor else None
        result.append(g)
    result.sort(key=lambda g: (g["company"], g["vendor_name"] or ""))
    return result


# ═══════════════════════════════════════════════════════════════════════════
# 轉採購單
# ═══════════════════════════════════════════════════════════════════════════

def _next_po_no(db: Session, on_date: date) -> str:
    prefix = f"PO-{on_date.strftime('%Y%m')}-"
    count = (
        db.query(func.count(CyclePurchasePO.id))
        .filter(CyclePurchasePO.po_no.like(f"{prefix}%"))
        .scalar()
        or 0
    )
    return f"{prefix}{count + 1:04d}"


def convert_to_po(
    db: Session, cycle_id: int, period_label: str, company: str, vendor_id: int, user
) -> CyclePurchasePO:
    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == cycle_id).first()
    if not cycle:
        raise SummaryServiceError("週期設定不存在")
    vendor = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.id == vendor_id).first()
    if not vendor:
        raise SummaryServiceError("供應商不存在")

    existing_po = (
        db.query(CyclePurchasePO)
        .filter(
            CyclePurchasePO.cycle_id == cycle_id,
            CyclePurchasePO.period_label == period_label,
            CyclePurchasePO.company == company,
            CyclePurchasePO.vendor_id == vendor_id,
        )
        .first()
    )
    if existing_po:
        raise SummaryServiceError(
            f"「{cycle.cycle_name}／{period_label}／{company}／{vendor.vendor_name}」"
            f"已經有一張採購單（{existing_po.po_no}），不能重複轉單"
        )

    matched = (
        db.query(CyclePurchaseSummary)
        .filter(
            CyclePurchaseSummary.cycle_id == cycle_id,
            CyclePurchaseSummary.period_label == period_label,
            CyclePurchaseSummary.company == company,
            CyclePurchaseSummary.vendor_id == vendor_id,
            CyclePurchaseSummary.status == "draft",
        )
        .all()
    )
    if not matched:
        raise SummaryServiceError(
            "沒有符合條件、狀態為草稿的彙整列可以轉單，"
            "請確認週期／期別／公司／供應商是否正確，或是否已經轉過單"
        )

    orderable = [r for r in matched if (r.adjusted_qty or 0) > 0]
    zero_rows = [r for r in matched if not (r.adjusted_qty or 0) > 0]
    if not orderable:
        raise SummaryServiceError("此供應商本期沒有調整量大於 0 的彙整列，不需要轉採購單")

    total_amount = sum((r.unit_price or Decimal("0")) * r.adjusted_qty for r in orderable)

    po = CyclePurchasePO(
        po_no=_next_po_no(db, date.today()),
        cycle_id=cycle_id,
        period_label=period_label,
        company=company,
        vendor_id=vendor_id,
        buyer_user_id=user.id,
        buyer_name=user.full_name,
        total_amount=total_amount,
        status="draft",
    )
    db.add(po)
    db.flush()

    for r in orderable:
        po_item = CyclePurchasePOItem(
            po_id=po.id,
            summary_id=r.id,
            item_id=r.item_id,
            item_code=r.item_code,
            item_name=r.item_name,
            unit=r.unit,
            unit_price=r.unit_price,
            ordered_qty=r.adjusted_qty,
            subtotal=(r.unit_price or Decimal("0")) * r.adjusted_qty,
        )
        db.add(po_item)
        r.status = "converted"
        r.po_id = po.id

    for r in zero_rows:
        r.status = "converted"
        r.po_id = po.id

    db.flush()
    return po
