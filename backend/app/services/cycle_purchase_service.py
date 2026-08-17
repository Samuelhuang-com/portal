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

2026-08-09：新增 get_cycle_options()，供週期設定表單的「適用公司」「適用品類」
下拉取主檔 distinct 值。這兩個欄位改版前是自由文字，要跟主檔做字串比對——
與彙整單 2026-07-16 踩過的「期別字串打不一致 → 查到 0 筆」是同一種病灶，
所以一律改成從主檔取選項，不讓使用者手打。
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


# 鏡像自合約模組的供應商（source_vendor_id 非空）不可在週採端修改的欄位。
# 這幾欄由 cycle_purchase_vendor_sync.py 每次同步覆寫，在此改了也會被蓋回去，
# 所以直接在後端擋掉（前端 disabled 只是輔助，不能當作唯一防線）。
VENDOR_SYNCED_READONLY_FIELDS = {
    "vendor_code", "vendor_name", "tax_id", "contact_name", "contact_phone",
}


def update_vendor(db: Session, vendor_id: int, payload) -> Optional[CyclePurchaseVendor]:
    vendor = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.id == vendor_id).first()
    if not vendor:
        return None
    data = payload.model_dump(exclude_unset=True)
    # source_vendor_id / synced_at 只由同步服務維護，任何情況都不吃前端傳入值
    data.pop("source_vendor_id", None)
    data.pop("synced_at", None)
    if vendor.source_vendor_id:
        for field in VENDOR_SYNCED_READONLY_FIELDS:
            data.pop(field, None)
    for k, v in data.items():
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
    """
    2026-08-17：新增「同步鎖定欄位」保護。`source_department_id` 非 None
    代表這筆部門是從 portal.db Company/RefDepartment 鏡像同步過來的（見
    cycle_purchase_department_sync.py），`company`／`dept_name` 由同步覆蓋，
    這裡的 API 若也放行改這兩欄，下次同步一跑就會被蓋回去——使用者會以為
    改成功了，其實只是暫時的，過陣子又「跳回舊值」，比不能改更誤導人。
    前端 Departments.tsx 會把這兩欄設成唯讀，但這裡才是真正擋住的地方
    （唯讀限制必須在後端，前端唯讀只是提示，比照 CLAUDE.md §9 廠商規則 4）。
    """
    dept = db.query(CyclePurchaseDepartment).filter(CyclePurchaseDepartment.id == dept_id).first()
    if not dept:
        return None
    updates = payload.model_dump(exclude_unset=True)
    if dept.source_department_id:
        updates.pop("company", None)
        updates.pop("dept_name", None)
    for k, v in updates.items():
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


def _attach_company_departments(db: Session, item: CyclePurchaseItem) -> CyclePurchaseItem:
    """附加 company_departments（見 schemas/cycle_purchase_item.py ItemOut 說明）。
    2026-08-17 新增：料號主檔列表原本要點進「料號對照」才看得到公司/部門，
    容易讓人誤以為同名品類可以跨公司套用。"""
    rows = (
        db.query(CyclePurchaseItemMapping.company, CyclePurchaseDepartment.dept_name)
        .outerjoin(
            CyclePurchaseDepartment,
            CyclePurchaseDepartment.id == CyclePurchaseItemMapping.department_id,
        )
        .filter(CyclePurchaseItemMapping.item_id == item.id)
        .all()
    )
    item.company_departments = [
        f"{company}／{dept_name}" if dept_name else company
        for company, dept_name in rows
    ]
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
        _attach_company_departments(db, r)
    return rows, total


def get_item(db: Session, item_id: int) -> Optional[CyclePurchaseItem]:
    item = db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id == item_id).first()
    if item:
        _attach_vendor_name(db, item)
        _attach_company_departments(db, item)
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


# ═══════════════════════════════════════════════════════════════════════════
# 週期設定表單的下拉選項來源（2026-08-09 新增）
# ═══════════════════════════════════════════════════════════════════════════

