"""
台中核准請購單／請款單 資料異常稽核服務（2026-09-16 完整複製自樂群 audit_service.py 的樂群段落）

規則與樂群相同（R01~R08），唯一差異：

  R08 同單號重複 —— 改成「同一個部門表單內」重複才算（使用者 2026-09-16 裁示）。
     台中各部門的單號在 Ragic 各自流水，跨部門同號是正常現象
     （實測：請購 121 張中 38 個單號跨部門重複、請款 173 張中 65 個），
     照樂群規則會把它們全部標成高風險異常。

公開函式（簽名同樂群）：
  get_anomalies(db, source, ..., page, per_page)   → 分頁異常列表
  get_audit_summary(db, source, ...)               → 各規則計數 KPI
"""
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dialect_compat import year_month as ym_expr
from app.models.taichung_purchase_request import (
    TaichungPurchaseRequest as ApprovedPurchaseRequest,
    TaichungPurchaseRequestItem as ApprovedPurchaseRequestItem,
    TAICHUNG_DEPT_SHEETS as DEPT_SHEETS,
)
from app.models.taichung_claim_request import (
    TaichungClaimRequest as ApprovedClaimRequest,
    TaichungClaimRequestItem as ApprovedClaimRequestItem,
    TAICHUNG_CLAIM_DEPT_SHEETS as CLAIM_DEPT_SHEETS,
)

# ── 規則定義 ───────────────────────────────────────────────────────────────────

RULE_META: dict[str, dict] = {
    "R01": {"name": "單號空白",        "severity": "high",   "applies_to": ["purchase", "claim"]},
    "R02": {"name": "部門空白",        "severity": "high",   "applies_to": ["purchase", "claim"]},
    "R03": {"name": "金額異常",        "severity": "high",   "applies_to": ["purchase", "claim"]},
    "R04": {"name": "品項加總不符",    "severity": "medium", "applies_to": ["purchase"]},
    "R05": {"name": "會科空白",        "severity": "medium", "applies_to": ["purchase", "claim"]},
    "R06": {"name": "付款種類空白",    "severity": "medium", "applies_to": ["claim"]},
    "R07": {"name": "Detail 未同步",   "severity": "low",    "applies_to": ["purchase", "claim"]},
    "R08": {"name": "同部門同單號重複", "severity": "high",   "applies_to": ["purchase", "claim"]},
}

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


# ── Ragic URL 輔助 ─────────────────────────────────────────────────────────────

def _purchase_ragic_url(order: ApprovedPurchaseRequest) -> str:
    """使用 list_path（記錄所在 Sheet）建構 Ragic 連結，非 detail_path（API 用）。"""
    for d in DEPT_SHEETS:
        if d["list_path"] == order.ragic_sheet_path:
            return f"https://ap12.ragic.com/soutlet001/{d['list_path']}/{order.ragic_record_id}"
    return ""


def _claim_ragic_url(order: ApprovedClaimRequest) -> str:
    """使用 list_path（記錄所在 Sheet）建構 Ragic 連結，非 detail_path（API 用）。"""
    for d in CLAIM_DEPT_SHEETS:
        if d["list_path"] == order.ragic_sheet_path:
            return f"https://ap12.ragic.com/soutlet001/{d['list_path']}/{order.ragic_record_id}"
    return ""


# ── 基礎查詢建構 ───────────────────────────────────────────────────────────────

def _purchase_base_q(
    db: Session,
    year_month: Optional[str] = None,
    year_month_from: Optional[str] = None,
    year_month_to: Optional[str] = None,
    department: Optional[str] = None,
    company: Optional[str] = None,
):
    q = db.query(ApprovedPurchaseRequest).filter(ApprovedPurchaseRequest.status == "F")
    ym_col = ym_expr(ApprovedPurchaseRequest.approved_date)
    if year_month_from and year_month_to:
        q = q.filter(ym_col >= year_month_from, ym_col <= year_month_to)
    elif year_month_from:
        q = q.filter(ym_col >= year_month_from)
    elif year_month:
        q = q.filter(ym_col == year_month)
    if department:
        q = q.filter(ApprovedPurchaseRequest.department_display == department)
    if company:
        q = q.filter(ApprovedPurchaseRequest.company == company)
    return q


