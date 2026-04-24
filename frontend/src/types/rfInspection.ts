/**
 * 整棟工務每日巡檢 - RF  TypeScript 型別定義【寬表格 Pivot 架構】
 *
 * 架構說明：
 *   每次巡檢場次（RFInspectionBatch）對應一筆 Ragic Row（Sheet 1）
 *   場次內的設備欄位 pivot 成多筆 RFInspectionItem（動態數量）
 *   批次識別符（batch_id）= ragic_id（Ragic Row ID 字串）
 */

export type RFInspectionResultStatus = 'normal' | 'abnormal' | 'pending' | 'unchecked' | 'no_record'

// ── 巡檢場次 ─────────────────────────────────────────────────────────────────
export interface RFInspectionBatch {
  ragic_id:        string    // Ragic Row ID（作為場次唯一識別符，用於路由）
  inspection_date: string    // "2026/04/14"（從開始時間萃取）
  inspector_name:  string    // 巡檢人員
  start_time:      string    // 開始巡檢時間（原始值）
  end_time:        string    // 巡檢結束時間（原始值）
  work_hours:      string    // 工時計算
  item_count:      number    // 設備項目總數（動態，依 RF Sheet 欄位數量）
  synced_at?:      string | null
}

// ── 設備巡檢項目（一筆 = 一個設備欄位）──────────────────────────────────────
export interface RFInspectionItem {
  ragic_id:       string    // "{batch_ragic_id}_{seq_no}"
  batch_ragic_id: string    // 所屬場次 ragic_id
  seq_no:         number    // 項次
  item_name:      string    // 設備/項目名稱（Ragic 欄位名，動態偵測）
  result_raw:     string    // 原始值（正常/異常/待處理 或空白）
  result_status:  RFInspectionResultStatus
  abnormal_flag:  boolean
  synced_at?:     string | null
}

// ── KPI ───────────────────────────────────────────────────────────────────────
export interface RFInspectionBatchKPI {
  total:            number
  normal:           number
  abnormal:         number
  pending:          number
  unchecked:        number
  completion_rate:  number   // (normal+abnormal+pending) / total × 100
  normal_rate:      number   // normal / (total-unchecked) × 100
}

// ── 狀態分布 ──────────────────────────────────────────────────────────────────
export interface RFStatusDistItem {
  status: string
  label:  string
  count:  number
  color:  string
}

// ── 場次清單項目（含 KPI） ────────────────────────────────────────────────────
export interface RFInspectionBatchListItem {
  batch: RFInspectionBatch
  kpi:   RFInspectionBatchKPI
}

// ── 場次詳情 ──────────────────────────────────────────────────────────────────
export interface RFInspectionBatchDetail {
  batch: RFInspectionBatch
  kpi:   RFInspectionBatchKPI
  items: RFInspectionItem[]
}

// ── 異常趨勢 ──────────────────────────────────────────────────────────────────
export interface RFAbnormalTrendItem {
  date:           string
  abnormal_count: number
  has_record:     boolean
}

// ── 全站統計 ──────────────────────────────────────────────────────────────────
export interface RFInspectionStats {
  latest_batch:        RFInspectionBatch | null
  latest_kpi:          RFInspectionBatchKPI | null
  recent_abnormal:     RFInspectionItem[]
  recent_pending:      RFInspectionItem[]
  status_distribution: RFStatusDistItem[]
  total_batches_7d:    number
  abnormal_trend:      RFAbnormalTrendItem[]
}

// ── 設備歷史 ──────────────────────────────────────────────────────────────────
export interface RFInspectionDailySummary {
  inspection_date: string
  inspector_name:  string
  start_time:      string
  result_status:   RFInspectionResultStatus
  result_raw:      string
  abnormal_flag:   boolean
  has_record:      boolean
  is_today:        boolean
}

export interface RFInspectionItemHistory {
  item_name:     string
  daily_summary: RFInspectionDailySummary[]
  stats: {
    total_days:    number
    normal_days:   number
    abnormal_days: number
  }
}
