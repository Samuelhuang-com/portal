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
    ragic_work_minutes:   Optional[int] = None  # Ragic「工時計算」欄位（分鐘）；NULL = 未填
    is_completed:         bool = False           # 保養是否完成（啟+迄均有值則自動 True）
    result_note:       str
    abnormal_flag:     bool
    abnormal_note:     str
    portal_edited_at:  Optional[datetime] = None
    synced_at:         Optional[datetime] = None
    # 計算欄位（由 API 動態注入）
    status:            str = "unscheduled"

    class Config:
        from_attributes = True


# ── Portal 編輯 ──────────────────────────────────────────────────────────────

# PMItemUpdate 已停用（Portal 不提供編輯，資料全部來自 Ragic 同步）
# 保留定義供未來需要時參考
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
    planned_minutes:      int     = 0   # 預估工時合計（estimated_minutes 加總）
    actual_minutes:       int     = 0   # 實際工時合計（end_time - start_time 加總）


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
    """未完成事項（僅顯示有 result_note 的項目）"""
    task_name:            str
    category:             str
    scheduled_date_full:  str    # "YYYY/MM/DD"
    result_note:          str
    frequency:            str


class PMSubPeriodBreakdown(BaseModel):
    """子期間分布：季統計→每月；年統計→每季"""
    label:     str            # "1月" / "Q1" 等
    total:     int
    completed: int
    rate:      Optional[float] = None    # None = N/A（分母為 0）


class PMPeriodStats(BaseModel):
    """月 / 季 / 年統計回傳結構"""
    period_type:   str    # "month" | "quarter" | "year"
    period_label:  str    # "2026年4月" / "2026 Q2" / "2026年"
    period_start:  str    # "2026-04-01"
    period_end:    str    # "2026-04-30"
    prev_period_end: str  # "2026-03-31"

    # ── 上期累計 ───────────────────────────────────────────────────────────
    prev_carry_over:         int            = 0     # 上期累計未完成數
    prev_resolved_in_period: int            = 0     # 上期未完成於本期結案數
    carry_over_rate:         Optional[float] = None  # 累計完成率（%），分母=0→None

    # ── 本期 ───────────────────────────────────────────────────────────────
    period_total:     int            = 0     # 本期項目數
    period_completed: int            = 0     # 本期完成數
    period_rate:      Optional[float] = None  # 本期完成率（%），分母=0→None

    # ── 子期間分布 ─────────────────────────────────────────────────────────
    sub_period_breakdown: List[PMSubPeriodBreakdown] = []

    # ── 未完成事項說明（result_note 非空才列入）────────────────────────────
    incomplete_items: List[PMIncompleteItem] = []


# ── 年度矩陣統計（12個月橫軸）────────────────────────────────────────────────

class PMYearMatrixMonth(BaseModel):
    """年度矩陣中單一月份的所有指標"""
    month:                   int            # 1-12
    label:                   str            # "一月" ... "十二月"
    prev_carry_over:         int   = 0      # 上月累計未完成項目數
    prev_resolved_in_period: int   = 0      # 上月未完成於本月結案數
    carry_over_rate:         Optional[float] = None  # 累計項目完成率（%）
    period_total:            int   = 0      # 本月週期保養項目數
    period_completed:        int   = 0      # 本月週期保養完成數
    period_rate:             Optional[float] = None  # 本月週期保養完成率（%）
    incomplete_notes:        str   = ""     # 未完成備註（換行分隔；空白=無）


class PMYearMatrix(BaseModel):
    """全年 12 個月矩陣統計"""
    year:   int
    months: List[PMYearMatrixMonth]
