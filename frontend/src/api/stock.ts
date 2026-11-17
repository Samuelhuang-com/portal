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
  count_blind: boolean
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
  count_blind?: boolean
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
  /** 清單：來源 Ragic 單據附件數（採購單含來源請購單的附件）（2026-11-17） */
  attachment_count?: number
  /** 明細：來源 Ragic 單據附件（2026-11-17） */
  attachments?: ImportAttachment[]
}

/** Ragic 單據附件；url 為 Ragic sims/file.jsp，瀏覽器需已登入 Ragic */
export interface ImportAttachment {
  field: string
  filename: string
  url: string
  is_image: boolean
  /** 例：「採購單 樂營採00014」「請購單 台資購-20261030-001」 */
  source: string
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
export const fetchAvailable = (code: string, warehouse_id: number, keyword?: string, include_zero = false) =>
  apiClient.get<AvailableItem[]>(`${BASE}/issues/available`, {
    params: { ...co(code), warehouse_id, ...(keyword ? { keyword } : {}), ...(include_zero ? { include_zero: true } : {}) },
  })
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

// ── Phase 4b（2026-11-17）領用範本 ──────────────────────────────────────────
export interface IssueTemplate {
  id: number
  warehouse_id: number
  warehouse_name: string
  name: string
  note: string | null
  lines: { item_id: number; item_code: string; item_name: string; spec: string | null; unit: string | null; qty: number; available: number }[]
  created_by: string | null
  updated_by: string | null
  updated_at: string | null
}
export interface IssueTemplateInput {
  warehouse_id: number
  name: string
  note?: string | null
  lines: { item_id: number; qty: number }[]
}
export const fetchIssueTemplates = (code: string, warehouse_id?: number) =>
  apiClient.get<IssueTemplate[]>(`${BASE}/issues/templates`, { params: { ...co(code), ...(warehouse_id ? { warehouse_id } : {}) } })
export const createIssueTemplate = (code: string, body: IssueTemplateInput) =>
  apiClient.post<{ id: number; name: string }>(`${BASE}/issues/templates`, body, { params: co(code) })
export const updateIssueTemplate = (code: string, id: number, body: IssueTemplateInput) =>
  apiClient.put<{ id: number; name: string }>(`${BASE}/issues/templates/${id}`, body, { params: co(code) })
export const deleteIssueTemplate = (code: string, id: number) =>
  apiClient.delete(`${BASE}/issues/templates/${id}`, { params: co(code) })

/** 手機領用頁網址（QR 標籤內容；用手機內建相機掃描即開啟，不需 HTTPS 相機權限） */
export const mobileIssueUrl = (base: string, code: string, warehouse_id: number, item_code: string) =>
  `${base.replace(/\/+$/, '')}/m/stock/issue?co=${encodeURIComponent(code)}&wh=${warehouse_id}&item=${encodeURIComponent(item_code)}`

// ── Phase 5（2026-11-17）盤點、月結、進銷存月報 ─────────────────────────────
export interface StockCountRow {
  id: number
  count_no: string
  warehouse_id: number
  warehouse_name: string
  period: string
  count_date: string
  cutoff_at: string
  blind: boolean
  count_type: 'full' | 'cycle'
  abc_classes: string | null
  status: 'counting' | 'submitted' | 'approved' | 'cancelled'
  status_label: string
  note: string | null
  line_count: number
  counted_count: number | null
  diff_count: number
  gain_amount: number | null
  loss_amount: number | null
  created_by: string | null
  created_at: string | null
  submitted_by: string | null
  approved_by: string | null
  approved_at: string | null
  closed_by: string | null
  close_reason: string | null
  can_input: boolean
  can_review: boolean
  can_cancel: boolean
  show_book: boolean
  lines?: StockCountLineRow[]
}
export interface StockCountLineRow {
  id: number
  item_id: number
  item_code: string
  item_name: string
  spec: string | null
  unit: string | null
  counted_qty: number | null
  counted_by: string | null
  note: string | null
  added_manually: boolean
  book_qty: number | null
  diff_qty?: number | null
  diff_amount?: number | null
  est_unit_cost?: number
  needs_recount?: boolean
  unit_cost?: number | null
}
export interface StockPeriodRow {
  period: string
  status: 'open' | 'closed'
  has_moves: boolean
  closed_by: string | null
  closed_at: string | null
  revalue_count: number
  revalue_amount: number | null
  reopen_count: number
  reopened_by: string | null
  reopen_reason: string | null
}
export interface PeriodCheck {
  ok: boolean
  problems: string[]
  warehouses: { warehouse_id: number; warehouse_name: string; need_count: boolean; status: string }[]
}
export interface MonthlyReportResp {
  period: string
  closed: boolean
  last_period: string | null
  columns: { key: string; label: string }[]
  rows: (Record<string, number | string | null> & {
    warehouse_id: number; warehouse_name: string; item_id: number; item_code: string; item_name: string; spec: string | null; unit: string | null
    open_qty: number; open_amt: number; close_qty: number; close_amt: number
    consume_amt: number; turnover_days: number | null
  })[]
}
type CountRes = { id: number; count_no: string; status: string; status_label: string }
export const fetchCounts = (code: string, params: { period?: string; status?: string[] } = {}) =>
  apiClient.get<StockCountRow[]>(`${BASE}/counts`, { params: { ...co(code), ...params }, ...LIST_PARAMS })
export const createCounts = (code: string, body: { warehouse_ids: number[]; count_date: string; note?: string | null; abc_classes?: string[] | null }) =>
  apiClient.post<{ created: { id: number; count_no: string; warehouse_name: string; line_count: number }[]; errors: string[] }>(
    `${BASE}/counts`, body, { params: co(code) })
export const fetchCount = (code: string, id: number) => apiClient.get<StockCountRow>(`${BASE}/counts/${id}`, { params: co(code) })
export const saveCountEntries = (code: string, id: number, entries: { item_id: number; counted_qty: number | null; note?: string | null }[]) =>
  apiClient.put<{ saved: number }>(`${BASE}/counts/${id}/entries`, { entries }, { params: co(code) })
export const searchCountItems = (code: string, id: number, keyword: string) =>
  apiClient.get<{ item_id: number; item_code: string; item_name: string; spec: string | null; unit: string | null }[]>(
    `${BASE}/counts/${id}/item-search`, { params: { ...co(code), keyword } })
export const addCountItem = (code: string, id: number, item_id: number) =>
  apiClient.post<{ line_id: number }>(`${BASE}/counts/${id}/items`, { item_id }, { params: co(code) })
export const submitCount = (code: string, id: number, fill_zero: boolean) =>
  apiClient.post<CountRes>(`${BASE}/counts/${id}/submit`, { fill_zero }, { params: co(code) })
export const returnCount = (code: string, id: number, reason: string, item_ids?: number[]) =>
  apiClient.post<CountRes>(`${BASE}/counts/${id}/return`, { reason, item_ids: item_ids?.length ? item_ids : null }, { params: co(code) })
export const approveCount = (code: string, id: number) => apiClient.post<CountRes>(`${BASE}/counts/${id}/approve`, null, { params: co(code) })
export const cancelCount = (code: string, id: number, reason?: string) =>
  apiClient.post<CountRes>(`${BASE}/counts/${id}/cancel`, { reason: reason || null }, { params: co(code) })
export const fetchPeriods = (code: string) => apiClient.get<StockPeriodRow[]>(`${BASE}/periods`, { params: co(code) })
export const checkPeriod = (code: string, period: string) => apiClient.get<PeriodCheck>(`${BASE}/periods/${period}/check`, { params: co(code) })
export const closePeriod = (code: string, period: string) => apiClient.post<StockPeriodRow>(`${BASE}/periods/${period}/close`, null, { params: co(code) })
export const reopenPeriod = (code: string, period: string, reason: string) =>
  apiClient.post<StockPeriodRow>(`${BASE}/periods/${period}/reopen`, { reason }, { params: co(code) })
export const fetchMonthlyReport = (code: string, period: string, warehouse_id?: number) =>
  apiClient.get<MonthlyReportResp>(`${BASE}/monthly-report`, { params: { ...co(code), period, ...(warehouse_id ? { warehouse_id } : {}) } })

// ── Phase 7（2026-11-17）ABC 建議、補貨建議 ─────────────────────────────────
export interface AbcRow {
  item_id: number; item_code: string; item_name: string; spec: string | null; unit: string | null
  consume_amount: number; share: number; cum_share: number; current: string | null; suggested: 'A' | 'B' | 'C'
}
export interface ReplenishRow {
  warehouse_id: number; warehouse_name: string; department_name: string | null
  item_id: number; item_code: string; item_name: string; spec: string | null; unit: string | null
  qty: number; reserved_qty: number; available: number; min_stock: number; max_stock: number | null
  suggest_qty: number; purchase_unit: string | null; unit_ratio: number; suggest_purchase_qty: number
  monthly_use: number; days_left: number | null; avg_cost: number; est_amount: number; vendor_name: string | null
}
export const fetchAbcSuggest = (code: string, days = 90) =>
  apiClient.get<{ days: number; rows: AbcRow[] }>(`${BASE}/items/abc-suggest`, { params: { ...co(code), days } })
export const applyAbc = (code: string, items: { item_id: number; abc_class: string | null }[]) =>
  apiClient.post<{ updated: number }>(`${BASE}/items/abc-apply`, { items }, { params: co(code) })
export const fetchReplenishment = (code: string, warehouse_id?: number, days = 90) =>
  apiClient.get<{ days: number; rows: ReplenishRow[] }>(`${BASE}/replenishment`, { params: { ...co(code), days, ...(warehouse_id ? { warehouse_id } : {}) } })

/** axios 錯誤 → 後端 detail 字串 */
export const errMsg = (e: unknown, fallback: string) => {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof d === 'string' ? d : fallback
}


// ── Dashboard（2026-11-17，SPEC §12.1）─────────────────────────────────────
export interface StockDashboardResp {
  company: string
  anchor: string
  data_end: string | null
  filters: { warehouse_id: number | null; department_id: string | null; start: string; end: string }
  import: { pending: number; changed: number; new_week: { count: number; amount: number | null }; new_month: { count: number; amount: number | null } }
  receipts: { week: { count: number; stock_qty: number; amount: number | null }; month: { count: number; stock_qty: number; amount: number | null }; period: { count: number; stock_qty: number; amount: number | null } }
  issues: { week: { count: number; amount: number | null }; month: { count: number; amount: number | null }; period: { count: number; amount: number | null }; pending_approval: number; pending_post: number }
  categories: { stock_categories: number }
  counts: { period: string; tables: number; by_status: Record<string, number>; lines: number; diff: number; gain_amount: number | null; loss_amount: number | null }
  balance: { amount: number | null; items: number; low: number; dead: number; negative: number; dead_days: number }
  period_close: { prev_period: string; prev_closed: boolean; last_closed: string | null }
  three_way_diff: number | null
  meta: { cost_visible: boolean; review_visible: boolean }
}

export interface StockDashboardParams {
  start?: string
  end?: string
  warehouse_id?: number
  department_id?: string
}

export const fetchStockDashboard = (code: string, params: StockDashboardParams = {}) =>
  apiClient.get<StockDashboardResp>(`${BASE}/dashboard`, { params: { ...co(code), ...params } })
