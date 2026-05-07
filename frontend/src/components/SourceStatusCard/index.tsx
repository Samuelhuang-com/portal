import React from 'react'
import { Card, Row, Col, Space, Button, Progress, Statistic, Alert, Tooltip, Typography } from 'antd'
import { RightOutlined } from '@ant-design/icons'

const { Text } = Typography

const GREEN  = '#52C41A'
const ORANGE = '#FA8C16'
const RED    = '#FF4D4F'

// ── fmtHours：與 HotelMgmtDashboard 相同邏輯 ──────────────────────────────
const fmtHours = (h: number) =>
  h < 0 ? '—' : h < 100 ? `${h.toFixed(1)} HR` : `${Math.round(h)} HR`

// ─────────────────────────────────────────────────────────────────────────────
// Props 介面（依 T16 規格）
// ─────────────────────────────────────────────────────────────────────────────
export interface SourceStatusCardProps {
  source_key:      string
  source_name:     string
  source_color:    string
  case_count:      number       // -1 = 不適用（不顯示統計欄位）
  completed_count: number
  work_hours:      number       // -1 = 不適用
  actual_hours?:   number       // 有值 → 顯示 PM「預估工時 / 保養時間」雙行
  completion_rate: number       // -1 = 不適用（不顯示進度條）
  abnormal_count:  number
  overdue_count:   number
  status_label:    string       // 狀態摘要文字（保留供父層使用，卡片內未直接渲染）
  is_placeholder?: boolean      // true → 顯示「數據準備中」佔位
  loading?:        boolean
  error?:          string | null
  onClick?:        () => void   // 點擊「詳情」按鈕的動作
  // ── 選用外觀控制（不影響資訊內容）────────────────────────────────────────
  icon?:           React.ReactNode   // 標題列 icon
  cardSize?:       'default' | 'small'  // 對應 Ant Design Card size prop
  titleFontSize?:  number            // 標題字型大小（預設 14）
  statFontSize?:   number            // Statistic 數值字型大小（預設 20）
  infoFontSize?:   number            // 資訊列字型大小（預設 15）
  footer?:         React.ReactNode  // 卡片底部追加內容（如費用摘要）
}

// ─────────────────────────────────────────────────────────────────────────────
// 主元件
// ─────────────────────────────────────────────────────────────────────────────
export function SourceStatusCard({
  source_key,
  source_name,
  source_color,
  case_count,
  completed_count,
  work_hours,
  actual_hours,
  completion_rate,
  abnormal_count,
  overdue_count,
  is_placeholder = false,
  loading = false,
  error,
  onClick,
  icon,
  cardSize       = 'default',
  titleFontSize  = 14,
  statFontSize   = 20,
  infoFontSize   = 15,
  footer,
}: SourceStatusCardProps) {
  const color       = source_color
  const showStats   = !is_placeholder && !loading && !error
  // 'dazhi'（飯店工務部）以「未完成」取代「異常」
  const abnormalLabel = source_key === 'dazhi' ? '未完成：' : '異常：'

  return (
    <Card
      size={cardSize}
      title={
        <Space>
          {icon && <span style={{ color }}>{icon}</span>}
          <Text strong style={{ color, fontSize: titleFontSize }}>{source_name}</Text>
        </Space>
      }
      extra={
        <Button
          type="link"
          size="small"
          icon={<RightOutlined />}
          style={{ color }}
          disabled={!onClick}
          onClick={onClick}
        >
          詳情
        </Button>
      }
      style={{ borderTop: `3px solid ${color}`, height: '100%' }}
      loading={loading}
    >
      {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 8 }} />}

      {(is_placeholder || case_count < 0) && !loading && !error && (
        <div style={{ textAlign: 'center', color: '#bbb', padding: '20px 0', fontSize: titleFontSize }}>
          數據準備中
        </div>
      )}

      {showStats && case_count >= 0 && (
        <>
          <Row gutter={[8, 8]}>
            <Col span={12}>
              <Statistic
                title={<Text style={{ fontSize: titleFontSize, color: '#888' }}>工項/案件數</Text>}
                value={case_count}
                suffix="筆"
                valueStyle={{ fontSize: statFontSize, color }}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title={<Text style={{ fontSize: titleFontSize, color: '#888' }}>已完成</Text>}
                value={completed_count}
                suffix="筆"
                valueStyle={{ fontSize: statFontSize, color: GREEN }}
              />
            </Col>
          </Row>

          {completion_rate >= 0 && (
            <div style={{ marginTop: 10 }}>
              <Progress
                percent={Math.round(completion_rate)}
                size="small"
                strokeColor={{ from: completion_rate < 50 ? RED : ORANGE, to: GREEN }}
                format={(p) => `完成率 ${p}%`}
              />
            </div>
          )}

          <Row gutter={[8, 0]} style={{ marginTop: 8 }}>
            {abnormal_count > 0 && (
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: infoFontSize }}>{abnormalLabel}</Text>
                <Text style={{ fontSize: infoFontSize, color: RED, fontWeight: 600 }}>{abnormal_count}</Text>
              </Col>
            )}
            {overdue_count > 0 && (
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: infoFontSize }}>逾期：</Text>
                <Text style={{ fontSize: infoFontSize, color: '#C0392B', fontWeight: 600 }}>{overdue_count}</Text>
              </Col>
            )}

            {/* PM 來源：actual_hours 存在 → 雙行（預估工時 + 保養時間） */}
            {actual_hours !== undefined ? (
              <>
                <Col span={12}>
                  <Tooltip title="計劃工時（planned_minutes / 60），來自週期保養排程">
                    <Text type="secondary" style={{ fontSize: infoFontSize - 1, cursor: 'help' }}>預估工時：</Text>
                  </Tooltip>
                  <Text style={{ fontSize: infoFontSize, color: '#4BA8E8', fontWeight: 600 }}>
                    {work_hours > 0 ? `${work_hours.toFixed(1)} HR` : '0'}
                  </Text>
                </Col>
                <Col span={12}>
                  <Tooltip title="實際完成工時（actual_minutes / 60）；後端計算完成後自動顯示">
                    <Text type="secondary" style={{ fontSize: infoFontSize - 1, cursor: 'help' }}>保養時間：</Text>
                  </Tooltip>
                  <Text style={{ fontSize: infoFontSize, color: GREEN, fontWeight: 600 }}>
                    {actual_hours > 0 ? `${actual_hours.toFixed(1)} HR` : '—'}
                  </Text>
                </Col>
              </>
            ) : (
              work_hours > 0 && (
                <Col span={12}>
                  <Text type="secondary" style={{ fontSize: infoFontSize }}>工時：</Text>
                  <Text style={{ fontSize: infoFontSize, color, fontWeight: 600 }}>
                    {fmtHours(work_hours)}
                  </Text>
                </Col>
              )
            )}
          </Row>
        </>
      )}
      {footer && <>{footer}</>}
    </Card>
  )
}
