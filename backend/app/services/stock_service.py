"""
庫存核心服務（Phase 2）— docs/SPEC_stock_management.md §8

唯一入口：post_move()。所有進、出、調、盤差、期初都經由這裡寫 stock_moves 並同步更新 stock_balances，
同一個 transaction 內完成；呼叫端負責 commit。

規則：
  - 異動帳只新增，不修改、不刪除；更正用反向異動（*_void）
  - 不允許負庫存（D 定案）
  - 倉庫狀態非 active（停用／盤點中）不可過帳；呼叫端可用 allow_status 放行特定狀態（例如盤點調整）
  - 成本：入庫以傳入單價更新移動平均；出庫以目前平均單價計（月結時改月加權平均，Phase 5）
  - 期初開帳：倉庫只要有「期初以外」的異動，就不能再開期初或作廢期初
"""
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Optional

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.cycle_purchase_item import CyclePurchaseItem
from app.models.stock import StockBalance, StockMove, StockOpening, StockWarehouse

Q4 = Decimal("0.0001")
Q2 = Decimal("0.01")
OPENING_TYPES = ("opening", "opening_void")


class StockError(Exception):
    """業務規則錯誤（router 轉 409／422）。"""


def _d(v) -> Decimal:
    return Decimal(str(v if v is not None else 0))


def _lock_balance(db: Session, warehouse_id: int, item_id: int) -> StockBalance:
    db.execute(
        pg_insert(StockBalance.__table__)
        .values(warehouse_id=warehouse_id, item_id=item_id, qty=0, reserved_qty=0, avg_cost=0, amount=0)
        .on_conflict_do_nothing(index_elements=["warehouse_id", "item_id"])
    )
    return (db.query(StockBalance)
            .filter(StockBalance.warehouse_id == warehouse_id, StockBalance.item_id == item_id)
            .with_for_update().populate_existing().one())


def _apply(bal: StockBalance, qty: Decimal, unit_cost: Optional[Decimal]) -> tuple[Decimal, Decimal]:
    """把一筆異動套到 balance 上；回傳 (實際單位成本, 金額)。不檢查負庫存。"""
    old_qty, old_amt, avg = _d(bal.qty), _d(bal.amount), _d(bal.avg_cost)
    new_qty = old_qty + qty
    if qty > 0:
        cost = _d(unit_cost) if unit_cost is not None else avg
        amt = (qty * cost).quantize(Q2, ROUND_HALF_UP)
        new_amt = old_amt + amt
        new_avg = (new_amt / new_qty).quantize(Q4, ROUND_HALF_UP) if new_qty > 0 else cost
    else:
        cost = avg
        amt = (qty * cost).quantize(Q2, ROUND_HALF_UP)
        new_amt = Decimal(0) if new_qty == 0 else old_amt + amt
        new_avg = avg
    bal.qty, bal.amount, bal.avg_cost = new_qty, new_amt, new_avg
    return cost, amt


def ensure_period_open(db: Session, company_code: str, moved_at: date) -> None:
    """異動日期所屬月份已月結 → 擋下（Phase 5）。"""
    from app.models.stock import StockPeriod
    period = moved_at.strftime("%Y-%m")
    closed = (db.query(StockPeriod.id).filter(StockPeriod.company_code == company_code, StockPeriod.period == period,
                                              StockPeriod.status == "closed").first())
    if closed:
        raise StockError(f"{period} 已月結，不能再有異動（新增或作廢）；請在下個月開單更正，或請財務反月結")


