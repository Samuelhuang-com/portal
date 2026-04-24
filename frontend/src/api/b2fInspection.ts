import apiClient from '@/api/client'
import type {
  B2FInspectionBatchListItem,
  B2FInspectionBatchDetail,
  B2FInspectionStats,
  B2FInspectionItemHistory,
} from '@/types/b2fInspection'

const BASE = '/mall/b2f-inspection'

export async function fetchB2FBatches(opts?: {
  year_month?: string
  start_date?: string
  end_date?:   string
}): Promise<B2FInspectionBatchListItem[]> {
  const params: Record<string, string> = {}
  if (opts?.year_month) params.year_month = opts.year_month
  if (opts?.start_date) params.start_date = opts.start_date
  if (opts?.end_date)   params.end_date   = opts.end_date
  const res = await apiClient.get<B2FInspectionBatchListItem[]>(`${BASE}/batches`, { params })
  return res.data
}

export async function fetchB2FBatchDetail(
  batchId: string,
  opts?: { status?: string; search?: string },
): Promise<B2FInspectionBatchDetail> {
  const params: Record<string, string> = {}
  if (opts?.status) params.status = opts.status
  if (opts?.search) params.search = opts.search
  const res = await apiClient.get<B2FInspectionBatchDetail>(`${BASE}/batches/${batchId}`, { params })
  return res.data
}

export async function fetchB2FStats(): Promise<B2FInspectionStats> {
  const res = await apiClient.get<B2FInspectionStats>(`${BASE}/stats`)
  return res.data
}

export async function syncB2FFromRagic(): Promise<{ status: string; result: unknown }> {
  const res = await apiClient.post(`${BASE}/sync`)
  return res.data
}

export async function fetchB2FItemHistory(
  itemName: string,
  days = 30,
): Promise<B2FInspectionItemHistory> {
  const res = await apiClient.get<B2FInspectionItemHistory>(`${BASE}/items/item-history`, {
    params: { item_name: itemName, days },
  })
  return res.data
}
