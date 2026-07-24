"""
每日數值登錄表 API Router
Prefix: /api/v1/hotel-meter-readings

端點：
  GET  /sheets                  — 取得所有 Sheet 設定（Ragic URL 等）
  POST /{sheet_key}/sync        — 從 Ragic 同步指定 Sheet（背景執行）
  POST /sync/all                — 從 Ragic 同步全部 4 張 Sheet（背景執行）
  GET  /{sheet_key}/batches     — 指定 Sheet 登錄清單（月份篩選）
  GET  /dashboard/summary       — 跨 Sheet 統計（Dashboard 總覽用）
  GET  /daily-calendar          — 月曆格資料（MonthlyCalendarGrid 用）
"""
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.hotel_meter_readings import HotelMRBatch
from app.services.hotel_meter_readings_sync import HMR_SERVER_URL, HMR_ACCOUNT, SHEET_CONFIGS
from app.services.ragic_verify_utils import (
    read_portal_count_and_last_sync, read_portal_ragic_ids,
    fetch_ragic_count_multi, fetch_ragic_url_map_multi,
    build_verify_count_response, build_verify_diff_response,
)

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
        title="全棟水電錶",
        ragic_url="https://ap12.ragic.com/soutlet001/hotel-routine-inspection/11",
        description="全棟水電儀表每日數值登錄",
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

def _get_missing_days(
    db: Session,
    sheet_key: str,
    start_date: date,
    end_date: date,
) -> list[str]:
    """
    計算 start_date 到 end_date（含）之間，哪些日期沒有任何登錄紀錄。
    返回缺漏日期清單 ['YYYY/MM/DD', ...]
    使用 timedelta 逐日遞增，確保月底邊界正確。
    """
    missing = []
    current = start_date
    while current <= end_date:
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
# POST /sync/all  <- 必須在 /{sheet_key}/sync 之前定義（路由優先順序）
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


# ── /verify-count／/verify-diff ─────────────────────────────────────────────────
# 4 張 Sheet 都 pivot 進同一張 HotelMRBatch（sheet_key 區分），做法同飯店每日巡檢。

def _hmr_sheets() -> list[dict]:
    return [
        {"sheet_key": key, "sheet_path": cfg["path"], "server_url": HMR_SERVER_URL, "account": HMR_ACCOUNT}
        for key, cfg in SHEET_CONFIGS.items()
    ]


@router.get("/verify-count", summary="與 Ragic 數量比對（管理員，4 張 Sheet 加總）",
            dependencies=[Depends(require_roles("system_admin"))])
async def verify_count(db: Session = Depends(get_db)):
    portal_count, last_synced_at = await read_portal_count_and_last_sync(
        db, HotelMRBatch, "每日數值登錄"
    )
    try:
        ragic_count = await fetch_ragic_count_multi(_hmr_sheets())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ragic 連線失敗：{exc}")
    return build_verify_count_response("每日數值登錄", portal_count, ragic_count, last_synced_at)


@router.get("/verify-diff", summary="與 Ragic 明細差集比對（管理員，4 張 Sheet 加總）",
            dependencies=[Depends(require_roles("system_admin"))])
async def verify_diff(db: Session = Depends(get_db)):
    try:
        ragic_url_map = await fetch_ragic_url_map_multi(_hmr_sheets())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ragic 連線失敗：{exc}")
    portal_ids = await read_portal_ragic_ids(db, HotelMRBatch)
    return build_verify_diff_response(ragic_url_map, portal_ids)


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

    cfg = next((c for c in SHEET_CONFIGS if c.key == sheet_key), None)
    result = []
    for b in batches:
        result.append({
            "id":            b.ragic_id,
            "record_date":   b.record_date,
            "recorder_name": b.recorder_name,
            "start_time":    getattr(b, "start_time", ""),
            "end_time":      getattr(b, "end_time", ""),
            "work_hours":    getattr(b, "work_hours", ""),
            "synced_at":     b.synced_at.strftime("%Y/%m/%d %H:%M") if b.synced_at else "",
            "ragic_url":     cfg.ragic_url if cfg else "",
        })

    return result


