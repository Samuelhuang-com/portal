/**
 * 整棟巡檢 — 共用樓層巡檢頁元件
 *
 * 對齊 portal 現有「整棟工務巡檢（B1F/B2F/RF）」的頁面規格：
 *   Tab 1「主管儀表板」：KPI 卡 + 巡檢進度 + 趨勢 + 異常/待處理清單
 *   Tab 2「巡檢紀錄」：月份篩選 + 場次清單
 *
 * 資料來源：尚未建立本地同步，各欄位顯示空狀態（等待日後加入 sync service）
 */
import { useState, useCallback, useEffect } from 'react'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Tabs, Progress, Alert,
  message, Badge, DatePicker,
} from 'antd'
import {
  HomeOutlined, SyncOutlined, ReloadOutlined,
  WarningOutlined, CheckCircleOutlined, ClockCircleOutlined,
  ExclamationCircleOutlined, SafetyOutlined, BarChartOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import { FULL_BUILDING_INSPECTION_SHEETS } from '@/constants/fullBuildingInspection'

const { Title, Text } = Typography

// ── Props ─────────────────────────────────────────────────────────────────────

interface InspectionFloorPageProps {
  sheetKey: string
}

// ── 型別（日後接 API 時替換為正式型別）────────────────────────────────────────

interface BatchRow {
  id: string
  inspection_date: string
  inspector_name:  string
  completion_rate: number
  total:    number
  checked:  number
  abnormal: number
  pending:  number
}

// ── 主元件 ────────────────────────────────────────────────────────────────────

export default function InspectionFloorPage({ sheetKey }: InspectionFloorPageProps) {
  const sheet       = FULL_BUILDING_INSPECTION_SHEETS[sheetKey]
  const [activeTab, setActiveTab]   = useState('dashboard')
  const [yearMonth, setYearMonth]   = useState<string>(dayjs().format('YYYY/MM'))
  const [loading,   setLoading]     = useState(false)
  const [syncing,   setSyncing]     = useState(false)
  const [batches,   setBatches]     = useState<BatchRow[]>([])

  // 防呆：找不到設定
  if (!sheet) {
    return (
      <Alert
        type="error"
        message="頁面設定錯誤"
        description={`找不到 sheetKey="${sheetKey}" 的巡檢設定，請確認路由是否正確。`}
        style={{ margin: 24 }}
        showIcon
      />
    )
  }

  // 對應的 nav label
  const NAV_KEY_MAP: Record<string, keyof typeof NAV_PAGE> = {
    'rf':  'fullBuildingRF',
    'b4f': 'fullBuildingB4F',
    'b2f': 'fullBuildingB2F',
    'b1f': 'fullBuildingB1F',
  }
  const navPageKey = NAV_KEY_MAP[sheetKey]
  const pageLabel  = navPageKey ? NAV_PAGE[navPageKey] : sheet.title

  // ── 資料載入（目前尚無 sync，保留結構供日後接 API）─────────────────────────

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    // TODO: 接 API → fetchFullBuildingStats(sheetKey)
    await new Promise((r) => setTimeout(r, 100))
    setLoading(false)
  }, [sheetKey])

  const loadBatches = useCallback(async () => {
    setLoading(true)
    // TODO: 接 API → fetchFullBuildingBatches(sheetKey, { year_month: yearMonth })
    await new Promise((r) => setTimeout(r, 100))
    setBatches([])
    setLoading(false)
  }, [sheetKey, yearMonth])

  useEffect(() => { loadDashboard() }, [loadDashboard])
  useEffect(() => {
    if (activeTab === 'list') loadBatches()
  }, [activeTab, loadBatches])

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

  // ── Tab 1：主管儀表板 ──────────────────────────────────────────────────────

  const DashboardTab = (
    <div>
      {/* KPI 卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        {[
          {
            title: '已巡檢（本次）',
            value: 0,
            suffix: '/ 0 項',
            icon: <SafetyOutlined />,
            color: '#1B3A5C',
          },
          {
            title: '正常（— %）',
            value: 0,
            suffix: '項',
            icon: <CheckCircleOutlined />,
            color: '#52C41A',
          },
          {
            title: '異常',
            value: 0,
            suffix: '項',
            icon: <WarningOutlined />,
            color: '#FF4D4F',
          },
          {
            title: '待處理',
            value: 0,
            suffix: '項',
            icon: <ExclamationCircleOutlined />,
            color: '#FAAD14',
          },
        ].map((card) => (
          <Col xs={24} sm={12} lg={6} key={card.title}>
            <Card size="small" hoverable loading={loading}>
              <Statistic
                title={card.title}
                value={card.value}
                suffix={card.suffix}
                prefix={<span style={{ color: card.color }}>{card.icon}</span>}
                valueStyle={{ color: card.color, fontSize: 28 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* 巡檢完成率進度條 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row align="middle" gutter={16}>
          <Col flex="100px"><Text strong>巡檢完成率</Text></Col>
          <Col flex="auto">
            <Progress
              percent={0}
              strokeColor={{ from: '#FAAD14', to: '#52C41A' }}
              format={() => '0%（0 / 0）'}
            />
          </Col>
          <Col flex="100px">
            <Text type="secondary">近 7 日：— 次</Text>
          </Col>
        </Row>
      </Card>

      {/* 異常 / 待處理清單 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card
            title={<><WarningOutlined style={{ color: '#FF4D4F' }} /> 本次異常項目</>}
            size="small"
          >
            <Alert message="本次巡檢無異常紀錄（尚未同步資料）" type="info" showIcon />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={<><ClockCircleOutlined style={{ color: '#FAAD14' }} /> 待處理項目</>}
            size="small"
          >
            <Alert message="目前無待處理項目（尚未同步資料）" type="info" showIcon />
          </Card>
        </Col>
      </Row>

      {/* 近 7 日趨勢（預留） */}
      <Card
        title={<><BarChartOutlined /> 近 7 日異常趨勢</>}
        size="small"
        style={{ marginTop: 16, height: 200 }}
      >
        <div style={{ textAlign: 'center', paddingTop: 50, color: '#999' }}>
          尚無趨勢資料（請先執行資料同步）
        </div>
      </Card>
    </div>
  )

  // ── Tab 2：巡檢紀錄 ────────────────────────────────────────────────────────

  const batchColumns = [
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
        if (row.abnormal > 0) return <Tag color="#FF4D4F">有異常</Tag>
        if (row.pending > 0)  return <Tag color="#FAAD14">待處理</Tag>
        if (row.checked >= row.total && row.total > 0)
          return <Tag color="#52C41A">已完成</Tag>
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
        v > 0 ? (
          <Badge count={v} color="#FF4D4F" />
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: '待處理',
      dataIndex: 'pending',
      width: 65,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? (
          <Badge count={v} color="#FAAD14" />
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
  ]

  const ListTab = (
    <div>
      <Row gutter={8} style={{ marginBottom: 16 }}>
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
          <Button
            icon={<ReloadOutlined />}
            onClick={loadBatches}
            loading={loading}
          >
            重新整理
          </Button>
        </Col>
      </Row>
      <Table<BatchRow>
        dataSource={batches}
        rowKey="id"
        columns={batchColumns}
        loading={loading}
        size="middle"
        pagination={{ pageSize: 30, showTotal: (t) => `共 ${t} 筆` }}
        locale={{ emptyText: '尚無巡檢紀錄（請先執行資料同步）' }}
      />
    </div>
  )

  // ── 頁面渲染 ──────────────────────────────────────────────────────────────

  return (
    <div style={{ padding: '0 4px' }}>
      {/* Breadcrumb */}
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <HomeOutlined /> },
          { title: NAV_GROUP.full_building_inspection },
          { title: pageLabel },
        ]}
      />

      {/* 標題列 */}
      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
            <SafetyOutlined /> {pageLabel}
          </Title>
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

      {/* Tabs */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          { key: 'dashboard', label: '主管儀表板', children: DashboardTab },
          { key: 'list',      label: '巡檢紀錄',   children: ListTab },
        ]}
      />
    </div>
  )
}
