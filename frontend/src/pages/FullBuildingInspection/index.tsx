/**
 * 整棟巡檢 — 統一整合頁面（掛於商場管理群組）
 *
 * 將原本分散的 Dashboard + RF / B4F / B2F / B1F 巡檢紀錄整合為 Tabs
 *   Tab 1 統計總覽  — 今日各樓層 KPI + Sheet 完成率彙整
 *   Tab 2 RF 巡檢  — 月份篩選 + 場次清單
 *   Tab 3 B4F 巡檢 — 同上
 *   Tab 4 B2F 巡檢 — 同上
 *   Tab 5 B1F 巡檢 — 同上
 *
 * URL query param：?tab=summary|rf|b4f|b2f|b1f
 * 資料來源：尚未建立本地同步，各欄位顯示空狀態，保留結構供日後擴充。
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Tabs, Alert, DatePicker, Badge,
  message, Progress,
} from 'antd'
import {
  HomeOutlined, SyncOutlined, ReloadOutlined,
  WarningOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  DashboardOutlined, SafetyOutlined, ClockCircleOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import {
  FULL_BUILDING_INSPECTION_SHEET_LIST,
  type FullBuildingInspectionSheet,
} from '@/constants/fullBuildingInspection'

const { Title, Text } = Typography

// ── 型別 ─────────────────────────────────────────────────────────────────────

interface SheetStats extends FullBuildingInspectionSheet {
  total_batches:   number
  total_items:     number
  checked_items:   number
  abnormal_items:  number
  pending_items:   number
  unchecked_items: number
  completion_rate: number
  has_data:        boolean
}

interface BatchRow {
  id:              string
  inspection_date: string
  inspector_name:  string
  completion_rate: number
  total:           number
  checked:         number
  abnormal:        number
  pending:         number
}

// ── 共用樓層巡檢紀錄 Tab ──────────────────────────────────────────────────────

function FloorInspectionListTab({ sheetKey }: { sheetKey: string }) {
  const [yearMonth, setYearMonth] = useState<string>(dayjs().format('YYYY/MM'))
  const [loading,   setLoading]   = useState(false)
  const [syncing,   setSyncing]   = useState(false)
  const [batches,   setBatches]   = useState<BatchRow[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    // TODO: 接 API → fetchFullBuildingBatches(sheetKey, { year_month: yearMonth })
    await new Promise((r) => setTimeout(r, 100))
    setBatches([])
    setLoading(false)
  }, [sheetKey, yearMonth])

  useEffect(() => { load() }, [load])

  const handleSync = async () => {
    setSyncing(true)
    try {
      // TODO: 接 API → syncFullBuildingFromRagic(sheetKey)
      await new Promise((r) => setTimeout(r, 800))
      message.info('同步功能開發中，請直接至 Ragic 填寫巡檢表單')
    } catch {
      message.error('同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  const columns = [
    {
      title: '巡檢日期',
      dataIndex: 'inspection_date',
      width: 110,
      sorter: (a: BatchRow, b: BatchRow) =>
        a.inspection_date.localeCompare(b.inspection_date),
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '巡檢人員',
      dataIndex: 'inspector_name',
      width: 100,
    },
    {
      title: '狀態',
      width: 90,
      render: (_: unknown, row: BatchRow) => {
        if (row.abnormal > 0)                          return <Tag color="#FF4D4F">有異常</Tag>
        if (row.pending  > 0)                          return <Tag color="#FAAD14">待處理</Tag>
        if (row.checked >= row.total && row.total > 0) return <Tag color="#52C41A">已完成</Tag>
        return <Tag color="#4BA8E8">巡檢中</Tag>
      },
    },
    {
      title: '巡檢進度',
      width: 200,
      render: (_: unknown, row: BatchRow) => (
        <div>
          <Progress
            percent={row.completion_rate}
            size="small"
            strokeColor={{ from: '#FAAD14', to: '#52C41A' }}
            format={() => `${row.completion_rate}%`}
          />
          <Text type="secondary" style={{ fontSize: 11 }}>
            {row.checked} / {row.total} 已巡檢
          </Text>
        </div>
      ),
    },
    {
      title: '異常',
      dataIndex: 'abnormal',
      width: 65,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#FF4D4F" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '待處理',
      dataIndex: 'pending',
      width: 65,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#FAAD14" /> : <Text type="secondary">—</Text>,
    },
  ]

  return (
    <div>
      <Row gutter={8} style={{ marginBottom: 16 }} align="middle">
        <Col>
          <DatePicker
            picker="month"
            value={dayjs(yearMonth, 'YYYY/MM')}
            format="YYYY/MM"
            allowClear={false}
            onChange={(d) => { if (d) setYearMonth(d.format('YYYY/MM')) }}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            重新整理
          </Button>
        </Col>
        <Col>
          <Button
            icon={<SyncOutlined spin={syncing} />}
            loading={syncing}
            onClick={handleSync}
          >
            同步 Ragic
          </Button>
        </Col>
      </Row>
      <Table<BatchRow>
        dataSource={batches}
        rowKey="id"
        columns={columns}
        loading={loading}
        size="middle"
        pagination={{ pageSize: 30, showTotal: (t) => `共 ${t} 筆` }}
        locale={{ emptyText: '尚無巡檢紀錄（請先執行資料同步）' }}
      />
    </div>
  )
}

// ── 統計總覽 Tab ──────────────────────────────────────────────────────────────

function SummaryTabContent() {
  const [targetDate, setTargetDate] = useState<string>(dayjs().format('YYYY/MM/DD'))
  const [loading,    setLoading]    = useState(false)
  const [syncing,    setSyncing]    = useState(false)

  const buildEmptyStats = (): SheetStats[] =>
    FULL_BUILDING_INSPECTION_SHEET_LIST.map((s) => ({
      ...s,
      total_batches:   0,
      total_items:     0,
      checked_items:   0,
      abnormal_items:  0,
      pending_items:   0,
      unchecked_items: 0,
      completion_rate: 0,
      has_data:        false,
    }))

  const [sheets, setSheets] = useState<SheetStats[]>(buildEmptyStats())

  const loadSummary = useCallback(async () => {
    setLoading(true)
    // TODO: 接 API → fetchFullBuildingDashboardSummary(targetDate)
    await new Promise((r) => setTimeout(r, 100))
    setSheets(buildEmptyStats())
    setLoading(false)
  }, [targetDate])

  useEffect(() => { loadSummary() }, [loadSummary])

  const handleSync = async () => {
    setSyncing(true)
    try {
      // TODO: 接 API → syncFullBuildingAllFromRagic()
      await new Promise((r) => setTimeout(r, 800))
      message.info('同步功能開發中，請直接至 Ragic 填寫巡檢表單')
    } catch {
      message.error('同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  const totalBatches = sheets.reduce((s, r) => s + r.total_batches, 0)
  const checkedAll   = sheets.reduce((s, r) => s + r.checked_items, 0)
  const totalAll     = sheets.reduce((s, r) => s + r.total_items,   0)
  const abnormalAll  = sheets.reduce((s, r) => s + r.abnormal_items + r.pending_items, 0)
  const rateAll      = totalAll > 0 ? Math.round((checkedAll / totalAll) * 100) : 0

  const sheetCols = [
    {
      title: '巡檢樓層',
      dataIndex: 'title',
      ellipsis: true,
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '場次',
      dataIndex: 'total_batches',
      width: 60,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#1B3A5C" showZero /> : <Text type="secondary">—</Text>,
    },
    {
      title: '完成率',
      dataIndex: 'completion_rate',
      width: 130,
      render: (v: number, row: SheetStats) =>
        row.has_data ? (
          <Progress
            percent={v}
            size="small"
            strokeColor={{ from: v < 50 ? '#FF4D4F' : '#FAAD14', to: '#52C41A' }}
            format={(p) => `${p}%`}
          />
        ) : (
          <Text type="secondary">無資料</Text>
        ),
    },
    {
      title: '異常',
      dataIndex: 'abnormal_items',
      width: 60,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#FF4D4F" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '待處理',
      dataIndex: 'pending_items',
      width: 65,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#FAAD14" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '未巡檢',
      dataIndex: 'unchecked_items',
      width: 65,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#999" /> : <Text type="secondary">—</Text>,
    },
  ]

  return (
    <div>
      <Row style={{ marginBottom: 16 }} align="middle" gutter={8}>
        <Col>
          <Space>
            <Text strong>查詢日期：</Text>
            <DatePicker
              value={dayjs(targetDate, 'YYYY/MM/DD')}
              format="YYYY/MM/DD"
              allowClear={false}
              onChange={(d) => { if (d) setTargetDate(d.format('YYYY/MM/DD')) }}
            />
            <Button icon={<ReloadOutlined />} onClick={loadSummary} loading={loading}>
              重新整理
            </Button>
            <Button
              icon={<SyncOutlined spin={syncing} />}
              loading={syncing}
              onClick={handleSync}
            >
              同步全部 Sheet
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 全體 KPI */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {[
          { title: '今日巡檢場次',  value: totalBatches, color: '#1B3A5C',                          icon: <DashboardOutlined /> },
          { title: '已巡檢項目',    value: checkedAll,   suffix: `/${totalAll}`, color: '#4BA8E8',  icon: <CheckCircleOutlined /> },
          { title: '異常 + 待處理', value: abnormalAll,  color: '#FF4D4F',                          icon: <WarningOutlined /> },
          { title: '整體完成率',    value: rateAll,      suffix: '%', color: rateAll >= 80 ? '#52C41A' : '#FAAD14', icon: <ExclamationCircleOutlined /> },
        ].map((card) => (
          <Col flex={1} style={{ minWidth: 140 }} key={card.title}>
            <Card size="small" hoverable style={{ height: '100%' }}>
              <Statistic
                title={card.title}
                value={card.value}
                suffix={card.suffix}
                prefix={<span style={{ color: card.color }}>{card.icon}</span>}
                valueStyle={{ color: card.color, fontSize: 26 }}
              />
            </Card>
          </Col>
        ))}
        <Col flex={1} style={{ minWidth: 140 }}>
          <Card size="small" hoverable style={{ height: '100%' }}>
            <Statistic
              title="巡檢時間"
              value={0}
              suffix="小時"
              prefix={<span style={{ color: '#4BA8E8' }}><ClockCircleOutlined /></span>}
              valueStyle={{ color: '#4BA8E8', fontSize: 26 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 各 Sheet 明細表 */}
      <Card size="small">
        <Table<SheetStats>
          dataSource={sheets}
          rowKey="key"
          columns={sheetCols}
          loading={loading}
          size="small"
          pagination={false}
          locale={{ emptyText: '尚無資料' }}
        />
      </Card>

      {!loading && totalAll === 0 && (
        <Alert
          style={{ marginTop: 16 }}
          type="info"
          message={`${targetDate} 尚無任何整棟巡檢記錄，請確認巡檢是否已執行並同步。`}
          showIcon
        />
      )}
    </div>
  )
}

