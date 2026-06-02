/**
 * G2 — 合約行事曆視圖
 *
 * 以月曆顯示三種事件：
 *   🔴 合約到期日（end_date）
 *   🔵 請款日期（claim_date）
 *   🟢 已核准續約截止日（renewal_end_date）
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  Card, Badge, Calendar, Row, Col, List, Tag, Typography, Breadcrumb,
  Space, Spin, Empty, message, Tooltip,
} from 'antd'
import { HomeOutlined, CalendarOutlined, FileProtectOutlined,
  DollarOutlined, SyncOutlined } from '@ant-design/icons'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useNavigate } from 'react-router-dom'

import apiClient from '@/api/client'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Title, Text } = Typography

// ── 型別 ──────────────────────────────────────────────────────────────────

interface CalendarEvent {
  date: string
  type: 'expiry' | 'claim' | 'renewal'
  color: string
  label: string
  contract_id: string
  contract_name?: string
  claim_id?: number
  amount?: number
  status?: string
  renewal_id?: number
}

const TYPE_CONFIG = {
  expiry:  { icon: <FileProtectOutlined />, label: '合約到期', color: '#FF4D4F', badgeColor: 'error'   as const },
  claim:   { icon: <DollarOutlined />,      label: '請款',     color: '#4BA8E8', badgeColor: 'processing' as const },
  renewal: { icon: <SyncOutlined />,        label: '續約截止', color: '#52C41A', badgeColor: 'success' as const },
}

async function fetchCalendarEvents(year: number, month: number): Promise<CalendarEvent[]> {
  const { data } = await apiClient.get('/contract/calendar-events', {
    params: { year, month },
  })
  return (data.events as CalendarEvent[]) || []
}

// ── 主元件 ────────────────────────────────────────────────────────────────

export default function ContractCalendarView() {
  const navigate = useNavigate()
  const [currentMonth, setCurrentMonth] = useState<Dayjs>(dayjs())
  const [events, setEvents]             = useState<CalendarEvent[]>([])
  const [loading, setLoading]           = useState(false)
  const [selectedDate, setSelectedDate] = useState<string>(dayjs().format('YYYY-MM-DD'))

  const loadEvents = useCallback(async (d: Dayjs) => {
    setLoading(true)
    try {
      const list = await fetchCalendarEvents(d.year(), d.month() + 1)
      setEvents(list)
    } catch {
      message.error('無法載入行事曆事件')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadEvents(currentMonth) }, [currentMonth, loadEvents])

  // 某日的事件
  const eventsOnDate = (date: string) => events.filter(e => e.date === date)
  const selectedEvents = eventsOnDate(selectedDate)

  // Calendar 的 dateCellRender
  const dateCellRender = (value: Dayjs) => {
    const dateStr = value.format('YYYY-MM-DD')
    const dayEvents = eventsOnDate(dateStr)
    if (!dayEvents.length) return null
    return (
      <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
        {dayEvents.slice(0, 3).map((ev, i) => (
          <li key={i}>
            <Badge color={ev.color} text={
              <span style={{ fontSize: 10, color: '#333' }}>
                {ev.label.length > 12 ? ev.label.slice(0, 12) + '…' : ev.label}
              </span>
            } />
          </li>
        ))}
        {dayEvents.length > 3 && (
          <li style={{ fontSize: 10, color: '#8c8c8c' }}>+ {dayEvents.length - 3} 筆</li>
        )}
      </ul>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <Breadcrumb style={{ marginBottom: 16 }}>
        <Breadcrumb.Item><HomeOutlined /></Breadcrumb.Item>
        <Breadcrumb.Item>{NAV_GROUP.contract}</Breadcrumb.Item>
        <Breadcrumb.Item><CalendarOutlined /> 合約行事曆</Breadcrumb.Item>
      </Breadcrumb>

      {/* 圖例 */}
      <Card style={{ marginBottom: 16 }} size="small">
        <Space size={24}>
          {Object.entries(TYPE_CONFIG).map(([key, cfg]) => (
            <Space key={key} size={6}>
              <Badge color={cfg.color} />
              <Text style={{ fontSize: 13 }}>{cfg.label}</Text>
            </Space>
          ))}
          <Text type="secondary" style={{ fontSize: 12 }}>
            點擊日期查看當日事件詳情
          </Text>
        </Space>
      </Card>

      <Row gutter={16}>
        {/* ── 月曆主體 ── */}
        <Col xs={24} lg={17}>
          <Card>
            <Spin spinning={loading}>
              <Calendar
                value={currentMonth}
                onPanelChange={(value) => {
                  setCurrentMonth(value)
                  setSelectedDate(value.format('YYYY-MM-DD'))
                }}
                onSelect={(value) => {
                  setSelectedDate(value.format('YYYY-MM-DD'))
                }}
                dateCellRender={dateCellRender}
              />
            </Spin>
          </Card>
        </Col>

        {/* ── 側邊事件清單 ── */}
        <Col xs={24} lg={7}>
          <Card
            title={
              <Space>
                <CalendarOutlined style={{ color: '#4BA8E8' }} />
                <span>{dayjs(selectedDate).format('M 月 D 日')}</span>
                {selectedEvents.length > 0 && (
                  <Badge count={selectedEvents.length} style={{ backgroundColor: '#4BA8E8' }} />
                )}
              </Space>
            }
            size="small"
            style={{ marginBottom: 12 }}
          >
            {selectedEvents.length === 0 ? (
              <Empty description="本日無事件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <List
                dataSource={selectedEvents}
                renderItem={(ev) => {
                  const cfg = TYPE_CONFIG[ev.type]
                  return (
                    <List.Item
                      style={{ padding: '8px 0', cursor: 'pointer' }}
                      onClick={() => navigate(`/contract?search=${ev.contract_id}`)}
                    >
                      <List.Item.Meta
                        avatar={
                          <div style={{
                            width: 32, height: 32, borderRadius: 6,
                            background: cfg.color + '20', display: 'flex',
                            alignItems: 'center', justifyContent: 'center',
                            color: cfg.color, fontSize: 15,
                          }}>
                            {cfg.icon}
                          </div>
                        }
                        title={
                          <Tooltip title={ev.label}>
                            <span style={{ fontSize: 13, fontWeight: 600 }}>
                              {ev.contract_id}
                            </span>
                          </Tooltip>
                        }
                        description={
                          <div>
                            <Tag color={ev.type === 'expiry' ? 'error' : ev.type === 'claim' ? 'processing' : 'success'}
                              style={{ fontSize: 10 }}>
                              {cfg.label}
                            </Tag>
                            {ev.amount != null && (
                              <span style={{ fontSize: 11, color: '#596780' }}>
                                　${ev.amount.toLocaleString('zh-TW')}
                              </span>
                            )}
                            {ev.status && (
                              <span style={{ fontSize: 11, color: '#8c8c8c' }}>　{ev.status}</span>
                            )}
                          </div>
                        }
                      />
                    </List.Item>
                  )
                }}
              />
            )}
          </Card>

          {/* 本月統計 */}
          <Card title="本月統計" size="small">
            {Object.entries(TYPE_CONFIG).map(([key, cfg]) => {
              const count = events.filter(e => e.type === key).length
              return (
                <div key={key} style={{ display: 'flex', justifyContent: 'space-between',
                  alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>
                  <Space size={6}>
                    <Badge color={cfg.color} />
                    <Text style={{ fontSize: 13 }}>{cfg.label}</Text>
                  </Space>
                  <Text strong style={{ color: count > 0 ? cfg.color : '#8c8c8c' }}>
                    {count} 筆
                  </Text>
                </div>
              )
            })}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
