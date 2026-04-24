"""
倉庫庫存業務邏輯層
- 讀取：從本地 SQLite DB 查詢（由 sync service 同步自 Ragic）
- 此模組為唯讀，庫存資料不在 Portal 端修改
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.inventory import InventoryRecord as InventoryORM
from app.schemas.inventory import (
    InventoryFilters,
    InventoryListResponse,
    InventoryRecord,
    InventoryStats,
)


def _orm_to_schema(orm: InventoryORM) -> InventoryRecord:
    """ORM 物件 → Pydantic schema"""
    return InventoryRecord(
        id=orm.ragic_id,
        inventory_no=orm.inventory_no,
        warehouse_code=orm.warehouse_code,
        warehouse_name=orm.warehouse_name,
        product_no=orm.product_no,
        product_name=orm.product_name,
        quantity=orm.quantity,
        category=orm.category,
        spec=orm.spec,
        created_at=orm.ragic_created_at,
        updated_at=orm.ragic_updated_at,
    )


def list_records(
    db: Session,
    warehouse_code: Optional[str] = None,
    product_no: Optional[str] = None,
    product_name: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
) -> InventoryListResponse:
    """從本地 DB 讀取倉庫庫存清單，支援篩選與分頁"""
    query = db.query(InventoryORM)

    if warehouse_code:
        query = query.filter(InventoryORM.warehouse_code.ilike(f"%{warehouse_code}%"))
    if product_no:
        query = query.filter(InventoryORM.product_no.ilike(f"%{product_no}%"))
    if product_name:
        query = query.filter(InventoryORM.product_name.ilike(f"%{product_name}%"))

    # 依庫存編號排序
    all_records = [_orm_to_schema(r) for r in query.order_by(InventoryORM.inventory_no).all()]

    total = len(all_records)
    start = (page - 1) * per_page
    paged = all_records[start : start + per_page]

    return InventoryListResponse(
        success=True,
        data=paged,
        meta={"total": total, "page": page, "per_page": per_page},
    )


def get_record(db: Session, record_id: str) -> InventoryRecord:
    """從本地 DB 讀取單筆記錄"""
    orm = db.get(InventoryORM, record_id)
    if not orm:
        raise ValueError(f"找不到 ID={record_id} 的庫存記錄")
    return _orm_to_schema(orm)


def get_stats(db: Session) -> InventoryStats:
    """從本地 DB 計算統計數字"""
    records = db.query(InventoryORM).all()

    total_skus      = len(records)
    total_quantity  = sum(r.quantity for r in records)
    zero_stock      = sum(1 for r in records if r.quantity <= 0)
    warehouses      = len({r.warehouse_code for r in records if r.warehouse_code})

    return InventoryStats(
        total_skus=total_skus,
        total_quantity=total_quantity,
        zero_stock_count=zero_stock,
        warehouse_count=warehouses,
    )
