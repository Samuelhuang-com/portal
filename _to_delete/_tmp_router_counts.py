

# ═══════════════════════════════════════════════════════════════════════════
# Phase 5（2026-11-17）盤點、盤盈虧、月結、進銷存月報 — SPEC §8.3～§8.6、§9
# ═══════════════════════════════════════════════════════════════════════════
#
# 權限：stock_count_execute 盤點（限所屬部門的倉）／stock_count_review 產生盤點表、審核盤盈虧（全部倉）
#       stock_period_close 月結／反月結／stock_balance_view 進銷存月報
# 盲盤（D8）：盤點表 blind＝True 時，只有審核者看得到帳面數與差異。

from app.models.stock import StockCount, StockCountLine, StockPeriod
from app.services import stock_count_service as cnt

COUNT_EXEC = "stock_count_execute"
COUNT_REVIEW = "stock_count_review"
PERIOD_CLOSE = "stock_period_close"
_count_any = require_any_permission(COUNT_EXEC, COUNT_REVIEW)


def _count_see_all(ctx: StockContext) -> bool:
    return ctx.has(COUNT_REVIEW)


def _count_in_scope(ctx: StockContext, depts: set, w: StockWarehouse) -> bool:
    return _count_see_all(ctx) or (w.department_id is not None and str(w.department_id) in depts)


def _count(cp: Session, ctx: StockContext, db: Session, cid: int) -> tuple[StockCount, StockWarehouse]:
    c = cp.query(StockCount).get(cid)
    if not c or c.company_code != ctx.code:
        raise HTTPException(status_code=404, detail="找不到盤點表")
    w = cp.query(StockWarehouse).get(c.warehouse_id)
    if not _count_in_scope(ctx, _my_dept_ids(db, ctx.user_id), w):
        raise HTTPException(status_code=404, detail="找不到盤點表")
    return c, w


def _count_out(c: StockCount, wname: str, ctx: StockContext, counted: Optional[int] = None) -> dict:
    review = ctx.has(COUNT_REVIEW)
    return {
        "id": c.id, "count_no": c.count_no, "warehouse_id": c.warehouse_id, "warehouse_name": wname, "period": c.period,
        "count_date": c.count_date.isoformat(), "cutoff_at": c.cutoff_at.strftime("%Y-%m-%d %H:%M"), "blind": bool(c.blind),
        "status": c.status, "status_label": cnt.STATUS_LABEL.get(c.status, c.status), "note": c.note,
        "line_count": c.line_count, "counted_count": counted, "diff_count": c.diff_count,
        "gain_amount": _f(c.gain_amount) if review else None, "loss_amount": _f(c.loss_amount) if review else None,
        "created_by": c.created_by, "created_at": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else None,
        "submitted_by": c.submitted_by, "approved_by": c.approved_by,
        "approved_at": c.approved_at.strftime("%Y-%m-%d %H:%M") if c.approved_at else None,
        "closed_by": c.closed_by, "close_reason": c.close_reason,
        "can_input": c.status == "counting" and (ctx.has(COUNT_EXEC) or review),
        "can_review": review and c.status == "submitted", "can_cancel": review and c.status in ("counting", "submitted"),
        "show_book": review or not c.blind,
    }


@router.get("/counts", summary="盤點表清單")
def list_counts(period: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"), status: Optional[list[str]] = Query(None),
                ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                cp: Session = Depends(get_cycle_purchase_db), _=Depends(_count_any)):
    depts = _my_dept_ids(db, ctx.user_id)
    whs = {w.id: w for w in cp.query(StockWarehouse).filter(StockWarehouse.company_code == ctx.code).all()}
    wids = [i for i, w in whs.items() if _count_in_scope(ctx, depts, w)]
    q = cp.query(StockCount).filter(StockCount.company_code == ctx.code, StockCount.warehouse_id.in_(wids or [0]))
    if period:
        q = q.filter(StockCount.period == period)
    if status:
        q = q.filter(StockCount.status.in_(status))
    rows = q.order_by(StockCount.count_date.desc(), StockCount.id.desc()).limit(1000).all()
    done = dict(cp.query(StockCountLine.count_id, func.count(StockCountLine.id))
                .filter(StockCountLine.count_id.in_([c.id for c in rows] or [0]), StockCountLine.counted_qty.isnot(None))
                .group_by(StockCountLine.count_id).all())
    return [_count_out(c, whs[c.warehouse_id].name, ctx, done.get(c.id, 0)) for c in rows]


class CountCreateIn(BaseModel):
    warehouse_ids: list[int] = Field(..., min_length=1, max_length=200)
    count_date: date
    note: Optional[str] = Field(None, max_length=500)


