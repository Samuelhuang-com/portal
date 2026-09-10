/**
 * 競品分析 API 封裝
 * 所有對 /api/v1/compset/* 的請求統一在此處理（不在元件內直接用 axios）
 *
 * 規格書：`docs/SPEC_compset_analysis.md` §8
 *
 * ⚠️ **不要在呼叫端帶 `subscriber_id`**，除非使用者真的在切換檢視對象。
 *    後端會自己解出當前使用者的訂閱；亂帶會拿到 403。
 */
import apiClient from '@/api/client'
import type {
  CadenceResult, DashboardResult, FetchLogRow, FetchRunResult, ImportResult,
  MatrixResult, QuotaGrantRow, RateDetail, SubscriberDetail, TrendResult,
} from '@/types/compset'

const BASE = '/compset'

/** 空字串與 undefined 一律不帶（比照 `api/ota.ts`）。 */
function toParams(input: Record<string, unknown> = {}): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  Object.entries(input).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') out[k] = v
  })
  return out
}

// ── 查詢 ────────────────────────────────────────────────────────────────
export async function fetchDashboard(subscriberId?: number): Promise<DashboardResult> {
  const { data } = await apiClient.get(`${BASE}/dashboard`,
    { params: toParams({ subscriber_id: subscriberId }) })
  return data
}

export async function fetchMatrix(params: {
  stayFrom: string; stayTo: string; snapshotDate?: string; subscriberId?: number
}): Promise<MatrixResult> {
  const { data } = await apiClient.get(`${BASE}/rates/matrix`, {
    params: toParams({
      stay_from: params.stayFrom, stay_to: params.stayTo,
      snapshot_date: params.snapshotDate, subscriber_id: params.subscriberId,
    }),
  })
  return data
}

export async function fetchTrend(params: {
  stayDate: string; snapshotFrom?: string; snapshotTo?: string; subscriberId?: number
}): Promise<TrendResult> {
  const { data } = await apiClient.get(`${BASE}/rates/trend`, {
    params: toParams({
      stay_date: params.stayDate, snapshot_from: params.snapshotFrom,
      snapshot_to: params.snapshotTo, subscriber_id: params.subscriberId,
    }),
  })
  return data
}

export async function fetchRateDetail(snapshotId: number): Promise<RateDetail> {
  const { data } = await apiClient.get(`${BASE}/rates/detail`,
    { params: { snapshot_id: snapshotId } })
  return data
}

export async function fetchLogs(limit = 50, subscriberId?: number)
  : Promise<{ items: FetchLogRow[] }> {
  const { data } = await apiClient.get(`${BASE}/logs`,
    { params: toParams({ limit, subscriber_id: subscriberId }) })
  return data
}

// ── 競爭組 ──────────────────────────────────────────────────────────────
export async function fetchHotels(subscriberId?: number) {
  const { data } = await apiClient.get(`${BASE}/hotels`,
    { params: toParams({ subscriber_id: subscriberId }) })
  return data
}

export async function createHotel(payload: Record<string, unknown>) {
  const { data } = await apiClient.post(`${BASE}/hotels`, payload)
  return data
}

export async function updateHotel(id: number, payload: Record<string, unknown>) {
  const { data } = await apiClient.put(`${BASE}/hotels/${id}`, payload)
  return data
}

export async function deleteHotel(id: number) {
  const { data } = await apiClient.delete(`${BASE}/hotels/${id}`)
  return data
}

// ── 訂閱與配額 ──────────────────────────────────────────────────────────
export async function fetchSubscribers(): Promise<{ items: SubscriberDetail[] }> {
  const { data } = await apiClient.get(`${BASE}/subscribers`)
  return data
}

export async function updateSubscriber(id: number, payload: Record<string, unknown>) {
  const { data } = await apiClient.put(`${BASE}/subscribers/${id}`, payload)
  return data
}

/**
 * 手動加發一次性額度。
 *
 * ⚠️ 後端會擋「對自己所屬的訂閱加發」（防提權 P-1），
 *    前端只是不顯示按鈕，**不是**安全機制。
 * ⚠️ `reason` 必填 —— 加發是花錢的動作，沒有理由事後無法稽核。
 */
export async function grantQuota(id: number, grantedQty: number, reason: string) {
  const { data } = await apiClient.post(`${BASE}/subscribers/${id}/grant-quota`,
    { granted_qty: grantedQty, reason })
  return data
}

export async function fetchGrants(id: number): Promise<{ items: QuotaGrantRow[] }> {
  const { data } = await apiClient.get(`${BASE}/subscribers/${id}/grants`)
  return data
}

// ── 抓取節奏 ────────────────────────────────────────────────────────────
export async function fetchCadence(subscriberId?: number): Promise<CadenceResult> {
  const { data } = await apiClient.get(`${BASE}/settings/cadence`,
    { params: toParams({ subscriber_id: subscriberId }) })
  return data
}

/**
 * 修改抓取節奏。
 *
 * ⚠️ 回應可能帶 `data_break_warning`（改了擷取參數 ＝ 前後期價格不可比）
 *    與 `over_quota_warning`（每月估算次數超過配額）。**兩個都要顯示給使用者**。
 */
export async function saveCadence(payload: Record<string, unknown>,
                                  subscriberId?: number): Promise<CadenceResult> {
  const { data } = await apiClient.put(`${BASE}/settings/cadence`, payload,
    { params: toParams({ subscriber_id: subscriberId }) })
  return data
}

// ── 手動觸發與重算 ──────────────────────────────────────────────────────
/** ⚠️ **會真的花錢**（每次查詢都扣配額）。按鈕要有二次確認。 */
export async function runFetch(tiers?: string[], subscriberId?: number)
  : Promise<FetchRunResult> {
  const { data } = await apiClient.post(`${BASE}/fetch/run`, { tiers: tiers ?? [] },
    { params: toParams({ subscriber_id: subscriberId }) })
  return data
}

/** 重算彙總快取。**不打外部 API、不花錢**，數字怪怪的先按這個。 */
export async function recomputeStats(payload: Record<string, unknown> = {},
                                     subscriberId?: number) {
  const { data } = await apiClient.post(`${BASE}/stats/recompute`, payload,
    { params: toParams({ subscriber_id: subscriberId }) })
  return data
}

// ── CSV 備援 ────────────────────────────────────────────────────────────
export async function downloadImportTemplate(): Promise<Blob> {
  const { data } = await apiClient.get(`${BASE}/import/template`,
    { responseType: 'blob' })
  return data
}

export async function importRatesCsv(file: File, subscriberId?: number)
  : Promise<ImportResult> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await apiClient.post(`${BASE}/import/upload`, form, {
    params: toParams({ subscriber_id: subscriberId }),
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
