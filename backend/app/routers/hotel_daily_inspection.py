"""
飯店每日巡檢 API Router
Prefix: /api/v1/hotel-daily-inspection

端點：
  GET  /sheets                  — 取得所有區域巡檢 Sheet 設定（Ragic URL 等）
  POST /{sheet_key}/sync        — 從 Ragic 同步指定區域（背景執行）
  POST /sync/all                — 從 Ragic 同步全部 5 張 Sheet（背景執行）
  GET  /{sheet_key}/stats       — 指定區域統計（Dashboard 用）
  GET  /{sheet_key}/batches     — 指定區域場次清單（月份篩選）
  GET  /dashboard/summary       — 跨 Sheet 統計（Dashboard 總覽用）
  GET  /daily-form              — 每日巡檢表彙整（year + month 篩選）
"""
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.hotel_daily_inspection import HotelDIBatch, HotelDIItem

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── Schema ────────────────────────────────────────────────────────────────────

class InspectionSheetConfig(BaseModel):
    key:         str
    floor:       str
    title:       str
    ragic_url:   str
    description: str


# ── Sheet 設定（對應 Ragic main-project-inspection 各 Sheet）──────────────────

SHEET_CONFIGS: List[InspectionSheetConfig] = [
    InspectionSheetConfig(
        key="rf",
        floor="RF",
        title="飯店每日巡檢 - RF",
        ragic_url="https://ap12.ragic.com/soutlet001/main-project-inspection/17",
        description="飯店屋頂層設施每日例行巡檢",
    ),
    InspectionSheetConfig(
        key="4f-10f",
        floor="4F ~ 10F",
        title="飯店每日巡檢 - 4F-10F",
        ragic_url="https://ap12.ragic.com/soutlet001/main-project-inspection/18",
        description="飯店 4 樓至 10 樓設施每日例行巡檢",
    ),
    InspectionSheetConfig(
        key="4f",
        floor="4F",
        title="飯店每日巡檢 - 4F",
        ragic_url="https://ap12.ragic.com/soutlet001/main-project-inspection/19?PAGEID=BAG",
        description="飯店 4 樓設施每日例行巡檢",
    ),
    InspectionSheetConfig(
        key="2f",
        floor="2F",
        title="飯店每日巡檢 - 2F",
        ragic_url="https://ap12.ragic.com/soutlet001/main-project-inspection/20",
        description="飯店 2 樓設施每日例行巡檢",
    ),
    InspectionSheetConfig(
        key="1f",
        floor="1F",
        title="飯店每日巡檢 - 1F",
        ragic_url="https://ap12.ragic.com/soutlet001/main-project-inspection/21",
        description="飯店 1 樓設施每日例行巡檢",
    ),
]

VALID_KEYS = {c.key for c in SHEET_CONFIGS}


# ── 業務邏輯輔助 ───────────────────────────────────────────────────────────────

def _calc_kpi(items: list[HotelDIItem]) -> dict:
    """計算一組巡檢項目的 KPI 統計（排除 is_note 項目）"""
    scored = [it for it in items if not it.is_note]
    total     = len(scored)
    normal    = sum(1 for it in scored if it.result_status == "normal")
    abnormal  = sum(1 for it in scored if it.result_status == "abnormal")
    pending   = sum(1 for it in scored if it.result_status == "pending")
    unchecked = sum(1 for it in scored if it.result_status == "unchecked")
    checked   = normal + abnormal + pending

    completion_rate = round(checked / total * 100, 1) if total > 0 else 0.0
    return {
        "total":           total,
        "normal":          normal,
        "abnormal":        abnormal,
        "pending":         pending,
        "unchecked":       unchecked,
        "checked":         checked,
        "completion_rate": completion_rate,
    }


def _parse_minutes(start: str, end: str) -> int:
    """解析 HH:MM 格式的開始/結束時間，回傳分鐘數差值；格式無效時回傳 0。"""
    import re
    def to_min(t: str):
        m = re.match(r'^(\d{1,2}):(\d{2})$', t.strip())
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))
        return None
    s, e = to_min(start), to_min(end)
    if s is None or e is None:
        return 0
    diff = e - s
    return diff + 24 * 60 if diff < 0 else diff


