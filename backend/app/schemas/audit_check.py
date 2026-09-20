"""
稽核檢查 — Pydantic Schemas
對應 app/models/audit_check.py、app/routers/audit_check.py
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── 判定類型 ───────────────────────────────────────────────────────────────
class ResultTypeBase(BaseModel):
    label: str = Field(..., max_length=50)
    color: str = Field("#000000", max_length=20)
    counts_as_pass: bool = True
    include_in_summary: bool = False
    is_default: bool = False
    sort_order: int = 0


class ResultTypeCreate(ResultTypeBase):
    code: str = Field(..., max_length=20, pattern=r"^[a-z][a-z0-9_]{1,19}$")


class ResultTypeUpdate(BaseModel):
    label: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    counts_as_pass: Optional[bool] = None
    include_in_summary: Optional[bool] = None
    is_default: Optional[bool] = None
    sort_order: Optional[int] = None


class ResultTypeOut(ResultTypeBase):
    id: int
    code: str
    is_system: bool
    is_active: bool

    class Config:
        from_attributes = True


# ── 檢查項主檔 ─────────────────────────────────────────────────────────────
class ItemCreate(BaseModel):
    name: str = Field(..., max_length=200)
    parent_id: Optional[int] = None
    description: Optional[str] = None
    sort_order: int = 0


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    sort_order: Optional[int] = None


class ItemOut(BaseModel):
    id: int
    parent_id: Optional[int]
    name: str
    description: Optional[str]
    sort_order: int
    is_active: bool
    in_use: bool = Field(False, description="是否已被任一期稽核單引用（True 則不可改名／刪除）")
    children: List["ItemOut"] = []

    class Config:
        from_attributes = True


ItemOut.model_rebuild()


# ── 期別 ───────────────────────────────────────────────────────────────────
class PeriodCreate(BaseModel):
    period: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    title: str = "財#3系統建置稽核"
    goal_major: int = 3
    goal_minor: int = 3
    note: Optional[str] = None
    review_counts_in_score: bool = True


class PeriodUpdate(BaseModel):
    title: Optional[str] = None
    goal_major: Optional[int] = None
    goal_minor: Optional[int] = None
    note: Optional[str] = None
    review_counts_in_score: Optional[bool] = None
    status: Optional[str] = None


class SheetSummary(BaseModel):
    id: int
    company_id: int
    company_name: str
    audited_on: Optional[date]
    status: str
    completion_rate: Optional[float]
    completion_label: str


class PeriodOut(BaseModel):
    id: int
    period: str
    title: str
    goal_major: int
    goal_minor: int
    note: Optional[str]
    review_counts_in_score: bool = True
    status: str
    created_at: datetime
    sheets: List[SheetSummary] = []

    class Config:
        from_attributes = True


# ── 稽核單 ─────────────────────────────────────────────────────────────────
class SheetItemSpec(BaseModel):
    """建立／調整稽核單時，一列檢查項的規格"""
    item_id: int
    scope_note: Optional[str] = None
    target_department_ids: List[int] = []


class SheetCreate(BaseModel):
    period_id: int
    company_id: int
    audited_on: Optional[date] = None
    audited_session: Optional[str] = None
    executor_label: Optional[str] = None
    department_ids: List[int] = []
    items: List[SheetItemSpec] = []
    carry_over: bool = Field(True, description="是否自動帶入上一期未達標項目為覆核待補正")


class SheetUpdate(BaseModel):
    audited_on: Optional[date] = None
    audited_session: Optional[str] = None
    executor_label: Optional[str] = None
    completion_adjust: Optional[int] = None
    remark: Optional[str] = None
    status: Optional[str] = None


class SheetLayoutUpdate(BaseModel):
    department_ids: List[int]
    items: List[SheetItemSpec]


class SheetDepartmentOut(BaseModel):
    id: int
    department_id: int
    name: str
    sort_order: int
    deficiency_override: Optional[str]
    deficiency: str = Field("", description="缺失列最終顯示值（覆寫優先，否則自動彙整）")


class SheetItemOut(BaseModel):
    id: int
    item_id: int
    parent_sheet_item_id: Optional[int]
    level: int
    display_no: Optional[str]
    name: str
    scope_note: Optional[str]
    target_department_ids: List[int]
    sort_order: int


class CellOut(BaseModel):
    sheet_item_id: int
    sheet_department_id: int
    comment: Optional[str]
    result_code: str
    updated_at: Optional[datetime]


class DepartmentScore(BaseModel):
    sheet_department_id: int
    department_id: int
    name: str
    sub_count: int
    pass_count: int
    score: Optional[float]
    score_label: str


class ReviewOut(BaseModel):
    sheet_department_id: int
    source_period: Optional[str]
    pending_text: Optional[str]
    pending_result: str
    result_text: Optional[str]
    result_status: str


class SheetDetail(BaseModel):
    id: int
    period_id: int
    period: str
    title: str
    goal_major: int
    goal_minor: int
    review_counts_in_score: bool
    company_id: int
    company_name: str
    audited_on: Optional[date]
    audited_session: Optional[str]
    audited_label: str
    executor_label: Optional[str]
    completion_adjust: int
    remark: Optional[str]
    status: str
    departments: List[SheetDepartmentOut]
    items: List[SheetItemOut]
    cells: List[CellOut]
    scores: List[DepartmentScore]
    reviews: List[ReviewOut]
    completion_rate: Optional[float]
    completion_label: str
    result_types: List[ResultTypeOut]


# ── 格子寫入 ───────────────────────────────────────────────────────────────
class CellUpsert(BaseModel):
    sheet_item_id: int
    sheet_department_id: int
    comment: Optional[str] = None
    result_code: Optional[str] = None


class CellBulkUpsert(BaseModel):
    cells: List[CellUpsert]


class ReviewUpsert(BaseModel):
    source_period: Optional[str] = None
    pending_text: Optional[str] = None
    pending_result: Optional[str] = None
    result_text: Optional[str] = None
    result_status: Optional[str] = None


class DeficiencyUpsert(BaseModel):
    deficiency_override: Optional[str] = None


# ── 統計 ───────────────────────────────────────────────────────────────────
class StatisticsCell(BaseModel):
    period: str
    score: Optional[float]
    label: str


class StatisticsRow(BaseModel):
    department_id: int
    name: str
    cells: List[StatisticsCell]


class StatisticsBlock(BaseModel):
    company_id: int
    company_name: str
    periods: List[str]
    audited_labels: List[str]
    major_items: List[List[str]]
    rows: List[StatisticsRow]
    completion: List[StatisticsCell]


class StatisticsOut(BaseModel):
    year: int
    note: Optional[str]
    blocks: List[StatisticsBlock]


class AdviceRow(BaseModel):
    company_name: str
    department_name: str
    item_name: str
    result_code: str
    result_label: str
    result_color: str
    comment: str
