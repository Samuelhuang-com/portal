/**
 * 日曜核准請款單月報表
 *
 * TAB 順序：
 *   TAB-1  請款單清單（訂單級 + Drawer 明細）
 *   TAB-2  月報明細（品項級）
 *   TAB-3  部門統計（型態A：單業務 blue Tag，請款前綴欄位）
 *   TAB-4  資料異常稽核
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
  AccountBookOutlined,
  TeamOutlined,
  BarChartOutlined,
  WarningOutlined,
  LinkOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import {
  getNichiyoClaimOrders,
  getNichiyoClaimOrderDetail,
  getNichiyoClaimMonthlyItems,
  getNichiyoClaimSummary,
  getNichiyoClaimCombinedDepartments,
  getNichiyoClaimDeptList,
  getNichiyoClaimAccountCategories,
  getNichiyoClaimAvailableMonths,
  exportNichiyoClaimReport,
  triggerNichiyoClaimSync,
  getNichiyoClaimSyncStatus,
  getNichiyoClaimAuditAnomalies,
  getNichiyoClaimAuditSummary,
  type NichiyoClaimReportItem,
  type NichiyoClaimReportSummary,
  type NichiyoClaimSyncStatus,
  type NichiyoClaimOrder,
  type NichiyoClaimOrderDetail,
  type NichiyoClaimAuditAnomaly,
  type NichiyoClaimAuditSummary,
  type NichiyoCombinedDeptStat,
} from '@/api/nichiyoClaimReport'
import { useAuthStore } from '@/stores/authStore'

const { Title, Text } = Typography

// ── 數字格式化 ──────────────────────────────────────────────────────────────────
const fmt = (n: number | null | undefined) =>
  n == null ? '-' : new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 0 }).format(n)

// ── 預設年月（上個月） ──────────────────────────────────────────────────────────
const defaultYearMonth = () => dayjs().subtract(1, 'month').format('YYYY-MM')

const PAGE_SIZE = 50
const STORAGE_KEY = 'nichiyo_claim_report_year_month'

// ── 簽核狀態 Tag ────────────────────────────────────────────────────────────────
const statusTag = (v: string) => {
  if (v === 'F')   return <Tag color="green">已核准</Tag>
  if (v === 'REJ') return <Tag color="red">退回</Tag>
  return <Tag color="orange">待審</Tag>
}

export default function NichiyoClaimReportPage() {
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const isAdmin = hasPermission('system_admin_only') || hasPermission('nichiyo_claim.admin')

  // ── 共用篩選 ──────────────────────────────────────────────────────────────────
  const savedYm = localStorage.getItem(STORAGE_KEY) || defaultYearMonth()
  const [yearMonth, setYearMonth]       = useState<string>(savedYm)
  const [pickerValue, setPickerValue]   = useState<Dayjs | null>(dayjs(savedYm, 'YYYY-MM'))
  const [dateMode, setDateMode]         = useState<'month' | 'year' | 'range'>('month')
  const [yearPickerValue, setYearPickerValue] = useState<Dayjs | null>(null)
  const [rangeValues, setRangeValues]   = useState<[Dayjs | null, Dayjs | null]>([null, null])
  const [yearMonthFrom, setYearMonthFrom] = useState<string | undefined>(undefined)
  const [yearMonthTo, setYearMonthTo]   = useState<string | undefined>(undefined)
  const [deptFilter, setDeptFilter]     = useState<string | undefined>(undefined)
  const [accountFilter, setAccountFilter] = useState<string | undefined>(undefined)
  const [searchInput, setSearchInput]   = useState<string>('')
  const [searchKeyword, setSearchKeyword] = useState<string>('')
  const [availableMonths, setAvailableMonths] = useState<string[]>([])
  const [deptOptions, setDeptOptions]   = useState<string[]>([])
  const [accountOptions, setAccountOptions] = useState<string[]>([])
  const initialMonthLoaded              = useRef(false)

  // ── Tab ───────────────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<string>('orders')

  // ── 請款資料 ──────────────────────────────────────────────────────────────────
  const [summary, setSummary]           = useState<NichiyoClaimReportSummary | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [orders, setOrders]             = useState<NichiyoClaimOrder[]>([])
  const [ordersTotal, setOrdersTotal]   = useState(0)
  const [ordersPage, setOrdersPage]     = useState(1)
  const [ordersLoading, setOrdersLoading] = useState(false)
  const [items, setItems]               = useState<NichiyoClaimReportItem[]>([])
  const [itemsTotal, setItemsTotal]     = useState(0)
  const [itemsPage, setItemsPage]       = useState(1)
  const [itemsLoading, setItemsLoading] = useState(false)
  const [deptStats, setDeptStats]       = useState<NichiyoCombinedDeptStat[]>([])
  const [deptStatsLoading, setDeptStatsLoading] = useState(false)
  const [syncStatus, setSyncStatus]     = useState<NichiyoClaimSyncStatus | null>(null)
  const [syncLoading, setSyncLoading]   = useState(false)
  const [syncing, setSyncing]           = useState(false)
  const [exportLoading, setExportLoading] = useState(false)

  // ── Detail Drawer ─────────────────────────────────────────────────────────────
  const [selectedOrder, setSelectedOrder]   = useState<NichiyoClaimOrderDetail | null>(null)
  const [drawerOpen, setDrawerOpen]         = useState(false)
  const [drawerLoading, setDrawerLoading]   = useState(false)

  // ── 稽核 ──────────────────────────────────────────────────────────────────────
  const [auditSummary, setAuditSummary]       = useState<NichiyoClaimAuditSummary | null>(null)
  const [auditSummaryLoading, setAuditSummaryLoading] = useState(false)
  const [auditAnomalies, setAuditAnomalies]   = useState<NichiyoClaimAuditAnomaly[]>([])
  const [auditTotal, setAuditTotal]           = useState(0)
  const [auditLoading, setAuditLoading]       = useState(false)
  const [auditRuleFilter, setAuditRuleFilter] = useState<string | undefined>(undefined)

  // ── 初始化：載入下拉選項 + 可用月份 ──────────────────────────────────────────
  useEffect(() => {
    getNichiyoClaimDeptList().then((r) => setDeptOptions(r.data ?? []))
    getNichiyoClaimAccountCategories().then((r) => setAccountOptions(r.data ?? []))
    getNichiyoClaimAvailableMonths().then((r) => {
      const months = r.data ?? []
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

  // ── 日期參數計算 ─────────────────────────────────────────────────────────────
  const dateParams = useCallback(() => {
    if (yearMonthFrom) return { year_month_from: yearMonthFrom, year_month_to: yearMonthTo }
    return { year_month: yearMonth }
  }, [yearMonth, yearMonthFrom, yearMonthTo])

  // ── Load 函數 ─────────────────────────────────────────────────────────────────
  const loadSummary = useCallback(() => {
    setSummaryLoading(true)
    getNichiyoClaimSummary({ ...dateParams(), department: deptFilter, account_category: accountFilter })
      .then((r) => setSummary(r.data))
      .finally(() => setSummaryLoading(false))
  }, [dateParams, deptFilter, accountFilter])

  const loadOrders = useCallback((page = 1) => {
    setOrdersLoading(true)
    setOrdersPage(page)
    getNichiyoClaimOrders({
      ...dateParams(), department: deptFilter, account_category: accountFilter,
      keyword: searchKeyword || undefined, page, per_page: 20,
    })
      .then((r) => { setOrders(r.data.items ?? []); setOrdersTotal(r.data.total ?? 0) })
      .finally(() => setOrdersLoading(false))
  }, [dateParams, deptFilter, accountFilter, searchKeyword])

  const loadItems = useCallback((page = 1) => {
    setItemsLoading(true)
    setItemsPage(page)
    getNichiyoClaimMonthlyItems({
      ...dateParams(), department: deptFilter, account_category: accountFilter,
      q: searchKeyword || undefined, page, per_page: PAGE_SIZE,
    })
      .then((r) => { setItems(r.data.items ?? []); setItemsTotal(r.data.total ?? 0) })
      .finally(() => setItemsLoading(false))
  }, [dateParams, deptFilter, accountFilter, searchKeyword])

  const loadDeptStats = useCallback(() => {
    setDeptStatsLoading(true)
    getNichiyoClaimCombinedDepartments({ ...dateParams() })
      .then((r) => setDeptStats(r.data ?? []))
      .finally(() => setDeptStatsLoading(false))
  }, [dateParams, accountFilter])

  const loadSyncStatus = useCallback(() => {
    if (!isAdmin) return
    setSyncLoading(true)
    getNichiyoClaimSyncStatus()
      .then((r) => setSyncStatus(r.data))
      .finally(() => setSyncLoading(false))
  }, [isAdmin])

  const loadAuditSummary = useCallback(() => {
    setAuditSummaryLoading(true)
    getNichiyoClaimAuditSummary({ ...dateParams(), department: deptFilter })
      .then((r) => setAuditSummary(r.data))
      .finally(() => setAuditSummaryLoading(false))
  }, [dateParams, deptFilter])

  const loadAuditAnomalies = useCallback((page = 1) => {
    setAuditLoading(true)
    getNichiyoClaimAuditAnomalies({
      ...dateParams(), department: deptFilter,
      rule_code: auditRuleFilter, page, per_page: 20,
    })
      .then((r) => { setAuditAnomalies(r.data.items ?? []); setAuditTotal(r.data.total ?? 0) })
      .finally(() => setAuditLoading(false))
  }, [dateParams, deptFilter, auditRuleFilter])

  // ── Tab 切換觸發對應 Load ─────────────────────────────────────────────────────
  useEffect(() => {
    if (activeTab === 'orders') { loadSummary(); loadOrders(1) }
    if (activeTab === 'monthly') { loadSummary(); loadItems(1) }
    if (activeTab === 'dept') { loadSummary(); loadDeptStats(); if (isAdmin) loadSyncStatus() }
    if (activeTab === 'audit') { loadAuditSummary(); loadAuditAnomalies(1) }
  }, [activeTab]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── 篩選條件變更時重新載入 ─────────────────────────────────────────────────────
  useEffect(() => {
    if (activeTab === 'orders')  { loadSummary(); loadOrders(1) }
    if (activeTab === 'monthly') { loadSummary(); loadItems(1) }
    if (activeTab === 'dept')    { loadSummary(); loadDeptStats() }
    if (activeTab === 'audit')   { loadAuditSummary(); loadAuditAnomalies(1) }
  }, [yearMonth, yearMonthFrom, yearMonthTo, deptFilter, accountFilter, searchKeyword]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── 日期模式切換 ───────────────────────────────────────────────────────────────
  const handleDateModeChange = (mode: string | number) => {
    const m = mode as 'month' | 'year' | 'range'
    setDateMode(m)
    setRangeValues([null, null])
    if (m === 'month') {
      const ym = availableMonths[0] || defaultYearMonth()
      setYearMonth(ym)
      setPickerValue(dayjs(ym, 'YYYY-MM'))
      setYearMonthFrom(undefined)
      setYearMonthTo(undefined)
      setYearPickerValue(null)
    } else if (m === 'year') {
      const thisYear = dayjs()
      setYearPickerValue(thisYear)
      setYearMonthFrom(thisYear.startOf('year').format('YYYY-MM'))
      setYearMonthTo(thisYear.endOf('year').format('YYYY-MM'))
    } else {
      setYearMonthFrom(undefined)
      setYearMonthTo(undefined)
      setYearPickerValue(null)
    }
  }

  // ── Excel 匯出 ─────────────────────────────────────────────────────────────────
  const handleExport = async () => {
    setExportLoading(true)
    try {
      const r = await exportNichiyoClaimReport({ ...dateParams(), department: deptFilter, account_category: accountFilter })
      const blob = new Blob([r.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const label = yearMonthFrom ? `${yearMonthFrom}_${yearMonthTo}` : yearMonth
      a.download = `日曜請款月報_${label}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      message.error('匯出失敗')
    } finally {
      setExportLoading(false)
    }
  }

  // ── 同步 ──────────────────────────────────────────────────────────────────────
  const handleSync = async (fullResync = false) => {
    setSyncing(true)
    try {
      const r = await triggerNichiyoClaimSync(fullResync)
      message.success(r.data.message || '同步已啟動')
      setTimeout(() => { loadOrders(ordersPage); loadSyncStatus() }, 2000)
    } catch {
      message.error('同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  // ── Drawer：開啟單筆詳情（接受 orderId，TAB-1 和 TAB-2 共用） ───────────────
  const handleOpenDrawer = async (orderId: number) => {
    setDrawerOpen(true)
    setDrawerLoading(true)
    setSelectedOrder(null)
    try {
      const r = await getNichiyoClaimOrderDetail(orderId)
      setSelectedOrder(r.data)
    } catch {
      message.error('載入明細失敗')
    } finally {
      setDrawerLoading(false)
    }
  }

  // ── 欄位定義：請款單清單 ───────────────────────────────────────────────────────
  const orderColumns = [
    { title: '單號', dataIndex: 'claim_no', key: 'claim_no', width: 190, ellipsis: true, fixed: 'left' as const,
      render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v || '-'}</span>,
      sorter: (a: NichiyoClaimOrder, b: NichiyoClaimOrder) => (a.claim_no ?? '').localeCompare(b.claim_no ?? '') },
    { title: '部門', dataIndex: 'department_display', key: 'dept', width: 80,
      render: (v: string) => <Tag color="blue">{v}</Tag>,
      sorter: (a: NichiyoClaimOrder, b: NichiyoClaimOrder) => a.department_display.localeCompare(b.department_display) },
    { title: '會科', dataIndex: 'account_category', key: 'account_category', width: 110, ellipsis: true,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span>,
      sorter: (a: NichiyoClaimOrder, b: NichiyoClaimOrder) => (a.account_category ?? '').localeCompare(b.account_category ?? '') },
    { title: '申請人', dataIndex: 'applicant', key: 'applicant', width: 80,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span>,
      sorter: (a: NichiyoClaimOrder, b: NichiyoClaimOrder) => (a.applicant ?? '').localeCompare(b.applicant ?? '') },
    { title: '事由', dataIndex: 'purpose_description', key: 'purpose_description', ellipsis: true,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span> },
    { title: '受款者', dataIndex: 'payee', key: 'payee', width: 120, ellipsis: true,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span>,
      sorter: (a: NichiyoClaimOrder, b: NichiyoClaimOrder) => (a.payee ?? '').localeCompare(b.payee ?? '') },
    { title: '付款種類', dataIndex: 'payment_type', key: 'payment_type', width: 90,
      render: (v: string | null) => v
        ? <Tag color={v === '匯款' ? 'blue' : 'default'}>{v}</Tag>
        : <span style={{ color: '#aaa' }}>—</span> },
    { title: '應付款', dataIndex: 'payable_amount', key: 'payable_amount', width: 110, align: 'right' as const,
      render: (v: number | null) => <span style={{ fontWeight: 600, color: '#1B3A5C' }}>{fmt(v)}</span>,
      sorter: (a: NichiyoClaimOrder, b: NichiyoClaimOrder) => (a.payable_amount ?? 0) - (b.payable_amount ?? 0) },
    { title: '狀態', dataIndex: 'status', key: 'status', width: 80, render: statusTag,
      sorter: (a: NichiyoClaimOrder, b: NichiyoClaimOrder) => a.status.localeCompare(b.status) },
    { title: '核准日期', dataIndex: 'approved_date', key: 'approved_date', width: 100,
      render: (v: string | null) => <span style={{ fontSize: 12, color: '#666' }}>{v || '-'}</span>,
      sorter: (a: NichiyoClaimOrder, b: NichiyoClaimOrder) => (a.approved_date ?? '').localeCompare(b.approved_date ?? '') },
    { title: '', key: 'action', width: 48, fixed: 'right' as const,
      render: (_: unknown, r: NichiyoClaimOrder) => (
        <Button type="link" size="small" icon={<EyeOutlined />}
          onClick={(e) => { e.stopPropagation(); handleOpenDrawer(r.id) }} style={{ padding: 0 }} />
      ) },
  ]

  // ── 欄位定義：月報明細（品項級） ─────────────────────────────────────────────
  const itemColumns = [
    { title: '部門', dataIndex: 'department_display', key: 'dept', width: 90,
      render: (v: string) => <Tag color="blue">{v}</Tag>,
      sorter: (a: NichiyoClaimReportItem, b: NichiyoClaimReportItem) => a.department_display.localeCompare(b.department_display) },
    { title: '請款單號', dataIndex: 'claim_no', key: 'claim_no', width: 180, ellipsis: true,
      render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v || '-'}</span>,
      sorter: (a: NichiyoClaimReportItem, b: NichiyoClaimReportItem) => a.claim_no.localeCompare(b.claim_no) },
    { title: '會科', dataIndex: 'account_category', key: 'account_category', width: 120, ellipsis: true,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span> },
    { title: '事由', dataIndex: 'purpose_description', key: 'purpose_description', ellipsis: true,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span> },
    { title: '品名', dataIndex: 'product_name', key: 'product_name', minWidth: 120, ellipsis: true,
      render: (v: string | null) => v || <Text type="secondary">—</Text> },
    { title: '受款者', dataIndex: 'payee', key: 'payee', width: 120, ellipsis: true,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span> },
    { title: '數量', dataIndex: 'qty', key: 'qty', width: 70, align: 'right' as const,
      render: (v: string | null) => v ?? '-' },
    { title: '單位', dataIndex: 'unit', key: 'unit', width: 55 },
    { title: '品項金額', dataIndex: 'amount', key: 'item_amount', width: 110, align: 'right' as const,
      render: (v: number | null) => <span style={{ whiteSpace: 'nowrap' }}>{fmt(v)}</span>,
      sorter: (a: NichiyoClaimReportItem, b: NichiyoClaimReportItem) => (a.amount ?? 0) - (b.amount ?? 0) },
    { title: '應付款', dataIndex: 'payable_amount', key: 'payable_amount', width: 110, align: 'right' as const,
      render: (v: number | null, r: NichiyoClaimReportItem, idx: number) => {
        const prev = items[idx - 1]?.order_id
        if (idx === 0 || prev !== r.order_id)
          return <span style={{ fontWeight: 600, color: '#1B3A5C', whiteSpace: 'nowrap' }}>{fmt(v)}</span>
        return <span style={{ color: '#aaa' }}>—</span>
      },
      sorter: (a: NichiyoClaimReportItem, b: NichiyoClaimReportItem) => (a.payable_amount ?? 0) - (b.payable_amount ?? 0) },
    { title: '核准日', dataIndex: 'approved_date', key: 'approved_date', width: 100,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span> },
  ]

  // ── 欄位定義：部門統計（雙色：請購藍 + 請款橙）────────────────────────────────
  const deptColumns = [
    { title: '部門', dataIndex: 'department_display', key: 'dept', width: 90,
      render: (v: string) => <Tag color="geekblue">{v}</Tag>,
      sorter: (a: NichiyoCombinedDeptStat, b: NichiyoCombinedDeptStat) => a.department_display.localeCompare(b.department_display) },
    // 請購（藍）
    { title: <span style={{ color: '#1B3A5C' }}>請購單數</span>, dataIndex: 'purchase_count', key: 'pc',
      align: 'right' as const, width: 90,
      render: (v: number) => <span style={{ color: '#1B3A5C' }}>{v}</span>,
      sorter: (a: NichiyoCombinedDeptStat, b: NichiyoCombinedDeptStat) => a.purchase_count - b.purchase_count },
    { title: <span style={{ color: '#1B3A5C' }}>請購未稅合計</span>, dataIndex: 'purchase_amount', key: 'pa',
      align: 'right' as const,
      render: (v: number) => <span style={{ color: '#1B3A5C', fontWeight: 600 }}>{fmt(v)}</span>,
      sorter: (a: NichiyoCombinedDeptStat, b: NichiyoCombinedDeptStat) => (a.purchase_amount ?? 0) - (b.purchase_amount ?? 0) },
    { title: <span style={{ color: '#1B3A5C' }}>請購稅額</span>, dataIndex: 'purchase_tax', key: 'pt',
      align: 'right' as const, width: 100,
      render: (v: number) => <span style={{ color: '#1B3A5C' }}>{fmt(v)}</span>,
      sorter: (a: NichiyoCombinedDeptStat, b: NichiyoCombinedDeptStat) => (a.purchase_tax ?? 0) - (b.purchase_tax ?? 0) },
    // 請款（橙）
    { title: <span style={{ color: '#d46b08' }}>請款筆數</span>, dataIndex: 'claim_count', key: 'cc',
      align: 'right' as const, width: 90,
      render: (v: number) => <span style={{ color: '#d46b08' }}>{v}</span>,
      sorter: (a: NichiyoCombinedDeptStat, b: NichiyoCombinedDeptStat) => a.claim_count - b.claim_count },
    { title: <span style={{ color: '#d46b08' }}>請款應付合計</span>, dataIndex: 'claim_payable', key: 'cp',
      align: 'right' as const,
      render: (v: number) => <span style={{ color: '#d46b08', fontWeight: 600 }}>{fmt(v)}</span>,
      sorter: (a: NichiyoCombinedDeptStat, b: NichiyoCombinedDeptStat) => (a.claim_payable ?? 0) - (b.claim_payable ?? 0) },
    { title: <span style={{ color: '#d46b08' }}>請款稅額</span>, dataIndex: 'claim_tax', key: 'ct',
      align: 'right' as const, width: 100,
      render: (v: number) => <span style={{ color: '#d46b08' }}>{fmt(v)}</span>,
      sorter: (a: NichiyoCombinedDeptStat, b: NichiyoCombinedDeptStat) => (a.claim_tax ?? 0) - (b.claim_tax ?? 0) },
    // 占比（以請購金額為基準）
    { title: '請購占比', key: 'ratio', width: 130,
      render: (_: unknown, r: NichiyoCombinedDeptStat) => {
        const total = deptStats.reduce((s, d) => s + (d.purchase_amount ?? 0), 0)
        const pct = total > 0 ? Math.round(((r.purchase_amount ?? 0) / total) * 100) : 0
        return <Progress percent={pct} size="small" strokeColor="#4BA8E8" />
      } },
  ]

  // ── 欄位定義：稽核異常 ────────────────────────────────────────────────────────
  const severityTag = (s: string) => {
    if (s === 'high')   return <Tag color="red">高</Tag>
    if (s === 'medium') return <Tag color="orange">中</Tag>
    return <Tag color="blue">低</Tag>
  }
  const auditColumns = [
    { title: '嚴重性', dataIndex: 'severity', key: 'severity', width: 70, render: severityTag },
    { title: '規則', dataIndex: 'rule_name', key: 'rule_name', width: 160, ellipsis: true },
    { title: '部門', dataIndex: 'department', key: 'department', width: 90,
      render: (v: string) => <Tag color="blue">{v}</Tag> },
    { title: '請款單號', dataIndex: 'doc_no', key: 'doc_no', width: 180, ellipsis: true,
      render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v || '-'}</span> },
    { title: '核准日', dataIndex: 'approved_date', key: 'approved_date', width: 100,
      render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span> },
    { title: '異常說明', dataIndex: 'detail', key: 'detail', ellipsis: true },
    { title: 'Ragic', key: 'ragic_url', width: 60, align: 'center' as const,
      render: (_: unknown, r: NichiyoClaimAuditAnomaly) => (
        r.ragic_url
          ? <Tooltip title="在 Ragic 開啟"><a href={r.ragic_url} target="_blank" rel="noreferrer"><LinkOutlined /></a></Tooltip>
          : null
      ) },
  ]

  // ── 共用篩選列 ────────────────────────────────────────────────────────────────
  const filterBar = (
    <Space wrap>
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
      {dateMode === 'month' && (
        <DatePicker
          picker="month"
          value={pickerValue}
          onChange={(d) => {
            if (!d) return
            const ym = d.format('YYYY-MM')
            setYearMonth(ym)
            setPickerValue(d)
            localStorage.setItem(STORAGE_KEY, ym)
          }}
          disabledDate={(d) => availableMonths.length > 0 && !availableMonths.includes(d.format('YYYY-MM'))}
          allowClear={false}
          size="small"
        />
      )}
      {dateMode === 'year' && (
        <DatePicker
          picker="year"
          value={yearPickerValue}
          onChange={(d) => {
            if (!d) return
            setYearPickerValue(d)
            setYearMonthFrom(d.startOf('year').format('YYYY-MM'))
            setYearMonthTo(d.endOf('year').format('YYYY-MM'))
          }}
          size="small"
        />
      )}
      {dateMode === 'range' && (
        <DatePicker.RangePicker
          picker="month"
          value={rangeValues}
          onChange={(vals) => {
            const [s, e] = vals ?? [null, null]
            setRangeValues([s, e])
            setYearMonthFrom(s ? s.format('YYYY-MM') : undefined)
            setYearMonthTo(e ? e.format('YYYY-MM') : undefined)
          }}
          size="small"
        />
      )}
      <Select
        allowClear placeholder="全部部門" size="small" style={{ width: 120 }}
        value={deptFilter}
        onChange={setDeptFilter}
        options={deptOptions.map((d) => ({ label: d, value: d }))}
      />
      <Select
        allowClear placeholder="全部會科" size="small" style={{ width: 150 }}
        value={accountFilter}
        onChange={setAccountFilter}
        options={accountOptions.map((a) => ({ label: a, value: a }))}
        showSearch
      />
      {(activeTab === 'orders' || activeTab === 'monthly') && (
        <Input.Search
          placeholder="搜尋關鍵字" size="small" style={{ width: 160 }}
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onSearch={(v) => setSearchKeyword(v)}
          onPressEnter={() => setSearchKeyword(searchInput)}
          allowClear
          onClear={() => { setSearchInput(''); setSearchKeyword('') }}
        />
      )}
    </Space>
  )

  // ── KPI 卡片 ──────────────────────────────────────────────────────────────────
  const kpiCards = summary && (
    <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
      <Col xs={12} sm={6}>
        <Card size="small">
          <Statistic title="請款單數" value={summary.order_count}
            prefix={<AccountBookOutlined />} valueStyle={{ color: '#1B3A5C' }} />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card size="small">
          <Statistic title="應付款合計" value={summary.total_payable}
            prefix={<DollarOutlined />} valueStyle={{ color: '#1B3A5C' }}
            formatter={(v) => fmt(v as number)} />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card size="small">
          <Statistic title="品項數" value={summary.item_count}
            prefix={<BarChartOutlined />} valueStyle={{ color: '#4BA8E8' }} />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card size="small">
          <Statistic title="涉及部門" value={summary.dept_count}
            prefix={<TeamOutlined />} valueStyle={{ color: '#4BA8E8' }} />
        </Card>
      </Col>
    </Row>
  )

  // ── Drawer 明細內容 ───────────────────────────────────────────────────────────
  const drawerContent = selectedOrder && (
    <>
      <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="請款單號" span={2}>
          <span style={{ fontFamily: 'monospace' }}>{selectedOrder.order.claim_no || '-'}</span>
        </Descriptions.Item>
        <Descriptions.Item label="申請日期">{selectedOrder.order.request_date || '-'}</Descriptions.Item>
        <Descriptions.Item label="核准日期">{selectedOrder.order.approved_date || '-'}</Descriptions.Item>
        <Descriptions.Item label="部門"><Tag color="blue">{selectedOrder.order.department_display}</Tag></Descriptions.Item>
        <Descriptions.Item label="申請人">{selectedOrder.order.applicant || '-'}</Descriptions.Item>
        <Descriptions.Item label="會科" span={2}>{selectedOrder.order.account_category || '-'}</Descriptions.Item>
        <Descriptions.Item label="事由說明" span={2}>
          {selectedOrder.order.purpose_description || <span style={{ color: '#aaa' }}>（無說明）</span>}
        </Descriptions.Item>
        <Descriptions.Item label="受款者" span={2}>{selectedOrder.order.payee || '-'}</Descriptions.Item>
        <Descriptions.Item label="付款種類">
          {selectedOrder.order.payment_type
            ? <Tag color={selectedOrder.order.payment_type === '匯款' ? 'blue' : 'default'}>{selectedOrder.order.payment_type}</Tag>
            : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="預計付款日">{selectedOrder.order.payment_date || '-'}</Descriptions.Item>
        <Descriptions.Item label="小計（未稅）">
          {fmt(selectedOrder.order.subtotal)}
        </Descriptions.Item>
        <Descriptions.Item label="營業稅">{fmt(selectedOrder.order.tax)}</Descriptions.Item>
        <Descriptions.Item label="總計（含稅）">
          {fmt(selectedOrder.order.total)}
        </Descriptions.Item>
        <Descriptions.Item label="應付款">
          <span style={{ fontWeight: 700, color: '#1B3A5C' }}>{fmt(selectedOrder.order.payable_amount)}</span>
        </Descriptions.Item>
        <Descriptions.Item label="簽核狀態">{statusTag(selectedOrder.order.status)}</Descriptions.Item>
        <Descriptions.Item label="最後更新">{selectedOrder.order.last_updated_at || '-'}</Descriptions.Item>
      </Descriptions>

      {selectedOrder.items.length > 0 ? (
        <>
          <Typography.Title level={5} style={{ marginBottom: 8 }}>
            品項明細（{selectedOrder.items.length} 項）
          </Typography.Title>
          <Table
            dataSource={selectedOrder.items} rowKey={(r, i) => `${r.id ?? i}`}
            size="small" pagination={false} scroll={{ x: 560 }}
            columns={[
              { title: '#', dataIndex: 'seq', width: 36, align: 'center' as const },
              { title: '品名', dataIndex: 'product_name', ellipsis: true },
              { title: '數量', dataIndex: 'qty', width: 55, align: 'right' as const },
              { title: '單位', dataIndex: 'unit', width: 50 },
              { title: '單價', dataIndex: 'unit_price', width: 85, align: 'right' as const, render: fmt },
              { title: '金額', dataIndex: 'amount', width: 90, align: 'right' as const,
                render: (v: number | null) => <span style={{ fontWeight: 600 }}>{fmt(v)}</span> },
              { title: '備註', dataIndex: 'item_remark', ellipsis: true,
                render: (v: string | null) => v || <span style={{ color: '#aaa' }}>—</span> },
            ]}
          />
        </>
      ) : (
        <Alert type={selectedOrder.order.detail_synced ? 'info' : 'warning'} showIcon
          message={selectedOrder.order.detail_synced
            ? '此請款單無品項記錄'
            : '品項尚未同步，請執行「增量同步」以載入品項明細'}
        />
      )}

      {selectedOrder.order.ragic_url && (
        <div style={{ marginTop: 16, textAlign: 'right' }}>
          <Button type="link" size="small"
            href={selectedOrder.order.ragic_url} target="_blank" rel="noopener noreferrer">
            在 Ragic 中開啟 ↗
          </Button>
        </div>
      )}
    </>
  )

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div>
      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <Title level={4} style={{ margin: 0, whiteSpace: 'nowrap' }}>
          日曜核准請款單月報表
        </Title>
        <Space wrap>
          {filterBar}
          <Button
            icon={<FileExcelOutlined />}
            loading={exportLoading}
            onClick={handleExport}
            size="small"
            type="primary"
          >
            匯出 Excel
          </Button>
        </Space>
      </div>

      {/* ── KPI ── */}
      <Spin spinning={summaryLoading}>{kpiCards}</Spin>

      {/* ── Tabs ── */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        size="small"
        items={[
          // ── TAB-1：請款單清單 ──────────────────────────────────────────────────
          {
            key: 'orders',
            label: `請款單清單（${summary?.order_count ?? ordersTotal} 張）`,
            children: (
              <Table
                size="small"
                dataSource={orders}
                rowKey="id"
                loading={ordersLoading}
                columns={orderColumns}
                scroll={{ x: 1100 }}
                onRow={(r) => ({ onClick: () => handleOpenDrawer(r.id), style: { cursor: 'pointer' } })}
                pagination={{
                  current: ordersPage,
                  pageSize: 20,
                  total: ordersTotal,
                  showTotal: (t) => `共 ${t} 筆`,
                  onChange: loadOrders,
                  size: 'small',
                }}
              />
            ),
          },
          // ── TAB-2：月報明細 ───────────────────────────────────────────────────
          {
            key: 'monthly',
            label: `請款單月報明細（${summary?.item_count ?? itemsTotal} 筆品項）`,
            children: (
              <Table
                size="small"
                dataSource={items}
                rowKey={(r) => `${r.order_id}-${r.item_id ?? r.seq}`}
                loading={itemsLoading}
                columns={itemColumns}
                scroll={{ x: 1200 }}
                onRow={(r) => ({ onClick: () => handleOpenDrawer(r.order_id), style: { cursor: 'pointer' } })}
                pagination={{
                  current: itemsPage,
                  pageSize: PAGE_SIZE,
                  total: itemsTotal,
                  showTotal: (t) => `共 ${t} 筆`,
                  onChange: loadItems,
                  size: 'small',
                }}
              />
            ),
          },
          // ── TAB-3：部門統計 ───────────────────────────────────────────────────
          {
            key: 'dept',
            label: '部門統計',
            children: (
              <>
                <Table
                  size="small"
                  dataSource={deptStats}
                  rowKey="department_display"
                  loading={deptStatsLoading}
                  columns={deptColumns}
                  pagination={false}
                  scroll={{ x: 700 }}
                  summary={(data) => {
                    const pCnt     = data.reduce((s, r) => s + (r.purchase_count  ?? 0), 0)
                    const pAmt     = data.reduce((s, r) => s + (r.purchase_amount ?? 0), 0)
                    const pTax     = data.reduce((s, r) => s + (r.purchase_tax    ?? 0), 0)
                    const cCnt     = data.reduce((s, r) => s + (r.claim_count     ?? 0), 0)
                    const cPayable = data.reduce((s, r) => s + (r.claim_payable   ?? 0), 0)
                    const cTax     = data.reduce((s, r) => s + (r.claim_tax       ?? 0), 0)
                    return (
                      <Table.Summary.Row style={{ background: '#f0f4f8', fontWeight: 600 }}>
                        <Table.Summary.Cell index={0}>合計</Table.Summary.Cell>
                        <Table.Summary.Cell index={1} align="right">{pCnt}</Table.Summary.Cell>
                        <Table.Summary.Cell index={2} align="right" style={{ color: '#1B3A5C' }}>{fmt(pAmt)}</Table.Summary.Cell>
                        <Table.Summary.Cell index={3} align="right" style={{ color: '#1B3A5C' }}>{fmt(pTax)}</Table.Summary.Cell>
                        <Table.Summary.Cell index={4} align="right" style={{ color: '#d46b08' }}>{cCnt}</Table.Summary.Cell>
                        <Table.Summary.Cell index={5} align="right" style={{ color: '#d46b08' }}>{fmt(cPayable)}</Table.Summary.Cell>
                        <Table.Summary.Cell index={6} align="right" style={{ color: '#d46b08' }}>{fmt(cTax)}</Table.Summary.Cell>
                        <Table.Summary.Cell index={7} />
                      </Table.Summary.Row>
                    )
                  }}
                />

                {/* admin：同步狀態 */}
                {isAdmin && (
                  <Collapse style={{ marginTop: 24 }}
                    items={[{
                      key: 'sync',
                      label: (
                        <Space>
                          <SyncOutlined />同步狀態管理
                          {(syncStatus?.pending_detail_count ?? 0) > 0 && (
                            <Badge count={syncStatus!.pending_detail_count} size="small" />
                          )}
                        </Space>
                      ),
                      children: (
                        <Card size="small" title={<span style={{ color: '#1B3A5C' }}>日曜請款單同步</span>}>
                          <Space style={{ marginBottom: 12 }}>
                            <Button type="primary" size="small" icon={<SyncOutlined spin={syncing} />}
                              loading={syncing} onClick={() => handleSync(false)}>增量同步</Button>
                            <Button danger size="small" icon={<SyncOutlined />} loading={syncing}
                              onClick={() => Modal.confirm({
                                title: '確認全量重新同步？',
                                content: '將重設所有品項 detail_synced 旗標，重新抓取所有 8 個部門的請款品項明細。',
                                okText: '確認執行', cancelText: '取消',
                                onOk: () => handleSync(true),
                              })}>全量同步</Button>
                            <Button size="small" icon={<SyncOutlined />} onClick={loadSyncStatus} loading={syncLoading}>刷新</Button>
                          </Space>
                          {(syncStatus?.pending_detail_count ?? 0) > 0 && (
                            <Alert type="warning" showIcon style={{ marginBottom: 12 }}
                              message={`尚有 ${syncStatus!.pending_detail_count} 筆未完成品項同步`} />
                          )}
                          <Spin spinning={syncLoading}>
                            {(syncStatus?.dept_stats?.length ?? 0) > 0 && (
                              <Table dataSource={syncStatus!.dept_stats} rowKey="department_display"
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
                            <Table dataSource={syncStatus?.recent_logs ?? []} rowKey="id"
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
                      ),
                    }]}
                  />
                )}
              </>
            ),
          },
          // ── TAB-4：資料異常稽核 ───────────────────────────────────────────────
          {
            key: 'audit',
            label: (() => {
              const total = auditSummary?.total_anomalies ?? 0
              return (
                <Space size={4}>
                  <WarningOutlined style={{ color: total > 0 ? '#ff4d4f' : undefined }} />
                  資料異常
                  {total > 0 && <Badge count={total} size="small" style={{ backgroundColor: '#ff4d4f' }} />}
                </Space>
              )
            })(),
            children: (
              <>
                {auditSummary && (
                  <Spin spinning={auditSummaryLoading}>
                    <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
                      <Col xs={12} sm={6}>
                        <Card size="small">
                          <Statistic title="異常筆數" value={auditSummary.total_anomalies}
                            valueStyle={{ color: auditSummary.total_anomalies > 0 ? '#cf1322' : '#3f8600' }} />
                        </Card>
                      </Col>
                      <Col xs={12} sm={6}>
                        <Card size="small">
                          <Statistic title="涉及請款單" value={auditSummary.total_orders} />
                        </Card>
                      </Col>
                    </Row>
                  </Spin>
                )}
                <Space wrap style={{ marginBottom: 12 }}>
                  <Select
                    allowClear placeholder="全部規則" size="small" style={{ width: 180 }}
                    value={auditRuleFilter}
                    onChange={(v) => { setAuditRuleFilter(v); loadAuditAnomalies(1) }}
                    options={auditSummary?.by_rule.map((r) => ({
                      label: `${r.rule_code} ${r.rule_name} (${r.count})`,
                      value: r.rule_code,
                    }))}
                  />
                </Space>
                <Table
                  size="small"
                  dataSource={auditAnomalies}
                  rowKey={(r) => `${r.order_id}-${r.rule_code}`}
                  loading={auditLoading}
                  columns={auditColumns}
                  scroll={{ x: 900 }}
                  pagination={{
                    total: auditTotal,
                    pageSize: 20,
                    showTotal: (t) => `共 ${t} 筆`,
                    onChange: loadAuditAnomalies,
                    size: 'small',
                  }}
                />
              </>
            ),
          },
        ]}
      />

      {/* ── Detail Drawer ── */}
      <Drawer
        title={selectedOrder
          ? `${selectedOrder.order.claim_no || '請款單'} — ${selectedOrder.order.department_display}`
          : '請款單明細'}
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); setSelectedOrder(null) }}
        width={680}
        bodyStyle={{ padding: 16 }}
        destroyOnClose
      >
        <Spin spinning={drawerLoading}>
          {drawerContent}
        </Spin>
      </Drawer>
    </div>
  )
}