# ══════════════════════════════════════════════════════════════════════════════
# GET /sheets
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/sheets",
    summary="取得飯店巡檢 Sheet 設定清單",
    response_model=List[InspectionSheetConfig],
    tags=["飯店每日巡檢"],
)
def get_sheets():
    """回傳飯店每日巡檢各區域 Sheet 設定，包含 Ragic URL。"""
    return SHEET_CONFIGS


# ══════════════════════════════════════════════════════════════════════════════
# POST /sync/all  ← 必須在 /{sheet_key}/sync 之前定義
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/sync/all",
    summary="從 Ragic 同步全部 5 張 Sheet（背景執行）",
    tags=["飯店每日巡檢"],
)
async def sync_all_sheets(background_tasks: BackgroundTasks):
    """觸發背景同步：全部 5 張 Sheet，立即回傳，不阻塞畫面"""
    from app.services.hotel_daily_inspection_sync import sync_all
    background_tasks.add_task(sync_all)
    return {"status": "ok", "message": "全部 5 張 Sheet 同步已在背景啟動"}


# ══════════════════════════════════════════════════════════════════════════════
# POST /{sheet_key}/sync
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{sheet_key}/sync",
    summary="從 Ragic 同步指定區域（背景執行）",
    tags=["飯店每日巡檢"],
)
async def sync_sheet(sheet_key: str, background_tasks: BackgroundTasks):
    """觸發背景同步：指定 sheet_key，立即回傳，不阻塞畫面"""
    if sheet_key not in VALID_KEYS:
        raise HTTPException(
            status_code=404,
            detail=f"未知的 sheet_key: {sheet_key}，有效值：{sorted(VALID_KEYS)}",
        )
    from app.services.hotel_daily_inspection_sync import sync_sheet as _sync
    background_tasks.add_task(_sync, sheet_key)
    return {"status": "ok", "message": f"{sheet_key} 同步已在背景啟動"}


# ══════════════════════════════════════════════════════════════════════════════
# GET /{sheet_key}/stats
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{sheet_key}/stats",
    summary="取得指定區域 Dashboard 統計",
    tags=["飯店每日巡檢"],
)
def get_sheet_stats(
    sheet_key: str,
    target_date: Optional[str] = Query(
        None,
        description="查詢日期 YYYY/MM/DD，不填則取最新場次"
    ),
    db: Session = Depends(get_db),
):
    if sheet_key not in VALID_KEYS:
        raise HTTPException(status_code=404, detail=f"未知的 sheet_key: {sheet_key}")

    today = date.today()

    # ── 取最新（或指定日期）場次 ─────────────────────────────────────────────
    q = db.query(HotelDIBatch).filter(HotelDIBatch.sheet_key == sheet_key)
    if target_date:
        q = q.filter(HotelDIBatch.inspection_date == target_date)

    latest_batch = q.order_by(HotelDIBatch.inspection_date.desc()).first()

    latest_kpi        = None
    latest_batch_info = None
    recent_abnormal: list[dict] = []

    if latest_batch:
        items = (
            db.query(HotelDIItem)
            .filter(HotelDIItem.batch_ragic_id == latest_batch.ragic_id)
            .order_by(HotelDIItem.seq_no)
            .all()
        )
        latest_kpi = _calc_kpi(items)
        latest_batch_info = {
            "ragic_id":       latest_batch.ragic_id,
            "inspection_date": latest_batch.inspection_date,
            "inspector_name": latest_batch.inspector_name,
            "start_time":     latest_batch.start_time,
            "end_time":       latest_batch.end_time,
            "work_hours":     latest_batch.work_hours,
        }
        recent_abnormal = [
            {
                "item_name":     it.item_name,
                "result_raw":    it.result_raw,
                "result_status": it.result_status,
            }
            for it in items
            if it.result_status in ("abnormal", "pending") and not it.is_note
        ][:20]

    # ── 近 7 日場次數 ─────────────────────────────────────────────────────────
    week_ago = (today - timedelta(days=7)).strftime("%Y/%m/%d")
    batches_7d = (
        db.query(HotelDIBatch)
        .filter(
            HotelDIBatch.sheet_key == sheet_key,
            HotelDIBatch.inspection_date >= week_ago,
        )
        .count()
    )

    # ── 近 7 日異常趨勢 ───────────────────────────────────────────────────────
    abnormal_trend = []
    for i in range(6, -1, -1):
        d     = today - timedelta(days=i)
        d_str = d.strftime("%Y/%m/%d")

        day_batches = (
            db.query(HotelDIBatch)
            .filter(
                HotelDIBatch.sheet_key == sheet_key,
                HotelDIBatch.inspection_date == d_str,
            )
            .all()
        )

        abn_count = 0
        for b in day_batches:
            abn_count += (
                db.query(HotelDIItem)
                .filter(
                    HotelDIItem.batch_ragic_id == b.ragic_id,
                    HotelDIItem.result_status.in_(["abnormal", "pending"]),
                    HotelDIItem.is_note == False,
                )
                .count()
            )

        abnormal_trend.append({
            "date":           d_str,
            "abnormal_count": abn_count,
            "has_record":     len(day_batches) > 0,
        })

    return {
        "sheet_key":        sheet_key,
        "latest_batch":     latest_batch_info,
        "latest_kpi":       latest_kpi,
        "recent_abnormal":  recent_abnormal,
        "total_batches_7d": batches_7d,
        "abnormal_trend":   abnormal_trend,
    }


