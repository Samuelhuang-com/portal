/**
 * 超級行事曆（Command Calendar）
 * Portal 事件總覽中心 / 跨模組時間軸中心
 *
 * 功能：
 *  - 月 / 週 / 日 / 清單（Agenda）四種視圖
 *  - 今日 KPI 摘要卡片
 *  - 今日重點側邊面板
 *  - 事件類型分層篩選
 *  - 點擊事件開啟詳情抽屜（含深連結）
 *  - 新增自訂事件
 */
import { useEffect, useState, useCallback, useRef } from 'react'
import {
  Row, Col, Card, Statistic, Space, Typography, Breadcrumb,
  Tag, Button, Modal, Form, Input, DatePicker, Select,
  Switch, TimePicker, ColorPicker, message, Spin,
} from 'antd'
import {
  HomeOutlined, CalendarOutlined, PlusOutlined, ReloadOutlined,
  WarningOutlined, ClockCircleOutlined,
  ExclamationCircleOutlined, BellOutlined, EditOutlined, DeleteOutlined,
} from '@ant-design/icons'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin  from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import listPlugin    from '@fullcalendar/list'
import interactionPlugin from '@fullcalendar/interaction'
import type { EventClickArg, DatesSetArg, EventInput } from '@fullcalendar/core'
import dayjs from 'dayjs'

import {
  fetchCalendarEvents,
  fetchCalendarToday,
  createCustomEvent,
  updateCustomEvent,
  deleteCustomEvent,
} from '@/api/calendar'
import type {
  CalendarEvent,
  CalendarTodaySummary,
  CalendarEventType,
  CalendarZone,
} from '@/types/calendar'
import {
  EVENT_TYPE_COLORS,
  EVENT_TYPE_LABELS,
  ZONE_VALUES,
  ZONE_COLORS,
  ZONE_LABELS,
} from '@/types/calendar'
import { NAV_GROUP } from '@/constants/navLabels'
import EventDrawer from './components/EventDrawer'
import TodayPanel  from './components/TodayPanel'

const { Title, Text } = Typography

// ── 可選的事件類型清單 ────────────────────────────────────────────────────────
const ALL_TYPES: CalendarEventType[] = [
  'hotel_pm', 'mall_pm', 'full_pm', 'pm_plan', 'approval', 'memo', 'custom',
]

// ── 將 CalendarEvent 轉換為 FullCalendar EventInput ────────────────────────
function toFCEvent(ev: CalendarEvent): EventInput {
  return {
    id:              ev.id,
    title:           ev.title,
    start:           ev.start,
    end:             ev.end || undefined,
    allDay:          ev.all_day,
    backgroundColor: ev.color,
    borderColor:     ev.color,
    textColor:       '#fff',
    extendedProps:   ev,
  }
}

