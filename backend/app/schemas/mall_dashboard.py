"""
商場管理統計 Dashboard  Pydantic Schemas
"""
from typing import List, Optional
from pydantic import BaseModel


# ── 巡檢 ──────────────────────────────────────────────────────────────────────

class FloorInspectionStats(BaseModel):
    floor:           str    # "b1f" | "b2f" | "rf"
    floor_label:     str    # "B1F" | "B2F" | "RF"
    batches:         int   = 0
    total_items:     int   = 0
    normal_items:    int   = 0
    abnormal_items:  int   = 0
    pending_items:   int   = 0
    unchecked_items: int   = 0
    checked_items:   int   = 0
    completion_rate: float = 0.0
    normal_rate:     float = 0.0


class InspectionSummary(BaseModel):
    target_date:     str
    total_batches:   int   = 0
    total_items:     int   = 0
    checked_items:   int   = 0
    unchecked_items: int   = 0
    abnormal_items:  int   = 0    # abnormal + pending
    completion_rate: float = 0.0
    by_floor:        List[FloorInspectionStats] = []


# ── 週期保養 ──────────────────────────────────────────────────────────────────

class PMSummary(BaseModel):
    period_month:    str
    total_items:     int   = 0
    completed_items: int   = 0
    incomplete_items: int  = 0
    overdue_items:   int   = 0
    abnormal_items:  int   = 0
    completion_rate: float = 0.0


# ── Dashboard 整體摘要 ─────────────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    inspection:   InspectionSummary
    pm:           PMSummary
    generated_at: str


# ── 異常 / 待追蹤清單 ─────────────────────────────────────────────────────────

class IssueItem(BaseModel):
    id:           str
    issue_date:   str
    issue_type:   str   # "inspection" | "pm"
    floor:        str   # "B1F" | "B2F" | "RF" | "商場"
    item_name:    str
    status:       str   # "abnormal" | "pending" | "unchecked" | "overdue"
    status_label: str
    responsible:  str
    note:         str
    batch_id:     str   # 供 deep-link 使用


class IssueListResponse(BaseModel):
    items: List[IssueItem]
    total: int


# ── 趨勢資料 ──────────────────────────────────────────────────────────────────

class TrendPoint(BaseModel):
    date:            str
    b1f_completion:  float = 0.0
    b2f_completion:  float = 0.0
    rf_completion:   float = 0.0
    b1f_abnormal:    int   = 0
    b2f_abnormal:    int   = 0
    rf_abnormal:     int   = 0
    total_abnormal:  int   = 0
    has_data:        bool  = False


class DashboardTrend(BaseModel):
    trend: List[TrendPoint]
    days:  int