# ══════════════════════════════════════════════════════════════════════════════
# GET /{sheet_key}/batches
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{sheet_key}/batches",
    summary="取得指定區域巡檢場次清單",
    tags=["飯店每日巡檢"],
)
def list_batches(
    sheet_key:  str,
    year_month: Optional[str] = Query(None, description="篩選年月，如 2026/04"),
    db: Session = Depends(get_db),
):
    if sheet_key not in VALID_KEYS:
        raise HTTPException(status_code=404, detail=f"未知的 sheet_key: {sheet_key}")

    q = db.query(HotelDIBatch).filter(HotelDIBatch.sheet_key == sheet_key)
    if year_month:
        q = q.filter(HotelDIBatch.inspection_date.like(f"{year_month}%"))

    batches = q.order_by(HotelDIBatch.inspection_date.desc()).all()

    result = []
    for b in batches:
        items = (
            db.query(HotelDIItem)
            .filter(HotelDIItem.batch_ragic_id == b.ragic_id)
            .all()
        )
        kpi = _calc_kpi(items)
        result.append({
            "id":              b.ragic_id,
            "inspection_date": b.inspection_date,
            "inspector_name":  b.inspector_name,
            "start_time":      b.start_time,
            "end_time":        b.end_time,
            "total":           kpi["total"],
            "checked":         kpi["checked"],
            "abnormal":        kpi["abnormal"],
            "pending":         kpi["pending"],
            "completion_rate": kpi["completion_rate"],
        })
    return result


# ══════════════════════════════════════════════════════════════════════════════
# GET /dashboard/summary  — 跨 Sheet 統計（index.tsx Dashboard 用）
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/dashboard/summary",
    summary="取得全體飯店每日巡檢 Dashboard 統計（跨 Sheet）",
    tags=["飯店每日巡檢"],
)
def get_dashboard_summary(
    target_date: Optional[str] = Query(
        None,
        description="查詢日期 YYYY/MM/DD，不填則取今日"
    ),
    db: Session = Depends(get_db),
):
    if not target_date:
        target_date = date.today().strftime("%Y/%m/%d")

    results = []
    for cfg in SHEET_CONFIGS:
        key = cfg.key

        # 指定日期的所有場次
        day_batches = (
            db.query(HotelDIBatch)
            .filter(
                HotelDIBatch.sheet_key == key,
                HotelDIBatch.inspection_date == target_date,
            )
            .all()
        )

        total_batches   = len(day_batches)
        total_items     = 0
        checked_items   = 0
        abnormal_items  = 0
        pending_items   = 0
        unchecked_items = 0
        total_minutes   = 0

        for b in day_batches:
            items = (
                db.query(HotelDIItem)
                .filter(
                    HotelDIItem.batch_ragic_id == b.ragic_id,
                    HotelDIItem.is_note == False,
                )
                .all()
            )
            kpi = _calc_kpi(items)
            total_items     += kpi["total"]
            checked_items   += kpi["checked"]
            abnormal_items  += kpi["abnormal"]
            pending_items   += kpi["pending"]
            unchecked_items += kpi["unchecked"]
            total_minutes   += _parse_minutes(b.start_time or "", b.end_time or "")

        completion_rate = (
            round(checked_items / total_items * 100, 1) if total_items > 0 else 0.0
        )

        results.append({
            "key":             key,
            "floor":           cfg.floor,
            "title":           cfg.title,
            "total_batches":   total_batches,
            "total_items":     total_items,
            "checked_items":   checked_items,
            "abnormal_items":  abnormal_items,
            "pending_items":   pending_items,
            "unchecked_items": unchecked_items,
            "completion_rate": completion_rate,
            "has_data":        total_batches > 0,
            "total_minutes":   total_minutes,
        })

    return {"target_date": target_date, "sheets": results}


