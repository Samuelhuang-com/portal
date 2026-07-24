"""
主管交辦／緊急事件 API Router
Prefix: /api/v1/other-tasks

端點：
  GET  /raw-fields            — Ragic 欄位名稱（debug 用）
  POST /sync                  — 觸發背景同步：Ragic → SQLite
  GET  /years                 — 資料中的年份清單
  GET  /filter-options        — 過濾條件選項（狀態、主管、工程人員）
  GET  /detail                — 明細清單（分頁+排序+搜尋+類型篩選）
  GET  /db-images/{ragic_id}  — 從 DB 讀取附圖（不打 Ragic）
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import case, text
from sqlalchemy.orm import Session

from app.core.database import get_db, engine
from app.dependencies import get_current_user, require_roles
from app.models.other_tasks import OtherTask
from app.services.other_tasks_service import _make_adapter
from app.services.ragic_verify_utils import (
    read_portal_count_and_last_sync, read_portal_ragic_ids,
    build_verify_count_response, build_verify_diff_response,
)

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── 啟動時自動補 images_json 欄位（輕量 migration）────────────────────────────

def _ensure_images_column() -> None:
    """若 other_task 表已存在但缺少 images_json 欄位，自動 ALTER TABLE 補上。"""
    try:
        with engine.connect() as conn:
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info(other_task)"))]
            if "images_json" not in cols:
                conn.execute(text("ALTER TABLE other_task ADD COLUMN images_json TEXT"))
                conn.commit()
                logger.info("[OtherTasks] 已補充 images_json 欄位")
    except Exception as exc:
        logger.warning(f"[OtherTasks] images_json migration 跳過：{exc}")


def _ensure_venue_column() -> None:
    """若 other_task 表已存在但缺少 venue 欄位，自動 ALTER TABLE 補上。"""
    try:
        with engine.connect() as conn:
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info(other_task)"))]
            if "venue" not in cols:
                conn.execute(text("ALTER TABLE other_task ADD COLUMN venue TEXT DEFAULT ''"))
                conn.commit()
                logger.info("[OtherTasks] 已補充 venue 欄位")
    except Exception as exc:
        logger.warning(f"[OtherTasks] venue migration 跳過：{exc}")


_ensure_images_column()
_ensure_venue_column()


# ── /raw-fields ───────────────────────────────────────────────────────────────

@router.get("/raw-fields", summary="回傳 Ragic 第一筆欄位名稱（debug 用）",
            dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def get_raw_fields():
    from app.services.other_tasks_service import fetch_raw_fields
    return await fetch_raw_fields()


# ── /sync ─────────────────────────────────────────────────────────────────────

@router.post("/sync", summary="觸發背景同步：Ragic → SQLite")
async def trigger_sync(background_tasks: BackgroundTasks):
    from app.services.other_tasks_sync import sync_from_ragic
    background_tasks.add_task(sync_from_ragic)
    return {"ok": True, "message": "主管交辦／緊急事件同步已啟動（背景執行）"}


# ── /verify-count／/verify-diff ─────────────────────────────────────────────────

@router.get("/verify-count", summary="與 Ragic 數量比對（管理員）",
            dependencies=[Depends(require_roles("system_admin"))])
async def verify_count(db: Session = Depends(get_db)):
    portal_count, last_synced_at = await read_portal_count_and_last_sync(
        db, OtherTask, "主管交辦／緊急事件"
    )
    adapter = _make_adapter()
    try:
        ragic_count = await adapter.fetch_count()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ragic 連線失敗：{exc}")
    return build_verify_count_response("主管交辦／緊急事件", portal_count, ragic_count, last_synced_at)


@router.get("/verify-diff", summary="與 Ragic 明細差集比對（管理員）",
            dependencies=[Depends(require_roles("system_admin"))])
async def verify_diff(db: Session = Depends(get_db)):
    adapter = _make_adapter()
    try:
        raw_ids = await adapter.fetch_ids()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ragic 連線失敗：{exc}")
    ragic_url_map = {rid: f"{adapter.base_url}/{rid}" for rid in raw_ids}
    portal_ids = await read_portal_ragic_ids(db, OtherTask)
    return build_verify_diff_response(ragic_url_map, portal_ids)


# ── /years ────────────────────────────────────────────────────────────────────

@router.get("/years", summary="回傳資料中的年份清單")
def get_years(db: Session = Depends(get_db)):
    rows = (
        db.query(OtherTask.year)
        .filter(OtherTask.year.isnot(None))
        .distinct()
        .order_by(OtherTask.year.desc())
        .all()
    )
    return {"years": [r.year for r in rows]}


# ── /filter-options ──────────────────────────────────────────────────────────

@router.get("/filter-options", summary="回傳過濾條件選項")
def get_filter_options(db: Session = Depends(get_db)):
    statuses = [
        r.status for r in
        db.query(OtherTask.status).distinct().order_by(OtherTask.status).all()
        if r.status
    ]
    supervisors = [
        r.supervisor for r in
        db.query(OtherTask.supervisor).distinct().order_by(OtherTask.supervisor).all()
        if r.supervisor
    ]
    engineers = [
        r.engineer for r in
        db.query(OtherTask.engineer).distinct().order_by(OtherTask.engineer).all()
        if r.engineer
    ]
    venues = [
        r.venue for r in
        db.query(OtherTask.venue).distinct().order_by(OtherTask.venue).all()
        if r.venue
    ]
    return {
        "statuses":    statuses,
        "supervisors": supervisors,
        "engineers":   engineers,
        "venues":      venues,
    }


# ── /detail ───────────────────────────────────────────────────────────────────

@router.get("/detail", summary="明細清單（分頁+過濾+搜尋）")
def get_detail(
    task_type:  Optional[str] = Query(None,  description="屬性篩選：上級交辦 / 緊急事件"),
    year:       Optional[int] = Query(None),
    month:      Optional[int] = Query(None),
    status:     Optional[str] = Query(None),
    supervisor: Optional[str] = Query(None),
    engineer:   Optional[str] = Query(None),
    venue:      Optional[str] = Query(None,  description="歸屬篩選：飯店 / 商場"),
    search:     Optional[str] = Query(None,  description="關鍵字搜尋（問題說明/備註）"),
    page:       int           = Query(1,     ge=1),
    page_size:  int           = Query(50,    ge=1, le=200),
    sort_field: str           = Query("created_at", description="排序欄位"),
    sort_order: str           = Query("desc",        description="排序方向：asc / desc"),
    db: Session = Depends(get_db),
):
    q = db.query(OtherTask)

    if task_type:
        q = q.filter(OtherTask.task_type == task_type)
    if year:
        q = q.filter(OtherTask.year == year)
    if month:
        q = q.filter(OtherTask.month == month)
    if status:
        q = q.filter(OtherTask.status == status)
    if supervisor:
        q = q.filter(OtherTask.supervisor == supervisor)
    if engineer:
        q = q.filter(OtherTask.engineer == engineer)
    if venue:
        q = q.filter(OtherTask.venue == venue)
    if search:
        like = f"%{search}%"
        q = q.filter(
            OtherTask.description.ilike(like) |
            OtherTask.notes.ilike(like)
        )

    total = q.count()

    sort_col = {
        "created_at": OtherTask.created_at,
        "updated_at": OtherTask.updated_at,
        "status":     OtherTask.status,
        "work_hours": OtherTask.work_hours,
        "supervisor": OtherTask.supervisor,
        "engineer":   OtherTask.engineer,
    }.get(sort_field, OtherTask.created_at)

    if sort_order == "asc":
        q = q.order_by(sort_col.asc())
    else:
        q = q.order_by(sort_col.desc())

    offset = (page - 1) * page_size
    items = q.offset(offset).limit(page_size).all()

    return {
        "items":     [item.to_dict() for item in items],
        "total":     total,
        "page":      page,
        "page_size": page_size,
    }


# ── /stats ────────────────────────────────────────────────────────────────────

@router.get("/stats", summary="各 task_type 件數與工時統計（供 Dashboard 用）")
def get_stats(
    year:       Optional[int] = Query(None),
    month:      Optional[int] = Query(None),
    status:     Optional[str] = Query(None),
    supervisor: Optional[str] = Query(None),
    engineer:   Optional[str] = Query(None),
    venue:      Optional[str] = Query(None),
    search:     Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    按 task_type 分組回傳件數（total / hotel / mall / completed / open）與工時合計（work_hours）。
    MallMgmtDashboard、ExecWorkDashboard 的 KPI 卡片與工項比較表使用此端點。
    hotel / mall 件數依 venue 欄位（飯店 / 商場）拆分；venue 空白者歸入 total 但不計入 hotel/mall。
    completed = 狀態為 結案/已結案/已完成/完成 的件數；open = total - completed（未結案）。
    支援 status / supervisor / engineer / venue / search 額外篩選（供 OtherTasksPage TAB 小計用）。
    """
    from sqlalchemy import func as sqlfunc

    COMPLETED_STATUSES = ("結案", "已結案", "已完成", "完成")

    def _apply_filters(q):
        if year:
            q = q.filter(OtherTask.year == year)
        if month:
            q = q.filter(OtherTask.month == month)
        if status:
            q = q.filter(OtherTask.status == status)
        if supervisor:
            q = q.filter(OtherTask.supervisor == supervisor)
        if engineer:
            q = q.filter(OtherTask.engineer == engineer)
        if venue:
            q = q.filter(OtherTask.venue == venue)
        if search:
            like = f"%{search}%"
            q = q.filter(
                OtherTask.description.ilike(like) |
                OtherTask.notes.ilike(like)
            )
        return q

    # ── 1. 總計（task_type 分組）
    base_q = db.query(
        OtherTask.task_type,
        sqlfunc.count(OtherTask.ragic_id).label("total"),
        sqlfunc.sum(OtherTask.work_hours).label("work_hours"),
        sqlfunc.sum(
            case((OtherTask.status.in_(COMPLETED_STATUSES), 1), else_=0)
        ).label("completed"),
    )
    base_q = _apply_filters(base_q)
    rows = base_q.group_by(OtherTask.task_type).all()

    result: dict = {}
    for row in rows:
        total     = row.total or 0
        completed = int(row.completed or 0)
        result[row.task_type] = {
            "total":      total,
            "hotel":      0,
            "mall":       0,
            "work_hours": round(float(row.work_hours or 0), 1),
            "completed":  completed,
            "open":       total - completed,
        }

    # ── 2. venue 拆分（task_type × venue 分組）
    venue_q = db.query(
        OtherTask.task_type,
        OtherTask.venue,
        sqlfunc.count(OtherTask.ragic_id).label("cnt"),
    )
    venue_q = _apply_filters(venue_q)
    venue_q = venue_q.filter(OtherTask.venue != "")
    for vrow in venue_q.group_by(OtherTask.task_type, OtherTask.venue).all():
        if vrow.task_type not in result:
            continue
        if vrow.venue == "飯店":
            result[vrow.task_type]["hotel"] += vrow.cnt or 0
        elif vrow.venue == "商場":
            result[vrow.task_type]["mall"] += vrow.cnt or 0

    return result


# ── /db-images/{ragic_id} ─────────────────────────────────────────────────────

@router.get("/db-images/{ragic_id}", summary="從 DB 讀取附圖（不打 Ragic）")
def get_db_images(ragic_id: str, db: Session = Depends(get_db)):
    """
    從本地 SQLite other_task.images_json 讀取附圖清單。
    Drawer 圖片預覽使用此端點，不依賴 Ragic 即時連線。
    """
    record = db.get(OtherTask, ragic_id)
    if not record:
        return {"ragic_id": ragic_id, "images": [], "source": "not_found"}
    try:
        images = json.loads(record.images_json) if record.images_json else []
    except Exception:
        images = []
    return {"ragic_id": ragic_id, "images": images, "source": "db"}
