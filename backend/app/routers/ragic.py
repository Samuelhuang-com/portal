"""
Ragic 連線管理 API Router
Prefix: /api/v1/ragic

端點：
  GET    /connections                    — 列出所有連線
  POST   /connections                    — 建立連線
  PUT    /connections/{id}               — 更新連線（api_key 可選）
  DELETE /connections/{id}               — 軟刪除（is_active=False）
  PATCH  /connections/{id}/active        — 切換啟用/停用
  POST   /connections/{id}/sync          — 手動觸發同步（背景）
  GET    /connections/{id}/logs          — 同步日誌（最新 50 筆）
  GET    /snapshots/{id}/latest          — 最新資料快照
  GET    /scheduler/status               — 列出所有排程任務狀態
"""
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.crypto import encrypt
from app.core.database import get_db
from app.core.scheduler import (
    deregister_connection_job,
    get_module_sync_interval,
    list_connection_jobs,
    register_connection_job,
    set_module_sync_interval,
)
from app.dependencies import is_system_admin
from app.models.ragic_connection import RagicConnection
from app.models.sync_log import SyncLog
from app.schemas.ragic import (
    RagicConnectionCreate,
    RagicConnectionOut,
    RagicConnectionUpdate,
    SyncLogOut,
)

router = APIRouter()


# ── GET /connections ──────────────────────────────────────────────────────────

@router.get("/connections", response_model=List[RagicConnectionOut])
def list_connections(
    current_user=Depends(is_system_admin),
    db: Session = Depends(get_db),
):
    """列出所有連線（含停用的）。"""
    return db.query(RagicConnection).order_by(RagicConnection.created_at).all()


# ── POST /connections ─────────────────────────────────────────────────────────

