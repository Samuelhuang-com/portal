"""
庫存管理 Phase 5：盤點、盤盈虧、月結、進銷存月報 — docs/SPEC_stock_management.md §8.3～§8.6、§9

所有庫存數字仍只經由 stock_service（post_move／post_revalue）變動；呼叫端（router）負責權限、資料範圍與 commit。

盤點流程（2026-11-17 Samuel 裁示：先手動產生）：
  產生（counting：凍結帳面數、倉庫狀態改「盤點中」暫停過帳 D7）
    → 盤點人輸入實盤數（盲盤 D8：看不到帳面數）→ 送出（submitted）
    → 主管審核：退回重盤（回 counting）／核准（approved：依差異寫 count_adjust 異動，倉庫恢復啟用）
  counting／submitted 可取消（倉庫恢復啟用，不寫任何異動）

月結（D3 月加權平均＋成本調整異動，2026-11-17 裁示）：
  條件：前面有異動的月份都已月結；本月有異動或月底有庫存的倉都要有「已核准」盤點（空倉免盤）；
        沒有盤點中的倉；沒有未發料／未核准的領用單（單據日在本月以前）；沒有未處理的「來源已異動」進貨
  成本：每倉 × 料號，本月加權平均單價 W＝（期初金額＋本月進貨金額）÷（期初數量＋本月進貨數量）
        （進貨＝進貨單與期初開帳，含其作廢）；月底結存應為「月底數量 × W」，與帳上金額的差額寫一筆
        cost_revalue（數量 0、只調金額）異動，日期為月底。原異動不改，庫存卡看得到調整。
  月結後該月不能再有任何異動（stock_service.ensure_period_open）。反月結需 stock_period_close、必填原因、
  每個月份限一次，且只能反最近一個已月結月份；再次月結時差額自動重算（已含前次調整）。
"""
from calendar import monthrange
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.cycle_purchase_item import CyclePurchaseItem
from app.models.stock import (
    RESERVING_STATUSES, StockBalance, StockCount, StockCountLine, StockImportLine, StockIssue, StockItemSetting,
    StockMove, StockPeriod, StockWarehouse,
)
from app.services import stock_service as svc
from app.services.stock_service import Q2, Q4, StockError, _d

# 複盤提醒門檻（§9.8）：差異數量超過帳面 5%，或差異金額達 1,000 元
RECOUNT_PCT = Decimal("0.05")
RECOUNT_AMOUNT = Decimal("1000")
STATUS_LABEL = {"counting": "盤點中", "submitted": "待審核", "approved": "已核准", "cancelled": "已取消"}
PURCHASE_TYPES = ("receipt", "receipt_void", "opening", "opening_void")


def period_bounds(period: str) -> tuple[date, date]:
    y, m = map(int, period.split("-"))
    return date(y, m, 1), date(y, m, monthrange(y, m)[1])


def _next_no(db: Session, code: str, d: date) -> str:
    prefix = f"CNT-{code}-{d.strftime('%Y%m')}-"
    last = (db.query(StockCount.count_no).filter(StockCount.count_no.like(prefix + "%"))
            .order_by(StockCount.count_no.desc()).with_for_update().first())
    return f"{prefix}{(int(last[0][-3:]) + 1 if last else 1):03d}"


# ── 盤點 ───────────────────────────────────────────────────────────────────────

def open_count_for(db: Session, warehouse_id: int) -> Optional[StockCount]:
    return (db.query(StockCount).filter(StockCount.warehouse_id == warehouse_id,
                                        StockCount.status.in_(("counting", "submitted"))).first())


