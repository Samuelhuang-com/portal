"""
庫存管理 API（/api/v1/stock）— docs/SPEC_stock_management.md

Phase 2（2026-11-17）庫存核心：倉庫、料號庫存設定、庫存總覽、庫存卡、期初開帳。
Phase 3（2026-11-17）進貨匯入：Ragic 採購單／請款單 → 待匯入清單 → 人工確認 → 進貨單過帳（§6）。
資料在週採資料庫（app/models/stock.py）；公司可見範圍由 stock_company_<代碼> 權限決定（stock_scope）。

權限：
  stock_balance_view     庫存（總覽、庫存卡）
  stock_settings_manage  庫存主檔設定（倉庫、料號庫存設定、重算庫存）
  stock_opening_manage   期初開帳（新增、作廢）
  stock_receipt_view     進貨匯入（待匯入清單、進貨單）
  stock_receipt_confirm  進貨匯入：重新整理待匯入、確認入庫、作廢進貨單、標記不入庫
  stock_issue_create     領用單：開領用／退料單（限所屬部門的倉）（Phase 4a）
  stock_issue_approve    領用單：核准（限所屬部門的倉）
  stock_issue_post       領用單：發料過帳／收退料／開調撥、報廢單（倉管，同公司所有倉）
  stock_count_execute    盤點（限所屬部門的倉）（Phase 5）
  stock_count_review     盤點：產生盤點表、審核盤盈虧
  stock_period_close     月結／反月結；進銷存月報用 stock_balance_view
  （Phase 1 的 Ragic 表單關聯已移到 /api/v1/settings/ragic-forms）
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.core.database import get_db
from app.dependencies import require_any_permission, require_permission
from app.models.cycle_purchase_category import CyclePurchaseCategory
from app.models.cycle_purchase_company import CyclePurchaseCompany
from app.models.cycle_purchase_item import CyclePurchaseItem
from app.models.reference_data import Company, RefDepartment
from app.models.stock import StockBalance, StockItemSetting, StockMove, StockOpening, StockWarehouse
from app.services.cycle_purchase_company_scope import resolve_company_code
from app.services.stock_scope import StockContext, stock_context
from app.services import stock_import_service as imp
from app.services import stock_service as svc

router = APIRouter()
VIEW = "stock_balance_view"
MANAGE = "stock_settings_manage"
OPENING = "stock_opening_manage"
RECEIPT_VIEW = "stock_receipt_view"
RECEIPT_CONFIRM = "stock_receipt_confirm"
_any = require_any_permission(VIEW, MANAGE, OPENING, RECEIPT_VIEW, RECEIPT_CONFIRM)
_receipt_any = require_any_permission(RECEIPT_VIEW, RECEIPT_CONFIRM)
# 公司選擇器：只開單領用的人也要能選公司（Phase 4a）；其餘主檔查詢仍用 _any
_company_any = require_any_permission(VIEW, MANAGE, OPENING, RECEIPT_VIEW, RECEIPT_CONFIRM,
                                      "stock_issue_create", "stock_issue_approve", "stock_issue_post",
                                      "stock_count_execute", "stock_count_review", "stock_period_close")
DEAD_DAYS = 90   # D17：90 天無異動＝呆滯料
MOVE_TYPE_LABEL = {
    "opening": "期初", "opening_void": "期初作廢", "receipt": "進貨", "receipt_void": "進貨作廢",
    "issue": "領用", "return": "退料", "transfer_in": "調撥入", "transfer_out": "調撥出",
    "scrap": "報廢", "count_adjust": "盤點調整",
    "return_void": "退料作廢", "transfer_in_void": "調撥入作廢", "transfer_out_void": "調撥出作廢", "scrap_void": "報廢作廢",
    "cost_revalue": "月結成本調整",
}


def _f(v) -> Optional[float]:
    return None if v is None else float(v)


def _business_error(e: svc.StockError):
    raise HTTPException(status_code=409, detail=str(e))


def _warehouse(cp: Session, ctx: StockContext, wid: int) -> StockWarehouse:
    w = cp.query(StockWarehouse).get(wid)
    if not w or w.company_code != ctx.code:
        raise HTTPException(status_code=404, detail="找不到倉庫")
    return w


# ── 公司／部門 ────────────────────────────────────────────────────────────────

@router.get("/companies", summary="使用者可見的公司")
def list_companies(ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
                   _=Depends(_company_any)):
    rows = cp.query(CyclePurchaseCompany).filter(CyclePurchaseCompany.code.in_(list(ctx.codes))).all()
    order = {"CH": 0, "OU": 1, "HO": 2}
    return {"default": ctx.code,
            "companies": [{"code": c.code, "name": c.name} for c in sorted(rows, key=lambda c: order.get(c.code, 9))]}


@router.get("/departments", summary="公司的主檔部門（settings/company-departments）")
def list_departments(ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                     cp: Session = Depends(get_cycle_purchase_db), _=Depends(_any)):
    out = []
    for comp in db.query(Company).filter(Company.is_active.is_(True)).all():
        if resolve_company_code(cp, comp.name) != ctx.code:
            continue
        for d in (db.query(RefDepartment).filter(RefDepartment.company_id == comp.id, RefDepartment.is_active.is_(True))
                  .order_by(RefDepartment.name).all()):
            out.append({"id": str(d.id), "name": d.name, "company_name": comp.name})
    return out


# ── 倉庫 ──────────────────────────────────────────────────────────────────────

class WarehouseIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    department_id: Optional[str] = None
    keeper_name: Optional[str] = Field(None, max_length=100)
    status: str = Field("active", pattern="^(active|inactive)$")
    issue_requires_approval: bool = False
    count_blind: bool = True
    notes: Optional[str] = None


def _dept_name(db: Session, cp: Session, ctx: StockContext, dept_id: Optional[str]) -> Optional[str]:
    if not dept_id:
        return None
    try:
        d = db.query(RefDepartment).get(int(dept_id))
    except ValueError:
        d = None
    if not d:
        raise HTTPException(status_code=422, detail="找不到部門")
    comp = db.query(Company).get(d.company_id)
    if not comp or resolve_company_code(cp, comp.name) != ctx.code:
        raise HTTPException(status_code=422, detail="部門不屬於這家公司")
    return d.name


@router.get("/warehouses", summary="倉庫清單")
def list_warehouses(include_inactive: bool = Query(True), ctx: StockContext = Depends(stock_context),
                    cp: Session = Depends(get_cycle_purchase_db), _=Depends(_any)):
    q = cp.query(StockWarehouse).filter(StockWarehouse.company_code == ctx.code)
    if not include_inactive:
        q = q.filter(StockWarehouse.status != "inactive")
    whs = q.order_by(StockWarehouse.name).all()
    stats = dict(((w, (n, a)) for w, n, a in
                  cp.query(StockBalance.warehouse_id, func.count(StockBalance.item_id), func.coalesce(func.sum(StockBalance.amount), 0))
                  .filter(StockBalance.warehouse_id.in_([w.id for w in whs] or [0]), StockBalance.qty != 0)
                  .group_by(StockBalance.warehouse_id).all()))
    moved = {w for (w,) in cp.query(StockMove.warehouse_id).filter(StockMove.warehouse_id.in_([w.id for w in whs] or [0]))
             .distinct().all()}
    return [{
        "id": w.id, "name": w.name, "department_id": w.department_id, "department_name": w.department_name,
        "keeper_name": w.keeper_name, "status": w.status, "notes": w.notes,
        "issue_requires_approval": bool(w.issue_requires_approval), "count_blind": bool(w.count_blind),
        "item_count": stats.get(w.id, (0, 0))[0], "amount": _f(stats.get(w.id, (0, 0))[1]),
        "has_moves": w.id in moved,
    } for w in whs]


@router.post("/warehouses", summary="新增倉庫")
def create_warehouse(body: WarehouseIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                     cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(MANAGE))):
    name = body.name.strip()
    if cp.query(StockWarehouse).filter(StockWarehouse.company_code == ctx.code, StockWarehouse.name == name).first():
        raise HTTPException(status_code=409, detail="同公司已有同名倉庫")
    w = StockWarehouse(company_code=ctx.code, name=name, department_id=body.department_id or None,
                       department_name=_dept_name(db, cp, ctx, body.department_id), keeper_name=body.keeper_name,
                       status=body.status, notes=body.notes, created_by=ctx.user_name,
                       issue_requires_approval=body.issue_requires_approval, count_blind=body.count_blind)
    cp.add(w)
    cp.flush()
    return {"id": w.id}


@router.put("/warehouses/{wid}", summary="修改倉庫")
def update_warehouse(wid: int, body: WarehouseIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                     cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(MANAGE))):
    w = _warehouse(cp, ctx, wid)
    if w.status == "counting":
        raise HTTPException(status_code=409, detail="倉庫盤點中，不能修改")
    name = body.name.strip()
    if cp.query(StockWarehouse).filter(StockWarehouse.company_code == ctx.code, StockWarehouse.name == name,
                                       StockWarehouse.id != w.id).first():
        raise HTTPException(status_code=409, detail="同公司已有同名倉庫")
    if body.status == "inactive" and w.status != "inactive":
        left = cp.query(StockBalance).filter(StockBalance.warehouse_id == w.id, StockBalance.qty != 0).count()
        if left:
            raise HTTPException(status_code=409, detail=f"倉庫還有 {left} 個料號有庫存，不能停用（請先調撥或盤點歸零）")
    w.name, w.keeper_name, w.status, w.notes = name, body.keeper_name, body.status, body.notes
    w.issue_requires_approval = body.issue_requires_approval
    w.count_blind = body.count_blind
    if (body.department_id or None) != w.department_id:
        w.department_id = body.department_id or None
        w.department_name = _dept_name(db, cp, ctx, body.department_id)
    return {"id": w.id}


# ── 料號庫存設定 ──────────────────────────────────────────────────────────────

class ItemSettingIn(BaseModel):
    is_stock_item: bool = True
    purchase_unit: Optional[str] = Field(None, max_length=20)
    unit_ratio: Decimal = Field(Decimal(1), gt=0)
    abc_class: Optional[str] = Field(None, pattern="^[ABC]?$")


class BulkSettingIn(BaseModel):
    item_ids: list[int] = Field(default_factory=list)
    category_id: Optional[int] = None
    is_stock_item: bool


def _category_label(c: Optional[CyclePurchaseCategory]) -> str:
    if not c:
        return ""
    return "／".join(x for x in (c.major_name, c.mid_name, c.sub_name) if x)


@router.get("/categories", summary="料號類別（公司）")
def list_categories(ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db), _=Depends(_any)):
    rows = (cp.query(CyclePurchaseCategory).filter(CyclePurchaseCategory.company_code == ctx.code,
                                                   CyclePurchaseCategory.is_active.is_(True))
            .order_by(CyclePurchaseCategory.major_code, CyclePurchaseCategory.mid_code, CyclePurchaseCategory.sub_code).all())
    return [{"id": c.id, "label": _category_label(c)} for c in rows]


@router.get("/items", summary="料號與庫存設定")
def list_items(keyword: Optional[str] = Query(None, max_length=100), category_id: Optional[int] = None,
               stock_only: bool = False, include_inactive: bool = False,
               ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db), _=Depends(_any)):
    q = (cp.query(CyclePurchaseItem, StockItemSetting, CyclePurchaseCategory)
         .outerjoin(StockItemSetting, StockItemSetting.item_id == CyclePurchaseItem.id)
         .outerjoin(CyclePurchaseCategory, CyclePurchaseCategory.id == CyclePurchaseItem.category_id)
         .filter(CyclePurchaseItem.company_code == ctx.code))
    if not include_inactive:
        q = q.filter(CyclePurchaseItem.is_active.is_(True))
    if category_id:
        q = q.filter(CyclePurchaseItem.category_id == category_id)
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(or_(CyclePurchaseItem.item_code.ilike(like), CyclePurchaseItem.item_name.ilike(like),
                         CyclePurchaseItem.spec.ilike(like)))
    if stock_only:
        q = q.filter(or_(StockItemSetting.item_id.is_(None), StockItemSetting.is_stock_item.is_(True)))
    rows = q.order_by(CyclePurchaseItem.item_code).limit(3000).all()
    qty = dict(cp.query(StockBalance.item_id, func.sum(StockBalance.qty))
               .join(StockWarehouse, StockWarehouse.id == StockBalance.warehouse_id)
               .filter(StockWarehouse.company_code == ctx.code).group_by(StockBalance.item_id).all())
    return [{
        "id": it.id, "item_code": it.item_code, "item_name": it.item_name, "spec": it.spec,
        "unit": it.unit, "category_id": it.category_id, "category": _category_label(cat) or (it.category or ""),
        "min_stock": it.min_stock, "max_stock": it.max_stock, "unit_price": _f(it.unit_price),
        "is_active": bool(it.is_active),
        "is_stock_item": True if st is None else bool(st.is_stock_item),
        "purchase_unit": st.purchase_unit if st else None,
        "unit_ratio": float(st.unit_ratio) if st else 1.0,
        "abc_class": st.abc_class if st else None,
        "has_setting": st is not None,
        "total_qty": _f(qty.get(it.id)),
    } for it, st, cat in rows]


def _item(cp: Session, ctx: StockContext, item_id: int) -> CyclePurchaseItem:
    it = cp.query(CyclePurchaseItem).get(item_id)
    if not it or it.company_code != ctx.code:
        raise HTTPException(status_code=404, detail="找不到料號")
    return it


def _upsert_setting(cp: Session, item_id: int, user: str, **vals) -> None:
    st = cp.query(StockItemSetting).get(item_id)
    if st is None:
        st = StockItemSetting(item_id=item_id)
        cp.add(st)
    for k, v in vals.items():
        setattr(st, k, v)
    st.updated_by = user


@router.put("/items/{item_id}/setting", summary="修改料號庫存設定")
def update_item_setting(item_id: int, body: ItemSettingIn, ctx: StockContext = Depends(stock_context),
                        cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(MANAGE))):
    it = _item(cp, ctx, item_id)
    if not body.is_stock_item:
        left = cp.query(func.coalesce(func.sum(StockBalance.qty), 0)).filter(StockBalance.item_id == it.id).scalar()
        if Decimal(str(left)) != 0:
            raise HTTPException(status_code=409, detail=f"{it.item_code} 還有庫存 {float(left):g}，不能改為不納入庫存")
    _upsert_setting(cp, it.id, ctx.user_name, is_stock_item=body.is_stock_item,
                    purchase_unit=(body.purchase_unit or None), unit_ratio=body.unit_ratio, abc_class=(body.abc_class or None))
    return {"id": it.id}


@router.post("/items/settings/bulk", summary="批次設定是否納入庫存（依勾選料號或類別）")
def bulk_item_setting(body: BulkSettingIn, ctx: StockContext = Depends(stock_context),
                      cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(MANAGE))):
    q = cp.query(CyclePurchaseItem).filter(CyclePurchaseItem.company_code == ctx.code)
    if body.item_ids:
        q = q.filter(CyclePurchaseItem.id.in_(body.item_ids))
    elif body.category_id:
        q = q.filter(CyclePurchaseItem.category_id == body.category_id)
    else:
        raise HTTPException(status_code=422, detail="請勾選料號或指定類別")
    items = q.all()
    skipped = []
    if not body.is_stock_item:
        left = dict(cp.query(StockBalance.item_id, func.sum(StockBalance.qty))
                    .filter(StockBalance.item_id.in_([i.id for i in items] or [0])).group_by(StockBalance.item_id).all())
        skipped = [i.item_code for i in items if Decimal(str(left.get(i.id) or 0)) != 0]
    done = 0
    for it in items:
        if it.item_code in skipped:
            continue
        _upsert_setting(cp, it.id, ctx.user_name, is_stock_item=body.is_stock_item)
        done += 1
    return {"updated": done, "skipped_with_stock": skipped}


# ── 庫存總覽／庫存卡 ──────────────────────────────────────────────────────────

@router.get("/balance", summary="庫存總覽")
def get_balance(warehouse_id: Optional[int] = None, keyword: Optional[str] = Query(None, max_length=100),
                category_id: Optional[int] = None, low_only: bool = False, dead_only: bool = False,
                include_zero: bool = False, ctx: StockContext = Depends(stock_context),
                cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(VIEW))):
    q = (cp.query(StockBalance, StockWarehouse, CyclePurchaseItem, CyclePurchaseCategory)
         .join(StockWarehouse, StockWarehouse.id == StockBalance.warehouse_id)
         .join(CyclePurchaseItem, CyclePurchaseItem.id == StockBalance.item_id)
         .outerjoin(CyclePurchaseCategory, CyclePurchaseCategory.id == CyclePurchaseItem.category_id)
         .filter(StockWarehouse.company_code == ctx.code))
    if warehouse_id:
        q = q.filter(StockBalance.warehouse_id == warehouse_id)
    if not include_zero:
        q = q.filter(or_(StockBalance.qty != 0, StockBalance.reserved_qty != 0))
    if category_id:
        q = q.filter(CyclePurchaseItem.category_id == category_id)
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(or_(CyclePurchaseItem.item_code.ilike(like), CyclePurchaseItem.item_name.ilike(like)))
    today = date.today()
    dead_before = today - timedelta(days=DEAD_DAYS)
    rows = []
    for b, w, it, cat in q.order_by(StockWarehouse.name, CyclePurchaseItem.item_code).all():
        qty, res = float(b.qty), float(b.reserved_qty)
        low = it.min_stock is not None and qty < it.min_stock
        over = it.max_stock is not None and it.max_stock > 0 and qty > it.max_stock
        dead = qty > 0 and (b.last_move_at is None or b.last_move_at < dead_before)
        if low_only and not low:
            continue
        if dead_only and not dead:
            continue
        rows.append({
            "warehouse_id": w.id, "warehouse_name": w.name, "warehouse_status": w.status,
            "item_id": it.id, "item_code": it.item_code, "item_name": it.item_name, "spec": it.spec,
            "unit": it.unit, "category": _category_label(cat) or (it.category or ""),
            "qty": qty, "reserved_qty": res, "available_qty": qty - res,
            "avg_cost": float(b.avg_cost), "amount": float(b.amount),
            "min_stock": it.min_stock, "max_stock": it.max_stock,
            "last_move_at": b.last_move_at.isoformat() if b.last_move_at else None,
            "is_low": low, "is_over": over, "is_dead": dead,
        })
    summary = {
        "rows": len(rows), "items": len({r["item_id"] for r in rows}),
        "amount": round(sum(r["amount"] for r in rows), 2),
        "low": sum(1 for r in rows if r["is_low"]), "dead": sum(1 for r in rows if r["is_dead"]),
    }
    last = cp.query(func.max(StockMove.moved_at)).filter(StockMove.company_code == ctx.code).scalar()
    return {"summary": summary, "rows": rows, "data_end": last.isoformat() if last else None, "dead_days": DEAD_DAYS}


@router.get("/stock-card", summary="料號庫存卡（某倉某料號的所有異動）")
def get_stock_card(warehouse_id: int, item_id: int, ctx: StockContext = Depends(stock_context),
                   cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(VIEW))):
    w = _warehouse(cp, ctx, warehouse_id)
    it = _item(cp, ctx, item_id)
    b = cp.query(StockBalance).get((w.id, it.id))
    rows = svc.stock_card(cp, w.id, it.id)
    for r in rows:
        r["move_type_label"] = MOVE_TYPE_LABEL.get(r["move_type"], r["move_type"])
    return {
        "warehouse": {"id": w.id, "name": w.name, "department_name": w.department_name},
        "item": {"id": it.id, "item_code": it.item_code, "item_name": it.item_name, "spec": it.spec, "unit": it.unit,
                 "min_stock": it.min_stock, "max_stock": it.max_stock},
        "balance": None if b is None else {"qty": float(b.qty), "reserved_qty": float(b.reserved_qty),
                                           "avg_cost": float(b.avg_cost), "amount": float(b.amount)},
        "moves": rows,
    }


@router.post("/balances/rebuild", summary="依異動帳重算庫存（管理用）")
def rebuild(ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
            _=Depends(require_permission(MANAGE))):
    return svc.rebuild_balances(cp, ctx.code)


# ── 期初開帳 ──────────────────────────────────────────────────────────────────

class OpeningLineIn(BaseModel):
    item_id: int
    qty: Decimal = Field(..., gt=0)
    unit_cost: Decimal = Field(Decimal(0), ge=0)


class OpeningIn(BaseModel):
    warehouse_id: int
    opening_date: date
    note: Optional[str] = None
    lines: list[OpeningLineIn] = Field(..., min_length=1, max_length=2000)


class VoidIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


def _opening_out(o: StockOpening, wname: dict) -> dict:
    return {"id": o.id, "doc_no": o.doc_no, "warehouse_id": o.warehouse_id, "warehouse_name": wname.get(o.warehouse_id, ""),
            "opening_date": o.opening_date.isoformat(), "status": o.status, "note": o.note,
            "line_count": o.line_count, "total_amount": _f(o.total_amount), "created_by": o.created_by,
            "created_at": o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else None,
            "voided_by": o.voided_by, "void_reason": o.void_reason}


@router.get("/openings", summary="期初開帳單清單")
def list_openings(ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db), _=Depends(_any)):
    wname = dict(cp.query(StockWarehouse.id, StockWarehouse.name).filter(StockWarehouse.company_code == ctx.code).all())
    rows = cp.query(StockOpening).filter(StockOpening.company_code == ctx.code).order_by(StockOpening.id.desc()).all()
    return [_opening_out(o, wname) for o in rows]


@router.get("/openings/{oid}", summary="期初開帳單明細")
def get_opening(oid: int, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db), _=Depends(_any)):
    o = cp.query(StockOpening).get(oid)
    if not o or o.company_code != ctx.code:
        raise HTTPException(status_code=404, detail="找不到期初單")
    wname = dict(cp.query(StockWarehouse.id, StockWarehouse.name).filter(StockWarehouse.company_code == ctx.code).all())
    lines = (cp.query(StockMove, CyclePurchaseItem).join(CyclePurchaseItem, CyclePurchaseItem.id == StockMove.item_id)
             .filter(StockMove.source_type == "opening", StockMove.source_id == str(o.id), StockMove.move_type == "opening")
             .order_by(CyclePurchaseItem.item_code).all())
    out = _opening_out(o, wname)
    out["lines"] = [{"item_id": it.id, "item_code": it.item_code, "item_name": it.item_name, "unit": it.unit,
                     "qty": float(m.qty), "unit_cost": float(m.unit_cost), "amount": float(m.amount)} for m, it in lines]
    return out


@router.get("/openings-check/{warehouse_id}", summary="倉庫是否還能開期初")
def opening_check(warehouse_id: int, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
                  _=Depends(_any)):
    w = _warehouse(cp, ctx, warehouse_id)
    blocked = svc.has_non_opening_moves(cp, w.id)
    return {"allowed": (not blocked) and w.status == "active",
            "reason": "已有期初以外的異動" if blocked else ("" if w.status == "active" else "倉庫不是啟用狀態")}


@router.post("/openings", summary="新增期初開帳單（直接過帳）")
def create_opening(body: OpeningIn, ctx: StockContext = Depends(stock_context),
                   cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(OPENING))):
    w = _warehouse(cp, ctx, body.warehouse_id)
    items = {i.id: i for i in cp.query(CyclePurchaseItem).filter(CyclePurchaseItem.id.in_([l.item_id for l in body.lines])).all()}
    for l in body.lines:
        it = items.get(l.item_id)
        if not it or it.company_code != ctx.code:
            raise HTTPException(status_code=422, detail=f"料號 id={l.item_id} 不屬於這家公司")
        st = cp.query(StockItemSetting).get(it.id)
        if st is not None and not st.is_stock_item:
            raise HTTPException(status_code=422, detail=f"{it.item_code} 設定為不納入庫存")
    try:
        doc = svc.create_opening(cp, warehouse=w, opening_date=body.opening_date, note=body.note, user_name=ctx.user_name,
                                 lines=[svc.OpeningLine(l.item_id, l.qty, l.unit_cost) for l in body.lines])
    except svc.StockError as e:
        _business_error(e)
    return {"id": doc.id, "doc_no": doc.doc_no, "total_amount": _f(doc.total_amount)}


@router.post("/openings/{oid}/void", summary="作廢期初開帳單（產生反向異動）")
def void_opening(oid: int, body: VoidIn, ctx: StockContext = Depends(stock_context),
                 cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(OPENING))):
    o = cp.query(StockOpening).get(oid)
    if not o or o.company_code != ctx.code:
        raise HTTPException(status_code=404, detail="找不到期初單")
    w = _warehouse(cp, ctx, o.warehouse_id)
    try:
        svc.void_opening(cp, doc=o, warehouse=w, reason=body.reason.strip(), user_name=ctx.user_name)
    except svc.StockError as e:
        _business_error(e)
    return {"id": o.id, "status": o.status}


# ═══════════════════════════════════════════════════════════════════════════
# Phase 3 進貨匯入（§6）
# ═══════════════════════════════════════════════════════════════════════════
from app.models.stock import StockImportLine, StockReceipt, StockReceiptItem  # noqa: E402

IMPORT_STATUS_LABEL = {"pending": "待確認", "partial": "部分匯入", "done": "已匯入", "non_stock": "不入庫",
                       "pre_opening": "開帳前不入庫", "linked_po": "已對應採購單"}
SOURCE_LABEL = {"ragic_po": "採購單", "ragic_claim": "請款單"}
SOURCE_STATUS_LABEL = {"ok": "", "changed": "來源已異動", "deleted": "Ragic 已刪除", "rejected": "Ragic 已退回"}


def _line_out(l: StockImportLine) -> dict:
    qty = _f(l.qty)
    imported = float(l.imported_qty or 0)
    return {
        "id": l.id, "source_type": l.source_type, "source_label": SOURCE_LABEL.get(l.source_type, l.source_type),
        "doc_no": l.doc_no, "po_no": l.po_no, "suspected_po_no": l.suspected_po_no, "department": l.department,
        "doc_date": l.doc_date.isoformat() if l.doc_date else None, "vendor_name": l.vendor_name,
        "item_code": l.item_code, "product_name": l.product_name, "qty": qty, "qty_raw": l.qty_raw, "unit": l.unit,
        "unit_price": _f(l.unit_price), "amount": _f(l.amount), "imported_qty": imported,
        "remaining_qty": None if qty is None else max(qty - imported, 0),
        "status": l.status, "status_label": IMPORT_STATUS_LABEL.get(l.status, l.status), "status_reason": l.status_reason,
        "marked_by": l.marked_by,
        "source_status": l.source_status, "source_status_label": SOURCE_STATUS_LABEL.get(l.source_status, l.source_status),
        "source_changed": bool(l.source_changed), "ragic_url": imp.ragic_url(l), "ragic_id": l.ragic_record_id,
    }


@router.get("/imports", summary="待匯入清單")
def list_imports(status: list[str] = Query(default=[]), source_type: Optional[str] = Query(None, pattern="^(ragic_po|ragic_claim)$"),
                 department: Optional[str] = None, keyword: Optional[str] = Query(None, max_length=100),
                 start: Optional[date] = None, end: Optional[date] = None, only_changed: bool = False,
                 limit: int = Query(3000, ge=1, le=10000),
                 ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
                 db: Session = Depends(get_db), _=Depends(_receipt_any)):
    base = cp.query(StockImportLine).filter(StockImportLine.company_code == ctx.code)
    q = base
    if status:
        q = q.filter(StockImportLine.status.in_(status))
    if source_type:
        q = q.filter(StockImportLine.source_type == source_type)
    if department:
        q = q.filter(StockImportLine.department == department)
    if start:
        q = q.filter(StockImportLine.doc_date >= start)
    if end:
        q = q.filter(StockImportLine.doc_date <= end)
    if only_changed:
        q = q.filter(StockImportLine.source_changed.is_(True))
    elif not status or set(status) & {"pending", "partial"}:
        # 未匯入且 Ragic 已刪除／退回的列不再出現在待確認（已匯入的仍顯示，供處理）
        q = q.filter(or_(StockImportLine.source_status == "ok", StockImportLine.imported_qty > 0))
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(or_(StockImportLine.doc_no.ilike(like), StockImportLine.product_name.ilike(like),
                         StockImportLine.vendor_name.ilike(like), StockImportLine.po_no.ilike(like)))
    total = q.count()
    rows = q.order_by(StockImportLine.doc_date.desc().nullslast(), StockImportLine.doc_no, StockImportLine.id).limit(limit).all()
    counts = dict(base.with_entities(StockImportLine.status, func.count(StockImportLine.id))
                  .filter(or_(StockImportLine.source_status == "ok", StockImportLine.imported_qty > 0))
                  .group_by(StockImportLine.status).all())
    changed = base.filter(StockImportLine.source_changed.is_(True)).count()
    depts = sorted({d for (d,) in base.with_entities(StockImportLine.department).distinct().all() if d})
    last = base.with_entities(func.max(StockImportLine.doc_date)).scalar()
    refreshed = base.with_entities(func.max(StockImportLine.refreshed_at)).scalar()
    # 2026-11-17：附件數（來源 Ragic 單據的檔案欄位），清單顯示迴紋針 icon 用
    att = imp.attachment_counts(db, ctx.code, rows)
    return {"total": total, "rows": [{**_line_out(l), "attachment_count": att.get(l.id, 0)} for l in rows], "status_counts": counts, "changed_count": changed,
            "departments": depts, "data_end": last.isoformat() if last else None,
            "refreshed_at": refreshed.strftime("%Y-%m-%d %H:%M") if refreshed else None}


@router.post("/imports/refresh", summary="依 Ragic 同步資料重新產生待匯入清單")
def refresh_imports(ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                    cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(RECEIPT_CONFIRM))):
    try:
        return imp.refresh_candidates(db, cp, ctx.code)
    except svc.StockError as e:
        _business_error(e)


@router.get("/imports/{line_id}", summary="待匯入品項明細（含 Ragic 來源單頭）")
def get_import(line_id: int, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
               db: Session = Depends(get_db), _=Depends(_receipt_any)):
    l = cp.query(StockImportLine).get(line_id)
    if not l or l.company_code != ctx.code:
        raise HTTPException(status_code=404, detail="找不到待匯入品項")
    out = _line_out(l)
    hist = (cp.query(StockReceiptItem, StockReceipt).join(StockReceipt, StockReceipt.id == StockReceiptItem.receipt_id)
            .filter(StockReceiptItem.import_line_id == l.id).order_by(StockReceipt.id).all())
    out["receipts"] = [{"receipt_id": r.id, "receipt_no": r.receipt_no, "receipt_date": r.receipt_date.isoformat(),
                        "status": r.status, "purchase_qty": float(ri.purchase_qty), "stock_qty": float(ri.stock_qty),
                        "unit_cost": float(ri.unit_cost), "amount": float(ri.amount), "override_reason": ri.override_reason}
                       for ri, r in hist]
    out["detail"] = {
        "來源": SOURCE_LABEL.get(l.source_type, l.source_type), "單號": l.doc_no or "", "對應採購單": l.po_no or "",
        "疑似採購單": l.suspected_po_no or "", "部門": l.department or "", "日期": out["doc_date"] or "",
        "廠商／受款者": l.vendor_name or "", "Ragic 料號": l.item_code or "", "品名": l.product_name or "",
        "數量": f"{l.qty_raw or ''} {l.unit or ''}".strip(), "單價（未稅）": "" if l.unit_price is None else f"{float(l.unit_price):,.4g}",
        "金額（未稅）": "" if l.amount is None else f"{float(l.amount):,.2f}", "已匯入量": f"{float(l.imported_qty or 0):g}",
        "狀態": out["status_label"], "狀態說明": l.status_reason or "", "Ragic 來源狀態": out["source_status_label"] or "正常",
    }
    # 2026-11-17：來源 Ragic 單據的附件（報價單、發票、照片…），Drawer「附件」區塊
    out["attachments"] = imp.attachments_for_line(db, ctx.code, l)
    return out


@router.get("/imports/{line_id}/suggest", summary="料號建議（品名對照＋相似度）")
def suggest(line_id: int, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
            _=Depends(_receipt_any)):
    l = cp.query(StockImportLine).get(line_id)
    if not l or l.company_code != ctx.code:
        raise HTTPException(status_code=404, detail="找不到待匯入品項")
    return imp.suggest_items(cp, ctx.code, l)


class MarkIn(BaseModel):
    line_ids: list[int] = Field(..., min_length=1)
    status: str = Field(..., pattern="^(non_stock|pre_opening|pending)$")
    reason: Optional[str] = Field(None, max_length=500)
    remember_non_stock: bool = False


@router.post("/imports/mark", summary="標記不入庫／開帳前／改回待確認")
def mark(body: MarkIn, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
         _=Depends(require_permission(RECEIPT_CONFIRM))):
    try:
        return imp.mark_lines(cp, code=ctx.code, line_ids=body.line_ids, status=body.status, reason=body.reason,
                              user_name=ctx.user_name, remember_non_stock=body.remember_non_stock)
    except svc.StockError as e:
        _business_error(e)


class MarkBeforeIn(BaseModel):
    before_date: date


@router.post("/imports/mark-before", summary="開帳前舊單據整批標「開帳前，不入庫」（D19）")
def mark_before(body: MarkBeforeIn, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
                _=Depends(require_permission(RECEIPT_CONFIRM))):
    return {"updated": imp.mark_before(cp, code=ctx.code, before=body.before_date, user_name=ctx.user_name)}


@router.post("/imports/{line_id}/ack-change", summary="來源已異動：人工確認後清除標示")
def ack_change(line_id: int, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
               _=Depends(require_permission(RECEIPT_CONFIRM))):
    l = cp.query(StockImportLine).get(line_id)
    if not l or l.company_code != ctx.code:
        raise HTTPException(status_code=404, detail="找不到待匯入品項")
    l.source_changed = False
    if l.source_status == "changed":
        l.source_status = "ok"
    l.marked_by = ctx.user_name
    return {"id": l.id}


class ReceiptLineIn(BaseModel):
    import_line_id: int
    item_id: int
    purchase_qty: Decimal = Field(..., gt=0)
    unit_ratio: Decimal = Field(Decimal(1), gt=0)
    unit_price: Optional[Decimal] = Field(None, ge=0, description="採購單位未稅單價；空白＝用來源單價")
    override_reason: Optional[str] = Field(None, max_length=500)
    remember_alias: bool = True
    remember_ratio: bool = False


class ReceiptIn(BaseModel):
    warehouse_id: int
    receipt_date: date
    note: Optional[str] = None
    lines: list[ReceiptLineIn] = Field(..., min_length=1, max_length=500)


@router.post("/receipts", summary="確認入庫（產生進貨單並過帳）")
def create_receipt(body: ReceiptIn, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
                   _=Depends(require_permission(RECEIPT_CONFIRM))):
    w = _warehouse(cp, ctx, body.warehouse_id)
    try:
        r = imp.confirm_receipt(cp, code=ctx.code, warehouse=w, receipt_date=body.receipt_date, note=body.note,
                                lines=[l.model_dump() for l in body.lines], user_name=ctx.user_name)
    except svc.StockError as e:
        _business_error(e)
    return {"id": r.id, "receipt_no": r.receipt_no, "total_amount": _f(r.total_amount)}


def _receipt_out(r: StockReceipt, wname: dict) -> dict:
    return {"id": r.id, "receipt_no": r.receipt_no, "warehouse_id": r.warehouse_id, "warehouse_name": wname.get(r.warehouse_id, ""),
            "receipt_date": r.receipt_date.isoformat(), "status": r.status, "note": r.note, "line_count": r.line_count,
            "total_amount": _f(r.total_amount), "created_by": r.created_by,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else None,
            "voided_by": r.voided_by, "void_reason": r.void_reason}


@router.get("/receipts", summary="進貨單清單")
def list_receipts(start: Optional[date] = None, end: Optional[date] = None, warehouse_id: Optional[int] = None,
                  ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db), _=Depends(_receipt_any)):
    q = cp.query(StockReceipt).filter(StockReceipt.company_code == ctx.code)
    if start:
        q = q.filter(StockReceipt.receipt_date >= start)
    if end:
        q = q.filter(StockReceipt.receipt_date <= end)
    if warehouse_id:
        q = q.filter(StockReceipt.warehouse_id == warehouse_id)
    wname = dict(cp.query(StockWarehouse.id, StockWarehouse.name).filter(StockWarehouse.company_code == ctx.code).all())
    rows = q.order_by(StockReceipt.receipt_date.desc(), StockReceipt.id.desc()).limit(2000).all()
    return [_receipt_out(r, wname) for r in rows]


@router.get("/receipts-summary", summary="本月進貨 KPI")
def receipts_summary(month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"), ctx: StockContext = Depends(stock_context),
                     cp: Session = Depends(get_cycle_purchase_db), _=Depends(_receipt_any)):
    last = cp.query(func.max(StockReceipt.receipt_date)).filter(StockReceipt.company_code == ctx.code,
                                                                StockReceipt.status == "posted").scalar()
    if month:
        y, m = map(int, month.split("-"))
    else:
        today = date.today()
        y, m = today.year, today.month
    first = date(y, m, 1)
    nxt = date(y + (m == 12), (m % 12) + 1, 1)
    rq = cp.query(StockReceipt).filter(StockReceipt.company_code == ctx.code, StockReceipt.status == "posted",
                                       StockReceipt.receipt_date >= first, StockReceipt.receipt_date < nxt)
    ids = [r.id for r in rq.all()]
    qty = cp.query(func.coalesce(func.sum(StockReceiptItem.stock_qty), 0)).filter(StockReceiptItem.receipt_id.in_(ids or [0])).scalar()
    amt = cp.query(func.coalesce(func.sum(StockReceiptItem.amount), 0)).filter(StockReceiptItem.receipt_id.in_(ids or [0])).scalar()
    pending = cp.query(StockImportLine).filter(StockImportLine.company_code == ctx.code,
                                               StockImportLine.status.in_(["pending", "partial"]),
                                               StockImportLine.source_status == "ok").count()
    changed = cp.query(StockImportLine).filter(StockImportLine.company_code == ctx.code, StockImportLine.source_changed.is_(True)).count()
    return {"month": f"{y:04d}-{m:02d}", "receipt_count": len(ids), "stock_qty": float(qty), "amount": float(amt),
            "pending_lines": pending, "changed_lines": changed, "data_end": last.isoformat() if last else None}


@router.get("/receipts/{rid}", summary="進貨單明細")
def get_receipt(rid: int, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
                _=Depends(_receipt_any)):
    r = cp.query(StockReceipt).get(rid)
    if not r or r.company_code != ctx.code:
        raise HTTPException(status_code=404, detail="找不到進貨單")
    wname = dict(cp.query(StockWarehouse.id, StockWarehouse.name).filter(StockWarehouse.company_code == ctx.code).all())
    out = _receipt_out(r, wname)
    rows = (cp.query(StockReceiptItem, StockImportLine, CyclePurchaseItem)
            .join(StockImportLine, StockImportLine.id == StockReceiptItem.import_line_id)
            .join(CyclePurchaseItem, CyclePurchaseItem.id == StockReceiptItem.item_id)
            .filter(StockReceiptItem.receipt_id == r.id).order_by(StockReceiptItem.id).all())
    out["lines"] = [{
        "id": ri.id, "source_label": SOURCE_LABEL.get(l.source_type, l.source_type), "doc_no": l.doc_no,
        "ragic_url": imp.ragic_url(l), "product_name": l.product_name, "item_code": it.item_code, "item_name": it.item_name,
        "purchase_qty": float(ri.purchase_qty), "purchase_unit": ri.purchase_unit, "unit_ratio": float(ri.unit_ratio),
        "stock_qty": float(ri.stock_qty), "stock_unit": it.unit, "unit_cost": float(ri.unit_cost), "amount": float(ri.amount),
        "is_estimated_cost": bool(ri.is_estimated_cost), "override_reason": ri.override_reason,
    } for ri, l, it in rows]
    return out


@router.post("/receipts/{rid}/void", summary="作廢進貨單（反向異動、回補可匯入量）")
def void_receipt(rid: int, body: VoidIn, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
                 _=Depends(require_permission(RECEIPT_CONFIRM))):
    r = cp.query(StockReceipt).get(rid)
    if not r or r.company_code != ctx.code:
        raise HTTPException(status_code=404, detail="找不到進貨單")
    w = _warehouse(cp, ctx, r.warehouse_id)
    try:
        imp.void_receipt(cp, receipt=r, warehouse=w, reason=body.reason.strip(), user_name=ctx.user_name)
    except svc.StockError as e:
        _business_error(e)
    return {"id": r.id, "status": r.status}


# ═══════════════════════════════════════════════════════════════════════════
# Phase 4a（2026-11-17）領用／退料／調撥／報廢 — SPEC §7、D26～D29
# ═══════════════════════════════════════════════════════════════════════════
#
# 資料範圍（D27）：有 stock_issue_create 者只能從「自己所屬部門（user_departments）」的倉開領用／退料單，
#   並看到這些倉的單據與自己開的單；倉管（stock_issue_post）與系統管理員看／操作同公司所有倉。
# 核准（D28）：倉庫設定「領用需核准」才走核准；核准者＝有 stock_issue_approve 且屬於該倉部門的人（系統管理員皆可）。
# 調撥／報廢（D29）：倉管開單即過帳，不走核准。
# 單位成本：只給倉管（stock_issue_post）、庫存檢視（stock_balance_view）與系統管理員看。

from app.models.stock import StockIssue, StockIssueLine, StockIssueTemplate
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
                     include_zero: bool = Query(False, description="連可用量 0 的料號也列出（列印 QR 標籤用）"),
                     ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                     cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    w = _warehouse(cp, ctx, warehouse_id)
    if not _in_scope(ctx, _my_dept_ids(db, ctx.user_id), w):
        raise HTTPException(status_code=403, detail="不能使用這個倉庫（不是您所屬部門的倉）")
    rows = iss.available_items(cp, w.id, keyword, limit=2000 if include_zero else 500, include_zero=include_zero)
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


# ── 領用範本（Phase 4b）：開單者可管理自己所屬部門倉的範本；倉管可管理全部 ─────────────

class TemplateLineIn(BaseModel):
    item_id: int
    qty: Decimal = Field(..., gt=0)


class TemplateIn(BaseModel):
    warehouse_id: int
    name: str = Field(..., min_length=1, max_length=100)
    note: Optional[str] = Field(None, max_length=500)
    lines: list[TemplateLineIn] = Field(..., min_length=1, max_length=300)


def _tpl_guard(ctx: StockContext, db: Session, w: StockWarehouse):
    if not (ctx.has(ISSUE_CREATE) or ctx.has(ISSUE_POST)):
        raise HTTPException(status_code=403, detail="沒有管理領用範本的權限")
    if not _in_scope(ctx, _my_dept_ids(db, ctx.user_id), w):
        raise HTTPException(status_code=403, detail="只能管理您所屬部門倉庫的範本")


@router.get("/issues/templates", summary="領用範本清單（可見倉庫）")
def list_issue_templates(warehouse_id: Optional[int] = None, ctx: StockContext = Depends(stock_context),
                         db: Session = Depends(get_db), cp: Session = Depends(get_cycle_purchase_db),
                         _=Depends(_issue_any)):
    depts = _my_dept_ids(db, ctx.user_id)
    whs = {w.id: w for w in cp.query(StockWarehouse).filter(StockWarehouse.company_code == ctx.code).all()}
    wids = [wid for wid, w in whs.items() if _in_scope(ctx, depts, w)]
    if warehouse_id:
        wids = [x for x in wids if x == warehouse_id]
    rows = (cp.query(StockIssueTemplate).filter(StockIssueTemplate.company_code == ctx.code,
                                                StockIssueTemplate.warehouse_id.in_(wids or [0]))
            .order_by(StockIssueTemplate.warehouse_id, StockIssueTemplate.name).all())
    out = []
    for t in rows:
        o = iss.template_out(cp, t)
        o["warehouse_name"] = whs[t.warehouse_id].name
        out.append(o)
    return out


@router.post("/issues/templates", summary="新增領用範本")
def create_issue_template(body: TemplateIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                          cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    w = _warehouse(cp, ctx, body.warehouse_id)
    _tpl_guard(ctx, db, w)
    try:
        t = iss.save_template(cp, tpl=None, code=ctx.code, warehouse=w, name=body.name, note=body.note,
                              lines=[(l.item_id, l.qty) for l in body.lines], user_name=ctx.user_name, user_id=ctx.user_id)
    except svc.StockError as e:
        _business_error(e)
    return {"id": t.id, "name": t.name}


def _tpl(cp: Session, ctx: StockContext, db: Session, tid: int) -> StockIssueTemplate:
    t = cp.query(StockIssueTemplate).get(tid)
    if not t or t.company_code != ctx.code:
        raise HTTPException(status_code=404, detail="找不到範本")
    _tpl_guard(ctx, db, cp.query(StockWarehouse).get(t.warehouse_id))
    return t


@router.put("/issues/templates/{tid}", summary="修改領用範本")
def update_issue_template(tid: int, body: TemplateIn, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                          cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    t = _tpl(cp, ctx, db, tid)
    w = _warehouse(cp, ctx, body.warehouse_id)
    _tpl_guard(ctx, db, w)
    try:
        iss.save_template(cp, tpl=t, code=ctx.code, warehouse=w, name=body.name, note=body.note,
                          lines=[(l.item_id, l.qty) for l in body.lines], user_name=ctx.user_name, user_id=ctx.user_id)
    except svc.StockError as e:
        _business_error(e)
    return {"id": t.id, "name": t.name}


@router.delete("/issues/templates/{tid}", summary="刪除領用範本（只刪範本，不影響任何單據與庫存）")
def delete_issue_template(tid: int, ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                          cp: Session = Depends(get_cycle_purchase_db), _=Depends(_issue_any)):
    t = _tpl(cp, ctx, db, tid)
    cp.delete(t)
    return {"id": tid}


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
        "count_type": c.count_type or "full", "abc_classes": c.abc_classes,
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
    abc_classes: Optional[list[str]] = Field(None, description="循環盤點：只盤這些 ABC 類（Phase 7）；空＝月底全盤")


@router.post("/counts", summary="產生盤點表（每個倉一張；倉庫改為盤點中、暫停過帳）")
def create_counts(body: CountCreateIn, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
                  _=Depends(require_permission(COUNT_REVIEW))):
    created, errors = [], []
    for wid in dict.fromkeys(body.warehouse_ids):
        w = _warehouse(cp, ctx, wid)
        sp = cp.begin_nested()
        try:
            abc = sorted({x for x in (body.abc_classes or []) if x in ("A", "B", "C")}) or None
            c = cnt.create_count(cp, warehouse=w, count_date=body.count_date, note=body.note, user_name=ctx.user_name,
                                 abc_classes=abc)
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


# ═══════════════════════════════════════════════════════════════════════════
# Phase 7（2026-11-17）ABC 分類建議、補貨建議 — SPEC §10
# ═══════════════════════════════════════════════════════════════════════════

from app.services import stock_insight_service as ins


@router.get("/items/abc-suggest", summary="ABC 分類建議（依近 N 天領用淨額）")
def abc_suggest(days: int = Query(90, ge=30, le=365), ctx: StockContext = Depends(stock_context),
                cp: Session = Depends(get_cycle_purchase_db), _=Depends(require_permission(MANAGE))):
    return {"days": days, "rows": ins.abc_suggest(cp, ctx.code, days)}


class AbcApplyIn(BaseModel):
    items: list[dict] = Field(..., min_length=1, max_length=5000, description="[{item_id, abc_class: A/B/C/null}]")


@router.post("/items/abc-apply", summary="套用 ABC 分類")
def abc_apply(body: AbcApplyIn, ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
              _=Depends(require_permission(MANAGE))):
    mapping = []
    for x in body.items:
        cls = x.get("abc_class")
        if cls not in ("A", "B", "C", None, ""):
            raise HTTPException(status_code=422, detail="ABC 類別只能是 A、B、C 或空白")
        mapping.append((int(x["item_id"]), cls or None))
    return {"updated": ins.apply_abc(cp, ctx.code, mapping, ctx.user_name)}


@router.get("/replenishment", summary="補貨建議（可用量低於安全量；只建議、不開單）")
def replenishment(warehouse_id: Optional[int] = None, days: int = Query(90, ge=30, le=365),
                  ctx: StockContext = Depends(stock_context), cp: Session = Depends(get_cycle_purchase_db),
                  _=Depends(require_permission(VIEW))):
    wids = [w for (w,) in cp.query(StockWarehouse.id).filter(StockWarehouse.company_code == ctx.code).all()
            if not warehouse_id or w == warehouse_id]
    return {"days": days, "rows": ins.replenishment(cp, ctx.code, wids, days)}


# ── Dashboard（2026-11-17）：SPEC §12.1 ─────────────────────────────────────────
# 錨點＝庫存異動最後一天（CLAUDE §8.2，不用今天）；本週／本月固定以錨點為終點；
# 期間（預設＝本月）、倉庫、部門為可選篩選；待匯入清單是公司層級（清單只記部門名稱，不對倉庫）。
# 金額依 _can_see_cost；盤盈虧金額依 COUNT_REVIEW（與盤點表 API 相同規則）。
DASHBOARD_ANY = require_any_permission(VIEW, MANAGE, OPENING, RECEIPT_VIEW, RECEIPT_CONFIRM,
                                       ISSUE_CREATE, ISSUE_APPROVE, ISSUE_POST, COUNT_EXEC, COUNT_REVIEW)


def _prev_month(y: int, m: int) -> tuple[int, int]:
    return (y, m - 1) if m > 1 else (y - 1, 12)


@router.get("/dashboard", summary="庫存 Dashboard（SPEC §12.1）")
def stock_dashboard(start: Optional[date] = None, end: Optional[date] = None,
                    warehouse_id: Optional[int] = None, department_id: Optional[str] = None,
                    ctx: StockContext = Depends(stock_context), db: Session = Depends(get_db),
                    cp: Session = Depends(get_cycle_purchase_db), _=Depends(DASHBOARD_ANY)):
    depts = _my_dept_ids(db, ctx.user_id)
    all_wh = cp.query(StockWarehouse).filter(StockWarehouse.company_code == ctx.code).all()
    wh = [w for w in all_wh if _in_scope(ctx, depts, w)
          and (warehouse_id is None or w.id == warehouse_id)
          and (not department_id or w.department_id == department_id)]
    wids = [w.id for w in wh] or [0]
    see_cost, see_review = _can_see_cost(ctx), ctx.has(COUNT_REVIEW)

    last_move = cp.query(func.max(StockMove.moved_at)).filter(StockMove.company_code == ctx.code).scalar()
    anchor = last_move or date.today()
    week_start = anchor - timedelta(days=anchor.weekday())
    month_start = anchor.replace(day=1)
    py, pm = _prev_month(anchor.year, anchor.month)
    prev_period = f"{py:04d}-{pm:02d}"
    p_start, p_end = start or month_start, end or anchor
    win = {"week": (week_start, anchor), "month": (month_start, anchor), "period": (p_start, p_end)}

    def _rcpt(a: date, b: date) -> dict:
        rs = cp.query(StockReceipt).filter(StockReceipt.company_code == ctx.code, StockReceipt.status == "posted",
                                           StockReceipt.warehouse_id.in_(wids),
                                           StockReceipt.receipt_date >= a, StockReceipt.receipt_date <= b).all()
        ids = [r.id for r in rs] or [0]
        qty = cp.query(func.coalesce(func.sum(StockReceiptItem.stock_qty), 0)).filter(StockReceiptItem.receipt_id.in_(ids)).scalar()
        amt = cp.query(func.coalesce(func.sum(StockReceiptItem.amount), 0)).filter(StockReceiptItem.receipt_id.in_(ids)).scalar()
        return {"count": len(rs), "stock_qty": float(qty), "amount": float(amt) if see_cost else None}

    def _issued(a: date, b: date) -> dict:
        ds = cp.query(StockIssue).filter(StockIssue.company_code == ctx.code, StockIssue.warehouse_id.in_(wids),
                                         StockIssue.status == "posted", StockIssue.doc_type == "issue",
                                         StockIssue.posted_date >= a, StockIssue.posted_date <= b).all()
        return {"count": len(ds), "amount": round(sum(float(x.total_amount or 0) for x in ds), 2) if see_cost else None}

    lines = cp.query(StockImportLine).filter(StockImportLine.company_code == ctx.code)

    def _new_lines(a: date, b: date) -> dict:
        ls = lines.filter(func.date(StockImportLine.created_at) >= a, func.date(StockImportLine.created_at) <= b).all()
        return {"count": len(ls), "amount": round(sum(float(x.amount or 0) for x in ls), 2) if see_cost else None}

    pending = lines.filter(StockImportLine.status.in_(["pending", "partial"]), StockImportLine.source_status == "ok").count()
    changed = lines.filter(StockImportLine.source_changed.is_(True)).count()

    issues_base = cp.query(StockIssue).filter(StockIssue.company_code == ctx.code, StockIssue.warehouse_id.in_(wids))
    pending_approval = issues_base.filter(StockIssue.status == "pending_approval").count()
    pending_post = issues_base.filter(StockIssue.status == "approved").count()

    cats = (cp.query(CyclePurchaseItem.category_id)
            .outerjoin(StockItemSetting, StockItemSetting.item_id == CyclePurchaseItem.id)
            .filter(CyclePurchaseItem.company_code == ctx.code, CyclePurchaseItem.is_active.is_(True),
                    CyclePurchaseItem.category_id.isnot(None),
                    or_(StockItemSetting.item_id.is_(None), StockItemSetting.is_stock_item.is_(True)))
            .distinct().count())

    counts = (cp.query(StockCount).filter(StockCount.warehouse_id.in_(wids), StockCount.period == prev_period,
                                          StockCount.status != "cancelled").all())
    by_status = {k: 0 for k in ("counting", "submitted", "approved")}
    for c in counts:
        by_status[c.status] = by_status.get(c.status, 0) + 1

    bals = (cp.query(StockBalance, CyclePurchaseItem)
            .join(CyclePurchaseItem, CyclePurchaseItem.id == StockBalance.item_id)
            .filter(StockBalance.warehouse_id.in_(wids), or_(StockBalance.qty != 0, StockBalance.reserved_qty != 0)).all())
    dead_before = date.today() - timedelta(days=DEAD_DAYS)
    bal_amount = round(sum(float(b.amount or 0) for b, _it in bals), 2)
    low = sum(1 for b, it in bals if it.min_stock is not None and float(b.qty) < it.min_stock)
    dead = sum(1 for b, _it in bals if float(b.qty) > 0 and (b.last_move_at is None or b.last_move_at < dead_before))
    negative = sum(1 for b, _it in bals if float(b.qty) < 0)

    closed_periods = [p.period for p in cp.query(StockPeriod).filter(StockPeriod.company_code == ctx.code,
                                                                      StockPeriod.status == "closed").all()]
    prev_closed = prev_period in closed_periods

    return {
        "company": ctx.code,
        "anchor": anchor.isoformat(),
        "data_end": last_move.isoformat() if last_move else None,
        "filters": {"warehouse_id": warehouse_id, "department_id": department_id,
                    "start": p_start.isoformat(), "end": p_end.isoformat()},
        "import": {"pending": pending, "changed": changed,
                   "new_week": _new_lines(*win["week"]), "new_month": _new_lines(*win["month"])},
        "receipts": {"week": _rcpt(*win["week"]), "month": _rcpt(*win["month"]), "period": _rcpt(*win["period"])},
        "issues": {"week": _issued(*win["week"]), "month": _issued(*win["month"]), "period": _issued(*win["period"]),
                   "pending_approval": pending_approval, "pending_post": pending_post},
        "categories": {"stock_categories": cats},
        "counts": {"period": prev_period, "tables": len(counts), "by_status": by_status,
                   "lines": sum(c.line_count or 0 for c in counts),
                   "diff": sum(c.diff_count or 0 for c in counts),
                   "gain_amount": round(sum(float(c.gain_amount or 0) for c in counts), 2) if see_review else None,
                   "loss_amount": round(sum(float(c.loss_amount or 0) for c in counts), 2) if see_review else None},
        "balance": {"amount": bal_amount if see_cost else None, "items": len(bals),
                    "low": low, "dead": dead, "negative": negative, "dead_days": DEAD_DAYS},
        "period_close": {"prev_period": prev_period, "prev_closed": prev_closed,
                         "last_closed": max(closed_periods) if closed_periods else None},
        "three_way_diff": None,
        "meta": {"cost_visible": see_cost, "review_visible": see_review},
    }
