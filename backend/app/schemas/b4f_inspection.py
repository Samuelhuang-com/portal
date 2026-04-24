"""
整棟工務每日巡檢 - B4F  Pydantic Schemas (v3)

架構說明（寬表格 Pivot）：
  InspectionBatchOut  → 一次巡檢場次，batch identifier = ragic_id（Ragic Row ID）
  InspectionItemOut   → 一個設備欄位巡檢結果（每場次 pivot 成 N 筆）
  路由 /batches/{batch_id} 的 batch_id = ragic_id
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# ── 巡檢場次 ─────────────────────────────────────────────────────────────────

class InspectionBatchOut(BaseModel):
    ragic_id:        str            # Ragic Row ID（作為批次唯一識別符）
    inspection_date: str            # YYYY/MM/DD（從開始時間萃取）
    inspector_name:  str
    start_time:      str            # 開始巡檢時間原始值
    end_time:        str            # 巡檢結束時間原始值
    work_hours:      str            # 工時計算（如 "2 分鐘"）
    item_count:      int = 0        # 該場次的設備項目總數
    synced_at:       Optional[datetime] = None

    class Config:
        from_attributes = True


# ── 設備巡檢項目 ──────────────────────────────────────────────────────────────

class InspectionItemOut(BaseModel):
    ragic_id:       str             # "{batch_ragic_id}_{seq_no}"
    batch_ragic_id: str
    seq_no:         int
    item_name:      str             # 設備/項目名稱（Ragic 欄位名）
    result_raw:     str             # 原始值（正常/異常/待處理 或空白）
    result_status:  str             # normal / abnormal / pending / unchecked
    abnormal_flag:  bool
    synced_at:      Optional[datetime] = None

    class Config:
        from_attributes = True


# ── KPI ───────────────────────────────────────────────────────────────────────

class InspectionBatchKPI(BaseModel):
    total:            int   = 0
    normal:           int   = 0
    abnormal:         int   = 0
    pending:          int   = 0
    unchecked:        int   = 0
    completion_rate:  float = 0.0   # (normal + abnormal + pending) / total × 100
    normal_rate:      float = 0.0   # normal / (total - unchecked) × 100


class StatusDistItem(BaseModel):
    status: str
    label:  str
    count:  int
    color:  str


# ── 批次詳情（含所有項目）────────────────────────────────────────────────────

class InspectionBatchDetail(BaseModel):
    batch: InspectionBatchOut
    kpi:   InspectionBatchKPI
    items: List[InspectionItemOut]


# ── 全站統計（Dashboard 資料來源）───────────────────────────────────────────

class InspectionStats(BaseModel):
    latest_batch:        Optional[InspectionBatchOut] = None
    latest_kpi:          Optional[InspectionBatchKPI] = None
    recent_abnormal:     List[InspectionItemOut]      = []
    recent_pending:      List[InspectionItemOut]      = []
    status_distribution: List[StatusDistItem]         = []
    total_batches_7d:    int                          = 0
    abnormal_trend:      List[dict]                   = []   # [{date, abnormal_count, has_record}]