def create_count(db: Session, *, warehouse: StockWarehouse, count_date: date, note: Optional[str], user_name: str,
                 abc_classes: Optional[list[str]] = None) -> StockCount:
    """產生盤點表：品項＝這個倉有過庫存紀錄的料號（含帳面為 0）；倉庫改為盤點中。
    abc_classes（Phase 7 循環盤點）：只盤這些 ABC 類的料號；屬於額外抽盤，不算月結要求的月底全盤（2026-11-17 裁示）。"""
    if warehouse.status == "inactive":
        raise StockError(f"倉庫「{warehouse.name}」已停用")
    if warehouse.status == "counting" or open_count_for(db, warehouse.id):
        raise StockError(f"倉庫「{warehouse.name}」已有進行中的盤點表")
    svc.ensure_period_open(db, warehouse.company_code, count_date)
    rows = (db.query(StockBalance, CyclePurchaseItem, StockItemSetting)
            .join(CyclePurchaseItem, CyclePurchaseItem.id == StockBalance.item_id)
            .outerjoin(StockItemSetting, StockItemSetting.item_id == CyclePurchaseItem.id)
            .filter(StockBalance.warehouse_id == warehouse.id)
            .order_by(CyclePurchaseItem.item_code).all())
    if abc_classes:
        rows = [(b, it, st) for b, it, st in rows if st is not None and st.abc_class in abc_classes]
        if not rows:
            raise StockError(f"倉庫「{warehouse.name}」沒有 {''.join(abc_classes)} 類的料號（請先在「料號庫存設定」設定 ABC）")
    rows = [(b, it) for b, it, st in rows if _d(b.qty) != 0 or st is None or st.is_stock_item]
    c = StockCount(count_no=_next_no(db, warehouse.company_code, count_date), company_code=warehouse.company_code,
                   warehouse_id=warehouse.id, period=count_date.strftime("%Y-%m"), count_date=count_date,
                   cutoff_at=twnow(), blind=bool(warehouse.count_blind), status="counting", note=note,
                   count_type="cycle" if abc_classes else "full", abc_classes="".join(abc_classes) if abc_classes else None,
                   line_count=len(rows), created_by=user_name)
    db.add(c)
    db.flush()
    for b, it in rows:
        db.add(StockCountLine(count_id=c.id, item_id=it.id, book_qty=_d(b.qty), book_avg_cost=_d(b.avg_cost)))
    warehouse.status = "counting"
    db.flush()
    return c


def _lines(db: Session, c: StockCount) -> list[StockCountLine]:
    return db.query(StockCountLine).filter(StockCountLine.count_id == c.id).all()


def save_counts(db: Session, c: StockCount, entries: list[tuple[int, Optional[Decimal], Optional[str]]], user_name: str) -> int:
    """輸入實盤數：entries＝(料號 id, 實盤數或 None＝清空, 備註)。只有盤點中可輸入。"""
    if c.status != "counting":
        raise StockError(f"盤點表「{c.count_no}」{STATUS_LABEL[c.status]}，不能再輸入")
    by_item = {l.item_id: l for l in _lines(db, c)}
    now, n = twnow(), 0
    for item_id, qty, note in entries:
        l = by_item.get(item_id)
        if l is None:
            raise StockError(f"料號 id={item_id} 不在這張盤點表，請先「加入料號」")
        if qty is not None and _d(qty) < 0:
            raise StockError("實盤數不可為負數")
        l.counted_qty = None if qty is None else _d(qty).quantize(Q4, ROUND_HALF_UP)
        l.counted_by, l.counted_at = (user_name, now) if qty is not None else (None, None)
        if note is not None:
            l.note = note.strip() or None
        n += 1
    return n


def add_item(db: Session, c: StockCount, item: CyclePurchaseItem, user_name: str) -> StockCountLine:
    """盤到清單外的料號（例如帳上沒有但實際有）：加入一列，帳面數＝目前帳上（盤點中不會變）。"""
    if c.status != "counting":
        raise StockError("只有盤點中可以加入料號")
    if item.company_code != c.company_code:
        raise StockError("料號不屬於這家公司")
    if db.query(StockCountLine.id).filter(StockCountLine.count_id == c.id, StockCountLine.item_id == item.id).first():
        raise StockError(f"{item.item_code} 已在盤點表中")
    b = db.query(StockBalance).filter(StockBalance.warehouse_id == c.warehouse_id, StockBalance.item_id == item.id).first()
    l = StockCountLine(count_id=c.id, item_id=item.id, book_qty=_d(b.qty) if b else 0,
                       book_avg_cost=_d(b.avg_cost) if b else 0, added_manually=True)
    db.add(l)
    c.line_count = (c.line_count or 0) + 1
    db.flush()
    return l


