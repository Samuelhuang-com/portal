"""
每日數值登錄表 API Router
Prefix: /api/v1/hotel-meter-readings

端點：
  GET  /sheets                  — 取得所有 Sheet 設定（Ragic URL 等）
  POST /{sheet_key}/sync        — 從 Ragic 同步指定 Sheet（背景執行）
  POST /sync/all                — 從 Ragic 同步全部 4 張 Sheet（背景執行）
  GET  /{sheet_key}/batches     — 指定 Sheet 登錄清單（月份篩選）
  GET  /dashboard/summary       — 跨 Sheet 統計（Dashboard 總覽用）
"""
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.hotel_meter_readings import HotelMRBatch, HotelMRReading

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── Schema ────────────────────────────────────────────────────────────────────

class MeterSheetConfig(BaseModel):
    key:         str
    title:       str
    ragic_url:   str
    description: str


# ── Sheet 設定（對應 Ragic hotel-routine-inspection 各 Sheet）──────────────────

SHEET_CONFIGS: List[MeterSheetConfig] = [
    MeterSheetConfig(
        key="building-electric",
        title="全棟電錶",
        ragic_url="https://ap12.ragic.com/soutlet001/hotel-routine-inspection/11",
        description="全棟電力儀表每日數值登錄",
    ),
    MeterSheetConfig(
        key="mall-ac-electric",
        title="商場空調箱電錶",
        ragic_url="https://ap12.ragic.com/soutlet001/hotel-routine-inspection/12",
        description="商場空調箱電力儀表每日數值登錄",
    ),
    MeterSheetConfig(
        key="tenant-electric",
        title="專櫃電錶",
        ragic_url="https://ap12.ragic.com/soutlet001/hotel-routine-inspection/14",
        description="專櫃電力儀表每日數值登錄",
    ),
    MeterSheetConfig(
        key="tenant-water",
        title="專櫃水錶",
        ragic_url="https://ap12.ragic.com/soutlet001/hotel-routine-inspection/15",
        description="專櫃水量儀表每日數值登錄",
    ),
]

VALID_KEYS = {c.key for c in SHEET_CONFIGS}


# ── 業務邏輯輔助 ───────────────────────────────────────────────────────────────

def _count_readings(db: Session, batch_ragic_id: str) -> int:
    """計算一次登錄場次的讀數筆數"""
    return (
        db.query(HotelMRReading)
        .filter(HotelMRReading.batch_ragic_id == batch_ragic_id)
        .count()
    )


def _missing_days_this_month(
    db: Session,
    sheet_key: str,
    target_date: date,
) -> list[str]:
    """
    計算本月 1 日到 target_date（含），哪些日期沒有任何登錄紀錄。
    返回缺漏日期清單 ['YYYY/MM/DD', ...]
    使用 timedelta 逐日遞增，確保月底邊界正確。
    """
    first_day = target_date.replace(day=1)
    missing = []
    current = first_day
    while current <= target_date:
        d_str = current.strftime("%Y/%m/%d")
        exists = (
            db.query(HotelMRBatch)
            .filter(
                HotelMRBatch.sheet_key == sheet_key,
                HotelMRBatch.record_date == d_str,
            )
            .first()
        )
        if not exists:
            missing.append(d_str)
        current += timedelta(days=1)

    return missing


# ══════════════════════════════════════════════════════════════════════════════
# GET /sheets
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/sheets",
    summary="取得每日數值登錄表 Sheet 設定清單",
    response_model=List[MeterSheetConfig],
    tags=["每日數值登錄表"],
)
def get_sheets():
    """回傳全部 4 張 Sheet 設定，包含 Ragic URL。"""
    return SHEET_CONFIGS


# ══════════════════════════════════════════════════════════════════════════════
# POST /sync/all  ← 必須在 /{sheet_key}/sync 之前定義（路由優先順序）
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/sync/all",
    summary="從 Ragic 同步全部 4 張 Sheet（背景執行）",
    tags=["每日數值登錄表"],
)
async def sync_all_sheets(background_tasks: BackgroundTasks):
    """觸發背景同步：全部 4 張 Sheet，立即回傳，不阻塞畫面"""
    from app.services.hotel_meter_readings_sync import sync_all
    background_tasks.add_task(sync_all)
    return {"status": "ok", "message": "全部 4 張 Sheet 同步已在背景啟動"}


# ══════════════════════════════════════════════════════════════════════════════
# POST /{sheet_key}/sync
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{sheet_key}/sync",
    summary="從 Ragic 同步指定 Sheet（背景執行）",
    tags=["每日數值登錄表"],
)
async def sync_sheet(sheet_key: str, background_tasks: BackgroundTasks):
    """觸發背景同步：指定 sheet_key，立即回傳，不阻塞畫面"""
    if sheet_key not in VALID_KEYS:
        raise HTTPException(
            status_code=404,
            detail=f"未知的 sheet_key: {sheet_key}，有效值：{sorted(VALID_KEYS)}",
        )
    from app.services.hotel_meter_readings_sync import sync_sheet as _sync
    background_tasks.add_task(_sync, sheet_key)
    return {"status": "ok", "message": f"{sheet_key} 同步已在背景啟動"}


