/**
 * 整棟巡檢 — 模組統計 Dashboard
 *
 * 對齊 portal 現有「保全巡檢統計 Dashboard」(SecurityDashboard) 的頁面規格：
 *   - 全體 KPI 卡片（4 個）
 *   - 各 Sheet 今日統計表
 *   - Tabs：今日統計 / 異常清單 / 趨勢分析
 *
 * 資料來源：尚未建立本地同步，各欄位顯示空狀態，保留結構供日後擴充。
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Tabs, Alert, DatePicker, Badge,
  message, Progress,
} from 'antd'
import {
  HomeOutlined, SyncOutlined, ReloadOutlined,
  WarningOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  DashboardOutlined, RightOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import {
  FULL_BUILDING_INSPECTION_SHEET_LIST,
  type FullBuildingInspectionSheet,
} from '@/constants/fullBuildingInspection'

const { Title, Text } = Typography

// ── 型別（日後接 API 時替換為正式型別）────────────────────────────────────────

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

// ── 主元件 ────────────────────────────────────────────────────────────────────

export default function FullBuildingInspectionDashboard() {
  const navigate = useNavigate()
  const [activeTab,   setActiveTab]   = useState('summary')
  const [targetDate,  setTargetDate]  = useState<string>(dayjs().format('YYYY/MM/DD'))
  const [loading,     setLoading]     = useState(false)
  const [syncing,     setSyncing]     = useState(false)

  // 以現有 sheet 清單組出初始統計列（全為 0，日後接 API 填入）
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

  // ── 全體 KPI 計算 ──────────────────────────────────────────────────────────

  const totalBatches  = sheets.reduce((s, r) => s + r.total_batches,   0)
  const checkedAll    = sheets.reduce((s, r) => s + r.checked_items,   0)
  const totalAll      = sheets.reduce((s, r) => s + r.total_items,     0)
  const abnormalAll   = sheets.reduce((s, r) => s + r.abnormal_items + r.pending_items, 0)
  const rateAll       = totalAll > 0 ? Math.round(checkedAll / totalAll * 100) : 0

  // ── 各 Sheet 表格欄位 ──────────────────────────────────────────────────────

  const sheetCols = [
    {
      title: '巡檢樓層',
      dataIndex: 'title',
      ellipsis: true,
      render: (v: string, row: SheetStats) => (
        <Button
          type="link"
          style={{ padding: 0, textAlign: 'left' }}
          onClick={() => navigate(`/full-building-inspection/${row.key}`)}
        >
          {v}
        </Button>
      ),
    },
    {
      title: '場次',
      dataIndex: 'total_batches',
      width: 60,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? (
          <Badge count={v} color="#1B3A5C" showZero />
        ) : (
          <Text type="secondary">—</Text>
        ),
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
        v > 0 ? (
          <Badge count={v} color="#FF4D4F" />
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: '待處理',
      dataIndex: 'pending_items',
      width: 65,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? (
          <Badge count={v} color="#FAAD14" />
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: '未巡檢',
      dataIndex: 'unchecked_items',
      width: 65,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? (
          <Badge count={v} color="#999" />
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: '操作',
      width: 80,
      render: (_: unknown, row: SheetStats) => (
        <Button
          type="primary"
          size="small"
          icon={<RightOutlined />}
          style={{ background: '#1B3A5C' }}
          onClick={() => navigate(`/full-building-inspection/${row.key}`)}
        >
          詳情
        </Button>
      ),
    },
  ]

  // ── 今日統計 Tab ───────────────────────────────────────────────────────────

  const SummaryTab = (
    <div>
      <Row style={{ marginBottom: 16 }} align="middle" gutter={8}>
        <Col>
          <Text strong>查詢日期：</Text>
        </Col>
        <Col>
          <DatePicker
            value={dayjs(targetDate, 'YYYY/MM/DD')}
            format="YYYY/MM/DD"
            allowClear={false}
            onChange={(d) => { if (d) setTargetDate(d.format('YYYY/MM/DD')) }}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadSummary} loading={loading}>
            重新整理
          </Button>
        </Col>
      </Row>

      {/* 全體 KPI */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {[
          {
            title: '今日巡檢場次',
            value: totalBatches,
            color: '#1B3A5C',
            icon: <DashboardOutlined />,
          },
          {
            title: '已巡檢項目',
            value: checkedAll,
            suffix: `/${totalAll}`,
            color: '#4BA8E8',
            icon: <CheckCircleOutlined />,
          },
          {
            title: '異常 + 待處理',
            value: abnormalAll,
            color: '#FF4D4F',
            icon: <WarningOutlined />,
          },
          {
            title: '整體完成率',
            value: rateAll,
            suffix: '%',
            color: rateAll >= 80 ? '#52C41A' : '#FAAD14',
            icon: <ExclamationCircleOutlined />,
          },
        ].map((card) => (
          <Col xs={12} sm={12} lg={6} key={card.title}>
            <Card size="small" hoverable>
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

  // ── 異常清單 Tab ───────────────────────────────────────────────────────────

  const IssuesTab = (
    <div>
      <Alert message="今日無異常記錄（尚未同步資料）" type="success" showIcon />
    </div>
  )

  // ── 趨勢 Tab ───────────────────────────────────────────────────────────────

  const TrendTab = (
    <Card title="近 7 日趨勢" size="small">
      <div style={{ textAlign: 'center', padding: '60px 0', color: '#999' }}>
        暫無趨勢資料（請先確認資料已同步）
      </div>
    </Card>
  )

  // ── 頁面渲染 ───────────────────────────────────────────────────────────────

  return (
    <div style={{ padding: '0 4px' }}>
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <HomeOutlined /> },
          { title: NAV_GROUP.full_building_inspection },
          { title: NAV_PAGE.fullBuildingDashboard },
        ]}
      />

      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
            <DashboardOutlined /> {NAV_PAGE.fullBuildingDashboard}
          </Title>
        </Col>
        <Col>
          <Space>
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

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          { key: 'summary', label: '今日統計', children: SummaryTab },
          { key: 'issues',  label: '異常清單', children: IssuesTab },
          { key: 'trend',   label: '趨勢分析', children: TrendTab },
        ]}
      />
    </div>
  )
}