def submit_count(db: Session, c: StockCount, fill_zero: bool, user_name: str) -> StockCount:
    if c.status != "counting":
        raise StockError(f"盤點表「{c.count_no}」{STATUS_LABEL[c.status]}，不能送出")
    lines = _lines(db, c)
    missing = [l for l in lines if l.counted_qty is None]
    if missing and not fill_zero:
        raise StockError(f"還有 {len(missing)} 項沒有盤（可勾選「未盤視為 0」後送出）")
    now = twnow()
    for l in missing:
        l.counted_qty, l.counted_by, l.counted_at = Decimal(0), user_name, now
    c.status, c.submitted_by, c.submitted_at = "submitted", user_name, now
    return c


def _gain_cost(l: StockCountLine, item: CyclePurchaseItem) -> Decimal:
    """盤盈計價：帳面平均單價；沒有（從未入庫）時用料號參考單價。"""
    if _d(l.book_avg_cost) > 0:
        return _d(l.book_avg_cost)
    return _d(item.unit_price) if item.unit_price is not None else Decimal(0)


def line_view(l: StockCountLine, item: CyclePurchaseItem) -> dict:
    """差異與是否需要複盤（審核畫面用）。"""
    diff = None if l.counted_qty is None else _d(l.counted_qty) - _d(l.book_qty)
    cost = _gain_cost(l, item) if (diff or 0) > 0 else _d(l.book_avg_cost)
    diff_amt = None if diff is None else (diff * cost).quantize(Q2, ROUND_HALF_UP)
    recount = False
    if diff:
        base = abs(_d(l.book_qty))
        recount = (base == 0 or abs(diff) / base > RECOUNT_PCT) or abs(diff_amt) >= RECOUNT_AMOUNT
    return {"diff_qty": None if diff is None else float(diff), "diff_amount": None if diff_amt is None else float(diff_amt),
            "est_unit_cost": float(cost), "needs_recount": recount}


def return_count(db: Session, c: StockCount, reason: str, item_ids: Optional[list[int]], user_name: str) -> StockCount:
    """退回重盤：回到盤點中；指定料號時只清掉那些料號的實盤數。"""
    if c.status != "submitted":
        raise StockError("只有「待審核」的盤點表可以退回重盤")
    if item_ids:
        for l in _lines(db, c):
            if l.item_id in item_ids:
                l.counted_qty, l.counted_by, l.counted_at = None, None, None
    c.status, c.closed_by, c.closed_at, c.close_reason = "counting", user_name, twnow(), f"退回重盤：{reason}"
    return c


def approve_count(db: Session, c: StockCount, user_name: str) -> StockCount:
    """核准：依差異寫盤點調整異動（盤盈以帳面平均單價或參考單價、盤虧以平均單價），倉庫恢復啟用。"""
    if c.status != "submitted":
        raise StockError("只有「待審核」的盤點表可以核准")
    wh = db.query(StockWarehouse).get(c.warehouse_id)
    lines = _lines(db, c)
    items = {i.id: i for i in db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id.in_([l.item_id for l in lines] or [0])).all()}
    gain, loss, n = Decimal(0), Decimal(0), 0
    for l in lines:
        diff = _d(l.counted_qty) - _d(l.book_qty)
        l.adj_qty = diff
        if diff == 0:
            l.unit_cost, l.adj_amount = _d(l.book_avg_cost), Decimal(0)
            continue
        it = items[l.item_id]
        m = svc.post_move(db, warehouse=wh, item=it, qty=diff, move_type="count_adjust", source_type="stock_count",
                          source_id=c.id, source_no=c.count_no, moved_at=c.count_date,
                          unit_cost=_gain_cost(l, it) if diff > 0 else None,
                          note=f"盤{'盈' if diff > 0 else '虧'}", user_name=user_name,
                          allow_status=("counting",), ignore_reserved=True)
        l.unit_cost, l.adj_amount = m.unit_cost, _d(m.amount)
        n += 1
        if diff > 0:
            gain += _d(m.amount)
        else:
            loss += -_d(m.amount)
    c.diff_count, c.gain_amount, c.loss_amount = n, gain, loss
    c.status, c.approved_by, c.approved_at = "approved", user_name, twnow()
    if wh.status == "counting":
        wh.status = "active"
    return c