export default function CalendarPage() {
  // ── State ──────────────────────────────────────────────────────────────────
  const [events,       setEvents]       = useState<CalendarEvent[]>([])
  const [todayEvents,  setTodayEvents]  = useState<CalendarEvent[]>([])
  const [summary,      setSummary]      = useState<CalendarTodaySummary | null>(null)
  const [loading,      setLoading]      = useState(false)
  const [todayLoading, setTodayLoading] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null)
  const [drawerOpen,   setDrawerOpen]   = useState(false)
  const [activeFilters, setActiveFilters] = useState<CalendarEventType[]>(ALL_TYPES)
  const [activeZones,   setActiveZones]   = useState<CalendarZone[]>([...ZONE_VALUES])
  const [addModalOpen,  setAddModalOpen]  = useState(false)
  const [addLoading,    setAddLoading]    = useState(false)
  const [editModalOpen,  setEditModalOpen]  = useState(false)
  const [editLoading,    setEditLoading]    = useState(false)
  const [editingEvent,   setEditingEvent]   = useState<CalendarEvent | null>(null)
  const [dateRange,     setDateRange]     = useState<{ start: string; end: string }>({
    start: dayjs().startOf('month').format('YYYY-MM-DD'),
    end:   dayjs().endOf('month').format('YYYY-MM-DD'),
  })

  const calendarRef = useRef<FullCalendar>(null)
  const [addForm]  = Form.useForm()
  const [editForm] = Form.useForm()

  // ── 載入事件 ──────────────────────────────────────────────────────────────
  const loadEvents = useCallback(async (start: string, end: string) => {
    setLoading(true)
    try {
      const types = activeFilters.length === ALL_TYPES.length
        ? undefined
        : activeFilters.join(',')
      const res = await fetchCalendarEvents({ start, end, types })
      setEvents(res.events)
    } catch {
      message.error('載入行事曆事件失敗')
    } finally {
      setLoading(false)
    }
  }, [activeFilters])

  // ── 載入今日摘要 ───────────────────────────────────────────────────────────
  const loadToday = useCallback(async () => {
    setTodayLoading(true)
    try {
      const [sum, todayRes] = await Promise.all([
        fetchCalendarToday(),
        fetchCalendarEvents({
          start: dayjs().format('YYYY-MM-DD'),
          end:   dayjs().format('YYYY-MM-DD'),
        }),
      ])
      setSummary(sum)
      setTodayEvents(todayRes.events)
    } catch {
      message.error('載入今日摘要失敗')
    } finally {
      setTodayLoading(false)
    }
  }, [])

  useEffect(() => {
    loadToday()
  }, [loadToday])

  useEffect(() => {
    loadEvents(dateRange.start, dateRange.end)
  }, [dateRange, activeFilters, loadEvents])

  // ── FullCalendar datesSet 回調（切換月份/週/日時） ─────────────────────────
  const handleDatesSet = useCallback((arg: DatesSetArg) => {
    const start = dayjs(arg.start).format('YYYY-MM-DD')
    const end   = dayjs(arg.end).subtract(1, 'day').format('YYYY-MM-DD')
    setDateRange({ start, end })
  }, [])

  // ── 點擊事件 ──────────────────────────────────────────────────────────────
  const handleEventClick = useCallback((arg: EventClickArg) => {
    const ev = arg.event.extendedProps as CalendarEvent
    setSelectedEvent(ev)
    setDrawerOpen(true)
  }, [])

  // ── 篩選器切換 ────────────────────────────────────────────────────────────
  const toggleFilter = (type: CalendarEventType) => {
    setActiveFilters((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    )
  }

  const toggleAllFilters = () => {
    setActiveFilters(
      activeFilters.length === ALL_TYPES.length ? [] : [...ALL_TYPES]
    )
  }

  const toggleZone = (zone: CalendarZone) => {
    setActiveZones((prev) =>
      prev.includes(zone) ? prev.filter((z) => z !== zone) : [...prev, zone]
    )
  }

  const toggleAllZones = () => {
    setActiveZones(
      activeZones.length === ZONE_VALUES.length ? [] : [...ZONE_VALUES]
    )
  }

  // ── 新增自訂事件 ───────────────────────────────────────────────────────────
  const handleAddEvent = async () => {
    try {
      const values = await addForm.validateFields()
      setAddLoading(true)
      await createCustomEvent({
        title:        values.title,
        description:  values.description || '',
        start_date:   values.start_date.format('YYYY-MM-DD'),
        end_date:     values.end_date ? values.end_date.format('YYYY-MM-DD') : '',
        all_day:      values.all_day !== false,
        start_time:   values.start_time ? values.start_time.format('HH:mm') : '',
        end_time:     values.end_time   ? values.end_time.format('HH:mm')   : '',
        color:        typeof values.color === 'string'
                        ? values.color
                        : (values.color?.toHexString?.() || '#13c2c2'),
        zone:         values.zone || '其它',
        responsible:  values.responsible || '',
      })
      message.success('自訂事件已新增')
      addForm.resetFields()
      setAddModalOpen(false)
      loadEvents(dateRange.start, dateRange.end)
      loadToday()
    } catch (err: any) {
      if (err?.errorFields) return   // form validation
      message.error('新增失敗')
    } finally {
      setAddLoading(false)
    }
  }

  // ── 開啟編輯 Modal（預填現有自訂事件資料）────────────────────────────────────
  const handleOpenEdit = useCallback((ev: CalendarEvent) => {
    setEditingEvent(ev)
    // ev.title 原本是原始 title（custom 事件沒有前綴）
    editForm.setFieldsValue({
      title:        ev.title,
      description:  ev.description || '',
      start_date:   dayjs(ev.start),
      end_date:     ev.end && ev.end !== ev.start ? dayjs(ev.end) : null,
      all_day:      ev.all_day !== false,
      zone:         ev.zone || '其它',
      responsible:  ev.responsible || '',
      color:        ev.color || '#13c2c2',
    })
    setEditModalOpen(true)
  }, [editForm])

  // ── 送出編輯 ──────────────────────────────────────────────────────────────
  const handleEditEvent = async () => {
    if (!editingEvent) return
    try {
      const values = await editForm.validateFields()
      setEditLoading(true)
      await updateCustomEvent(editingEvent.source_id, {
        title:       values.title,
        description: values.description || '',
        start_date:  values.start_date.format('YYYY-MM-DD'),
        end_date:    values.end_date ? values.end_date.format('YYYY-MM-DD') : '',
        all_day:     values.all_day !== false,
        start_time:  '',
        end_time:    '',
        color:       typeof values.color === 'string'
                       ? values.color
                       : (values.color?.toHexString?.() || '#13c2c2'),
        zone:        values.zone || '其它',
        responsible: values.responsible || '',
      })
      message.success('事件已更新')
      editForm.resetFields()
      setEditModalOpen(false)
      setEditingEvent(null)
      loadEvents(dateRange.start, dateRange.end)
      loadToday()
    } catch (err: any) {
      if (err?.errorFields) return
      message.error('更新失敗')
    } finally {
      setEditLoading(false)
    }
  }

  // ── 刪除自訂事件 ───────────────────────────────────────────────────────────
  const handleDeleteEvent = useCallback(async (ev: CalendarEvent) => {
    try {
      await deleteCustomEvent(ev.source_id)
      message.success('事件已刪除')
      loadEvents(dateRange.start, dateRange.end)
      loadToday()
    } catch {
      message.error('刪除失敗')
    }
  }, [dateRange, loadEvents, loadToday])

  // ── 轉換事件格式給 FullCalendar（套用區域篩選，AND 邏輯）───────────────────
  const fcEvents: EventInput[] = events
    .filter((ev) =>
      activeZones.length === 0 ||
      activeZones.length === ZONE_VALUES.length ||
      activeZones.includes((ev.zone || '其它') as CalendarZone)
    )
    .map(toFCEvent)

  // ── 快速導航按鈕 ──────────────────────────────────────────────────────────
  const goToday = () => calendarRef.current?.getApi().today()

  // ── KPI 摘要顯示 ──────────────────────────────────────────────────────────
  const kpiCards = [
    {
      title:  '今日事件',
      value:  summary?.total_events ?? 0,
      color:  '#1677ff',
      icon:   <CalendarOutlined />,
    },
    {
      title:  '待執行',
      value:  summary?.pending_count ?? 0,
      color:  '#faad14',
      icon:   <ClockCircleOutlined />,
    },
    {
      title:  '異常 / 退回',
      value:  summary?.abnormal_count ?? 0,
      color:  '#ff4d4f',
      icon:   <WarningOutlined />,
    },
    {
      title:  '逾期',
      value:  summary?.overdue_count ?? 0,
      color:  '#ff4d4f',
      icon:   <ExclamationCircleOutlined />,
    },
    {
      title:  '待簽核（全）',
      value:  summary?.approval_pending ?? 0,
      color:  '#fa8c16',
      icon:   <BellOutlined />,
    },
    {
      title:  '高風險事件',
      value:  summary?.high_risk_count ?? 0,
      color:  '#cf1322',
      icon:   <WarningOutlined />,
    },
  ]

  return (
    <div>
      {/* ── Breadcrumb ──────────────────────────────────────────────────── */}
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: <HomeOutlined /> },
          { title: NAV_GROUP.calendar },
        ]}
      />

      {/* ── 頁面標題列 ──────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <CalendarOutlined style={{ marginRight: 8 }} />
          {NAV_GROUP.calendar}
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => { loadToday(); loadEvents(dateRange.start, dateRange.end) }}>
            重新整理
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddModalOpen(true)}>
            新增事件
          </Button>
        </Space>
      </div>

      {/* ── KPI 卡片列 ──────────────────────────────────────────────────── */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {kpiCards.map((kpi) => (
          <Col key={kpi.title} xs={12} sm={8} md={4}>
            <Card size="small" loading={todayLoading}>
              <Statistic
                title={<span style={{ fontSize: 12 }}>{kpi.title}</span>}
                value={kpi.value}
                valueStyle={{ color: kpi.color, fontSize: 22 }}
                prefix={kpi.icon}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* ── 事件類型篩選器 ───────────────────────────────────────────────── */}
      <Card size="small" style={{ marginBottom: 8 }}>
        <Space wrap align="center">
          <Text strong style={{ fontSize: 12 }}>類型：</Text>
          <Button
            size="small"
            type={activeFilters.length === ALL_TYPES.length ? 'primary' : 'default'}
            onClick={toggleAllFilters}
          >
            全選
          </Button>
          {ALL_TYPES.map((type) => (
            <Tag.CheckableTag
              key={type}
              checked={activeFilters.includes(type)}
              onChange={() => toggleFilter(type)}
              style={{
                backgroundColor: activeFilters.includes(type) ? EVENT_TYPE_COLORS[type] : undefined,
                color:           activeFilters.includes(type) ? '#fff' : undefined,
                borderColor:     EVENT_TYPE_COLORS[type],
                border:          `1px solid ${EVENT_TYPE_COLORS[type]}`,
              }}
            >
              {EVENT_TYPE_LABELS[type]}
            </Tag.CheckableTag>
          ))}
        </Space>
      </Card>

      {/* ── 區域別篩選器 ─────────────────────────────────────────────────── */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap align="center">
          <Text strong style={{ fontSize: 12 }}>區域：</Text>
          <Button
            size="small"
            type={activeZones.length === ZONE_VALUES.length ? 'primary' : 'default'}
            onClick={toggleAllZones}
          >
            全選
          </Button>
          {ZONE_VALUES.map((zone) => (
            <Tag.CheckableTag
              key={zone}
              checked={activeZones.includes(zone)}
              onChange={() => toggleZone(zone)}
              style={{
                backgroundColor: activeZones.includes(zone) ? ZONE_COLORS[zone] : undefined,
                color:           activeZones.includes(zone) ? '#fff' : undefined,
                borderColor:     ZONE_COLORS[zone],
                border:          `1px solid ${ZONE_COLORS[zone]}`,
              }}
            >
              {ZONE_LABELS[zone]}
            </Tag.CheckableTag>
          ))}
        </Space>
      </Card>

      {/* ── 主體：今日面板 + 行事曆視圖 ──────────────────────────────────── */}
      <Row gutter={16}>
        {/* 左側：今日重點 */}
        <Col xs={24} lg={6} style={{ marginBottom: 16 }}>
          <TodayPanel
            events={todayEvents}
            loading={todayLoading}
            onSelect={(ev) => { setSelectedEvent(ev); setDrawerOpen(true) }}
          />
        </Col>

        {/* 右側：FullCalendar 主視圖 */}
        <Col xs={24} lg={18}>
          <Card
            bodyStyle={{ padding: '12px 8px' }}
            style={{ minHeight: 600 }}
          >
            {loading && (
              <div style={{
                position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                background: 'rgba(255,255,255,0.6)', zIndex: 10,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Spin tip="載入中..." />
              </div>
            )}

            <FullCalendar
              ref={calendarRef}
              plugins={[dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin]}
              initialView="dayGridMonth"
              locale="zh-tw"
              headerToolbar={{
                left:   'prev,next today',
                center: 'title',
                right:  'dayGridMonth,timeGridWeek,timeGridDay,listMonth',
              }}
              buttonText={{
                today:        '今天',
                month:        '月',
                week:         '週',
                day:          '日',
                list:         '清單',
                listMonth:    '清單',
              }}
              height="auto"
              events={fcEvents}
              datesSet={handleDatesSet}
              eventClick={handleEventClick}
              eventDisplay="block"
              dayMaxEvents={4}
              moreLinkText={(n) => `+${n} 筆`}
              noEventsText="此期間無事件"
              listDayFormat={{ month: 'long', day: 'numeric', weekday: 'short' }}
              eventTimeFormat={{ hour: '2-digit', minute: '2-digit', meridiem: false }}
              eventContent={(arg) => {
                const ev = arg.event.extendedProps as CalendarEvent
                // 區域 → 單字徽章
                const ZONE_BADGE: Record<string, string> = {
                  '飯店': '飯', '商場': '商', '公區': '公', '其它': '',
                }
                const badge     = ZONE_BADGE[ev.zone] ?? ''
                const badgeColor = ZONE_COLORS[ev.zone as CalendarZone] ?? ev.color
                // 去掉 [xxx] 前綴，顯示乾淨標題
                const cleanTitle = arg.event.title.replace(/^\[.*?\]\s*/, '')
                return (
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 3,
                    overflow: 'hidden', padding: '0 3px', height: '100%',
                  }}>
                    {badge && (
                      <span style={{
                        background: badgeColor, color: '#fff',
                        borderRadius: 3, padding: '0 4px',
                        fontSize: 10, fontWeight: 700,
                        flexShrink: 0, lineHeight: '16px',
                      }}>
                        {badge}
                      </span>
                    )}
                    <span style={{
                      overflow: 'hidden', textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap', fontSize: 11,
                    }}>
                      {cleanTitle}
                    </span>
                  </div>
                )
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* ── 事件詳情抽屜 ────────────────────────────────────────────────── */}
      <EventDrawer
        event={selectedEvent}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onEdit={handleOpenEdit}
        onDelete={handleDeleteEvent}
      />

      {/* ── 編輯自訂事件 Modal ──────────────────────────────────────────── */}
      <Modal
        title={<><EditOutlined /> 編輯自訂事件</>}
        open={editModalOpen}
        onOk={handleEditEvent}
        onCancel={() => {
          setEditModalOpen(false)
          setEditingEvent(null)
          editForm.resetFields()
        }}
        confirmLoading={editLoading}
        okText="儲存"
        cancelText="取消"
        width={520}
      >
        <Form
          form={editForm}
          layout="vertical"
          initialValues={{ all_day: true, color: '#13c2c2', zone: '其它' }}
        >
          <Form.Item name="title" label="事件標題" rules={[{ required: true, message: '請填寫標題' }]}>
            <Input placeholder="請輸入事件標題" />
          </Form.Item>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="start_date" label="開始日期" rules={[{ required: true, message: '請選擇日期' }]}>
                <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="end_date" label="結束日期（選填）">
                <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="zone" label="區域別">
                <Select options={ZONE_VALUES.map((z) => ({ label: z, value: z }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="all_day" label="全天事件" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="responsible" label="負責人（選填）">
            <Input placeholder="填入負責人姓名" />
          </Form.Item>

          <Form.Item name="description" label="說明（選填）">
            <Input.TextArea rows={2} placeholder="事件說明" />
          </Form.Item>

          <Form.Item name="color" label="事件顏色">
            <ColorPicker />
          </Form.Item>
        </Form>
      </Modal>

      {/* ── 新增自訂事件 Modal ──────────────────────────────────────────── */}
      <Modal
        title={<><PlusOutlined /> 新增自訂事件</>}
        open={addModalOpen}
        onOk={handleAddEvent}
        onCancel={() => { setAddModalOpen(false); addForm.resetFields() }}
        confirmLoading={addLoading}
        okText="新增"
        cancelText="取消"
        width={520}
      >
        <Form
          form={addForm}
          layout="vertical"
          initialValues={{ all_day: true, color: '#13c2c2', zone: '其它' }}
        >
          <Form.Item name="title" label="事件標題" rules={[{ required: true, message: '請填寫標題' }]}>
            <Input placeholder="請輸入事件標題" />
          </Form.Item>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="start_date" label="開始日期" rules={[{ required: true, message: '請選擇日期' }]}>
                <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="end_date" label="結束日期（選填）">
                <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="zone" label="區域別">
                <Select options={ZONE_VALUES.map((z) => ({ label: z, value: z }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="all_day" label="全天事件" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) => prev.all_day !== curr.all_day}
          >
            {({ getFieldValue }) =>
              !getFieldValue('all_day') ? (
                <Row gutter={12}>
                  <Col span={12}>
                    <Form.Item name="start_time" label="開始時間">
                      <TimePicker format="HH:mm" style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="end_time" label="結束時間">
                      <TimePicker format="HH:mm" style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>
              ) : null
            }
          </Form.Item>

          <Form.Item name="responsible" label="負責人（選填）">
            <Input placeholder="填入負責人姓名" />
          </Form.Item>

          <Form.Item name="description" label="說明（選填）">
            <Input.TextArea rows={2} placeholder="事件說明" />
          </Form.Item>

          <Form.Item name="color" label="事件顏色">
            <ColorPicker />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