# ── GET /dashboard/monthly-summary — 月份彙總（供 hotel/overview Dashboard 使用）──
@router.get(
    "/dashboard/monthly-summary",
    summary="飯店每日巡檢月份彙總統計（跨 Sheet，供飯店管理 Dashboard 使用）",
    tags=["飯店每日巡檢"],
)
def get_dashboard_monthly_summary(
    year:  int = Query(..., ge=2020, le=2030, description="年份"),
    month: int = Query(..., ge=1,    le=12,   description="月份（1–12）"),
    db: Session = Depends(get_db),
):
    """
    彙整指定年月內所有飯店每日巡檢的月份統計（跨所有 Sheet），
    供飯店管理 Dashboard KPI Card「飯店每日巡檢」顯示月份口徑資料。

    回傳：
      year_month      — 查詢年月（如 "2026/04"）
      total_items     — 月內所有巡檢項目總數
      checked_items   — 已確認項目數
      abnormal_items  — 異常項目數
      total_minutes   — 月內總巡檢時間（分鐘）
      completion_rate — 完成率（%）
      sheets          — 各 Sheet 的月份彙總明細
    """
    year_month_prefix = f"{year}/{month:02d}/"

    results = []
    for cfg in SHEET_CONFIGS:
        key = cfg.key

        # 指定月份的所有批次
        month_batches = (
            db.query(HotelDIBatch)
            .filter(
                HotelDIBatch.sheet_key == key,
                HotelDIBatch.inspection_date.like(f"{year_month_prefix}%"),
            )
            .all()
        )

        total_batches   = len(month_batches)
        total_items     = 0
        checked_items   = 0
        abnormal_items  = 0
        pending_items   = 0
        unchecked_items = 0
        total_minutes   = 0

        for b in month_batches:
            items = (
                db.query(HotelDIItem)
                .filter(
                    HotelDIItem.batch_ragic_id == b.ragic_id,
                    HotelDIItem.is_note == False,
                )
                .all()
            )
            kpi = _calc_kpi(items)
            total_items     += kpi["total"]
            checked_items   += kpi["checked"]
            abnormal_items  += kpi["abnormal"]
            pending_items   += kpi["pending"]
            unchecked_items += kpi["unchecked"]
            total_minutes   += _parse_minutes(b.start_time or "", b.end_time or "")

        completion_rate = (
            round(checked_items / total_items * 100, 1) if total_items > 0 else 0.0
        )

        results.append({
            "key":             key,
            "floor":           cfg.floor,
            "title":           cfg.title,
            "total_batches":   total_batches,
            "total_items":     total_items,
            "checked_items":   checked_items,
            "abnormal_items":  abnormal_items,
            "pending_items":   pending_items,
            "unchecked_items": unchecked_items,
            "completion_rate": completion_rate,
            "has_data":        total_batches > 0,
            "total_minutes":   total_minutes,
        })

    total_items_all    = sum(s["total_items"]    for s in results)
    checked_items_all  = sum(s["checked_items"]  for s in results)
    abnormal_items_all = sum(s["abnormal_items"] for s in results)
    total_minutes_all  = sum(s["total_minutes"]  for s in results)
    overall_rate = (
        round(checked_items_all / total_items_all * 100, 1) if total_items_all > 0 else 0.0
    )

    return {
        "year":            year,
        "month":           month,
        "year_month":      f"{year}/{month:02d}",
        "total_items":     total_items_all,
        "checked_items":   checked_items_all,
        "abnormal_items":  abnormal_items_all,
        "total_minutes":   total_minutes_all,
        "completion_rate": overall_rate,
        "sheets":          results,
    }


