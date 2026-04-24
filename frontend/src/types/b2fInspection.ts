/**
 * 整棟工務每日巡檢 - B2F  TypeScript 型別定義【寬表格 Pivot 架構】
 *
 * 對應 Ragic Sheet 3（full-building-inspection/3）
 * 設備欄位由同步服務動態偵測，數量依 Sheet 實際欄位而定
 */

export type B2FInspectionResultStatus = 'normal' | 'abnormal' | 'pending' | 'unchecked' | 'no_record'

export interface B2FInspectionBatch {
  ragic_id:        string
  inspection_date: string
  inspector_name:  string
  start_time:      string
  end_time:        string
  work_hours:      string
  item_count:      number
  synced_at?:      string | null
}

export interface B2FInspectionItem {
  ragic_id:       string
  batch_ragic_id: string
  seq_no:         number
  item_name:      string
  result_raw:     string
  result_status:  B2FInspectionResultStatus
  abnormal_flag:  boolean
  synced_at?:     string | null
}

export interface B2FInspectionBatchKPI {
  total:            number
  normal:           number
  abnormal:         number
  pending:          number
  unchecked:        number
  completion_rate:  number
  normal_rate:      number
}

export interface B2FStatusDistItem {
  status: string
  label:  string
  count:  number
  color:  string
}

export interface B2FInspectionBatchListItem {
  batch: B2FInspectionBatch
  kpi:   B2FInspectionBatchKPI
}

export interface B2FInspectionBatchDetail {
  batch: B2FInspectionBatch
  kpi:   B2FInspectionBatchKPI
  items: B2FInspectionItem[]
}

export interface B2FAbnormalTrendItem {
  date:           string
  abnormal_count: number
  has_record:     boolean
}

export interface B2FInspectionStats {
  latest_batch:        B2FInspectionBatch | null
  latest_kpi:          B2FInspectionBatchKPI | null
  recent_abnormal:     B2FInspectionItem[]
  recent_pending:      B2FInspectionItem[]
  status_distribution: B2FStatusDistItem[]
  total_batches_7d:    number
  abnormal_trend:      B2FAbnormalTrendItem[]
}

export interface B2FInspectionDailySummary {
  inspection_date: string
  inspector_name:  string
  start_time:      string
  result_status:   B2FInspectionResultStatus
  result_raw:      string
  abnormal_flag:   boolean
  has_record:      boolean
  is_today:        boolean
}

export interface B2FInspectionItemHistory {
  item_name:     string
  daily_summary: B2FInspectionDailySummary[]
  stats: {
    total_days:    number
    normal_days:   number
    abnormal_days: number
  }
}
