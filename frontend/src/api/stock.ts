/**
 * 庫存管理 API（規格 docs/SPEC_stock_management.md §8）
 * Phase 2（2026-11-17）：倉庫、料號庫存設定、庫存總覽、庫存卡、期初開帳
 * 所有請求帶 co（公司代碼 CH／OU／HO），後端依 stock_company_<代碼> 權限檢查
 */
import apiClient from '@/api/client'

const BASE = '/stock'

export interface StockCompany { code: string; name: string }
export interface StockDepartment { id: string; name: string; company_name: string }

export interface Warehouse {
  id: number
  name: string
  department_id: string | null
  department_name: string | null
  keeper_name: string | null
  status: 'active' | 'inactive' | 'counting'
  notes: string | null
  issue_requires_approval: boolean
  item_count: number
  amount: number | null
  has_moves: boolean
}

export interface WarehouseInput {
  name: string
  department_id?: string | null
  keeper_name?: string | null
  status: 'active' | 'inactive'
  issue_requires_approval?: boolean
  notes?: string | null
}

export interface StockItem {
  id: number
  item_code: string
  item_name: string
  spec: string | null
  unit: string | null
  category_id: number | null
  category: string
  min_stock: number | null
  max_stock: number | null
  unit_price: number | null
  is_active: boolean
  is_stock_item: boolean
  purchase_unit: string | null
  unit_ratio: number
  abc_class: string | null
  has_setting: boolean
  total_qty: number | null
}

export interface BalanceRow {
  warehouse_id: number
  warehouse_name: string
  warehouse_status: string
  item_id: number
  item_code: string
  item_name: string
  spec: string | null
  unit: string | null
  category: string
  qty: number
  reserved_qty: number
  available_qty: number
  avg_cost: number
  amount: number
  min_stock: number | null
  max_stock: number | null
  last_move_at: string | null
  is_low: boolean
  is_over: boolean
  is_dead: boolean
}

export interface BalanceResp {
  summary: { rows: number; items: number; amount: number; low: number; dead: number }
  rows: BalanceRow[]
  data_end: string | null
  dead_days: number
}

export interface StockCardMove {
  id: number
  moved_at: string
  move_type: string
  move_type_label: string
  source_type: string
  source_id: string | null
  source_no: string | null
  in_qty: number | null
  out_qty: number | null
  unit_cost: number
  amount: number
  balance_qty: number
  balance_amount: number
  note: string | null
  created_by: string | null
  created_at: string | null
}

export interface StockCardResp {
  warehouse: { id: number; name: string; department_name: string | null }
  item: { id: number; item_code: string; item_name: string; spec: string | null; unit: string | null; min_stock: number | null; max_stock: number | null }
  balance: { qty: number; reserved_qty: number; avg_cost: number; amount: number } | null
  moves: StockCardMove[]
}

export interface Opening {
  id: number
  doc_no: string
  warehouse_id: number
  warehouse_name: string
  opening_date: string
  status: 'posted' | 'voided'
  note: string | null
  line_count: number
  total_amount: number | null
  created_by: string | null
  created_at: string | null
  voided_by: string | null
  void_reason: string | null
  lines?: { item_id: number; item_code: string; item_name: string; unit: string | null; qty: number; unit_cost: number; amount: number }[]
}

const co = (code: string) => ({ co: code })

export const fetchStockCompanies = () => apiClient.get<{ default: string; companies: StockCompany[] }>(`${BASE}/companies`)
export const fetchStockDepartments = (code: string) => apiClient.get<StockDepartment[]>(`${BASE}/departments`, { params: co(code) })
export const fetchCategories = (code: string) => apiClient.get<{ id: number; label: string }[]>(`${BASE}/categories`, { params: co(code) })

export const fetchWarehouses = (code: string) => apiClient.get<Warehouse[]>(`${BASE}/warehouses`, { params: co(code) })
export const createWarehouse = (code: string, body: WarehouseInput) => apiClient.post(`${BASE}/warehouses`, body, { params: co(code) })
export const updateWarehouse = (code: string, id: number, body: WarehouseInput) =>
  apiClient.put(`${BASE}/warehouses/${id}`, body, { params: co(code) })

export const fetchStockItems = (code: string, params: { keyword?: string; category_id?: number; stock_only?: boolean } = {}) =>
  apiClient.get<StockItem[]>(`${BASE}/items`, { params: { ...co(code), ...params } })
