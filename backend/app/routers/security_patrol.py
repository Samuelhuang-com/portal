"""
保全巡檢 API Router【統一路由，7 張 Sheet 共用】
Prefix: /api/v1/security/patrol

端點：
  POST /sync                              — 同步所有 Sheet（或指定 sheet_key）
  GET  /sheets                            — 取得所有 Sheet 設定清單
  GET  /{sheet_key}/batches               — 場次清單（日期篩選）
  GET  /{sheet_key}/batches/{batch_id}    — 單場次完整資料（含巡檢項目 + KPI）
  GET  /{sheet_key}/batches/{batch_id}/kpi — 場次 KPI 統計
  GET  /{sheet_key}/items                 — 跨場次查詢巡檢項目
  GET  /{sheet_key}/stats                 — 全站統計（Dashboard 用）
  GET  /{sheet_key}/items/item-history    — 依巡檢點查詢近 N 日歷史
  GET  /{sheet_key}/debug/ragic-raw       — 除錯：顯示 Ragic 原始欄位
"""
from collections import Counter
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.security_patrol import SecurityPatrolBatch, SecurityPatrolItem
from app.schemas.security_patrol import (
    PatrolBatchOut, PatrolItemOut, PatrolBatchKPI,
    PatrolBatchDetail, StatusDistItem, PatrolStats, SheetConfig,
)
from app.services.security_patrol_sync import (
    SHEET_CONFIGS, sync_all, sync_sheet,
)
from app.services.ragic_adapter import RagicAdapter
from app.services.security_patrol_sync import SP_SERVER_URL, SP_ACCOUNT

router = APIRouter(dependencies=[Depends(get_current_user)])

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


# ── 輔助函式 ──────────────────────────────────────────────────────────────────

def _validate_sheet_key(sheet_key: str):
    if sheet_key not in SHEET_CONFIGS:
        raise HTTPException(
            status_code=404,
            detail=f"未知的 sheet_key：{sheet_key}，有效值：{list(SHEET_CONFIGS.keys())}"
        )


def _batch_to_out(b: SecurityPatrolBatch, item_count: int = 0) -> PatrolBatchOut:
    return PatrolBatchOut(
        ragic_id        = b.ragic_id,
        sheet_key       = b.sheet_key,
        sheet_id        = b.sheet_id,
        sheet_name      = b.sheet_name,
        inspection_date = b.inspection_date,
        inspector_name  = b.inspector_name,
        start_time      = b.start_time,
        end_time        = b.end_time,
        work_hours      = b.work_hours,
        item_count      = item_count,
        synced_at       = b.synced_at,
    )


def _item_to_out(it: SecurityPatrolItem) -> PatrolItemOut:
    return PatrolItemOut(
        ragic_id       = it.ragic_id,
        batch_ragic_id = it.batch_ragic_id,
        sheet_key      = it.sheet_key,
        seq_no         = it.seq_no,
        item_name      = it.item_name,
        result_raw     = it.result_raw,
        result_status  = it.result_status,
        abnormal_flag  = bool(it.abnormal_flag),
        is_note        = bool(it.is_note),
        synced_at      = it.synced_at,
    )


def _calc_kpi(items: list[SecurityPatrolItem]) -> PatrolBatchKPI:
    """計算 KPI，僅統計評分項目（is_note=False 的項目）"""
    score_items = [it for it in items if not it.is_note]
    total     = len(score_items)
    normal    = sum(1 for it in score_items if it.result_status == "normal")
    abnormal  = sum(1 for it in score_items if it.result_status == "abnormal")
    pending   = sum(1 for it in score_items if it.result_status == "pending")
    unchecked = sum(1 for it in score_items if it.result_status == "unchecked")
    checked   = normal + abnormal + pending

    return PatrolBatchKPI(
        total           = total,
        normal          = normal,
        abnormal        = abnormal,
        pending         = pending,
        unchecked       = unchecked,
        completion_rate = round(checked / total * 100, 1) if total > 0 else 0.0,
        normal_rate     = round(normal  / checked * 100, 1) if checked > 0 else 0.0,
    )


