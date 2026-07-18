/**
 * 週期採購（Cycle Purchase）API
 * 所有週期採購相關 API 呼叫的封裝函數
 * 對應後端 Prefix: /api/v1/cycle-purchase
 */
import apiClient from '@/api/client'
import type {
  CpAccountCode,
  CpAuditLog,
  CpAvailableItem,
  CpCostCenter,
  CpCycle,
  CpDepartment,
  CpDepartmentBreakdown,
  CpEligibleRequest,
  CpItem,
  CpItemDetail,
  CpItemListResponse,
  CpItemMapping,
  CpPO,
  CpPODetail,
  CpPayableReceiving,
  CpPayment,
  CpPaymentAllocation,
  CpPaymentDetail,
  CpPushToRagicResult,
  CpReceivableItem,
  CpReceiving,
  CpReceivingDetail,
  CpReceivingItem,
  CpReceivingReportRow,
  CpRequest,
  CpRequestDetail,
  CpRequestItem,
  CpSummary,
  CpVendor,
  CpVendorGroup,
  TodoSummary,
} from '@/types/cyclePurchase'

const BASE = '/cycle-purchase'

// ── 供應商主檔 ────────────────────────────────────────────────────────────────

export const getVendors = (params?: { q?: string; is_active?: boolean }) =>
  apiClient.get<CpVendor[]>(`${BASE}/masters/vendors`, { params })

export const createVendor = (data: Omit<CpVendor, 'id' | 'created_at' | 'updated_at'>) =>
  apiClient.post<CpVendor>(`${BASE}/masters/vendors`, data)

export const updateVendor = (id: number, data: Partial<CpVendor>) =>
  apiClient.put<CpVendor>(`${BASE}/masters/vendors/${id}`, data)

// ── 部門主檔 ──────────────────────────────────────────────────────────────────

export const getCpDepartments = (params?: { is_active?: boolean }) =>
  apiClient.get<CpDepartment[]>(`${BASE}/masters/departments`, { params })

export const createCpDepartment = (data: Omit<CpDepartment, 'id' | 'created_at'>) =>
  apiClient.post<CpDepartment>(`${BASE}/masters/departments`, data)

export const updateCpDepartment = (id: number, data: Partial<CpDepartment>) =>
  apiClient.put<CpDepartment>(`${BASE}/masters/departments/${id}`, data)

// ── 成本中心主檔 ──────────────────────────────────────────────────────────────

export const getCostCenters = (params?: { department_id?: number; is_active?: boolean }) =>
  apiClient.get<CpCostCenter[]>(`${BASE}/masters/cost-centers`, { params })

export const createCostCenter = (data: Omit<CpCostCenter, 'id' | 'created_at' | 'department_name'>) =>
  apiClient.post<CpCostCenter>(`${BASE}/masters/cost-centers`, data)

export const updateCostCenter = (id: number, data: Partial<CpCostCenter>) =>
  apiClient.put<CpCostCenter>(`${BASE}/masters/cost-centers/${id}`, data)

// ── 會計科目主檔 ──────────────────────────────────────────────────────────────

export const getCpAccountCodes = (params?: { is_active?: boolean }) =>
  apiClient.get<CpAccountCode[]>(`${BASE}/masters/account-codes`, { params })

export const createCpAccountCode = (data: Omit<CpAccountCode, 'id' | 'created_at'>) =>
  apiClient.post<CpAccountCode>(`${BASE}/masters/account-codes`, data)

export const updateCpAccountCode = (id: number, data: Partial<CpAccountCode>) =>
  apiClient.put<CpAccountCode>(`${BASE}/masters/account-codes/${id}`, data)

// ── 料號主檔 ──────────────────────────────────────────────────────────────────

export const getItems = (params?: {
  q?: string
  category?: string
  is_active?: boolean
  page?: number
  per_page?: number
}) => apiClient.get<CpItemListResponse>(`${BASE}/items`, { params })

export const getItem = (id: number) =>
  apiClient.get<CpItemDetail>(`${BASE}/items/${id}`)

