"""
客房保養業務邏輯層
- 讀取：從本地 SQLite DB 查詢（由 sync service 同步自 Ragic）
- 寫入：新增/更新/刪除仍直接操作 Ragic，之後呼叫方負責觸發同步
"""
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.room_maintenance import RoomMaintenanceRecord as RoomMaintenanceORM
from app.schemas.room_maintenance import (
    RoomMaintenanceCreate,
    RoomMaintenanceListResponse,
    RoomMaintenanceRecord,
    RoomMaintenanceStats,
    RoomMaintenanceUpdate,
    WorkItemStatus,
)
from app.services.ragic_adapter import RagicAdapter

# ── Field ID 常數 ─────────────────────────────────────────────────────────────
F_ROOM_NO       = settings.RAGIC_FIELD_ROOM_NO
F_INSPECT_ITEMS = settings.RAGIC_FIELD_INSPECT_ITEMS
F_DEPT          = settings.RAGIC_FIELD_DEPT
F_WORK_ITEM     = settings.RAGIC_FIELD_WORK_ITEM
F_INSPECT_DT    = settings.RAGIC_FIELD_INSPECT_DT
F_CLOSE_DATE    = settings.RAGIC_FIELD_CLOSE_DATE


def _get_adapter() -> RagicAdapter:
    return RagicAdapter(sheet_path=settings.RAGIC_ROOM_MAINTENANCE_PATH)


def _orm_to_schema(orm: RoomMaintenanceORM) -> RoomMaintenanceRecord:
    """ORM 物件 → Pydantic schema"""
    return RoomMaintenanceRecord(
        id=orm.ragic_id,
        room_no=orm.room_no,
        inspect_items=orm.get_inspect_items(),
        dept=orm.dept,
        work_item=orm.work_item,
        inspect_datetime=orm.inspect_datetime,
        created_at=orm.ragic_created_at,
        updated_at=orm.ragic_updated_at,
        close_date=orm.close_date,
        subtotal=orm.subtotal,
        incomplete=orm.incomplete,
    )


# ── DB 讀取函數 ───────────────────────────────────────────────────────────────

def list_records(
    db: Session,
    room_no: Optional[str] = None,
    work_item: Optional[str] = None,
    dept: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
) -> RoomMaintenanceListResponse:
    """從本地 DB 讀取客房保養清單，支援篩選與分頁"""
    query = db.query(RoomMaintenanceORM)

    if room_no:
        query = query.filter(RoomMaintenanceORM.room_no == room_no)
    if work_item:
        query = query.filter(RoomMaintenanceORM.work_item.contains(work_item))
    if dept:
        query = query.filter(RoomMaintenanceORM.dept.ilike(f"%{dept}%"))

    all_records = [_orm_to_schema(r) for r in query.all()]

    # 依房號排序（數字優先，再字串）
    def _sort_key(r: RoomMaintenanceRecord):
        try:
            return (0, int(r.room_no))
        except ValueError:
            return (1, r.room_no)

    all_records.sort(key=_sort_key)

    total = len(all_records)
    start = (page - 1) * per_page
    paged = all_records[start : start + per_page]

    return RoomMaintenanceListResponse(
        success=True,
        data=paged,
        meta={"total": total, "page": page, "per_page": per_page},
    )


def get_record(db: Session, record_id: str) -> RoomMaintenanceRecord:
    """從本地 DB 讀取單筆記錄"""
    orm = db.get(RoomMaintenanceORM, record_id)
    if not orm:
        raise ValueError(f"找不到 ID={record_id} 的客房保養記錄")
    return _orm_to_schema(orm)


def get_stats(db: Session) -> RoomMaintenanceStats:
    """從本地 DB 計算統計數字"""
    records = [_orm_to_schema(r) for r in db.query(RoomMaintenanceORM).all()]

    total            = len(records)
    completed        = sum(1 for r in records if WorkItemStatus.COMPLETED     in r.work_item)
    not_scheduled    = sum(1 for r in records if WorkItemStatus.NOT_SCHEDULED in r.work_item)
    total_incomplete = sum(r.incomplete for r in records)
    completion_rate  = round(completed / total * 100, 1) if total > 0 else 0.0

    return RoomMaintenanceStats(
        total=total,
        completed=completed,
        not_scheduled=not_scheduled,
        total_incomplete=total_incomplete,
        completion_rate=completion_rate,
    )


# ── Ragic 寫入操作 ────────────────────────────────────────────────────────────

async def create_record(payload: RoomMaintenanceCreate) -> dict:
    """新增一筆記錄到 Ragic（呼叫方應在之後觸發 sync）"""
    adapter = _get_adapter()
    data = {
        F_ROOM_NO:       payload.room_no,
        F_INSPECT_ITEMS: ",".join(payload.inspect_items),
        F_DEPT:          payload.dept,
        F_WORK_ITEM:     payload.work_item,
        F_INSPECT_DT:    payload.inspect_datetime,
        F_CLOSE_DATE:    payload.close_date or "",
    }
    return await adapter.create(data)


async def update_record(record_id: str, payload: RoomMaintenanceUpdate) -> dict:
    """更新 Ragic 上的記錄（呼叫方應在之後觸發 sync）"""
    adapter = _get_adapter()
    data: dict = {}
    if payload.room_no          is not None: data[F_ROOM_NO]       = payload.room_no
    if payload.inspect_items    is not None: data[F_INSPECT_ITEMS] = ",".join(payload.inspect_items)
    if payload.dept             is not None: data[F_DEPT]          = payload.dept
    if payload.work_item        is not None: data[F_WORK_ITEM]     = payload.work_item
    if payload.inspect_datetime is not None: data[F_INSPECT_DT]    = payload.inspect_datetime
    if payload.close_date       is not None: data[F_CLOSE_DATE]    = payload.close_date
    return await adapter.update(record_id, data)


async def delete_record(record_id: str) -> dict:
    """從 Ragic 刪除記錄"""
    adapter = _get_adapter()
    await adapter.delete(record_id)
    return {"success": True, "deleted_id": record_id}