@router.post("/connections", response_model=RagicConnectionOut)
def create_connection(
    data: RagicConnectionCreate,
    current_user=Depends(is_system_admin),
    db: Session = Depends(get_db),
):
    """建立新 Ragic 連線，並自動加入排程。"""
    conn = RagicConnection(
        tenant_id=data.tenant_id,
        display_name=data.display_name,
        server=data.server,
        account_name=data.account_name,
        api_key_enc=encrypt(data.api_key),
        sheet_path=data.sheet_path,
        field_mappings=data.field_mappings,
        sync_interval=data.sync_interval,
        is_active=True,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    # 新增排程任務
    register_connection_job(conn.id, conn.sync_interval)

    return conn


# ── PUT /connections/{conn_id} ────────────────────────────────────────────────

@router.put("/connections/{conn_id}", response_model=RagicConnectionOut)
def update_connection(
    conn_id: str,
    data: RagicConnectionUpdate,
    current_user=Depends(is_system_admin),
    db: Session = Depends(get_db),
):
    """
    更新連線設定。api_key 為選填——不傳則沿用現有加密值。
    更新 sync_interval 後會自動重新排程。
    """
    conn = db.query(RagicConnection).filter(RagicConnection.id == conn_id).first()
    if not conn:
        raise HTTPException(404, "連線不存在")

    conn.display_name  = data.display_name
    conn.server        = data.server
    conn.account_name  = data.account_name
    conn.sheet_path    = data.sheet_path
    conn.field_mappings = data.field_mappings
    conn.sync_interval = data.sync_interval

    if data.api_key:                    # 只在有傳入時才更新加密值
        conn.api_key_enc = encrypt(data.api_key)

    db.commit()
    db.refresh(conn)

    # 若連線為啟用狀態，重新排程（更新 interval）
    if conn.is_active:
        register_connection_job(conn.id, conn.sync_interval)

    return conn


# ── DELETE /connections/{conn_id} ─────────────────────────────────────────────

@router.delete("/connections/{conn_id}", status_code=200)
def delete_connection(
    conn_id: str,
    current_user=Depends(is_system_admin),
    db: Session = Depends(get_db),
):
    """軟刪除連線（設 is_active=False）並移除排程任務。"""
    conn = db.query(RagicConnection).filter(RagicConnection.id == conn_id).first()
    if not conn:
        raise HTTPException(404, "連線不存在")

    conn.is_active = False
    db.commit()

    deregister_connection_job(conn_id)
    return {"success": True, "message": f"連線「{conn.display_name}」已停用並移除排程"}


# ── PATCH /connections/{conn_id}/active ───────────────────────────────────────

@router.patch("/connections/{conn_id}/active", response_model=RagicConnectionOut)
def toggle_connection_active(
    conn_id: str,
    current_user=Depends(is_system_admin),
    db: Session = Depends(get_db),
):
    """切換連線的啟用/停用狀態，並同步更新排程任務。"""
    conn = db.query(RagicConnection).filter(RagicConnection.id == conn_id).first()
    if not conn:
        raise HTTPException(404, "連線不存在")

    conn.is_active = not conn.is_active
    db.commit()
    db.refresh(conn)

    if conn.is_active:
        register_connection_job(conn.id, conn.sync_interval)
    else:
        deregister_connection_job(conn.id)

    return conn


# ── POST /connections/{conn_id}/sync ──────────────────────────────────────────

@router.post("/connections/{conn_id}/sync")
def trigger_sync(
    conn_id: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(is_system_admin),
    db: Session = Depends(get_db),
):
    """手動觸發單一連線同步（背景執行，立即回傳）。"""
    conn = db.query(RagicConnection).filter(
        RagicConnection.id == conn_id,
        RagicConnection.is_active == True,
    ).first()
    if not conn:
        raise HTTPException(404, "連線不存在或已停用")

    from app.services.sync_service import run_sync
    background_tasks.add_task(run_sync, conn_id, "manual")
    return {"success": True, "message": f"同步已在背景啟動：{conn.display_name}"}


# ── GET /connections/{conn_id}/logs ───────────────────────────────────────────

@router.get("/connections/{conn_id}/logs", response_model=List[SyncLogOut])
def get_sync_logs(
    conn_id: str,
    limit: int = 50,
    current_user=Depends(is_system_admin),
    db: Session = Depends(get_db),
):
    """取得連線同步日誌（預設最新 50 筆）。"""
    conn = db.query(RagicConnection).filter(RagicConnection.id == conn_id).first()
    if not conn:
        raise HTTPException(404, "連線不存在")

    return (
        db.query(SyncLog)
        .filter(SyncLog.connection_id == conn_id)
        .order_by(SyncLog.started_at.desc())
        .limit(min(limit, 200))
        .all()
    )


# ── GET /snapshots/{conn_id}/latest ───────────────────────────────────────────

@router.get("/snapshots/{conn_id}/latest")
def get_latest_snapshot(
    conn_id: str,
    current_user=Depends(is_system_admin),
    db: Session = Depends(get_db),
):
    """取得連線最新資料快照。"""
    from app.models.data_snapshot import DataSnapshot

    snap = (
        db.query(DataSnapshot)
        .filter(DataSnapshot.connection_id == conn_id)
        .order_by(DataSnapshot.synced_at.desc())
        .first()
    )
    if not snap:
        raise HTTPException(404, "尚無快照資料")

    return {
        "id":            snap.id,
        "connection_id": snap.connection_id,
        "synced_at":     snap.synced_at.isoformat(),
        "record_count":  snap.record_count,
        "data":          snap.data,
    }


# ── GET /scheduler/status ─────────────────────────────────────────────────────

@router.get("/scheduler/status")
def get_scheduler_status(current_user=Depends(is_system_admin)):
    """列出所有 RagicConnection 排程任務的目前狀態（下次執行時間等）。"""
    return {"jobs": list_connection_jobs()}


# ── GET/POST /scheduler/module-interval ───────────────────────────────────────

@router.get("/scheduler/module-interval")
def get_module_interval(current_user=Depends(is_system_admin)):
    """取得目前硬編碼模組（客房保養、工務報修等）的自動同步間隔（分鐘）。"""
    return {"interval_minutes": get_module_sync_interval()}


# ── POST /sync-logs/trigger ───────────────────────────────────────────────────

@router.post("/sync-logs/trigger")
def trigger_all_modules_sync(
    background_tasks: BackgroundTasks,
    current_user=Depends(is_system_admin),
):
    """手動觸發一次所有硬編碼模組的完整同步（背景執行，立即回傳）。"""
    # 延遲 import 避免 circular import（main ↔ ragic）
    from app.main import _manual_sync  # noqa: PLC0415
    background_tasks.add_task(_manual_sync)
    return {"success": True, "message": "所有模組同步已在背景啟動，完成後可重新整理查看紀錄"}


# ── GET /sync-logs/modules ────────────────────────────────────────────────────

@router.get("/sync-logs/modules")
def list_syncable_modules(current_user=Depends(is_system_admin)):
    """回傳所有可單獨觸發同步的模組名稱清單。"""
    from app.main import list_syncable_modules as _list  # noqa: PLC0415
    return {"modules": _list()}


# ── POST /sync-logs/trigger/{module_name} ────────────────────────────────────

@router.post("/sync-logs/trigger/{module_name}")
def trigger_single_module_sync(
    module_name: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(is_system_admin),
):
    """手動觸發單一模組同步（背景執行，立即回傳）。"""
    from app.main import _single_module_sync, list_syncable_modules  # noqa: PLC0415
    if module_name not in list_syncable_modules():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"未知模組：{module_name}")
    background_tasks.add_task(_single_module_sync, module_name)
    return {"success": True, "message": f"{module_name} 同步已在背景啟動，約 30 秒後重新整理可查看結果"}


