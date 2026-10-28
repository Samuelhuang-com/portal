/**
 * 整棟巡檢 — 共用樓層巡檢頁元件（/full-building-inspection/rf|b4f|b2f|b1f 四條獨立路由）
 *
 *   Tab 1「主管儀表板」：最新場次 KPI + 完成率 + 異常/待處理清單 + 近 7 日異常趨勢
 *   Tab 2「巡檢紀錄」  ：月份篩選 + 場次清單 + 明細 Drawer（共用 FloorInspectionList）
 *
 * 資料來源：GET /mall/{key}-inspection/stats
 * ⚠️ prefix 是 /mall/ 不是 /full-building-inspection/，見 api/fullBuildingInspection.ts
 *
 * ⚠️ 清單與明細 Drawer 一律用 FloorInspectionList，不要在這裡重刻一份 ——
 *    Dashboard 頁（index.tsx）的四個 Tab 用的是同一支。
 */
import { useState, useCallback, useEffect } from 'react'
import {
  Row, Col, Card, Statistic, Tag, Typography, Breadcrumb, Tabs,
  Progress, Alert, List, Empty, Tooltip,
} from 'antd'
import {
  HomeOutlined, WarningOutlined, CheckCircleOutlined, ClockCircleOutlined,
  ExclamationCircleOutlined, SafetyOutlined, BarChartOutlined, LinkOutlined,
} from '@ant-design/icons'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import { FULL_BUILDING_INSPECTION_SHEETS } from '@/constants/fullBuildingInspection'
import { fetchFloorStats, type FloorStats } from '@/api/fullBuildingInspection'
import FloorInspectionList from './FloorInspectionList'

const { Title, Text } = Typography

// ── Props ─────────────────────────────────────────────────────────────────────

interface InspectionFloorPageProps {
  sheetKey: string
}

// ── 主元件 ────────────────────────────────────────────────────────────────────

