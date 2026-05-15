/**
 * 核准請款單月報表（Phase 2）
 *
 * TAB 順序：
 *   TAB-1  請款單清單（訂單級）
 *   TAB-2  請款單月報明細（品項級）
 *   TAB-3  總表（請購 + 請款合併）
 *   TAB-4  部門統計（雙色） + 同步狀態（admin 折疊）
 *   TAB-5  資料異常稽核
 *
 * 注意：purchase 相關 state / 函式保留（combined / audit TAB 仍需要）
 */
import { useEffect, useState, useCallback, useRef } from 'react'
import {
  Card,
  Col,
  Row,
  Statistic,
  Select,
  Input,
  Table,
  Tag,
  Button,
  Tabs,
  Spin,
  Space,
  Typography,
  Alert,
  DatePicker,
  Segmented,
  Tooltip,
  Badge,
  Progress,
  Modal,
  message,
  Drawer,
  Descriptions,
  Collapse,
} from 'antd'
import {
  FileExcelOutlined,
  SyncOutlined,
  DollarOutlined,
  ShoppingCartOutlined,
  TeamOutlined,
  BarChartOutlined,
  EyeOutlined,
  CreditCardOutlined,
  ApartmentOutlined,
  BankOutlined,
  WarningOutlined,
  ExceptionOutlined,
  LinkOutlined,
} from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import {
  getPurchaseMonthlyItems,
  getPurchaseSummary,
  getPurchaseDeptList,
  exportPurchaseReport,
  triggerPurchaseSync,
  getPurchaseSyncStatus,
  getPurchaseAvailableMonths,
  getPurchaseAccountCategories,
  getApprovedOrders,
  getApprovedOrderDetail,
  getPurchaseAuditAnomalies,
  getPurchaseAuditSummary,
  type PurchaseReportItem,
  type PurchaseReportSummary,
  type PurchaseSyncStatus,
  type PurchaseOrder,
  type PurchaseOrderDetail,
  type AuditAnomaly,
  type AuditSummary,
} from '@/api/purchaseReport'
import {
  getClaimOrders,
  getClaimOrderDetail,
  getClaimMonthlyItems,
  getClaimSummary,
  getClaimDepartments,
  getClaimAvailableMonths,
  getClaimPaymentTypes,
  getClaimAccountSubjects,
  exportClaimReport,
  triggerClaimSync,
  getClaimSyncStatus,
  getClaimAuditAnomalies,
  getClaimAuditSummary,
  type ClaimOrder,
  type ClaimOrderDetail,
  type ClaimReportItem,
  type ClaimReportSummary,
  type ClaimDeptStat,
  type ClaimSyncStatus,
} from '@/api/claimReport'
import {
  getCombinedSummary,
  getCombinedDepartments,
  type CombinedSummary,
  type CombinedDeptStat,
} from '@/api/combinedReport'
import { useAuthStore } from '@/stores/authStore'

const { Title, Text } = Typography

// ── 數字格式化 ──────────────────────────────────────────────────────────────────
const fmt = (n: number | null | undefined) =>
  n == null ? '-' : new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 0 }).format(n)

// ── 預設年月（上個月） ──────────────────────────────────────────────────────────
const defaultYearMonth = () => dayjs().subtract(1, 'month').format('YYYY-MM')

const PAGE_SIZE = 50
const STORAGE_KEY = 'claim_report_year_month'

// ── 簽核狀態 Tag ────────────────────────────────────────────────────────────────
const statusTag = (v: string) => {
  if (v === 'F')   return <Tag color="green">已核准</Tag>
  if (v === 'REJ') return <Tag color="red">退回</Tag>
  return <Tag color="orange">待審</Tag>
}

// ── 付款種類 Tag ─────────────────────────────────────────────────────────────────
const paymentTag = (v: string | null) => {
  if (!v) return <span style={{ color: '#aaa' }}>—</span>
  const color = v.includes('匯款') ? 'blue' : 'cyan'
  return <Tag color={color}>{v}</Tag>
}

