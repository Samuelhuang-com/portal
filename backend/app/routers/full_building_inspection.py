"""
整棟巡檢 API Router
Prefix: /api/v1/full-building-inspection

本模組是「跨樓層聚合層」：各樓層（RF / B4F / B2F / B1F）各自有獨立的
Ragic Sheet、sync service 與 router，本模組不另做同步，只把四張
*_inspection_batch / *_inspection_item 表彙總成 Dashboard 需要的視圖。

端點：
  GET /sheets                    — 取得所有樓層巡檢 Sheet 設定（Ragic URL 等）
  GET /dashboard/monthly-summary — Dashboard 月份統計（跨樓層）
  GET /dashboard/calendar        — 月曆格（樓層 × 日）
  GET /daily-form                — 每日巡檢表（模板結構；欄位對應尚未接線）
"""
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.rf_inspection  import RFInspectionBatch,  RFInspectionItem
from app.models.b4f_inspection import B4FInspectionBatch, B4FInspectionItem
from app.models.b2f_inspection import B2FInspectionBatch, B2FInspectionItem
from app.models.b1f_inspection import B1FInspectionBatch, B1FInspectionItem

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── 樓層 key → ORM 模型對照 ──────────────────────────────────────────────────
# 四個樓層的表結構完全相同（batch / item 寬表格 Pivot），只差表名，
# 故用對照表統一處理，新增樓層時只需在此與 SHEET_CONFIGS 各加一列。
MODEL_MAP = {
    "rf":  (RFInspectionBatch,  RFInspectionItem),
    "b4f": (B4FInspectionBatch, B4FInspectionItem),
    "b2f": (B2FInspectionBatch, B2FInspectionItem),
    "b1f": (B1FInspectionBatch, B1FInspectionItem),
}


def _calc_item_kpi(items) -> dict:
    """由 item 清單算出 total / checked / abnormal / pending。

    ⚠️ 一律先過濾成「真正的設備項目」再算 —— 動態欄位偵測會把「拍照」
       「異常說明」「建立日期」「建立年份」「月份」也收成 item，而
       _normalize_result_status() 對不認得的值一律判 abnormal，
       檔名與日期會被算成異常（2026-08-24 修）。
       規則與四支樓層 router、前端 FloorInspectionList.tsx 共用同一份。
    """
    from app.services.inspection_field_rules import is_equipment_field
    items    = [i for i in items if is_equipment_field(i.item_name, i.result_raw)]
    total    = len(items)
    checked  = sum(1 for i in items if i.result_status != "unchecked")
    abnormal = sum(1 for i in items if i.result_status == "abnormal")
    pending  = sum(1 for i in items if i.result_status == "pending")
    return {
        "total":    total,
        "checked":  checked,
        "abnormal": abnormal,
        "pending":  pending,
    }


# ── Schema ────────────────────────────────────────────────────────────────────

class InspectionSheetConfig(BaseModel):
    key:         str
    floor:       str
    title:       str
    ragic_url:   str
    description: str


# ── Sheet 設定（對應 Ragic full-building-inspection 各 Sheet）─────────────────

SHEET_CONFIGS: List[InspectionSheetConfig] = [
    InspectionSheetConfig(
        key="rf",
        floor="RF",
        title="整棟工務每日巡檢 - RF",
        ragic_url="https://ap12.ragic.com/soutlet001/full-building-inspection/1?PAGEID=i4T",
        description="整棟工務 RF 層（屋頂層）設施每日例行巡檢",
    ),
    InspectionSheetConfig(
        key="b4f",
        floor="B4F",
        title="整棟工務每日巡檢 - B4F",
        ragic_url="https://ap12.ragic.com/soutlet001/full-building-inspection/2?PAGEID=i4T",
        description="整棟工務 B4F 地下 4 樓設施每日例行巡檢",
    ),
    InspectionSheetConfig(
        key="b2f",
        floor="B2F",
        title="整棟工務每日巡檢 - B2F",
        ragic_url="https://ap12.ragic.com/soutlet001/full-building-inspection/3?PAGEID=i4T",
        description="整棟工務 B2F 地下 2 樓設施每日例行巡檢",
    ),
    InspectionSheetConfig(
        key="b1f",
        floor="B1F",
        title="整棟工務每日巡檢 - B1F",
        ragic_url="https://ap12.ragic.com/soutlet001/full-building-inspection/4?PAGEID=i4T",
        description="整棟工務 B1F 地下 1 樓設施每日例行巡檢",
    ),
]


