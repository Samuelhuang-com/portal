"""
飯店例行維護 Pydantic Schemas
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel


# ── 批次主表 ──────────────────────────────────────────────────────────────────

class HotelRoutinePMBatchOut(BaseModel):
    ragic_id:         str
    journal_no:       str
    period_month:     str
    ragic_created_at: str
    ragic_updated_at: str
    ragic_url:        str = ""
    synced_at:        Optional[datetime] = None

    class Config:
        from_attributes = True


# ── 保養項目 ──────────────────────────────────────────────────────────────────

class HotelRoutinePMItemOut(BaseModel):
    ragic_id:          str
    batch_ragic_id:    str
    seq_no:            int
    category:          str
    frequency:         str
    exec_months_raw:   str
    exec_months_json:  str
    task_name:         str
    location:          str
    estimated_minutes: int
    scheduled_date:    str
    scheduler_name:    str
    executor_name:     str
    start_time:        str
    end_time:          str
    ragic_work_minutes: Optional[int] = None
    is_completed:      bool = False
    result_note:       str
    abnormal_flag:     bool
    abnormal_note:     str
    portal_edited_at:  Optional[datetime] = None
    synced_at:         Optional[datetime] = None
    status:            str = "unscheduled"
    ragic_url:         str = ""

    class Config:
        from_attributes = True


# ── Portal 編輯 ──────────────────────────────────────────────────────────────

class HotelRoutinePMItemUpdate(BaseModel):
    pass


# ── KPI ───────────────────────────────────────────────────────────────────────

class HotelRoutinePMBatchKPI(BaseModel):
    total:                int   = 0
    current_month_total:  int   = 0
    completed:            int   = 0
    in_progress:          int   = 0
    scheduled:            int   = 0
    unscheduled:          int   = 0
    overdue:              int   = 0
    abnormal:             int   = 0
    completion_rate:      float = 0.0
    planned_minutes:      int   = 0
    actual_minutes:       int   = 0


class HotelRoutinePMCategoryStat(BaseModel):
    category:  str
    total:     int
    completed: int
    rate:      float


class HotelRoutinePMStatusDistItem(BaseModel):
    status: str
    label:  str
    count:  int
    color:  str


# ── 批次詳情（含所有項目）────────────────────────────────────────────────────

class HotelRoutinePMBatchDetail(BaseModel):
    batch:      HotelRoutinePMBatchOut
    kpi:        HotelRoutinePMBatchKPI
    items:      List[HotelRoutinePMItemOut]
    categories: List[HotelRoutinePMCategoryStat]


# ── 全站統計 ─────────────────────────────────────────────────────────────────

class HotelRoutinePMStats(BaseModel):
    current_batch:       Optional[HotelRoutinePMBatchOut]  = None
    current_kpi:         Optional[HotelRoutinePMBatchKPI]  = None
    overdue_items:       List[HotelRoutinePMItemOut]       = []
    upcoming_items:      List[HotelRoutinePMItemOut]       = []
    category_stats:      List[HotelRoutinePMCategoryStat]  = []
    status_distribution: List[HotelRoutinePMStatusDistItem] = []


# ── 週期統計 ─────────────────────────────────────────────────────────────────

class HotelRoutinePMIncompleteItem(BaseModel):
    task_name:           str
    category:            str
    scheduled_date_full: str
    result_note:         str
    frequency:           str


class HotelRoutinePMSubPeriodBreakdown(BaseModel):
    label:     str
    total:     int
    completed: int
    rate:      Optional[float] = None


class HotelRoutinePMPeriodStats(BaseModel):
    period_type:   str
    period_label:  str
    period_start:  str
    period_end:    str
    prev_period_end:         str
    prev_carry_over:         int           = 0
    prev_resolved_in_period: int           = 0
    carry_over_rate:         Optional[float] = None
    period_total:     int           = 0
    period_completed: int           = 0
    period_rate:      Optional[float] = None
    sub_period_breakdown: List[HotelRoutinePMSubPeriodBreakdown] = []
    incomplete_items: List[HotelRoutinePMIncompleteItem] = []


# ── 年度矩陣統計 ─────────────────────────────────────────────────────────────

class HotelRoutinePMYearMatrixMonth(BaseModel):
    month:                   int
    label:                   str
    prev_carry_over:         int   = 0
    prev_resolved_in_period: int   = 0
    carry_over_rate:         Optional[float] = None
    period_total:            int   = 0
    period_completed:        int   = 0
    period_rate:             Optional[float] = None
    incomplete_notes:        str   = ""


class HotelRoutinePMYearMatrix(BaseModel):
    year:   int
    months: List[HotelRoutinePMYearMatrixMonth]


# ── 排程管理 Schemas ──────────────────────────────────────────────────────────

class HotelRoutinePMScheduleOut(BaseModel):
    id:                int
    year_month:        str
    item_ragic_id:     str
    category:          str
    task_name:         str
    location:          str
    frequency:         str
    estimated_minutes: int
    scheduled_date:    str
    executor_name:     str
    schedule_source:   str
    start_time:        str
    end_time:          str
    is_completed:      bool
    result_note:       str
    abnormal_flag:     bool
    abnormal_note:     str
    portal_edited_at:  Optional[datetime] = None
    created_at:        datetime
    updated_at:        datetime
    status:            str = "unscheduled"

    class Config:
        from_attributes = True


class HotelRoutinePMScheduleKPI(BaseModel):
    total:              int   = 0
    unscheduled:        int   = 0
    scheduled:          int   = 0
    in_progress:        int   = 0
    completed:          int   = 0
    overdue:            int   = 0
    abnormal:           int   = 0
    should_do_not_done: int   = 0
    completion_rate:    float = 0.0


class HotelRoutinePMScheduleGenerateResult(BaseModel):
    year_month:            str
    generated:             int
    updated:               int
    skipped_completed:     int
    skipped_edited:        int
    skipped_non_month:     int
    skipped_no_frequency:  int
    errors:                List[str] = []


class HotelRoutinePMScheduleUpdate(BaseModel):
    scheduled_date: Optional[str]  = None
    executor_name:  Optional[str]  = None
    start_time:     Optional[str]  = None
    end_time:       Optional[str]  = None
    is_completed:   Optional[bool] = None
    result_note:    Optional[str]  = None
    abnormal_flag:  Optional[bool] = None
    abnormal_note:  Optional[str]  = None


# ── 年度計劃矩陣 ─────────────────────────────────────────────────────────────

class HotelRoutinePMScheduleMatrixCell(BaseModel):
    month:          int
    status:         str
    schedule_id:    Optional[int] = None
    scheduled_date: Optional[str] = None


class HotelRoutinePMScheduleMatrixRow(BaseModel):
    item_ragic_id: str
    category:      str
    task_name:     str
    location:      str
    frequency:     str
    cells:         List[HotelRoutinePMScheduleMatrixCell]


class HotelRoutinePMScheduleAnnualMatrix(BaseModel):
    year:    int
    rows:    List[HotelRoutinePMScheduleMatrixRow]
    summary: dict = {}


# ── 保養項目目錄 ─────────────────────────────────────────────────────────────

class HotelRoutinePMCatalogItem(BaseModel):
    seq_no:            int
    category:          str
    frequency:         str
    task_name:         str
    location:          str
    estimated_minutes: int
    exec_months_raw:   str


# ── 矩陣明細項目 ─────────────────────────────────────────────────────────────

class HotelRoutinePMMatrixItem(BaseModel):
    ragic_id:      str
    seq_no:        int
    category:      str
    frequency:     str
    task_name:     str
    location:      str
    exec_months_raw: str
    scheduled_date: str
    start_time:    str
    end_time:      str
    is_completed:  bool
    ragic_work_minutes: Optional[int] = None
    status:        str = "unscheduled"