# ══════════════════════════════════════════════════════════════════════════════
# POST /sync
# ══════════════════════════════════════════════════════════════════════════════
@router.post("/sync", summary="從 Ragic 同步保全巡檢資料（背景執行）", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def sync_patrol(
    background_tasks: BackgroundTasks,
    sheet_key: Optional[str] = Query(None, description="指定 sheet_key 同步（空白 = 全部）"),
):
    """觸發背景同步：Ragic → SQLite，立即回傳，不阻塞畫面"""
    if sheet_key:
        _validate_sheet_key(sheet_key)
        background_tasks.add_task(sync_sheet, sheet_key)
    else:
        background_tasks.add_task(sync_all)
    return {"status": "ok", "message": "同步已在背景啟動"}


# ══════════════════════════════════════════════════════════════════════════════
# GET /sheets
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/sheets", summary="取得所有 Sheet 設定清單")
def list_sheets():
    return [
        SheetConfig(key=k, id=v["id"], name=v["name"], path=v["path"])
        for k, v in SHEET_CONFIGS.items()
    ]


# ══════════════════════════════════════════════════════════════════════════════
# GET /{sheet_key}/batches
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/{sheet_key}/batches", summary="取得巡檢場次清單")
def list_batches(
    sheet_key:  str,
    year_month: Optional[str] = Query(None, description="篩選年月，如 2026/04"),
    start_date: Optional[str] = Query(None, description="起始日期 YYYY/MM/DD"),
    end_date:   Optional[str] = Query(None, description="結束日期 YYYY/MM/DD"),
    db: Session = Depends(get_db),
):
    _validate_sheet_key(sheet_key)
    q = db.query(SecurityPatrolBatch).filter(
        SecurityPatrolBatch.sheet_key == sheet_key
    )
    if year_month:
        q = q.filter(SecurityPatrolBatch.inspection_date.like(f"{year_month}%"))
    if start_date:
        q = q.filter(SecurityPatrolBatch.inspection_date >= start_date)
    if end_date:
        q = q.filter(SecurityPatrolBatch.inspection_date <= end_date)

    batches = q.order_by(SecurityPatrolBatch.inspection_date.desc()).all()

    result = []
    for b in batches:
        items = db.query(SecurityPatrolItem).filter(
            SecurityPatrolItem.batch_ragic_id == b.ragic_id
        ).all()
        kpi = _calc_kpi(items)  # 內部已排除 is_note
        score_count = sum(1 for it in items if not it.is_note)
        result.append({
            "batch": _batch_to_out(b, score_count).model_dump(),
            "kpi":   kpi.model_dump(),
        })
    return result


# ══════════════════════════════════════════════════════════════════════════════
# GET /{sheet_key}/batches/{batch_id}
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/{sheet_key}/batches/{batch_id}", summary="取得單一場次完整資料")
def get_batch_detail(
    sheet_key:     str,
    batch_id:      str,
    result_status: Optional[str] = Query(None, alias="status"),
    search:        Optional[str] = Query(None, description="搜尋巡檢點名稱"),
    db: Session = Depends(get_db),
):
    _validate_sheet_key(sheet_key)
    batch = db.get(SecurityPatrolBatch, batch_id)
    if not batch or batch.sheet_key != sheet_key:
        raise HTTPException(status_code=404, detail=f"找不到場次：{batch_id}")

    items = db.query(SecurityPatrolItem).filter(
        SecurityPatrolItem.batch_ragic_id == batch_id
    ).order_by(SecurityPatrolItem.seq_no).all()

    kpi = _calc_kpi(items)  # 內部已排除 is_note
    score_count = sum(1 for it in items if not it.is_note)

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

    return PatrolBatchDetail(
        batch = _batch_to_out(batch, score_count),
        kpi   = kpi,
        items = filtered,
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /{sheet_key}/batches/{batch_id}/kpi
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/{sheet_key}/batches/{batch_id}/kpi", summary="取得場次 KPI 統計")
def get_batch_kpi(sheet_key: str, batch_id: str, db: Session = Depends(get_db)):
    _validate_sheet_key(sheet_key)
    batch = db.get(SecurityPatrolBatch, batch_id)
    if not batch or batch.sheet_key != sheet_key:
        raise HTTPException(status_code=404, detail=f"找不到場次：{batch_id}")
    items = db.query(SecurityPatrolItem).filter(
        SecurityPatrolItem.batch_ragic_id == batch_id
    ).all()
    return _calc_kpi(items)


# ══════════════════════════════════════════════════════════════════════════════
# GET /{sheet_key}/items
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/{sheet_key}/items", summary="跨場次查詢巡檢項目")
def list_items(
    sheet_key:     str,
    batch_id:      Optional[str] = Query(None),
    result_status: Optional[str] = Query(None, alias="status"),
    search:        Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    _validate_sheet_key(sheet_key)
    q = db.query(SecurityPatrolItem).filter(
        SecurityPatrolItem.sheet_key == sheet_key
    )
    if batch_id:
        q = q.filter(SecurityPatrolItem.batch_ragic_id == batch_id)

    items = q.order_by(
        SecurityPatrolItem.batch_ragic_id,
        SecurityPatrolItem.seq_no,
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
# GET /{sheet_key}/stats
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/{sheet_key}/stats", summary="全站統計（Dashboard 資料來源）",
            response_model=PatrolStats)
def get_stats(sheet_key: str, db: Session = Depends(get_db)):
    _validate_sheet_key(sheet_key)
    cfg       = SHEET_CONFIGS[sheet_key]
    today     = date.today()
    today_str = today.strftime("%Y/%m/%d")

    latest_batch = (
        db.query(SecurityPatrolBatch)
        .filter(SecurityPatrolBatch.sheet_key == sheet_key)
        .order_by(SecurityPatrolBatch.inspection_date.desc())
        .first()
    )

    latest_batch_out = None
    latest_kpi       = None
    recent_abnormal: list[PatrolItemOut] = []
    recent_pending:  list[PatrolItemOut] = []
    status_dist:     list[StatusDistItem] = []

    if latest_batch:
        items = db.query(SecurityPatrolItem).filter(
            SecurityPatrolItem.batch_ragic_id == latest_batch.ragic_id
        ).order_by(SecurityPatrolItem.seq_no).all()

        latest_batch_out = _batch_to_out(latest_batch, sum(1 for it in items if not it.is_note))
        latest_kpi       = _calc_kpi(items)  # 內部已排除 is_note

        # 狀態分布只計入評分項目（is_note=False）
        score_items   = [it for it in items if not it.is_note]
        status_counts = Counter(it.result_status for it in score_items)
        for s, cnt in status_counts.items():
            if cnt > 0:
                status_dist.append(StatusDistItem(
                    status = s,
                    label  = STATUS_LABELS.get(s, s),
                    count  = cnt,
                    color  = STATUS_COLORS.get(s, "#666666"),
                ))

        recent_abnormal = [
            _item_to_out(it) for it in score_items
            if it.result_status in ("abnormal", "pending")
        ][:10]

        recent_pending = [
            _item_to_out(it) for it in score_items
            if it.result_status == "pending"
        ][:10]

    # 近 7 日異常趨勢
    abnormal_trend: list[dict] = []
    for i in range(6, -1, -1):
        d     = today - timedelta(days=i)
        d_str = d.strftime("%Y/%m/%d")

        day_batches = db.query(SecurityPatrolBatch).filter(
            SecurityPatrolBatch.sheet_key      == sheet_key,
            SecurityPatrolBatch.inspection_date == d_str,
        ).all()

        abn_count = 0
        for b in day_batches:
            abn_count += db.query(SecurityPatrolItem).filter(
                SecurityPatrolItem.batch_ragic_id == b.ragic_id,
                SecurityPatrolItem.result_status.in_(["abnormal", "pending"]),
                SecurityPatrolItem.is_note == False,  # noqa: E712
            ).count()

        abnormal_trend.append({
            "date":           d_str,
            "abnormal_count": abn_count,
            "has_record":     len(day_batches) > 0,
        })

    week_ago         = (today - timedelta(days=7)).strftime("%Y/%m/%d")
    total_batches_7d = db.query(SecurityPatrolBatch).filter(
        SecurityPatrolBatch.sheet_key      == sheet_key,
        SecurityPatrolBatch.inspection_date >= week_ago,
    ).count()

    return PatrolStats(
        sheet_key           = sheet_key,
        sheet_name          = cfg["name"],
        latest_batch        = latest_batch_out,
        latest_kpi          = latest_kpi,
        recent_abnormal     = recent_abnormal,
        recent_pending      = recent_pending,
        status_distribution = status_dist,
        total_batches_7d    = total_batches_7d,
        abnormal_trend      = abnormal_trend,
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /{sheet_key}/items/item-history
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/{sheet_key}/items/item-history", summary="依巡檢點查詢近 N 日歷史")
def get_item_history(
    sheet_key: str,
    item_name: str = Query(..., description="巡檢點名稱"),
    days:      int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    _validate_sheet_key(sheet_key)
    today = date.today()

    rows = (
        db.query(SecurityPatrolItem, SecurityPatrolBatch)
        .join(
            SecurityPatrolBatch,
            SecurityPatrolItem.batch_ragic_id == SecurityPatrolBatch.ragic_id,
        )
        .filter(
            SecurityPatrolItem.sheet_key  == sheet_key,
            SecurityPatrolItem.item_name  == item_name,
        )
        .order_by(SecurityPatrolBatch.inspection_date.desc())
        .all()
    )

    if not rows:
        raise HTTPException(status_code=404, detail=f"找不到巡檢點記錄：{item_name}")

    date_map: dict[str, tuple] = {}
    for item, batch in rows:
        if batch.inspection_date not in date_map:
            date_map[batch.inspection_date] = (item, batch)

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
# GET /{sheet_key}/debug/ragic-raw
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/{sheet_key}/debug/ragic-raw", summary="[除錯] 顯示 Ragic 原始欄位")
async def debug_ragic_raw(sheet_key: str):
    _validate_sheet_key(sheet_key)
    cfg = SHEET_CONFIGS[sheet_key]

    adapter = RagicAdapter(
        sheet_path=cfg["path"],
        server_url=SP_SERVER_URL,
        account=SP_ACCOUNT,
    )
    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        return {"error": str(exc)}

    first_rec = next(iter(raw_data.values()), {}) if raw_data else {}
    return {
        "sheet_key":    sheet_key,
        "sheet_path":   cfg["path"],
        "total_records": len(raw_data),
        "all_fields":   list(first_rec.keys()),
        "first_record_sample": {k: repr(v)[:80] for k, v in first_rec.items()},
    }
