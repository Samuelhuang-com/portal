"""
週期保養表 Pydantic Schemas (v2)
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel




# ── 批次主表 ──────────────────────────────────────────────────────────────────

class PMBatchOut(BaseModel):
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

class PMItemOut(BaseModel):
    ragic_id:          str
    batch_ragic_id:    str
    seq_no:            int
    category:          str
    frequency:         str
    exec_months_raw:   str
    exec_months_json:  str          # JSON string "[2,5,8,11]"
    task_name:         str
    location:          str
    estimated_minutes: int
    scheduled_date:    str
    scheduler_name:    str
    executor_name:     str
    start_time:           str
    end_time:             str
    ragic_work_minutes:   Optional[int] = None
    is_completed:         bool = False
    result_note:       str
    abnormal_flag:     bool
    abnormal_note:     str
    portal_edited_at:  Optional[datetime] = None
    synced_at:         Optional[datetime] = None
    status:            str = "unscheduled"
    ragic_url:         str = ""
    repair_hours:      Optional[float] = None

    class Config:
        from_attributes = True


# ── Portal 編輯 ──────────────────────────────────────────────────────────────

class PMItemUpdate(BaseModel):
    pass


# ── KPI ───────────────────────────────────────────────────────────────────────

class PMBatchKPI(BaseModel):
    total:                int     = 0
    current_month_total:  int     = 0
    completed:            int     = 0
    in_progress:          int     = 0
    scheduled:            int     = 0
    unscheduled:          int     = 0
    overdue:              int     = 0
    abnormal:             int     = 0
    completion_rate:      float   = 0.0
    planned_minutes:      int     = 0
    actual_minutes:       int     = 0


class CategoryStat(BaseModel):
    category:   str
    total:      int
    completed:  int
    rate:       float


class StatusDistItem(BaseModel):
    status: str
    label:  str
    count:  int
    color:  str


# ── 批次詳情（含所有項目）────────────────────────────────────────────────────

class PMBatchDetail(BaseModel):
    batch:      PMBatchOut
    kpi:        PMBatchKPI
    items:      List[PMItemOut]
    categories: List[CategoryStat]


# ── 全站統計（Dashboard 資料來源）───────────────────────────────────────────

class PMStats(BaseModel):
    current_batch:       Optional[PMBatchOut]   = None
    current_kpi:         Optional[PMBatchKPI]   = None
    overdue_items:       List[PMItemOut]        = []
    upcoming_items:      List[PMItemOut]        = []
    category_stats:      List[CategoryStat]     = []
    status_distribution: List[StatusDistItem]   = []


# ── 週期統計（月 / 季 / 年）─────────────────────────────────────────────────

class PMIncompleteItem(BaseModel):
    task_name:            str
    category:             str
    scheduled_date_full:  str
    result_note:          str
    frequency:            str


class PMSubPeriodBreakdown(BaseModel):
    label:     str
    total:     int
    completed: int
    rate:      Optional[float] = None


class PMPeriodStats(BaseModel):
    period_type:   str
    period_label:  str
    period_start:  str
    period_end:    str
    prev_period_end: str
    prev_carry_over:         int            = 0
    prev_resolved_in_period: int            = 0
    carry_over_rate:         Optional[float] = None
    period_total:     int            = 0
    period_completed: int            = 0
    period_rate:      Optional[float] = None
    sub_period_breakdown: List[PMSubPeriodBreakdown] = []
    incomplete_items: List[PMIncompleteItem] = []


# ── 年度矩陣統計（12個月橫軸）────────────────────────────────────────────────

class PMYearMatrixMonth(BaseModel):
    month:                   int
    label:                   str
    prev_carry_over:         int   = 0
    prev_resolved_in_period: int   = 0
    carry_over_rate:         Optional[float] = None
    period_total:            int   = 0
    period_completed:        int   = 0
    period_rate:             Optional[float] = None
    incomplete_notes:        str   = ""


class PMYearMatrix(BaseModel):
    year:   int
    months: List[PMYearMatrixMonth]


# ════════════════════════════════════════════════════════════════════════════
# 排程管理（pm_schedule）Schemas
# ════════════════════════════════════════════════════════════════════════════

class PMScheduleOut(BaseModel):
    id:               int
    year_month:       str
    item_ragic_id:    str
    category:         str
    task_name:        str
    location:         str
    frequency:        str
    estimated_minutes: int
    scheduled_date:   str
    executor_name:    str
    schedule_source:  str
    start_time:       str
    end_time:         str
    is_completed:     bool
    result_note:      str
    abnormal_flag:    bool
    abnormal_note:    str
    portal_edited_at: Optional[datetime] = None
    created_at:       datetime
    updated_at:       datetime
    status:           str = "unscheduled"   # 動態計算，不存 DB

    class Config:
        from_attributes = True


class PMScheduleKPI(BaseModel):
    total:               int   = 0
    unscheduled:         int   = 0
    scheduled:           int   = 0
    in_progress:         int   = 0
    completed:           int   = 0
    overdue:             int   = 0
    abnormal:            int   = 0
    should_do_not_done:  int   = 0   # 頻率符合但尚未納入排程的項目數
    completion_rate:     float = 0.0


class PMScheduleGenerateResult(BaseModel):
    year_month:              str
    generated:               int
    updated:                 int
    skipped_completed:       int
    skipped_edited:          int
    skipped_non_month:       int
    skipped_no_frequency:    int
    errors:                  List[str] = []


class PMScheduleUpdate(BaseModel):
    scheduled_date: Optional[str] = None
    executor_name:  Optional[str] = None
    start_time:     Optional[str] = None
    end_time:       Optional[str] = None
    is_completed:   Optional[bool] = None
    result_note:    Optional[str] = None
    abnormal_flag:  Optional[bool] = None
    abnormal_note:  Optional[str] = None


# ── 年度計劃矩陣 ──────────────────────────────────────────────────────────────

class PMScheduleMatrixCell(BaseModel):
    month:          int
    status:         str    # 'completed'|'overdue'|'in_progress'|'scheduled'|'unscheduled'|'non_month'|'no_data'|'no_frequency'
    schedule_id:    Optional[int] = None
    scheduled_date: Optional[str] = None   # e.g. "05/15"，有排定日期才填


class PMScheduleMatrixRow(BaseModel):
    item_ragic_id:  str
    category:       str
    task_name:      str
    location:       str
    frequency:      str
    cells:          List[PMScheduleMatrixCell]   # 12 個月（index 0 = 1月）


class PMScheduleAnnualMatrix(BaseModel):
    year:    int
    rows:    List[PMScheduleMatrixRow]
    summary: dict = {}   # { "total_items": N, "completed_count": N, ... }