# ══════════════════════════════════════════════════════════════════════════════
# GET /{sheet_key}/batches
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{sheet_key}/batches",
    summary="取得指定 Sheet 登錄清單（月份篩選）",
    tags=["每日數值登錄表"],
)
def list_batches(
    sheet_key:  str,
    year_month: Optional[str] = Query(None, description="篩選年月，如 2026/04"),
    search:     Optional[str] = Query(None, description="關鍵字搜尋（登錄人員、日期）"),
    db: Session = Depends(get_db),
):
    if sheet_key not in VALID_KEYS:
        raise HTTPException(status_code=404, detail=f"未知的 sheet_key: {sheet_key}")

    q = db.query(HotelMRBatch).filter(HotelMRBatch.sheet_key == sheet_key)

    if year_month:
        q = q.filter(HotelMRBatch.record_date.like(f"{year_month}%"))

    if search:
        keyword = f"%{search}%"
        q = q.filter(
            HotelMRBatch.record_date.like(keyword)
            | HotelMRBatch.recorder_name.like(keyword)
        )

    batches = q.order_by(HotelMRBatch.record_date.desc()).all()

    result = []
    for b in batches:
        readings_count = _count_readings(db, b.ragic_id)
        # 找出各 Sheet 的 Ragic URL
        cfg = next((c for c in SHEET_CONFIGS if c.key == sheet_key), None)
        result.append({
            "id":             b.ragic_id,
            "record_date":    b.record_date,
            "recorder_name":  b.recorder_name,
            "readings_count": readings_count,
            "synced_at":      b.synced_at.strftime("%Y/%m/%d %H:%M") if b.synced_at else "",
            "ragic_url":      cfg.ragic_url if cfg else "",
        })

    return result


# ══════════════════════════════════════════════════════════════════════════════
# GET /dashboard/summary  — 跨 Sheet 統計（Dashboard 總覽用）
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/dashboard/summary",
    summary="取得每日數值登錄 Dashboard 統計（跨 Sheet）",
    tags=["每日數值登錄表"],
)
def get_dashboard_summary(
    target_date: Optional[str] = Query(
        None,
        description="查詢日期 YYYY/MM/DD，不填則取今日"
    ),
    db: Session = Depends(get_db),
):
    today = date.today()
    if not target_date:
        target_date = today.strftime("%Y/%m/%d")

    year_month = target_date[:7]  # e.g. "2026/04"

    # target_date 轉 date 物件（用於計算缺漏天數）
    try:
        td = date.fromisoformat(target_date.replace("/", "-"))
    except ValueError:
        td = today

    results = []
    for cfg in SHEET_CONFIGS:
        key = cfg.key

        # ── 今日是否已登錄 ─────────────────────────────────────────────────
        today_batch = (
            db.query(HotelMRBatch)
            .filter(
                HotelMRBatch.sheet_key == key,
                HotelMRBatch.record_date == target_date,
            )
            .first()
        )
        has_today = today_batch is not None

        # ── 本月登錄筆數 ────────────────────────────────────────────────────
        month_count = (
            db.query(HotelMRBatch)
            .filter(
                HotelMRBatch.sheet_key == key,
                HotelMRBatch.record_date.like(f"{year_month}%"),
            )
            .count()
        )

        # ── 最近登錄日期 ────────────────────────────────────────────────────
        latest = (
            db.query(HotelMRBatch)
            .filter(HotelMRBatch.sheet_key == key)
            .order_by(HotelMRBatch.record_date.desc())
            .first()
        )
        latest_record_date = latest.record_date if latest else ""

        # ── 本月讀數欄位總筆數 ──────────────────────────────────────────────
        month_batches = (
            db.query(HotelMRBatch)
            .filter(
                HotelMRBatch.sheet_key == key,
                HotelMRBatch.record_date.like(f"{year_month}%"),
            )
            .all()
        )
        total_readings = sum(
            _count_readings(db, b.ragic_id) for b in month_batches
        )

        # ── 缺漏日期（本月 1 日到 target_date）─────────────────────────────
        missing_days = _missing_days_this_month(db, key, td)

        # ── 近 7 天是否有登錄（趨勢）──────────────────────────────────────
        trend_7d = []
        for i in range(6, -1, -1):
            d     = today - timedelta(days=i)
            d_str = d.strftime("%Y/%m/%d")
            has   = (
                db.query(HotelMRBatch)
                .filter(
                    HotelMRBatch.sheet_key == key,
                    HotelMRBatch.record_date == d_str,
                )
                .first()
            ) is not None
            trend_7d.append({"date": d_str, "has_record": has})

        results.append({
            "key":                key,
            "title":              cfg.title,
            "ragic_url":          cfg.ragic_url,
            "has_today":          has_today,
            "month_count":        month_count,
            "latest_record_date": latest_record_date,
            "total_readings":     total_readings,
            "missing_days":       missing_days,
            "missing_count":      len(missing_days),
            "trend_7d":           trend_7d,
            "has_data":           month_count > 0,
        })

    return {
        "target_date": target_date,
        "year_month":  year_month,
        "sheets":      results,
    }
