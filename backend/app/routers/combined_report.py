"""
請購單 + 請款單 整合總表 API Router（方案 B：後端合併端點）

端點：
  GET /api/v1/combined-report/orders   — 請購 + 請款 合併清單（分頁）
  GET /api/v1/combined-report/summary  — 請購 + 請款 合計 KPI
  GET /api/v1/combined-report/departments — 部門雙色統計（請購/請款並排）

設計：
  - 每列加入 source_type: "purchase" | "claim" 欄位，前端以此決定顏色
  - 金額統一映射：purchase.amount → amount_field；claim.payable_amount → amount_field
  - 兩者共用篩選：year_month / company / department
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_permission
from app.models.purchase_request import ApprovedPurchaseRequest
from app.models.claim_request import ApprovedClaimRequest

router = APIRouter()

_PERM = "system_admin_only"


# ── 工具函式 ──────────────────────────────────────────────────────────────────

def _purchase_date_filter(
    q,
    year_month: Optional[str] = None,
    year_month_from: Optional[str] = None,
    year_month_to: Optional[str] = None,
):
    q = q.filter(ApprovedPurchaseRequest.status == "F")
    ym_col = func.strftime("%Y-%m", ApprovedPurchaseRequest.approved_date)
    if year_month_from and year_month_to:
        q = q.filter(ym_col >= year_month_from, ym_col <= year_month_to)
    elif year_month_from:
        q = q.filter(ym_col >= year_month_from)
    elif year_month:
        q = q.filter(ym_col == year_month)
    return q


def _claim_date_filter(
    q,
    year_month: Optional[str] = None,
    year_month_from: Optional[str] = None,
    year_month_to: Optional[str] = None,
):
    q = q.filter(ApprovedClaimRequest.status == "F")
    ym_col = func.strftime("%Y-%m", ApprovedClaimRequest.approved_date)
    if year_month_from and year_month_to:
        q = q.filter(ym_col >= year_month_from, ym_col <= year_month_to)
    elif year_month_from:
        q = q.filter(ym_col >= year_month_from)
    elif year_month:
        q = q.filter(ym_col == year_month)
    return q


def _date_label(
    year_month: Optional[str] = None,
    year_month_from: Optional[str] = None,
    year_month_to: Optional[str] = None,
) -> str:
    if year_month_from and year_month_to:
        if (
            year_month_from.endswith("-01")
            and year_month_to.endswith("-12")
            and year_month_from[:4] == year_month_to[:4]
        ):
            return f"{year_month_from[:4]}年度"
        return f"{year_month_from}~{year_month_to}"
    return year_month or ""


def _purchase_to_row(o: ApprovedPurchaseRequest) -> dict:
    return {
        "source_type":        "purchase",
        "id":                 o.id,
        "department_display": o.department_display,
        "doc_no":             o.purchase_no,         # 單號（請購）
        "account_label":      o.account_category,    # 會科
        "apply_date":         o.request_date.isoformat() if o.request_date else None,
        "approved_date":      o.approved_date.isoformat() if o.approved_date else None,
        "applicant":          o.applicant,
        "description":        o.description,
        "amount":             o.amount,              # 全案小計（未稅）
        "tax":                o.amount_tax,
        "total":              o.amount_total,
        "payable_amount":     o.amount_total,        # purchase 無 payable_amount，以 total 代替
        "payment_type":       None,
        "payee":              None,
        "status":             o.status,
        "detail_synced":      o.detail_synced,
        "last_updated_at":    o.last_updated_at.isoformat() if o.last_updated_at else None,
    }


def _claim_to_row(o: ApprovedClaimRequest) -> dict:
    return {
        "source_type":        "claim",
        "id":                 o.id,
        "department_display": o.department_display,
        "doc_no":             o.request_no,          # 單號（請款）
        "account_label":      o.account_subject,     # 會科
        "apply_date":         o.apply_date.isoformat() if o.apply_date else None,
        "approved_date":      o.approved_date.isoformat() if o.approved_date else None,
        "applicant":          o.applicant,
        "description":        o.purpose_description,
        "amount":             o.subtotal,            # 未稅
        "tax":                o.tax,
        "total":              o.total,
        "payable_amount":     o.payable_amount,
        "payment_type":       o.payment_type,
        "payee":              o.payee,
        "status":             o.status,
        "detail_synced":      o.detail_synced,
        "last_updated_at":    o.last_updated_at.isoformat() if o.last_updated_at else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /orders — 請購 + 請款 合併清單（分頁）
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/orders")
def get_combined_orders(
    year_month:      Optional[str] = Query(None,  description="YYYY-MM"),
    year_month_from: Optional[str] = Query(None,  description="YYYY-MM 區間起"),
    year_month_to:   Optional[str] = Query(None,  description="YYYY-MM 區間迄"),
    company:         str           = Query("樂群"),
    department:      Optional[str] = Query(None),
    source_type:     Optional[str] = Query(None,  description="purchase | claim | None=全部"),
    keyword:         Optional[str] = Query(None),
    page:            int           = Query(1, ge=1),
    per_page:        int           = Query(20, ge=1, le=200),
    db:              Session       = Depends(get_db),
    _:               object        = Depends(require_permission(_PERM)),
):
    purchase_rows: list[dict] = []
    claim_rows:    list[dict] = []

    if source_type in (None, "purchase"):
        pq = db.query(ApprovedPurchaseRequest).filter(ApprovedPurchaseRequest.company == company)
        pq = _purchase_date_filter(pq, year_month, year_month_from, year_month_to)
        if department:
            pq = pq.filter(ApprovedPurchaseRequest.department_display == department)
        if keyword:
            like = f"%{keyword}%"
            pq = pq.filter(
                ApprovedPurchaseRequest.description.ilike(like)
                | ApprovedPurchaseRequest.purchase_no.ilike(like)
                | ApprovedPurchaseRequest.applicant.ilike(like)
            )
        purchase_rows = [_purchase_to_row(o) for o in pq.all()]

    if source_type in (None, "claim"):
        cq = db.query(ApprovedClaimRequest).filter(ApprovedClaimRequest.company == company)
        cq = _claim_date_filter(cq, year_month, year_month_from, year_month_to)
        if department:
            cq = cq.filter(ApprovedClaimRequest.department_display == department)
        if keyword:
            like = f"%{keyword}%"
            cq = cq.filter(
                ApprovedClaimRequest.purpose_description.ilike(like)
                | ApprovedClaimRequest.request_no.ilike(like)
                | ApprovedClaimRequest.applicant.ilike(like)
            )
        claim_rows = [_claim_to_row(o) for o in cq.all()]

    # 合併並依 approved_date 降冪排序
    all_rows = purchase_rows + claim_rows
    all_rows.sort(key=lambda r: (r["approved_date"] or ""), reverse=True)

    total = len(all_rows)
    start = (page - 1) * per_page
    page_rows = all_rows[start: start + per_page]

    return {
        "total":          total,
        "page":           page,
        "per_page":       per_page,
        "purchase_count": len(purchase_rows),
        "claim_count":    len(claim_rows),
        "items":          page_rows,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /summary — 合計 KPI
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/summary")
def get_combined_summary(
    year_month:      Optional[str] = Query(None),
    year_month_from: Optional[str] = Query(None, description="YYYY-MM 區間起"),
    year_month_to:   Optional[str] = Query(None, description="YYYY-MM 區間迄"),
    company:         str           = Query("樂群"),
    department:      Optional[str] = Query(None),
    db:              Session       = Depends(get_db),
    _:               object        = Depends(require_permission(_PERM)),
):
    label = _date_label(year_month, year_month_from, year_month_to)

    # 請購 KPI
    pq = db.query(ApprovedPurchaseRequest).filter(ApprovedPurchaseRequest.company == company)
    pq = _purchase_date_filter(pq, year_month, year_month_from, year_month_to)
    if department:
        pq = pq.filter(ApprovedPurchaseRequest.department_display == department)
    purchase_orders = pq.all()

    purchase_total    = sum(o.amount or 0 for o in purchase_orders)
    purchase_tax      = sum(o.amount_tax or 0 for o in purchase_orders)
    purchase_count    = len(purchase_orders)

    # 請款 KPI
    cq = db.query(ApprovedClaimRequest).filter(ApprovedClaimRequest.company == company)
    cq = _claim_date_filter(cq, year_month, year_month_from, year_month_to)
    if department:
        cq = cq.filter(ApprovedClaimRequest.department_display == department)
    claim_orders = cq.all()

    claim_total   = sum(o.payable_amount or 0 for o in claim_orders)
    claim_tax     = sum(o.tax or 0 for o in claim_orders)
    claim_count   = len(claim_orders)

    return {
        "label":           label,
        "year_month":      year_month,
        "purchase": {
            "order_count":   purchase_count,
            "total_amount":  purchase_total,
            "total_tax":     purchase_tax,
        },
        "claim": {
            "order_count":  claim_count,
            "total_payable": claim_total,
            "total_tax":    claim_tax,
        },
        "combined": {
            "order_count":   purchase_count + claim_count,
            "total_amount":  purchase_total + claim_total,
            "total_tax":     purchase_tax + claim_tax,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /departments — 部門雙色統計（請購 / 請款 並排）
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/departments")
def get_combined_departments(
    year_month:      Optional[str] = Query(None),
    year_month_from: Optional[str] = Query(None, description="YYYY-MM 區間起"),
    year_month_to:   Optional[str] = Query(None, description="YYYY-MM 區間迄"),
    company:         str           = Query("樂群"),
    db:              Session       = Depends(get_db),
    _:               object        = Depends(require_permission(_PERM)),
):
    # 請購部門統計
    pq = (
        db.query(
            ApprovedPurchaseRequest.department_display,
            func.count(ApprovedPurchaseRequest.id).label("p_count"),
            func.sum(ApprovedPurchaseRequest.amount).label("p_amount"),
            func.sum(ApprovedPurchaseRequest.amount_tax).label("p_tax"),
        )
        .filter(ApprovedPurchaseRequest.company == company)
    )
    pq = _purchase_date_filter(pq, year_month, year_month_from, year_month_to)
    p_rows = pq.group_by(ApprovedPurchaseRequest.department_display).all()
    p_dict = {r.department_display: r for r in p_rows}

    # 請款部門統計
    cq = (
        db.query(
            ApprovedClaimRequest.department_display,
            func.count(ApprovedClaimRequest.id).label("c_count"),
            func.sum(ApprovedClaimRequest.payable_amount).label("c_payable"),
            func.sum(ApprovedClaimRequest.tax).label("c_tax"),
        )
        .filter(ApprovedClaimRequest.company == company)
    )
    cq = _claim_date_filter(cq, year_month, year_month_from, year_month_to)
    c_rows = cq.group_by(ApprovedClaimRequest.department_display).all()
    c_dict = {r.department_display: r for r in c_rows}

    # 合併所有部門
    all_depts = sorted(set(list(p_dict.keys()) + list(c_dict.keys())))

    return [
        {
            "department_display": dept,
            # 請購欄（藍色）
            "purchase_count":   p_dict[dept].p_count  if dept in p_dict else 0,
            "purchase_amount":  int(p_dict[dept].p_amount or 0) if dept in p_dict else 0,
            "purchase_tax":     int(p_dict[dept].p_tax or 0)    if dept in p_dict else 0,
            # 請款欄（橙色）
            "claim_count":      c_dict[dept].c_count  if dept in c_dict else 0,
            "claim_payable":    int(c_dict[dept].c_payable or 0) if dept in c_dict else 0,
            "claim_tax":        int(c_dict[dept].c_tax or 0)    if dept in c_dict else 0,
        }
        for dept in all_depts
    ]
