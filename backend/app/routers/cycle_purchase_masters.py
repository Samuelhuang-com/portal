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
from app.schemas.cycle_purchase_category import (
    CategoryCreate, CategoryNextCodeOut, CategoryOut, CategoryUpdate,
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


@router.post("/vendors/sync", summary="自合約模組同步供應商主檔")
def sync_vendors_from_contract(
    _: User = Depends(require_permission("cycle_purchase_admin")),
):
    """
    把合約模組的廠商主檔（portal.db `vendors`）鏡像同步到週期採購。

    ⚠ 這是**同步 def**（不是 async def），FastAPI 會丟到 thread pool 執行。
    刻意如此：sync_from_contract() 內部是一連串阻塞的 SQLAlchemy 呼叫，
    寫成 async def 會直接卡住事件迴圈、整個 Portal 沒有回應（2026-07-15 已經
    因為這個原因修過 12 個 router 檔）。既然已經在 thread pool 的執行緒上，
    跨行程鎖就用同步版的 sync_lock（見 sync_lock.py 的 docstring）。

    與「設定 → Ragic 連線 → 立即同步」的差別：
      - 那邊是背景執行、不回傳結果，而且要 system_admin 權限
      - 這裡同步等待並把 created/updated/skipped/warnings/errors 直接回給前端，
        使用者在供應商主檔頁面按下去就能看到這次到底同步了什麼

    注意：這條路徑不會寫 module_sync_log（那是 main.py 排程的內部機制），
    所以「設定 → Ragic 連線」的同步紀錄不會出現這一筆。
    """
    import asyncio

    from app.core.sync_lock import sync_lock
    from app.services.cycle_purchase_vendor_sync import sync_from_contract

    try:
        with sync_lock("週期採購供應商"):
            # sync_from_contract 是 async def（要能被 sync_dispatcher 與排程共用），
            # 但內部沒有任何 await，在這條 worker 執行緒直接 asyncio.run 即可。
            result = asyncio.run(sync_from_contract())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"同步失敗：{exc}")

    if result.get("errors"):
        raise HTTPException(
            status_code=500,
            detail="同步過程發生錯誤：" + "；".join(str(e) for e in result["errors"][:3]),
        )
    return result


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


# ── 類別主檔（2026-08-18 新增）────────────────────────────────────────────────
# 三層編碼（大分類英文 + 中分類 2 碼 + 細分類 2 碼 + 流水 3 碼），
# 設計理由與 department_id 可為 NULL 的語意見
# models/cycle_purchase_category.py 檔頭。

@router.get("/categories", response_model=List[CategoryOut], summary="類別主檔清單")
def list_categories(
    company: Optional[str] = Query(None, description="公司別"),
    department_id: Optional[int] = Query(None, description="歸屬部門"),
    q: str = Query("", description="關鍵字（類別／大中細分類名稱）"),
    is_active: Optional[bool] = Query(None),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_categories(
        db, company=company, department_id=department_id, q=q, is_active=is_active
    )


@router.post(
    "/categories",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="新增類別",
)
def create_category(
    payload: CategoryCreate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    try:
        return svc.create_category(db, payload)
    except IntegrityError:
        db.rollback()
        raise _conflict("同公司底下已有相同的大／中／細分類代碼組合")


@router.get(
    "/categories/{category_id}/next-code",
    response_model=CategoryNextCodeOut,
    summary="取這個類別下一個可用料號",
)
def get_category_next_code(
    category_id: int,
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    result = svc.get_next_item_code(db, category_id)
    if not result:
        raise HTTPException(status_code=404, detail="類別不存在")
    return result


@router.put("/categories/{category_id}", response_model=CategoryOut, summary="更新類別")
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    try:
        category = svc.update_category(db, category_id, payload)
    except IntegrityError:
        db.rollback()
        raise _conflict("同公司底下已有相同的大／中／細分類代碼組合")
    if not category:
        raise HTTPException(status_code=404, detail="類別不存在")
    return category
