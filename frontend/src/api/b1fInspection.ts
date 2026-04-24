import apiClient from '@/api/client'
import type {
  B1FInspectionBatchListItem,
  B1FInspectionBatchDetail,
  B1FInspectionStats,
  B1FInspectionItemHistory,
} from '@/types/b1fInspection'

const BASE = '/mall/b1f-inspection'

export async function fetchB1FBatches(opts?: {
  year_month?: string
  start_date?: string
  end_date?:   string
}): Promise<B1FInspectionBatchListItem[]> {
  const params: Record<string, string> = {}
  if (opts?.year_month) params.year_month = opts.year_month
  if (opts?.start_date) params.start_date = opts.start_date
  if (opts?.end_date)   params.end_date   = opts.end_date
  const res = await apiClient.get<B1FInspectionBatchListItem[]>(`${BASE}/batches`, { params })
  return res.data
}

export async function fetchB1FBatchDetail(
  batchId: string,
  opts?: { status?: string; search?: string },
): Promise<B1FInspectionBatchDetail> {
  const params: Record<string, string> = {}
  if (opts?.status) params.status = opts.status
  if (opts?.search) params.search = opts.search
  const res = await apiClient.get<B1FInspectionBatchDetail>(`${BASE}/batches/${batchId}`, { params })
  return res.data
}

export async function fetchB1FStats(): Promise<B1FInspectionStats> {
  const res = await apiClient.get<B1FInspectionStats>(`${BASE}/stats`)
  return res.data
}

export async function syncB1FFromRagic(): Promise<{ status: string; result: unknown }> {
  const res = await apiClient.post(`${BASE}/sync`)
  return res.data
}

export async function fetchB1FItemHistory(
  itemName: string,
  days = 30,
): Promise<B1FInspectionItemHistory> {
  const res = await apiClient.get<B1FInspectionItemHistory>(`${BASE}/items/item-history`, {
    params: { item_name: itemName, days },
  })
  return res.data
}
