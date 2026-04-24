/**
 * 整棟工務每日巡檢 - B1F  TypeScript 型別定義【寬表格 Pivot 架構】
 *
 * 對應 Ragic Sheet 4（full-building-inspection/4）
 * 設備欄位由同步服務動態偵測，數量依 Sheet 實際欄位而定
 */

export type B1FInspectionResultStatus = 'normal' | 'abnormal' | 'pending' | 'unchecked' | 'no_record'

export interface B1FInspectionBatch {
  ragic_id:        string
  inspection_date: string
  inspector_name:  string
  start_time:      string
  end_time:        string
  work_hours:      string
  item_count:      number
  synced_at?:      string | null
}

export interface B1FInspectionItem {
  ragic_id:       string
  batch_ragic_id: string
  seq_no:         number
  item_name:      string
  result_raw:     string
  result_status:  B1FInspectionResultStatus
  abnormal_flag:  boolean
  synced_at?:     string | null
}

export interface B1FInspectionBatchKPI {
  total:            number
  normal:           number
  abnormal:         number
  pending:          number
  unchecked:        number
  completion_rate:  number
  normal_rate:      number
}

export interface B1FStatusDistItem {
  status: string
  label:  string
  count:  number
  color:  string
}

export interface B1FInspectionBatchListItem {
  batch: B1FInspectionBatch
  kpi:   B1FInspectionBatchKPI
}

export interface B1FInspectionBatchDetail {
  batch: B1FInspectionBatch
  kpi:   B1FInspectionBatchKPI
  items: B1FInspectionItem[]
}

export interface B1FAbnormalTrendItem {
  date:           string
  abnormal_count: number
  has_record:     boolean
}

export interface B1FInspectionStats {
  latest_batch:        B1FInspectionBatch | null
  latest_kpi:          B1FInspectionBatchKPI | null
  recent_abnormal:     B1FInspectionItem[]
  recent_pending:      B1FInspectionItem[]
  status_distribution: B1FStatusDistItem[]
  total_batches_7d:    number
  abnormal_trend:      B1FAbnormalTrendItem[]
}

export interface B1FInspectionDailySummary {
  inspection_date: string
  inspector_name:  string
  start_time:      string
  result_status:   B1FInspectionResultStatus
  result_raw:      string
  abnormal_flag:   boolean
  has_record:      boolean
  is_today:        boolean
}

export interface B1FInspectionItemHistory {
  item_name:     string
  daily_summary: B1FInspectionDailySummary[]
  stats: {
    total_days:    number
    normal_days:   number
    abnormal_days: number
  }
}