def get_cycle_options(db: Session, companies_filter: Optional[list[str]] = None) -> dict:
    """
    「適用公司」取自部門主檔的 distinct company（只取啟用中部門——停用部門的
    公司值留著只會讓人選到產不出單的設定），**一律回傳全部公司**，不受
    `companies_filter` 影響——這欄位本身就是用來選公司的來源，不能先篩掉自己。

    「適用品類」取自料號主檔的 distinct category（只取啟用中料號，排除 NULL／
    空字串）。2026-08-17 新增 `companies_filter`：若有帶值，只回傳「該公司底下
    有對照表資料」的品類，不再列出全部公司混在一起的 100 多個品類。

    背景（與 Samuel 確認）：連續兩次同一種誤設——編輯週期設定時「適用公司」
    選了春大直，但「適用品類」下拉列出全系統所有公司的品類，選到了實際上只
    屬於日耀天地的品類，導致該部門篩不出任何啟用中料號、請購單永遠空白。
    「適用部門」本來就有依「適用公司」連動過濾（見 models/cycle_purchase_cycle.py
    2026-08-09 說明），這裡讓「適用品類」比照辦理，從源頭擋掉選錯公司品類的
    可能性，不能只靠使用者自己看仔細。

    2026-08-17 再追加 `category_departments`（品類 → 部門名稱清單）：光靠篩選
    還是只解決「選錯公司」，同一公司底下不同部門的品類仍然混在一起列出
    （如工務部的「空調備品-濾網」跟清潔部的「公區備品-垃圾袋」）。經查證
    `cycle_purchase_items.category` 在現有資料下對每家公司來說是乾淨的
    「一品類 = 一部門」（見 models/cycle_purchase_item.py 2026-07-11 docstring
    「逐列核對兩家公司 Excel，同一公司內沒有任何料號橫跨兩個分頁/部門」），
    所以直接把部門名稱附加在下拉選項標籤上（如「空調備品-濾網（工務部）」）
    就足夠釐清，不需要更複雜的分組 UI。回傳型別是 list 而非 dict，
    因為理論上 schema 沒有強制 1 品類 1 部門，極端情況下可能有多個部門，
    要能如實反映。
    """
    companies = [
        row[0]
        for row in db.query(CyclePurchaseDepartment.company)
        .filter(CyclePurchaseDepartment.is_active == True)  # noqa: E712
        .distinct()
        .order_by(CyclePurchaseDepartment.company)
        .all()
        if row[0]
    ]

    category_query = db.query(CyclePurchaseItem.category).filter(
        CyclePurchaseItem.is_active == True,  # noqa: E712
        CyclePurchaseItem.category.isnot(None),
        CyclePurchaseItem.category != "",
    )
    if companies_filter:
        category_query = category_query.join(
            CyclePurchaseItemMapping, CyclePurchaseItemMapping.item_id == CyclePurchaseItem.id
        ).filter(CyclePurchaseItemMapping.company.in_(companies_filter))
    categories = [
        row[0]
        for row in category_query.distinct().order_by(CyclePurchaseItem.category).all()
        if row[0]
    ]

    # 品類 → 部門名稱清單，供前端在下拉選項標籤附加部門名稱（見上方 docstring）。
    # 篩選條件（is_active／companies_filter）跟上面的 categories 查詢保持一致，
    # 否則會出現「品類選項裡沒有這個公司的品類，但 category_departments 卻有」
    # 這種兜不起來的情況。
    dept_query = (
        db.query(CyclePurchaseItem.category, CyclePurchaseDepartment.dept_name)
        .join(CyclePurchaseItemMapping, CyclePurchaseItemMapping.item_id == CyclePurchaseItem.id)
        .outerjoin(
            CyclePurchaseDepartment,
            CyclePurchaseDepartment.id == CyclePurchaseItemMapping.department_id,
        )
        .filter(
            CyclePurchaseItem.is_active == True,  # noqa: E712
            CyclePurchaseItem.category.isnot(None),
            CyclePurchaseItem.category != "",
        )
    )
    if companies_filter:
        dept_query = dept_query.filter(CyclePurchaseItemMapping.company.in_(companies_filter))
    category_departments: dict[str, list[str]] = {}
    for category, dept_name in dept_query.distinct().all():
        if not dept_name:
            continue
        category_departments.setdefault(category, [])
        if dept_name not in category_departments[category]:
            category_departments[category].append(dept_name)

    return {
        "companies": companies,
        "categories": categories,
        "category_departments": category_departments,
    }


def list_exclude_item_candidates(
    db: Session, companies: list[str], categories: list[str]
) -> list[dict]:
    """
    週期設定「排除料號」下拉的候選清單：依表單上目前選的「適用公司」＋
    「適用品類」現算，不是固定清單——避免使用者排除了一筆料號，之後又改了
    適用品類／適用公司，排除清單裡卻殘留一筆已經不相干的料號 id
    （見 models/cycle_purchase_cycle.py 2026-08-16 說明）。

    companies／categories 皆為空清單＝不限（回傳全部啟用中料號，數量可能較大，
    但週期設定畫面本來就是低頻操作，不特別分頁）。
    """
    query = (
        db.query(CyclePurchaseItem, CyclePurchaseItemMapping.company)
        .join(
            CyclePurchaseItemMapping,
            CyclePurchaseItemMapping.item_id == CyclePurchaseItem.id,
        )
        .filter(CyclePurchaseItem.is_active == True)  # noqa: E712
    )
    if companies:
        query = query.filter(CyclePurchaseItemMapping.company.in_(companies))
    if categories:
        query = query.filter(CyclePurchaseItem.category.in_(categories))

    by_item: dict[int, dict] = {}
    for item, company in query.order_by(CyclePurchaseItem.item_code).all():
        entry = by_item.setdefault(
            item.id,
            {
                "item_id": item.id,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "category": item.category,
                "companies": [],
            },
        )
        if company and company not in entry["companies"]:
            entry["companies"].append(company)

    return sorted(by_item.values(), key=lambda r: r["item_code"])
