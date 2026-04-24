/**
 * 整棟工務每日巡檢 - B4F  TypeScript 型別定義【寬表格 Pivot 架構】
 *
 * 架構說明：
 *   每次巡檢場次（InspectionBatch）對應一筆 Ragic Row
 *   場次內的 35 個設備欄位 pivot 成 35 筆 InspectionItem
 *   批次識別符（batch_id）= ragic_id（Ragic Row ID 字串）
 */

export type InspectionResultStatus = 'normal' | 'abnormal' | 'pending' | 'unchecked' | 'no_record'

// ── 巡檢場次 ─────────────────────────────────────────────────────────────────
export interface InspectionBatch {
  ragic_id:        string    // Ragic Row ID（作為場次唯一識別符，用於路由）
  inspection_date: string    // "2026/04/14"（從開始時間萃取）
  inspector_name:  string    // 巡檢人員
  start_time:      string    // 開始巡檢時間（原始值）
  end_time:        string    // 巡檢結束時間（原始值）
  work_hours:      string    // 工時計算（如 "2 分鐘"）
  item_count:      number    // 設備項目總數（固定 35 筆）
  synced_at?:      string | null
}

// ── 設備巡檢項目（一筆 = 一個設備欄位）──────────────────────────────────────
export interface InspectionItem {
  ragic_id:       string    // "{batch_ragic_id}_{seq_no}"
  batch_ragic_id: string    // 所屬場次 ragic_id
  seq_no:         number    // 項次（1–35）
  item_name:      string    // 設備/項目名稱（Ragic 欄位名）
  result_raw:     string    // 原始值（正常/異常/待處理 或空白）
  result_status:  InspectionResultStatus
  abnormal_flag:  boolean
  synced_at?:     string | null
}

// ── KPI ───────────────────────────────────────────────────────────────────────
export interface InspectionBatchKPI {
  total:            number
  normal:           number
  abnormal:         number
  pending:          number
  unchecked:        number
  completion_rate:  number   // (normal+abnormal+pending) / total × 100
  normal_rate:      number   // normal / (total-unchecked) × 100
}

// ── 狀態分布 ──────────────────────────────────────────────────────────────────
export interface StatusDistItem {
  status: string
  label:  string
  count:  number
  color:  string
}

// ── 場次清單項目（含 KPI） ────────────────────────────────────────────────────
export interface InspectionBatchListItem {
  batch: InspectionBatch
  kpi:   InspectionBatchKPI
}

// ── 場次詳情 ──────────────────────────────────────────────────────────────────
export interface InspectionBatchDetail {
  batch: InspectionBatch
  kpi:   InspectionBatchKPI
  items: InspectionItem[]
}

// ── 異常趨勢 ──────────────────────────────────────────────────────────────────
export interface AbnormalTrendItem {
  date:           string
  abnormal_count: number
  has_record:     boolean
}

// ── 全站統計 ──────────────────────────────────────────────────────────────────
export interface InspectionStats {
  latest_batch:        InspectionBatch | null
  latest_kpi:          InspectionBatchKPI | null
  recent_abnormal:     InspectionItem[]
  recent_pending:      InspectionItem[]
  status_distribution: StatusDistItem[]
  total_batches_7d:    number
  abnormal_trend:      AbnormalTrendItem[]
}

// ── 設備歷史 ──────────────────────────────────────────────────────────────────
export interface InspectionDailySummary {
  inspection_date: string
  inspector_name:  string
  start_time:      string
  result_status:   InspectionResultStatus
  result_raw:      string
  abnormal_flag:   boolean
  has_record:      boolean
  is_today:        boolean
}

export interface InspectionItemHistory {
  item_name:     string
  daily_summary: InspectionDailySummary[]
  stats: {
    total_days:    number
    normal_days:   number
    abnormal_days: number
  }
}
