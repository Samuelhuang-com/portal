"""
整棟工務每日巡檢 - B4F  API Router【寬表格 Pivot 架構】
Prefix: /api/v1/mall/b4f-inspection

架構：
  每次巡檢場次儲存為 B4FInspectionBatch（ragic_id = Ragic Row ID）
  場次的 35 個設備欄 pivot 成 B4FInspectionItem 記錄
  路由 /batches/{batch_id} 的 batch_id = ragic_id（Ragic Row ID 字串）

端點：
  POST /sync                    — 從 Ragic 同步
  GET  /batches                 — 巡檢場次清單（日期篩選）
  GET  /batches/{batch_id}      — 單場次完整資料（含所有設備項目 + KPI）
  GET  /batches/{batch_id}/kpi  — 場次 KPI 統計
  GET  /items                   — 跨場次查詢設備項目
  GET  /stats                   — 全站統計（Dashboard）
  GET  /items/item-history      — 依設備名稱查詢近 N 日歷史
  GET  /debug/ragic-raw         — 除錯：顯示 Ragic Sheet 2 原始欄位
"""
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.b4f_inspection import B4FInspectionBatch, B4FInspectionItem
from app.schemas.b4f_inspection import (
    InspectionBatchOut, InspectionItemOut, InspectionBatchKPI,
    InspectionBatchDetail, StatusDistItem, InspectionStats,
)
from app.services.b4f_inspection_sync import sync_from_ragic
from app.services.ragic_adapter import RagicAdapter

router = APIRouter()

# ── 狀態設定 ──────────────────────────────────────────────────────────────────
STATUS_LABELS = {
    "normal":    "正常",
    "abnormal":  "異常",
    "pending":   "待處理",
    "unchecked": "未填寫",
}
STATUS_COLORS = {
    "normal":    "#52C41A",
    "abnormal":  "#FF4D4F",
    "pending":   "#FAAD14",
    "unchecked": "#999999",
}


# ── 業務邏輯輔助函式 ──────────────────────────────────────────────────────────

def _batch_to_out(b: B4FInspectionBatch, item_count: int = 0) -> InspectionBatchOut:
    return InspectionBatchOut(
        ragic_id        = b.ragic_id,
        inspection_date = b.inspection_date,
        inspector_name  = b.inspector_name,
        start_time      = b.start_time,
        end_time        = b.end_time,
        work_hours      = b.work_hours,
        item_count      = item_count,
        synced_at       = b.synced_at,
    )


def _item_to_out(it: B4FInspectionItem) -> InspectionItemOut:
    return InspectionItemOut(
        ragic_id       = it.ragic_id,
        batch_ragic_id = it.batch_ragic_id,
        seq_no         = it.seq_no,
        item_name      = it.item_name,
        result_raw     = it.result_raw,
        result_status  = it.result_status,
        abnormal_flag  = bool(it.abnormal_flag),
        synced_at      = it.synced_at,
    )


def _calc_kpi(items: list[B4FInspectionItem]) -> InspectionBatchKPI:
    total     = len(items)
    normal    = sum(1 for it in items if it.result_status == "normal")
    abnormal  = sum(1 for it in items if it.result_status == "abnormal")
    pending   = sum(1 for it in items if it.result_status == "pending")
    unchecked = sum(1 for it in items if it.result_status == "unchecked")
    checked   = normal + abnormal + pending

    completion_rate = round(checked / total * 100, 1) if total > 0 else 0.0
    normal_rate     = round(normal  / checked * 100, 1) if checked > 0 else 0.0

    return InspectionBatchKPI(
        total           = total,
        normal          = normal,
        abnormal        = abnormal,
        pending         = pending,
        unchecked       = unchecked,
        completion_rate = completion_rate,
        normal_rate     = normal_rate,
    )


# ══════════════════════════════════════════════════════════════════════════════
# POST /sync
# ══════════════════════════════════════════════════════════════════════════════
@router.post("/sync", summary="從 Ragic 同步 B4F 巡檢資料（背景執行）")
async def sync_b4f_inspection(background_tasks: BackgroundTasks):
    """觸發背景同步：Ragic → SQLite，立即回傳，不阻塞畫面"""
    background_tasks.add_task(sync_from_ragic)
    return {"status": "ok", "message": "同步已在背景啟動"}


