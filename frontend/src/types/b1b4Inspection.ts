/**
 * 整棟工務每日巡檢 - B1B4  TypeScript 型別定義【寬表格 Pivot 架構】
 *
 * 對應 Ragic Sheet 4（full-building-inspection/4）
 * 設備欄位由同步服務動態偵測，數量依 Sheet 實際欄位而定
 */

export type B1B4InspectionResultStatus = 'normal' | 'abnormal' | 'pending' | 'unchecked' | 'no_record'

export interface B1B4InspectionBatch {
  ragic_id:        string
  inspection_date: string
  inspector_name:  string
  start_time:      string
  end_time:        string
  work_hours:      string
  item_count:      number
  synced_at?:      string | null
}

export interface B1B4InspectionItem {
  ragic_id:       string
  batch_ragic_id: string
  seq_no:         number
  item_name:      string
  result_raw:     string
  result_status:  B1B4InspectionResultStatus
  abnormal_flag:  boolean
  synced_at?:     string | null
}

export interface B1B4InspectionBatchKPI {
  total:            number
  normal:           number
  abnormal:         number
  pending:          number
  unchecked:        number
  completion_rate:  number
  normal_rate:      number
}

export interface B1B4StatusDistItem {
  status: string
  label:  string
  count:  number
  color:  string
}

export interface B1B4InspectionBatchListItem {
  batch: B1B4InspectionBatch
  kpi:   B1B4InspectionBatchKPI
}

export interface B1B4InspectionBatchDetail {
  batch: B1B4InspectionBatch
  kpi:   B1B4InspectionBatchKPI
  items: B1B4InspectionItem[]
}

export interface B1B4AbnormalTrendItem {
  date:           string
  abnormal_count: number
  has_record:     boolean
}

export interface B1B4InspectionStats {
  latest_batch:        B1B4InspectionBatch | null
  latest_kpi:          B1B4InspectionBatchKPI | null
  recent_abnormal:     B1B4InspectionItem[]
  recent_pending:      B1B4InspectionItem[]
  status_distribution: B1B4StatusDistItem[]
  total_batches_7d:    number
  abnormal_trend:      B1B4AbnormalTrendItem[]
}

export interface B1B4InspectionDailySummary {
  inspection_date: string
  inspector_name:  string
  start_time:      string
  result_status:   B1B4InspectionResultStatus
  result_raw:      string
  abnormal_flag:   boolean
  has_record:      boolean
  is_today:        boolean
}

export interface B1B4InspectionItemHistory {
  item_name:     string
  daily_summary: B1B4InspectionDailySummary[]
  stats: {
    total_days:    number
    normal_days:   number
    abnormal_days: number
  }
}