# ── GET /sync-logs/recent ─────────────────────────────────────────────────────

@router.get("/sync-logs/recent")
def get_recent_sync_logs(
    hours: int = 24,
    current_user=Depends(is_system_admin),
    db: Session = Depends(get_db),
):
    """
    取得最近 N 小時內的模組同步紀錄（預設 24 小時），依 started_at 降序排列。
    """
    from datetime import timedelta
    from app.models.module_sync_log import ModuleSyncLog
    from app.core.time import twnow

    since = twnow() - timedelta(hours=max(1, min(hours, 168)))
    logs = (
        db.query(ModuleSyncLog)
        .filter(ModuleSyncLog.started_at >= since)
        .order_by(ModuleSyncLog.started_at.desc())
        .limit(500)
        .all()
    )
    return [
        {
            "id":            log.id,
            "module_name":   log.module_name,
            "started_at":    log.started_at.isoformat(),
            "finished_at":   log.finished_at.isoformat() if log.finished_at else None,
            "duration_sec":  log.duration_sec,
            "status":        log.status,
            "fetched":       log.fetched,
            "upserted":      log.upserted,
            "errors_count":  log.errors_count,
            "error_msg":     log.error_msg,
            "triggered_by":  log.triggered_by,
            "retry_count":   getattr(log, "retry_count", 0),
            "parent_log_id": getattr(log, "parent_log_id", None),
            "is_anomaly":    getattr(log, "is_anomaly", False),
        }
        for log in logs
    ]


# ── GET /sync-logs/loop-health ────────────────────────────────────────────────

