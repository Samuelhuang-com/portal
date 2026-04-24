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
    start_time:        str
    end_time:          str
    is_completed:      bool = False        # 保養是否完成（啟+迄均有值則自動 True）
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
    planned_minutes:      int     = 0


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
