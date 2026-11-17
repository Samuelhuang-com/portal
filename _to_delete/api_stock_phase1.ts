/**
 * 庫存管理 API（規格 docs/SPEC_stock_management.md）
 * Phase 1（2026-11-17）：Ragic 表單關聯、Ragic 採購單清單／明細
 */
import apiClient from '@/api/client'

const BASE = '/stock'

export type FormKey = 'purchase' | 'po' | 'claim'

export interface RagicFormCell {
  module: string
  form_name: string
  path: string
  url: string
  is_active: boolean
  records: number
  last_sync_at: string | null
}

export interface RagicFormRow {
  company: string
  company_alias: string
  department: string
  purchase: RagicFormCell | null
  po: RagicFormCell | null
  claim: RagicFormCell | null
}

export interface RagicFormsResp {
  companies: string[]
  company_alias: Record<string, string>
  rows: RagicFormRow[]
}

export interface PurchaseOrderRow {
  id: number
  company: string
  department: string
  po_no: string
  source_pr_no: string | null
  requester: string | null
  apply_date: string | null
  arrival_date: string | null
  purpose: string | null
  vendor_name: string | null
  subtotal: number | null
  tax: number | null
  total: number | null
  item_count: number
  is_ragic_deleted: boolean
  last_sync_at: string | null
  ragic_id: string
  ragic_url: string
  detail: Record<string, string>
}

export interface PurchaseOrderItem {
  id: number
  seq: number | null
  item_code: string | null
  product_name: string | null
  qty: number | null
  qty_raw: string | null
  unit: string | null
  unit_price: number | null
  amount: number | null
  remark: string | null
  item_dept: string | null
}

export interface PurchaseOrderDetail extends PurchaseOrderRow {
  items: PurchaseOrderItem[]
}

export interface PurchaseOrderQuery {
  company?: string
  department?: string
  keyword?: string
  include_deleted?: boolean
}

export const fetchRagicForms = () => apiClient.get<RagicFormsResp>(`${BASE}/ragic-forms`)

export const fetchPurchaseOrders = (params: PurchaseOrderQuery) =>
  apiClient.get<{ total: number; rows: PurchaseOrderRow[] }>(`${BASE}/purchase-orders`, { params })

export const fetchPurchaseOrder = (id: number) =>
  apiClient.get<PurchaseOrderDetail>(`${BASE}/purchase-orders/${id}`)