@router.post("/counts", summary="產生盤點表（每個倉一張；倉庫改為盤點中、暫停過帳）")
def create_counts(body: CountCreateIn, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
                  _=Depends(require_permission(COUNT_REVIEW))):
    created, errors = [], []
    for wid in dict.fromkeys(body.warehouse_ids):
        w = _warehouse(cp, ctx, wid)
        sp = cp.begin_nested()
        try:
            c = cnt.create_count(cp, warehouse=w, count_date=body.count_date, note=body.note, user_name=ctx.user_name)
            sp.commit()
            created.append({"id": c.id, "count_no": c.count_no, "warehouse_name": w.name, "line_count": c.line_count})
        except svc.StockError as e:
            sp.rollback()
            errors.append(f"{w.name}：{e}")
    return {"created": created, "errors": errors}


@router.get("/counts/{cid}", summary="盤點表明細（盲盤時盤點人看不到帳面數）")
def get_count(cid: int, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
              cp: Session = Depends(get_cycle_purchase_db), _=Depends(_count_any)):
    c, w = _count(cp, ctx, db, cid)
    rows = (cp.query(StockCountLine, CyclePurchaseItem).join(CyclePurchaseItem, CyclePurchaseItem.id == StockCountLine.item_id)
            .filter(StockCountLine.count_id == c.id).order_by(CyclePurchaseItem.item_code).all())
    out = _count_out(c, w.name, ctx, sum(1 for l, _ in rows if l.counted_qty is not None))
    show_book, review = out["show_book"], ctx.has(COUNT_REVIEW)
    lines = []
    for l, it in rows:
        r = {"id": l.id, "item_id": it.id, "item_code": it.item_code, "item_name": it.item_name, "spec": it.spec, "unit": it.unit,
             "counted_qty": _f(l.counted_qty), "counted_by": l.counted_by, "note": l.note, "added_manually": bool(l.added_manually),
             "book_qty": _f(l.book_qty) if show_book else None}
        if review:
            v = cnt.line_view(l, it)
            if c.status == "approved":
                v["diff_qty"], v["diff_amount"] = _f(l.adj_qty), _f(l.adj_amount)
            r.update(v)
            r["unit_cost"] = _f(l.unit_cost)
        lines.append(r)
    out["lines"] = lines
    return out


class CountEntryIn(BaseModel):
    item_id: int
    counted_qty: Optional[Decimal] = Field(None, ge=0)
    note: Optional[str] = Field(None, max_length=500)


class CountEntriesIn(BaseModel):
    entries: list[CountEntryIn] = Field(..., min_length=1, max_length=3000)


def _count_act(cid, ctx, db, cp, need, fn):
    c, w = _count(cp, ctx, db, cid)
    if not ctx.has(need) and not (need == COUNT_EXEC and ctx.has(COUNT_REVIEW)):
        raise HTTPException(status_code=403, detail="權限不足")
    try:
        res = fn(c)
    except svc.StockError as e:
        _business_error(e)
    return res if isinstance(res, dict) else {"id": c.id, "count_no": c.count_no, "status": c.status,
                                              "status_label": cnt.STATUS_LABEL.get(c.status, c.status)}


@router.put("/counts/{cid}/entries", summary="輸入實盤數（counted_qty 留空＝清除）")
def save_count_entries(cid: int, body: CountEntriesIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                       cp: Session = Depends(get_cycle_purchase_db), _=Depends(_count_any)):
    return _count_act(cid, ctx, db, cp, COUNT_EXEC, lambda c: {"saved": cnt.save_counts(
        cp, c, [(e.item_id, e.counted_qty, e.note) for e in body.entries], ctx.user_name)})


@router.get("/counts/{cid}/item-search", summary="盤點加入料號：搜尋本公司料號")
def count_item_search(cid: int, keyword: str = Query(..., min_length=1, max_length=100), ctx: StockContext = Depends(stock_context),
                      db: Session = Depends(get_db), cp: Session = Depends(get_cycle_purchase_db), _=Depends(_count_any)):
    c, _w = _count(cp, ctx, db, cid)
    kw = f"%{keyword.strip()}%"
    rows = (cp.query(CyclePurchaseItem).filter(CyclePurchaseItem.company_code == ctx.code, CyclePurchaseItem.is_active.is_(True),
                                               or_(CyclePurchaseItem.item_code.ilike(kw), CyclePurchaseItem.item_name.ilike(kw)))
            .order_by(CyclePurchaseItem.item_code).limit(30).all())
    return [{"item_id": i.id, "item_code": i.item_code, "item_name": i.item_name, "spec": i.spec, "unit": i.unit} for i in rows]


class CountAddIn(BaseModel):
    item_id: int


@router.post("/counts/{cid}/items", summary="盤點加入清單外的料號")
def count_add_item(cid: int, body: CountAddIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                   cp: Session = Depends(get_cycle_purchase_db), _=Depends(_count_any)):
    it = _item(cp, ctx, body.item_id)
    return _count_act(cid, ctx, db, cp, COUNT_EXEC, lambda c: {"line_id": cnt.add_item(cp, c, it, ctx.user_name).id})


class CountSubmitIn(BaseModel):
    fill_zero: bool = False


@router.post("/counts/{cid}/submit", summary="送出盤點（待審核）")
def submit_count(cid: int, body: CountSubmitIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                 cp: Session = Depends(get_cycle_purchase_db), _=Depends(_count_any)):
    return _count_act(cid, ctx, db, cp, COUNT_EXEC, lambda c: cnt.submit_count(cp, c, body.fill_zero, ctx.user_name))


class CountReturnIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    item_ids: Optional[list[int]] = None


@router.post("/counts/{cid}/return", summary="退回重盤（可只清指定料號）")
def return_count(cid: int, body: CountReturnIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                 cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(COUNT_REVIEW))):
    return _count_act(cid, ctx, db, cp, COUNT_REVIEW,
                      lambda c: cnt.return_count(cp, c, body.reason.strip(), body.item_ids, ctx.user_name))


@router.post("/counts/{cid}/approve", summary="核准盤盈虧（寫盤點調整異動，倉庫恢復啟用）")
def approve_count(cid: int, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                  cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(COUNT_REVIEW))):
    return _count_act(cid, ctx, db, cp, COUNT_REVIEW, lambda c: cnt.approve_count(cp, c, ctx.user_name))


@router.post("/counts/{cid}/cancel", summary="取消盤點（不寫異動，倉庫恢復啟用）")
def cancel_count(cid: int, body: ReasonIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                 cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(COUNT_REVIEW))):
    return _count_act(cid, ctx, db, cp, COUNT_REVIEW,
                      lambda c: cnt.cancel_count(cp, c, (body.reason or "").strip() or None, ctx.user_name))


# ── 月結 ───────────────────────────────────────────────────────────────────────

def _period_out(p: Optional[StockPeriod], period: str, has_moves: bool) -> dict:
    return {"period": period, "status": p.status if p else "open", "has_moves": has_moves,
            "closed_by": p.closed_by if p else None,
            "closed_at": p.closed_at.strftime("%Y-%m-%d %H:%M") if p and p.closed_at else None,
            "revalue_count": p.revalue_count if p else 0, "revalue_amount": _f(p.revalue_amount) if p else 0,
            "reopen_count": p.reopen_count if p else 0, "reopened_by": p.reopened_by if p else None,
            "reopen_reason": p.reopen_reason if p else None}


@router.get("/periods", summary="月結狀態（有異動的月份＋已有月結紀錄的月份）")
def list_periods(ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
                 _=Depends(require_any_permission(PERIOD_CLOSE, VIEW))):
    moved = {x for (x,) in cp.query(StockMove.period).filter(StockMove.company_code == ctx.code).distinct()}
    recs = {p.period: p for p in cp.query(StockPeriod).filter(StockPeriod.company_code == ctx.code).all()}
    return [_period_out(recs.get(x), x, x in moved) for x in sorted(moved | set(recs), reverse=True)]


@router.get("/periods/{period}/check", summary="月結前檢查")
def check_period(period: str, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
                 _=Depends(require_permission(PERIOD_CLOSE))):
    if not __import__("re").fullmatch(r"\d{4}-\d{2}", period):
        raise HTTPException(status_code=422, detail="月份格式為 YYYY-MM")
    return cnt.close_checks(cp, ctx.code, period)


@router.post("/periods/{period}/close", summary="月結（寫月加權平均成本調整、鎖定該月）")
def close_period(period: str, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
                 _=Depends(require_permission(PERIOD_CLOSE))):
    if not __import__("re").fullmatch(r"\d{4}-\d{2}", period):
        raise HTTPException(status_code=422, detail="月份格式為 YYYY-MM")
    try:
        p = cnt.close_period(cp, ctx.code, period, ctx.user_name)
    except svc.StockError as e:
        _business_error(e)
    return _period_out(p, period, True)


@router.post("/periods/{period}/reopen", summary="反月結（每個月份限一次，必填原因）")
def reopen_period(period: str, body: VoidIn, ctx: StockContext = Depends(stock_context),
                  cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(PERIOD_CLOSE))):
    try:
        p = cnt.reopen_period(cp, ctx.code, period, body.reason.strip(), ctx.user_name)
    except svc.StockError as e:
        _business_error(e)
    return _period_out(p, period, True)


# ── 進銷存月報 ─────────────────────────────────────────────────────────────────

@router.get("/monthly-report", summary="進銷存月報（料號一列：期初、各類異動、期末；數量＋金額）")
def monthly_report(period: str = Query(..., pattern=r"^\d{4}-\d{2}$"), warehouse_id: Optional[int] = None,
                   ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
                   _=Depends(require_permission(VIEW))):
    whs = cp.query(StockWarehouse).filter(StockWarehouse.company_code == ctx.code).all()
    wids = [w.id for w in whs if not warehouse_id or w.id == warehouse_id]
    p = cp.query(StockPeriod).filter(StockPeriod.company_code == ctx.code, StockPeriod.period == period).first()
    last = cp.query(func.max(StockMove.period)).filter(StockMove.company_code == ctx.code).scalar()
    return {"period": period, "closed": bool(p and p.status == "closed"), "last_period": last,
            "columns": [{"key": k, "label": lbl} for k, _t, lbl in cnt.REPORT_COLS],
            "rows": cnt.monthly_report(cp, ctx.code, period, wids)}
