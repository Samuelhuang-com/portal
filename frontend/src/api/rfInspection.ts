import apiClient from '@/api/client'
import type {
  RFInspectionBatchListItem,
  RFInspectionBatchDetail,
  RFInspectionStats,
  RFInspectionItemHistory,
} from '@/types/rfInspection'

const BASE = '/mall/rf-inspection'

/** 巡檢批次清單 */
export async function fetchRFBatches(opts?: {
  year_month?: string    // "2026/04"
  start_date?: string   // "2026/04/01"
  end_date?:   string   // "2026/04/30"
}): Promise<RFInspectionBatchListItem[]> {
  const params: Record<string, string> = {}
  if (opts?.year_month) params.year_month = opts.year_month
  if (opts?.start_date) params.start_date = opts.start_date
  if (opts?.end_date)   params.end_date   = opts.end_date
  const res = await apiClient.get<RFInspectionBatchListItem[]>(`${BASE}/batches`, { params })
  return res.data
}

/** 單筆批次完整資料（含項目 + KPI） */
export async function fetchRFBatchDetail(
  batchId: string,
  opts?: { status?: string; search?: string },
): Promise<RFInspectionBatchDetail> {
  const params: Record<string, string> = {}
  if (opts?.status) params.status = opts.status
  if (opts?.search) params.search = opts.search
  const res = await apiClient.get<RFInspectionBatchDetail>(`${BASE}/batches/${batchId}`, { params })
  return res.data
}

/** 全站統計（Dashboard 資料來源） */
export async function fetchRFStats(): Promise<RFInspectionStats> {
  const res = await apiClient.get<RFInspectionStats>(`${BASE}/stats`)
  return res.data
}

/** 手動觸發 Ragic 同步 */
export async function syncRFFromRagic(): Promise<{ status: string; result: unknown }> {
  const res = await apiClient.post(`${BASE}/sync`)
  return res.data
}

/** 依巡檢項目名稱查詢近 N 日執行歷史 */
export async function fetchRFItemHistory(
  itemName: string,
  days = 30,
): Promise<RFInspectionItemHistory> {
  const res = await apiClient.get<RFInspectionItemHistory>(`${BASE}/items/item-history`, {
    params: { item_name: itemName, days },
  })
  return res.data
}