export default function InspectionFloorPage({ sheetKey }: InspectionFloorPageProps) {
  const sheet = FULL_BUILDING_INSPECTION_SHEETS[sheetKey]
  const [activeTab, setActiveTab] = useState('dashboard')
  const [loading,   setLoading]   = useState(false)
  const [stats,     setStats]     = useState<FloorStats | null>(null)
  const [error,     setError]     = useState<string | null>(null)

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

  // ── 資料載入 ───────────────────────────────────────────────────────────────

  const loadStats = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setStats(await fetchFloorStats(sheetKey))
    } catch (e) {
      setStats(null)
      setError(e instanceof Error ? e.message : '載入統計失敗')
    } finally {
      setLoading(false)
    }
  }, [sheetKey])

  useEffect(() => { loadStats() }, [loadStats])

  // ⚠️ 該樓層一筆資料都沒有時，後端回的 latest_batch / latest_kpi 是 null，
  //    不可直接 stats.latest_kpi.total，一律走這個有預設值的物件。
  const kpi = stats?.latest_kpi ?? {
    total: 0, normal: 0, abnormal: 0, pending: 0,
    unchecked: 0, measure: 0, completion_rate: 0, normal_rate: 0,
  }
  const checked   = kpi.total - kpi.unchecked
  const hasData   = !!stats?.latest_batch
  const trend     = stats?.abnormal_trend ?? []
  const trendMax  = Math.max(1, ...trend.map((t) => t.abnormal_count))

  const ragicRecordUrl = (ragicId: string) =>
    `${sheet.ragicUrl.split('?')[0]}/${ragicId}`

  // ── Tab 1：主管儀表板 ──────────────────────────────────────────────────────

  const DashboardTab = (
    <div>
      {error && (
        <Alert type="error" message={error} style={{ marginBottom: 16 }}
               closable onClose={() => setError(null)} />
      )}

      {/* 最新場次資訊 */}
      {hasData && stats?.latest_batch && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row align="middle" gutter={16}>
            <Col>
              <Text type="secondary">最新場次</Text>
            </Col>
            <Col>
              <Text strong style={{ fontSize: 16 }}>
                {stats.latest_batch.inspection_date || '—'}
              </Text>
            </Col>
            <Col>
              <Text type="secondary">巡檢人員</Text>{' '}
              <Text>{stats.latest_batch.inspector_name || '—'}</Text>
            </Col>
            <Col>
              <Text type="secondary">工時</Text>{' '}
              <Text>{stats.latest_batch.work_hours || '—'}</Text>
            </Col>
            <Col flex="auto" style={{ textAlign: 'right' }}>
              <a
                href={ragicRecordUrl(stats.latest_batch.ragic_id)}
                target="_blank"
                rel="noreferrer"
                style={{ color: '#4BA8E8', fontSize: 12 }}
              >
                <LinkOutlined /> 在 Ragic 查看
              </a>
            </Col>
          </Row>
        </Card>
      )}

      {/* KPI 卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        {[
          {
            title: '已巡檢（本次）',
            value: checked,
            suffix: `/ ${kpi.total} 項`,
            icon: <SafetyOutlined />,
            color: '#1B3A5C',
          },
          {
            title: `正常（${hasData ? kpi.normal_rate : '—'} %）`,
            value: kpi.normal,
            suffix: '項',
            icon: <CheckCircleOutlined />,
            color: '#52C41A',
          },
          {
            title: '異常',
            value: kpi.abnormal,
            suffix: '項',
            icon: <WarningOutlined />,
            color: '#FF4D4F',
          },
          {
            title: '待處理',
            value: kpi.pending,
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
      <Card size="small" style={{ marginBottom: 16 }} loading={loading}>
        <Row align="middle" gutter={16}>
          <Col flex="100px"><Text strong>巡檢完成率</Text></Col>
          <Col flex="auto">
            <Progress
              percent={kpi.completion_rate}
              strokeColor={{ from: '#FAAD14', to: '#52C41A' }}
              format={() => `${kpi.completion_rate}%（${checked} / ${kpi.total}）`}
            />
          </Col>
          <Col flex="120px" style={{ textAlign: 'right' }}>
            <Text type="secondary">近 7 日：{stats?.total_batches_7d ?? 0} 次</Text>
          </Col>
        </Row>
      </Card>

      {/* 異常 / 待處理清單 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card
            title={<><WarningOutlined style={{ color: '#FF4D4F' }} /> 本次異常項目</>}
            size="small"
            loading={loading}
          >
            {stats && stats.recent_abnormal.length > 0 ? (
              <List
                size="small"
                dataSource={stats.recent_abnormal}
                renderItem={(it) => (
                  <List.Item>
                    <Text>{it.item_name}</Text>
                    <Tag color={it.result_status === 'abnormal' ? '#FF4D4F' : '#FAAD14'}>
                      {it.result_raw || (it.result_status === 'abnormal' ? '異常' : '待處理')}
                    </Tag>
                  </List.Item>
                )}
              />
            ) : (
              <Alert
                message={hasData ? '本次巡檢無異常紀錄' : '尚無巡檢資料'}
                type="info"
                showIcon
              />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={<><ClockCircleOutlined style={{ color: '#FAAD14' }} /> 待處理項目</>}
            size="small"
            loading={loading}
          >
            {stats && stats.recent_pending.length > 0 ? (
              <List
                size="small"
                dataSource={stats.recent_pending}
                renderItem={(it) => (
                  <List.Item>
                    <Text>{it.item_name}</Text>
                    <Tag color="#FAAD14">{it.result_raw || '待處理'}</Tag>
                  </List.Item>
                )}
              />
            ) : (
              <Alert
                message={hasData ? '目前無待處理項目' : '尚無巡檢資料'}
                type="info"
                showIcon
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* 近 7 日異常趨勢 */}
      <Card
        title={<><BarChartOutlined /> 近 7 日異常趨勢</>}
        size="small"
        style={{ marginTop: 16 }}
        loading={loading}
      >
        {trend.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚無趨勢資料" />
        ) : (
          <Row gutter={8} align="bottom" style={{ height: 140 }}>
            {trend.map((t) => (
              <Col flex="1" key={t.date} style={{ textAlign: 'center' }}>
                <Tooltip
                  title={`${t.date}｜${t.has_record ? `異常/待處理 ${t.abnormal_count} 項` : '未登錄'}`}
                >
                  <div style={{ height: 100, display: 'flex', alignItems: 'flex-end',
                                justifyContent: 'center' }}>
                    <div
                      style={{
                        width: '60%',
                        // 沒登錄用灰色細條表示「沒資料」，與「有登錄但 0 異常」區分開
                        height: t.has_record
                          ? Math.max(4, (t.abnormal_count / trendMax) * 100)
                          : 4,
                        background: !t.has_record
                          ? '#e8e8e8'
                          : t.abnormal_count > 0 ? '#FF4D4F' : '#52C41A',
                        borderRadius: 2,
                      }}
                    />
                  </div>
                </Tooltip>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {t.date.slice(5)}
                </Text>
              </Col>
            ))}
          </Row>
        )}
      </Card>
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
      </Row>

      {/* Tabs */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          { key: 'dashboard', label: '主管儀表板', children: DashboardTab },
          {
            key:      'list',
            label:    '巡檢紀錄',
            children: <FloorInspectionList sheetKey={sheetKey} />,
          },
        ]}
      />
    </div>
  )
}
