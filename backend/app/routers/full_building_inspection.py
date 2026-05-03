"""
整棟巡檢 API Router
Prefix: /api/v1/full-building-inspection

此模組不做本地資料同步，僅提供 Ragic 表單設定給前端使用。
各樓層巡檢實際填寫作業在 Ragic 系統執行。

端點：
  GET /sheets                    — 取得所有樓層巡檢 Sheet 設定（Ragic URL 等）
  GET /dashboard/monthly-summary — Dashboard 月份統計（目前回傳空結構，待同步功能實作後填充）
"""
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.dependencies import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


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
):
    """
    回傳各 Sheet 的月份 KPI 結構。
    目前此模組尚未實作本地資料同步，故全部統計回傳零值。
    待後續接入本地同步後，可直接在此填充真實資料。
    """
    from app.core.date_utils import get_month_range, to_ragic_year_month

    today = date.today()
    if not month:
        month = today.strftime("%Y-%m")

    start_date, end_date = get_month_range(month)
    year_month = to_ragic_year_month(month)
    is_current = (start_date.year == today.year and start_date.month == today.month)
    trend_ref  = today if is_current else end_date

    # 近 7 天趨勢（空資料結構，待同步實作後填充）
    default_trend = []
    for i in range(6, -1, -1):
        d = trend_ref - timedelta(days=i)
        default_trend.append({"date": d.strftime("%Y/%m/%d"), "has_record": False})

    results = []
    for cfg in SHEET_CONFIGS:
        results.append({
            "key":               cfg.key,
            "floor":             cfg.floor,
            "title":             cfg.title,
            "month_count":       0,
            "missing_count":     0,
            "missing_days":      [],
            "latest_batch_date": "",
            "has_today":         False,
            "is_current_month":  is_current,
            "trend_7d":          list(default_trend),
            "has_data":          False,
        })

    return {
        "month":      month,
        "year_month": year_month,
        "sheets":     results,
    }
