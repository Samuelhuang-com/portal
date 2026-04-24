"""
整棟巡檢 API Router
Prefix: /api/v1/full-building-inspection

此模組不做本地資料同步，僅提供 Ragic 表單設定給前端使用。
各樓層巡檢實際填寫作業在 Ragic 系統執行。

端點：
  GET /sheets  — 取得所有樓層巡檢 Sheet 設定（Ragic URL 等）
"""
from fastapi import APIRouter
from typing import List
from pydantic import BaseModel

router = APIRouter()


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
