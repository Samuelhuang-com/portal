"""
保全巡檢統計 Dashboard Pydantic Schemas
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


class SheetStats(BaseModel):
    """單一 Sheet 的統計摘要"""
    sheet_key:       str
    sheet_name:      str
    total_batches:   int   = 0   # 今日場次數
    total_items:     int   = 0
    checked_items:   int   = 0
    unchecked_items: int   = 0
    abnormal_items:  int   = 0
    pending_items:   int   = 0
    completion_rate: float = 0.0
    normal_rate:     float = 0.0
    has_data:        bool  = False


class DashboardSummary(BaseModel):
    """Dashboard 主摘要"""
    target_date:   str
    sheets:        List[SheetStats] = []
    # 全體加總
    total_batches_all:   int   = 0
    total_items_all:     int   = 0
    checked_items_all:   int   = 0
    abnormal_items_all:  int   = 0
    completion_rate_all: float = 0.0
    generated_at:  str   = ""


class IssueItem(BaseModel):
    id:            str
    issue_date:    str
    sheet_key:     str
    sheet_name:    str
    item_name:     str
    status:        str
    status_label:  str
    inspector:     str = ""
    note:          str = ""
    batch_id:      str = ""


class IssueListResponse(BaseModel):
    items: List[IssueItem]
    total: int


class TrendPoint(BaseModel):
    date:           str
    abnormal_count: int   = 0
    total_batches:  int   = 0
    has_data:       bool  = False
    # 各 sheet 資料（key = sheet_key）
    by_sheet:       dict  = {}


class DashboardTrend(BaseModel):
    trend: List[TrendPoint]
    days:  int
