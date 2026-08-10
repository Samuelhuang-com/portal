/**
 * 即時營運 API 封裝
 *
 * 規格書：docs/SPEC_realtime_operations.md §7
 * Prefix: /api/v1/realtime
 *
 * ⚠️ 與 `api/opera.ts` 完全獨立，不共用任何端點。
 * ⚠️ 前端**絕不直接打 OHIP** —— 憑證只在後端，用量必須集中控管。
 */
import apiClient from '@/api/client'
import type {
  ApiRevenueResult,
  CompareResult,
  LiveBusinessDate,
  LiveStatusResult,
  OhipCallLogResult,
} from '@/types/realtime'

const RT = '/realtime'

// ── 即時房況（OHIP API，2026-08-06）──────────────────────────────────────────
// ⚠️ 與 /opera/* 其他端點資料來源不同：這是即時打 OPERA Cloud，不是上傳落地的資料。

export async function fetchLiveStatus(params: {
  days_ahead?: number
  force?: boolean
} = {}): Promise<LiveStatusResult> {
  const res = await apiClient.get(`${RT}/status`, { params })
  return res.data
}

export async function fetchLiveBusinessDate(): Promise<LiveBusinessDate> {
  const res = await apiClient.get(`${RT}/business-date`)
  return res.data
}

export async function fetchOhipCallLogs(params: {
  limit?: number
  offset?: number
} = {}): Promise<OhipCallLogResult> {
  const res = await apiClient.get(`${RT}/logs`, { params })
  return res.data
}

/** API vs TXT 逐欄比對。⚠️ 不走快取，每次都會實際呼叫 OHIP。 */
export async function fetchApiTxtCompare(params: {
  days_back?: number
  days_ahead?: number
  property_code?: string
  tolerance?: number
} = {}): Promise<CompareResult> {
  const res = await apiClient.get(`${RT}/compare`, { params })
  return res.data
}

/** 營收與結構分析（非同步版 API）。⚠️ 單段約 3 秒，查一年約 12 秒。 */
export async function fetchApiRevenue(params: {
  start: string
  end: string
  group_by?: string[]
  force?: boolean
}): Promise<ApiRevenueResult> {
  const res = await apiClient.get(`${RT}/revenue`, {
    params,
    paramsSerializer: {
      // group_by 是可重複的 query，不能被序列化成 group_by[]=A
      indexes: null,
    },
  })
  return res.data
}
