/**
 * 倉庫庫存 TypeScript 型別定義
 */

export interface InventoryRecord {
  id: string
  inventory_no: string
  warehouse_code: string
  warehouse_name: string
  product_no: string
  product_name: string
  quantity: number
  category: string
  spec: string
  created_at: string
  updated_at: string
}

export interface InventoryStats {
  total_skus: number
  total_quantity: number
  zero_stock_count: number
  warehouse_count: number
}

export interface InventoryListResponse {
  success: boolean
  data: InventoryRecord[]
  meta: {
    total: number
    page: number
    per_page: number
  }
}

export interface InventorySingleResponse {
  success: boolean
  data: InventoryRecord
}

export interface InventoryStatsResponse {
  success: boolean
  data: InventoryStats
}

export interface InventoryFilters {
  warehouse_code?: string
  product_no?: string
  product_name?: string
  page?: number
  per_page?: number
}
