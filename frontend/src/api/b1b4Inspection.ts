import apiClient from '@/api/client'
import type {
  B1B4InspectionBatchListItem,
  B1B4InspectionBatchDetail,
  B1B4InspectionStats,
  B1B4InspectionItemHistory,
} from '@/types/b1b4Inspection'

const BASE = '/mall/b1b4-inspection'

export async function fetchB1B4Batches(opts?: {
  year_month?: string
  start_date?: string
  end_date?:   string
}): Promise<B1B4InspectionBatchListItem[]> {
  const params: Record<string, string> = {}
  if (opts?.year_month) params.year_month = opts.year_month
  if (opts?.start_date) params.start_date = opts.start_date
  if (opts?.end_date)   params.end_date   = opts.end_date
  const res = await apiClient.get<B1B4InspectionBatchListItem[]>(`${BASE}/batches`, { params })
  return res.data
}

export async function fetchB1B4BatchDetail(
  batchId: string,
  opts?: { status?: string; search?: string },
): Promise<B1B4InspectionBatchDetail> {
  const params: Record<string, string> = {}
  if (opts?.status) params.status = opts.status
  if (opts?.search) params.search = opts.search
  const res = await apiClient.get<B1B4InspectionBatchDetail>(`${BASE}/batches/${batchId}`, { params })
  return res.data
}

export async function fetchB1B4Stats(): Promise<B1B4InspectionStats> {
  const res = await apiClient.get<B1B4InspectionStats>(`${BASE}/stats`)
  return res.data
}

export async function syncB1B4FromRagic(): Promise<{ status: string; result: unknown }> {
  const res = await apiClient.post(`${BASE}/sync`)
  return res.data
}

export async function fetchB1B4ItemHistory(
  itemName: string,
  days = 30,
): Promise<B1B4InspectionItemHistory> {
  const res = await apiClient.get<B1B4InspectionItemHistory>(`${BASE}/items/item-history`, {
    params: { item_name: itemName, days },
  })
  return res.data
}
