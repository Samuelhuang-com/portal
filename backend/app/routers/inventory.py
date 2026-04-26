"""
倉庫庫存 API Router
Prefix: /api/v1/inventory

架構：讀取本地 SQLite DB（由 /sync 同步自 Ragic），此模組為唯讀。
"""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.schemas.inventory import (
    InventoryListResponse,
    InventorySingleResponse,
    InventoryStatsResponse,
)
from app.services import inventory_service as svc
from app.services.inventory_sync import sync_from_ragic

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── GET /debug-raw — 查看 Ragic 原始回傳格式（除錯用）───────────────────────
@router.get("/debug-raw", summary="[除錯] 查看 Ragic 原始 JSON key 格式", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def debug_raw():
    """直接回傳 Ragic 第一筆記錄的原始 key，用於確認欄位 ID 格式"""
    from app.services.ragic_adapter import RagicAdapter
    from app.core.config import settings

    adapter = RagicAdapter(sheet_path=settings.RAGIC_INVENTORY_PATH)
    raw_data = await adapter.fetch_all()

    first_id, first_record = next(iter(raw_data.items()), (None, {}))
    return {
        "total_records": len(raw_data),
        "first_ragic_id": first_id,
        "raw_keys": list(first_record.keys()),
        "raw_sample": {k: v for k, v in list(first_record.items())[:20]},
        "sheet_path": settings.RAGIC_INVENTORY_PATH,
    }


# ── POST /sync — 從 Ragic 同步資料到本地 DB ────────────────────────────────────
@router.post("/sync", summary="從 Ragic 同步倉庫庫存資料到本地 DB（背景執行）", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def sync_records(background_tasks: BackgroundTasks):
    """觸發背景同步：Ragic → SQLite，立即回傳，不阻塞畫面"""
    background_tasks.add_task(sync_from_ragic)
    return {"success": True, "message": "同步已在背景啟動"}


# ── GET /stats — 統計總覽 ────────────────────────────────────────────────────
@router.get("/stats", response_model=InventoryStatsResponse, summary="統計總覽")
async def get_stats(db: Session = Depends(get_db)):
    """回傳 KPI 數字：SKU 數、總庫存量、零庫存數、倉庫數"""
    try:
        stats = svc.get_stats(db)
        return InventoryStatsResponse(data=stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"統計計算失敗：{str(e)}",
        )


# ── GET / — 列表 ─────────────────────────────────────────────────────────────
@router.get("/", response_model=InventoryListResponse, summary="倉庫庫存清單")
async def list_records(
    warehouse_code: Optional[str] = Query(None, description="依倉庫代碼篩選"),
    product_no:     Optional[str] = Query(None, description="依商品編號篩選"),
    product_name:   Optional[str] = Query(None, description="依商品名稱篩選"),
    page:     int = Query(1,  ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """從本地 SQLite 讀取倉庫庫存清單，支援篩選與分頁"""
    try:
        return svc.list_records(
            db=db,
            warehouse_code=warehouse_code,
            product_no=product_no,
            product_name=product_name,
            page=page,
            per_page=per_page,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"讀取本地資料失敗：{str(e)}",
        )


# ── GET /{record_id} — 單筆 ──────────────────────────────────────────────────
@router.get("/{record_id}", response_model=InventorySingleResponse, summary="單筆庫存記錄")
async def get_record(record_id: str, db: Session = Depends(get_db)):
    """從本地 DB 讀取單筆庫存記錄"""
    try:
        record = svc.get_record(db, record_id)
        return InventorySingleResponse(data=record)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