export const updateItemSetting = (code: string, id: number, body: { is_stock_item: boolean; purchase_unit?: string | null; unit_ratio: number; abc_class?: string | null }) =>
  apiClient.put(`${BASE}/items/${id}/setting`, body, { params: co(code) })
export const bulkItemSetting = (code: string, body: { item_ids?: number[]; category_id?: number; is_stock_item: boolean }) =>
  apiClient.post<{ updated: number; skipped_with_stock: string[] }>(`${BASE}/items/settings/bulk`, body, { params: co(code) })

export const fetchBalance = (code: string, params: { warehouse_id?: number; keyword?: string; category_id?: number; low_only?: boolean; dead_only?: boolean; include_zero?: boolean } = {}) =>
  apiClient.get<BalanceResp>(`${BASE}/balance`, { params: { ...co(code), ...params } })
export const fetchStockCard = (code: string, warehouse_id: number, item_id: number) =>
  apiClient.get<StockCardResp>(`${BASE}/stock-card`, { params: { ...co(code), warehouse_id, item_id } })
export const rebuildBalances = (code: string) =>
  apiClient.post<{ balances: number; negative_points: string[] }>(`${BASE}/balances/rebuild`, null, { params: co(code) })

export const fetchOpenings = (code: string) => apiClient.get<Opening[]>(`${BASE}/openings`, { params: co(code) })
export const fetchOpening = (code: string, id: number) => apiClient.get<Opening>(`${BASE}/openings/${id}`, { params: co(code) })
export const checkOpening = (code: string, warehouse_id: number) =>
  apiClient.get<{ allowed: boolean; reason: string }>(`${BASE}/openings-check/${warehouse_id}`, { params: co(code) })
export const createOpening = (code: string, body: { warehouse_id: number; opening_date: string; note?: string; lines: { item_id: number; qty: number; unit_cost: number }[] }) =>
  apiClient.post<{ id: number; doc_no: string; total_amount: number }>(`${BASE}/openings`, body, { params: co(code) })
export const voidOpening = (code: string, id: number, reason: string) =>
  apiClient.post(`${BASE}/openings/${id}/void`, { reason }, { params: co(code) })

// ── Phase 3 進貨匯入（§6）─────────────────────────────────────────────────────

export type ImportStatus = 'pending' | 'partial' | 'done' | 'non_stock' | 'pre_opening' | 'linked_po'

export interface ImportLine {
  id: number
  source_type: 'ragic_po' | 'ragic_claim'
  source_label: string
  doc_no: string | null
  po_no: string | null
  suspected_po_no: string | null
  department: string | null
  doc_date: string | null
  vendor_name: string | null
  item_code: string | null
  product_name: string | null
  qty: number | null
  qty_raw: string | null
  unit: string | null
  unit_price: number | null
  amount: number | null
  imported_qty: number
  remaining_qty: number | null
  status: ImportStatus
  status_label: string
  status_reason: string | null
  marked_by?: string | null
  source_status: 'ok' | 'changed' | 'deleted' | 'rejected'
  source_status_label: string
  source_changed: boolean
  ragic_url: string
  ragic_id: string
  detail?: Record<string, string>
  receipts?: { receipt_id: number; receipt_no: string; receipt_date: string; status: string; purchase_qty: number; stock_qty: number; unit_cost: number; amount: number; override_reason: string | null }[]
}

export interface ImportListResp {
  total: number
  rows: ImportLine[]
  status_counts: Record<string, number>
  changed_count: number
  departments: string[]
  data_end: string | null
  refreshed_at: string | null
}

export interface ItemSuggestion {
  item_id: number
  item_code: string
  item_name: string
  spec: string | null
  unit: string | null
  unit_price: number | null
  purchase_unit: string | null
  unit_ratio: number
  score: number
  reason: string
}

export interface ReceiptLineInput {
  import_line_id: number
  item_id: number
  purchase_qty: number
  unit_ratio: number
  unit_price?: number | null
  override_reason?: string | null
  remember_alias?: boolean
  remember_ratio?: boolean
}

export interface Receipt {
  id: number
  receipt_no: string
  warehouse_id: number
  warehouse_name: string
  receipt_date: string
  status: 'posted' | 'voided'
  note: string | null
  line_count: number
  total_amount: number | null
  created_by: string | null
  created_at: string | null
  voided_by: string | null
  void_reason: string | null
  lines?: { id: number; source_label: string; doc_no: string | null; ragic_url: string; product_name: string | null; item_code: string; item_name: string; purchase_qty: number; purchase_unit: string | null; unit_ratio: number; stock_qty: number; stock_unit: string | null; unit_cost: number; amount: number; is_estimated_cost: boolean; override_reason: string | null }[]
}

