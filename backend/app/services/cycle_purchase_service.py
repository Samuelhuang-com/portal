"""
週期採購 — Service 層（第一期範圍：供應商／部門／成本中心／會計科目 主檔、
料號主檔＋料號對照表、週期設定）

所有函式吃/回傳 SQLAlchemy Session，這裡的 db 一律是
Depends(get_cycle_purchase_db)（cycle-purchase.db），不是 portal.db 的 get_db()。
部門的 owner_name（承辦人姓名，跨 portal.db users 查詢）不在這裡處理，
比照 cycle_purchase_request_service.get_dashboard_todos 的既有慣例，
由 router 層（cycle_purchase_masters.py）另外拿 portal_db session 補上，
維持這個 service 檔案「只碰 cycle-purchase.db」的單純性。

命名慣例與例外處理比照既有 memo_service.py／contract_service.py：
簡單 CRUD 直接回傳 ORM 物件或 None，唯一鍵衝突交給 router 層轉成 409。

2026-07-11：批次（CyclePurchaseBatch）已拿掉，相關 CRUD
（_next_batch_no／list_batches／get_batch／create_batch／update_batch）
一併移除，理由見 models/cycle_purchase_request.py 開頭說明。
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.cycle_purchase_vendor import CyclePurchaseVendor
from app.models.cycle_purchase_reference import (
    CyclePurchaseDepartment,
    CyclePurchaseCostCenter,
    CyclePurchaseAccountCode,
)
from app.models.cycle_purchase_item import CyclePurchaseItem, CyclePurchaseItemMapping
from app.models.cycle_purchase_cycle import CyclePurchaseCycle


# ═══════════════════════════════════════════════════════════════════════════
# 供應商主檔
# ═══════════════════════════════════════════════════════════════════════════

def list_vendors(db: Session, is_active: Optional[bool] = None, q: str = ""):
    query = db.query(CyclePurchaseVendor)
    if is_active is not None:
        query = query.filter(CyclePurchaseVendor.is_active == is_active)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (CyclePurchaseVendor.vendor_name.like(like))
            | (CyclePurchaseVendor.vendor_code.like(like))
        )
    return query.order_by(CyclePurchaseVendor.vendor_code).all()


def create_vendor(db: Session, payload) -> CyclePurchaseVendor:
    vendor = CyclePurchaseVendor(**payload.model_dump())
    db.add(vendor)
    db.flush()
    return vendor


def update_vendor(db: Session, vendor_id: int, payload) -> Optional[CyclePurchaseVendor]:
    vendor = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.id == vendor_id).first()
    if not vendor:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(vendor, k, v)
    db.flush()
    return vendor


# ═══════════════════════════════════════════════════════════════════════════
# 部門 / 成本中心 / 會計科目 主檔
# ═══════════════════════════════════════════════════════════════════════════

def list_departments(db: Session, is_active: Optional[bool] = None):
    query = db.query(CyclePurchaseDepartment)
    if is_active is not None:
        query = query.filter(CyclePurchaseDepartment.is_active == is_active)
    return query.order_by(CyclePurchaseDepartment.company, CyclePurchaseDepartment.dept_code).all()


def create_department(db: Session, payload) -> CyclePurchaseDepartment:
    dept = CyclePurchaseDepartment(**payload.model_dump())
    db.add(dept)
    db.flush()
    return dept


def update_department(db: Session, dept_id: int, payload) -> Optional[CyclePurchaseDepartment]:
    dept = db.query(CyclePurchaseDepartment).filter(CyclePurchaseDepartment.id == dept_id).first()
    if not dept:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(dept, k, v)
    db.flush()
    return dept


def list_cost_centers(db: Session, department_id: Optional[int] = None, is_active: Optional[bool] = None):
    query = db.query(CyclePurchaseCostCenter)
    if department_id is not None:
        query = query.filter(CyclePurchaseCostCenter.department_id == department_id)
    if is_active is not None:
        query = query.filter(CyclePurchaseCostCenter.is_active == is_active)
    rows = query.order_by(CyclePurchaseCostCenter.cc_code).all()
    for r in rows:
        r.department_name = r.department.dept_name if r.department else None
    return rows


def create_cost_center(db: Session, payload) -> CyclePurchaseCostCenter:
    cc = CyclePurchaseCostCenter(**payload.model_dump())
    db.add(cc)
    db.flush()
    return cc


def update_cost_center(db: Session, cc_id: int, payload) -> Optional[CyclePurchaseCostCenter]:
    cc = db.query(CyclePurchaseCostCenter).filter(CyclePurchaseCostCenter.id == cc_id).first()
    if not cc:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(cc, k, v)
    db.flush()
    return cc


def list_account_codes(db: Session, is_active: Optional[bool] = None):
    query = db.query(CyclePurchaseAccountCode)
    if is_active is not None:
        query = query.filter(CyclePurchaseAccountCode.is_active == is_active)
    return query.order_by(CyclePurchaseAccountCode.code).all()


def create_account_code(db: Session, payload) -> CyclePurchaseAccountCode:
    ac = CyclePurchaseAccountCode(**payload.model_dump())
    db.add(ac)
    db.flush()
    return ac


def update_account_code(db: Session, ac_id: int, payload) -> Optional[CyclePurchaseAccountCode]:
    ac = db.query(CyclePurchaseAccountCode).filter(CyclePurchaseAccountCode.id == ac_id).first()
    if not ac:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(ac, k, v)
    db.flush()
    return ac


# ═══════════════════════════════════════════════════════════════════════════
# 料號主檔 + 料號對照表
# ═══════════════════════════════════════════════════════════════════════════

def _attach_vendor_name(db: Session, item: CyclePurchaseItem) -> CyclePurchaseItem:
    item.default_vendor_name = None
    if item.default_vendor_id:
        vendor = db.query(CyclePurchaseVendor).filter(
            CyclePurchaseVendor.id == item.default_vendor_id
        ).first()
        if vendor:
            item.default_vendor_name = vendor.vendor_name
    return item


def list_items(
    db: Session,
    q: str = "",
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    per_page: int = 20,
):
    query = db.query(CyclePurchaseItem)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (CyclePurchaseItem.item_name.like(like))
            | (CyclePurchaseItem.item_code.like(like))
        )
    if category:
        query = query.filter(CyclePurchaseItem.category == category)
    if is_active is not None:
        query = query.filter(CyclePurchaseItem.is_active == is_active)

    total = query.count()
    rows = (
        query.order_by(CyclePurchaseItem.item_code)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    for r in rows:
        _attach_vendor_name(db, r)
    return rows, total


def get_item(db: Session, item_id: int) -> Optional[CyclePurchaseItem]:
    item = db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id == item_id).first()
    if item:
        _attach_vendor_name(db, item)
        for m in item.mappings:
            _attach_mapping_display_fields(db, m)
    return item


def create_item(db: Session, payload) -> CyclePurchaseItem:
    item = CyclePurchaseItem(**payload.model_dump())
    db.add(item)
    db.flush()
    return _attach_vendor_name(db, item)


def update_item(db: Session, item_id: int, payload) -> Optional[CyclePurchaseItem]:
    item = db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id == item_id).first()
    if not item:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.flush()
    return _attach_vendor_name(db, item)


def _attach_mapping_display_fields(db: Session, mapping: CyclePurchaseItemMapping) -> CyclePurchaseItemMapping:
    """附加 department_name（部門顯示名稱）與 vendor_name（2026-07-11 新增：這個料號
    在這家公司實際跟哪個供應商叫貨，供彙整單/採購單按供應商分單、以及料號對照表
    畫面顯示用）。"""
    mapping.department_name = None
    if mapping.department_id:
        dept = db.query(CyclePurchaseDepartment).filter(
            CyclePurchaseDepartment.id == mapping.department_id
        ).first()
        if dept:
            mapping.department_name = dept.dept_name
    mapping.vendor_name = None
    if mapping.vendor_id:
        vendor = db.query(CyclePurchaseVendor).filter(
            CyclePurchaseVendor.id == mapping.vendor_id
        ).first()
        if vendor:
            mapping.vendor_name = vendor.vendor_name
    return mapping


def list_item_mappings(db: Session, item_id: int):
    rows = (
        db.query(CyclePurchaseItemMapping)
        .filter(CyclePurchaseItemMapping.item_id == item_id)
        .order_by(CyclePurchaseItemMapping.company)
        .all()
    )
    for r in rows:
        _attach_mapping_display_fields(db, r)
    return rows


def create_item_mapping(db: Session, item_id: int, payload) -> Optional[CyclePurchaseItemMapping]:
    item = db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id == item_id).first()
    if not item:
        return None
    mapping = CyclePurchaseItemMapping(item_id=item_id, **payload.model_dump())
    db.add(mapping)
    db.flush()
    return _attach_mapping_display_fields(db, mapping)


def update_item_mapping(db: Session, item_id: int, mapping_id: int, payload):
    mapping = (
        db.query(CyclePurchaseItemMapping)
        .filter(
            CyclePurchaseItemMapping.id == mapping_id,
            CyclePurchaseItemMapping.item_id == item_id,
        )
        .first()
    )
    if not mapping:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(mapping, k, v)
    db.flush()
    return _attach_mapping_display_fields(db, mapping)


def delete_item_mapping(db: Session, item_id: int, mapping_id: int) -> bool:
    mapping = (
        db.query(CyclePurchaseItemMapping)
        .filter(
            CyclePurchaseItemMapping.id == mapping_id,
            CyclePurchaseItemMapping.item_id == item_id,
        )
        .first()
    )
    if not mapping:
        return False
    db.delete(mapping)
    db.flush()
    return True


# ═══════════════════════════════════════════════════════════════════════════
# 週期設定
# ═══════════════════════════════════════════════════════════════════════════

def list_cycles(db: Session, status: Optional[str] = None):
    query = db.query(CyclePurchaseCycle)
    if status:
        query = query.filter(CyclePurchaseCycle.status == status)
    return query.order_by(CyclePurchaseCycle.cycle_code).all()


def get_cycle(db: Session, cycle_id: int) -> Optional[CyclePurchaseCycle]:
    return db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == cycle_id).first()


def create_cycle(db: Session, payload) -> CyclePurchaseCycle:
    cycle = CyclePurchaseCycle(**payload.model_dump())
    db.add(cycle)
    db.flush()
    return cycle


def update_cycle(db: Session, cycle_id: int, payload) -> Optional[CyclePurchaseCycle]:
    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == cycle_id).first()
    if not cycle:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(cycle, k, v)
    db.flush()
    return cycle