export const createItem = (data: Omit<CpItem, 'id' | 'created_at' | 'updated_at' | 'default_vendor_name'>) =>
  apiClient.post<CpItem>(`${BASE}/items`, data)

export const updateItem = (id: number, data: Partial<CpItem>) =>
  apiClient.put<CpItem>(`${BASE}/items/${id}`, data)

// ── 料號對照表 ────────────────────────────────────────────────────────────────

export const getItemMappings = (itemId: number) =>
  apiClient.get<CpItemMapping[]>(`${BASE}/items/${itemId}/mappings`)

export const createItemMapping = (
  itemId: number,
  data: Omit<CpItemMapping, 'id' | 'item_id' | 'created_at' | 'updated_at'>,
) => apiClient.post<CpItemMapping>(`${BASE}/items/${itemId}/mappings`, data)

export const updateItemMapping = (
  itemId: number,
  mappingId: number,
  data: Partial<CpItemMapping>,
) => apiClient.put<CpItemMapping>(`${BASE}/items/${itemId}/mappings/${mappingId}`, data)

export const deleteItemMapping = (itemId: number, mappingId: number) =>
  apiClient.delete(`${BASE}/items/${itemId}/mappings/${mappingId}`)

// ── 週期設定 ──────────────────────────────────────────────────────────────────

export const getCycles = (params?: { status?: string }) =>
  apiClient.get<CpCycle[]>(`${BASE}/cycles`, { params })

export const getCycle = (id: number) =>
  apiClient.get<CpCycle>(`${BASE}/cycles/${id}`)

export const createCycle = (data: Omit<CpCycle, 'id' | 'created_at' | 'updated_at'>) =>
  apiClient.post<CpCycle>(`${BASE}/cycles`, data)

export const updateCycle = (id: number, data: Partial<CpCycle>) =>
  apiClient.put<CpCycle>(`${BASE}/cycles/${id}`, data)

// ── 請購單 ────────────────────────────────────────────────────────────────────
// 2026-07-11：拿掉「批次」，請購單改依 cycle_id + period_label 篩選/建立。
// 「產生本期請購單」取代原本批次開放時的自動觸發，隨時可呼叫、同一週期＋期別冪等。

export const getRequests = (params?: {
  cycle_id?: number
  period_label?: string
  department_id?: number
  status?: string
}) => apiClient.get<CpRequest[]>(`${BASE}/requests`, { params })

export const getRequest = (id: number) =>
  apiClient.get<CpRequestDetail>(`${BASE}/requests/${id}`)

// 2026-07-17：period_label 不再由呼叫端指定，一律由後端在建立當下蓋章為現在的月份。
export const generateRequestsForPeriod = (data: { cycle_id: number }) =>
  apiClient.post<CpRequest[]>(`${BASE}/requests/generate`, data)

export const getTodos = () =>
  apiClient.get<TodoSummary>(`${BASE}/requests/todos`)

export const createRequest = (data: {
  cycle_id: number
  department_id: number
  cost_center_id?: number | null
}) => apiClient.post<CpRequest>(`${BASE}/requests`, data)

export const updateRequest = (id: number, data: { cost_center_id?: number | null; notes?: string | null }) =>
  apiClient.put<CpRequest>(`${BASE}/requests/${id}`, data)

export const getAvailableItems = (requestId: number) =>
  apiClient.get<CpAvailableItem[]>(`${BASE}/requests/${requestId}/available-items`)

export const addRequestItem = (
  requestId: number,
  data: { item_id: number; request_qty?: number; account_code_id?: number | null; notes?: string | null },
) => apiClient.post<CpRequestItem>(`${BASE}/requests/${requestId}/items`, data)

export const updateRequestItem = (
  requestId: number,
  itemRowId: number,
  data: { request_qty?: number; account_code_id?: number | null; notes?: string | null },
) => apiClient.put<CpRequestItem>(`${BASE}/requests/${requestId}/items/${itemRowId}`, data)

export const deleteRequestItem = (requestId: number, itemRowId: number) =>
  apiClient.delete(`${BASE}/requests/${requestId}/items/${itemRowId}`)

