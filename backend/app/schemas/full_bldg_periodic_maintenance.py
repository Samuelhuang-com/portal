"""
全棟例行維護 Pydantic Schemas
包含排程管理（full_bldg_pm_schedule）相關 Schemas
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# ════════════════════════════════════════════════════════════════════════════
# 排程管理（full_bldg_pm_schedule）Schemas
# ════════════════════════════════════════════════════════════════════════════

class FullBldgPMScheduleOut(BaseModel):
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
    status:    str = "unscheduled"   # 動態計算，不存 DB
    ragic_url: str = ""              # 該月份批次的 Ragic 連結（動態注入）

    class Config:
        from_attributes = True


class FullBldgPMScheduleKPI(BaseModel):
    total:               int   = 0
    unscheduled:         int   = 0
    scheduled:           int   = 0
    in_progress:         int   = 0
    completed:           int   = 0
    overdue:             int   = 0
    abnormal:            int   = 0
    should_do_not_done:  int   = 0   # 頻率符合但尚未納入排程的項目數
    completion_rate:     float = 0.0


class FullBldgPMScheduleGenerateResult(BaseModel):
    year_month:              str
    generated:               int
    updated:                 int
    skipped_completed:       int
    skipped_edited:          int
    skipped_non_month:       int
    skipped_no_frequency:    int
    errors:                  List[str] = []


class FullBldgPMScheduleUpdate(BaseModel):
    scheduled_date: Optional[str] = None
    executor_name:  Optional[str] = None
    start_time:     Optional[str] = None
    end_time:       Optional[str] = None
    is_completed:   Optional[bool] = None
    result_note:    Optional[str] = None
    abnormal_flag:  Optional[bool] = None
    abnormal_note:  Optional[str] = None


# ── 年度計劃矩陣 ──────────────────────────────────────────────────────────────

class FullBldgPMScheduleMatrixEntry(BaseModel):
    """
    2026-08-12 新增（比照 mall_pm）：同一個月、同一個保養項目可能有多筆批次記錄
    （例如同名項目排在 07/22、07/23 各一筆）。每一筆的原始資料放在這裡，供明細
    Drawer 逐筆列出，不被格內的彙總狀態蓋掉。
    """
    item_ragic_id:  str
    status:         str
    schedule_id:    Optional[int] = None
    scheduled_date: Optional[str] = None
    category:       str = ""
    frequency:      str = ""
    ragic_url:      str = ""
    # 2026-08-26 新增（年度計劃表 rule=v2）：這筆記錄「原本屬於哪個批次月份」。
    # v2 規則會把批次月份與顯示月份拆開（例：4 月批次、執行月份填 7 月 → 顯示在
    # 7 月欄），此欄保留原批次月份供前端提示與比對。legacy 規則下恆等於格子月份。
    origin_month:   Optional[int] = None
    # 2026-08-26：這一列的批次月份不在「執行月份」內，但已經有實際執行記錄，
    # 靠安全閥保留下來的。前端要標註，避免使用者以為它排錯月份。
    off_schedule:   bool = False


class FullBldgPMScheduleMatrixCell(BaseModel):
    month:          int
    status:         str    # 'completed'|'overdue'|'in_progress'|'scheduled'|'unscheduled'|'non_month'|'no_data'|'no_frequency'
    schedule_id:    Optional[int] = None
    scheduled_date: Optional[str] = None   # e.g. "05/15"，有排定日期才填
    count:          int = 0                # 該月實際記錄筆數（0 = 該月無此項目）
    entries:        List[FullBldgPMScheduleMatrixEntry] = []


class FullBldgPMScheduleMatrixRow(BaseModel):
    item_ragic_id:  str
    category:       str
    task_name:      str
    location:       str
    frequency:      str
    cells:          List[FullBldgPMScheduleMatrixCell]   # 12 個月（index 0 = 1月）
    # 2026-08-12 新增（比照 mall_pm）：以 task_name 跨月合併成一列後的附加資訊
    category_variants:  List[str] = []   # 跨月出現過的所有類別（顯示值取最近月份）
    frequency_variants: List[str] = []   # 跨月出現過的所有頻率（顯示值取最近月份）
    month_count:        int = 0          # 本列合併自幾個月份的批次
    ragic_url:          str = ""


class FullBldgPMScheduleAnnualMatrix(BaseModel):
    year:             int
    rows:             List[FullBldgPMScheduleMatrixRow]
    summary:          dict = {}   # { "total_items": N, "total_records": N, "completed_count": N, ... }
    month_batch_urls: dict = {}   # { "5": "https://...", "6": "https://..." }  月份 → Ragic 批次 URL