def _claim_base_q(
    db: Session,
    year_month: Optional[str] = None,
    year_month_from: Optional[str] = None,
    year_month_to: Optional[str] = None,
    department: Optional[str] = None,
    company: Optional[str] = None,
):
    q = db.query(ApprovedClaimRequest).filter(ApprovedClaimRequest.status == "F")
    ym_col = ym_expr(ApprovedClaimRequest.approved_date)
    if year_month_from and year_month_to:
        q = q.filter(ym_col >= year_month_from, ym_col <= year_month_to)
    elif year_month_from:
        q = q.filter(ym_col >= year_month_from)
    elif year_month:
        q = q.filter(ym_col == year_month)
    if department:
        q = q.filter(ApprovedClaimRequest.department_display == department)
    if company:
        q = q.filter(ApprovedClaimRequest.company == company)
    return q


# ── 異常記錄建構輔助 ───────────────────────────────────────────────────────────

def _p_rec(order: ApprovedPurchaseRequest, rule_code: str, detail: str) -> dict:
    return {
        "source":        "purchase",
        "order_id":      order.id,
        "doc_no":        order.purchase_no or "",
        "department":    order.department_display or "",
        "approved_date": order.approved_date.isoformat() if order.approved_date else None,
        "rule_code":     rule_code,
        "rule_name":     RULE_META[rule_code]["name"],
        "severity":      RULE_META[rule_code]["severity"],
        "detail":        detail,
        "ragic_url":     _purchase_ragic_url(order),
    }


def _c_rec(order: ApprovedClaimRequest, rule_code: str, detail: str) -> dict:
    return {
        "source":        "claim",
        "order_id":      order.id,
        "doc_no":        order.request_no or "",
        "department":    order.department_display or "",
        "approved_date": order.approved_date.isoformat() if order.approved_date else None,
        "rule_code":     rule_code,
        "rule_name":     RULE_META[rule_code]["name"],
        "severity":      RULE_META[rule_code]["severity"],
        "detail":        detail,
        "ragic_url":     _claim_ragic_url(order),
    }


# ── 請購稽核規則 ───────────────────────────────────────────────────────────────

def _check_purchase(db: Session, base_q) -> list[dict]:
    results: list[dict] = []

    # R01 單號空白
    for o in base_q.filter(
        (ApprovedPurchaseRequest.purchase_no == None)  # noqa: E711
        | (ApprovedPurchaseRequest.purchase_no == "")
    ).all():
        results.append(_p_rec(o, "R01", "purchase_no 為空白"))

    # R02 部門空白
    for o in base_q.filter(
        (ApprovedPurchaseRequest.department_display == None)  # noqa: E711
        | (ApprovedPurchaseRequest.department_display == "")
    ).all():
        results.append(_p_rec(o, "R02", "department_display 為空白"))

    # R03 金額異常（NULL 或 ≤0）
    for o in base_q.filter(
        (ApprovedPurchaseRequest.amount == None)  # noqa: E711
        | (ApprovedPurchaseRequest.amount <= 0)
    ).all():
        results.append(_p_rec(o, "R03", f"amount = {o.amount}（應為正整數）"))

    # R04 品項加總不符（只對 detail_synced=True，容差 ±1 元）
    # 豁免條件：item_sum IS NULL → 品項 selected_amount 全為空（金額在擬定廠商欄尚未同步），
    #   不屬於「加總不符」，由 R07 負責提示同步狀態
    item_sum_sq = (
        db.query(
            ApprovedPurchaseRequestItem.order_id,
            func.sum(ApprovedPurchaseRequestItem.selected_amount).label("item_sum"),
        )
        .group_by(ApprovedPurchaseRequestItem.order_id)
        .subquery()
    )
    r04_rows = (
        base_q
        .filter(ApprovedPurchaseRequest.detail_synced == True)  # noqa: E712
        .outerjoin(item_sum_sq, ApprovedPurchaseRequest.id == item_sum_sq.c.order_id)
        .add_columns(item_sum_sq.c.item_sum)
        .filter(
            item_sum_sq.c.item_sum.isnot(None),          # NULL 加總 = 品項無金額，非加總不符
            func.abs(
                func.coalesce(ApprovedPurchaseRequest.amount, 0)
                - item_sum_sq.c.item_sum
            ) > 1
        )
        .all()
    )
    for row in r04_rows:
        o, item_sum = row[0], row[1]
        diff = abs((o.amount or 0) - (item_sum or 0))
        results.append(_p_rec(o, "R04",
            f"主單 amount={o.amount}，品項加總={item_sum}，差異={diff} 元"))

    # R05 會科空白
    for o in base_q.filter(
        (ApprovedPurchaseRequest.account_category == None)  # noqa: E711
        | (ApprovedPurchaseRequest.account_category == "")
    ).all():
        results.append(_p_rec(o, "R05", "account_category 為空白"))

    # R07 Detail 未同步（status=F 但品項尚未從 Ragic 拉取）
    for o in base_q.filter(
        ApprovedPurchaseRequest.detail_synced == False  # noqa: E712
    ).all():
        results.append(_p_rec(o, "R07", "detail_synced = False，品項尚未完成 Ragic 同步"))

    # R08 同部門同單號重複（台中：跨部門同號是正常，只有同一個部門表單內重複才算）
    dup_sq = (
        base_q
        .with_entities(
            ApprovedPurchaseRequest.ragic_sheet_path,
            ApprovedPurchaseRequest.purchase_no,
            func.count(ApprovedPurchaseRequest.id).label("cnt"),
        )
        .filter(ApprovedPurchaseRequest.purchase_no != "")
        .filter(ApprovedPurchaseRequest.purchase_no != None)  # noqa: E711
        .group_by(ApprovedPurchaseRequest.ragic_sheet_path, ApprovedPurchaseRequest.purchase_no)
        .having(func.count(ApprovedPurchaseRequest.id) > 1)
        .subquery()
    )
    dup_keys = {(r[0], r[1]) for r in db.query(dup_sq.c.ragic_sheet_path, dup_sq.c.purchase_no).all()}
    if dup_keys:
        for o in base_q.filter(
            ApprovedPurchaseRequest.purchase_no.in_([k[1] for k in dup_keys])
        ).all():
            if (o.ragic_sheet_path, o.purchase_no) in dup_keys:
                results.append(_p_rec(o, "R08",
                    f"purchase_no「{o.purchase_no}」在 {o.department_display} 本期重複出現多筆"))

    return results


