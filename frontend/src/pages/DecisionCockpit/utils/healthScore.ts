/**
 * 健康分數計算工具 — 決策駕駛艙
 *
 * 規格來源：docs/decision-cockpit/HEALTH_SCORE_SPEC.md
 *
 * ⚠️ 所有權重為「草案」，業主確認後修改此常數即可，無需改邏輯程式。
 */

// ── 可調整常數（業主確認後固化）────────────────────────────────────────────────

/** 健康分數四維度權重（合計必須 = 1.0）*/
export const HEALTH_SCORE_WEIGHTS = {
  completion_rate:   0.40,   // 完成率權重
  overdue_control:   0.25,   // 逾期控制（反向：逾期越低越好）
  anomaly_control:   0.20,   // 異常管理（反向：異常越低越好）
  data_completeness: 0.15,   // 資料完整度
} as const

/** 燈號閾值 */
export const HEALTH_THRESHOLDS = {
  green:  80,   // ≥ 80 → 綠燈
  yellow: 60,   // 60 ~ 79 → 黃燈
               //  < 60 → 紅燈
} as const

/** 集團健康分數各模組占比（合計 = 1.0）*/
export const GROUP_WEIGHTS = {
  hotel:  0.40,
  mall:   0.40,
  repair: 0.20,
} as const

/** 工務健康各來源占比（合計 = 1.0）*/
export const REPAIR_WEIGHTS = {
  dazhi:  0.60,
  luqun:  0.40,
} as const

// ── 型別定義 ─────────────────────────────────────────────────────────────────

export type TrafficLight = 'green' | 'yellow' | 'red' | 'gray'

export interface HealthScoreInput {
  /** 0~100 完成率（已有完成率直接傳；或由 completed/total 計算後傳入）*/
  completion_rate_pct: number
  /** 0~100 逾期率（反向指標：越低越好；無資料傳 0）*/
  overdue_rate_pct: number
  /** 0~100 異常率（反向指標：越低越好；無資料傳 0）*/
  anomaly_rate_pct: number
  /** 0~100 資料完整度（無資料傳 100，不納入扣分）*/
  data_completeness_pct: number
}

export interface ModuleHealthInput {
  total:     number   // 本期總件數
  completed: number   // 已完成件數
  overdue:   number   // 逾期未完成件數（不確定時傳 uncompleted）
  anomaly:   number   // 異常標記件數（無資料傳 0）
  has_assignee_pct?: number  // 有負責人的比例（無資料傳 100）
}

// ── 核心計算函式 ─────────────────────────────────────────────────────────────

/**
 * 計算健康分數（0~100）
 * 所有輸入已是 0~100 的百分比值
 */
export function calcHealthScore(input: HealthScoreInput): number {
  const { completion_rate, overdue_control, anomaly_control, data_completeness } = HEALTH_SCORE_WEIGHTS
  const score =
    input.completion_rate_pct   * completion_rate
    + (100 - input.overdue_rate_pct)  * overdue_control
    + (100 - input.anomaly_rate_pct)  * anomaly_control
    + input.data_completeness_pct     * data_completeness
  return Math.max(0, Math.min(100, Math.round(score)))
}

/**
 * 從原始模組數據自動計算健康分數
 */
export function calcModuleHealth(input: ModuleHealthInput): number | null {
  if (input.total === 0) return null   // 無資料 → 灰燈

  const completion_rate_pct  = (input.completed / input.total) * 100
  const overdue_rate_pct     = (input.overdue   / input.total) * 100
  const anomaly_rate_pct     = (input.anomaly   / input.total) * 100
  const data_completeness_pct = input.has_assignee_pct ?? 100

  return calcHealthScore({
    completion_rate_pct,
    overdue_rate_pct,
    anomaly_rate_pct,
    data_completeness_pct,
  })
}

/**
 * 計算工務健康分數（大直 × 0.60 + 商場 × 0.40）
 * 任一來源為 null 時，僅用另一來源，並在 UI 標示「部分計算」
 */
export function calcRepairHealth(
  dazhiScore: number | null,
  luqunScore: number | null,
): { score: number | null; partial: boolean } {
  if (dazhiScore === null && luqunScore === null) return { score: null, partial: false }

  if (dazhiScore === null) return { score: luqunScore, partial: true }
  if (luqunScore === null) return { score: dazhiScore, partial: true }

  const score = Math.round(
    dazhiScore * REPAIR_WEIGHTS.dazhi + luqunScore * REPAIR_WEIGHTS.luqun
  )
  return { score, partial: false }
}

/**
 * 計算集團健康分數（飯店 × 0.40 + 商場 × 0.40 + 工務 × 0.20）
 * 任一模組為 null 時，按剩餘比例重新標準化，並標示「部分計算」
 */
export function calcGroupHealth(
  hotelScore:  number | null,
  mallScore:   number | null,
  repairScore: number | null,
): { score: number | null; partial: boolean } {
  const entries: Array<{ score: number; weight: number }> = []
  if (hotelScore  !== null) entries.push({ score: hotelScore,  weight: GROUP_WEIGHTS.hotel  })
  if (mallScore   !== null) entries.push({ score: mallScore,   weight: GROUP_WEIGHTS.mall   })
  if (repairScore !== null) entries.push({ score: repairScore, weight: GROUP_WEIGHTS.repair })

  if (entries.length === 0) return { score: null, partial: false }

  const totalWeight = entries.reduce((s, e) => s + e.weight, 0)
  const raw = entries.reduce((s, e) => s + e.score * e.weight, 0) / totalWeight
  return {
    score:   Math.round(raw),
    partial: entries.length < 3,
  }
}

// ── 燈號判斷 ─────────────────────────────────────────────────────────────────

/** score 為 null → 'gray'；否則依閾值回傳燈號 */
export function getTrafficLight(score: number | null): TrafficLight {
  if (score === null) return 'gray'
  if (score >= HEALTH_THRESHOLDS.green)  return 'green'
  if (score >= HEALTH_THRESHOLDS.yellow) return 'yellow'
  return 'red'
}

export const TRAFFIC_LIGHT_COLOR: Record<TrafficLight, string> = {
  green:  '#52c41a',
  yellow: '#faad14',
  red:    '#ff4d4f',
  gray:   '#8c8c8c',
}

export const TRAFFIC_LIGHT_LABEL: Record<TrafficLight, string> = {
  green:  '正常',
  yellow: '需注意',
  red:    '警告',
  gray:   '資料準備中',
}

/** 將數字 score 轉成帶顏色的顯示字串 */
export function formatScore(score: number | null): string {
  return score === null ? '—' : `${score}`
}