export default function ClaimReportPage() {
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const isAdmin = hasPermission('system_admin_only')

  // ── 共用篩選 ──────────────────────────────────────────────────────────────────
  const savedYm = localStorage.getItem(STORAGE_KEY) || defaultYearMonth()
  const [yearMonth, setYearMonth]       = useState<string>(savedYm)
  const [pickerValue, setPickerValue]   = useState<Dayjs | null>(dayjs(savedYm, 'YYYY-MM'))
  // ── 日期模式 ──────────────────────────────────────────────────────────────────
  const [dateMode, setDateMode]         = useState<'month' | 'year' | 'range'>('month')
  const [yearPickerValue, setYearPickerValue] = useState<Dayjs | null>(null)
  const [rangeValues, setRangeValues]   = useState<[Dayjs | null, Dayjs | null]>([null, null])
  const [yearMonthFrom, setYearMonthFrom] = useState<string | undefined>(undefined)
  const [yearMonthTo, setYearMonthTo]   = useState<string | undefined>(undefined)
  const [deptFilter, setDeptFilter]     = useState<string | undefined>(undefined)
  const [availableMonths, setAvailableMonths] = useState<string[]>([])
  const initialMonthLoaded              = useRef(false)

  // ── 請購專用篩選 ──────────────────────────────────────────────────────────────
  const [accountFilter, setAccountFilter]       = useState<string | undefined>(undefined)
  const [searchInput, setSearchInput]           = useState<string>('')
  const [searchKeyword, setSearchKeyword]       = useState<string>('')
  const [accountOptions, setAccountOptions]     = useState<string[]>([])

  // ── 請款專用篩選 ──────────────────────────────────────────────────────────────
  const [paymentTypeFilter, setPaymentTypeFilter]     = useState<string | undefined>(undefined)
  const [claimAccountFilter, setClaimAccountFilter]   = useState<string | undefined>(undefined)
  const [claimSearchInput, setClaimSearchInput]       = useState<string>('')
  const [claimSearchKeyword, setClaimSearchKeyword]   = useState<string>('')
  const [paymentTypeOptions, setPaymentTypeOptions]   = useState<string[]>([])
  const [claimAccountOptions, setClaimAccountOptions] = useState<string[]>([])


  // ── 下拉選項 ──────────────────────────────────────────────────────────────────
  const [deptOptions, setDeptOptions] = useState<string[]>([])

  // ── Tab ───────────────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<string>('claim-orders')

  // ── 請購資料 ──────────────────────────────────────────────────────────────────
  const [purchaseSummary, setPurchaseSummary]   = useState<PurchaseReportSummary | null>(null)
  const [purchaseSummaryLoading, setPurchaseSummaryLoading] = useState(false)
  const [orders, setOrders]                     = useState<PurchaseOrder[]>([])
  const [ordersTotal, setOrdersTotal]           = useState(0)
  const [ordersPage, setOrdersPage]             = useState(1)
  const [ordersLoading, setOrdersLoading]       = useState(false)
  const [items, setItems]                       = useState<PurchaseReportItem[]>([])
  const [itemsTotal, setItemsTotal]             = useState(0)
  const [itemsPage, setItemsPage]               = useState(1)
  const [itemsLoading, setItemsLoading]         = useState(false)
  const [purchaseSyncStatus, setPurchaseSyncStatus] = useState<PurchaseSyncStatus | null>(null)
  const [purchaseSyncLoading, setPurchaseSyncLoading] = useState(false)
  const [purchaseSyncing, setPurchaseSyncing]   = useState(false)
  const [exportPurchaseLoading, setExportPurchaseLoading] = useState(false)

  // ── 請款資料 ──────────────────────────────────────────────────────────────────
  const [claimSummary, setClaimSummary]           = useState<ClaimReportSummary | null>(null)
  const [claimSummaryLoading, setClaimSummaryLoading] = useState(false)
  const [claimOrders, setClaimOrders]             = useState<ClaimOrder[]>([])
  const [claimOrdersTotal, setClaimOrdersTotal]   = useState(0)
  const [claimOrdersPage, setClaimOrdersPage]     = useState(1)
  const [claimOrdersLoading, setClaimOrdersLoading] = useState(false)
  const [claimItems, setClaimItems]               = useState<ClaimReportItem[]>([])
  const [claimItemsTotal, setClaimItemsTotal]     = useState(0)
  const [claimItemsPage, setClaimItemsPage]       = useState(1)
  const [claimItemsLoading, setClaimItemsLoading] = useState(false)
  const [claimDeptStats, setClaimDeptStats]       = useState<ClaimDeptStat[]>([])
  const [claimSyncStatus, setClaimSyncStatus]     = useState<ClaimSyncStatus | null>(null)
  const [claimSyncLoading, setClaimSyncLoading]   = useState(false)
  const [claimSyncing, setClaimSyncing]           = useState(false)
  const [exportClaimLoading, setExportClaimLoading] = useState(false)

  // ── 部門統計資料 ──────────────────────────────────────────────────────────────
  const [combinedSummary, setCombinedSummary]       = useState<CombinedSummary | null>(null)
  const [combinedSummaryLoading, setCombinedSummaryLoading] = useState(false)
  const [combinedDeptStats, setCombinedDeptStats]   = useState<CombinedDeptStat[]>([])
  const [combinedDeptLoading, setCombinedDeptLoading] = useState(false)

  // ── 資料異常稽核 ──────────────────────────────────────────────────────────────
  const [auditSummaryP, setAuditSummaryP]       = useState<AuditSummary | null>(null)
  const [auditSummaryC, setAuditSummaryC]       = useState<AuditSummary | null>(null)
  const [auditSummaryLoading, setAuditSummaryLoading] = useState(false)
  const [auditAnomalies, setAuditAnomalies]     = useState<AuditAnomaly[]>([])
  const [auditTotal, setAuditTotal]             = useState(0)
  const [auditLoading, setAuditLoading]         = useState(false)
  const [auditSourceFilter, setAuditSourceFilter] = useState<'all' | 'purchase' | 'claim'>('all')
  const [auditRuleFilter, setAuditRuleFilter]   = useState<string | undefined>(undefined)

  // ── 請購 Detail Drawer ────────────────────────────────────────────────────────
  const [selectedOrder, setSelectedOrder]     = useState<PurchaseOrderDetail | null>(null)
  const [drawerOpen, setDrawerOpen]           = useState(false)
  const [drawerLoading, setDrawerLoading]     = useState(false)

  // ── 請款 Detail Drawer ────────────────────────────────────────────────────────
  const [selectedClaimOrder, setSelectedClaimOrder] = useState<ClaimOrderDetail | null>(null)
  const [claimDrawerOpen, setClaimDrawerOpen]       = useState(false)
  const [claimDrawerLoading, setClaimDrawerLoading] = useState(false)

  // ── 初始化：載入下拉選項 + 可用月份 ──────────────────────────────────────────
  useEffect(() => {
    getPurchaseDeptList().then((r) => setDeptOptions(r.data ?? []))
    getPurchaseAccountCategories().then((r) => setAccountOptions(r.data ?? []))
    getClaimPaymentTypes().then((r) => setPaymentTypeOptions(r.data ?? []))
    getClaimAccountSubjects().then((r) => setClaimAccountOptions(r.data ?? []))

    Promise.all([
      getPurchaseAvailableMonths(),
      getClaimAvailableMonths(),
    ]).then(([pr, cr]) => {
      const months = Array.from(new Set([...(pr.data ?? []), ...(cr.data ?? [])])).sort().reverse()
      setAvailableMonths(months)
      if (!initialMonthLoaded.current && months.length > 0) {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (!stored || !months.includes(stored)) {
          initialMonthLoaded.current = true
          setYearMonth(months[0])
          setPickerValue(dayjs(months[0], 'YYYY-MM'))
          localStorage.setItem(STORAGE_KEY, months[0])
        }
      }
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Load 函數：請購 ───────────────────────────────────────────────────────────
  const loadPurchaseSummary = useCallback(() => {
    setPurchaseSummaryLoading(true)
    getPurchaseSummary({ year_month: yearMonthFrom ? undefined : yearMonth, year_month_from: yearMonthFrom, year_month_to: yearMonthTo, department: deptFilter, account_category: accountFilter })
      .then((r) => setPurchaseSummary(r.data))
      .finally(() => setPurchaseSummaryLoading(false))
  }, [yearMonth, yearMonthFrom, yearMonthTo, deptFilter, accountFilter])

  const loadOrders = useCallback((page = 1) => {
    setOrdersLoading(true)
    setOrdersPage(page)
    getApprovedOrders({
      year_month: yearMonthFrom ? undefined : yearMonth,
      year_month_from: yearMonthFrom, year_month_to: yearMonthTo,
      department: deptFilter, account_category: accountFilter,
      keyword: searchKeyword || undefined, page, per_page: 20,
    })
      .then((r) => { setOrders(r.data.items ?? []); setOrdersTotal(r.data.total ?? 0) })
      .finally(() => setOrdersLoading(false))
  }, [yearMonth, yearMonthFrom, yearMonthTo, deptFilter, accountFilter, searchKeyword])

  const loadItems = useCallback((page = 1) => {
    setItemsLoading(true)
    setItemsPage(page)
    getPurchaseMonthlyItems({
      year_month: yearMonthFrom ? undefined : yearMonth,
      year_month_from: yearMonthFrom, year_month_to: yearMonthTo,
      department: deptFilter, account_category: accountFilter,
      q: searchKeyword || undefined, page, per_page: PAGE_SIZE,
    })
      .then((r) => { setItems(r.data.items ?? []); setItemsTotal(r.data.total ?? 0) })
      .finally(() => setItemsLoading(false))
  }, [yearMonth, yearMonthFrom, yearMonthTo, deptFilter, accountFilter, searchKeyword])

  const loadPurchaseSyncStatus = useCallback(() => {
    if (!isAdmin) return
    setPurchaseSyncLoading(true)
    getPurchaseSyncStatus()
      .then((r) => setPurchaseSyncStatus(r.data))
      .finally(() => setPurchaseSyncLoading(false))
  }, [isAdmin])

  // ── Load 函數：請款 ───────────────────────────────────────────────────────────
  const loadClaimSummary = useCallback(() => {
    setClaimSummaryLoading(true)
    getClaimSummary({ year_month: yearMonthFrom ? undefined : yearMonth, year_month_from: yearMonthFrom, year_month_to: yearMonthTo, department: deptFilter, payment_type: paymentTypeFilter, account_subject: claimAccountFilter })
      .then((r) => setClaimSummary(r.data))
      .finally(() => setClaimSummaryLoading(false))
  }, [yearMonth, yearMonthFrom, yearMonthTo, deptFilter, paymentTypeFilter, claimAccountFilter])

  const loadClaimOrders = useCallback((page = 1) => {
    setClaimOrdersLoading(true)
    setClaimOrdersPage(page)
    getClaimOrders({
      year_month: yearMonthFrom ? undefined : yearMonth,
      year_month_from: yearMonthFrom, year_month_to: yearMonthTo,
      department: deptFilter, payment_type: paymentTypeFilter,
      account_subject: claimAccountFilter, keyword: claimSearchKeyword || undefined,
      page, per_page: 20,
    })
      .then((r) => { setClaimOrders(r.data.items ?? []); setClaimOrdersTotal(r.data.total ?? 0) })
      .finally(() => setClaimOrdersLoading(false))
  }, [yearMonth, yearMonthFrom, yearMonthTo, deptFilter, paymentTypeFilter, claimAccountFilter, claimSearchKeyword])

  const loadClaimItems = useCallback((page = 1) => {
    setClaimItemsLoading(true)
    setClaimItemsPage(page)
    getClaimMonthlyItems({
      year_month: yearMonthFrom ? undefined : yearMonth,
      year_month_from: yearMonthFrom, year_month_to: yearMonthTo,
      department: deptFilter, payment_type: paymentTypeFilter,
      account_subject: claimAccountFilter, q: claimSearchKeyword || undefined,
      page, per_page: PAGE_SIZE,
    })
      .then((r) => { setClaimItems(r.data.items ?? []); setClaimItemsTotal(r.data.total ?? 0) })
      .finally(() => setClaimItemsLoading(false))
  }, [yearMonth, yearMonthFrom, yearMonthTo, deptFilter, paymentTypeFilter, claimAccountFilter, claimSearchKeyword])

  const loadClaimDeptStats = useCallback(() => {
    getClaimDepartments({ year_month: yearMonthFrom ? undefined : yearMonth, year_month_from: yearMonthFrom, year_month_to: yearMonthTo, payment_type: paymentTypeFilter, account_subject: claimAccountFilter })
      .then((r) => setClaimDeptStats(r.data ?? []))
  }, [yearMonth, yearMonthFrom, yearMonthTo, paymentTypeFilter, claimAccountFilter])

  const loadClaimSyncStatus = useCallback(() => {
    if (!isAdmin) return
    setClaimSyncLoading(true)
    getClaimSyncStatus()
      .then((r) => setClaimSyncStatus(r.data))
      .finally(() => setClaimSyncLoading(false))
  }, [isAdmin])

  // ── Load 函數：總表 ───────────────────────────────────────────────────────────
  const loadCombinedSummary = useCallback(() => {
    setCombinedSummaryLoading(true)
    getCombinedSummary({ year_month: yearMonthFrom ? undefined : yearMonth, year_month_from: yearMonthFrom, year_month_to: yearMonthTo, company: '樂群', department: deptFilter })
      .then((r) => setCombinedSummary(r.data))
      .finally(() => setCombinedSummaryLoading(false))
  }, [yearMonth, yearMonthFrom, yearMonthTo, deptFilter])

  const loadCombinedDeptStats = useCallback(() => {
    setCombinedDeptLoading(true)
    getCombinedDepartments({ year_month: yearMonthFrom ? undefined : yearMonth, year_month_from: yearMonthFrom, year_month_to: yearMonthTo, company: '樂群' })
      .then((r) => setCombinedDeptStats(r.data ?? []))
      .finally(() => setCombinedDeptLoading(false))
  }, [yearMonth, yearMonthFrom, yearMonthTo])

  // ── Load 函數：資料異常稽核 ───────────────────────────────────────────────────
  const loadAuditSummaries = useCallback(() => {
    setAuditSummaryLoading(true)
    const params = {
      year_month: yearMonthFrom ? undefined : yearMonth,
      year_month_from: yearMonthFrom,
      year_month_to: yearMonthTo,
      department: deptFilter,
    }
    Promise.all([getPurchaseAuditSummary(params), getClaimAuditSummary(params)])
      .then(([pr, cr]) => { setAuditSummaryP(pr.data); setAuditSummaryC(cr.data) })
      .finally(() => setAuditSummaryLoading(false))
  }, [yearMonth, yearMonthFrom, yearMonthTo, deptFilter])

  const loadAuditAnomalies = useCallback(() => {
    setAuditLoading(true)
    const params = {
      year_month: yearMonthFrom ? undefined : yearMonth,
      year_month_from: yearMonthFrom,
      year_month_to: yearMonthTo,
      department: deptFilter,
      rule_code: auditRuleFilter,
      page: 1, per_page: 200,
    }
    const fetchP = auditSourceFilter !== 'claim'
      ? getPurchaseAuditAnomalies(params)
      : Promise.resolve({ data: { total: 0, page: 1, per_page: 200, items: [] as AuditAnomaly[] } })
    const fetchC = auditSourceFilter !== 'purchase'
      ? getClaimAuditAnomalies(params)
      : Promise.resolve({ data: { total: 0, page: 1, per_page: 200, items: [] as AuditAnomaly[] } })
    const sevOrd: Record<string, number> = { high: 0, medium: 1, low: 2 }
    Promise.all([fetchP, fetchC]).then(([pr, cr]) => {
      const all = [...(pr.data?.items ?? []), ...(cr.data?.items ?? [])]
      all.sort((a, b) => {
        const sv = (sevOrd[a.severity] ?? 9) - (sevOrd[b.severity] ?? 9)
        if (sv !== 0) return sv
        return (b.approved_date || '').localeCompare(a.approved_date || '')
      })
      setAuditAnomalies(all)
      setAuditTotal(all.length)
    }).finally(() => setAuditLoading(false))
  }, [yearMonth, yearMonthFrom, yearMonthTo, deptFilter, auditSourceFilter, auditRuleFilter])

  // ── 篩選條件變更 → 重新載入對應 TAB 資料 ─────────────────────────────────────
  useEffect(() => {
    loadPurchaseSummary()
    loadClaimSummary()
    loadCombinedSummary()
    loadAuditSummaries()

    if (activeTab === 'purchase-orders' || activeTab === 'purchase-detail') {
      loadOrders(1)
      loadItems(1)
    } else if (activeTab === 'claim-orders' || activeTab === 'claim-detail') {
      loadClaimOrders(1)
      loadClaimItems(1)
    } else if (activeTab === 'dept') {
      loadCombinedDeptStats()
    } else if (activeTab === 'audit') {
      loadAuditAnomalies()
    }
  }, [yearMonth, yearMonthFrom, yearMonthTo, deptFilter, accountFilter, searchKeyword, paymentTypeFilter, claimAccountFilter, claimSearchKeyword]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── TAB 切換 → 載入新 TAB 資料 ───────────────────────────────────────────────
  useEffect(() => {
    if (activeTab === 'purchase-orders') { loadOrders(1); loadItems(1) }
    else if (activeTab === 'purchase-detail') { loadItems(1) }
    else if (activeTab === 'claim-orders') { loadClaimOrders(1); loadClaimItems(1) }
    else if (activeTab === 'claim-detail') { loadClaimItems(1) }
    else if (activeTab === 'dept') {
      loadCombinedDeptStats()
      loadClaimDeptStats()
      if (isAdmin) { loadPurchaseSyncStatus(); loadClaimSyncStatus() }
    }
    else if (activeTab === 'audit') { loadAuditAnomalies() }
  }, [activeTab]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── 稽核篩選（規則 / 來源）變更 → 重新載入異常列表 ───────────────────────────
  useEffect(() => {
    if (activeTab === 'audit') loadAuditAnomalies()
  }, [auditRuleFilter, auditSourceFilter]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── 日期模式切換 & 個別 Picker 處理器 ────────────────────────────────────────
  const handleMonthChange = (v: Dayjs | null) => {
    if (!v) return
    const ym = v.format('YYYY-MM')
    setPickerValue(v)
    setYearMonth(ym)
    setYearMonthFrom(undefined)
    setYearMonthTo(undefined)
    localStorage.setItem(STORAGE_KEY, ym)
  }

  const handleYearChange = (v: Dayjs | null) => {
    setYearPickerValue(v)
    if (v) {
      const y = v.year()
      setYearMonthFrom(`${y}-01`)
      setYearMonthTo(`${y}-12`)
    } else {
      setYearMonthFrom(undefined)
      setYearMonthTo(undefined)
    }
  }

  const handleRangeChange = (vals: [Dayjs | null, Dayjs | null] | null) => {
    if (!vals) {
      setRangeValues([null, null])
      setYearMonthFrom(undefined)
      setYearMonthTo(undefined)
      return
    }
    setRangeValues(vals)
    if (vals[0] && vals[1]) {
      setYearMonthFrom(vals[0].format('YYYY-MM'))
      setYearMonthTo(vals[1].format('YYYY-MM'))
    }
  }

  const handleDateModeChange = (mode: string) => {
    const m = mode as 'month' | 'year' | 'range'
    setDateMode(m)
    if (m === 'month') {
      setYearMonthFrom(undefined)
      setYearMonthTo(undefined)
    } else if (m === 'year') {
      const v = yearPickerValue || dayjs()
      setYearPickerValue(v)
      const y = v.year()
      setYearMonthFrom(`${y}-01`)
      setYearMonthTo(`${y}-12`)
    } else if (m === 'range') {
      if (rangeValues[0] && rangeValues[1]) {
        setYearMonthFrom(rangeValues[0].format('YYYY-MM'))
        setYearMonthTo(rangeValues[1].format('YYYY-MM'))
      } else {
        setYearMonthFrom(undefined)
        setYearMonthTo(undefined)
      }
    }
  }

  // ── 匯出 Excel ────────────────────────────────────────────────────────────────
  const handleExportPurchase = async () => {
    setExportPurchaseLoading(true)
    const label = yearMonthFrom
      ? (yearMonthFrom.endsWith('-01') && yearMonthTo?.endsWith('-12') && yearMonthFrom.slice(0, 4) === yearMonthTo?.slice(0, 4)
        ? `${yearMonthFrom.slice(0, 4)}年度`
        : `${yearMonthFrom}~${yearMonthTo}`)
      : yearMonth
    try {
      const res = await exportPurchaseReport({
        year_month: yearMonthFrom ? undefined : yearMonth,
        year_month_from: yearMonthFrom, year_month_to: yearMonthTo,
        department: deptFilter, account_category: accountFilter,
      })
      const url = URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a'); a.href = url
      a.download = `核准請購單月報表_${label}${deptFilter ? '_' + deptFilter : ''}.xlsx`
      a.click(); URL.revokeObjectURL(url)
    } catch { message.error('匯出失敗，請稍後再試') }
    finally { setExportPurchaseLoading(false) }
  }

  const handleExportClaim = async () => {
    setExportClaimLoading(true)
    const label = yearMonthFrom
      ? (yearMonthFrom.endsWith('-01') && yearMonthTo?.endsWith('-12') && yearMonthFrom.slice(0, 4) === yearMonthTo?.slice(0, 4)
        ? `${yearMonthFrom.slice(0, 4)}年度`
        : `${yearMonthFrom}~${yearMonthTo}`)
      : yearMonth
    try {
      const res = await exportClaimReport({
        year_month: yearMonthFrom ? undefined : yearMonth,
        year_month_from: yearMonthFrom, year_month_to: yearMonthTo,
        department: deptFilter, payment_type: paymentTypeFilter, account_subject: claimAccountFilter,
      })
      const url = URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a'); a.href = url
      a.download = `核准請款單月報表_${label}${deptFilter ? '_' + deptFilter : ''}.xlsx`
      a.click(); URL.revokeObjectURL(url)
    } catch { message.error('匯出失敗，請稍後再試') }
    finally { setExportClaimLoading(false) }
  }

  // ── 觸發同步 ──────────────────────────────────────────────────────────────────
  const handlePurchaseSync = async (fullResync = false) => {
    setPurchaseSyncing(true)
    try {
      await triggerPurchaseSync(fullResync)
      message.success('請購同步已觸發，請稍後重新整理')
      setTimeout(() => loadPurchaseSyncStatus(), 3000)
    } catch { message.error('同步觸發失敗') }
    finally { setPurchaseSyncing(false) }
  }

  const handleClaimSync = async (fullResync = false) => {
    setClaimSyncing(true)
    try {
      await triggerClaimSync(fullResync)
      message.success('請款同步已觸發，請稍後重新整理')
      setTimeout(() => loadClaimSyncStatus(), 3000)
    } catch { message.error('同步觸發失敗') }
    finally { setClaimSyncing(false) }
  }

  // ── Drawer 開啟 ──────────────────────────────────────────────────────────────
  const openPurchaseDrawer = async (orderId: number) => {
    setDrawerOpen(true); setDrawerLoading(true)
    try { const res = await getApprovedOrderDetail(orderId); setSelectedOrder(res.data) }
    catch { message.error('載入明細失敗') }
    finally { setDrawerLoading(false) }
  }

  const openClaimDrawer = async (orderId: number) => {
    setClaimDrawerOpen(true); setClaimDrawerLoading(true)
    try { const res = await getClaimOrderDetail(orderId); setSelectedClaimOrder(res.data) }
    catch { message.error('載入請款明細失敗') }
    finally { setClaimDrawerLoading(false) }
  }

  // ── 欄位定義：請購單清單 ──────────────────────────────────────────────────────
  const purchaseOrderColumns = [
    { title: '編號', dataIndex: 'purchase_no', key: 'purchase_no', width: 190, ellipsis: true, fixed: 'left' as const,
      render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v || '-'}</span>,
      sorter: (a: PurchaseOrder, b: PurchaseOrder) => (a.purchase_no ?? '').localeCompare(b.purchase_no ?? '') },
    { title: '部門', dataIndex: 'department_display', key: 'dept', width: 80,
      render: (v: string) => <Tag color="blue">{v}</Tag>,
      sorter: (a: PurchaseOrder, b: PurchaseOrder) => a.department_display.localeCompare(b.department_display) },
    { title: '會科', dataIndex: 'account_category', key: 'account_category', width: 110, ellipsis: true,
      sorter: (a: PurchaseOrder, b: PurchaseOrder) => (a.account_category ?? '').localeCompare(b.account_category ?? '') },
    { title: '申請人', dataIndex: 'applicant', key: 'applicant', width: 80,
      sorter: (a: PurchaseOrder, b: PurchaseOrder) => (a.applicant ?? '').localeCompare(b.applicant ?? '') },
    { title: '說明', dataIndex: 'description', key: 'description', ellipsis: true,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span>,
      sorter: (a: PurchaseOrder, b: PurchaseOrder) => (a.description ?? '').localeCompare(b.description ?? '') },
    { title: '全案小計', dataIndex: 'amount', key: 'amount', width: 110, align: 'right' as const,
      render: (v: number | null) => <span style={{ fontWeight: 600, color: '#1B3A5C' }}>{fmt(v)}</span>,
      sorter: (a: PurchaseOrder, b: PurchaseOrder) => (a.amount ?? 0) - (b.amount ?? 0) },
    { title: '狀態', dataIndex: 'status', key: 'status', width: 80, render: statusTag,
      sorter: (a: PurchaseOrder, b: PurchaseOrder) => a.status.localeCompare(b.status) },
    { title: '核准日期', dataIndex: 'approved_date', key: 'approved_date', width: 100,
      render: (v: string | null) => <span style={{ fontSize: 12, color: '#666' }}>{v || '-'}</span>,
      sorter: (a: PurchaseOrder, b: PurchaseOrder) => (a.approved_date ?? '').localeCompare(b.approved_date ?? '') },
    { title: '', key: 'action', width: 48, fixed: 'right' as const,
      render: (_: unknown, r: PurchaseOrder) => (
        <Button type="link" size="small" icon={<EyeOutlined />}
          onClick={(e) => { e.stopPropagation(); openPurchaseDrawer(r.id) }} style={{ padding: 0 }} />
      ) },
  ]

  // ── 欄位定義：請購月報明細 ────────────────────────────────────────────────────
  const purchaseDetailColumns = [
    { title: '核准日期', dataIndex: 'approved_date', key: 'approved_date', width: 100,
      render: (v: string | null) => v ?? '-', fixed: 'left' as const,
      sorter: (a: PurchaseReportItem, b: PurchaseReportItem) => (a.approved_date ?? '').localeCompare(b.approved_date ?? '') },
    { title: '部門', dataIndex: 'department_display', key: 'dept', width: 80, fixed: 'left' as const,
      render: (v: string) => <Tag color="blue">{v}</Tag>,
      sorter: (a: PurchaseReportItem, b: PurchaseReportItem) => a.department_display.localeCompare(b.department_display) },
    { title: '申請單號', dataIndex: 'purchase_no', key: 'purchase_no', width: 175,
      sorter: (a: PurchaseReportItem, b: PurchaseReportItem) => (a.purchase_no ?? '').localeCompare(b.purchase_no ?? '') },
    { title: '會科', dataIndex: 'account_category', key: 'account_category', width: 130, ellipsis: true,
      sorter: (a: PurchaseReportItem, b: PurchaseReportItem) => (a.account_category ?? '').localeCompare(b.account_category ?? '') },
    { title: '申請人', dataIndex: 'applicant', key: 'applicant', width: 80,
      sorter: (a: PurchaseReportItem, b: PurchaseReportItem) => (a.applicant ?? '').localeCompare(b.applicant ?? '') },
    { title: '品名', dataIndex: 'product_name', key: 'product_name', minWidth: 140, ellipsis: true,
      render: (v: string) => v || <Text type="secondary">（未同步品項）</Text>,
      sorter: (a: PurchaseReportItem, b: PurchaseReportItem) => (a.product_name ?? '').localeCompare(b.product_name ?? '') },
    { title: '數量', dataIndex: 'qty', key: 'qty', width: 60, align: 'right' as const,
      render: (v: number | null) => v ?? '-',
      sorter: (a: PurchaseReportItem, b: PurchaseReportItem) => (a.qty ?? 0) - (b.qty ?? 0) },
    { title: '單位', dataIndex: 'unit', key: 'unit', width: 55 },
    { title: '選用廠商', dataIndex: 'selected_vendor', key: 'selected_vendor', width: 150,
      sorter: (a: PurchaseReportItem, b: PurchaseReportItem) => (a.selected_vendor ?? '').localeCompare(b.selected_vendor ?? '') },
    { title: '品項金額', dataIndex: 'selected_amount', key: 'selected_amount', width: 110, align: 'right' as const,
      render: (v: number | null) => <span style={{ whiteSpace: 'nowrap' }}>{fmt(v)}</span>,
      sorter: (a: PurchaseReportItem, b: PurchaseReportItem) => (a.selected_amount ?? 0) - (b.selected_amount ?? 0) },
    { title: '全案小計(未稅)', dataIndex: 'amount', key: 'amount', width: 135, align: 'right' as const,
      render: (v: number | null, r: PurchaseReportItem, idx: number) => {
        const prev = items[idx - 1]?.order_id
        if (idx === 0 || prev !== r.order_id)
          return <span style={{ fontWeight: 600, color: '#1B3A5C', whiteSpace: 'nowrap' }}>{fmt(v)}</span>
        return <span style={{ color: '#aaa' }}>—</span>
      },
      sorter: (a: PurchaseReportItem, b: PurchaseReportItem) => (a.amount ?? 0) - (b.amount ?? 0) },
    { title: '營業稅', dataIndex: 'amount_tax', key: 'amount_tax', width: 90, align: 'right' as const,
      render: (v: number | null, r: PurchaseReportItem, idx: number) => {
        const prev = items[idx - 1]?.order_id
        if (idx === 0 || prev !== r.order_id) return <span style={{ whiteSpace: 'nowrap' }}>{fmt(v)}</span>
        return <span style={{ color: '#aaa' }}>—</span>
      },
      sorter: (a: PurchaseReportItem, b: PurchaseReportItem) => (a.amount_tax ?? 0) - (b.amount_tax ?? 0) },
  ]

  // ── 欄位定義：請款單清單 ──────────────────────────────────────────────────────
  const claimOrderColumns = [
    { title: '單號', dataIndex: 'request_no', key: 'request_no', width: 180, ellipsis: true, fixed: 'left' as const,
      render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v || '-'}</span>,
      sorter: (a: ClaimOrder, b: ClaimOrder) => (a.request_no ?? '').localeCompare(b.request_no ?? '') },
    { title: '部門', dataIndex: 'department_display', key: 'dept', width: 80,
      render: (v: string) => <Tag color="orange">{v}</Tag>,
      sorter: (a: ClaimOrder, b: ClaimOrder) => a.department_display.localeCompare(b.department_display) },
    { title: '會科', dataIndex: 'account_subject', key: 'account_subject', width: 120, ellipsis: true,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span>,
      sorter: (a: ClaimOrder, b: ClaimOrder) => (a.account_subject ?? '').localeCompare(b.account_subject ?? '') },
    { title: '付款種類', dataIndex: 'payment_type', key: 'payment_type', width: 90, render: paymentTag,
      sorter: (a: ClaimOrder, b: ClaimOrder) => (a.payment_type ?? '').localeCompare(b.payment_type ?? '') },
    { title: '申請人', dataIndex: 'applicant', key: 'applicant', width: 80,
      sorter: (a: ClaimOrder, b: ClaimOrder) => (a.applicant ?? '').localeCompare(b.applicant ?? '') },
    { title: '事由', dataIndex: 'purpose_description', key: 'purpose_description', ellipsis: true,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span>,
      sorter: (a: ClaimOrder, b: ClaimOrder) => (a.purpose_description ?? '').localeCompare(b.purpose_description ?? '') },
    { title: '受款人', dataIndex: 'payee', key: 'payee', width: 100, ellipsis: true,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span>,
      sorter: (a: ClaimOrder, b: ClaimOrder) => (a.payee ?? '').localeCompare(b.payee ?? '') },
    { title: '應付金額', dataIndex: 'payable_amount', key: 'payable_amount', width: 110, align: 'right' as const,
      render: (v: number | null) => <span style={{ fontWeight: 600, color: '#d46b08' }}>{fmt(v)}</span>,
      sorter: (a: ClaimOrder, b: ClaimOrder) => (a.payable_amount ?? 0) - (b.payable_amount ?? 0) },
    { title: '狀態', dataIndex: 'status', key: 'status', width: 80, render: statusTag,
      sorter: (a: ClaimOrder, b: ClaimOrder) => a.status.localeCompare(b.status) },
    { title: '核准日期', dataIndex: 'approved_date', key: 'approved_date', width: 100,
      render: (v: string | null) => <span style={{ fontSize: 12, color: '#666' }}>{v || '-'}</span>,
      sorter: (a: ClaimOrder, b: ClaimOrder) => (a.approved_date ?? '').localeCompare(b.approved_date ?? '') },
    { title: '', key: 'action', width: 48, fixed: 'right' as const,
      render: (_: unknown, r: ClaimOrder) => (
        <Button type="link" size="small" icon={<EyeOutlined />}
          onClick={(e) => { e.stopPropagation(); openClaimDrawer(r.id) }} style={{ padding: 0 }} />
      ) },
  ]

  // ── 欄位定義：請款月報明細 ────────────────────────────────────────────────────
  const claimDetailColumns = [
    { title: '核准日期', dataIndex: 'approved_date', key: 'approved_date', width: 100,
      render: (v: string | null) => v ?? '-', fixed: 'left' as const,
      sorter: (a: ClaimReportItem, b: ClaimReportItem) => (a.approved_date ?? '').localeCompare(b.approved_date ?? '') },
    { title: '部門', dataIndex: 'department_display', key: 'dept', width: 80, fixed: 'left' as const,
      render: (v: string) => <Tag color="orange">{v}</Tag>,
      sorter: (a: ClaimReportItem, b: ClaimReportItem) => a.department_display.localeCompare(b.department_display) },
    { title: '申請單號', dataIndex: 'request_no', key: 'request_no', width: 180, ellipsis: true,
      render: (v: string | null) => (
        <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v || '-'}</span>
      ),
      sorter: (a: ClaimReportItem, b: ClaimReportItem) => (a.request_no ?? '').localeCompare(b.request_no ?? '') },
    { title: '會科', dataIndex: 'account_subject', key: 'account_subject', width: 120, ellipsis: true,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span>,
      sorter: (a: ClaimReportItem, b: ClaimReportItem) => (a.account_subject ?? '').localeCompare(b.account_subject ?? '') },
    { title: '付款種類', dataIndex: 'payment_type', key: 'payment_type', width: 90, render: paymentTag,
      sorter: (a: ClaimReportItem, b: ClaimReportItem) => (a.payment_type ?? '').localeCompare(b.payment_type ?? '') },
    { title: '事由', dataIndex: 'purpose_description', key: 'purpose_description', minWidth: 120, ellipsis: true,
      sorter: (a: ClaimReportItem, b: ClaimReportItem) => (a.purpose_description ?? '').localeCompare(b.purpose_description ?? '') },
    { title: '品名', dataIndex: 'item_name', key: 'item_name', minWidth: 120, ellipsis: true,
      render: (v: string | null) => v || <Text type="secondary">—</Text>,
      sorter: (a: ClaimReportItem, b: ClaimReportItem) => (a.item_name ?? '').localeCompare(b.item_name ?? '') },
    { title: '數量', dataIndex: 'quantity', key: 'quantity', width: 60, align: 'right' as const,
      render: (v: string | null) => v ?? '-',
      sorter: (a: ClaimReportItem, b: ClaimReportItem) => parseFloat(a.quantity ?? '0') - parseFloat(b.quantity ?? '0') },
    { title: '單位', dataIndex: 'unit', key: 'unit', width: 55 },
    { title: '品項金額', dataIndex: 'proposed_vendor_amount', key: 'pva', width: 100, align: 'right' as const,
      render: (v: number | null) => <span style={{ whiteSpace: 'nowrap' }}>{fmt(v)}</span>,
      sorter: (a: ClaimReportItem, b: ClaimReportItem) => (a.proposed_vendor_amount ?? 0) - (b.proposed_vendor_amount ?? 0) },
    { title: '應付合計', dataIndex: 'payable_amount', key: 'payable_amount', width: 110, align: 'right' as const,
      render: (v: number | null, r: ClaimReportItem, idx: number) => {
        const prev = claimItems[idx - 1]?.claim_id
        if (idx === 0 || prev !== r.claim_id)
          return <span style={{ fontWeight: 600, color: '#d46b08', whiteSpace: 'nowrap' }}>{fmt(v)}</span>
        return <span style={{ color: '#aaa' }}>—</span>
      },
      sorter: (a: ClaimReportItem, b: ClaimReportItem) => (a.payable_amount ?? 0) - (b.payable_amount ?? 0) },
    { title: '發票號碼', dataIndex: 'invoice_no', key: 'invoice_no', width: 110, ellipsis: true,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span>,
      sorter: (a: ClaimReportItem, b: ClaimReportItem) => (a.invoice_no ?? '').localeCompare(b.invoice_no ?? '') },
  ]

  // ── 欄位定義：部門統計（雙色） ────────────────────────────────────────────────
  const combinedDeptColumns = [
    { title: '部門', dataIndex: 'department_display', key: 'dept', width: 90,
      render: (v: string) => <Tag color="geekblue">{v}</Tag>,
      sorter: (a: CombinedDeptStat, b: CombinedDeptStat) => a.department_display.localeCompare(b.department_display) },
    // 請購（藍）
    { title: <span style={{ color: '#1B3A5C' }}>請購單數</span>, dataIndex: 'purchase_count', key: 'pc',
      align: 'right' as const, width: 90,
      render: (v: number) => <span style={{ color: '#1B3A5C' }}>{v}</span>,
      sorter: (a: CombinedDeptStat, b: CombinedDeptStat) => a.purchase_count - b.purchase_count },
    { title: <span style={{ color: '#1B3A5C' }}>請購未稅合計</span>, dataIndex: 'purchase_amount', key: 'pa',
      align: 'right' as const,
      render: (v: number) => <span style={{ color: '#1B3A5C', fontWeight: 600 }}>{fmt(v)}</span>,
      sorter: (a: CombinedDeptStat, b: CombinedDeptStat) => (a.purchase_amount ?? 0) - (b.purchase_amount ?? 0) },
    { title: <span style={{ color: '#1B3A5C' }}>請購稅額</span>, dataIndex: 'purchase_tax', key: 'pt',
      align: 'right' as const, width: 100,
      render: (v: number) => <span style={{ color: '#1B3A5C' }}>{fmt(v)}</span>,
      sorter: (a: CombinedDeptStat, b: CombinedDeptStat) => (a.purchase_tax ?? 0) - (b.purchase_tax ?? 0) },
    // 請款（橙）
    { title: <span style={{ color: '#d46b08' }}>請款筆數</span>, dataIndex: 'claim_count', key: 'cc',
      align: 'right' as const, width: 90,
      render: (v: number) => <span style={{ color: '#d46b08' }}>{v}</span>,
      sorter: (a: CombinedDeptStat, b: CombinedDeptStat) => a.claim_count - b.claim_count },
    { title: <span style={{ color: '#d46b08' }}>請款應付合計</span>, dataIndex: 'claim_payable', key: 'cp',
      align: 'right' as const,
      render: (v: number) => <span style={{ color: '#d46b08', fontWeight: 600 }}>{fmt(v)}</span>,
      sorter: (a: CombinedDeptStat, b: CombinedDeptStat) => (a.claim_payable ?? 0) - (b.claim_payable ?? 0) },
    { title: <span style={{ color: '#d46b08' }}>請款稅額</span>, dataIndex: 'claim_tax', key: 'ct',
      align: 'right' as const, width: 100,
      render: (v: number) => <span style={{ color: '#d46b08' }}>{fmt(v)}</span>,
      sorter: (a: CombinedDeptStat, b: CombinedDeptStat) => (a.claim_tax ?? 0) - (b.claim_tax ?? 0) },
    // 占比（以請購金額為基準）
    { title: '請購占比', key: 'ratio', width: 130,
      render: (_: unknown, r: CombinedDeptStat) => {
        const total = combinedDeptStats.reduce((s, d) => s + (d.purchase_amount ?? 0), 0)
        const pct = total > 0 ? Math.round(((r.purchase_amount ?? 0) / total) * 100) : 0
        return <Progress percent={pct} size="small" strokeColor="#4BA8E8" />
      } },
  ]

  // ── 輔助：判斷當前 Tab 群組 ────────────────────────────────────────────────────
  const isPurchaseTab  = activeTab === 'purchase-orders' || activeTab === 'purchase-detail'
  const isClaimTab     = activeTab === 'claim-orders'    || activeTab === 'claim-detail'
  const isCombinedTab  = activeTab === 'dept'

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div>
      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          {isPurchaseTab ? '核准請購單月報表' : isClaimTab ? '核准請款單月報表' : isCombinedTab ? '部門統計' : '資料異常稽核'}
        </Title>
        <Space wrap style={{ justifyContent: 'flex-end' }}>
          {/* 日期模式切換（共用） */}
          <Segmented
            value={dateMode}
            onChange={handleDateModeChange}
            options={[
              { label: '單月', value: 'month' },
              { label: '全年度', value: 'year' },
              { label: '自訂區間', value: 'range' },
            ]}
            size="small"
          />

          {/* 單月選擇器 */}
          {dateMode === 'month' && (
            <Tooltip
              title={availableMonths.length > 0
                ? `有資料的月份：${availableMonths.slice(0, 6).join('、')}${availableMonths.length > 6 ? '…' : ''}`
                : '尚無核准資料（請先執行同步）'}
            >
              <DatePicker
                picker="month" value={pickerValue} onChange={handleMonthChange}
                format="YYYY年MM月" allowClear={false} style={{ width: 140 }}
                status={availableMonths.length > 0 && !availableMonths.includes(yearMonth) ? 'warning' : undefined}
              />
            </Tooltip>
          )}

          {/* 全年度選擇器 */}
          {dateMode === 'year' && (
            <DatePicker
              picker="year" value={yearPickerValue} onChange={handleYearChange}
              format="YYYY年" allowClear={false} style={{ width: 110 }}
              placeholder="選擇年度"
            />
          )}

          {/* 自訂區間選擇器 */}
          {dateMode === 'range' && (
            <DatePicker.RangePicker
              picker="month"
              value={rangeValues}
              onChange={handleRangeChange as any}
              format="YYYY-MM"
              style={{ width: 220 }}
              placeholder={['起始月份', '結束月份']}
            />
          )}

          {/* 部門篩選（共用） */}
          <Select placeholder="全部部門" allowClear style={{ width: 120 }}
            value={deptFilter} onChange={setDeptFilter}
            options={deptOptions.map((d) => ({ label: d, value: d }))} />

          {/* 請購專用篩選 */}
          {isPurchaseTab && (
            <>
              <Select placeholder="全部會科" allowClear style={{ width: 160 }}
                value={accountFilter} onChange={setAccountFilter}
                showSearch optionFilterProp="label"
                options={accountOptions.map((a) => ({ label: a, value: a }))} />
              <Input.Search
                placeholder="說明/單號/申請人/廠商" allowClear style={{ width: 230 }}
                value={searchInput}
                onChange={(e) => { setSearchInput(e.target.value); if (!e.target.value) setSearchKeyword('') }}
                onSearch={(v) => setSearchKeyword(v.trim())}
              />
              <Button icon={<FileExcelOutlined />} loading={exportPurchaseLoading} onClick={handleExportPurchase}
                style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)', border: 'none', color: '#fff' }}>
                匯出 Excel
              </Button>
            </>
          )}

          {/* 請款專用篩選 */}
          {isClaimTab && (
            <>
              <Select placeholder="全部付款種類" allowClear style={{ width: 130 }}
                value={paymentTypeFilter} onChange={setPaymentTypeFilter}
                options={paymentTypeOptions.map((t) => ({ label: t, value: t }))} />
              <Select placeholder="全部會科" allowClear style={{ width: 160 }}
                value={claimAccountFilter} onChange={setClaimAccountFilter}
                showSearch optionFilterProp="label"
                options={claimAccountOptions.map((a) => ({ label: a, value: a }))} />
              <Input.Search
                placeholder="事由/單號/申請人/受款人" allowClear style={{ width: 230 }}
                value={claimSearchInput}
                onChange={(e) => { setClaimSearchInput(e.target.value); if (!e.target.value) setClaimSearchKeyword('') }}
                onSearch={(v) => setClaimSearchKeyword(v.trim())}
              />
              <Button icon={<FileExcelOutlined />} loading={exportClaimLoading} onClick={handleExportClaim}
                style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)', border: 'none', color: '#fff' }}>
                匯出 Excel
              </Button>
            </>
          )}

        </Space>
      </div>

      {/* ── KPI Cards ── */}
      {isPurchaseTab && (
        <Spin spinning={purchaseSummaryLoading}>
          <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="核准訂單數" value={purchaseSummary?.order_count ?? '-'}
                prefix={<ShoppingCartOutlined />} valueStyle={{ color: '#1B3A5C', fontSize: 22 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="未稅合計" value={fmt(purchaseSummary?.total_amount)}
                prefix={<DollarOutlined />} valueStyle={{ color: '#4BA8E8', fontSize: 18 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="營業稅合計" value={fmt(purchaseSummary?.total_tax)}
                valueStyle={{ color: '#52c41a', fontSize: 18 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="品項筆數" value={purchaseSummary?.item_count ?? '-'}
                prefix={<BarChartOutlined />} valueStyle={{ color: '#722ed1', fontSize: 22 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="涉及部門" value={purchaseSummary?.dept_count ?? '-'}
                prefix={<TeamOutlined />} valueStyle={{ color: '#fa8c16', fontSize: 22 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="平均單筆金額" value={fmt(purchaseSummary?.avg_amount)}
                valueStyle={{ color: '#1B3A5C', fontSize: 18 }} />
            </Card></Col>
          </Row>
        </Spin>
      )}

      {isClaimTab && (
        <Spin spinning={claimSummaryLoading}>
          <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="核准請款數" value={claimSummary?.order_count ?? '-'}
                prefix={<CreditCardOutlined />} valueStyle={{ color: '#d46b08', fontSize: 22 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="小計合計" value={fmt(claimSummary?.total_subtotal)}
                prefix={<DollarOutlined />} valueStyle={{ color: '#fa8c16', fontSize: 18 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="應付合計" value={fmt(claimSummary?.total_payable)}
                prefix={<BankOutlined />} valueStyle={{ color: '#d46b08', fontSize: 18 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="稅額合計" value={fmt(claimSummary?.total_tax)}
                valueStyle={{ color: '#52c41a', fontSize: 18 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="涉及部門" value={claimSummary?.dept_count ?? '-'}
                prefix={<TeamOutlined />} valueStyle={{ color: '#722ed1', fontSize: 22 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="平均應付金額" value={fmt(claimSummary?.avg_payable)}
                valueStyle={{ color: '#d46b08', fontSize: 18 }} />
            </Card></Col>
          </Row>
        </Spin>
      )}

      {isCombinedTab && (
        <Spin spinning={combinedSummaryLoading}>
          <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="請購訂單數" value={combinedSummary?.purchase.order_count ?? '-'}
                prefix={<ShoppingCartOutlined />} valueStyle={{ color: '#1B3A5C', fontSize: 22 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="請購未稅合計" value={fmt(combinedSummary?.purchase.total_amount)}
                prefix={<DollarOutlined />} valueStyle={{ color: '#4BA8E8', fontSize: 18 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="請款筆數" value={combinedSummary?.claim.order_count ?? '-'}
                prefix={<CreditCardOutlined />} valueStyle={{ color: '#d46b08', fontSize: 22 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="請款應付合計" value={fmt(combinedSummary?.claim.total_payable)}
                prefix={<BankOutlined />} valueStyle={{ color: '#d46b08', fontSize: 18 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="合計筆數" value={combinedSummary?.combined.order_count ?? '-'}
                prefix={<ApartmentOutlined />} valueStyle={{ color: '#722ed1', fontSize: 22 }} />
            </Card></Col>
            <Col xs={12} sm={8} md={4}><Card size="small">
              <Statistic title="合計金額(含稅)" value={fmt(combinedSummary?.combined.total_amount)}
                valueStyle={{ color: '#1B3A5C', fontSize: 18 }} />
            </Card></Col>
          </Row>
        </Spin>
      )}

      {/* ── TABs ── */}
      <Card bodyStyle={{ padding: 0 }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          tabBarStyle={{ paddingLeft: 16, marginBottom: 0 }}
          items={[
            // ── TAB-1：請款單清單 ──────────────────────────────────────────────
            {
              key: 'claim-orders',
              label: `請款單清單（${claimSummary?.order_count ?? claimOrdersTotal} 張）`,
              children: (
                <div style={{ padding: '0 16px 16px' }}>
                  <Table<ClaimOrder>
                    dataSource={claimOrders} rowKey="id" columns={claimOrderColumns}
                    loading={claimOrdersLoading} size="small" scroll={{ x: 1050 }}
                    onRow={(r) => ({ onClick: () => openClaimDrawer(r.id), style: { cursor: 'pointer' } })}
                    pagination={{
                      total: claimOrdersTotal, current: claimOrdersPage, pageSize: 20,
                      showSizeChanger: false, showTotal: (t) => `共 ${t} 張請款單`,
                      onChange: (p) => loadClaimOrders(p),
                    }}
                    summary={(pageData) => {
                      const pagePayable = pageData.reduce((s, r) => s + (r.payable_amount ?? 0), 0)
                      const pageTax = pageData.reduce((s, r) => s + (r.tax ?? 0), 0)
                      return (
                        <Table.Summary fixed>
                          <Table.Summary.Row style={{ background: '#fff7e6', fontWeight: 600 }}>
                            <Table.Summary.Cell index={0} colSpan={6}>本頁小計（{pageData.length} 張）</Table.Summary.Cell>
                            <Table.Summary.Cell index={6} align="right">
                              <span style={{ color: '#d46b08', whiteSpace: 'nowrap' }}>{fmt(pagePayable)}</span>
                              {pageTax > 0 && <span style={{ color: '#888', fontSize: 11, marginLeft: 4 }}>（稅 {fmt(pageTax)}）</span>}
                            </Table.Summary.Cell>
                            <Table.Summary.Cell index={7} /><Table.Summary.Cell index={8} /><Table.Summary.Cell index={9} />
                          </Table.Summary.Row>
                        </Table.Summary>
                      )
                    }}
                  />
                </div>
              ),
            },

            // ── TAB-2：請款單月報明細 ──────────────────────────────────────────
            {
              key: 'claim-detail',
              label: `請款單月報明細（${claimSummary?.item_count ?? claimItemsTotal} 筆品項）`,
              children: (
                <div style={{ padding: '0 16px 16px' }}>
                  <Table<ClaimReportItem>
                    dataSource={claimItems} rowKey={(r, i) => `${r.claim_id}-${r.seq ?? i}`}
                    columns={claimDetailColumns} loading={claimItemsLoading} size="small" scroll={{ x: 1400 }}
                    onRow={(r) => ({ onClick: () => openClaimDrawer(r.claim_id), style: { cursor: 'pointer' } })}
                    pagination={{
                      total: claimItemsTotal, current: claimItemsPage, pageSize: PAGE_SIZE,
                      showSizeChanger: false, showTotal: (t) => `共 ${t} 筆品項`,
                      onChange: (p) => loadClaimItems(p),
                    }}
                    rowClassName={(r, i) => {
                      const prev = claimItems[i - 1]?.claim_id
                      return (i === 0 || prev !== r.claim_id) ? 'claim-row-first' : 'claim-row-cont'
                    }}
                    summary={(pageData) => {
                      const itemAmt = pageData.reduce((s, r) => s + (r.proposed_vendor_amount ?? 0), 0)
                      const seen = new Set<number>(); let payable = 0
                      for (const r of pageData) {
                        if (!seen.has(r.claim_id)) { seen.add(r.claim_id); payable += r.payable_amount ?? 0 }
                      }
                      return (
                        <Table.Summary fixed>
                          <Table.Summary.Row style={{ background: '#fff7e6', fontWeight: 600 }}>
                            <Table.Summary.Cell index={0} colSpan={8}>本頁小計（{pageData.length} 筆 / {seen.size} 張請款單）</Table.Summary.Cell>
                            <Table.Summary.Cell index={8} align="right"><span style={{ color: '#722ed1', whiteSpace: 'nowrap' }}>{fmt(itemAmt)}</span></Table.Summary.Cell>
                            <Table.Summary.Cell index={9} align="right"><span style={{ color: '#d46b08', whiteSpace: 'nowrap' }}>{fmt(payable)}</span></Table.Summary.Cell>
                            <Table.Summary.Cell index={10} />
                          </Table.Summary.Row>
                        </Table.Summary>
                      )
                    }}
                  />
                  <style>{`
                    .claim-row-first td { background: #fffbf0 !important; border-top: 1px solid #ffe7ba !important; }
                    .claim-row-cont  td { background: #ffffff !important; }
                    .claim-row-first:hover td, .claim-row-cont:hover td { background: #fff7e0 !important; }
                  `}</style>
                </div>
              ),
            },

            // ── TAB-3：部門統計 ────────────────────────────────────────────────
            {
              key: 'dept',
              label: '部門統計',
              children: (
                <div style={{ padding: '0 16px 16px' }}>
                  <Table<CombinedDeptStat>
                    dataSource={combinedDeptStats} rowKey="department_display"
                    columns={combinedDeptColumns} loading={combinedDeptLoading}
                    size="small" pagination={false}
                    summary={(rows) => {
                      const totalPC = rows.reduce((s, r) => s + r.purchase_count, 0)
                      const totalPA = rows.reduce((s, r) => s + (r.purchase_amount ?? 0), 0)
                      const totalPT = rows.reduce((s, r) => s + (r.purchase_tax ?? 0), 0)
                      const totalCC = rows.reduce((s, r) => s + r.claim_count, 0)
                      const totalCP = rows.reduce((s, r) => s + (r.claim_payable ?? 0), 0)
                      const totalCT = rows.reduce((s, r) => s + (r.claim_tax ?? 0), 0)
                      return (
                        <Table.Summary fixed>
                          <Table.Summary.Row style={{ background: '#f5f5f5', fontWeight: 600 }}>
                            <Table.Summary.Cell index={0}>合計（{rows.length} 部門）</Table.Summary.Cell>
                            <Table.Summary.Cell index={1} align="right"><strong style={{ color: '#1B3A5C' }}>{totalPC}</strong></Table.Summary.Cell>
                            <Table.Summary.Cell index={2} align="right"><strong style={{ color: '#1B3A5C' }}>{fmt(totalPA)}</strong></Table.Summary.Cell>
                            <Table.Summary.Cell index={3} align="right"><strong style={{ color: '#1B3A5C' }}>{fmt(totalPT)}</strong></Table.Summary.Cell>
                            <Table.Summary.Cell index={4} align="right"><strong style={{ color: '#d46b08' }}>{totalCC}</strong></Table.Summary.Cell>
                            <Table.Summary.Cell index={5} align="right"><strong style={{ color: '#d46b08' }}>{fmt(totalCP)}</strong></Table.Summary.Cell>
                            <Table.Summary.Cell index={6} align="right"><strong style={{ color: '#d46b08' }}>{fmt(totalCT)}</strong></Table.Summary.Cell>
                            <Table.Summary.Cell index={7} />
                          </Table.Summary.Row>
                        </Table.Summary>
                      )
                    }}
                  />

                  {/* ── 同步狀態（admin 折疊） ── */}
                  {isAdmin && (
                    <Collapse style={{ marginTop: 24 }}
                      items={[{
                        key: 'sync',
                        label: (
                          <Space>
                            <SyncOutlined />同步狀態管理
                            {(purchaseSyncStatus?.pending_detail_count ?? 0) + 0 > 0 && (
                              <Badge count={purchaseSyncStatus!.pending_detail_count} size="small" />
                            )}
                            {(claimSyncStatus?.pending_detail_count ?? 0) > 0 && (
                              <Badge count={claimSyncStatus!.pending_detail_count} size="small" style={{ backgroundColor: '#fa8c16' }} />
                            )}
                          </Space>
                        ),
                        children: (
                          <Row gutter={[16, 16]}>
                            {/* 請購同步 */}
                            <Col xs={24} md={12}>
                              <Card size="small" title={<span style={{ color: '#1B3A5C' }}>請購單同步</span>}>
                                <Space style={{ marginBottom: 12 }}>
                                  <Button type="primary" size="small" icon={<SyncOutlined spin={purchaseSyncing} />}
                                    loading={purchaseSyncing} onClick={() => handlePurchaseSync(false)}>增量同步</Button>
                                  <Button danger size="small" icon={<SyncOutlined />} loading={purchaseSyncing}
                                    onClick={() => Modal.confirm({
                                      title: '確認全量重新同步（請購）？',
                                      content: '將重設所有品項 detail_synced 旗標，重新抓取所有部門品項明細。',
                                      okText: '確認執行', cancelText: '取消',
                                      onOk: () => handlePurchaseSync(true),
                                    })}>全量同步</Button>
                                  <Button size="small" icon={<SyncOutlined />} onClick={loadPurchaseSyncStatus} loading={purchaseSyncLoading}>刷新</Button>
                                </Space>
                                {(purchaseSyncStatus?.pending_detail_count ?? 0) > 0 && (
                                  <Alert type="warning" showIcon style={{ marginBottom: 12 }}
                                    message={`尚有 ${purchaseSyncStatus!.pending_detail_count} 筆未完成品項同步`} />
                                )}
                                <Spin spinning={purchaseSyncLoading}>
                                  {(purchaseSyncStatus?.dept_stats?.length ?? 0) > 0 && (
                                    <Table dataSource={purchaseSyncStatus!.dept_stats} rowKey="department_display"
                                      size="small" pagination={false} style={{ marginBottom: 12 }}
                                      columns={[
                                        { title: '部門', dataIndex: 'department_display', width: 80, render: (v: string) => <Tag color="blue">{v}</Tag> },
                                        { title: '主單', dataIndex: 'total', align: 'right' as const, width: 60 },
                                        { title: '已同步', dataIndex: 'detail_synced', align: 'right' as const, width: 70, render: (v: number) => <span style={{ color: '#52c41a' }}>{v}</span> },
                                        { title: '待同步', dataIndex: 'pending', align: 'right' as const, width: 70, render: (v: number) => <span style={{ color: v > 0 ? '#fa8c16' : '#aaa' }}>{v}</span> },
                                        { title: '同步率', key: 'rate', width: 100,
                                          render: (_: unknown, r: { total: number; detail_synced: number }) => {
                                            const pct = r.total > 0 ? Math.round(r.detail_synced / r.total * 100) : 100
                                            return <Progress percent={pct} size="small" strokeColor={pct === 100 ? '#52c41a' : '#fa8c16'} />
                                          } },
                                      ]}
                                    />
                                  )}
                                  <Table dataSource={purchaseSyncStatus?.recent_logs ?? []} rowKey="id"
                                    size="small" pagination={false}
                                    columns={[
                                      { title: '時間', dataIndex: 'created_at', width: 140, render: (v: string) => v?.slice(0, 19).replace('T', ' ') },
                                      { title: '觸發', dataIndex: 'trigger', width: 70 },
                                      { title: '狀態', dataIndex: 'status', width: 70,
                                        render: (v: string) => <Tag color={v === 'success' ? 'green' : v === 'error' ? 'red' : 'processing'}>{v}</Tag> },
                                      { title: '訊息', dataIndex: 'message', ellipsis: true },
                                    ]}
                                  />
                                </Spin>
                              </Card>
                            </Col>

                            {/* 請款同步 */}
                            <Col xs={24} md={12}>
                              <Card size="small" title={<span style={{ color: '#d46b08' }}>請款單同步</span>}>
                                <Space style={{ marginBottom: 12 }}>
                                  <Button type="primary" size="small" icon={<SyncOutlined spin={claimSyncing} />}
                                    loading={claimSyncing} onClick={() => handleClaimSync(false)}
                                    style={{ background: '#fa8c16', borderColor: '#fa8c16' }}>增量同步</Button>
                                  <Button danger size="small" icon={<SyncOutlined />} loading={claimSyncing}
                                    onClick={() => Modal.confirm({
                                      title: '確認全量重新同步（請款）？',
                                      content: '將重設所有品項 detail_synced 旗標，重新抓取所有 9 個部門的請款品項。',
                                      okText: '確認執行', cancelText: '取消',
                                      onOk: () => handleClaimSync(true),
                                    })}>全量同步</Button>
                                  <Button size="small" icon={<SyncOutlined />} onClick={loadClaimSyncStatus} loading={claimSyncLoading}>刷新</Button>
                                </Space>
                                {(claimSyncStatus?.pending_detail_count ?? 0) > 0 && (
                                  <Alert type="warning" showIcon style={{ marginBottom: 12 }}
                                    message={`尚有 ${claimSyncStatus!.pending_detail_count} 筆未完成品項同步`} />
                                )}
                                <Spin spinning={claimSyncLoading}>
                                  {(claimSyncStatus?.dept_stats?.length ?? 0) > 0 && (
                                    <Table dataSource={claimSyncStatus!.dept_stats} rowKey="department_display"
                                      size="small" pagination={false} style={{ marginBottom: 12 }}
                                      columns={[
                                        { title: '部門', dataIndex: 'department_display', width: 80, render: (v: string) => <Tag color="orange">{v}</Tag> },
                                        { title: '主單', dataIndex: 'total', align: 'right' as const, width: 60 },
                                        { title: '已同步', dataIndex: 'detail_synced', align: 'right' as const, width: 70, render: (v: number) => <span style={{ color: '#52c41a' }}>{v}</span> },
                                        { title: '待同步', dataIndex: 'pending', align: 'right' as const, width: 70, render: (v: number) => <span style={{ color: v > 0 ? '#fa8c16' : '#aaa' }}>{v}</span> },
                                        { title: '同步率', key: 'rate', width: 100,
                                          render: (_: unknown, r: { total: number; detail_synced: number }) => {
                                            const pct = r.total > 0 ? Math.round(r.detail_synced / r.total * 100) : 100
                                            return <Progress percent={pct} size="small" strokeColor={pct === 100 ? '#52c41a' : '#fa8c16'} />
                                          } },
                                      ]}
                                    />
                                  )}
                                  <Table dataSource={claimSyncStatus?.recent_logs ?? []} rowKey="id"
                                    size="small" pagination={false}
                                    columns={[
                                      { title: '時間', dataIndex: 'created_at', width: 140, render: (v: string) => v?.slice(0, 19).replace('T', ' ') },
                                      { title: '觸發', dataIndex: 'trigger', width: 70 },
                                      { title: '狀態', dataIndex: 'status', width: 70,
                                        render: (v: string) => <Tag color={v === 'success' ? 'green' : v === 'error' ? 'red' : 'processing'}>{v}</Tag> },
                                      { title: '訊息', dataIndex: 'message', ellipsis: true },
                                    ]}
                                  />
                                </Spin>
                              </Card>
                            </Col>
                          </Row>
                        ),
                      }]}
                    />
                  )}
                </div>
              ),
            },
            // ── TAB-5：資料異常 ────────────────────────────────────────────────
            {
              key: 'audit',
              label: (() => {
                const total = (auditSummaryP?.total_anomalies ?? 0) + (auditSummaryC?.total_anomalies ?? 0)
                return (
                  <Space size={4}>
                    <WarningOutlined style={{ color: total > 0 ? '#ff4d4f' : undefined }} />
                    資料異常
                    {total > 0 && <Badge count={total} size="small" style={{ backgroundColor: '#ff4d4f' }} />}
                  </Space>
                )
              })(),
              children: (
                <div style={{ padding: '0 16px 16px' }}>
                  {/* KPI 卡：各規則計數 */}
                  <Spin spinning={auditSummaryLoading}>
                    <Row gutter={[12, 12]} style={{ marginBottom: 16, marginTop: 12 }}>
                      {(() => {
                        // 合併 purchase + claim 的 by_rule 計數
                        const merged: Record<string, { name: string; sev: string; count: number }> = {}
                        const add = (rules: AuditSummary['by_rule'] | undefined) =>
                          rules?.forEach(r => {
                            if (!merged[r.rule_code]) merged[r.rule_code] = { name: r.rule_name, sev: r.severity, count: 0 }
                            merged[r.rule_code].count += r.count
                          })
                        add(auditSummaryP?.by_rule)
                        add(auditSummaryC?.by_rule)
                        const sevColor = (s: string) => s === 'high' ? '#ff4d4f' : s === 'medium' ? '#fa8c16' : '#faad14'
                        return Object.entries(merged).map(([code, info]) => (
                          <Col xs={12} sm={8} md={6} lg={3} key={code}>
                            <Card
                              size="small"
                              style={{
                                cursor: 'pointer',
                                borderColor: auditRuleFilter === code ? sevColor(info.sev) : undefined,
                                background: auditRuleFilter === code ? `${sevColor(info.sev)}10` : undefined,
                              }}
                              bodyStyle={{ padding: '8px 12px' }}
                              onClick={() => {
                                setAuditRuleFilter(auditRuleFilter === code ? undefined : code)
                              }}
                            >
                              <div style={{ fontSize: 11, color: '#888', marginBottom: 2 }}>
                                <Tag color={sevColor(info.sev)} style={{ fontSize: 10, padding: '0 4px', marginRight: 4 }}>{code}</Tag>
                                {info.name}
                              </div>
                              <div style={{ fontSize: 22, fontWeight: 700, color: info.count > 0 ? sevColor(info.sev) : '#aaa' }}>
                                {info.count}
                              </div>
                            </Card>
                          </Col>
                        ))
                      })()}
                      {/* 總計卡 */}
                      <Col xs={12} sm={8} md={6} lg={3}>
                        <Card size="small" bodyStyle={{ padding: '8px 12px' }}
                          style={{ background: '#fafafa', cursor: 'pointer' }}
                          onClick={() => setAuditRuleFilter(undefined)}>
                          <div style={{ fontSize: 11, color: '#888', marginBottom: 2 }}>
                            <ExceptionOutlined style={{ marginRight: 4 }} />全部異常
                          </div>
                          <div style={{ fontSize: 22, fontWeight: 700, color: auditTotal > 0 ? '#ff4d4f' : '#aaa' }}>
                            {(auditSummaryP?.total_anomalies ?? 0) + (auditSummaryC?.total_anomalies ?? 0)}
                          </div>
                        </Card>
                      </Col>
                    </Row>
                  </Spin>

                  {/* 篩選列 */}
                  <Space style={{ marginBottom: 12 }} wrap>
                    <Segmented
                      value={auditSourceFilter}
                      onChange={(v) => setAuditSourceFilter(v as 'all' | 'purchase' | 'claim')}
                      options={[
                        { label: '全部', value: 'all' },
                        { label: '請購', value: 'purchase' },
                        { label: '請款', value: 'claim' },
                      ]}
                      size="small"
                    />
                    {auditRuleFilter && (
                      <Tag closable color="red" onClose={() => setAuditRuleFilter(undefined)}>
                        規則：{auditRuleFilter}
                      </Tag>
                    )}
                    <Button size="small" icon={<SyncOutlined />} onClick={loadAuditAnomalies} loading={auditLoading}>
                      重新稽核
                    </Button>
                  </Space>

                  {/* 異常列表 Table */}
                  <Table<AuditAnomaly>
                    dataSource={auditAnomalies}
                    rowKey={(r) => `${r.source}-${r.order_id}-${r.rule_code}`}
                    loading={auditLoading}
                    size="small"
                    scroll={{ x: 900 }}
                    pagination={{
                      pageSize: 20,
                      showTotal: (t) => `共 ${t} 筆異常`,
                      showSizeChanger: false,
                    }}
                    columns={[
                      {
                        title: '嚴重程度', dataIndex: 'severity', key: 'severity', width: 90, fixed: 'left' as const,
                        render: (v: string) => {
                          const cfg = v === 'high'
                            ? { color: '#ff4d4f', text: '🔴 高' }
                            : v === 'medium'
                            ? { color: '#fa8c16', text: '🟠 中' }
                            : { color: '#faad14', text: '🟡 低' }
                          return <span style={{ color: cfg.color, fontWeight: 600, fontSize: 12 }}>{cfg.text}</span>
                        },
                      },
                      {
                        title: '規則', dataIndex: 'rule_code', key: 'rule', width: 130,
                        render: (code: string, r: AuditAnomaly) => (
                          <Space size={4}>
                            <Tag style={{ fontSize: 11 }}>{code}</Tag>
                            <span style={{ fontSize: 12 }}>{r.rule_name}</span>
                          </Space>
                        ),
                      },
                      {
                        title: '來源', dataIndex: 'source', key: 'source', width: 68,
                        render: (v: string) => v === 'purchase'
                          ? <Tag color="blue">請購</Tag>
                          : <Tag color="orange">請款</Tag>,
                      },
                      {
                        title: '單號', dataIndex: 'doc_no', key: 'doc_no', width: 180, ellipsis: true,
                        render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v || '-'}</span>,
                      },
                      {
                        title: '部門', dataIndex: 'department', key: 'dept', width: 80,
                        render: (v: string, r: AuditAnomaly) => (
                          <Tag color={r.source === 'purchase' ? 'blue' : 'orange'}>{v || '-'}</Tag>
                        ),
                      },
                      {
                        title: '說明', dataIndex: 'detail', key: 'detail', ellipsis: true,
                        render: (v: string) => <span style={{ fontSize: 12, color: '#555' }}>{v}</span>,
                      },
                      {
                        title: '核准日期', dataIndex: 'approved_date', key: 'approved_date', width: 100,
                        render: (v: string | null) => v ?? '-',
                      },
                      {
                        title: '', key: 'link', width: 48, fixed: 'right' as const,
                        render: (_: unknown, r: AuditAnomaly) => r.ragic_url ? (
                          <Tooltip title="在 Ragic 中開啟">
                            <Button type="link" size="small" icon={<LinkOutlined />}
                              href={r.ragic_url} target="_blank" rel="noopener noreferrer"
                              style={{ padding: 0 }} />
                          </Tooltip>
                        ) : null,
                      },
                    ]}
                  />
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* ── 請購 Detail Drawer ── */}
      <Drawer
        title={selectedOrder
          ? `${selectedOrder.order.purchase_no || '請購單'} — ${selectedOrder.order.department_display}`
          : '請購單明細'}
        width={680} open={drawerOpen} onClose={() => setDrawerOpen(false)}
        bodyStyle={{ padding: 16 }}
      >
        <Spin spinning={drawerLoading}>
          {selectedOrder && (
            <>
              <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
                <Descriptions.Item label="編號" span={2}>
                  <span style={{ fontFamily: 'monospace' }}>{selectedOrder.order.purchase_no || '-'}</span>
                </Descriptions.Item>
                <Descriptions.Item label="申請日期">{selectedOrder.order.request_date || '-'}</Descriptions.Item>
                <Descriptions.Item label="核准日期">{selectedOrder.order.approved_date || '-'}</Descriptions.Item>
                <Descriptions.Item label="部門"><Tag color="blue">{selectedOrder.order.department_display}</Tag></Descriptions.Item>
                <Descriptions.Item label="申請人">{selectedOrder.order.applicant || '-'}</Descriptions.Item>
                <Descriptions.Item label="會科" span={2}>{selectedOrder.order.account_category || '-'}</Descriptions.Item>
                <Descriptions.Item label="說明" span={2}>
                  {selectedOrder.order.description || <span style={{ color: '#aaa' }}>（無說明）</span>}
                </Descriptions.Item>
                <Descriptions.Item label="廠商(一)">{selectedOrder.order.vendor1 || '-'}</Descriptions.Item>
                <Descriptions.Item label="廠商(二)">{selectedOrder.order.vendor2 || '-'}</Descriptions.Item>
                {selectedOrder.order.vendor3 && (
                  <Descriptions.Item label="廠商(三)" span={2}>{selectedOrder.order.vendor3}</Descriptions.Item>
                )}
                {!selectedOrder.order.detail_synced && (
                  <Descriptions.Item label="廠商資訊" span={2}>
                    <Text type="secondary">尚未同步（執行增量同步後可取得）</Text>
                  </Descriptions.Item>
                )}
                <Descriptions.Item label="全案小計(未稅)">
                  <span style={{ fontWeight: 700, color: '#1B3A5C' }}>{fmt(selectedOrder.order.amount)}</span>
                </Descriptions.Item>
                <Descriptions.Item label="營業稅">{fmt(selectedOrder.order.amount_tax)}</Descriptions.Item>
                <Descriptions.Item label="簽核狀態">{statusTag(selectedOrder.order.status)}</Descriptions.Item>
                <Descriptions.Item label="最後更新">{selectedOrder.order.last_updated_at || '-'}</Descriptions.Item>
                {selectedOrder.order.remark && (
                  <Descriptions.Item label="備註" span={2}>
                    <div
                      dangerouslySetInnerHTML={{ __html: selectedOrder.order.remark }}
                      style={{ lineHeight: 1.6 }}
                    />
                  </Descriptions.Item>
                )}
              </Descriptions>

              {selectedOrder.items.length > 0 ? (
                <>
                  <Typography.Title level={5} style={{ marginBottom: 8 }}>
                    品項明細（{selectedOrder.items.length} 項）
                  </Typography.Title>
                  <Table
                    dataSource={selectedOrder.items} rowKey={(r, i) => `${r.id ?? i}`}
                    size="small" pagination={false} scroll={{ x: 600 }}
                    columns={[
                      { title: '#', dataIndex: 'seq', width: 36, align: 'center' as const },
                      { title: '品名', dataIndex: 'product_name', ellipsis: true },
                      { title: '數量', dataIndex: 'qty', width: 55, align: 'right' as const },
                      { title: '單位', dataIndex: 'unit', width: 50 },
                      { title: '選定廠商', dataIndex: 'selected_vendor', width: 95, ellipsis: true },
                      { title: '單價', dataIndex: 'selected_unit_price', width: 80, align: 'right' as const, render: fmt },
                      { title: '金額', dataIndex: 'selected_amount', width: 90, align: 'right' as const,
                        render: (v: number | null) => <span style={{ fontWeight: 600 }}>{fmt(v)}</span> },
                    ]}
                  />
                </>
              ) : (
                <Alert type={selectedOrder.order.detail_synced ? 'info' : 'warning'} showIcon
                  message={selectedOrder.order.detail_synced
                    ? '此請購單無品項記錄'
                    : '品項尚未同步，請執行「增量同步」以載入品項明細'}
                />
              )}

              {selectedOrder.order.ragic_url && (
                <div style={{ marginTop: 16, textAlign: 'right' }}>
                  <Button
                    type="link" size="small"
                    href={selectedOrder.order.ragic_url} target="_blank" rel="noopener noreferrer"
                  >
                    在 Ragic 中開啟 ↗
                  </Button>
                </div>
              )}
            </>
          )}
        </Spin>
      </Drawer>

      {/* ── 請款 Detail Drawer ── */}
      <Drawer
        title={selectedClaimOrder
          ? `${selectedClaimOrder.order.request_no || '請款單'} — ${selectedClaimOrder.order.department_display}`
          : '請款單明細'}
        width={700} open={claimDrawerOpen} onClose={() => setClaimDrawerOpen(false)}
        bodyStyle={{ padding: 16 }}
      >
        <Spin spinning={claimDrawerLoading}>
          {selectedClaimOrder && (
            <>
              <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
                <Descriptions.Item label="請款單號" span={2}>
                  <span style={{ fontFamily: 'monospace' }}>{selectedClaimOrder.order.request_no || '-'}</span>
                </Descriptions.Item>
                <Descriptions.Item label={selectedClaimOrder.order.dept_request_no_label || '部門單號'} span={2}>
                  {selectedClaimOrder.order.department_request_no || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="申請日期">{selectedClaimOrder.order.apply_date || '-'}</Descriptions.Item>
                <Descriptions.Item label="核准日期">{selectedClaimOrder.order.approved_date || '-'}</Descriptions.Item>
                <Descriptions.Item label="部門"><Tag color="orange">{selectedClaimOrder.order.department_display}</Tag></Descriptions.Item>
                <Descriptions.Item label="申請人">{selectedClaimOrder.order.applicant || '-'}</Descriptions.Item>
                <Descriptions.Item label="會科" span={2}>{selectedClaimOrder.order.account_subject || '-'}</Descriptions.Item>
                <Descriptions.Item label="事由" span={2}>
                  {selectedClaimOrder.order.purpose_description || <span style={{ color: '#aaa' }}>（無說明）</span>}
                </Descriptions.Item>
                <Descriptions.Item label="付款種類">{paymentTag(selectedClaimOrder.order.payment_type)}</Descriptions.Item>
                <Descriptions.Item label="付款日期">{selectedClaimOrder.order.payment_date || '-'}</Descriptions.Item>
                <Descriptions.Item label="受款人" span={2}>{selectedClaimOrder.order.payee || '-'}</Descriptions.Item>
                {selectedClaimOrder.order.bank_name && (
                  <>
                    <Descriptions.Item label="銀行">{selectedClaimOrder.order.bank_name} {selectedClaimOrder.order.bank_branch || ''}</Descriptions.Item>
                    <Descriptions.Item label="帳號">{selectedClaimOrder.order.bank_account || '-'}</Descriptions.Item>
                  </>
                )}
                <Descriptions.Item label="小計(未稅)">
                  <span style={{ fontWeight: 700 }}>{fmt(selectedClaimOrder.order.subtotal)}</span>
                </Descriptions.Item>
                <Descriptions.Item label="營業稅">{fmt(selectedClaimOrder.order.tax)}</Descriptions.Item>
                <Descriptions.Item label="合計">{fmt(selectedClaimOrder.order.total)}</Descriptions.Item>
                <Descriptions.Item label="應付金額">
                  <span style={{ fontWeight: 700, color: '#d46b08' }}>{fmt(selectedClaimOrder.order.payable_amount)}</span>
                </Descriptions.Item>
                <Descriptions.Item label="簽核狀態">{statusTag(selectedClaimOrder.order.status)}</Descriptions.Item>
                <Descriptions.Item label="最後更新">{selectedClaimOrder.order.last_updated_at || '-'}</Descriptions.Item>
              </Descriptions>

              {selectedClaimOrder.items.length > 0 ? (
                <>
                  <Typography.Title level={5} style={{ marginBottom: 8 }}>
                    品項明細（{selectedClaimOrder.items.length} 項）
                  </Typography.Title>
                  <Table
                    dataSource={selectedClaimOrder.items} rowKey={(r, i) => `${r.id ?? i}`}
                    size="small" pagination={false} scroll={{ x: 580 }}
                    columns={[
                      { title: '#', dataIndex: 'seq', width: 36, align: 'center' as const },
                      { title: '品名', dataIndex: 'item_name', ellipsis: true },
                      { title: '數量', dataIndex: 'quantity', width: 60, align: 'right' as const },
                      { title: '單位', dataIndex: 'unit', width: 50 },
                      { title: '金額', dataIndex: 'proposed_vendor_amount', width: 90, align: 'right' as const,
                        render: (v: number | null) => <span style={{ fontWeight: 600 }}>{fmt(v)}</span> },
                      { title: '發票號碼', dataIndex: 'invoice_no', width: 110, ellipsis: true,
                        render: (v: string | null) => v || '-' },
                      { title: '收據號碼', dataIndex: 'receipt_no', width: 110, ellipsis: true,
                        render: (v: string | null) => v || '-' },
                      { title: '備註', dataIndex: 'item_note', ellipsis: true,
                        render: (v: string | null) => v || '-' },
                    ]}
                  />
                </>
              ) : (
                <Alert type={selectedClaimOrder.order.detail_synced ? 'info' : 'warning'} showIcon
                  message={selectedClaimOrder.order.detail_synced
                    ? '此請款單無品項記錄'
                    : '品項尚未同步，請執行「增量同步」以載入品項明細'}
                />
              )}

              {selectedClaimOrder.order.ragic_url && (
                <div style={{ marginTop: 16, textAlign: 'right' }}>
                  <Button
                    type="link" size="small"
                    href={selectedClaimOrder.order.ragic_url} target="_blank" rel="noopener noreferrer"
                  >
                    在 Ragic 中開啟 ↗
                  </Button>
                </div>
              )}
            </>
          )}
        </Spin>
      </Drawer>
    </div>
  )
}