def cancel_count(db: Session, c: StockCount, reason: Optional[str], user_name: str) -> StockCount:
    if c.status not in ("counting", "submitted"):
        raise StockError(f"盤點表「{c.count_no}」{STATUS_LABEL[c.status]}，不能取消")
    wh = db.query(StockWarehouse).get(c.warehouse_id)
    c.status, c.closed_by, c.closed_at, c.close_reason = "cancelled", user_name, twnow(), reason
    if wh.status == "counting":
        wh.status = "active"
    return c


# ── 月結 ───────────────────────────────────────────────────────────────────────

def _moves_upto(db: Session, wh_ids: list[int], end: date):
    """各 倉×料號 截至 end（含）的 數量、金額。"""
    rows = (db.query(StockMove.warehouse_id, StockMove.item_id, func.sum(StockMove.qty), func.sum(StockMove.amount))
            .filter(StockMove.warehouse_id.in_(wh_ids or [0]), StockMove.moved_at <= end)
            .group_by(StockMove.warehouse_id, StockMove.item_id).all())
    return {(w, i): (_d(q), _d(a)) for w, i, q, a in rows}


def close_checks(db: Session, code: str, period: str) -> dict:
    """月結前檢查：回傳 {ok, problems[], warehouses[]}（不寫任何資料）。"""
    start, end = period_bounds(period)
    problems: list[str] = []
    p = db.query(StockPeriod).filter(StockPeriod.company_code == code, StockPeriod.period == period).first()
    if p and p.status == "closed":
        problems.append(f"{period} 已月結")
    # 前面有異動的月份都要已月結
    earlier = {x for (x,) in db.query(StockMove.period).filter(StockMove.company_code == code, StockMove.period < period).distinct()}
    closed = {x for (x,) in db.query(StockPeriod.period).filter(StockPeriod.company_code == code, StockPeriod.status == "closed")}
    for x in sorted(earlier - closed):
        problems.append(f"{x} 有異動但尚未月結（請依月份順序月結）")
    if date.today() <= end:
        problems.append(f"{period} 尚未過完（今天 {date.today().isoformat()}），月底後才能月結")
    whs = db.query(StockWarehouse).filter(StockWarehouse.company_code == code).all()
    upto = _moves_upto(db, [w.id for w in whs], end)
    moved = {w for (w,) in db.query(StockMove.warehouse_id).filter(StockMove.company_code == code, StockMove.period == period).distinct()}
    approved = {w for (w,) in db.query(StockCount.warehouse_id).filter(StockCount.company_code == code, StockCount.period == period,
                                                                       StockCount.status == "approved",
                                                                       StockCount.count_type == "full").distinct()}
    wh_rows = []
    for w in sorted(whs, key=lambda x: x.name):
        has_stock = any(q != 0 for (wid, _), (q, _a) in upto.items() if wid == w.id)
        need = w.id in moved or has_stock
        st = "免盤（空倉）" if not need else ("已盤點" if w.id in approved else "未完成盤點")
        if w.status == "counting":
            st = "盤點中"
            problems.append(f"倉庫「{w.name}」盤點中，請先完成或取消盤點")
        elif need and w.id not in approved:
            problems.append(f"倉庫「{w.name}」{period} 沒有已核准的月底全盤（循環盤點不算）")
        wh_rows.append({"warehouse_id": w.id, "warehouse_name": w.name, "need_count": need, "status": st})
    pend = (db.query(StockIssue.doc_no).filter(StockIssue.company_code == code, StockIssue.status.in_(RESERVING_STATUSES),
                                               StockIssue.doc_date <= end).all())
    if pend:
        problems.append(f"還有 {len(pend)} 張未核准或未發料的領用單：{'、'.join(x for (x,) in pend[:5])}{'…' if len(pend) > 5 else ''}")
    changed = db.query(StockImportLine).filter(StockImportLine.company_code == code, StockImportLine.source_changed.is_(True)).count()
    if changed:
        problems.append(f"進貨匯入有 {changed} 筆「來源已異動」尚未處理")
    return {"ok": not problems, "problems": problems, "warehouses": wh_rows}


