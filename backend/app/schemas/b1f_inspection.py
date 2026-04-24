"""
整棟工務每日巡檢 - B1F  Pydantic Schemas【寬表格 Pivot 架構】
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class B1FInspectionBatchOut(BaseModel):
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


class B1FInspectionItemOut(BaseModel):
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


class B1FInspectionBatchKPI(BaseModel):
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


class B1FInspectionBatchDetail(BaseModel):
    batch: B1FInspectionBatchOut
    kpi:   B1FInspectionBatchKPI
    items: List[B1FInspectionItemOut]


class B1FInspectionStats(BaseModel):
    latest_batch:        Optional[B1FInspectionBatchOut] = None
    latest_kpi:          Optional[B1FInspectionBatchKPI] = None
    recent_abnormal:     List[B1FInspectionItemOut] = []
    recent_pending:      List[B1FInspectionItemOut] = []
    status_distribution: List[StatusDistItem]       = []
    total_batches_7d:    int = 0
    abnormal_trend:      List[dict] = []