def post_move(
    db: Session, *, warehouse: StockWarehouse, item: CyclePurchaseItem, qty, move_type: str,
    source_type: str, source_id=None, source_no: Optional[str] = None, moved_at: date,
    unit_cost=None, note: Optional[str] = None, user_name: Optional[str] = None,
    allow_status: Iterable[str] = ("active",), release_reserved=None, ignore_reserved: bool = False,
) -> StockMove:
    """release_reserved：這筆出庫同時釋放的保留量（領用單發料過帳用，Phase 4）。
    出庫時除了帳上不得為負，扣完後也不得低於「其他單據的保留量」（Phase 4：避免作廢進貨／報廢／調撥
    把已被領用單保留的數量拿走）。
    ignore_reserved：盤點調整用（Phase 5）——實物就是這麼多，盤虧可以讓帳上低於保留量（仍不得為負）。
    已月結的月份不能再有任何異動（Phase 5，§8.6）。"""
    qty = _d(qty).quantize(Q4, ROUND_HALF_UP)
    if qty == 0:
        raise StockError("異動數量不可為 0")
    if warehouse.status not in tuple(allow_status):
        label = {"inactive": "已停用", "counting": "盤點中"}.get(warehouse.status, warehouse.status)
        raise StockError(f"倉庫「{warehouse.name}」{label}，不能過帳")
    if item.company_code != warehouse.company_code:
        raise StockError(f"料號 {item.item_code} 不屬於倉庫「{warehouse.name}」的公司")
    ensure_period_open(db, warehouse.company_code, moved_at)
    bal = _lock_balance(db, warehouse.id, item.id)
    if release_reserved is not None:
        rel = _d(release_reserved)
        if rel < 0 or rel > _d(bal.reserved_qty):
            raise StockError(f"{item.item_code} 保留量不一致（帳上保留 {_d(bal.reserved_qty).normalize():f}），請先重算庫存")
        bal.reserved_qty = _d(bal.reserved_qty) - rel
    if _d(bal.qty) + qty < 0:
        raise StockError(f"{item.item_code} {item.item_name} 庫存不足：帳上 {_d(bal.qty).normalize():f}，本次扣 {(-qty).normalize():f}")
    if qty < 0 and not ignore_reserved and _d(bal.qty) + qty < _d(bal.reserved_qty):
        raise StockError(f"{item.item_code} {item.item_name} 可用量不足：帳上 {_d(bal.qty).normalize():f}，"
                         f"已被領用單保留 {_d(bal.reserved_qty).normalize():f}，本次扣 {(-qty).normalize():f}")
    cost, amt = _apply(bal, qty, None if unit_cost is None else _d(unit_cost))
    if bal.last_move_at is None or moved_at > bal.last_move_at:
        bal.last_move_at = moved_at
    m = StockMove(
        company_code=warehouse.company_code, warehouse_id=warehouse.id, item_id=item.id,
        qty=qty, unit_cost=cost, amount=amt, move_type=move_type, source_type=source_type,
        source_id=None if source_id is None else str(source_id), source_no=source_no,
        moved_at=moved_at, period=moved_at.strftime("%Y-%m"), note=note, created_by=user_name,
    )
    db.add(m)
    db.flush()
    return m


def post_revalue(db: Session, *, warehouse: StockWarehouse, item: CyclePurchaseItem, amount, moved_at: date,
                 source_id=None, source_no: Optional[str] = None, note: Optional[str] = None,
                 user_name: Optional[str] = None) -> Optional[StockMove]:
    """月結成本調整（Phase 5，D3 月加權平均）：數量 0、只調整金額。不檢查倉庫狀態與月結（由月結流程在標記已月結前呼叫）。"""
    amt = _d(amount).quantize(Q2, ROUND_HALF_UP)
    if amt == 0:
        return None
    bal = _lock_balance(db, warehouse.id, item.id)
    bal.amount = _d(bal.amount) + amt
    q = _d(bal.qty)
    bal.avg_cost = (_d(bal.amount) / q).quantize(Q4, ROUND_HALF_UP) if q > 0 else _d(bal.avg_cost)
    m = StockMove(company_code=warehouse.company_code, warehouse_id=warehouse.id, item_id=item.id, qty=0, unit_cost=0,
                  amount=amt, move_type="cost_revalue", source_type="period_close",
                  source_id=None if source_id is None else str(source_id), source_no=source_no, moved_at=moved_at,
                  period=moved_at.strftime("%Y-%m"), note=note, created_by=user_name)
    db.add(m)
    db.flush()
    return m


def reserve(db: Session, *, warehouse: StockWarehouse, item: CyclePurchaseItem, qty) -> None:
    """保留數量（領用單送出時，Phase 4）：可用量＝帳上 − 已保留，不足即拒絕。"""
    qty = _d(qty).quantize(Q4, ROUND_HALF_UP)
    if qty <= 0:
        raise StockError("保留數量必須大於 0")
    bal = _lock_balance(db, warehouse.id, item.id)
    avail = _d(bal.qty) - _d(bal.reserved_qty)
    if qty > avail:
        raise StockError(f"{item.item_code} {item.item_name} 可用量不足：可用 {avail.normalize():f}，本次領 {qty.normalize():f}")
    bal.reserved_qty = _d(bal.reserved_qty) + qty