# ── 請款稽核規則 ───────────────────────────────────────────────────────────────

def _check_claim(db: Session, base_q) -> list[dict]:
    results: list[dict] = []

    # R01 單號空白
    for o in base_q.filter(
        (ApprovedClaimRequest.request_no == None)  # noqa: E711
        | (ApprovedClaimRequest.request_no == "")
    ).all():
        results.append(_c_rec(o, "R01", "request_no 為空白"))

    # R02 部門空白
    for o in base_q.filter(
        (ApprovedClaimRequest.department_display == None)  # noqa: E711
        | (ApprovedClaimRequest.department_display == "")
    ).all():
        results.append(_c_rec(o, "R02", "department_display 為空白"))

    # R03 金額異常（payable_amount NULL 或 ≤0）
    # 豁免條件：detail_synced=True 且品項層 selected_amount 加總 > 0
    #   → 代表金額存在於品項，payable_amount 僅為 Ragic 同步欄位遺漏，不屬異常
    r03_candidates = base_q.filter(
        (ApprovedClaimRequest.payable_amount == None)  # noqa: E711
        | (ApprovedClaimRequest.payable_amount <= 0)
    ).all()
    for o in r03_candidates:
        if o.detail_synced:
            item_total = (
                db.query(func.sum(ApprovedClaimRequestItem.proposed_vendor_amount))
                .filter(ApprovedClaimRequestItem.claim_id == o.id)
                .scalar()
            )
            if item_total and item_total > 0:
                continue  # 品項有金額，跳過 R03
        results.append(_c_rec(o, "R03", f"payable_amount = {o.payable_amount}（應為正整數）"))

    # R05 會科空白
    for o in base_q.filter(
        (ApprovedClaimRequest.account_subject == None)  # noqa: E711
        | (ApprovedClaimRequest.account_subject == "")
    ).all():
        results.append(_c_rec(o, "R05", "account_subject 為空白"))

    # R06 付款種類空白（claim only）
    for o in base_q.filter(
        (ApprovedClaimRequest.payment_type == None)  # noqa: E711
        | (ApprovedClaimRequest.payment_type == "")
    ).all():
        results.append(_c_rec(o, "R06", "payment_type 為空白"))

    # R07 Detail 未同步
    for o in base_q.filter(
        ApprovedClaimRequest.detail_synced == False  # noqa: E712
    ).all():
        results.append(_c_rec(o, "R07", "detail_synced = False，品項尚未完成 Ragic 同步"))

    # R08 同部門同單號重複（台中：跨部門同號是正常，只有同一個部門表單內重複才算）
    dup_sq = (
        base_q
        .with_entities(
            ApprovedClaimRequest.ragic_sheet_path,
            ApprovedClaimRequest.request_no,
            func.count(ApprovedClaimRequest.id).label("cnt"),
        )
        .filter(ApprovedClaimRequest.request_no != "")
        .filter(ApprovedClaimRequest.request_no != None)  # noqa: E711
        .group_by(ApprovedClaimRequest.ragic_sheet_path, ApprovedClaimRequest.request_no)
        .having(func.count(ApprovedClaimRequest.id) > 1)
        .subquery()
    )
    dup_keys = {(r[0], r[1]) for r in db.query(dup_sq.c.ragic_sheet_path, dup_sq.c.request_no).all()}
    if dup_keys:
        for o in base_q.filter(
            ApprovedClaimRequest.request_no.in_([k[1] for k in dup_keys])
        ).all():
            if (o.ragic_sheet_path, o.request_no) in dup_keys:
                results.append(_c_rec(o, "R08",
                    f"request_no「{o.request_no}」在 {o.department_display} 本期重複出現多筆"))

    return results


