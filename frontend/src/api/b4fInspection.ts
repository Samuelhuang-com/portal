import apiClient from '@/api/client'
import type {
  InspectionBatchListItem,
  InspectionBatchDetail,
  InspectionStats,
  InspectionItemHistory,
} from '@/types/b4fInspection'

const BASE = '/mall/b4f-inspection'

/** 巡檢批次清單 */
export async function fetchB4FBatches(opts?: {
  year_month?: string    // "2026/04"
  start_date?: string   // "2026/04/01"
  end_date?:   string   // "2026/04/30"
}): Promise<InspectionBatchListItem[]> {
  const params: Record<string, string> = {}
  if (opts?.year_month) params.year_month = opts.year_month
  if (opts?.start_date) params.start_date = opts.start_date
  if (opts?.end_date)   params.end_date   = opts.end_date
  const res = await apiClient.get<InspectionBatchListItem[]>(`${BASE}/batches`, { params })
  return res.data
}

/** 單筆批次完整資料（含項目 + KPI） */
export async function fetchB4FBatchDetail(
  batchId: string,
  opts?: { status?: string; search?: string },
): Promise<InspectionBatchDetail> {
  const params: Record<string, string> = {}
  if (opts?.status) params.status = opts.status
  if (opts?.search) params.search = opts.search
  const res = await apiClient.get<InspectionBatchDetail>(`${BASE}/batches/${batchId}`, { params })
  return res.data
}

/** 全站統計（Dashboard 資料來源） */
export async function fetchB4FStats(): Promise<InspectionStats> {
  const res = await apiClient.get<InspectionStats>(`${BASE}/stats`)
  return res.data
}

/** 手動觸發 Ragic 同步 */
export async function syncB4FFromRagic(): Promise<{ status: string; result: unknown }> {
  const res = await apiClient.post(`${BASE}/sync`)
  return res.data
}

/** 依巡檢項目名稱查詢近 N 日執行歷史 */
export async function fetchB4FItemHistory(
  itemName: string,
  days = 30,
): Promise<InspectionItemHistory> {
  const res = await apiClient.get<InspectionItemHistory>(`${BASE}/items/item-history`, {
    params: { item_name: itemName, days },
  })
  return res.data
}