def close_period(db: Session, code: str, period: str, user_name: str) -> StockPeriod:
    chk = close_checks(db, code, period)
    if not chk["ok"]:
        raise StockError("不能月結：" + "；".join(chk["problems"]))
    start, end = period_bounds(period)
    whs = {w.id: w for w in db.query(StockWarehouse).filter(StockWarehouse.company_code == code).all()}
    opening = _moves_upto(db, list(whs), date.fromordinal(start.toordinal() - 1))
    closing = _moves_upto(db, list(whs), end)
    purch = {(w, i): (_d(q), _d(a)) for w, i, q, a in
             db.query(StockMove.warehouse_id, StockMove.item_id, func.sum(StockMove.qty), func.sum(StockMove.amount))
             .filter(StockMove.warehouse_id.in_(list(whs) or [0]), StockMove.moved_at >= start, StockMove.moved_at <= end,
                     StockMove.move_type.in_(PURCHASE_TYPES))
             .group_by(StockMove.warehouse_id, StockMove.item_id).all()}
    items = {i.id: i for i in db.query(CyclePurchaseItem).filter(
        CyclePurchaseItem.id.in_({i for _, i in closing} or {0})).all()}
    p = db.query(StockPeriod).filter(StockPeriod.company_code == code, StockPeriod.period == period).first()
    if p is None:
        p = StockPeriod(company_code=code, period=period)
        db.add(p)
    n, total = 0, Decimal(0)
    for key, (cq, ca) in closing.items():
        oq, oa = opening.get(key, (Decimal(0), Decimal(0)))
        pq, pa = purch.get(key, (Decimal(0), Decimal(0)))
        base_q = oq + pq
        if cq == 0:
            target = Decimal(0)                      # 月底沒有庫存：金額應歸零（清掉尾差）
        elif base_q > 0:
            w_avg = (oa + pa) / base_q               # 月加權平均（D3）
            target = (cq * w_avg).quantize(Q2, ROUND_HALF_UP)
        else:
            continue                                 # 沒有期初也沒有進貨（例如只有調入）：維持移動平均
        delta = target - ca
        if abs(delta) < Decimal("0.01"):
            continue
        m = svc.post_revalue(db, warehouse=whs[key[0]], item=items[key[1]], amount=delta, moved_at=end,
                             source_no=f"月結 {period}", note=f"{period} 月加權平均成本調整", user_name=user_name)
        if m:
            n += 1
            total += _d(m.amount)
    p.status, p.closed_by, p.closed_at = "closed", user_name, twnow()
    p.revalue_count, p.revalue_amount = n, total
    db.flush()
    return p


def reopen_period(db: Session, code: str, period: str, reason: str, user_name: str) -> StockPeriod:
    p = db.query(StockPeriod).filter(StockPeriod.company_code == code, StockPeriod.period == period).first()
    if not p or p.status != "closed":
        raise StockError(f"{period} 沒有月結，不需要反月結")
    later = (db.query(StockPeriod.period).filter(StockPeriod.company_code == code, StockPeriod.status == "closed",
                                                 StockPeriod.period > period).first())
    if later:
        raise StockError(f"{later[0]} 已月結，只能反最近一個已月結的月份")
    if (p.reopen_count or 0) >= 1:
        raise StockError(f"{period} 已反月結過一次，不能再反月結（規格 §8.6）")
    p.status, p.reopen_count = "open", (p.reopen_count or 0) + 1
    p.reopened_by, p.reopened_at, p.reopen_reason = user_name, twnow(), reason
    return p


