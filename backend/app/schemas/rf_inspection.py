"""
整棟工務每日巡檢 - RF  Pydantic Schemas【寬表格 Pivot 架構】
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class RFInspectionBatchOut(BaseModel):
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


class RFInspectionItemOut(BaseModel):
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


class RFInspectionBatchKPI(BaseModel):
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


class RFInspectionBatchDetail(BaseModel):
    batch: RFInspectionBatchOut
    kpi:   RFInspectionBatchKPI
    items: List[RFInspectionItemOut]


class RFInspectionStats(BaseModel):
    latest_batch:        Optional[RFInspectionBatchOut] = None
    latest_kpi:          Optional[RFInspectionBatchKPI] = None
    recent_abnormal:     List[RFInspectionItemOut] = []
    recent_pending:      List[RFInspectionItemOut] = []
    status_distribution: List[StatusDistItem]      = []
    total_batches_7d:    int = 0
    abnormal_trend:      List[dict] = []
