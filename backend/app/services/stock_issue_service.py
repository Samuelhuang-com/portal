"""
庫存管理 Phase 4a：領用／退料／調撥／報廢 — docs/SPEC_stock_management.md §7

所有庫存數字仍只經由 stock_service.post_move()／reserve()／release() 變動；本檔只管單據狀態與規則。
呼叫端（router）負責權限與資料範圍判斷、負責 commit。

流程（D26～D29，2026-11-17 Samuel 裁示）：
  領用 issue   ：draft ─送出（保留）→ pending_approval（倉庫設定需核准）／approved（待發料）─倉管發料→ posted
                 draft／pending_approval／approved 可取消（釋放保留）；pending_approval 可退回（釋放保留）
                 已過帳不能改、不能作廢，只能開退料單
  退料 return  ：draft ─送出→ approved（待收料）─倉管收料→ posted；必須對應原領用單，不得超過「已領−已退」
  調撥 transfer：倉管開單 draft ─過帳→ posted（同公司、出倉入倉同時完成，入倉成本＝出倉平均單價）
  報廢 scrap   ：倉管開單 draft ─過帳→ posted（必填原因）
  退料／調撥／報廢已過帳可作廢（反向異動）
倉庫「盤點中」不能送出、不能過帳（D7）。
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.cycle_purchase_item import CyclePurchaseItem
from app.models.cycle_purchase_reference import CyclePurchaseCostCenter, CyclePurchaseDepartment
from app.models.stock import (
    RESERVING_STATUSES, StockBalance, StockIssue, StockIssueLine, StockIssueTemplate, StockIssueTemplateLine,
    StockItemSetting, StockWarehouse,
)
from app.services import stock_service as svc
from app.services.stock_service import StockError, _d

DOC_PREFIX = {"issue": "ISU", "return": "RTN", "transfer": "TRF", "scrap": "SCR"}
DOC_LABEL = {"issue": "領用單", "return": "退料單", "transfer": "調撥單", "scrap": "報廢單"}
STATUS_LABEL = {
    "draft": "草稿", "pending_approval": "待核准", "approved": "待發料", "posted": "已過帳",
    "cancelled": "已取消", "rejected": "已退回", "voided": "已作廢",
}
EDITABLE = ("draft",)
CANCELLABLE = ("draft", "pending_approval", "approved")
VOIDABLE_TYPES = ("return", "transfer", "scrap")


def status_label(doc: StockIssue) -> str:
    if doc.doc_type == "return" and doc.status == "approved":
        return "待收料"
    return STATUS_LABEL.get(doc.status, doc.status)


@dataclass
class LineIn:
    item_id: int
    qty: Decimal
    ref_line_id: Optional[int] = None
    note: Optional[str] = None


# ── 編號 ───────────────────────────────────────────────────────────────────────

def next_doc_no(db: Session, doc_type: str, code: str, d: date) -> str:
    prefix = f"{DOC_PREFIX[doc_type]}-{code}-{d.strftime('%Y%m')}-"
    last = (db.query(StockIssue.doc_no).filter(StockIssue.doc_no.like(prefix + "%"))
            .order_by(StockIssue.doc_no.desc()).with_for_update().first())
    seq = int(last[0][-3:]) + 1 if last else 1
    return f"{prefix}{seq:03d}"


# ── 成本中心 ──────────────────────────────────────────────────────────────────

def cost_centers(db: Session, code: str, department_id: Optional[str]) -> dict:
    """公司的成本中心；預設＝倉庫部門（主檔）所連結週採部門的預設成本中心。"""
    rows = (db.query(CyclePurchaseCostCenter, CyclePurchaseDepartment)
            .join(CyclePurchaseDepartment, CyclePurchaseDepartment.id == CyclePurchaseCostCenter.department_id)
            .filter(CyclePurchaseCostCenter.company_code == code, CyclePurchaseCostCenter.is_active.is_(True))
            .order_by(CyclePurchaseDepartment.dept_name, CyclePurchaseCostCenter.cc_code).all())
    default_id = None
    out = []
    for cc, dep in rows:
        mine = bool(department_id) and dep.source_department_id == str(department_id)
        if mine and (default_id is None or cc.is_default):
            default_id = cc.id
        out.append({"id": cc.id, "label": f"{cc.cc_code} {cc.cc_name}", "department_name": dep.dept_name,
                    "is_mine": mine})
    out.sort(key=lambda r: (not r["is_mine"], r["department_name"] or "", r["label"]))
    return {"default_id": default_id, "items": out}


def _cost_center_snapshot(db: Session, code: str, cc_id: Optional[int]) -> Optional[str]:
    if not cc_id:
        return None
    cc = db.query(CyclePurchaseCostCenter).get(cc_id)
    if not cc or cc.company_code != code or not cc.is_active:
        raise StockError("成本中心不存在或已停用")
    return f"{cc.cc_code} {cc.cc_name}"


# ── 可領用量／可退量 ─────────────────────────────────────────────────────────

def available_items(db: Session, warehouse_id: int, keyword: Optional[str] = None, limit: int = 500,
                    include_zero: bool = False) -> list[dict]:
    """include_zero：連目前可用量為 0 的料號也列出（列印 QR 標籤用，Phase 4b）。"""
    q = (db.query(StockBalance, CyclePurchaseItem)
         .join(CyclePurchaseItem, CyclePurchaseItem.id == StockBalance.item_id)
         .filter(StockBalance.warehouse_id == warehouse_id))
    if not include_zero:
        q = q.filter(StockBalance.qty - StockBalance.reserved_qty > 0)
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.filter((CyclePurchaseItem.item_code.ilike(kw)) | (CyclePurchaseItem.item_name.ilike(kw))
                     | (CyclePurchaseItem.spec.ilike(kw)))
    out = []
    for b, it in q.order_by(CyclePurchaseItem.item_code).limit(limit).all():
        out.append({"item_id": it.id, "item_code": it.item_code, "item_name": it.item_name, "spec": it.spec,
                    "unit": it.unit, "qty": float(b.qty), "reserved_qty": float(b.reserved_qty),
                    "available": float(_d(b.qty) - _d(b.reserved_qty)), "avg_cost": float(b.avg_cost)})
    return out


def returned_qty(db: Session, ref_line_id: int, exclude_issue_id: Optional[int] = None) -> Decimal:
    """原領用明細已退（含送出未收料）的數量。"""
    q = (db.query(func.coalesce(func.sum(StockIssueLine.qty), 0))
         .join(StockIssue, StockIssue.id == StockIssueLine.issue_id)
         .filter(StockIssueLine.ref_line_id == ref_line_id, StockIssue.doc_type == "return",
                 StockIssue.status.in_(("approved", "posted"))))
    if exclude_issue_id:
        q = q.filter(StockIssue.id != exclude_issue_id)
    return _d(q.scalar())


def returnable_lines(db: Session, issue: StockIssue, exclude_issue_id: Optional[int] = None) -> list[dict]:
    if issue.doc_type != "issue" or issue.status != "posted":
        raise StockError("只有已過帳的領用單可以退料")
    out = []
    for l, it in (db.query(StockIssueLine, CyclePurchaseItem)
                  .join(CyclePurchaseItem, CyclePurchaseItem.id == StockIssueLine.item_id)
                  .filter(StockIssueLine.issue_id == issue.id).order_by(StockIssueLine.id).all()):
        done = returned_qty(db, l.id, exclude_issue_id)
        out.append({"ref_line_id": l.id, "item_id": it.id, "item_code": it.item_code, "item_name": it.item_name,
                    "unit": it.unit, "issued_qty": float(l.qty), "returned_qty": float(done),
                    "returnable": float(_d(l.qty) - done), "unit_cost": float(_d(l.unit_cost))})
    return out


# ── 草稿 ───────────────────────────────────────────────────────────────────────

def _check_wh(wh: StockWarehouse, action: str):
    if wh.status == "inactive":
        raise StockError(f"倉庫「{wh.name}」已停用，不能{action}")
    if wh.status == "counting":
        raise StockError(f"倉庫「{wh.name}」盤點中，不能{action}（D7）")


def _items(db: Session, code: str, ids: list[int]) -> dict:
    items = {i.id: i for i in db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id.in_(ids or [0])).all()}
    settings = {s.item_id: s for s in db.query(StockItemSetting).filter(StockItemSetting.item_id.in_(ids or [0])).all()}
    for i in ids:
        it = items.get(i)
        if not it or it.company_code != code:
            raise StockError(f"找不到料號 id={i}")
        st = settings.get(i)
        if st is not None and not st.is_stock_item:
            raise StockError(f"{it.item_code} {it.item_name} 未納入庫存")
    return items


def save_draft(db: Session, *, doc: Optional[StockIssue], doc_type: str, code: str, warehouse: StockWarehouse,
               to_warehouse: Optional[StockWarehouse], doc_date: date, requester_name: Optional[str],
               requester_user_id: Optional[str], purpose: Optional[str], cost_center_id: Optional[int],
               account_code: Optional[str], ref_issue: Optional[StockIssue], lines: list[LineIn],
               user_name: str, user_id: str) -> StockIssue:
    if doc_type not in DOC_PREFIX:
        raise StockError("單據類型錯誤")
    if doc is not None and doc.status not in EDITABLE:
        raise StockError(f"{DOC_LABEL[doc.doc_type]}「{doc.doc_no}」已{status_label(doc)}，不能修改")
    if not lines:
        raise StockError("至少要有一筆料號")
    if any(_d(l.qty) <= 0 for l in lines):
        raise StockError("數量必須大於 0")
    _check_wh(warehouse, "開單")

    if doc_type == "transfer":
        if to_warehouse is None:
            raise StockError("調撥單要選調入倉")
        if to_warehouse.id == warehouse.id:
            raise StockError("調出倉與調入倉不能相同")
        if to_warehouse.company_code != warehouse.company_code:
            raise StockError("不能跨公司調撥（D6）")
        _check_wh(to_warehouse, "調入")
    else:
        to_warehouse = None
    if doc_type == "scrap" and not (purpose or "").strip():
        raise StockError("報廢單必須填寫報廢原因")

    if doc_type == "return":
        if ref_issue is None:
            raise StockError("退料單必須選擇原領用單")
        if ref_issue.company_code != code or ref_issue.warehouse_id != warehouse.id:
            raise StockError("退料只能退回原領用單的倉庫")
        ref_lines = {r["ref_line_id"]: r for r in returnable_lines(db, ref_issue, doc.id if doc else None)}
        seen = set()
        for l in lines:
            r = ref_lines.get(l.ref_line_id or 0)
            if r is None:
                raise StockError("退料明細必須對應原領用單的品項")
            if l.ref_line_id in seen:
                raise StockError("同一筆領用明細不能重複退料")
            seen.add(l.ref_line_id)
            l.item_id = r["item_id"]
            if _d(l.qty) > _d(r["returnable"]):
                raise StockError(f"{r['item_code']} 最多可退 {_d(r['returnable']).normalize():f}")
    else:
        ref_issue = None
        ids = [l.item_id for l in lines]
        if len(set(ids)) != len(ids):
            raise StockError("同一張單不可重複料號")
        for l in lines:
            l.ref_line_id = None
    _items(db, code, [l.item_id for l in lines])

    if doc is None:
        doc = StockIssue(doc_no=next_doc_no(db, doc_type, code, doc_date), doc_type=doc_type, company_code=code,
                         status="draft", created_by=user_name, created_by_user_id=user_id)
        db.add(doc)
    doc.warehouse_id = warehouse.id
    doc.to_warehouse_id = to_warehouse.id if to_warehouse else None
    doc.doc_date = doc_date
    doc.requester_name = (requester_name or "").strip() or user_name
    doc.requester_user_id = requester_user_id if doc.requester_name == user_name else None
    doc.department_id, doc.department_name = warehouse.department_id, warehouse.department_name
    doc.purpose = (purpose or "").strip() or None
    doc.cost_center_id = cost_center_id or None
    doc.cost_center_name = _cost_center_snapshot(db, code, cost_center_id)
    doc.account_code = (account_code or "").strip() or None
    doc.ref_issue_id = ref_issue.id if ref_issue else None
    doc.line_count = len(lines)
    db.flush()
    db.query(StockIssueLine).filter(StockIssueLine.issue_id == doc.id).delete(synchronize_session=False)
    for l in lines:
        db.add(StockIssueLine(issue_id=doc.id, item_id=l.item_id, qty=_d(l.qty), reserved_qty=0,
                              ref_line_id=l.ref_line_id, note=(l.note or None)))
    db.flush()
    return doc


# ── 狀態轉換 ──────────────────────────────────────────────────────────────────

def _lines(db: Session, doc: StockIssue) -> list[StockIssueLine]:
    return db.query(StockIssueLine).filter(StockIssueLine.issue_id == doc.id).order_by(StockIssueLine.id).all()


def _wh(db: Session, wid: Optional[int]) -> Optional[StockWarehouse]:
    return db.query(StockWarehouse).get(wid) if wid else None


def submit(db: Session, doc: StockIssue, user_name: str) -> StockIssue:
    if doc.doc_type not in ("issue", "return"):
        raise StockError("調撥／報廢單由倉管直接過帳，不需送出")
    if doc.status != "draft":
        raise StockError(f"這張單已{status_label(doc)}，不能送出")
    wh = _wh(db, doc.warehouse_id)
    _check_wh(wh, "送出領用單" if doc.doc_type == "issue" else "送出退料單")
    lines = _lines(db, doc)
    if not lines:
        raise StockError("至少要有一筆料號")
    items = _items(db, doc.company_code, [l.item_id for l in lines])
    if doc.doc_type == "issue":
        for l in lines:
            svc.reserve(db, warehouse=wh, item=items[l.item_id], qty=l.qty)
            l.reserved_qty = _d(l.qty)
        doc.status = "pending_approval" if wh.issue_requires_approval else "approved"
    else:
        ref = db.query(StockIssue).get(doc.ref_issue_id)
        remain = {r["ref_line_id"]: _d(r["returnable"]) for r in returnable_lines(db, ref, doc.id)}
        for l in lines:
            if _d(l.qty) > remain.get(l.ref_line_id, Decimal(0)):
                raise StockError(f"{items[l.item_id].item_code} 超過可退量 {remain.get(l.ref_line_id, Decimal(0)).normalize():f}")
        doc.status = "approved"
    doc.submitted_by, doc.submitted_at = user_name, twnow()
    return doc


def _release_all(db: Session, doc: StockIssue):
    for l in _lines(db, doc):
        if _d(l.reserved_qty) > 0:
            svc.release(db, warehouse_id=doc.warehouse_id, item_id=l.item_id, qty=l.reserved_qty)
            l.reserved_qty = 0


def approve(db: Session, doc: StockIssue, user_name: str) -> StockIssue:
    if doc.doc_type != "issue" or doc.status != "pending_approval":
        raise StockError("只有「待核准」的領用單可以核准")
    doc.status, doc.approved_by, doc.approved_at = "approved", user_name, twnow()
    return doc


def reject(db: Session, doc: StockIssue, reason: str, user_name: str) -> StockIssue:
    if doc.doc_type != "issue" or doc.status != "pending_approval":
        raise StockError("只有「待核准」的領用單可以退回")
    _release_all(db, doc)
    doc.status, doc.closed_by, doc.closed_at, doc.close_reason = "rejected", user_name, twnow(), reason
    return doc


def cancel(db: Session, doc: StockIssue, reason: Optional[str], user_name: str) -> StockIssue:
    if doc.status not in CANCELLABLE:
        raise StockError(f"這張單已{status_label(doc)}，不能取消")
    _release_all(db, doc)
    doc.status, doc.closed_by, doc.closed_at, doc.close_reason = "cancelled", user_name, twnow(), reason
    return doc


def post(db: Session, doc: StockIssue, post_date: date, user_name: str) -> StockIssue:
    """發料（領用）／收料（退料）／過帳（調撥、報廢）。"""
    need = "approved" if doc.doc_type in ("issue", "return") else "draft"
    if doc.status != need:
        if doc.doc_type == "issue" and doc.status == "pending_approval":
            raise StockError("領用單尚未核准，不能發料")
        if doc.doc_type == "return" and doc.status == "draft":
            raise StockError("退料單尚未送出，不能收料")
        raise StockError(f"這張單已{status_label(doc)}，不能過帳")
    wh = _wh(db, doc.warehouse_id)
    lines = _lines(db, doc)
    items = _items(db, doc.company_code, [l.item_id for l in lines])
    src = dict(source_type=f"stock_{doc.doc_type}", source_id=doc.id, source_no=doc.doc_no, moved_at=post_date,
               user_name=user_name)
    total = Decimal(0)
    if doc.doc_type == "issue":
        for l in lines:
            m = svc.post_move(db, warehouse=wh, item=items[l.item_id], qty=-_d(l.qty), move_type="issue",
                              release_reserved=_d(l.reserved_qty), note=doc.purpose, **src)
            l.reserved_qty, l.unit_cost, l.amount = 0, m.unit_cost, -_d(m.amount)
            total += -_d(m.amount)
    elif doc.doc_type == "return":
        ref = db.query(StockIssue).get(doc.ref_issue_id)
        remain = {r["ref_line_id"]: r for r in returnable_lines(db, ref, doc.id)}
        for l in lines:
            r = remain.get(l.ref_line_id)
            if r is None or _d(l.qty) > _d(r["returnable"]):
                raise StockError(f"{items[l.item_id].item_code} 超過可退量")
            m = svc.post_move(db, warehouse=wh, item=items[l.item_id], qty=_d(l.qty), unit_cost=_d(r["unit_cost"]),
                              move_type="return", note=doc.purpose, **src)
            l.unit_cost, l.amount = m.unit_cost, _d(m.amount)
            total += _d(m.amount)
    elif doc.doc_type == "transfer":
        to_wh = _wh(db, doc.to_warehouse_id)
        _check_wh(to_wh, "調入")
        for l in lines:
            out = svc.post_move(db, warehouse=wh, item=items[l.item_id], qty=-_d(l.qty), move_type="transfer_out",
                                note=f"調撥至 {to_wh.name}", **src)
            svc.post_move(db, warehouse=to_wh, item=items[l.item_id], qty=_d(l.qty), unit_cost=out.unit_cost,
                          move_type="transfer_in", note=f"由 {wh.name} 調入", **src)
            l.unit_cost, l.amount = out.unit_cost, -_d(out.amount)
            total += -_d(out.amount)
    else:  # scrap
        for l in lines:
            m = svc.post_move(db, warehouse=wh, item=items[l.item_id], qty=-_d(l.qty), move_type="scrap",
                              note=doc.purpose, **src)
            l.unit_cost, l.amount = m.unit_cost, -_d(m.amount)
            total += -_d(m.amount)
    doc.status, doc.posted_by, doc.posted_at, doc.posted_date = "posted", user_name, twnow(), post_date
    doc.total_amount = total
    if doc.doc_type in ("transfer", "scrap") and not doc.submitted_at:
        doc.submitted_by, doc.submitted_at = user_name, doc.posted_at
    return doc


def void(db: Session, doc: StockIssue, reason: str, user_name: str) -> StockIssue:
    if doc.doc_type not in VOIDABLE_TYPES:
        raise StockError("已過帳的領用單不能作廢，請開退料單")
    if doc.status != "posted":
        raise StockError("只有已過帳的單據可以作廢")
    wh = _wh(db, doc.warehouse_id)
    lines = _lines(db, doc)
    items = _items(db, doc.company_code, [l.item_id for l in lines])
    d = doc.posted_date or doc.doc_date
    src = dict(source_type=f"stock_{doc.doc_type}", source_id=doc.id, source_no=doc.doc_no, moved_at=d,
               user_name=user_name, note=f"作廢：{reason}")
    for l in lines:
        it = items[l.item_id]
        if doc.doc_type == "return":
            svc.post_move(db, warehouse=wh, item=it, qty=-_d(l.qty), move_type="return_void", **src)
        elif doc.doc_type == "scrap":
            svc.post_move(db, warehouse=wh, item=it, qty=_d(l.qty), unit_cost=_d(l.unit_cost), move_type="scrap_void", **src)
        else:
            to_wh = _wh(db, doc.to_warehouse_id)
            svc.post_move(db, warehouse=to_wh, item=it, qty=-_d(l.qty), move_type="transfer_in_void", **src)
            svc.post_move(db, warehouse=wh, item=it, qty=_d(l.qty), unit_cost=_d(l.unit_cost),
                          move_type="transfer_out_void", **src)
    doc.status, doc.closed_by, doc.closed_at, doc.close_reason = "voided", user_name, twnow(), reason
    return doc


def is_reserving(doc: StockIssue) -> bool:
    return doc.doc_type == "issue" and doc.status in RESERVING_STATUSES


# ── 領用範本（Phase 4b）────────────────────────────────────────────────────────

def template_out(db: Session, t: StockIssueTemplate) -> dict:
    bal = {b.item_id: b for b in db.query(StockBalance).filter(StockBalance.warehouse_id == t.warehouse_id).all()}
    lines = []
    for l, it in (db.query(StockIssueTemplateLine, CyclePurchaseItem)
                  .join(CyclePurchaseItem, CyclePurchaseItem.id == StockIssueTemplateLine.item_id)
                  .filter(StockIssueTemplateLine.template_id == t.id)
                  .order_by(StockIssueTemplateLine.sort_order, StockIssueTemplateLine.id).all()):
        b = bal.get(it.id)
        lines.append({"item_id": it.id, "item_code": it.item_code, "item_name": it.item_name, "spec": it.spec,
                      "unit": it.unit, "qty": float(l.qty),
                      "available": float(_d(b.qty) - _d(b.reserved_qty)) if b else 0.0})
    return {"id": t.id, "warehouse_id": t.warehouse_id, "name": t.name, "note": t.note, "lines": lines,
            "created_by": t.created_by, "created_by_user_id": t.created_by_user_id, "updated_by": t.updated_by,
            "updated_at": t.updated_at.strftime("%Y-%m-%d %H:%M") if t.updated_at else None}


def save_template(db: Session, *, tpl: Optional[StockIssueTemplate], code: str, warehouse: StockWarehouse, name: str,
                  note: Optional[str], lines: list[tuple[int, Decimal]], user_name: str, user_id: str) -> StockIssueTemplate:
    name = (name or "").strip()
    if not name:
        raise StockError("請輸入範本名稱")
    if not lines:
        raise StockError("範本至少要有一筆料號")
    ids = [i for i, _ in lines]
    if len(set(ids)) != len(ids):
        raise StockError("同一個範本不可重複料號")
    if any(_d(q) <= 0 for _, q in lines):
        raise StockError("數量必須大於 0")
    _items(db, code, ids)
    dup = (db.query(StockIssueTemplate.id).filter(StockIssueTemplate.warehouse_id == warehouse.id,
                                                  StockIssueTemplate.name == name))
    if tpl is not None:
        dup = dup.filter(StockIssueTemplate.id != tpl.id)
    if dup.first():
        raise StockError(f"這個倉已有名為「{name}」的範本")
    if tpl is None:
        tpl = StockIssueTemplate(company_code=code, warehouse_id=warehouse.id, created_by=user_name,
                                 created_by_user_id=user_id)
        db.add(tpl)
    tpl.name, tpl.note, tpl.updated_by = name, (note or "").strip() or None, user_name
    tpl.warehouse_id = warehouse.id
    db.flush()
    db.query(StockIssueTemplateLine).filter(StockIssueTemplateLine.template_id == tpl.id).delete(synchronize_session=False)
    for i, (item_id, qty) in enumerate(lines):
        db.add(StockIssueTemplateLine(template_id=tpl.id, item_id=item_id, qty=_d(qty), sort_order=i))
    db.flush()
    return tpl
