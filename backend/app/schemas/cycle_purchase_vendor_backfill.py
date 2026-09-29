"""
週期採購 — 料號主檔「供應商資料回填」Pydantic Schemas（2026-09-30 新增）
說明見 app/services/cycle_purchase_vendor_backfill_service.py 檔頭。
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class BackfillCandidate(BaseModel):
    ragic_id: str
    ragic_code: str = ""
    name: str
    short_name: str = ""
    tax_id: str = ""
    ragic_url: str
    score: float
    target_vendor_id: Optional[int] = None
    target_vendor_code: Optional[str] = None
    target_vendor_name: Optional[str] = None
    selectable: bool
    block_reason: Optional[str] = None


class BackfillRow(BaseModel):
    vendor_id: int
    vendor_code: str
    vendor_name: str
    is_active: bool
    item_count: int
    mapping_count: int
    summary_count: int = Field(0, description="尚未拋轉 Ragic、尚未轉採購單的彙整列數")
    match_type: str = Field(description="short＝簡稱相同／similar＝名稱相似（人工選定）／none＝Ragic 找不到")
    candidates: List[BackfillCandidate]
    suggested_ragic_id: Optional[str] = None


class BackfillSummary(BaseModel):
    ragic_vendor_count: int
    ragic_short_name_count: int
    orphan_count: int
    short_count: int
    similar_count: int
    none_count: int
    items_without_vendor: int


class BackfillSyncStep(BaseModel):
    name: str
    ok: bool
    message: str


class BackfillPreview(BaseModel):
    sync_steps: List[BackfillSyncStep] = []
    summary: BackfillSummary
    rows: List[BackfillRow]


class BackfillDecision(BaseModel):
    vendor_id: int = Field(description="要回填的週採供應商（未對照合約主檔的那一筆）id")
    ragic_id: str = Field(description="選定的 Ragic 廠商資料表記錄 id")


class BackfillApplyPayload(BaseModel):
    decisions: List[BackfillDecision] = Field(min_length=1)


class BackfillApplyRow(BaseModel):
    vendor_id: int
    vendor_name: str
    target_vendor_id: int
    target_vendor_name: str
    items_updated: int
    mappings_updated: int
    summaries_updated: int = 0


class BackfillApplyResult(BaseModel):
    results: List[BackfillApplyRow]
    items_updated: int
    mappings_updated: int
    summaries_updated: int = 0