// ── 主元件 ────────────────────────────────────────────────────────────────────

const VALID_TABS = ['summary', 'rf', 'b4f', 'b2f', 'b1f']

export default function FullBuildingInspectionDashboard() {
  const [searchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState<string>(() => {
    const t = searchParams.get('tab')
    return t && VALID_TABS.includes(t) ? t : 'summary'
  })

  // 已開啟過的 Tab（懶載入：只在首次切入時掛載子元件）
  const [openedTabs, setOpenedTabs] = useState<Set<string>>(
    () => new Set([activeTab])
  )

  const handleTabChange = (key: string) => {
    setActiveTab(key)
    setOpenedTabs((prev) => new Set([...prev, key]))
  }

  return (
    <div style={{ padding: '0 4px' }}>
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <HomeOutlined /> },
          { title: NAV_GROUP.mall },
          { title: NAV_PAGE.fullBuildingDashboard },
        ]}
      />

      <Row align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
            <SafetyOutlined /> {NAV_PAGE.fullBuildingDashboard}
          </Title>
        </Col>
      </Row>

      <Tabs
        type="card"
        activeKey={activeTab}
        onChange={handleTabChange}
        items={[
          {
            key:      'summary',
            label:    'Dashboard',
            children: openedTabs.has('summary') ? <SummaryTabContent /> : null,
          },
          {
            key:      'rf',
            label:    'RF 巡檢',
            children: openedTabs.has('rf') ? <FloorInspectionListTab sheetKey="rf" /> : null,
          },
          {
            key:      'b4f',
            label:    'B4F 巡檢',
            children: openedTabs.has('b4f') ? <FloorInspectionListTab sheetKey="b4f" /> : null,
          },
          {
            key:      'b2f',
            label:    'B2F 巡檢',
            children: openedTabs.has('b2f') ? <FloorInspectionListTab sheetKey="b2f" /> : null,
          },
          {
            key:      'b1f',
            label:    'B1F 巡檢',
            children: openedTabs.has('b1f') ? <FloorInspectionListTab sheetKey="b1f" /> : null,
          },
        ]}
      />
    </div>
  )
}
