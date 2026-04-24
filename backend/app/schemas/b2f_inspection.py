"""
整棟工務每日巡檢 - B2F  Pydantic Schemas【寬表格 Pivot 架構】
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class B2FInspectionBatchOut(BaseModel):
    ragic_id:        str
    inspection_date: str
    inspector_name:  str
    start_time:      str
    end_time:        str
    work_hours:      str
    item_count:      int = 0
    synced_at:       Optional[datetime] = None

    class Config:
        from_attributes = True


class B2FInspectionItemOut(BaseModel):
    ragic_id:       str
    batch_ragic_id: str
    seq_no:         int
    item_name:      str
    result_raw:     str
    result_status:  str
    abnormal_flag:  bool
    synced_at:      Optional[datetime] = None

    class Config:
        from_attributes = True


class B2FInspectionBatchKPI(BaseModel):
    total:            int   = 0
    normal:           int   = 0
    abnormal:         int   = 0
    pending:          int   = 0
    unchecked:        int   = 0
    completion_rate:  float = 0.0
    normal_rate:      float = 0.0


class StatusDistItem(BaseModel):
    status: str
    label:  str
    count:  int
    color:  str


class B2FInspectionBatchDetail(BaseModel):
    batch: B2FInspectionBatchOut
    kpi:   B2FInspectionBatchKPI
    items: List[B2FInspectionItemOut]


class B2FInspectionStats(BaseModel):
    latest_batch:        Optional[B2FInspectionBatchOut] = None
    latest_kpi:          Optional[B2FInspectionBatchKPI] = None
    recent_abnormal:     List[B2FInspectionItemOut] = []
    recent_pending:      List[B2FInspectionItemOut] = []
    status_distribution: List[StatusDistItem]       = []
    total_batches_7d:    int = 0
    abnormal_trend:      List[dict] = []