# ══════════════════════════════════════════════════════════════════════════════
# GET /daily-form  — 每日巡檢表彙整（year + month 篩選）
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/daily-form",
    summary="取得每日巡檢表彙整（依標準模板與各 Sheet 比對）",
    tags=["飯店每日巡檢"],
)
def get_daily_form(
    year:            int           = Query(...,  ge=2020, le=2030, description="年份"),
    month:           int           = Query(...,  ge=1,    le=12,   description="月份（1–12）"),
    inspection_date: Optional[str] = Query(None, description="指定日期 YYYY/MM/DD；不填則取整月彙整"),
    db: Session = Depends(get_db),
):
    """
    依標準模板（hoteldaily-inspection.xlsx）與各 Sheet 實際巡檢資料比對。

    inspection_date 不填 → 整月所有 batch 彙整。
    inspection_date 填入 → 只取該日 batch；無資料時所有列 matched=False。
    回傳額外欄位 has_data_today（bool）供前端顯示「無YYYY/MM/DD資料」提示。
    """
    from app.services.daily_inspection_builder import build_daily_inspection_table
    rows = build_daily_inspection_table(
        year=year, month=month, db=db,
        inspection_date=inspection_date,
    )
    has_data_today = any(r["matched"] for r in rows) if inspection_date else None
    return {
        "year":           year,
        "month":          month,
        "inspection_date": inspection_date,
        "has_data_today": has_data_today,
        "rows":           rows,
    }


# =============================================================================
# GET /daily-calendar
# =============================================================================

@router.get(
    "/daily-calendar",
    summary="取得指定月份每日巡檢狀況（各 Sheet × 各日，Dashboard 月曆格用）",
    tags=["飯店每日巡檢"],
)
def get_daily_calendar(
    year:  int = Query(..., ge=2020, le=2030, description="年份"),
    month: int = Query(..., ge=1,    le=12,   description="月份（1–12）"),
    db: Session = Depends(get_db),
):
    """
    回傳當月每日 × 每個 Sheet 的巡檢狀態，供 Dashboard 月曆格使用。
    回傳：
      max_day  — 當月天數
      sheets[] — 各 Sheet，含 daily{day_str: {has_record, completion_rate, abnormal_count}}
    """
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    year_month_prefix = f"{year}/{month:02d}/"

    sheets_out = []
    for cfg in SHEET_CONFIGS:
        key = cfg.key

        month_batches = (
            db.query(HotelDIBatch)
            .filter(
                HotelDIBatch.sheet_key == key,
                HotelDIBatch.inspection_date.like(f"{year_month_prefix}%"),
            )
            .all()
        )

        by_date = {}
        for b in month_batches:
            try:
                day = int(b.inspection_date.split("/")[2])
            except (IndexError, ValueError):
                continue
            by_date.setdefault(day, []).append(b)

        daily = {}
        for day in range(1, max_day + 1):
            day_batches = by_date.get(day, [])
            if not day_batches:
                daily[str(day)] = {"has_record": False, "completion_rate": 0.0,
                                   "abnormal_count": 0, "pending_count": 0}
                continue

            total_items    = 0
            checked_items  = 0
            abnormal_count = 0
            pending_count  = 0

            for b in day_batches:
                items = (
                    db.query(HotelDIItem)
                    .filter(
                        HotelDIItem.batch_ragic_id == b.ragic_id,
                        HotelDIItem.is_note == False,
                    )
                    .all()
                )
                kpi = _calc_kpi(items)
                total_items    += kpi["total"]
                checked_items  += kpi["checked"]
                abnormal_count += kpi["abnormal"]
                pending_count  += kpi["pending"]

            rate = round(checked_items / total_items * 100, 1) if total_items > 0 else 0.0
            daily[str(day)] = {
                "has_record":      True,
                "completion_rate": rate,
                "abnormal_count":  abnormal_count,
                "pending_count":   pending_count,
            }

        sheets_out.append({
            "key":   key,
            "floor": cfg.floor,
            "title": cfg.title,
            "daily": daily,
        })

    return {
        "year":    year,
        "month":   month,
        "max_day": max_day,
        "sheets":  sheets_out,
    }