# ── 端點 ──────────────────────────────────────────────────────────────────────

@router.get(
    "/sheets",
    summary="取得整棟巡檢 Sheet 設定清單",
    response_model=List[InspectionSheetConfig],
    tags=["整棟巡檢"],
)
def get_sheets():
    """
    回傳整棟巡檢各樓層 Sheet 設定，
    包含 Ragic URL 供前端導頁或顯示摘要使用。
    """
    return SHEET_CONFIGS


# ══════════════════════════════════════════════════════════════════════════════
# GET /dashboard/monthly-summary  — Dashboard 月份統計
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/dashboard/monthly-summary",
    summary="取得整棟巡檢 Dashboard 月份統計（跨 Sheet）",
    tags=["整棟巡檢"],
)
def get_dashboard_monthly_summary(
    month: Optional[str] = Query(
        None,
        description="查詢月份 YYYY-MM（如 2026-05），不填則取當月"
    ),
    db: Session = Depends(get_db),
):
    """
    依查詢月份回傳各樓層 Sheet 的月份 KPI：
      - month_count       本月登錄場次數（batch 筆數，同一天多場次分開計）
      - missing_count     缺漏天數
      - missing_days      缺漏日期清單（整月每天都視為應巡檢，不排除週末／假日）
      - latest_batch_date 查詢月份內最近登錄日期
      - has_today         今日（非當月則為該月末日）是否已登錄
      - trend_7d          近 7 天是否有登錄

    註：查詢當月時，缺漏只計算到「今天」為止，不把未來日期算成缺漏
        （與商場工務巡檢 /mall-facility-inspection 的口徑一致）。
    """
    from app.core.date_utils import get_month_range, to_ragic_year_month

    today = date.today()
    if not month:
        month = today.strftime("%Y-%m")

    start_date, end_date = get_month_range(month)
    year_month = to_ragic_year_month(month)                 # "2026/08"
    is_current = (start_date.year == today.year and start_date.month == today.month)
    missing_end  = today if is_current else end_date
    trend_ref    = today if is_current else end_date
    ref_date_str = trend_ref.strftime("%Y/%m/%d")

    results = []
    for cfg in SHEET_CONFIGS:
        BatchModel, _ItemModel = MODEL_MAP[cfg.key]

        # ── 查詢月份所有場次 ───────────────────────────────────────────────
        month_batches = (
            db.query(BatchModel)
            .filter(BatchModel.inspection_date.like(f"{year_month}%"))
            .all()
        )
        month_count = len(month_batches)

        # ── 已登錄日期集合 / 月內最近登錄日 ────────────────────────────────
        inspected_days = {b.inspection_date for b in month_batches if b.inspection_date}
        latest_batch_date = max(inspected_days) if inspected_days else ""
        has_today = ref_date_str in inspected_days

        # ── 缺漏日期（月初 → missing_end，整月每天都算應巡檢）─────────────
        missing_days: list[str] = []
        cursor = start_date
        while cursor <= missing_end:
            d_str = cursor.strftime("%Y/%m/%d")
            if d_str not in inspected_days:
                missing_days.append(d_str)
            cursor += timedelta(days=1)

        # ── 近 7 天趨勢 ────────────────────────────────────────────────────
        trend_7d = []
        for i in range(6, -1, -1):
            d_str = (trend_ref - timedelta(days=i)).strftime("%Y/%m/%d")
            trend_7d.append({"date": d_str, "has_record": d_str in inspected_days})

        results.append({
            "key":               cfg.key,
            "floor":             cfg.floor,
            "title":             cfg.title,
            "month_count":       month_count,
            "missing_count":     len(missing_days),
            "missing_days":      missing_days,
            "latest_batch_date": latest_batch_date,
            "has_today":         has_today,
            "is_current_month":  is_current,
            "trend_7d":          trend_7d,
            "has_data":          month_count > 0,
        })

    return {
        "month":      month,
        "year_month": year_month,
        "sheets":     results,
    }


