

# ═══════════════════════════════════════════════════════════════════════════
# Phase 4a（2026-11-17）領用／退料／調撥／報廢 — SPEC §7、D26～D29
# ═══════════════════════════════════════════════════════════════════════════
#
# 資料範圍（D27）：有 stock_issue_create 者只能從「自己所屬部門（user_departments）」的倉開領用／退料單，
#   並看到這些倉的單據與自己開的單；倉管（stock_issue_post）與系統管理員看／操作同公司所有倉。
# 核准（D28）：倉庫設定「領用需核准」才走核准；核准者＝有 stock_issue_approve 且屬於該倉部門的人（系統管理員皆可）。
# 調撥／報廢（D29）：倉管開單即過帳，不走核准。
# 單位成本：只給倉管（stock_issue_post）、庫存檢視（stock_balance_view）與系統管理員看。

from app.models.stock import StockIssue, StockIssueLine
from app.models.user_department import UserDepartment
from app.services import stock_issue_service as iss
from app.services.stock_service import _d

ISSUE_CREATE = "stock_issue_create"
ISSUE_APPROVE = "stock_issue_approve"
ISSUE_POST = "stock_issue_post"
_issue_any = require_any_permission(ISSUE_CREATE, ISSUE_APPROVE, ISSUE_POST)


def _my_dept_ids(db: Session, user_id: str) -> set:
    return {str(d) for (d,) in db.query(UserDepartment.department_id).filter(UserDepartment.user_id == user_id).all()}


def _see_all(ctx: StockContext) -> bool:
    return ctx.has(ISSUE_POST)


def _can_see_cost(ctx: StockContext) -> bool:
    return ctx.has(ISSUE_POST) or ctx.has(VIEW)


def _in_scope(ctx: StockContext, depts: set, w: StockWarehouse) -> bool:
    return _see_all(ctx) or (w.department_id is not None and str(w.department_id) in depts)


def _can_approve(ctx: StockContext, depts: set, w: StockWarehouse) -> bool:
    if ctx.is_admin:
        return True
    return ISSUE_APPROVE in ctx.perms and w.department_id is not None and str(w.department_id) in depts


def _doc(cp: Session, ctx: StockContext, depts: set, did: int) -> StockIssue:
    d = cp.query(StockIssue).get(did)
    if not d or d.company_code != ctx.code:
        raise HTTPException(status_code=404, detail="找不到單據")
    w = cp.query(StockWarehouse).get(d.warehouse_id)
    if not (_in_scope(ctx, depts, w) or d.created_by_user_id == ctx.user_id):
        raise HTTPException(status_code=404, detail="找不到單據")
    return d


def _actions(ctx: StockContext, depts: set, d: StockIssue, w: StockWarehouse) -> list[str]:
    """這張單目前「這個使用者」可以做的動作（前端依此顯示按鈕；後端仍會再檢查一次）。"""
    mine = d.created_by_user_id == ctx.user_id
    keeper = ctx.has(ISSUE_POST)
    out = []
    if d.status == "draft":
        if d.doc_type in ("issue", "return") and (mine or keeper):
            out += ["edit", "submit", "cancel"]
        if d.doc_type in ("transfer", "scrap") and keeper:
            out += ["edit", "post", "cancel"]
    elif d.status == "pending_approval":
        if _can_approve(ctx, depts, w):
            out += ["approve", "reject"]
        if mine or keeper:
            out.append("cancel")
    elif d.status == "approved":
        if keeper:
            out.append("post")
        if mine or keeper:
            out.append("cancel")
    elif d.status == "posted":
        if d.doc_type in iss.VOIDABLE_TYPES and keeper:
            out.append("void")
        if d.doc_type == "issue" and (keeper or ctx.has(ISSUE_CREATE)):
            out.append("return")
    return out


