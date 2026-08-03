"""
商場週期保養表 Pydantic Schemas
包含排程管理（mall_pm_schedule）相關 Schemas
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# ════════════════════════════════════════════════════════════════════════════
# 排程管理（mall_pm_schedule）Schemas
# ════════════════════════════════════════════════════════════════════════════

class MallPMScheduleOut(BaseModel):
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
    ragic_url:        str = ""             # 動態計算，指向 Ragic Sheet 24

    class Config:
        from_attributes = True


class MallPMScheduleKPI(BaseModel):
    total:               int   = 0
    unscheduled:         int   = 0
    scheduled:           int   = 0
    in_progress:         int   = 0
    completed:           int   = 0
    overdue:             int   = 0
    abnormal:            int   = 0
    should_do_not_done:  int   = 0   # 頻率符合但尚未納入排程的項目數
    completion_rate:     float = 0.0


class MallPMScheduleGenerateResult(BaseModel):
    year_month:              str
    generated:               int
    updated:                 int
    skipped_completed:       int
    skipped_edited:          int
    skipped_non_month:       int
    skipped_no_frequency:    int
    errors:                  List[str] = []


class MallPMScheduleUpdate(BaseModel):
    scheduled_date: Optional[str] = None
    executor_name:  Optional[str] = None
    start_time:     Optional[str] = None
    end_time:       Optional[str] = None
    is_completed:   Optional[bool] = None
    result_note:    Optional[str] = None
    abnormal_flag:  Optional[bool] = None
    abnormal_note:  Optional[str] = None


# ── 年度計劃矩陣 ──────────────────────────────────────────────────────────────

class MallPMScheduleMatrixEntry(BaseModel):
    """
    2026-08-03 新增：同一保養項目在同一個月可能有多筆批次記錄
    （實測 2026/07「1F~3F空調→保養」有 07/22、07/23、07/24 三筆），
    合併成一格後每一筆的原始資料保留在這裡，供明細 Drawer 逐筆列出。
    """
    item_ragic_id:  str
    status:         str
    schedule_id:    Optional[int] = None
    scheduled_date: Optional[str] = None
    category:       str = ""
    frequency:      str = ""
    ragic_url:      str = ""   # 指向 Ragic Sheet 24 該筆保養項目


class MallPMScheduleMatrixCell(BaseModel):
    month:          int
    status:         str    # 'completed'|'overdue'|'in_progress'|'scheduled'|'unscheduled'|'non_month'|'no_data'|'no_frequency'
    schedule_id:    Optional[int] = None
    scheduled_date: Optional[str] = None   # e.g. "05/15"，有排定日期才填
    # ── 2026-08-03 新增（同月多筆彙總）────────────────────────────────────────
    count:          int = 0                # 該月實際筆數；0 = 非本月／無資料
    entries:        List[MallPMScheduleMatrixEntry] = []   # count > 1 時供 Drawer 使用


class MallPMScheduleMatrixRow(BaseModel):
    item_ragic_id:  str
    category:       str
    task_name:      str
    location:       str
    frequency:      str
    cells:          List[MallPMScheduleMatrixCell]   # 12 個月（index 0 = 1月）
    # ── 2026-08-03 新增（跨月合併後的資料一致性提示）──────────────────────────
    # 同一 task_name 跨月的類別／頻率若不一致（實測「門扇→巡檢保養」有
    # 其它／空調／整體 三種類別），列首顯示最近月份的值，並把所有出現過的值
    # 放在這裡供前端 Tooltip 提示，避免 Ragic 上的分類錯誤被靜默隱藏。
    category_variants:  List[str] = []
    frequency_variants: List[str] = []
    month_count:        int = 0    # 此列合併自幾個月份的批次
    ragic_url:          str = ""   # 指向 Ragic Sheet 24（取最近月份那一筆）


class MallPMScheduleAnnualMatrix(BaseModel):
    year:    int
    rows:    List[MallPMScheduleMatrixRow]
    summary: dict = {}   # { "total_items": N, "completed_count": N, ... }