# ══════════════════════════════════════════════════════════════════════════════
# GET /dashboard/summary  — 跨 Sheet 月份統計（Dashboard 總覽用）
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/dashboard/summary",
    summary="取得每日數值登錄 Dashboard 統計（跨 Sheet）",
    tags=["每日數值登錄表"],
)
def get_dashboard_summary(
    month: Optional[str] = Query(
        None,
        description="查詢月份 YYYY-MM（如 2026-05），不填則取當月"
    ),
    target_date: Optional[str] = Query(
        None,
        description="[已棄用] 查詢日期 YYYY/MM/DD，請改用 month 參數"
    ),
    db: Session = Depends(get_db),
):
    """
    跨 Sheet 月份統計。
    優先使用 month 參數（YYYY-MM）；若僅提供舊版 target_date，自動轉換為對應月份。
    """
    from app.core.date_utils import get_month_range, to_ragic_year_month

    today = date.today()

    # ── 決定查詢月份 ─────────────────────────────────────────────────────────
    if month:
        query_month = month  # e.g. "2026-05"
    elif target_date:
        # 舊版向後相容：從 target_date 取月份
        query_month = target_date[:7].replace("/", "-")  # "2026/04" -> "2026-04"
    else:
        query_month = today.strftime("%Y-%m")

    start_date, end_date = get_month_range(query_month)
    year_month  = to_ragic_year_month(query_month)          # "2026/05"
    is_current  = (start_date.year == today.year and start_date.month == today.month)

    # 缺漏天數計算上界：當月用今日，過去月用月末
    missing_end = today if is_current else end_date

    # 趨勢參考日：當月用今日，過去月用月末
    trend_ref   = today if is_current else end_date

    # 「今日 / 末日」登錄判斷基準
    ref_date_str = today.strftime("%Y/%m/%d") if is_current else end_date.strftime("%Y/%m/%d")

    results = []
    for cfg in SHEET_CONFIGS:
        key = cfg.key

        # ── 今日（或末日）是否已登錄 ──────────────────────────────────────
        has_today = (
            db.query(HotelMRBatch)
            .filter(
                HotelMRBatch.sheet_key == key,
                HotelMRBatch.record_date == ref_date_str,
            )
            .first()
        ) is not None

        # ── 查詢月份登錄筆數 ───────────────────────────────────────────────
        month_count = (
            db.query(HotelMRBatch)
            .filter(
                HotelMRBatch.sheet_key == key,
                HotelMRBatch.record_date.like(f"{year_month}%"),
            )
            .count()
        )

        # ── 查詢月份內最近登錄日期 ─────────────────────────────────────────
        latest = (
            db.query(HotelMRBatch)
            .filter(
                HotelMRBatch.sheet_key == key,
                HotelMRBatch.record_date.like(f"{year_month}%"),
            )
            .order_by(HotelMRBatch.record_date.desc())
            .first()
        )
        latest_record_date = latest.record_date if latest else ""

        # ── 缺漏日期（月初到 missing_end）────────────────────────────────
        missing_days = _get_missing_days(db, key, start_date, missing_end)

        # ── 近 7 天是否有登錄（依 trend_ref 往前 7 天）───────────────────
        trend_7d = []
        for i in range(6, -1, -1):
            d     = trend_ref - timedelta(days=i)
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
            "is_current_month":   is_current,
            "month_count":        month_count,
            "latest_record_date": latest_record_date,
            "missing_days":       missing_days,
            "missing_count":      len(missing_days),
            "trend_7d":           trend_7d,
            "has_data":           month_count > 0,
        })

    return {
        "month":       query_month,
        "target_date": ref_date_str,    # 向後相容
        "year_month":  year_month,
        "sheets":      results,
    }


# ══════════════════════════════════════════════════════════════════════════════
# GET /daily-calendar  — 月曆格資料（MonthlyCalendarGrid 用）
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/daily-calendar",
    summary="取得每日數值登錄月曆格資料（所有 Sheet）",
    tags=["每日數值登錄表"],
)
def get_daily_calendar(
    year:  int = Query(..., description="年份，如 2026"),
    month: int = Query(..., description="月份 1-12，如 5"),
    db: Session = Depends(get_db),
):
    """
    回傳用於 MonthlyCalendarGrid 的月曆格資料。
    rows = 4 張 Sheet；cols = 當月各日（1-31）。
    每格只有兩個狀態：has_record=true（✓）/ has_record=false（—）。
    """
    import calendar

    max_day = calendar.monthrange(year, month)[1]

    rows = []
    for cfg in SHEET_CONFIGS:
        key   = cfg.key
        title = cfg.title
        year_month_str = f"{year}/{month:02d}"

        # 一次查出本月所有登錄，以 record_date 為 key
        batches = (
            db.query(HotelMRBatch.record_date)
            .filter(
                HotelMRBatch.sheet_key == key,
                HotelMRBatch.record_date.like(f"{year_month_str}%"),
            )
            .all()
        )
        recorded_days: set[int] = set()
        for (record_date,) in batches:
            # record_date 格式 "YYYY/MM/DD"
            try:
                day = int(record_date.split("/")[2])
                recorded_days.add(day)
            except (IndexError, ValueError):
                pass

        daily: dict[str, dict] = {}
        for d in range(1, max_day + 1):
            has = d in recorded_days
            daily[str(d)] = {
                "has_record":       has,
                "completion_rate":  1.0 if has else 0.0,
                "abnormal_count":   0,
                "pending_count":    0,
            }

        rows.append({"key": key, "label": title, "daily": daily})

    return {
        "year":    year,
        "month":   month,
        "max_day": max_day,
        "rows":    rows,
    }
