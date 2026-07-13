/**
 * 週期採購 — Dashboard
 *
 * 2026-07-11（拿掉「批次」後改版）：
 *   - 移除「開放中批次」統計（批次實體已拿掉，見 cycle_purchase_request.py
 *     開頭說明）。
 *   - 新增「待辦提醒」：登入者自己部門（依 CpDepartment.owner_user_id 判斷）
 *     還沒填/被退回要改的請購單，以及（若有簽核權限）全部待簽核的請購單。
 *     第一版先只做這裡的 Dashboard 卡片，之後若要加 email 通知另外規劃。
 *
 * 完整 KPI／彙整／採購／驗收／請款等流程留待後續階段（見規劃報告第八節）。
 */
import { useEffect, useState } from 'react'
import { Alert, Badge, Card, Col, Empty, List, Row, Statistic, Tag, Typography } from 'antd'
import {
  ShopOutlined, DatabaseOutlined, CalendarOutlined, ClockCircleOutlined, AuditOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { getCycles, getItems, getTodos, getVendors } from '@/api/cyclePurchase'
import type { CpRequest, TodoSummary } from '@/types/cyclePurchase'

const { Title } = Typography

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  draft:     { color: 'default', label: '草稿' },
  submitted: { color: 'blue',    label: '已送出' },
  approved:  { color: 'green',   label: '已核准' },
  rejected:  { color: 'red',     label: '已退回' },
}

export default function CpDashboardPage() {
  const navigate = useNavigate()
  const [counts, setCounts] = useState({
    vendors: 0,
    items: 0,
    activeCycles: 0,
  })
  const [todos, setTodos] = useState<TodoSummary | null>(null)
  const [todosLoading, setTodosLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getVendors({ is_active: true }),
      getItems({ is_active: true, per_page: 1 }),
      getCycles({ status: 'active' }),
    ]).then(([vendorsRes, itemsRes, cyclesRes]) => {
      setCounts({
        vendors: vendorsRes.data.length,
        items: itemsRes.data.total,
        activeCycles: cyclesRes.data.length,
      })
    })
    getTodos()
      .then((r) => setTodos(r.data))
      .finally(() => setTodosLoading(false))
  }, [])

  const renderRequestItem = (r: CpRequest) => (
    <List.Item onClick={() => navigate(`/cycle-purchase/requests/${r.id}`)} style={{ cursor: 'pointer' }}>
      <List.Item.Meta
        title={
          <span>
            {r.request_no}
            <Tag color={STATUS_TAG[r.status]?.color} style={{ marginLeft: 8 }}>
              {STATUS_TAG[r.status]?.label || r.status}
            </Tag>
          </span>
        }
        description={`${r.cycle_name || ''}／${r.period_label}　${r.company} - ${r.department_name}`}
      />
    </List.Item>
  )

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>週採（週期採購管理）</Title>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="上線範圍"
        description="目前已提供：基礎設定（供應商／部門／成本中心／會計科目主檔）、料號主檔與料號對照表、週期設定、請購單（含產生本期請購單、填寫、送出、簽核）。彙整單／採購單／驗收單／請款單等流程在後續階段陸續開放，詳見規劃評估報告第八節分期計畫。"
      />

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic title="啟用中供應商" value={counts.vendors} prefix={<ShopOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="啟用中料號" value={counts.items} prefix={<DatabaseOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="啟用中週期" value={counts.activeCycles} prefix={<CalendarOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card
            size="small"
            title={
              <span>
                <ClockCircleOutlined style={{ marginRight: 8 }} />
                我的待辦（我部門待填／被退回）
              </span>
            }
            loading={todosLoading}
          >
            {todos && todos.my_pending.length > 0 ? (
              <List dataSource={todos.my_pending} renderItem={renderRequestItem} size="small" />
            ) : (
              <Empty
                description={
                  todos ? '目前沒有待填的請購單' : ''
                }
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card
            size="small"
            title={
              <span>
                <AuditOutlined style={{ marginRight: 8 }} />
                待簽核
                {todos && todos.pending_approval_count > 0 && (
                  <Badge count={todos.pending_approval_count} style={{ marginLeft: 8 }} />
                )}
              </span>
            }
            loading={todosLoading}
          >
            {todos && todos.pending_approval.length > 0 ? (
              <List dataSource={todos.pending_approval} renderItem={renderRequestItem} size="small" />
            ) : (
              <Empty
                description={todos ? '目前沒有待簽核的請購單（或您沒有簽核權限）' : ''}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