// 2026-07-17（第三次調整）：拿掉送出／簽核／退回，改成「關閉／重新開啟」。

export const getOpenRequestsForClose = (params: { cycle_id: number; company?: string; year_month?: string }) =>
  apiClient.get<CpRequest[]>(`${BASE}/requests/open-for-close`, { params })

export const closeRequests = (request_ids: number[]) =>
  apiClient.post<CpRequest[]>(`${BASE}/requests/close`, { request_ids })

export const closeAllRequests = (data: { cycle_id: number; company?: string | null; year_month?: string | null }) =>
  apiClient.post<CpRequest[]>(`${BASE}/requests/close-all`, data)

export const reopenRequests = (request_ids: number[]) =>
  apiClient.post<CpRequest[]>(`${BASE}/requests/reopen`, { request_ids })

// ── 彙整單（第三期，2026-07-11 新增）───────────────────────────────────────────
// 只彙總 approved 的請購明細，同一週期＋期別＋公司＋料號冪等。

export const getSummary = (params?: {
  cycle_id?: number
  period_label?: string
  company?: string
  vendor_id?: number
  status?: string
  department_id?: number
}) => apiClient.get<CpSummary[]>(`${BASE}/summary`, { params })

export const getVendorGroups = (params: { cycle_id: number; period_label: string; company?: string }) =>
  apiClient.get<CpVendorGroup[]>(`${BASE}/summary/vendor-groups`, { params })

// 2026-07-16 改版：拿掉舊版「輸入週期＋期別字串」的產生彙整方式（原本
// generateSummary()／POST /summary/generate），改成「勾選請購單」——見
// 後端 services/cycle_purchase_summary_service.py 開頭「第二次調整」說明。
export const getEligibleRequests = (params: { cycle_id: number; company: string; year_month: string }) =>
  apiClient.get<CpEligibleRequest[]>(`${BASE}/summary/eligible-requests`, { params })

export const generateSummaryFromRequests = (data: { request_ids: number[] }) =>
  apiClient.post<CpSummary[]>(`${BASE}/summary/generate-from-requests`, data)

export const updateSummaryItem = (id: number, data: { adjusted_qty?: number; adjust_reason?: string | null }) =>
  apiClient.put<CpSummary>(`${BASE}/summary/${id}`, data)

export const convertToPo = (data: { cycle_id: number; period_label: string; company: string; vendor_id: number }) =>
  apiClient.post<CpPODetail>(`${BASE}/summary/convert-to-po`, data)

// 2026-07-16 新增：匯總請購單畫面 — 依料號分組展開部門別＋小計
export const getDepartmentBreakdown = (params: { cycle_id: number; period_label: string; company?: string }) =>
  apiClient.get<CpDepartmentBreakdown[]>(`${BASE}/summary/department-breakdown`, { params })

// 2026-07-16 新增：拋轉到 Ragic「匯總請購單」（目前為 stub，見後端
// cycle_purchase_ragic_push.py 開頭說明，Ragic 端表單尚未建立）
export const pushSummaryToRagic = (data: { cycle_id: number; period_label: string; company: string }) =>
  apiClient.post<CpPushToRagicResult>(`${BASE}/summary/push-to-ragic`, data)

// ── 採購單（第三期，2026-07-11 新增）───────────────────────────────────────────
// 一張採購單＝一個公司＋一個供應商（同一週期＋期別內），由「轉採購單」動作產生。

export const getPos = (params?: {
  cycle_id?: number
  period_label?: string
  company?: string
  vendor_id?: number
  status?: string
}) => apiClient.get<CpPO[]>(`${BASE}/pos`, { params })

export const getPo = (id: number) =>
  apiClient.get<CpPODetail>(`${BASE}/pos/${id}`)

export const updatePo = (id: number, data: { expected_date?: string | null; notes?: string | null }) =>
  apiClient.put<CpPO>(`${BASE}/pos/${id}`, data)

export const setPoStatus = (id: number, status: 'issued' | 'cancelled') =>
  apiClient.post<CpPO>(`${BASE}/pos/${id}/status`, { status })

