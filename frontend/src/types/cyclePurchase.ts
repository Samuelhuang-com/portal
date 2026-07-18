/**
 * 週期採購（Cycle Purchase）型別定義
 * 對應後端 backend/app/schemas/cycle_purchase_*.py
 */

// ── 供應商主檔 ────────────────────────────────────────────────────────────────
export interface CpVendor {
  id: number
  vendor_code: string
  vendor_name: string
  tax_id?: string | null
  contact_name?: string | null
  contact_phone?: string | null
  payment_terms?: string | null
  notes?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

// ── 部門 / 成本中心 / 會計科目 主檔 ──────────────────────────────────────────
export interface CpDepartment {
  id: number
  company: string
  dept_code: string
  dept_name: string
  // 2026-07-11 新增：承辦人（portal.db users.id，軟關聯），供「待辦提醒」
  // 判斷登入者屬於哪個週採部門用。owner_name 由後端 router 層跨查 portal.db 附加。
  owner_user_id?: string | null
  owner_name?: string | null
  is_active: boolean
  created_at: string
}

export interface CpCostCenter {
  id: number
  department_id: number
  department_name?: string | null
  cc_code: string
  cc_name: string
  is_active: boolean
  created_at: string
}

export interface CpAccountCode {
  id: number
  code: string
  name: string
  is_active: boolean
  created_at: string
}

// ── 料號主檔 + 料號對照表 ─────────────────────────────────────────────────────
export interface CpItem {
  id: number
  item_code: string
  item_name: string
  spec?: string | null
  category?: string | null
  unit?: string | null
  default_qty: number
  moq: number
  max_stock?: number | null
  min_stock?: number | null
  unit_price?: number | null
  default_vendor_id?: number | null
  default_vendor_name?: string | null
  is_active: boolean
  is_cycle_item: boolean
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface CpItemMapping {
  id: number
  item_id: number
  company: string
  // 2026-07-11 新增：這個料號在這家公司屬於哪個部門（工務／清潔／文具印刷／
  // 營業用品），逐列核對兩家公司的「設料號明細表.xlsx」後確認分頁邊界對應
  // 真實的功能性部門。請購單「可選料號」查詢按公司＋部門篩選用。
  department_id: number
  department_name?: string | null
  original_code?: string | null
  original_name?: string | null
  original_vendor_name?: string | null
  // 2026-07-11 新增（第三期彙整單／採購單規劃時發現並修正）：這個料號在這家
  // 公司實際跟哪個供應商叫貨，取代原本只有文字的 original_vendor_name。
  // 彙整單/採購單一律依這個欄位分供應商。可為 null（原始資料廠商欄位本來
  // 就是空的，或舊資料尚未跑過 backfill_item_mapping_vendor_id.py 回填）。
  vendor_id?: number | null
  vendor_name?: string | null
  original_unit_price?: number | null
  is_confirmed: boolean
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface CpItemDetail extends CpItem {
  mappings: CpItemMapping[]
}

export interface CpItemListResponse {
  items: CpItem[]
  total: number
  page: number
  per_page: number
}

// ── 週期設定 ──────────────────────────────────────────────────────────────────
export interface CpCycle {
  id: number
  cycle_code: string
  cycle_name: string
  frequency: 'monthly' | 'biweekly' | 'bimonthly' | 'custom'
  open_rule?: string | null
  close_rule?: string | null
  applicable_categories?: string | null
  applicable_scope?: string | null
  auto_generate: boolean
  reminder_rule?: string | null
  status: 'active' | 'inactive' | 'paused'
  notes?: string | null
  created_at: string
  updated_at: string
}

// ── 請購單 / 請購明細 ──────────────────────────────────────────────────────────
// 2026-07-11：拿掉「批次」實體（原本批次開放後系統自動產生請購單）。
// 請購單改成直接掛「週期設定」(cycle_id) + 期別標籤 (period_label，如
// 「2026-07」)，取代原本的 batch_id/batch_no。「產生本期請購單」隨時可觸發，
// 同一週期＋期別冪等，不需要先手動開批次，也沒有固定時間窗限制 —— 週採的
// 範圍界線是「料號主檔」，不是時間窗。
// 2026-07-17（第三次調整，請購單流程大改版）：拿掉送出／核准／退回，status
// 欄位是改版前的歷史殘留（新資料一律固定寫 draft），實際可不可以編輯看的是
// is_closed（有沒有被關閉）＋ period_label（是不是還是當月），不是 status。
// 新增關閉／重新開啟相關欄位，見 backend models/cycle_purchase_request.py
// 開頭「2026-07-17」說明。
export interface CpRequestItem {
  id: number
  request_id: number
  item_id: number
  item_mapping_id?: number | null
  account_code_id?: number | null
  account_code_label?: string | null
  item_code: string
  item_name: string
  unit?: string | null
  unit_price?: number | null
  request_qty: number
  subtotal: number
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface CpRequest {
  id: number
  request_no: string
  cycle_id: number
  cycle_name?: string | null
  period_label: string
  department_id: number
  department_name?: string | null
  company: string
  cost_center_id?: number | null
  cost_center_name?: string | null
  total_amount: number
  // 改版前的狀態機殘留欄位：新資料一律固定寫 draft，實際可不可以編輯看
  // is_closed／period_label，不是這個欄位（見上方 2026-07-17 說明）。
  status: 'draft' | 'submitted' | 'approved' | 'rejected'
  submitted_by_user_id?: string | null
  submitted_by_name?: string | null
  submitted_at?: string | null
  // [改版前歷史欄位，2026-07-17 起停止寫入]
  approved_by_user_id?: string | null
  approved_by_name?: string | null
  approved_at?: string | null
  reject_reason?: string | null
  // 2026-07-17 新增：是否已關閉（關閉後不能再新增/編輯明細，也不能再修改請購單本身）。
  is_closed: boolean
  closed_by_user_id?: string | null
  closed_by_name?: string | null
  closed_at?: string | null
  close_batch_no?: string | null
  reopened_by_user_id?: string | null
  reopened_by_name?: string | null
  reopened_at?: string | null
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface CpRequestDetail extends CpRequest {
  items: CpRequestItem[]
}

// 2026-07-16 新增（彙整單產生方式改版）：「彙整單」頁面用，列出某週期＋公司＋
// 期別下，已關閉且尚未被彙整過的請購單，供使用者勾選要納入這次彙整的範圍。
// 2026-07-17：approved_by_name／approved_at 改成 closed_by_name／closed_at
// （拿掉核准這個動作，「關閉」才是彙整的前提條件）。
export interface CpEligibleRequest {
  id: number
  request_no: string
  department_id?: number | null
  department_name?: string | null
  submitted_by_name?: string | null
  closed_by_name?: string | null
  closed_at?: string | null
  total_amount: number
}

export interface CpAvailableItem {
  item_id: number
  item_mapping_id: number
  item_code: string
  item_name: string
  unit?: string | null
  category?: string | null
  unit_price?: number | null
  is_confirmed: boolean
}

// ── 彙整單（第三期，2026-07-11 新增）──────────────────────────────────────────
// 只彙總 approved 的請購明細（草稿/已送出/已退回都不算）。同一週期＋期別＋
// 公司＋料號只會有一列（冪等）：重複「產生彙整」不會覆寫已存在的列，只會
// 新增這次才第一次出現的組合——若核准的請購明細在彙整之後又增加，需要
// 人工重新整理，這是刻意的保守設計，避免自動改動已經在跑後續流程的數字。
// 供應商一律來自料號對照表的 vendor_id（不是料號主檔的 default_vendor_id）。
// 狀態機：draft（可調整調整量／原因）-> converted（已轉採購單，鎖定不可再改）。
// 2026-07-16：彙整粒度改成「公司＋料號＋部門」（department_id），並新增拋轉
// Ragic 追蹤欄位。department_id 為 null 代表 2026-07-16 之前產生的歷史列，
// 未拆分部門（見 backend models/cycle_purchase_summary.py 開頭說明）。
export interface CpSummary {
  id: number
  cycle_id: number
  cycle_name?: string | null
  period_label: string
  company: string
  item_id: number
  item_mapping_id?: number | null
  department_id?: number | null
  department_name?: string | null
  vendor_id?: number | null
  vendor_name?: string | null
  item_code: string
  item_name: string
  unit?: string | null
  unit_price?: number | null
  demand_qty: number
  adjusted_qty: number
  adjust_reason?: string | null
  status: 'draft' | 'converted'
  po_id?: number | null
  po_no?: string | null
  ragic_push_batch_no?: string | null
  ragic_pushed: boolean
  ragic_record_id?: string | null
  ragic_pushed_at?: string | null
  ragic_push_error?: string | null
  notes?: string | null
  created_at: string
  updated_at: string
}

// 給「轉採購單」畫面用：某週期＋期別下還沒轉單（draft）的彙整列，依公司＋
// 供應商分組統計。has_missing_vendor=true 代表這組沒有供應商，不能轉單，
// 需要先到料號對照表補上供應商。
export interface CpVendorGroup {
  company: string
  vendor_id?: number | null
  vendor_name?: string | null
  item_count: number
  total_amount: number
  has_missing_vendor: boolean
}

// 2026-07-16 新增：匯總請購單畫面用，依料號分組展開部門別＋小計。
export interface CpDepartmentBreakdownRow {
  summary_id: number
  department_id?: number | null
  department_name?: string | null
  demand_qty: number
  adjusted_qty: number
  subtotal: number
  status: 'draft' | 'converted'
}

export interface CpDepartmentBreakdown {
  company: string
  item_id: number
  item_code: string
  item_name: string
  unit?: string | null
  vendor_id?: number | null
  vendor_name?: string | null
  unit_price?: number | null
  departments: CpDepartmentBreakdownRow[]
  total_adjusted_qty: number
  total_amount: number
  has_missing_vendor: boolean
}

// 2026-07-16 新增：拋轉到 Ragic「匯總請購單」的結果。Ragic 端表單尚未建立，
// is_stub=true 代表這是模擬結果，不是真正寫入 Ragic 的記錄。
export interface CpPushToRagicResult {
  batch_no: string
  pushed_count: number
  ragic_record_id?: string | null
  is_stub: boolean
  message: string
}

// ── 採購單（第三期，2026-07-11 新增）──────────────────────────────────────────
// 一張採購單＝一個公司＋一個供應商（同一週期＋期別內，同公司同供應商的所有
// 彙整列合成一張採購單）。由「轉採購單」動作產生，只會納入調整量 > 0 的
// 彙整列進明細；調整量 = 0 的列（代表「本期決定不訂這個料號」）會一併鎖定
// 但不會出現在採購明細裡。狀態機：draft -> issued -> cancelled（issued 也
// 可以直接 cancelled，例如供應商無法供貨）。
export interface CpPOItem {
  id: number
  po_id: number
  summary_id: number
  item_id: number
  item_code: string
  item_name: string
  unit?: string | null
  unit_price?: number | null
  ordered_qty: number
  subtotal: number
  created_at: string
  updated_at: string
}

export interface CpPO {
  id: number
  po_no: string
  cycle_id: number
  cycle_name?: string | null
  period_label: string
  company: string
  vendor_id: number
  vendor_name?: string | null
  buyer_user_id?: string | null
  buyer_name?: string | null
  expected_date?: string | null
  total_amount: number
  // 2026-07-11（第四期）：partial_received／received 由驗收單送出後系統自動
  // 重算，不會透過 PUT /pos/{id}/status 人工指定（那個 endpoint 只給
  // issued／cancelled 用）。
  status: 'draft' | 'issued' | 'partial_received' | 'received' | 'cancelled'
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface CpPODetail extends CpPO {
  items: CpPOItem[]
}

// ── 驗收單（第四期，2026-07-11 新增）──────────────────────────────────────────
// 一張採購單可以分好幾次驗收（部分到貨）。每張驗收明細行有 is_final_for_item
// 旗標（預設 true，多數情況一次到齊）：只有這個旗標為 true 的列，送出時才會
// 計算差異數量（variance_qty＝累計已驗收數量－訂購數量），非 true 的列代表
// 「這只是部分到貨，之後還會再驗收」，中途不計算差異，避免誤判。
// 這期不記錄發票數量（留到第五期請款單再處理），差異只比對「驗收數量 vs
// 訂購數量」。驗收用獨立權限 cycle_purchase_receive；報表用 cycle_purchase_report。
// 狀態機：draft（可編輯明細）-> completed（送出後無差異）／discrepancy（送出
// 後有差異，系統自動判定，不可人工指定）。送出後不能再編輯明細。
export interface CpReceivableItem {
  po_item_id: number
  item_id: number
  item_code: string
  item_name: string
  unit?: string | null
  ordered_qty: number
  previously_received_qty: number
  remaining_qty: number
  // 若這張（草稿）驗收單已經填過這個料號，以下欄位會有值：
  receiving_item_id?: number | null
  received_qty?: number | null
  is_final_for_item?: boolean | null
  variance_reason?: string | null
}

export interface CpReceivingItem {
  id: number
  receiving_id: number
  po_item_id: number
  item_id: number
  item_code: string
  item_name: string
  unit?: string | null
  ordered_qty: number
  previously_received_qty: number
  received_qty: number
  is_final_for_item: boolean
  variance_qty?: number | null
  variance_reason?: string | null
  created_at: string
  updated_at: string
}

export interface CpReceiving {
  id: number
  receiving_no: string
  po_id: number
  po_no?: string | null
  company?: string | null
  vendor_name?: string | null
  receiver_user_id?: string | null
  receiver_name?: string | null
  received_date: string
  status: 'draft' | 'completed' | 'discrepancy'
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface CpReceivingDetail extends CpReceiving {
  items: CpReceivingItem[]
}

// 進貨數量報表：依月份＋公司＋供應商＋料號彙總，只計已送出（completed/
// discrepancy）驗收單，草稿不算。
export interface CpReceivingReportRow {
  period: string
  company: string
  vendor_id?: number | null
  vendor_name?: string | null
  item_id: number
  item_code: string
  item_name: string
  unit?: string | null
  total_received_qty: number
  total_amount: number
  receiving_count: number
}

// ── 請款單（第五期，2026-07-11 新增）──────────────────────────────────────────
// 請款單關聯到「一張採購單」（po_id），涵蓋這張採購單底下的一或多張已送出
// （completed/discrepancy）驗收單（同一張驗收單只能被一張請款單涵蓋）。
// 建立時系統自動依原始請購資料試算費用分攤明細（suggested_amount，不可再
// 變動），allocated_amount 預設等於試算值，草稿狀態下可調整（不同時需填
// adjust_reason）。狀態機：draft -> submitted -> paying -> paid（只能依序
// 推進，不能跳過或倒退）。送出時若分攤總額與發票金額不符，需先填
// amount_diff_reason（透過 PUT /payments/{id} 更新）才能送出，並自動寫一筆
// 異常稽核紀錄。
export interface CpPayableReceiving {
  receiving_id: number
  receiving_no: string
  received_date: string
  status: 'completed' | 'discrepancy'
  estimated_amount: number
}

export interface CpPaymentAllocation {
  id: number
  payment_id: number
  company: string
  department_id?: number | null
  department_name?: string | null
  cost_center_id?: number | null
  cost_center_name?: string | null
  account_code_id?: number | null
  account_code_label?: string | null
  suggested_amount: number
  allocated_amount: number
  adjust_reason?: string | null
  created_at: string
  updated_at: string
}

export interface CpPaymentReceiving {
  id: number
  receiving_id: number
  receiving_no?: string | null
  received_date?: string | null
  status?: string | null
}

export interface CpPayment {
  id: number
  payment_no: string
  po_id: number
  po_no?: string | null
  company?: string | null
  vendor_name?: string | null
  invoice_no: string
  invoice_date: string
  invoice_amount: number
  total_allocated?: number | null
  status: 'draft' | 'submitted' | 'paying' | 'paid'
  amount_diff_reason?: string | null
  processor_user_id?: string | null
  processor_name?: string | null
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface CpPaymentDetail extends CpPayment {
  allocations: CpPaymentAllocation[]
  receivings: CpPaymentReceiving[]
}

// ── 異常稽核紀錄（第五期，2026-07-11 新增）─────────────────────────────────────
// 系統內部自動寫入（驗收單送出有差異／請款單送出金額不符時），append-only，
// 沒有新增／修改／刪除 endpoint，前端只做查詢。查看權限 cycle_purchase_admin。
export interface CpAuditLog {
  id: number
  document_type: 'request' | 'po' | 'receiving' | 'payment'
  document_id: number
  document_no: string
  event_type: 'backfill' | 'overdue' | 'shortage' | 'substitute' | 'receiving_variance' | 'payment_variance'
  description: string
  operator_user_id?: string | null
  operator_name?: string | null
  old_value?: string | null
  new_value?: string | null
  created_at: string
}

// ── Dashboard 待辦提醒 ──────────────────────────────────────────────────────────
// 2026-07-11 新增：登入者自己部門待填（依 CpDepartment.owner_user_id 判斷）+
// （若有簽核權限）全部待簽核。目前只做 Dashboard 卡片，不做 email 通知。
// 2026-07-17：拿掉送出/核准狀態機，pending_approval 改名 pending_close
// （本月還沒關閉、需要買家記得關閉的請購單，依 cycle_purchase_close 權限判斷）。
export interface TodoSummary {
  my_pending: CpRequest[]
  pending_close_count: number
  pending_close: CpRequest[]
}