# ══════════════════════════════════════════════════════════════════════════════
# GET /batches
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/batches", summary="取得巡檢場次清單")
def list_batches(
    year_month: Optional[str] = Query(None, description="篩選年月，如 2026/04"),
    start_date: Optional[str] = Query(None, description="起始日期 YYYY/MM/DD"),
    end_date:   Optional[str] = Query(None, description="結束日期 YYYY/MM/DD"),
    db: Session = Depends(get_db),
):
    q = db.query(B4FInspectionBatch)
    if year_month:
        q = q.filter(B4FInspectionBatch.inspection_date.like(f"{year_month}%"))
    if start_date:
        q = q.filter(B4FInspectionBatch.inspection_date >= start_date)
    if end_date:
        q = q.filter(B4FInspectionBatch.inspection_date <= end_date)

    batches = q.order_by(B4FInspectionBatch.inspection_date.desc()).all()

    result = []
    for b in batches:
        items = db.query(B4FInspectionItem).filter(
            B4FInspectionItem.batch_ragic_id == b.ragic_id
        ).all()
        kpi = _calc_kpi(items)
        result.append({
            "batch": _batch_to_out(b, len(items)).model_dump(),
            "kpi":   kpi.model_dump(),
        })
    return result


# ══════════════════════════════════════════════════════════════════════════════
# GET /batches/{batch_id}
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/batches/{batch_id}", summary="取得單一場次完整資料（含所有設備項目 + KPI）")
def get_batch_detail(
    batch_id:      str,
    result_status: Optional[str] = Query(None, alias="status"),
    search:        Optional[str] = Query(None, description="搜尋設備名稱"),
    db:            Session = Depends(get_db),
):
    batch = db.get(B4FInspectionBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"找不到場次：{batch_id}")

    items = db.query(B4FInspectionItem).filter(
        B4FInspectionItem.batch_ragic_id == batch_id
    ).order_by(B4FInspectionItem.seq_no).all()

    kpi = _calc_kpi(items)

    filtered = []
    for it in items:
        if result_status:
            if result_status == "abnormal_all":
                if it.result_status not in ("abnormal", "pending"):
                    continue
            elif it.result_status != result_status:
                continue
        if search and search.lower() not in it.item_name.lower():
            continue
        filtered.append(_item_to_out(it))

    return InspectionBatchDetail(
        batch = _batch_to_out(batch, len(items)),
        kpi   = kpi,
        items = filtered,
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /batches/{batch_id}/kpi
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/batches/{batch_id}/kpi", summary="取得場次 KPI 統計")
def get_batch_kpi(batch_id: str, db: Session = Depends(get_db)):
    batch = db.get(B4FInspectionBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"找不到場次：{batch_id}")
    items = db.query(B4FInspectionItem).filter(
        B4FInspectionItem.batch_ragic_id == batch_id
    ).all()
    return _calc_kpi(items)


# ══════════════════════════════════════════════════════════════════════════════
# GET /items
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/items", summary="跨場次查詢設備巡檢項目")
def list_items(
    batch_id:      Optional[str] = Query(None, description="場次 ragic_id"),
    result_status: Optional[str] = Query(None, alias="status"),
    search:        Optional[str] = Query(None, description="搜尋設備名稱"),
    db:            Session = Depends(get_db),
):
    q = db.query(B4FInspectionItem)
    if batch_id:
        q = q.filter(B4FInspectionItem.batch_ragic_id == batch_id)

    items = q.order_by(
        B4FInspectionItem.batch_ragic_id,
        B4FInspectionItem.seq_no,
    ).all()

    result = []
    for it in items:
        if result_status and it.result_status != result_status:
            continue
        if search and search.lower() not in it.item_name.lower():
            continue
        result.append(_item_to_out(it))
    return result


# ══════════════════════════════════════════════════════════════════════════════
# GET /stats
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/stats", summary="全站統計（Dashboard）", response_model=InspectionStats)
def get_stats(db: Session = Depends(get_db)):
    today     = date.today()
    today_str = today.strftime("%Y/%m/%d")

    # 最新場次
    latest_batch = db.query(B4FInspectionBatch).order_by(
        B4FInspectionBatch.inspection_date.desc()
    ).first()

    latest_batch_out = None
    latest_kpi       = None
    recent_abnormal: list[InspectionItemOut] = []
    recent_pending:  list[InspectionItemOut] = []
    status_dist:     list[StatusDistItem]    = []

    if latest_batch:
        items = db.query(B4FInspectionItem).filter(
            B4FInspectionItem.batch_ragic_id == latest_batch.ragic_id
        ).order_by(B4FInspectionItem.seq_no).all()

        latest_batch_out = _batch_to_out(latest_batch, len(items))
        latest_kpi       = _calc_kpi(items)

        # 狀態分布
        status_counts = Counter(it.result_status for it in items)
        for s, cnt in status_counts.items():
            if cnt > 0:
                status_dist.append(StatusDistItem(
                    status = s,
                    label  = STATUS_LABELS.get(s, s),
                    count  = cnt,
                    color  = STATUS_COLORS.get(s, "#666666"),
                ))

        recent_abnormal = [
            _item_to_out(it) for it in items
            if it.result_status in ("abnormal", "pending")
        ][:10]

        recent_pending = [
            _item_to_out(it) for it in items
            if it.result_status == "pending"
        ][:10]

    # 近 7 日異常趨勢
    abnormal_trend: list[dict] = []
    for i in range(6, -1, -1):
        d     = today - timedelta(days=i)
        d_str = d.strftime("%Y/%m/%d")

        day_batches = db.query(B4FInspectionBatch).filter(
            B4FInspectionBatch.inspection_date == d_str
        ).all()

        abn_count = 0
        for b in day_batches:
            abn_count += db.query(B4FInspectionItem).filter(
                B4FInspectionItem.batch_ragic_id == b.ragic_id,
                B4FInspectionItem.result_status.in_(["abnormal", "pending"]),
            ).count()

        abnormal_trend.append({
            "date":           d_str,
            "abnormal_count": abn_count,
            "has_record":     len(day_batches) > 0,
        })

    # 近 7 日場次總數
    week_ago         = (today - timedelta(days=7)).strftime("%Y/%m/%d")
    total_batches_7d = db.query(B4FInspectionBatch).filter(
        B4FInspectionBatch.inspection_date >= week_ago
    ).count()

    return InspectionStats(
        latest_batch        = latest_batch_out,
        latest_kpi          = latest_kpi,
        recent_abnormal     = recent_abnormal,
        recent_pending      = recent_pending,
        status_distribution = status_dist,
        total_batches_7d    = total_batches_7d,
        abnormal_trend      = abnormal_trend,
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /items/item-history
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/items/item-history", summary="依設備名稱查詢近 N 日執行歷史")
def get_item_history(
    item_name: str = Query(..., description="設備/項目名稱（完整比對）"),
    days:      int = Query(30, ge=1, le=90, description="查詢最近幾天"),
    db:        Session = Depends(get_db),
):
    today = date.today()

    rows = (
        db.query(B4FInspectionItem, B4FInspectionBatch)
        .join(
            B4FInspectionBatch,
            B4FInspectionItem.batch_ragic_id == B4FInspectionBatch.ragic_id,
        )
        .filter(B4FInspectionItem.item_name == item_name)
        .order_by(B4FInspectionBatch.inspection_date.desc())
        .all()
    )

    if not rows:
        raise HTTPException(status_code=404, detail=f"找不到設備記錄：{item_name}")

    # date → (item, batch) 映射（同日取最新一筆）
    date_map: dict[str, tuple] = {}
    for item, batch in rows:
        if batch.inspection_date not in date_map:
            date_map[batch.inspection_date] = (item, batch)

    # 近 N 日摘要
    daily_summary = []
    for i in range(days - 1, -1, -1):
        d     = today - timedelta(days=i)
        d_str = d.strftime("%Y/%m/%d")

        if d_str in date_map:
            it, b = date_map[d_str]
            daily_summary.append({
                "inspection_date": d_str,
                "inspector_name":  b.inspector_name or "",
                "start_time":      b.start_time or "",
                "result_status":   it.result_status,
                "result_raw":      it.result_raw or "",
                "abnormal_flag":   bool(it.abnormal_flag),
                "has_record":      True,
                "is_today":        (d == today),
            })
        else:
            daily_summary.append({
                "inspection_date": d_str,
                "inspector_name":  "",
                "start_time":      "",
                "result_status":   "no_record",
                "result_raw":      "",
                "abnormal_flag":   False,
                "has_record":      False,
                "is_today":        (d == today),
            })

    normal_days   = sum(1 for ds in daily_summary if ds["result_status"] == "normal")
    abnormal_days = sum(1 for ds in daily_summary if ds["result_status"] in ("abnormal", "pending"))

    return {
        "item_name":     item_name,
        "daily_summary": daily_summary,
        "stats": {
            "total_days":    days,
            "normal_days":   normal_days,
            "abnormal_days": abnormal_days,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# GET /debug/ragic-raw
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/debug/ragic-raw", summary="[除錯] 顯示 Ragic Sheet 2 原始欄位")
async def debug_ragic_raw():
    from app.services.b4f_inspection_sync import (
        B4F_SERVER_URL, B4F_ACCOUNT, B4F_SHEET_PATH, CHECK_ITEMS,
    )

    adapter = RagicAdapter(
        sheet_path=B4F_SHEET_PATH,
        server_url=B4F_SERVER_URL,
        account=B4F_ACCOUNT,
    )
    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        return {"error": str(exc)}

    record_ids = list(raw_data.keys())
    first_rec  = next(iter(raw_data.values()), {}) if raw_data else {}

    # 核對 CHECK_ITEMS 中哪些欄位有實際資料
    matched   = [k for k in CHECK_ITEMS if k in first_rec]
    unmatched = [k for k in CHECK_ITEMS if k not in first_rec]

    return {
        "sheet_path":     B4F_SHEET_PATH,
        "total_records":  len(raw_data),
        "record_ids":     record_ids[:10],
        "all_fields":     list(first_rec.keys()),
        "check_items_matched":   matched,
        "check_items_unmatched": unmatched,
        "first_record_sample":   {k: repr(v)[:80] for k, v in first_rec.items()},
    }
