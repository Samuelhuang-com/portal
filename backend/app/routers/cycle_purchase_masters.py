"""
週期採購 — 基礎設定主檔 API Router
Prefix: /api/v1/cycle-purchase/masters

包含：供應商主檔、部門主檔、成本中心主檔、會計科目主檔。
2026-07-10 決策：以上四張主檔全部是週期採購自建、獨立於 portal.db 其他模組
（Contract 的 Vendors、Budget 的 budget_system_v1.sqlite、
reference_data.py 的 Company/RefDepartment）之外，存在獨立的
cycle-purchase.db（見 app/core/cycle_purchase_database.py 說明）。
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.core.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.cycle_purchase_vendor import VendorCreate, VendorOut, VendorUpdate
from app.schemas.cycle_purchase_reference import (
    DepartmentCreate, DepartmentOut, DepartmentUpdate,
    CostCenterCreate, CostCenterOut, CostCenterUpdate,
    AccountCodeCreate, AccountCodeOut, AccountCodeUpdate,
)
from app.services import cycle_purchase_service as svc

router = APIRouter()


def _conflict(detail: str = "資料重複（代碼已存在）"):
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _attach_owner_names(portal_db: Session, depts) -> None:
    """
    部門的 owner_user_id 是軟關聯到 portal.db 的 users.id（cycle-purchase.db
    自己不存 user 資料，比照本專案應用層軟關聯原則）。這裡在 router 層另外
    拿 portal_db session 補上 owner_name 快照顯示用，cycle_purchase_service.py
    本身維持只碰 cycle-purchase.db。單一物件或 list 都可傳入。
    """
    rows = depts if isinstance(depts, list) else [depts]
    ids = {r.owner_user_id for r in rows if getattr(r, "owner_user_id", None)}
    name_map = {}
    if ids:
        users = portal_db.query(User).filter(User.id.in_(ids)).all()
        name_map = {u.id: u.full_name for u in users}
    for r in rows:
        r.owner_name = name_map.get(r.owner_user_id)


# ── 供應商主檔 ────────────────────────────────────────────────────────────────

@router.get("/vendors", response_model=List[VendorOut], summary="供應商主檔清單")
def list_vendors(
    q: str = Query("", description="關鍵字（供應商代碼／名稱）"),
    is_active: Optional[bool] = Query(None),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_vendors(db, is_active=is_active, q=q)


@router.post("/vendors", response_model=VendorOut, status_code=status.HTTP_201_CREATED, summary="新增供應商")
def create_vendor(
    payload: VendorCreate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    try:
        return svc.create_vendor(db, payload)
    except IntegrityError:
        db.rollback()
        raise _conflict("供應商代碼已存在")


@router.put("/vendors/{vendor_id}", response_model=VendorOut, summary="更新供應商")
def update_vendor(
    vendor_id: int,
    payload: VendorUpdate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    try:
        vendor = svc.update_vendor(db, vendor_id, payload)
    except IntegrityError:
        db.rollback()
        raise _conflict("供應商代碼已存在")
    if not vendor:
        raise HTTPException(status_code=404, detail="供應商不存在")
    return vendor


# ── 部門主檔 ──────────────────────────────────────────────────────────────────

@router.get("/departments", response_model=List[DepartmentOut], summary="部門主檔清單")
def list_departments(
    is_active: Optional[bool] = Query(None),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
    portal_db: Session = Depends(get_db),
):
    depts = svc.list_departments(db, is_active=is_active)
    _attach_owner_names(portal_db, depts)
    return depts


@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED, summary="新增部門")
def create_department(
    payload: DepartmentCreate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
    portal_db: Session = Depends(get_db),
):
    dept = svc.create_department(db, payload)
    _attach_owner_names(portal_db, dept)
    return dept


@router.put("/departments/{dept_id}", response_model=DepartmentOut, summary="更新部門")
def update_department(
    dept_id: int,
    payload: DepartmentUpdate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
    portal_db: Session = Depends(get_db),
):
    dept = svc.update_department(db, dept_id, payload)
    if not dept:
        raise HTTPException(status_code=404, detail="部門不存在")
    _attach_owner_names(portal_db, dept)
    return dept


# ── 成本中心主檔 ──────────────────────────────────────────────────────────────

@router.get("/cost-centers", response_model=List[CostCenterOut], summary="成本中心主檔清單")
def list_cost_centers(
    department_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_cost_centers(db, department_id=department_id, is_active=is_active)


@router.post("/cost-centers", response_model=CostCenterOut, status_code=status.HTTP_201_CREATED, summary="新增成本中心")
def create_cost_center(
    payload: CostCenterCreate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    try:
        return svc.create_cost_center(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=422, detail="部門不存在或成本中心代碼重複")


@router.put("/cost-centers/{cc_id}", response_model=CostCenterOut, summary="更新成本中心")
def update_cost_center(
    cc_id: int,
    payload: CostCenterUpdate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    cc = svc.update_cost_center(db, cc_id, payload)
    if not cc:
        raise HTTPException(status_code=404, detail="成本中心不存在")
    return cc


# ── 會計科目主檔 ──────────────────────────────────────────────────────────────

@router.get("/account-codes", response_model=List[AccountCodeOut], summary="會計科目主檔清單")
def list_account_codes(
    is_active: Optional[bool] = Query(None),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_account_codes(db, is_active=is_active)


@router.post("/account-codes", response_model=AccountCodeOut, status_code=status.HTTP_201_CREATED, summary="新增會計科目")
def create_account_code(
    payload: AccountCodeCreate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    try:
        return svc.create_account_code(db, payload)
    except IntegrityError:
        db.rollback()
        raise _conflict("會計科目代碼已存在")


@router.put("/account-codes/{ac_id}", response_model=AccountCodeOut, summary="更新會計科目")
def update_account_code(
    ac_id: int,
    payload: AccountCodeUpdate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    ac = svc.update_account_code(db, ac_id, payload)
    if not ac:
        raise HTTPException(status_code=404, detail="會計科目不存在")
    return ac