# ── 進銷存月報 ─────────────────────────────────────────────────────────────────

REPORT_COLS = [
    ("receipt", ("receipt", "receipt_void"), "進貨"),
    ("opening", ("opening", "opening_void"), "期初開帳"),
    ("issue", ("issue",), "領用"),
    ("return", ("return", "return_void"), "退料"),
    ("transfer_in", ("transfer_in", "transfer_in_void"), "調撥入"),
    ("transfer_out", ("transfer_out", "transfer_out_void"), "調撥出"),
    ("scrap", ("scrap", "scrap_void"), "報廢"),
    ("count_adjust", ("count_adjust",), "盤盈虧"),
    ("cost_revalue", ("cost_revalue",), "成本調整"),
]


def monthly_report(db: Session, code: str, period: str, warehouse_ids: list[int]) -> list[dict]:
    """料號一列：期初、各類異動（數量＋金額）、期末。期初＝月初以前所有異動加總。"""
    start, end = period_bounds(period)
    col_of = {t: k for k, types, _ in REPORT_COLS for t in types}
    acc: dict[tuple[int, int], dict] = {}

    def row(key):
        r = acc.get(key)
        if r is None:
            r = acc[key] = {"open_qty": Decimal(0), "open_amt": Decimal(0),
                            **{f"{k}_qty": Decimal(0) for k, _, _ in REPORT_COLS},
                            **{f"{k}_amt": Decimal(0) for k, _, _ in REPORT_COLS}}
        return r

    for w, i, q, a in (db.query(StockMove.warehouse_id, StockMove.item_id, func.sum(StockMove.qty), func.sum(StockMove.amount))
                       .filter(StockMove.warehouse_id.in_(warehouse_ids or [0]), StockMove.moved_at < start)
                       .group_by(StockMove.warehouse_id, StockMove.item_id).all()):
        r = row((w, i))
        r["open_qty"], r["open_amt"] = _d(q), _d(a)
    for w, i, t, q, a in (db.query(StockMove.warehouse_id, StockMove.item_id, StockMove.move_type,
                                   func.sum(StockMove.qty), func.sum(StockMove.amount))
                          .filter(StockMove.warehouse_id.in_(warehouse_ids or [0]), StockMove.moved_at >= start,
                                  StockMove.moved_at <= end)
                          .group_by(StockMove.warehouse_id, StockMove.item_id, StockMove.move_type).all()):
        k = col_of.get(t)
        if k is None:
            continue
        r = row((w, i))
        r[f"{k}_qty"] += _d(q)
        r[f"{k}_amt"] += _d(a)
    items = {it.id: it for it in db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id.in_({i for _, i in acc} or {0})).all()}
    wname = dict(db.query(StockWarehouse.id, StockWarehouse.name).filter(StockWarehouse.id.in_(warehouse_ids or [0])).all())
    out = []
    for (w, i), r in acc.items():
        cq = r["open_qty"] + sum(r[f"{k}_qty"] for k, _, _ in REPORT_COLS)
        ca = r["open_amt"] + sum(r[f"{k}_amt"] for k, _, _ in REPORT_COLS)
        if all(v == 0 for v in r.values()) and cq == 0:
            continue
        it = items[i]
        # 周轉天數（Phase 7）＝平均庫存金額 ÷ 每日領用淨額；本月沒有領用＝不計
        consume = -(r["issue_amt"] + r["return_amt"])
        days_in = (end - start).days + 1
        avg_inv = (r["open_amt"] + ca) / 2
        turnover = None if consume <= 0 else float(round(avg_inv / (consume / days_in), 1))
        out.append({"warehouse_id": w, "warehouse_name": wname.get(w, ""), "item_id": i, "item_code": it.item_code,
                    "item_name": it.item_name, "spec": it.spec, "unit": it.unit,
                    **{k: float(v) for k, v in r.items()}, "close_qty": float(cq), "close_amt": float(ca),
                    "consume_amt": float(consume), "turnover_days": turnover})
    out.sort(key=lambda x: (x["warehouse_name"], x["item_code"]))
    return out