def _issue_out(d: StockIssue, wname: dict, ctx: StockContext, depts: set, wmap: dict) -> dict:
    w = wmap.get(d.warehouse_id)
    return {
        "id": d.id, "doc_no": d.doc_no, "doc_type": d.doc_type, "doc_type_label": iss.DOC_LABEL[d.doc_type],
        "warehouse_id": d.warehouse_id, "warehouse_name": wname.get(d.warehouse_id, ""),
        "to_warehouse_id": d.to_warehouse_id, "to_warehouse_name": wname.get(d.to_warehouse_id, "") if d.to_warehouse_id else None,
        "doc_date": d.doc_date.isoformat(), "posted_date": d.posted_date.isoformat() if d.posted_date else None,
        "requester_name": d.requester_name, "department_name": d.department_name, "purpose": d.purpose,
        "cost_center_id": d.cost_center_id, "cost_center_name": d.cost_center_name, "account_code": d.account_code,
        "ref_issue_id": d.ref_issue_id, "status": d.status, "status_label": iss.status_label(d),
        "line_count": d.line_count, "total_amount": _f(d.total_amount) if _can_see_cost(ctx) else None,
        "created_by": d.created_by, "created_at": d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else None,
        "submitted_by": d.submitted_by, "approved_by": d.approved_by,
        "approved_at": d.approved_at.strftime("%Y-%m-%d %H:%M") if d.approved_at else None,
        "posted_by": d.posted_by, "posted_at": d.posted_at.strftime("%Y-%m-%d %H:%M") if d.posted_at else None,
        "closed_by": d.closed_by, "close_reason": d.close_reason,
        "actions": _actions(ctx, depts, d, w) if w else [],
    }


