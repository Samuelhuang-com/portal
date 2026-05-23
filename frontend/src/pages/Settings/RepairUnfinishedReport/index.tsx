/**
 * 報修未完成報表
 * Route: /settings/repair-unfinished-report
 *
 * Tab 1：報修未完成報表（KPI + 查詢 + 表格 + 匯出）
 * Tab 2：飯店 / 商場明細（來源切換）
 * Tab 3：收件人與排程（CRUD + 排程設定 + 手動寄送）
 * Tab 4：寄送紀錄（每日 log）
 *
 * 權限：
 *   repair_unfinished_report_view   — Tab 1 / Tab 2 / 匯出
 *   repair_unfinished_report_manage — Tab 3（收件人、排程、手動寄送）
 *   repair_unfinished_report_admin  — Tab 4（寄送紀錄）
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Drawer,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Statistic,
  Switch,
  Table,
  Tabs,
  Tag,
  TimePicker,
  Tooltip,
  Typography,
} from 'antd'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  DownloadOutlined,
  ExclamationCircleOutlined,
  LinkOutlined,
  MailOutlined,
  PlusOutlined,
  ReloadOutlined,
  SendOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/authStore'
import {
  KpiData,
  MailLog,
  Recipient,
  ScheduleSettings,
  UnifiedCase,
  repairReportApi,
} from '@/api/repairReport'

const { Title, Text } = Typography
const { Option } = Select

// ── 品牌色 ───────────────────────────────────────────────────────────────────
const BRAND_PRIMARY = '#1B3A5C'
const BRAND_ACCENT  = '#4BA8E8'
const OVERDUE_BG    = '#fff5f5'
const OVERDUE_BORDER = '#ffccc7'

// ── 工具函數 ─────────────────────────────────────────────────────────────────
const fmtDate = (v?: string | null) => (v ? v.slice(0, 10) : '—')

function SourceTag({ source }: { source: string }) {
  return (
    <Tag color={source === 'hotel' ? 'blue' : 'orange'}>
      {source === 'hotel' ? '飯店' : '商場'}
    </Tag>
  )
}

function StatusTag({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    待處理: 'default', 處理中: 'processing', 逾期: 'error',
  }
  return <Tag color={colorMap[status] ?? 'default'}>{status || '—'}</Tag>
}

// ── 主頁面 ────────────────────────────────────────────────────────────────────
export default function RepairUnfinishedReport() {
  const { user } = useAuthStore()

  const hasView   = user?.permissions?.includes('repair_unfinished_report_view')   ?? false
  const hasManage = user?.permissions?.includes('repair_unfinished_report_manage') ?? false
  const hasAdmin  = user?.permissions?.includes('repair_unfinished_report_admin')  ?? false
  const isAdmin   = user?.roles?.includes('system_admin') ?? false

  // system_admin 全開
  const canView   = isAdmin || hasView
  const canManage = isAdmin || hasManage
  const canAdmin  = isAdmin || hasAdmin

  const now = dayjs()
  const [activeTab, setActiveTab] = useState('report')

  // ── Tab 1 / 2 共用狀態 ────────────────────────────────────────────────────
  const [year,   setYear]   = useState(now.year())
  const [month,  setMonth]  = useState(now.month() + 1)
  const [source, setSource] = useState<'all' | 'hotel' | 'mall'>('all')
  const [statusFilter, setStatusFilter] = useState<string>()
  const [overdueOnly,  setOverdueOnly]  = useState(false)
  const [repairTypeFilter, setRepairTypeFilter] = useState<string>()
  const [keyword, setKeyword] = useState('')
  const [page,     setPage]     = useState(1)
  const [pageSize, setPageSize] = useState(50)

  const [loading,  setLoading]  = useState(false)
  const [cases,    setCases]    = useState<UnifiedCase[]>([])
  const [total,    setTotal]    = useState(0)
  const [kpi,      setKpi]      = useState<KpiData | null>(null)
  const [filterOpts, setFilterOpts] = useState<{ statuses: string[]; repair_types: string[] }>({ statuses: [], repair_types: [] })

  // Drawer 明細
  const [drawerCase, setDrawerCase] = useState<UnifiedCase | null>(null)

  const fetchCases = useCallback(async () => {
    if (!canView) return
    setLoading(true)
    try {
      const res = await repairReportApi.getUnfinishedCases({
        year, month, source,
        status_filter: statusFilter,
        overdue_only: overdueOnly,
        repair_type_filter: repairTypeFilter,
        keyword: keyword || undefined,
        page, page_size: pageSize,
      })
      setCases(res.items)
      setTotal(res.total)
      setKpi(res.kpi)
      setFilterOpts(res.filter_options)
    } catch (err: any) {
      const status = err?.response?.status
      const detail = err?.response?.data?.detail
      console.error('[RepairReport] fetchCases error:', err?.response ?? err)
      message.error(`載入資料失敗${status ? ` (HTTP ${status})` : ''}${detail ? `：${detail}` : ''}`)
    } finally {
      setLoading(false)
    }
  }, [year, month, source, statusFilter, overdueOnly, repairTypeFilter, keyword, page, pageSize, canView])

  useEffect(() => { fetchCases() }, [fetchCases])

  // ── KPI Cards ─────────────────────────────────────────────────────────────
  const kpiCards = useMemo(() => [
    { title: '未完成案件總數',   value: kpi?.total_unfinished ?? 0,   color: BRAND_PRIMARY, icon: <ExclamationCircleOutlined /> },
    { title: '飯店未完成案件數', value: kpi?.hotel_unfinished ?? 0,   color: '#1677ff',     icon: <ClockCircleOutlined /> },
    { title: '商場未完成案件數', value: kpi?.mall_unfinished  ?? 0,   color: '#fa8c16',     icon: <ClockCircleOutlined /> },
    { title: '可能逾期案件數',   value: kpi?.overdue_count    ?? 0,   color: '#cf1322',     icon: <WarningOutlined /> },
    { title: '平均等待天數',     value: kpi?.avg_pending_days ?? 0,   color: '#722ed1',     suffix: '天' },
    { title: '最長等待天數',     value: kpi?.max_pending_days ?? 0,   color: '#c41d7f',     suffix: '天' },
    { title: '本月新增未完成',   value: kpi?.new_this_month   ?? 0,   color: '#08979c' },
    { title: '今日新增未完成',   value: kpi?.new_today        ?? 0,   color: '#389e0d' },
  ], [kpi])

  // ── 表格欄位定義 ──────────────────────────────────────────────────────────
  const columns = useMemo(() => [
    {
      title: '來源', dataIndex: 'source', key: 'source', width: 70,
      render: (s: string) => <SourceTag source={s} />,
    },
    {
      title: '案件編號', dataIndex: 'case_no', key: 'case_no', width: 140,
      render: (v: string, row: UnifiedCase) => (
        <a onClick={() => setDrawerCase(row)} style={{ color: BRAND_ACCENT }}>{v || row.ragic_id}</a>
      ),
    },
    { title: '報修日期', dataIndex: 'occurred_at', key: 'occurred_at', width: 100, render: fmtDate },
    { title: '報修地點', dataIndex: 'floor', key: 'floor', width: 120, ellipsis: true },
    { title: '工項類別', dataIndex: 'repair_type', key: 'repair_type', width: 110, ellipsis: true },
    { title: '報修內容', dataIndex: 'title', key: 'title', ellipsis: true },
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 90,
      render: (s: string) => <StatusTag status={s} />,
    },
    { title: '工務處理人員', dataIndex: 'responsible_unit', key: 'responsible_unit', width: 120, ellipsis: true },
    {
      title: '等待天數', dataIndex: 'pending_days', key: 'pending_days', width: 80,
      render: (v: number | null) => (v != null ? `${v}` : '—'),
      sorter: (a: UnifiedCase, b: UnifiedCase) => (a.pending_days ?? 0) - (b.pending_days ?? 0),
    },
    {
      title: (
        <Tooltip title={`等待天數 > 3 天（暫定規則）`}>
          可能逾期 <ExclamationCircleOutlined style={{ color: '#faad14' }} />
        </Tooltip>
      ),
      dataIndex: 'is_overdue', key: 'is_overdue', width: 90,
      render: (v: boolean) => v
        ? <Tag color="error" icon={<WarningOutlined />}>是</Tag>
        : <Tag color="default">否</Tag>,
    },
    {
      title: '原始資料',
      dataIndex: 'ragic_url', key: 'ragic_url', width: 80,
      render: (url: string) => url
        ? <a href={url} target="_blank" rel="noopener noreferrer"><LinkOutlined style={{ color: BRAND_ACCENT }} /></a>
        : '—',
    },
  ], [])

  // ── 篩選列 ────────────────────────────────────────────────────────────────
  const FilterBar = () => (
    <Card size="small" style={{ marginBottom: 12, background: '#f8fafc', border: `1px solid #e2e8f0` }}>
      <Space wrap>
        <DatePicker
          picker="month"
          value={dayjs(`${year}-${String(month).padStart(2, '0')}`, 'YYYY-MM')}
          onChange={d => { if (d) { setYear(d.year()); setMonth(d.month() + 1); setPage(1) } }}
          allowClear={false}
        />
        <Select value={source} onChange={v => { setSource(v); setPage(1) }} style={{ width: 100 }}>
          <Option value="all">全部</Option>
          <Option value="hotel">飯店</Option>
          <Option value="mall">商場</Option>
        </Select>
        <Select
          placeholder="狀態篩選"
          allowClear
          value={statusFilter}
          onChange={v => { setStatusFilter(v); setPage(1) }}
          style={{ minWidth: 120 }}
        >
          {filterOpts.statuses.map(s => <Option key={s} value={s}>{s}</Option>)}
        </Select>
        <Select
          placeholder="工項類別"
          allowClear
          value={repairTypeFilter}
          onChange={v => { setRepairTypeFilter(v); setPage(1) }}
          style={{ minWidth: 120 }}
        >
          {filterOpts.repair_types.map(t => <Option key={t} value={t}>{t}</Option>)}
        </Select>
        <Input.Search
          placeholder="關鍵字搜尋"
          value={keyword}
          onChange={e => setKeyword(e.target.value)}
          onSearch={() => { setPage(1); fetchCases() }}
          style={{ width: 180 }}
          allowClear
        />
        <Switch
          checkedChildren="只看逾期"
          unCheckedChildren="全部未完成"
          checked={overdueOnly}
          onChange={v => { setOverdueOnly(v); setPage(1) }}
        />
        <Button icon={<ReloadOutlined />} onClick={fetchCases}>重新整理</Button>
        {canView && (
          <Button
            icon={<DownloadOutlined />}
            type="primary"
            ghost
            onClick={() => {
              const url = repairReportApi.getExportUrl({ year, month, source, overdue_only: overdueOnly, keyword: keyword || undefined })
              window.open(url, '_blank')
            }}
          >
            匯出 Excel
          </Button>
        )}
      </Space>
    </Card>
  )

  // ── Tab 1：報修未完成報表 ──────────────────────────────────────────────────
  const Tab1 = () => (
    <div>
      {/* KPI Cards */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {kpiCards.map(c => (
          <Col key={c.title} xs={12} sm={8} md={6} lg={3}>
            <Card size="small" bodyStyle={{ padding: '12px 16px' }}>
              <Statistic
                title={<span style={{ fontSize: 12 }}>{c.title}</span>}
                value={c.value}
                suffix={c.suffix}
                valueStyle={{ color: c.color, fontSize: 22, fontWeight: 700 }}
                prefix={c.icon}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Alert
        type="warning"
        showIcon
        message="⚠️ 逾期判斷暫定規則：等待天數 > 3 天標示為「可能逾期」，非正式逾期標準。"
        style={{ marginBottom: 12 }}
        closable
      />

      <FilterBar />

      <Table
        dataSource={cases}
        columns={columns}
        rowKey={r => `${r.source}-${r.ragic_id}`}
        loading={loading}
        size="small"
        scroll={{ x: 1400 }}
        rowClassName={r => r.is_overdue ? 'overdue-row' : ''}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          pageSizeOptions: ['20', '50', '100', '200'],
          showTotal: t => `共 ${t} 筆`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
        onRow={r => ({ onClick: () => setDrawerCase(r), style: { cursor: 'pointer' } })}
      />

      <style>{`.overdue-row td { background: ${OVERDUE_BG} !important; }`}</style>
    </div>
  )

  // ── Tab 2：飯店 / 商場明細（各自獨立 fetch，避免分頁造成 client filter 漏資料）─
  const Tab2 = () => {
    const [tab2Source, setTab2Source] = useState<'hotel' | 'mall'>('hotel')
    const [tab2Cases,  setTab2Cases]  = useState<UnifiedCase[]>([])
    const [tab2Total,  setTab2Total]  = useState(0)
    const [tab2Loading, setTab2Loading] = useState(false)
    const [tab2Page,    setTab2Page]   = useState(1)
    const [tab2PageSize, setTab2PageSize] = useState(50)

    const fetchTab2 = useCallback(async (src: 'hotel' | 'mall', pg: number, ps: number) => {
      if (!canView) return
      setTab2Loading(true)
      try {
        const res = await repairReportApi.getUnfinishedCases({
          year, month, source: src, page: pg, page_size: ps,
        })
        setTab2Cases(res.items)
        setTab2Total(res.total)
      } catch (err: any) {
        message.error('載入明細資料失敗')
      } finally {
        setTab2Loading(false)
      }
    }, [year, month, canView])

    // 切換來源或年月時重新 fetch
    useEffect(() => {
      setTab2Page(1)
      fetchTab2(tab2Source, 1, tab2PageSize)
    }, [tab2Source, year, month, fetchTab2])

    const switchSource = (src: 'hotel' | 'mall') => {
      setTab2Source(src)
      setTab2Page(1)
    }

    return (
      <div>
        <Space style={{ marginBottom: 12 }}>
          <Button
            type={tab2Source === 'hotel' ? 'primary' : 'default'}
            onClick={() => switchSource('hotel')}
            style={tab2Source === 'hotel' ? { background: BRAND_PRIMARY } : {}}
          >
            飯店 ({kpi?.hotel_unfinished ?? 0})
          </Button>
          <Button
            type={tab2Source === 'mall' ? 'primary' : 'default'}
            onClick={() => switchSource('mall')}
            style={tab2Source === 'mall' ? { background: '#fa8c16', borderColor: '#fa8c16' } : {}}
          >
            商場 ({kpi?.mall_unfinished ?? 0})
          </Button>
          <DatePicker
            picker="month"
            value={dayjs(`${year}-${String(month).padStart(2, '0')}`, 'YYYY-MM')}
            onChange={d => { if (d) { setYear(d.year()); setMonth(d.month() + 1) } }}
            allowClear={false}
          />
        </Space>
        <Table
          dataSource={tab2Cases}
          columns={columns.filter(c => c.key !== 'source')}
          rowKey={r => `${r.source}-${r.ragic_id}`}
          size="small"
          loading={tab2Loading}
          scroll={{ x: 1200 }}
          rowClassName={r => r.is_overdue ? 'overdue-row' : ''}
          pagination={{
            current: tab2Page,
            pageSize: tab2PageSize,
            total: tab2Total,
            showSizeChanger: true,
            pageSizeOptions: ['20', '50', '100', '200'],
            showTotal: t => `共 ${t} 筆`,
            onChange: (p, ps) => {
              setTab2Page(p)
              setTab2PageSize(ps)
              fetchTab2(tab2Source, p, ps)
            },
          }}
          onRow={r => ({ onClick: () => setDrawerCase(r), style: { cursor: 'pointer' } })}
        />
        <style>{`.overdue-row td { background: ${OVERDUE_BG} !important; }`}</style>
      </div>
    )
  }

  // ── Tab 3：收件人與排程 ────────────────────────────────────────────────────
  const Tab3 = () => {
    const [recipients, setRecipients] = useState<Recipient[]>([])
    const [rcptLoading, setRcptLoading] = useState(false)
    const [rcptModalOpen, setRcptModalOpen] = useState(false)
    const [editingRcpt, setEditingRcpt] = useState<Recipient | null>(null)
    const [rcptForm] = Form.useForm()

    const [schedule, setSchedule] = useState<ScheduleSettings | null>(null)
    const [schedLoading, setSchedLoading] = useState(false)
    const [schedForm] = Form.useForm()

    const [sendLoading, setSendLoading] = useState(false)
    const [sendResultModal, setSendResultModal] = useState(false)
    const [sendResults, setSendResults] = useState<{ sent_count: number; failed_count: number; results: { recipient_email: string; success: boolean; error_message: string | null }[] } | null>(null)

    const fetchRecipients = async () => {
      setRcptLoading(true)
      try { setRecipients(await repairReportApi.listRecipients()) }
      catch { message.error('載入收件人失敗') }
      finally { setRcptLoading(false) }
    }

    const fetchSchedule = async () => {
      setSchedLoading(true)
      try {
        const s = await repairReportApi.getSchedule()
        setSchedule(s)
        schedForm.setFieldsValue({ ...s })
      } catch { message.error('載入排程設定失敗') }
      finally { setSchedLoading(false) }
    }

    useEffect(() => {
      if (!canManage) return
      fetchRecipients()
      fetchSchedule()
    }, [])

    const handleSaveRecipient = async () => {
      try {
        const vals = await rcptForm.validateFields()
        if (editingRcpt) {
          await repairReportApi.updateRecipient(editingRcpt.id, vals)
          message.success('已更新')
        } else {
          await repairReportApi.createRecipient(vals)
          message.success('已新增')
        }
        setRcptModalOpen(false)
        fetchRecipients()
      } catch (e: any) {
        if (e?.response?.data?.detail) message.error(e.response.data.detail)
      }
    }

    const handleSaveSchedule = async () => {
      try {
        const vals = await schedForm.validateFields()
        await repairReportApi.updateSchedule(vals)
        message.success('寄信設定已儲存')
        fetchSchedule()
      } catch { message.error('儲存失敗') }
    }

    const handleManualSend = async () => {
      setSendLoading(true)
      try {
        const res = await repairReportApi.sendNow({ year, month })
        setSendResults(res)
        setSendResultModal(true)
      } catch { message.error('寄送失敗') }
      finally { setSendLoading(false) }
    }

    if (!canManage) return <Alert type="warning" message="您沒有管理權限" />

    return (
      <Row gutter={24}>
        {/* 左：收件人管理 */}
        <Col xs={24} lg={14}>
          <Card
            title="收件人管理"
            extra={
              <Button type="primary" icon={<PlusOutlined />} size="small"
                onClick={() => { setEditingRcpt(null); rcptForm.resetFields(); setRcptModalOpen(true) }}>
                新增收件人
              </Button>
            }
          >
            <Table
              dataSource={recipients}
              rowKey="id"
              size="small"
              loading={rcptLoading}
              pagination={false}
              columns={[
                { title: '姓名', dataIndex: 'name' },
                { title: 'Email', dataIndex: 'email' },
                { title: '部門', dataIndex: 'department' },
                {
                  title: '狀態', dataIndex: 'is_active',
                  render: (v: boolean) => <Badge status={v ? 'success' : 'default'} text={v ? '啟用' : '停用'} />,
                },
                {
                  title: '操作', width: 150,
                  render: (_: unknown, r: Recipient) => (
                    <Space size={4}>
                      <Button size="small" onClick={() => {
                        setEditingRcpt(r); rcptForm.setFieldsValue(r); setRcptModalOpen(true)
                      }}>編輯</Button>
                      <Popconfirm title="確認寄送測試信？" onConfirm={async () => {
                        const res = await repairReportApi.testSendToRecipient(r.id)
                        res.success ? message.success(res.message) : message.error(res.message)
                      }}>
                        <Button size="small" icon={<SendOutlined />}>測試</Button>
                      </Popconfirm>
                      <Popconfirm title="確認刪除？" onConfirm={async () => {
                        await repairReportApi.deleteRecipient(r.id); fetchRecipients()
                      }}>
                        <Button size="small" danger>刪除</Button>
                      </Popconfirm>
                    </Space>
                  ),
                },
              ]}
            />
          </Card>
        </Col>

        {/* 右：排程設定 + 手動寄送 */}
        <Col xs={24} lg={10}>
          <Card
            title="寄信設定"
            extra={<Text type="secondary" style={{ fontSize: 12 }}>排程時間請至 sync_tool 設定</Text>}
            loading={schedLoading}
          >
            <Form form={schedForm} layout="vertical" onFinish={handleSaveSchedule}>
              <Form.Item name="schedule_name" label="排程名稱">
                <Input />
              </Form.Item>
              <Form.Item name="report_year_month_mode" label="報表年月">
                <Select>
                  <Option value="current_month">當月</Option>
                  <Option value="previous_month">上個月</Option>
                </Select>
              </Form.Item>
              <Form.Item name="include_hotel" label="包含飯店" valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item name="include_mall" label="包含商場" valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item name="include_excel_attachment" label="附加 Excel 附件" valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit">儲存寄信設定</Button>
                </Space>
              </Form.Item>
            </Form>
          </Card>

          <Card title="手動寄送" style={{ marginTop: 16 }}>
            <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
              立即寄送 {year}年{month}月 未完成報表給所有啟用收件人
            </Text>
            <Alert
              type="info"
              showIcon
              message="手動寄送後會寫入寄送紀錄"
              style={{ marginBottom: 12 }}
            />
            <Popconfirm
              title={`確認立即寄送 ${year}年${month}月 報表？`}
              onConfirm={handleManualSend}
            >
              <Button type="primary" icon={<MailOutlined />} loading={sendLoading} block>
                立即寄送測試
              </Button>
            </Popconfirm>
          </Card>
        </Col>

        {/* 收件人新增/編輯 Modal */}
        <Modal
          title={editingRcpt ? '編輯收件人' : '新增收件人'}
          open={rcptModalOpen}
          onOk={handleSaveRecipient}
          onCancel={() => setRcptModalOpen(false)}
          okText="儲存"
          cancelText="取消"
        >
          <Form form={rcptForm} layout="vertical">
            <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="email" label="Email"
              rules={[{ required: true }, { type: 'email', message: 'Email 格式不正確' }]}>
              <Input />
            </Form.Item>
            <Form.Item name="department" label="部門">
              <Input />
            </Form.Item>
            <Form.Item name="role" label="職稱">
              <Input />
            </Form.Item>
            <Form.Item name="is_active" label="啟用" valuePropName="checked" initialValue={true}>
              <Switch />
            </Form.Item>
          </Form>
        </Modal>

        {/* 手動寄送結果 Modal */}
        <Modal
          title="寄送結果"
          open={sendResultModal}
          onOk={() => setSendResultModal(false)}
          onCancel={() => setSendResultModal(false)}
          cancelButtonProps={{ style: { display: 'none' } }}
        >
          {sendResults && (
            <div>
              <Space style={{ marginBottom: 12 }}>
                <Tag color="success" icon={<CheckCircleOutlined />}>成功 {sendResults.sent_count} 筆</Tag>
                {sendResults.failed_count > 0 && (
                  <Tag color="error" icon={<CloseCircleOutlined />}>失敗 {sendResults.failed_count} 筆</Tag>
                )}
              </Space>
              <Table
                dataSource={sendResults.results}
                rowKey="recipient_email"
                size="small"
                pagination={false}
                columns={[
                  { title: 'Email', dataIndex: 'recipient_email' },
                  {
                    title: '狀態', dataIndex: 'success',
                    render: (v: boolean) => v
                      ? <Tag color="success">成功</Tag>
                      : <Tag color="error">失敗</Tag>,
                  },
                  { title: '錯誤', dataIndex: 'error_message', render: (v: string | null) => v || '—', ellipsis: true },
                ]}
              />
            </div>
          )}
        </Modal>
      </Row>
    )
  }

  // ── Tab 4：寄送紀錄 ────────────────────────────────────────────────────────
  const Tab4 = () => {
    const [logs, setLogs] = useState<MailLog[]>([])
    const [logTotal, setLogTotal] = useState(0)
    const [logLoading, setLogLoading] = useState(false)
    const [logPage, setLogPage] = useState(1)
    const [logYear,  setLogYear]  = useState<number | undefined>(now.year())
    const [logMonth, setLogMonth] = useState<number | undefined>(now.month() + 1)
    const [logStatus, setLogStatus] = useState<string | undefined>()

    const fetchLogs = useCallback(async () => {
      setLogLoading(true)
      try {
        const res = await repairReportApi.getMailLogs({
          year: logYear, month: logMonth,
          status: logStatus,
          page: logPage, page_size: 50,
        })
        setLogs(res.items)
        setLogTotal(res.total)
      } catch { message.error('載入寄送紀錄失敗') }
      finally { setLogLoading(false) }
    }, [logYear, logMonth, logStatus, logPage])

    useEffect(() => { if (canAdmin) fetchLogs() }, [fetchLogs, canAdmin])

    if (!canAdmin) return <Alert type="warning" message="您沒有查看寄送紀錄的權限" />

    const statusColor: Record<string, string> = { success: 'success', failed: 'error', skipped: 'default' }
    const statusLabel: Record<string, string> = { success: '成功', failed: '失敗', skipped: '略過' }

    return (
      <div>
        <Space style={{ marginBottom: 12 }} wrap>
          <DatePicker
            picker="month"
            value={logYear && logMonth ? dayjs(`${logYear}-${String(logMonth).padStart(2, '0')}`, 'YYYY-MM') : null}
            onChange={d => { setLogYear(d?.year()); setLogMonth(d ? d.month() + 1 : undefined); setLogPage(1) }}
            placeholder="年月篩選"
          />
          <Select
            placeholder="狀態"
            allowClear
            value={logStatus}
            onChange={v => { setLogStatus(v); setLogPage(1) }}
            style={{ width: 100 }}
          >
            <Option value="success">成功</Option>
            <Option value="failed">失敗</Option>
            <Option value="skipped">略過</Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={fetchLogs}>重新整理</Button>
        </Space>

        <Table
          dataSource={logs}
          rowKey="id"
          size="small"
          loading={logLoading}
          scroll={{ x: 1100 }}
          pagination={{
            current: logPage,
            pageSize: 50,
            total: logTotal,
            showTotal: t => `共 ${t} 筆`,
            onChange: p => setLogPage(p),
          }}
          columns={[
            { title: '寄送日期', dataIndex: 'send_date', width: 100 },
            { title: '時間',    dataIndex: 'send_time', width: 70 },
            { title: '報表年月', width: 90, render: (_: unknown, r: MailLog) => `${r.report_year}/${String(r.report_month).padStart(2,'0')}` },
            { title: '收件人', dataIndex: 'recipient_email', ellipsis: true },
            {
              title: '狀態', dataIndex: 'status', width: 70,
              render: (s: string) => <Tag color={statusColor[s] ?? 'default'}>{statusLabel[s] ?? s}</Tag>,
            },
            { title: '飯店未完成', dataIndex: 'hotel_unfinished_count', width: 90, render: (v: number | null) => v ?? '—' },
            { title: '商場未完成', dataIndex: 'mall_unfinished_count',  width: 90, render: (v: number | null) => v ?? '—' },
            { title: '總計',      dataIndex: 'total_unfinished_count',  width: 70, render: (v: number | null) => v ?? '—' },
            { title: '附件',  dataIndex: 'attachment_filename', width: 90,  render: (v: string | null) => v ? <Tag color="blue">有</Tag> : '—' },
            { title: '錯誤訊息', dataIndex: 'error_message', ellipsis: true, render: (v: string | null) => v ? <Text type="danger" style={{ fontSize: 12 }}>{v}</Text> : '—' },
          ]}
        />
      </div>
    )
  }

  // ── 案件 Drawer ───────────────────────────────────────────────────────────
  const CaseDrawer = () => {
    if (!drawerCase) return null
    const c = drawerCase
    const identifier = c.case_no || c.ragic_id

    return (
      <Drawer
        title={
          <Space>
            <SourceTag source={c.source} />
            <span>報修案件：{identifier}</span>
            {c.ragic_url && (
              <a href={c.ragic_url} target="_blank" rel="noopener noreferrer">
                <LinkOutlined style={{ color: BRAND_ACCENT }} /> 在 Ragic 查看
              </a>
            )}
          </Space>
        }
        open={!!drawerCase}
        onClose={() => setDrawerCase(null)}
        width={480}
      >
        <Descriptions column={1} size="small" bordered labelStyle={{ width: 120, fontWeight: 600 }}>
          <Descriptions.Item label="案件編號">{c.case_no || '—'}</Descriptions.Item>
          <Descriptions.Item label="報修日期">{fmtDate(c.occurred_at)}</Descriptions.Item>
          <Descriptions.Item label="報修地點">{c.floor || '—'}</Descriptions.Item>
          <Descriptions.Item label="工項類別">{c.repair_type || '—'}</Descriptions.Item>
          <Descriptions.Item label="報修內容">{c.title || '—'}</Descriptions.Item>
          <Descriptions.Item label="狀態"><StatusTag status={c.status} /></Descriptions.Item>
          <Descriptions.Item label="工務處理人員">{c.responsible_unit || '—'}</Descriptions.Item>
          <Descriptions.Item label="已等待天數">
            {c.pending_days != null ? `${c.pending_days} 天` : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="可能逾期">
            {c.is_overdue
              ? <Tag color="error" icon={<WarningOutlined />}>是（暫定：&gt;3 天）</Tag>
              : <Tag color="default">否</Tag>}
          </Descriptions.Item>
          <Descriptions.Item label="最後更新">{fmtDate(c.synced_at)}</Descriptions.Item>
          <Descriptions.Item label="處理說明">{c.finance_note || '—'}</Descriptions.Item>
        </Descriptions>
      </Drawer>
    )
  }

  // ── Tab 定義 ──────────────────────────────────────────────────────────────
  const tabItems = [
    ...(canView ? [{
      key: 'report',
      label: <span><ExclamationCircleOutlined /> 報修未完成報表</span>,
      children: <Tab1 />,
    }] : []),
    ...(canView ? [{
      key: 'detail',
      label: <span>飯店 / 商場明細</span>,
      children: <Tab2 />,
    }] : []),
    ...(canManage ? [{
      key: 'recipients',
      label: <span><MailOutlined /> 收件人與排程</span>,
      children: <Tab3 />,
    }] : []),
    ...(canAdmin ? [{
      key: 'logs',
      label: <span>寄送紀錄</span>,
      children: <Tab4 />,
    }] : []),
  ]

  return (
    <div style={{ padding: '0 0 24px' }}>
      <div style={{
        background: `linear-gradient(135deg, ${BRAND_PRIMARY}, ${BRAND_ACCENT})`,
        padding: '16px 24px',
        borderRadius: 8,
        marginBottom: 16,
      }}>
        <Title level={4} style={{ color: '#fff', margin: 0 }}>
          報修未完成報表
        </Title>
        <Text style={{ color: '#dce9f5', fontSize: 13 }}>
          整合飯店與商場報修未完成案件，支援排程寄信與 Excel 匯出
        </Text>
      </div>

      {!canView && (
        <Alert type="error" message="您沒有查看此頁面的權限，請聯絡系統管理員。" showIcon />
      )}

      {canView && (
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          destroyInactiveTabPane={false}
        />
      )}

      <CaseDrawer />
    </div>
  )
}