@router.get("/sync-logs/loop-health")
def get_loop_health(
    current_user=Depends(is_system_admin),
    db: Session = Depends(get_db),
):
    """
    Loop Engineering 健康儀表板：各模組最新同步狀態、重試次數、異常旗標、連續失敗數。

    每個模組回傳：
    - module_name       : 模組名稱
    - last_status       : 最新一次（retry_count=0）的狀態
    - last_synced_at    : 最新一次同步時間
    - total_retries_24h : 過去 24 小時內的重試記錄筆數
    - anomaly_count_24h : 過去 24 小時內的異常標記筆數
    - consecutive_fails : 最近連續失敗次數（遇到 success 停止計算）
    """
    from datetime import timedelta
    from app.models.module_sync_log import ModuleSyncLog
    from app.core.time import twnow
    from sqlalchemy import func

    now = twnow()
    since = now - timedelta(hours=24)

    # 每個模組最新一筆（首次嘗試，排除重試記錄）
    subq = (
        db.query(
            ModuleSyncLog.module_name,
            func.max(ModuleSyncLog.id).label("max_id"),
        )
        .filter(ModuleSyncLog.retry_count == 0)
        .group_by(ModuleSyncLog.module_name)
        .subquery()
    )
    latest_rows = (
        db.query(ModuleSyncLog)
        .join(subq, ModuleSyncLog.id == subq.c.max_id)
        .all()
    )

    result = []
    for row in sorted(latest_rows, key=lambda r: r.module_name):
        # 過去 24h 重試次數
        retries_24h = (
            db.query(func.count(ModuleSyncLog.id))
            .filter(
                ModuleSyncLog.module_name == row.module_name,
                ModuleSyncLog.retry_count > 0,
                ModuleSyncLog.started_at >= since,
            )
            .scalar()
            or 0
        )
        # 過去 24h 異常次數
        anomaly_24h = (
            db.query(func.count(ModuleSyncLog.id))
            .filter(
                ModuleSyncLog.module_name == row.module_name,
                ModuleSyncLog.is_anomaly == True,  # noqa: E712
                ModuleSyncLog.started_at >= since,
            )
            .scalar()
            or 0
        )
        # 連續失敗次數（從最新往回算，遇到 success 停止）
        recent_10 = (
            db.query(ModuleSyncLog)
            .filter(
                ModuleSyncLog.module_name == row.module_name,
                ModuleSyncLog.retry_count == 0,
            )
            .order_by(ModuleSyncLog.started_at.desc())
            .limit(10)
            .all()
        )
        consecutive_fails = 0
        for r in recent_10:
            if r.status == "success":
                break
            consecutive_fails += 1

        result.append({
            "module_name":        row.module_name,
            "last_status":        row.status,
            "last_synced_at":     row.started_at.isoformat(),
            "total_retries_24h":  retries_24h,
            "anomaly_count_24h":  anomaly_24h,
            "consecutive_fails":  consecutive_fails,
        })

    return result


# ── Ragic 應用程式對應表（Portal 標註）────────────────────────────────────────

from app.models.ragic_app_directory import RagicAppPortalAnnotation


@router.get("/app-directory/annotations")
def get_app_directory_annotations(
    db: Session = Depends(get_db),
    current_user=Depends(is_system_admin),
):
    """
    取得所有 Portal 標註（portal_name / portal_url）。
    前端將這份資料與靜態 Ragic App 清單合併顯示。
    """
    rows = db.query(RagicAppPortalAnnotation).all()
    return {
        row.item_no: {
            "portal_name": row.portal_name or "",
            "portal_url":  row.portal_url or "",
            "updated_at":  row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    }


@router.put("/app-directory/annotations/{item_no}")
def upsert_app_directory_annotation(
    item_no: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user=Depends(is_system_admin),
):
    """
    新增或更新單筆 Portal 標註。
    body: { "portal_name": "...", "portal_url": "..." }
    僅 system_admin 可操作。
    """
    if item_no < 1 or item_no > 500:
        raise HTTPException(400, "item_no 超出範圍")

    portal_name = str(body.get("portal_name", "")).strip()
    portal_url  = str(body.get("portal_url",  "")).strip()

    row = db.query(RagicAppPortalAnnotation).filter_by(item_no=item_no).first()
    if row:
        row.portal_name = portal_name
        row.portal_url  = portal_url
    else:
        row = RagicAppPortalAnnotation(
            item_no=item_no,
            portal_name=portal_name,
            portal_url=portal_url,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "item_no":     row.item_no,
        "portal_name": row.portal_name,
        "portal_url":  row.portal_url,
        "updated_at":  row.updated_at.isoformat() if row.updated_at else None,
    }


@router.post("/scheduler/module-interval")
def update_module_interval(
    body: dict,
    current_user=Depends(is_system_admin),
):
    """
    更新硬編碼模組的自動同步間隔。
    body: { "interval_minutes": 30 }
    注意：in-memory 設定，服務重啟後恢復預設 30 分鐘。
    """
    minutes = body.get("interval_minutes")
    if not isinstance(minutes, int) or minutes < 5:
        from fastapi import HTTPException
        raise HTTPException(400, "interval_minutes 必須為整數且 ≥ 5")
    set_module_sync_interval(minutes)
    return {"success": True, "interval_minutes": minutes, "message": f"自動同步間隔已更新為 {minutes} 分鐘"}
