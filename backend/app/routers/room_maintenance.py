"""
客房保養 API Router
Prefix: /api/v1/room-maintenance

架構：讀取本地 SQLite DB（由 /sync 同步自 Ragic），寫入直接操作 Ragic。
"""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.schemas.room_maintenance import (
    INSPECT_ITEM_OPTIONS,
    WORK_ITEM_OPTIONS,
    OptionsResponse,
    RoomMaintenanceCreate,
    RoomMaintenanceListResponse,
    RoomMaintenanceSingleResponse,
    RoomMaintenanceStatsResponse,
    RoomMaintenanceUpdate,
)
from app.services import room_maintenance_service as svc
from app.services.room_maintenance_sync import sync_from_ragic

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── GET /debug-raw — 查看 Ragic 原始回傳格式（除錯用，上線前移除）─────────────
@router.get("/debug-raw", summary="[除錯] 查看 Ragic 原始 JSON key 格式", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def debug_raw():
    """直接回傳 Ragic 第一筆記錄的原始 key，用於確認欄位 ID 格式"""
    from app.services.ragic_adapter import RagicAdapter
    from app.core.config import settings

    adapter = RagicAdapter(sheet_path=settings.RAGIC_ROOM_MAINTENANCE_PATH)
    raw_data = await adapter.fetch_all()

    # 取第一筆
    first_id, first_record = next(iter(raw_data.items()), (None, {}))
    return {
        "total_records": len(raw_data),
        "first_ragic_id": first_id,
        "raw_keys": list(first_record.keys()),
        "raw_sample": {k: v for k, v in list(first_record.items())[:20]},
        "config_field_ids": {
            "RAGIC_FIELD_ROOM_NO": settings.RAGIC_FIELD_ROOM_NO,
            "RAGIC_FIELD_INSPECT_ITEMS": settings.RAGIC_FIELD_INSPECT_ITEMS,
            "RAGIC_FIELD_WORK_ITEM": settings.RAGIC_FIELD_WORK_ITEM,
            "RAGIC_FIELD_INSPECT_DT": settings.RAGIC_FIELD_INSPECT_DT,
            "RAGIC_FIELD_DEPT": settings.RAGIC_FIELD_DEPT,
            "RAGIC_FIELD_CLOSE_DATE": settings.RAGIC_FIELD_CLOSE_DATE,
            "RAGIC_FIELD_SUBTOTAL": settings.RAGIC_FIELD_SUBTOTAL,
            "RAGIC_FIELD_INCOMPLETE": settings.RAGIC_FIELD_INCOMPLETE,
        },
    }


# ── POST /sync — 從 Ragic 同步資料到本地 DB ────────────────────────────────────
@router.post("/sync", summary="從 Ragic 同步客房保養資料到本地 DB（背景執行）", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def sync_records(background_tasks: BackgroundTasks):
    """觸發背景同步：Ragic → SQLite，立即回傳，不阻塞畫面"""
    background_tasks.add_task(sync_from_ragic)
    return {"success": True, "message": "同步已在背景啟動"}


# ── GET /options — 下拉選項 ──────────────────────────────────────────────────
@router.get("/options", response_model=OptionsResponse, summary="取得選項清單")
async def get_options():
    """回傳前端新增/編輯表單所需的下拉選項"""
    return OptionsResponse(
        inspect_item_options=INSPECT_ITEM_OPTIONS,
        work_item_options=WORK_ITEM_OPTIONS,
    )


# ── GET /stats — 統計總覽 ────────────────────────────────────────────────────
@router.get("/stats", response_model=RoomMaintenanceStatsResponse, summary="統計總覽")
async def get_stats(db: Session = Depends(get_db)):
    """回傳 KPI 數字：完成率、總筆數、未完項目數等（從本地 DB 計算）"""
    try:
        stats = svc.get_stats(db)
        return RoomMaintenanceStatsResponse(data=stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"統計計算失敗：{str(e)}",
        )


# ── GET / — 列表 ─────────────────────────────────────────────────────────────
@router.get("/", response_model=RoomMaintenanceListResponse, summary="客房保養清單")
async def list_records(
    room_no:  Optional[str] = Query(None, description="依房號篩選"),
    work_item: Optional[str] = Query(None, description="依工作項目篩選"),
    dept:     Optional[str] = Query(None, description="依報修部門篩選"),
    page:     int = Query(1,  ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """從本地 SQLite 讀取客房保養清單，支援篩選與分頁"""
    try:
        return svc.list_records(
            db=db,
            room_no=room_no,
            work_item=work_item,
            dept=dept,
            page=page,
            per_page=per_page,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"讀取本地資料失敗：{str(e)}",
        )


# ── GET /{record_id} — 單筆 ──────────────────────────────────────────────────
@router.get("/{record_id}", response_model=RoomMaintenanceSingleResponse, summary="單筆記錄")
async def get_record(record_id: str, db: Session = Depends(get_db)):
    """從本地 DB 讀取單筆客房保養記錄"""
    try:
        record = svc.get_record(db, record_id)
        return RoomMaintenanceSingleResponse(data=record)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ── POST / — 新增（寫 Ragic，背景同步回 DB）──────────────────────────────────
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="新增客房保養記錄",
)
async def create_record(payload: RoomMaintenanceCreate, background_tasks: BackgroundTasks):
    """新增記錄到 Ragic，並在背景觸發同步更新本地 DB"""
    try:
        result = await svc.create_record(payload)
        background_tasks.add_task(sync_from_ragic)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


# ── PUT /{record_id} — 更新 ──────────────────────────────────────────────────
@router.put("/{record_id}", summary="更新記錄")
async def update_record(record_id: str, payload: RoomMaintenanceUpdate, background_tasks: BackgroundTasks):
    """更新 Ragic 記錄，並在背景觸發同步更新本地 DB"""
    try:
        result = await svc.update_record(record_id, payload)
        background_tasks.add_task(sync_from_ragic)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


# ── DELETE /{record_id} — 刪除 ───────────────────────────────────────────────
@router.delete("/{record_id}", summary="刪除記錄")
async def delete_record(record_id: str):
    """從 Ragic 刪除記錄"""
    try:
        return await svc.delete_record(record_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