@router.get("/issues/meta", summary="領用單：可操作的倉庫與權限旗標")
def issues_meta(ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    depts = _my_dept_ids(db, ctx.user_id)
    whs = (cp.query(StockWarehouse).filter(StockWarehouse.company_code == ctx.code, StockWarehouse.status != "inactive")
           .order_by(StockWarehouse.name).all())
    return {
        "can_create": ctx.has(ISSUE_CREATE) or ctx.has(ISSUE_POST),
        "can_post": ctx.has(ISSUE_POST), "can_approve": ctx.has(ISSUE_APPROVE),
        "can_see_cost": _can_see_cost(ctx), "user_name": ctx.user_name,
        # 可開領用／退料單的倉（所屬部門；倉管＝全部）
        "my_warehouses": [{"id": w.id, "name": w.name, "department_name": w.department_name, "status": w.status,
                           "issue_requires_approval": bool(w.issue_requires_approval)}
                          for w in whs if _in_scope(ctx, depts, w)],
        # 調入倉（倉管開調撥用：同公司全部）
        "all_warehouses": [{"id": w.id, "name": w.name, "department_name": w.department_name, "status": w.status}
                           for w in whs] if ctx.has(ISSUE_POST) else [],
    }


@router.get("/issues/available", summary="倉庫可領用的料號（可用量 > 0）")
def issues_available(warehouse_id: int, keyword: Optional[str] = Query(None, max_length=100),
                     ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                     cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    w = _warehouse(cp, ctx, warehouse_id)
    if not _in_scope(ctx, _my_dept_ids(db, ctx.user_id), w):
        raise HTTPException(status_code=403, detail="不能使用這個倉庫（不是您所屬部門的倉）")
    rows = iss.available_items(cp, w.id, keyword)
    if not _can_see_cost(ctx):
        for r in rows:
            r["avg_cost"] = None
    return rows


@router.get("/issues/cost-centers", summary="成本中心（預設＝倉庫部門的預設成本中心）")
def issues_cost_centers(warehouse_id: Optional[int] = None, ctx: StockContext = Depends(stock_context),
                        cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    dept = None
    if warehouse_id:
        dept = _warehouse(cp, ctx, warehouse_id).department_id
    return iss.cost_centers(cp, ctx.code, dept)


@router.get("/issues/summary", summary="領用單 KPI（期間）")
def issues_summary(start: Optional[date] = None, end: Optional[date] = None, ctx: StockContext = Depends(stock_context),
                   db: Session = Depends(get_db), cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    depts = _my_dept_ids(db, ctx.user_id)
    whs = cp.query(StockWarehouse).filter(StockWarehouse.company_code == ctx.code).all()
    wids = [w.id for w in whs if _in_scope(ctx, depts, w)]
    base = cp.query(StockIssue).filter(StockIssue.company_code == ctx.code,
                                       or_(StockIssue.warehouse_id.in_(wids or [0]),
                                           StockIssue.created_by_user_id == ctx.user_id))
    last = (cp.query(func.max(StockIssue.posted_date))
            .filter(StockIssue.company_code == ctx.code, StockIssue.status == "posted").scalar())
    posted = base.filter(StockIssue.status == "posted", StockIssue.doc_type == "issue")
    if start:
        posted = posted.filter(StockIssue.posted_date >= start)
    if end:
        posted = posted.filter(StockIssue.posted_date <= end)
    pdocs = posted.all()
    return {
        "issue_count": len(pdocs),
        "issue_amount": float(sum(_d(x.total_amount) for x in pdocs)) if _can_see_cost(ctx) else None,
        "pending_approval": base.filter(StockIssue.status == "pending_approval").count(),
        "pending_post": base.filter(StockIssue.status == "approved").count(),
        "drafts": base.filter(StockIssue.status == "draft", StockIssue.created_by_user_id == ctx.user_id).count(),
        "data_end": last.isoformat() if last else None,
    }


@router.get("/issues", summary="領用／退料／調撥／報廢單清單")
def list_issues(doc_type: Optional[str] = Query(None, pattern="^(issue|return|transfer|scrap)$"),
                status: Optional[list[str]] = Query(None), warehouse_id: Optional[int] = None,
                start: Optional[date] = None, end: Optional[date] = None, mine: bool = False,
                ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    depts = _my_dept_ids(db, ctx.user_id)
    whs = cp.query(StockWarehouse).filter(StockWarehouse.company_code == ctx.code).all()
    wmap = {w.id: w for w in whs}
    wname = {w.id: w.name for w in whs}
    wids = [w.id for w in whs if _in_scope(ctx, depts, w)]
    q = cp.query(StockIssue).filter(StockIssue.company_code == ctx.code,
                                    or_(StockIssue.warehouse_id.in_(wids or [0]), StockIssue.created_by_user_id == ctx.user_id))
    if doc_type:
        q = q.filter(StockIssue.doc_type == doc_type)
    if status:
        q = q.filter(StockIssue.status.in_(status))
    if warehouse_id:
        q = q.filter(or_(StockIssue.warehouse_id == warehouse_id, StockIssue.to_warehouse_id == warehouse_id))
    if start:
        q = q.filter(StockIssue.doc_date >= start)
    if end:
        q = q.filter(StockIssue.doc_date <= end)
    if mine:
        q = q.filter(StockIssue.created_by_user_id == ctx.user_id)
    rows = q.order_by(StockIssue.doc_date.desc(), StockIssue.id.desc()).limit(2000).all()
    return [_issue_out(d, wname, ctx, depts, wmap) for d in rows]


@router.get("/issues/{did}", summary="單據明細")
def get_issue(did: int, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
              cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    depts = _my_dept_ids(db, ctx.user_id)
    d = _doc(cp, ctx, depts, did)
    whs = cp.query(StockWarehouse).filter(StockWarehouse.company_code == ctx.code).all()
    out = _issue_out(d, {w.id: w.name for w in whs}, ctx, depts, {w.id: w for w in whs})
    bal = {b.item_id: b for b in cp.query(StockBalance).filter(StockBalance.warehouse_id == d.warehouse_id).all()}
    cost = _can_see_cost(ctx)
    lines = []
    for l, it in (cp.query(StockIssueLine, CyclePurchaseItem).join(CyclePurchaseItem, CyclePurchaseItem.id == StockIssueLine.item_id)
                  .filter(StockIssueLine.issue_id == d.id).order_by(StockIssueLine.id).all()):
        b = bal.get(it.id)
        lines.append({
            "id": l.id, "item_id": it.id, "item_code": it.item_code, "item_name": it.item_name, "spec": it.spec,
            "unit": it.unit, "qty": float(l.qty), "reserved_qty": float(l.reserved_qty), "ref_line_id": l.ref_line_id,
            "note": l.note, "available": float(_d(b.qty) - _d(b.reserved_qty)) if b else 0.0,
            "unit_cost": _f(l.unit_cost) if cost else None, "amount": _f(l.amount) if cost else None,
        })
    out["lines"] = lines
    if d.ref_issue_id:
        ref = cp.query(StockIssue).get(d.ref_issue_id)
        out["ref_issue_no"] = ref.doc_no if ref else None
    out["returns"] = [{"id": r.id, "doc_no": r.doc_no, "status_label": iss.status_label(r)}
                      for r in cp.query(StockIssue).filter(StockIssue.ref_issue_id == d.id).order_by(StockIssue.id).all()]
    return out


@router.get("/issues/{did}/returnable", summary="原領用單可退料的品項")
def issue_returnable(did: int, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                     cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    d = _doc(cp, ctx, _my_dept_ids(db, ctx.user_id), did)
    try:
        rows = iss.returnable_lines(cp, d)
    except svc.StockError as e:
        _business_error(e)
    if not _can_see_cost(ctx):
        for r in rows:
            r["unit_cost"] = None
    return rows


class IssueLineIn(BaseModel):
    item_id: int = 0
    qty: Decimal = Field(..., gt=0)
    ref_line_id: Optional[int] = None
    note: Optional[str] = Field(None, max_length=500)


class IssueIn(BaseModel):
    doc_type: str = Field(..., pattern="^(issue|return|transfer|scrap)$")
    warehouse_id: int
    to_warehouse_id: Optional[int] = None
    doc_date: date
    requester_name: Optional[str] = Field(None, max_length=100)
    purpose: Optional[str] = Field(None, max_length=1000)
    cost_center_id: Optional[int] = None
    account_code: Optional[str] = Field(None, max_length=50)
    ref_issue_id: Optional[int] = None
    lines: list[IssueLineIn] = Field(..., min_length=1, max_length=300)
    then: Optional[str] = Field(None, pattern="^(submit|post)$", description="存檔後接著送出（領用／退料）或過帳（調撥／報廢）")
    post_date: Optional[date] = None


class ReasonIn(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class PostIn(BaseModel):
    post_date: Optional[date] = None


def _today() -> date:
    from app.core.time import twnow
    return twnow().date()


def _save(body: IssueIn, doc: Optional[StockIssue], ctx: StockContext, db: Session, cp: Session) -> StockIssue:
    depts = _my_dept_ids(db, ctx.user_id)
    w = _warehouse(cp, ctx, body.warehouse_id)
    if body.doc_type in ("transfer", "scrap"):
        if not ctx.has(ISSUE_POST):
            raise HTTPException(status_code=403, detail="調撥／報廢單限倉管（領用單：發料過帳／調撥／報廢）開立")
    else:
        if not (ctx.has(ISSUE_CREATE) or ctx.has(ISSUE_POST)):
            raise HTTPException(status_code=403, detail="沒有開立領用／退料單的權限")
        if not _in_scope(ctx, depts, w):
            raise HTTPException(status_code=403, detail="只能從您所屬部門的倉庫開單")
    if doc is not None and doc.created_by_user_id != ctx.user_id and not ctx.has(ISSUE_POST):
        raise HTTPException(status_code=403, detail="只能修改自己開的草稿")
    to_w = _warehouse(cp, ctx, body.to_warehouse_id) if body.to_warehouse_id else None
    ref = None
    if body.ref_issue_id:
        ref = _doc(cp, ctx, depts, body.ref_issue_id)
    try:
        d = iss.save_draft(
            cp, doc=doc, doc_type=body.doc_type, code=ctx.code, warehouse=w, to_warehouse=to_w, doc_date=body.doc_date,
            requester_name=body.requester_name, requester_user_id=ctx.user_id, purpose=body.purpose,
            cost_center_id=body.cost_center_id, account_code=body.account_code, ref_issue=ref,
            lines=[iss.LineIn(item_id=l.item_id, qty=l.qty, ref_line_id=l.ref_line_id, note=l.note) for l in body.lines],
            user_name=ctx.user_name, user_id=ctx.user_id)
        if body.then == "submit":
            iss.submit(cp, d, ctx.user_name)
        elif body.then == "post":
            if not ctx.has(ISSUE_POST):
                raise HTTPException(status_code=403, detail="沒有過帳權限")
            iss.post(cp, d, body.post_date or _today(), ctx.user_name)
    except svc.StockError as e:
        _business_error(e)
    return d


@router.post("/issues", summary="新增單據（草稿；可接著送出／過帳）")
def create_issue(body: IssueIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                 cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    d = _save(body, None, ctx, db, cp)
    return {"id": d.id, "doc_no": d.doc_no, "status": d.status}


@router.put("/issues/{did}", summary="修改草稿（可接著送出／過帳）")
def update_issue(did: int, body: IssueIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                 cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    d = _doc(cp, ctx, _my_dept_ids(db, ctx.user_id), did)
    if body.doc_type != d.doc_type:
        raise HTTPException(status_code=422, detail="不能變更單據類型")
    d = _save(body, d, ctx, db, cp)
    return {"id": d.id, "doc_no": d.doc_no, "status": d.status}


def _act(did: int, action: str, ctx: StockContext, db: Session, cp: Session, fn):
    depts = _my_dept_ids(db, ctx.user_id)
    d = _doc(cp, ctx, depts, did)
    w = cp.query(StockWarehouse).get(d.warehouse_id)
    if action not in _actions(ctx, depts, d, w):
        raise HTTPException(status_code=403, detail="您不能對這張單執行這個動作（權限、部門或狀態不符）")
    try:
        fn(d)
    except svc.StockError as e:
        _business_error(e)
    return {"id": d.id, "doc_no": d.doc_no, "status": d.status, "status_label": iss.status_label(d)}


@router.post("/issues/{did}/submit", summary="送出（領用：保留數量；退料：待收料）")
def submit_issue(did: int, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                 cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    return _act(did, "submit", ctx, db, cp, lambda d: iss.submit(cp, d, ctx.user_name))


@router.post("/issues/{did}/approve", summary="核准領用單（部門主管）")
def approve_issue(did: int, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                  cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(ISSUE_APPROVE))):
    return _act(did, "approve", ctx, db, cp, lambda d: iss.approve(cp, d, ctx.user_name))


@router.post("/issues/{did}/reject", summary="退回領用單（釋放保留）")
def reject_issue(did: int, body: ReasonIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                 cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(ISSUE_APPROVE))):
    if not (body.reason or "").strip():
        raise HTTPException(status_code=422, detail="請填寫退回原因")
    return _act(did, "reject", ctx, db, cp, lambda d: iss.reject(cp, d, body.reason.strip(), ctx.user_name))


@router.post("/issues/{did}/cancel", summary="取消（釋放保留）")
def cancel_issue(did: int, body: ReasonIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                 cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    return _act(did, "cancel", ctx, db, cp, lambda d: iss.cancel(cp, d, (body.reason or "").strip() or None, ctx.user_name))


@router.post("/issues/{did}/post", summary="發料／收料／過帳（倉管）")
def post_issue(did: int, body: PostIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
               cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(ISSUE_POST))):
    return _act(did, "post", ctx, db, cp, lambda d: iss.post(cp, d, body.post_date or _today(), ctx.user_name))


@router.post("/issues/{did}/void", summary="作廢已過帳的退料／調撥／報廢單（反向異動）")
def void_issue(did: int, body: ReasonIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
               cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(ISSUE_POST))):
    if not (body.reason or "").strip():
        raise HTTPException(status_code=422, detail="請填寫作廢原因")
    return _act(did, "void", ctx, db, cp, lambda d: iss.void(cp, d, body.reason.strip(), ctx.user_name))
