"""
保全巡檢 Pydantic Schemas
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# ── 場次 ──────────────────────────────────────────────────────────────────────

class PatrolBatchOut(BaseModel):
    ragic_id:        str
    sheet_key:       str
    sheet_id:        int
    sheet_name:      str
    inspection_date: str
    inspector_name:  str
    start_time:      str
    end_time:        str
    work_hours:      str
    item_count:      int = 0
    synced_at:       Optional[datetime] = None

    class Config:
        from_attributes = True


# ── 巡檢項目 ──────────────────────────────────────────────────────────────────

class PatrolItemOut(BaseModel):
    ragic_id:       str
    batch_ragic_id: str
    sheet_key:      str
    seq_no:         int
    item_name:      str
    result_raw:     str
    result_status:  str   # normal / abnormal / pending / unchecked / note
    abnormal_flag:  bool
    is_note:        bool = False  # True = 文字備註欄位（異常說明），呈現但不計入統計
    synced_at:      Optional[datetime] = None

    class Config:
        from_attributes = True


# ── KPI ───────────────────────────────────────────────────────────────────────

class PatrolBatchKPI(BaseModel):
    total:           int   = 0
    normal:          int   = 0
    abnormal:        int   = 0
    pending:         int   = 0
    unchecked:       int   = 0
    completion_rate: float = 0.0
    normal_rate:     float = 0.0


class StatusDistItem(BaseModel):
    status: str
    label:  str
    count:  int
    color:  str


# ── 批次詳情 ──────────────────────────────────────────────────────────────────

class PatrolBatchDetail(BaseModel):
    batch: PatrolBatchOut
    kpi:   PatrolBatchKPI
    items: List[PatrolItemOut]


# ── 全站統計（Dashboard 資料來源）────────────────────────────────────────────

class PatrolStats(BaseModel):
    sheet_key:          str
    sheet_name:         str
    latest_batch:       Optional[PatrolBatchOut] = None
    latest_kpi:         Optional[PatrolBatchKPI] = None
    recent_abnormal:    List[PatrolItemOut]       = []
    recent_pending:     List[PatrolItemOut]       = []
    status_distribution: List[StatusDistItem]     = []
    total_batches_7d:   int                       = 0
    abnormal_trend:     List[dict]                = []


# ── Sheet 設定資訊 ─────────────────────────────────────────────────────────────

class SheetConfig(BaseModel):
    key:  str
    id:   int
    name: str
    path: str