# ── 內部：取得全部異常（未分頁）─────────────────────────────────────────────────

def _all_anomalies(
    db: Session,
    source: str = "all",
    year_month: Optional[str] = None,
    year_month_from: Optional[str] = None,
    year_month_to: Optional[str] = None,
    department: Optional[str] = None,
    company: Optional[str] = None,
) -> list[dict]:
    results: list[dict] = []

    if source in ("purchase", "all"):
        pq = _purchase_base_q(db, year_month, year_month_from, year_month_to, department, company)
        results.extend(_check_purchase(db, pq))

    if source in ("claim", "all"):
        cq = _claim_base_q(db, year_month, year_month_from, year_month_to, department, company)
        results.extend(_check_claim(db, cq))

    # 排序：嚴重程度 high→medium→low，然後核准日期降冪
    # ⚠️ 第三個鍵 `doc_no` 是**穩定性次要鍵**，不是排序需求（2026-08-29 補）。
    #    只用 (嚴重度, 日期) 的話，同一天同嚴重度的多筆先後由引擎決定 ——
    #    SQLite 與 PostgreSQL 的實作不同，切換後這份清單的順序會變**且不報錯**。
    results.sort(key=lambda r: (
        _SEVERITY_ORDER.get(r["severity"], 9),
        -(int((r["approved_date"] or "0000-00-00").replace("-", ""))),
        r.get("doc_no") or "",
    ))
    return results


# ── 公開 API ───────────────────────────────────────────────────────────────────

def get_anomalies(
    db: Session,
    source: str = "all",
    year_month: Optional[str] = None,
    year_month_from: Optional[str] = None,
    year_month_to: Optional[str] = None,
    department: Optional[str] = None,
    company: Optional[str] = None,
    rule_code: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """回傳分頁異常列表。"""
    items = _all_anomalies(db, source, year_month, year_month_from, year_month_to, department, company)

    if rule_code:
        items = [i for i in items if i["rule_code"] == rule_code]

    total = len(items)
    offset = (page - 1) * per_page
    return {
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "items":    items[offset: offset + per_page],
    }


def get_audit_summary(
    db: Session,
    source: str = "all",
    year_month: Optional[str] = None,
    year_month_from: Optional[str] = None,
    year_month_to: Optional[str] = None,
    department: Optional[str] = None,
    company: Optional[str] = None,
) -> dict:
    """回傳各規則計數 KPI。"""
    items = _all_anomalies(db, source, year_month, year_month_from, year_month_to, department, company)

    # 各規則命中次數
    by_rule_count: dict[str, int] = {}
    for item in items:
        by_rule_count[item["rule_code"]] = by_rule_count.get(item["rule_code"], 0) + 1

    # 有任何異常的唯一訂單數
    unique_orders = len({(r["source"], r["order_id"]) for r in items})

    rule_summary = []
    for code, meta in RULE_META.items():
        if source != "all" and source not in meta["applies_to"]:
            continue
        rule_summary.append({
            "rule_code":  code,
            "rule_name":  meta["name"],
            "severity":   meta["severity"],
            "applies_to": meta["applies_to"],
            "count":      by_rule_count.get(code, 0),
        })

    return {
        "total_anomalies": len(items),
        "total_orders":    unique_orders,
        "by_rule":         rule_summary,
    }