export interface ReceiptSummary {
  month: string
  receipt_count: number
  stock_qty: number
  amount: number
  pending_lines: number
  changed_lines: number
  data_end: string | null
}

const LIST_PARAMS = { paramsSerializer: { indexes: null } } as const

export const fetchImports = (code: string, params: { status?: string[]; source_type?: string; department?: string; keyword?: string; start?: string; end?: string; only_changed?: boolean }) =>
  apiClient.get<ImportListResp>(`${BASE}/imports`, { params: { ...co(code), ...params }, ...LIST_PARAMS })
export const refreshImports = (code: string) =>
  apiClient.post<{ inserted: number; updated: number; changed_after_import: number; missing: number; total_source_lines: number }>(`${BASE}/imports/refresh`, null, { params: co(code) })
export const fetchImport = (code: string, id: number) => apiClient.get<ImportLine>(`${BASE}/imports/${id}`, { params: co(code) })
export const suggestItems = (code: string, id: number) => apiClient.get<ItemSuggestion[]>(`${BASE}/imports/${id}/suggest`, { params: co(code) })
export const markImports = (code: string, body: { line_ids: number[]; status: 'non_stock' | 'pre_opening' | 'pending'; reason?: string; remember_non_stock?: boolean }) =>
  apiClient.post<{ updated: number; skipped: string[] }>(`${BASE}/imports/mark`, body, { params: co(code) })
export const markBefore = (code: string, before_date: string) =>
  apiClient.post<{ updated: number }>(`${BASE}/imports/mark-before`, { before_date }, { params: co(code) })
export const ackChange = (code: string, id: number) => apiClient.post(`${BASE}/imports/${id}/ack-change`, null, { params: co(code) })

export const createReceipt = (code: string, body: { warehouse_id: number; receipt_date: string; note?: string; lines: ReceiptLineInput[] }) =>
  apiClient.post<{ id: number; receipt_no: string; total_amount: number }>(`${BASE}/receipts`, body, { params: co(code) })
export const fetchReceipts = (code: string, params: { start?: string; end?: string; warehouse_id?: number } = {}) =>
  apiClient.get<Receipt[]>(`${BASE}/receipts`, { params: { ...co(code), ...params } })
export const fetchReceipt = (code: string, id: number) => apiClient.get<Receipt>(`${BASE}/receipts/${id}`, { params: co(code) })
export const voidReceipt = (code: string, id: number, reason: string) =>
  apiClient.post(`${BASE}/receipts/${id}/void`, { reason }, { params: co(code) })
export const fetchReceiptSummary = (code: string, month?: string) =>
  apiClient.get<ReceiptSummary>(`${BASE}/receipts-summary`, { params: { ...co(code), ...(month ? { month } : {}) } })

// ── Phase 4a（2026-11-17）領用／退料／調撥／報廢 ─────────────────────────────
export type IssueDocType = 'issue' | 'return' | 'transfer' | 'scrap'
export type IssueAction = 'edit' | 'submit' | 'cancel' | 'post' | 'approve' | 'reject' | 'void' | 'return'

export interface IssueMeta {
  can_create: boolean
  can_post: boolean
  can_approve: boolean
  can_see_cost: boolean
  user_name: string
  my_warehouses: { id: number; name: string; department_name: string | null; status: string; issue_requires_approval: boolean }[]
  all_warehouses: { id: number; name: string; department_name: string | null; status: string }[]
}

export interface AvailableItem {
  item_id: number
  item_code: string
  item_name: string
  spec: string | null
  unit: string | null
  qty: number
  reserved_qty: number
  available: number
  avg_cost: number | null
}

export interface ReturnableLine {
  ref_line_id: number
  item_id: number
  item_code: string
  item_name: string
  unit: string | null
  issued_qty: number
  returned_qty: number
  returnable: number
  unit_cost: number | null
}

export interface IssueLine {
  id: number
  item_id: number
  item_code: string
  item_name: string
  spec: string | null
  unit: string | null
  qty: number
  reserved_qty: number
  ref_line_id: number | null
  note: string | null
  available: number
  unit_cost: number | null
  amount: number | null
}