def release(db: Session, *, warehouse_id: int, item_id: int, qty) -> None:
    """釋放保留（取消／退回）。保留量不會小於 0。"""
    qty = _d(qty)
    if qty <= 0:
        return
    bal = _lock_balance(db, warehouse_id, item_id)
    bal.reserved_qty = max(Decimal(0), _d(bal.reserved_qty) - qty)


def _open_reservations(db: Session, wh_ids: list[int]) -> dict:
    """由未結領用單重算保留量（Phase 4：保留量的唯一來源是 stock_issue_lines.reserved_qty）。"""
    from app.models.stock import RESERVING_STATUSES, StockIssue, StockIssueLine
    rows = (db.query(StockIssue.warehouse_id, StockIssueLine.item_id, func.sum(StockIssueLine.reserved_qty))
            .join(StockIssueLine, StockIssueLine.issue_id == StockIssue.id)
            .filter(StockIssue.warehouse_id.in_(wh_ids or [0]), StockIssue.status.in_(RESERVING_STATUSES))
            .group_by(StockIssue.warehouse_id, StockIssueLine.item_id).all())
    return {(w, i): _d(q) for w, i, q in rows if _d(q) > 0}


def rebuild_balances(db: Session, company_code: str) -> dict:
    """依 stock_moves 重算該公司所有倉的 stock_balances；reserved_qty 依未結領用單重算。"""
    wh_ids = [w for (w,) in db.query(StockWarehouse.id).filter(StockWarehouse.company_code == company_code).all()]
    reserved = _open_reservations(db, wh_ids)
    db.query(StockBalance).filter(StockBalance.warehouse_id.in_(wh_ids or [0])).delete(synchronize_session=False)
    acc: dict[tuple[int, int], StockBalance] = {}
    negative = []
    for m in (db.query(StockMove).filter(StockMove.warehouse_id.in_(wh_ids or [0]))
              .order_by(StockMove.moved_at, StockMove.id).all()):
        key = (m.warehouse_id, m.item_id)
        b = acc.get(key)
        if b is None:
            b = acc[key] = StockBalance(warehouse_id=m.warehouse_id, item_id=m.item_id, qty=0, amount=0,
                                        avg_cost=0, reserved_qty=reserved.get(key, 0))
        if _d(m.qty) == 0:   # 月結成本調整：只調金額（Phase 5）
            b.amount = _d(b.amount) + _d(m.amount)
            b.avg_cost = (_d(b.amount) / _d(b.qty)).quantize(Q4, ROUND_HALF_UP) if _d(b.qty) > 0 else _d(b.avg_cost)
        else:
            _apply(b, _d(m.qty), _d(m.unit_cost) if _d(m.qty) > 0 else None)
        b.last_move_at = m.moved_at if b.last_move_at is None or m.moved_at > b.last_move_at else b.last_move_at
        if _d(b.qty) < 0:
            negative.append(f"倉 {m.warehouse_id} 料號 {m.item_id} 於 {m.moved_at}")
    for key, r in reserved.items():
        if key not in acc and r:
            acc[key] = StockBalance(warehouse_id=key[0], item_id=key[1], qty=0, amount=0, avg_cost=0, reserved_qty=r)
    db.add_all(acc.values())
    db.flush()
    return {"balances": len(acc), "negative_points": negative[:50]}


# ── 期初開帳 ──────────────────────────────────────────────────────────────────

def has_non_opening_moves(db: Session, warehouse_id: int) -> bool:
    return db.query(StockMove.id).filter(StockMove.warehouse_id == warehouse_id,
                                         StockMove.move_type.notin_(OPENING_TYPES)).first() is not None


def _next_doc_no(db: Session, company_code: str, d: date) -> str:
    prefix = f"OPN-{company_code}-{d.strftime('%Y%m')}-"
    last = (db.query(StockOpening.doc_no).filter(StockOpening.doc_no.like(prefix + "%"))
            .order_by(StockOpening.doc_no.desc()).with_for_update().first())
    seq = int(last[0][-3:]) + 1 if last else 1
    return f"{prefix}{seq:03d}"