# ══════════════════════════════════════════════════════════════════════════════
# GET /dashboard/calendar  — 月曆格（樓層 × 日）
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/dashboard/calendar",
    summary="整棟巡檢月曆格（樓層 × 日）",
    tags=["整棟巡檢"],
)
def get_dashboard_calendar(
    year:  int = Query(..., description="年份，如 2026"),
    month: int = Query(..., ge=1, le=12, description="月份，如 5"),
    db: Session = Depends(get_db),
):
    """
    回傳指定年月的樓層 × 日期月曆格資料。
    cell key = str(d)（非零填充，配合 MonthlyCalendarGrid 的 String(d) 讀法）。

    completion_rate = 該日所有場次的「已填項目數 / 總項目數」× 100，
    同一天有多場次時分子分母各自累加後再相除。
    """
    import calendar as cal_mod

    max_day = cal_mod.monthrange(year, month)[1]
    ym_prefix = f"{year}/{month:02d}/"

    rows = []
    for cfg in SHEET_CONFIGS:
        BatchModel, ItemModel = MODEL_MAP[cfg.key]

        month_batches = (
            db.query(BatchModel)
            .filter(BatchModel.inspection_date.like(f"{ym_prefix}%"))
            .all()
        )

        # ── 依「日」分組 ───────────────────────────────────────────────────
        by_day: dict[int, list] = {}
        for b in month_batches:
            try:
                day = int(b.inspection_date.split("/")[2])
            except (AttributeError, IndexError, ValueError):
                continue
            by_day.setdefault(day, []).append(b)

        # ── 一次撈完當月所有 item，避免每格一次 query ──────────────────────
        batch_ids = [b.ragic_id for b in month_batches]
        items_by_batch: dict[str, list] = {}
        if batch_ids:
            for it in (
                db.query(ItemModel)
                .filter(ItemModel.batch_ragic_id.in_(batch_ids))
                .all()
            ):
                items_by_batch.setdefault(it.batch_ragic_id, []).append(it)

        daily: dict[str, dict] = {}
        for d in range(1, max_day + 1):
            day_batches = by_day.get(d, [])
            if not day_batches:
                daily[str(d)] = {
                    "has_record":      False,
                    "completion_rate": 0,
                    "abnormal_count":  0,
                    "pending_count":   0,
                }
                continue

            total = checked = abnormal = pending = 0
            for b in day_batches:
                kpi = _calc_item_kpi(items_by_batch.get(b.ragic_id, []))
                total    += kpi["total"]
                checked  += kpi["checked"]
                abnormal += kpi["abnormal"]
                pending  += kpi["pending"]

            daily[str(d)] = {
                "has_record":      True,
                "completion_rate": round(checked / total * 100, 1) if total else 0,
                "abnormal_count":  abnormal,
                "pending_count":   pending,
            }

        rows.append({"key": cfg.key, "label": cfg.floor, "daily": daily})

    return {"year": year, "month": month, "max_day": max_day, "rows": rows}


# ══════════════════════════════════════════════════════════════════════════════
# GET /daily-form  — 每日巡檢表（模板結構，待本地同步接通後填充真實資料）
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/daily-form",
    summary="整棟巡檢每日巡檢表（樓層 × 項目 × 檢查內容）",
    tags=["整棟巡檢"],
)
def get_daily_form(
    year:            int           = Query(...,  description="年份，如 2026"),
    month:           int           = Query(...,  ge=1, le=12, description="月份，如 5"),
    inspection_date: Optional[str] = Query(None, description="巡檢日期 YYYY/MM/DD（不填則顯示整月模板）"),
):
    """
    回傳整棟巡檢每日巡檢表列（依 Excel #2.3整棟-每日巡檢表.xlsx）。

    本模組尚未實作本地 DB 同步，目前各列 matched=False、inspector/result_text 為空，
    模板結構（floor/item/check_content/result_options/rowSpan）已備妥，
    待本地同步接通後可在此填充真實巡檢資料。
    """
    from app.services.full_building_inspection_template import (
        FULL_BUILDING_DAILY_INSPECTION_TEMPLATE,
        STANDARD_MINUTES_MORNING,
        STANDARD_MINUTES_TOTAL,
    )

    rows = []
    for tmpl in FULL_BUILDING_DAILY_INSPECTION_TEMPLATE:
        rows.append({
            **tmpl,
            "inspector":     "",
            "result_text":   "",
            "result_status": "unchecked",
            "abnormal_note": "",
            "matched":       False,
            "abnormal":      False,
            "actual_minutes": 0,
        })

    return {
        "year":                    year,
        "month":                   month,
        "inspection_date":         inspection_date or "",
        "rows":                    rows,
        "standard_minutes_morning": STANDARD_MINUTES_MORNING,
        "standard_minutes_total":   STANDARD_MINUTES_TOTAL,
        "actual_minutes":           0,
    }