export interface IssueDoc {
  id: number
  doc_no: string
  doc_type: IssueDocType
  doc_type_label: string
  warehouse_id: number
  warehouse_name: string
  to_warehouse_id: number | null
  to_warehouse_name: string | null
  doc_date: string
  posted_date: string | null
  requester_name: string | null
  department_name: string | null
  purpose: string | null
  cost_center_id: number | null
  cost_center_name: string | null
  account_code: string | null
  ref_issue_id: number | null
  ref_issue_no?: string | null
  status: string
  status_label: string
  line_count: number
  total_amount: number | null
  created_by: string | null
  created_at: string | null
  submitted_by: string | null
  approved_by: string | null
  approved_at: string | null
  posted_by: string | null
  posted_at: string | null
  closed_by: string | null
  close_reason: string | null
  actions: IssueAction[]
  lines?: IssueLine[]
  returns?: { id: number; doc_no: string; status_label: string }[]
}

export interface IssueInput {
  doc_type: IssueDocType
  warehouse_id: number
  to_warehouse_id?: number | null
  doc_date: string
  requester_name?: string | null
  purpose?: string | null
  cost_center_id?: number | null
  account_code?: string | null
  ref_issue_id?: number | null
  lines: { item_id?: number; qty: number; ref_line_id?: number | null; note?: string | null }[]
  then?: 'submit' | 'post' | null
  post_date?: string | null
}

export interface IssueSummary {
  issue_count: number
  issue_amount: number | null
  pending_approval: number
  pending_post: number
  drafts: number
  data_end: string | null
}

export const fetchIssueMeta = (code: string) => apiClient.get<IssueMeta>(`${BASE}/issues/meta`, { params: co(code) })
export const fetchAvailable = (code: string, warehouse_id: number, keyword?: string) =>
  apiClient.get<AvailableItem[]>(`${BASE}/issues/available`, { params: { ...co(code), warehouse_id, ...(keyword ? { keyword } : {}) } })
export const fetchIssueCostCenters = (code: string, warehouse_id?: number) =>
  apiClient.get<{ default_id: number | null; items: { id: number; label: string; department_name: string; is_mine: boolean }[] }>(
    `${BASE}/issues/cost-centers`, { params: { ...co(code), ...(warehouse_id ? { warehouse_id } : {}) } })
export const fetchIssueSummary = (code: string, params: { start?: string; end?: string } = {}) =>
  apiClient.get<IssueSummary>(`${BASE}/issues/summary`, { params: { ...co(code), ...params } })
export const fetchIssues = (code: string, params: { doc_type?: IssueDocType; status?: string[]; warehouse_id?: number; start?: string; end?: string; mine?: boolean } = {}) =>
  apiClient.get<IssueDoc[]>(`${BASE}/issues`, { params: { ...co(code), ...params }, ...LIST_PARAMS })
export const fetchIssue = (code: string, id: number) => apiClient.get<IssueDoc>(`${BASE}/issues/${id}`, { params: co(code) })
export const fetchReturnable = (code: string, id: number) =>
  apiClient.get<ReturnableLine[]>(`${BASE}/issues/${id}/returnable`, { params: co(code) })
type IssueRes = { id: number; doc_no: string; status: string; status_label?: string }
export const createIssue = (code: string, body: IssueInput) => apiClient.post<IssueRes>(`${BASE}/issues`, body, { params: co(code) })
export const updateIssue = (code: string, id: number, body: IssueInput) => apiClient.put<IssueRes>(`${BASE}/issues/${id}`, body, { params: co(code) })
export const submitIssue = (code: string, id: number) => apiClient.post<IssueRes>(`${BASE}/issues/${id}/submit`, null, { params: co(code) })
export const approveIssue = (code: string, id: number) => apiClient.post<IssueRes>(`${BASE}/issues/${id}/approve`, null, { params: co(code) })
export const rejectIssue = (code: string, id: number, reason: string) => apiClient.post<IssueRes>(`${BASE}/issues/${id}/reject`, { reason }, { params: co(code) })
export const cancelIssue = (code: string, id: number, reason?: string) => apiClient.post<IssueRes>(`${BASE}/issues/${id}/cancel`, { reason: reason || null }, { params: co(code) })
export const postIssue = (code: string, id: number, post_date?: string) => apiClient.post<IssueRes>(`${BASE}/issues/${id}/post`, { post_date: post_date || null }, { params: co(code) })
export const voidIssue = (code: string, id: number, reason: string) => apiClient.post<IssueRes>(`${BASE}/issues/${id}/void`, { reason }, { params: co(code) })

/** axios 錯誤 → 後端 detail 字串 */
export const errMsg = (e: unknown, fallback: string) => {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof d === 'string' ? d : fallback
}