@dataclass
class OpeningLine:
    item_id: int
    qty: Decimal
    unit_cost: Decimal


def create_opening(db: Session, *, warehouse: StockWarehouse, opening_date: date, lines: list[OpeningLine],
                   note: Optional[str], user_name: str) -> StockOpening:
    if not lines:
        raise StockError("至少要有一筆料號")
    if has_non_opening_moves(db, warehouse.id):
        raise StockError(f"倉庫「{warehouse.name}」已有期初以外的異動，不能再開期初（請改用盤點調整）")
    ids = [l.item_id for l in lines]
    if len(set(ids)) != len(ids):
        raise StockError("同一張期初單不可重複料號")
    items = {i.id: i for i in db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id.in_(ids)).all()}
    for l in lines:
        it = items.get(l.item_id)
        if not it:
            raise StockError(f"找不到料號 id={l.item_id}")
        if l.qty <= 0:
            raise StockError(f"{it.item_code} 期初數量必須大於 0")
        if l.unit_cost < 0:
            raise StockError(f"{it.item_code} 單價不可為負數")
    doc = StockOpening(doc_no=_next_doc_no(db, warehouse.company_code, opening_date),
                       company_code=warehouse.company_code, warehouse_id=warehouse.id,
                       opening_date=opening_date, status="posted", note=note, created_by=user_name,
                       line_count=len(lines), total_amount=0)
    db.add(doc)
    db.flush()
    total = Decimal(0)
    for l in lines:
        m = post_move(db, warehouse=warehouse, item=items[l.item_id], qty=l.qty, unit_cost=l.unit_cost,
                      move_type="opening", source_type="opening", source_id=doc.id, source_no=doc.doc_no,
                      moved_at=opening_date, note=note, user_name=user_name)
        total += _d(m.amount)
    doc.total_amount = total
    return doc


def void_opening(db: Session, *, doc: StockOpening, warehouse: StockWarehouse, reason: str, user_name: str) -> StockOpening:
    if doc.status != "posted":
        raise StockError("這張期初單已作廢")
    if has_non_opening_moves(db, warehouse.id):
        raise StockError(f"倉庫「{warehouse.name}」已有期初以外的異動，不能作廢期初（請改用盤點調整）")
    moves = db.query(StockMove).filter(StockMove.source_type == "opening", StockMove.source_id == str(doc.id),
                                       StockMove.move_type == "opening").all()
    items = {i.id: i for i in db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id.in_([m.item_id for m in moves] or [0])).all()}
    for m in moves:
        post_move(db, warehouse=warehouse, item=items[m.item_id], qty=-_d(m.qty), move_type="opening_void",
                  source_type="opening", source_id=doc.id, source_no=doc.doc_no, moved_at=doc.opening_date,
                  note=f"作廢：{reason}", user_name=user_name)
    from app.core.time import twnow
    doc.status, doc.voided_by, doc.voided_at, doc.void_reason = "voided", user_name, twnow(), reason
    return doc


def stock_card(db: Session, warehouse_id: int, item_id: int) -> list[dict]:
    rows, run_qty, run_amt = [], Decimal(0), Decimal(0)
    for m in (db.query(StockMove).filter(StockMove.warehouse_id == warehouse_id, StockMove.item_id == item_id)
              .order_by(StockMove.moved_at, StockMove.id).all()):
        q = _d(m.qty)
        run_qty += q
        run_amt = Decimal(0) if run_qty == 0 else run_amt + _d(m.amount)
        rows.append({
            "id": m.id, "moved_at": m.moved_at.isoformat(), "move_type": m.move_type,
            "source_type": m.source_type, "source_id": m.source_id, "source_no": m.source_no,
            "in_qty": float(q) if q > 0 else None, "out_qty": float(-q) if q < 0 else None,
            "unit_cost": float(m.unit_cost), "amount": float(m.amount),
            "balance_qty": float(run_qty), "balance_amount": float(run_amt),
            "note": m.note, "created_by": m.created_by,
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else None,
        })
    return rows