// ── 驗收單（第四期，2026-07-11 新增）───────────────────────────────────────────
// 一張採購單可以分好幾次驗收（部分到貨）。送出後系統自動判定 completed／
// discrepancy，並重算對應採購單狀態（issued -> partial_received -> received）。

export const getReceivingList = (params?: { po_id?: number; status?: string; company?: string }) =>
  apiClient.get<CpReceiving[]>(`${BASE}/receiving`, { params })

export const getReceiving = (id: number) =>
  apiClient.get<CpReceivingDetail>(`${BASE}/receiving/${id}`)

export const createReceiving = (data: { po_id: number; received_date: string; notes?: string | null }) =>
  apiClient.post<CpReceiving>(`${BASE}/receiving`, data)

export const getReceivableItems = (receivingId: number) =>
  apiClient.get<CpReceivableItem[]>(`${BASE}/receiving/${receivingId}/receivable-items`)

export const upsertReceivingItem = (
  receivingId: number,
  data: { po_item_id: number; received_qty: number; is_final_for_item?: boolean; variance_reason?: string | null },
) => apiClient.post<CpReceivingItem>(`${BASE}/receiving/${receivingId}/items`, data)

export const deleteReceivingItem = (receivingId: number, receivingItemId: number) =>
  apiClient.delete(`${BASE}/receiving/${receivingId}/items/${receivingItemId}`)

export const submitReceiving = (id: number) =>
  apiClient.post<CpReceiving>(`${BASE}/receiving/${id}/submit`)

export const getReceivingReport = (params?: {
  date_from?: string
  date_to?: string
  company?: string
  vendor_id?: number
}) => apiClient.get<CpReceivingReportRow[]>(`${BASE}/receiving/report`, { params })

// ── 請款單（第五期，2026-07-11 新增）───────────────────────────────────────────
// 一張採購單可以有多張請款單（例如分期付款）；一張驗收單只能被一張請款單涵蓋。
// 建立時系統自動試算費用分攤明細，草稿狀態可調整。狀態機：draft -> submitted
// -> paying -> paid（只能依序推進）。

export const getPayments = (params?: { po_id?: number; status?: string; company?: string }) =>
  apiClient.get<CpPayment[]>(`${BASE}/payments`, { params })

export const getPayableReceivings = (poId: number) =>
  apiClient.get<CpPayableReceiving[]>(`${BASE}/payments/payable-receivings`, { params: { po_id: poId } })

export const getPayment = (id: number) =>
  apiClient.get<CpPaymentDetail>(`${BASE}/payments/${id}`)

export const createPayment = (data: {
  po_id: number
  receiving_ids: number[]
  invoice_no: string
  invoice_date: string
  invoice_amount: number
  notes?: string | null
}) => apiClient.post<CpPayment>(`${BASE}/payments`, data)

export const updatePayment = (
  id: number,
  data: {
    invoice_no?: string
    invoice_date?: string
    invoice_amount?: number
    notes?: string | null
    amount_diff_reason?: string | null
  },
) => apiClient.put<CpPayment>(`${BASE}/payments/${id}`, data)

export const updateAllocationItem = (
  paymentId: number,
  allocationId: number,
  data: { allocated_amount: number; adjust_reason?: string | null },
) => apiClient.put<CpPaymentAllocation>(`${BASE}/payments/${paymentId}/allocations/${allocationId}`, data)

export const submitPayment = (id: number) =>
  apiClient.post<CpPayment>(`${BASE}/payments/${id}/submit`)

export const setPaymentStatus = (id: number, status: 'paying' | 'paid') =>
  apiClient.post<CpPayment>(`${BASE}/payments/${id}/status`, { status })

// ── 異常稽核紀錄（第五期，2026-07-11 新增）─────────────────────────────────────
// 系統內部自動寫入（驗收差異／請款差異），append-only，前端只做查詢。

export const getAuditLog = (params?: {
  document_type?: string
  event_type?: string
  date_from?: string
  date_to?: string
}) => apiClient.get<CpAuditLog[]>(`${BASE}/audit-log`, { params })
