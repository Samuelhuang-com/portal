/**
 * 房價預測（/opera/forecast）
 * 評估文件：docs/EVAL_opera_rate_forecasting.md §3.2、§3.3、§5
 *
 * TAB：期間預測 / 情境模擬 / 事件月曆 / 模型係數 / 回測 / 預測快照
 *
 * 2026-08-05：「事件月曆」原為獨立頁 /opera/events，依業主指示併入本頁的 TAB。
 *   舊路由保留並導向 /opera/forecast?tab=events（CLAUDE.md §5 禁止移除既有路由）。
 *
 * 設計原則（不可為了畫面好看而拿掉）
 *   1. 每一個預測數字都必須看得到**係數拆解**（點該列開 Drawer）
 *   2. 一律顯示**預測區間**，不給單一數字
 *   3. 回測頁不是可選項 —— 沒有 MAPE，使用者無從判斷該信到什麼程度
 *   4. 樸素基準（去年同期同星期）必須並列顯示，模型沒勝出就要誠實講
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col, DatePicker, Descriptions, Divider, Empty, Form, Input,
  InputNumber, Modal, Popconfirm, Row, Space, Spin, Statistic, Switch, Table, Tabs,
  Tag, Tooltip, Typography, message,
} from 'antd'
import {
  DeleteOutlined, ExperimentOutlined, InfoCircleOutlined, PlusOutlined,
  ReloadOutlined, SaveOutlined, ThunderboltOutlined, UndoOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import { useSearchParams } from 'react-router-dom'
import {
  Area, Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line,
  ResponsiveContainer, Tooltip as RcTooltip, XAxis, YAxis,
} from 'recharts'

import {
  compareForecastRuns, fetchBacktest, fetchCoefficients, fetchForecast,
  fetchForecastRuns, fitCoefficients, runForecastScenario, updateCoefficients,
} from '@/api/opera'
import type {
  BacktestResult, CoefficientListResult, ForecastCoefficient, ForecastDayRow,
  ForecastResult, ForecastRun, RunCompareResult, ScenarioEvent,
} from '@/types/opera'
import BackToTop from '../components/BackToTop'
import ForecastDayDrawer from '../components/ForecastDayDrawer'
import OperaEventsPage from '../Events'
import {
  ACCENT, BRAND, EMPTY, GREEN, GREY, ORANGE, RED,
  fmtInt, fmtMoney, fmtPct, shortDate, trendColor,
} from '../components/formatters'

const { Title, Text, Paragraph } = Typography
const { RangePicker } = DatePicker

const CHART_HEIGHT = 320

/** 評估文件實測的樸素基準，作為畫面上的參考線 */
const NAIVE_ADR_MAPE_REFERENCE = 0.146

const TAB_KEYS = ['predict', 'scenario', 'events', 'coefficients', 'backtest', 'runs'] as const

const OperaForecastPage: React.FC = () => {
  // TAB 與網址同步：可用 ?tab=events 直接開啟「事件月曆」
  //（/opera/events 舊路由即導向此處）
  const [searchParams, setSearchParams] = useSearchParams()
  const raw = searchParams.get('tab') || ''
  const tab = (TAB_KEYS as readonly string[]).includes(raw) ? raw : 'predict'
  const setTab = useCallback((key: string) => {
    // 用 replace 避免每切一次 TAB 就多一筆瀏覽器上一頁紀錄
    setSearchParams(key === 'predict' ? {} : { tab: key }, { replace: true })
  }, [setSearchParams])

  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)

  const [range, setRange] = useState<[Dayjs, Dayjs]>(
    () => [dayjs().add(1, 'day'), dayjs().add(30, 'day')],
  )
  const [forecast, setForecast] = useState<ForecastResult | null>(null)
  const [scenario, setScenario] = useState<ForecastResult | null>(null)
  const [scenarioEvents, setScenarioEvents] = useState<ScenarioEvent[]>([])
  const [eventModal, setEventModal] = useState(false)
  const [eventForm] = Form.useForm()

  const [coefs, setCoefs] = useState<CoefficientListResult | null>(null)
  const [draft, setDraft] = useState<Record<number, number>>({})
  const [backtest, setBacktest] = useState<BacktestResult | null>(null)
  const [runs, setRuns] = useState<ForecastRun[]>([])
  const [runCompare, setRunCompare] = useState<RunCompareResult | null>(null)

  const [drawerRow, setDrawerRow] = useState<ForecastDayRow | null>(null)

  // ── 載入 ────────────────────────────────────────────────────────────────
  const load = useCallback(async (which: string) => {
    setLoading(true)
    try {
      if (which === 'predict') {
        setForecast(await fetchForecast(range[0].format('YYYY-MM-DD'), range[1].format('YYYY-MM-DD')))
      } else if (which === 'coefficients') {
        setCoefs(await fetchCoefficients())
        setDraft({})
      } else if (which === 'backtest') {
        setBacktest(await fetchBacktest())
      } else if (which === 'runs') {
        const res = await fetchForecastRuns()
        setRuns(res.items)
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [range])

  useEffect(() => { load(tab) }, [tab, load])

  // ── 動作 ────────────────────────────────────────────────────────────────
  const handleFit = async () => {
    setBusy(true)
    try {
      const res = await fitCoefficients()
      Modal.info({
        title: '係數估算完成',
        width: 620,
        content: (
          <Space direction="vertical" size={8} style={{ width: '100%', marginTop: 12 }}>
            <Descriptions size="small" column={1} bordered>
              <Descriptions.Item label="訓練資料">
                {`${res.fit_start} ~ ${res.fit_end}，共 ${fmtInt(res.fit_days)} 個可用日`}
              </Descriptions.Item>
              <Descriptions.Item label="錨點">{res.anchor_date}</Descriptions.Item>
              <Descriptions.Item label="基準 ADR／住房率">
                {`$${fmtMoney(res.baseline_adr)}　${fmtPct(res.baseline_occ)}`}
              </Descriptions.Item>
              <Descriptions.Item label="年成長">
                {`ADR ${((res.growth_adr - 1) * 100).toFixed(1)}%　住房率 ${((res.growth_occ - 1) * 100).toFixed(1)}%`}
              </Descriptions.Item>
              <Descriptions.Item label="可售房晚（近 90 天中位數）">
                {res.available_rooms.toFixed(0)}
              </Descriptions.Item>
              <Descriptions.Item label="排除的日子">
                {res.excluded_count > 0
                  ? `${res.excluded_count} 天（負營收／無房晚，不納入估算）`
                  : '無'}
              </Descriptions.Item>
            </Descriptions>
            {res.warnings.length > 0 && (
              <Alert
                type="warning"
                showIcon
                message={`有 ${res.warnings.length} 項提醒`}
                description={<ul style={{ margin: 0, paddingLeft: 18 }}>
                  {res.warnings.slice(0, 8).map((w, i) => <li key={i}>{w}</li>)}
                </ul>}
              />
            )}
            <Text type="secondary" style={{ fontSize: 12 }}>{res.note}</Text>
          </Space>
        ),
      })
      await load('coefficients')
      setForecast(null)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '估算失敗')
    } finally {
      setBusy(false)
    }
  }

  const dirtyIds = Object.keys(draft).map(Number).filter((id) => {
    const row = coefs?.items.find((c) => c.id === id)
    return row && draft[id] !== row.value
  })

  const handleSaveCoefs = async () => {
    if (!dirtyIds.length) { message.info('沒有變更需要儲存'); return }
    setBusy(true)
    try {
      const res = await updateCoefficients(dirtyIds.map((id) => ({ id, value: draft[id], is_manual: true })))
      setCoefs(res)
      setDraft({})
      message.success(`已覆寫 ${dirtyIds.length} 項係數`)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '儲存失敗')
    } finally {
      setBusy(false)
    }
  }

  const handleRevert = async (row: ForecastCoefficient) => {
    setBusy(true)
    try {
      setCoefs(await updateCoefficients([{ id: row.id, is_manual: false }]))
      message.success('已改回自動估算值')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '還原失敗')
    } finally {
      setBusy(false)
    }
  }

  const handleRunScenario = async (save = false) => {
    setBusy(true)
    try {
      const res = await runForecastScenario({
        start: range[0].format('YYYY-MM-DD'),
        end: range[1].format('YYYY-MM-DD'),
        events: scenarioEvents,
        save,
        note: scenarioEvents.map((e) => e.name).join('、'),
      })
      setScenario(res)
      if (save && res.saved_run_id) message.success(`已存成快照 #${res.saved_run_id}`)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '情境模擬失敗')
    } finally {
      setBusy(false)
    }
  }

  const handleCompareRuns = async () => {
    setBusy(true)
    try {
      const res = await compareForecastRuns()
      setRunCompare(res)
      message.success(`已回填 ${res.filled} 天的實際值`)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '比對失敗')
    } finally {
      setBusy(false)
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 期間預測
  // ══════════════════════════════════════════════════════════════════════════

  const forecastChart = useMemo(
    () => (forecast?.items || []).map((d) => ({
      date: shortDate(d.business_date),
      預測ADR: Math.round(d.predicted_adr),
      區間下限: Math.round(d.adr_lower),
      區間寬度: Math.round(d.adr_upper - d.adr_lower),
      樸素基準: d.naive ? Math.round(d.naive.predicted_adr) : null,
      實際: d.actual ? Math.round(d.actual.adr) : null,
      預測住房率: Number((d.predicted_occupancy * 100).toFixed(1)),
    })),
    [forecast],
  )

  const forecastColumns: ColumnsType<ForecastDayRow> = [
    { title: '日期', dataIndex: 'business_date', width: 118 },
    {
      title: '星期',
      dataIndex: 'weekday_label',
      width: 84,
      render: (v: string, r) => <Tag color={r.weekday >= 4 ? ORANGE : ACCENT}>{v}</Tag>,
    },
    {
      title: '預測 ADR',
      dataIndex: 'predicted_adr',
      width: 110,
      align: 'right',
      render: (v: number) => <Text strong>{`$${fmtMoney(v)}`}</Text>,
    },
    {
      title: '預測區間',
      width: 165,
      align: 'right',
      render: (_, r) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {`$${fmtMoney(r.adr_lower)} ~ $${fmtMoney(r.adr_upper)}`}
        </Text>
      ),
    },
    {
      title: '預測住房率',
      dataIndex: 'predicted_occupancy',
      width: 110,
      align: 'right',
      render: (v: number) => fmtPct(v),
    },
    {
      title: '預測營收',
      dataIndex: 'predicted_revenue',
      width: 120,
      align: 'right',
      render: (v: number) => `$${fmtMoney(v)}`,
    },
    {
      title: '樸素基準',
      width: 110,
      align: 'right',
      render: (_, r) => (r.naive
        ? <Text type="secondary">{`$${fmtMoney(r.naive.predicted_adr)}`}</Text>
        : <Text type="secondary">{EMPTY}</Text>),
    },
    {
      title: '實際',
      width: 130,
      align: 'right',
      render: (_, r) => {
        if (!r.actual) return <Text type="secondary">{EMPTY}</Text>
        const err = r.actual.adr ? (r.predicted_adr - r.actual.adr) / r.actual.adr : null
        return (
          <Space direction="vertical" size={0}>
            <Text>{`$${fmtMoney(r.actual.adr)}`}</Text>
            {err !== null && (
              <Text style={{ fontSize: 12, color: Math.abs(err) > 0.15 ? RED : GREY }}>
                {`${err >= 0 ? '+' : ''}${(err * 100).toFixed(1)}%`}
              </Text>
            )}
          </Space>
        )
      },
    },
    {
      title: '事件',
      width: 150,
      render: (_, r) => (r.events.length
        ? <Space size={4} wrap>{r.events.map((e, i) => <Tag key={i} color="purple">{e.name}</Tag>)}</Space>
        : <Text type="secondary">{EMPTY}</Text>),
    },
  ]

  const renderNotFitted = (reason?: string) => (
    <Empty
      description={
        <Space direction="vertical">
          <Text>{reason || '尚未估算模型係數'}</Text>
          <Button type="primary" icon={<ThunderboltOutlined />} loading={busy} onClick={handleFit}>
            重新估算係數
          </Button>
        </Space>
      }
    />
  )

  const renderSummary = (res: ForecastResult, title: string) => (
    <Row gutter={16}>
      <Col span={6}>
        <Card size="small">
          <Statistic title={`${title}加權 ADR`} value={fmtMoney(res.summary.predicted_adr)}
            prefix="$" valueStyle={{ color: BRAND }} />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {`區間 $${fmtMoney(res.summary.adr_lower)} ~ $${fmtMoney(res.summary.adr_upper)}`}
          </Text>
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small">
          <Statistic title="預測住房率" value={fmtPct(res.summary.predicted_occupancy)} valueStyle={{ color: BRAND }} />
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small">
          <Statistic title="預測 RevPAR" value={fmtMoney(res.summary.predicted_revpar)}
            prefix="$" valueStyle={{ color: BRAND }} />
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small">
          <Statistic title={`預測總營收（${res.summary.days} 天）`}
            value={fmtMoney(res.summary.predicted_revenue)} prefix="$" valueStyle={{ color: BRAND }} />
        </Card>
      </Col>
    </Row>
  )

  const renderPredictTab = () => {
    if (!forecast) return <Empty description="請選擇預測期間" />
    if (!forecast.ok) return renderNotFitted(forecast.reason)

    return (
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          type="info"
          showIcon
          message="期間預測比單日可靠"
          description={
            '單日預測的隨機性很大（一團 20 間房就能讓住房率跳 29 個百分點）。'
            + '做訂價與預算決策請看下方的期間加權值；單日數字請搭配預測區間一起看。'
            + '點任一列可展開係數拆解。'
          }
        />

        {forecast.warnings.map((w, i) => (
          <Alert key={i} type="warning" showIcon message={w} />
        ))}

        {renderSummary(forecast, '期間')}

        {forecast.naive_summary && (
          <Card size="small">
            <Space size={24} wrap>
              <Text type="secondary">同期間的樸素基準（去年同星期）：</Text>
              <Text strong>{`ADR $${fmtMoney(forecast.naive_summary.predicted_adr)}`}</Text>
              <Text>{`總營收 $${fmtMoney(forecast.naive_summary.predicted_revenue)}`}</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {`（涵蓋 ${forecast.naive_summary.days} / ${forecast.summary.days} 天）`}
              </Text>
              <Tooltip title="兩者差距大時，代表模型認為今年的季節性或成長與去年不同。差距的原因可到「模型係數」頁查證。">
                <InfoCircleOutlined style={{ color: GREY }} />
              </Tooltip>
            </Space>
          </Card>
        )}

        <Card size="small" title="逐日預測（陰影為預測區間）">
          <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
            <ComposedChart data={forecastChart}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" minTickGap={24} />
              <YAxis tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
              <RcTooltip />
              <Legend />
              {/* 用「下限 + 寬度」堆疊出區間帶：下限那層設透明 */}
              <Area type="monotone" dataKey="區間下限" stackId="band" stroke="none" fill="transparent" legendType="none" />
              <Area type="monotone" dataKey="區間寬度" stackId="band" stroke="none" fill={ACCENT} fillOpacity={0.18} />
              <Line type="monotone" dataKey="預測ADR" stroke={BRAND} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="樸素基準" stroke={GREY} strokeWidth={1} dot={false} strokeDasharray="4 4" />
              <Line type="monotone" dataKey="實際" stroke={GREEN} strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </Card>

        <Card size="small" title="逐日明細" extra={<Text type="secondary" style={{ fontSize: 12 }}>點列展開係數拆解</Text>}>
          <Table
            rowKey="business_date"
            size="small"
            dataSource={forecast.items}
            columns={forecastColumns}
            pagination={{ pageSize: 31, showSizeChanger: false }}
            onRow={(row) => ({ onClick: () => setDrawerRow(row), style: { cursor: 'pointer' } })}
          />
        </Card>

        <Card size="small" title="本次預測採用的模型參數">
          <Descriptions size="small" column={3} bordered>
            <Descriptions.Item label="錨點日">{forecast.coefficients.anchor_date || EMPTY}</Descriptions.Item>
            <Descriptions.Item label="基準 ADR">{`$${fmtMoney(forecast.coefficients.baseline_adr)}`}</Descriptions.Item>
            <Descriptions.Item label="基準住房率">{fmtPct(forecast.coefficients.baseline_occ)}</Descriptions.Item>
            <Descriptions.Item label="年成長（ADR）">
              {`${((forecast.coefficients.growth_adr - 1) * 100).toFixed(1)}%`}
            </Descriptions.Item>
            <Descriptions.Item label="可售房晚">{forecast.coefficients.available_rooms.toFixed(0)}</Descriptions.Item>
            <Descriptions.Item label="訓練資料">
              {`${forecast.coefficients.fit_start} ~ ${forecast.coefficients.fit_end}（${fmtInt(forecast.coefficients.fit_days)} 天）`}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      </Space>
    )
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 情境模擬
  // ══════════════════════════════════════════════════════════════════════════

  const renderScenarioTab = () => (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Alert
        type="info"
        showIcon
        message="假設情境不會存進事件月曆"
        description={
          '在這裡填的事件只影響這一次的試算，例如「如果國際電腦展辦在這個週末會怎樣」。'
          + '要長期套用請到「事件月曆」頁新增。倍數 1.35 代表 +35%（不是 135）。'
        }
      />

      <Card
        size="small"
        title="假設事件"
        extra={
          <Space>
            <Button icon={<PlusOutlined />} onClick={() => { eventForm.resetFields(); setEventModal(true) }}>
              加入事件
            </Button>
            <Button type="primary" icon={<ExperimentOutlined />} loading={busy}
              disabled={!scenarioEvents.length} onClick={() => handleRunScenario(false)}>
              試算
            </Button>
            <Button icon={<SaveOutlined />} loading={busy} disabled={!scenario}
              onClick={() => handleRunScenario(true)}>
              存成快照
            </Button>
          </Space>
        }
      >
        {scenarioEvents.length ? (
          <Table
            rowKey={(r) => `${r.name}-${r.start_date}`}
            size="small"
            pagination={false}
            dataSource={scenarioEvents}
            columns={[
              { title: '事件', dataIndex: 'name', width: 200 },
              { title: '起', dataIndex: 'start_date', width: 120 },
              { title: '迄', dataIndex: 'end_date', width: 120 },
              { title: 'ADR 倍數', dataIndex: 'adr_index', width: 110, align: 'right',
                render: (v: number) => `×${v.toFixed(2)}` },
              { title: '住房率倍數', dataIndex: 'occ_index', width: 120, align: 'right',
                render: (v: number) => `×${v.toFixed(2)}` },
              {
                title: '',
                width: 60,
                render: (_, r) => (
                  <Button type="text" danger icon={<DeleteOutlined />}
                    onClick={() => setScenarioEvents((prev) => prev.filter((x) => x !== r))} />
                ),
              },
            ]}
          />
        ) : <Empty description="尚未加入任何假設事件" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
      </Card>

      {scenario && scenario.ok && (
        <>
          {renderSummary(scenario, '情境')}
          {forecast && forecast.ok && (
            <Card size="small" title="與無事件情境的差異">
              <Descriptions size="small" column={3} bordered>
                <Descriptions.Item label="ADR">
                  <Space>
                    <Text type="secondary">{`$${fmtMoney(forecast.summary.predicted_adr)}`}</Text>
                    <Text>→</Text>
                    <Text strong>{`$${fmtMoney(scenario.summary.predicted_adr)}`}</Text>
                    <Text style={{ color: trendColor(scenario.summary.predicted_adr - forecast.summary.predicted_adr) }}>
                      {`(×${(scenario.summary.predicted_adr / (forecast.summary.predicted_adr || 1)).toFixed(3)})`}
                    </Text>
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="住房率">
                  <Space>
                    <Text type="secondary">{fmtPct(forecast.summary.predicted_occupancy)}</Text>
                    <Text>→</Text>
                    <Text strong>{fmtPct(scenario.summary.predicted_occupancy)}</Text>
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="總營收">
                  <Space>
                    <Text type="secondary">{`$${fmtMoney(forecast.summary.predicted_revenue)}`}</Text>
                    <Text>→</Text>
                    <Text strong>{`$${fmtMoney(scenario.summary.predicted_revenue)}`}</Text>
                    <Text style={{ color: trendColor(scenario.summary.predicted_revenue - forecast.summary.predicted_revenue) }}>
                      {`(+$${fmtMoney(scenario.summary.predicted_revenue - forecast.summary.predicted_revenue)})`}
                    </Text>
                  </Space>
                </Descriptions.Item>
              </Descriptions>
            </Card>
          )}
          <Card size="small" title="情境逐日明細">
            <Table
              rowKey="business_date"
              size="small"
              dataSource={scenario.items}
              columns={forecastColumns}
              pagination={{ pageSize: 31, showSizeChanger: false }}
              onRow={(row) => ({ onClick: () => setDrawerRow(row), style: { cursor: 'pointer' } })}
            />
          </Card>
        </>
      )}

      <Modal
        open={eventModal}
        title="加入假設事件"
        onCancel={() => setEventModal(false)}
        onOk={async () => {
          const v = await eventForm.validateFields()
          setScenarioEvents((prev) => [...prev, {
            name: v.name,
            start_date: v.dates[0].format('YYYY-MM-DD'),
            end_date: v.dates[1].format('YYYY-MM-DD'),
            adr_index: v.adr_index,
            occ_index: v.occ_index,
          }])
          setEventModal(false)
        }}
      >
        <Form form={eventForm} layout="vertical"
          initialValues={{ adr_index: 1.2, occ_index: 1.1, dates: range }}>
          <Form.Item name="name" label="事件名稱" rules={[{ required: true, message: '請填事件名稱' }]}>
            <Input placeholder="例：國際電腦展" />
          </Form.Item>
          <Form.Item name="dates" label="期間" rules={[{ required: true, message: '請選期間' }]}>
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="adr_index" label="ADR 倍數"
                extra="1.35 = ADR 提高 35%"
                rules={[{ required: true }, { type: 'number', min: 0.1, max: 5, message: '合理範圍 0.1 ~ 5' }]}>
                <InputNumber style={{ width: '100%' }} step={0.05} precision={2} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="occ_index" label="住房率倍數"
                extra="滿房有上限，實際會壓在 100% 以內"
                rules={[{ required: true }, { type: 'number', min: 0.1, max: 5, message: '合理範圍 0.1 ~ 5' }]}>
                <InputNumber style={{ width: '100%' }} step={0.05} precision={2} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </Space>
  )

  // ══════════════════════════════════════════════════════════════════════════
  // 模型係數
  // ══════════════════════════════════════════════════════════════════════════

  const coefColumns: ColumnsType<ForecastCoefficient> = [
    { title: '類別', dataIndex: 'kind_label', width: 130 },
    { title: '項目', dataIndex: 'key_label', width: 100 },
    { title: '指標', dataIndex: 'metric_label', width: 80 },
    {
      title: '目前值',
      width: 160,
      render: (_, row) => {
        if (!row.is_editable) {
          return <Text>{row.kind === 'baseline' && row.metric === 'occupancy'
            ? fmtPct(row.value) : row.value.toFixed(4)}</Text>
        }
        const isBaseline = row.kind === 'baseline'
        return (
          <InputNumber
            size="small"
            style={{ width: 130 }}
            value={draft[row.id] !== undefined ? draft[row.id] : row.value}
            min={0}
            step={isBaseline ? 10 : 0.01}
            precision={isBaseline ? 2 : 4}
            onChange={(v) => { if (v !== null) setDraft((p) => ({ ...p, [row.id]: v as number })) }}
          />
        )
      },
    },
    {
      title: '自動估算值',
      dataIndex: 'fitted_value',
      width: 130,
      align: 'right',
      render: (v: number, row) => (
        <Text type="secondary">
          {row.kind === 'baseline' && row.metric === 'occupancy' ? fmtPct(v) : v.toFixed(4)}
        </Text>
      ),
    },
    {
      title: '樣本天數',
      dataIndex: 'sample_days',
      width: 110,
      align: 'right',
      render: (v: number, row) => (
        row.is_reliable
          ? fmtInt(v)
          : <Tooltip title="樣本不足 8 天，這個係數已固定為 1.00 不套用">
              <Tag color={ORANGE}>{`${v} 天`}</Tag>
            </Tooltip>
      ),
    },
    {
      title: '狀態',
      width: 110,
      align: 'center',
      render: (_, row) => {
        if (dirtyIds.includes(row.id)) return <Tag color={ORANGE}>未儲存</Tag>
        if (row.is_manual) return <Tag color="blue">人工覆寫</Tag>
        if (!row.is_editable) return <Tag>算出來的</Tag>
        return <Tag>自動</Tag>
      },
    },
    {
      title: '',
      width: 80,
      render: (_, row) => (row.is_manual ? (
        <Popconfirm title="改回自動估算值？" onConfirm={() => handleRevert(row)}>
          <Button type="text" size="small" icon={<UndoOutlined />}>還原</Button>
        </Popconfirm>
      ) : null),
    },
  ]

  const dowChart = useMemo(() => {
    if (!coefs) return []
    const labels = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    return labels.map((label, i) => ({
      label,
      ADR係數: coefs.items.find((c) => c.kind === 'dow' && c.coef_key === String(i) && c.metric === 'adr')?.value ?? 1,
      住房率係數: coefs.items.find((c) => c.kind === 'dow' && c.coef_key === String(i) && c.metric === 'occupancy')?.value ?? 1,
    }))
  }, [coefs])

  const monthChart = useMemo(() => {
    if (!coefs) return []
    return Array.from({ length: 12 }, (_, i) => ({
      label: `${i + 1} 月`,
      ADR係數: coefs.items.find((c) => c.kind === 'month' && c.coef_key === String(i + 1) && c.metric === 'adr')?.value ?? 1,
      住房率係數: coefs.items.find((c) => c.kind === 'month' && c.coef_key === String(i + 1) && c.metric === 'occupancy')?.value ?? 1,
    }))
  }, [coefs])

  const renderCoefTab = () => {
    if (!coefs || !coefs.has_fitted) return renderNotFitted()

    return (
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          type="info"
          showIcon
          message="係數可以人工覆寫，重新估算時不會被蓋掉"
          description={
            '覆寫後仍保留自動估算值供對照，隨時可以按「還原」改回去。'
            + '基準值、星期、月份、年成長可改；錨點與預測區間是算出來的事實，改了會讓模型自相矛盾，故不開放。'
          }
        />

        <Row gutter={16}>
          <Col span={12}>
            <Card size="small" title="星期係數">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={dowChart}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" />
                  <YAxis domain={[0.6, 1.4]} />
                  <RcTooltip />
                  <Legend />
                  <Bar dataKey="ADR係數" fill={BRAND} />
                  <Bar dataKey="住房率係數" fill={ACCENT} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small" title="月份係數（已扣除星期效應）">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={monthChart}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" />
                  <YAxis domain={[0.6, 1.4]} />
                  <RcTooltip />
                  <Legend />
                  <Bar dataKey="ADR係數" fill={BRAND} />
                  <Bar dataKey="住房率係數" fill={ACCENT} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        </Row>

        <Card
          size="small"
          title="全部係數"
          extra={
            <Space>
              <Button icon={<ReloadOutlined />} onClick={() => load('coefficients')}>重新載入</Button>
              <Button icon={<UndoOutlined />} disabled={!dirtyIds.length} onClick={() => setDraft({})}>放棄變更</Button>
              <Button type="primary" icon={<SaveOutlined />} loading={busy}
                disabled={!dirtyIds.length} onClick={handleSaveCoefs}>
                {dirtyIds.length ? `儲存（${dirtyIds.length} 項）` : '儲存'}
              </Button>
              <Button icon={<ThunderboltOutlined />} loading={busy} onClick={handleFit}>重新估算係數</Button>
            </Space>
          }
        >
          <Table rowKey="id" size="small" pagination={false} dataSource={coefs.items} columns={coefColumns} />
        </Card>
      </Space>
    )
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 回測
  // ══════════════════════════════════════════════════════════════════════════

  const renderBacktestTab = () => {
    if (!backtest) return <Empty description="載入中" />
    if (!backtest.ok) {
      return <Alert type="warning" showIcon message="目前無法回測" description={backtest.reason} />
    }

    const decomp = backtest.models.find((m) => m.model === 'decomp')!
    const naive = backtest.models.find((m) => m.model === 'naive')!

    return (
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          type={backtest.beats_naive ? 'success' : 'warning'}
          showIcon
          message={backtest.beats_naive ? '分解模型勝過樸素基準' : '分解模型沒有勝過樸素基準'}
          description={backtest.verdict}
        />

        <Card size="small" title="回測設定">
          <Descriptions size="small" column={2} bordered>
            <Descriptions.Item label="訓練期">
              {`${backtest.train.start} ~ ${backtest.train.end}（${fmtInt(backtest.train.days)} 天）`}
            </Descriptions.Item>
            <Descriptions.Item label="測試期">
              {`${backtest.test.start} ~ ${backtest.test.end}（${fmtInt(backtest.test.days)} 天）`}
            </Descriptions.Item>
            <Descriptions.Item label="切分方式" span={2}>
              用測試期之前的資料重新估係數，再去預測測試期 —— 沒有偷看答案，所以 MAPE 不會虛低
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Card size="small" title="模型比較（MAPE 越低越好）">
          <Table
            rowKey="model"
            size="small"
            pagination={false}
            dataSource={backtest.models}
            columns={[
              {
                title: '模型',
                dataIndex: 'label',
                width: 230,
                render: (v: string, r) => (
                  <Space>
                    <Text strong={r.model === 'decomp'}>{v}</Text>
                    {r.model === 'naive' && <Tag>基準線</Tag>}
                  </Space>
                ),
              },
              {
                title: 'ADR MAPE',
                width: 130,
                align: 'right',
                render: (_, r) => {
                  const best = r.adr.mape !== null && r.adr.mape === Math.min(
                    ...backtest.models.map((m) => m.adr.mape ?? 9),
                  )
                  return (
                    <Text strong={best} style={{ color: best ? GREEN : undefined }}>
                      {r.adr.mape !== null ? fmtPct(r.adr.mape) : EMPTY}
                    </Text>
                  )
                },
              },
              {
                title: '住房率 MAPE',
                width: 130,
                align: 'right',
                render: (_, r) => (r.occupancy.mape !== null ? fmtPct(r.occupancy.mape) : EMPTY),
              },
              {
                title: '營收 MAPE',
                width: 130,
                align: 'right',
                render: (_, r) => (r.revenue.mape !== null ? fmtPct(r.revenue.mape) : EMPTY),
              },
              {
                title: 'ADR 平均誤差',
                width: 130,
                align: 'right',
                render: (_, r) => (r.adr.mae !== null ? `$${fmtMoney(r.adr.mae)}` : EMPTY),
              },
              {
                title: 'ADR 偏誤',
                width: 140,
                align: 'right',
                render: (_, r) => (r.adr.bias !== null
                  ? (
                    <Tooltip title={r.adr.bias > 0 ? '系統性高估' : '系統性低估'}>
                      <Text style={{ color: Math.abs(r.adr.bias) > 100 ? ORANGE : undefined }}>
                        {`${r.adr.bias >= 0 ? '+' : '−'}$${fmtMoney(Math.abs(r.adr.bias))}`}
                      </Text>
                    </Tooltip>
                  )
                  : EMPTY),
              },
              { title: '樣本天數', width: 100, align: 'right', render: (_, r) => fmtInt(r.adr.n) },
            ]}
          />
          <Divider style={{ margin: '12px 0' }} />
          <Space size={24} wrap>
            <Text type="secondary">
              {`預測區間涵蓋率 ${fmtPct(backtest.interval_coverage)}（目標 ${fmtPct(backtest.interval_target)}）`}
            </Text>
            <Tooltip title="實際值落在預測區間內的比例。太低代表區間過窄、對不確定性過度樂觀；太高代表區間太寬、沒有參考價值。">
              <InfoCircleOutlined style={{ color: GREY }} />
            </Tooltip>
            <Text type="secondary">
              {`評估文件的樸素基準參考值：ADR MAPE ${fmtPct(NAIVE_ADR_MAPE_REFERENCE)}`}
            </Text>
          </Space>
        </Card>

        <Card size="small" title="逐月 ADR MAPE">
          <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
            <ComposedChart data={backtest.monthly_series.map((m) => ({
              month: m.month,
              分解模型: m.decomp_mape !== null ? Number((m.decomp_mape * 100).toFixed(1)) : null,
              樸素基準: m.naive_mape !== null ? Number((m.naive_mape * 100).toFixed(1)) : null,
            }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis unit="%" />
              <RcTooltip />
              <Legend />
              <Bar dataKey="分解模型" fill={BRAND} />
              <Bar dataKey="樸素基準" fill={GREY} />
            </ComposedChart>
          </ResponsiveContainer>
        </Card>

        <Card size="small" title="測試期預測 vs 實際（ADR）">
          <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
            <ComposedChart data={backtest.series.map((s) => ({
              date: shortDate(s.business_date),
              實際: Math.round(s.actual_adr),
              分解模型: Math.round(s.decomp_adr),
              樸素基準: s.naive_adr !== null ? Math.round(s.naive_adr) : null,
            }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" minTickGap={30} />
              <YAxis tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
              <RcTooltip />
              <Legend />
              <Line dataKey="實際" stroke={GREEN} strokeWidth={2} dot={false} />
              <Line dataKey="分解模型" stroke={BRAND} strokeWidth={2} dot={false} />
              <Line dataKey="樸素基準" stroke={GREY} strokeWidth={1} dot={false} strokeDasharray="4 4" />
            </ComposedChart>
          </ResponsiveContainer>
        </Card>

        {backtest.warnings.length > 0 && (
          <Alert
            type="warning"
            showIcon
            message="訓練期的提醒"
            description={<ul style={{ margin: 0, paddingLeft: 18 }}>
              {backtest.warnings.slice(0, 10).map((w, i) => <li key={i}>{w}</li>)}
            </ul>}
          />
        )}
      </Space>
    )
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 預測快照
  // ══════════════════════════════════════════════════════════════════════════

  const renderRunsTab = () => (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Alert
        type="info"
        showIcon
        message="快照是算出真實準確度的唯一方法"
        description={
          '「回測」是模型回頭重算，「快照」是當時真的預測了什麼。'
          + '把每次預測存下來，等日期過了再按「回填實際值」，就能知道模型在真實情況下準不準。'
        }
      />

      {runCompare && (
        <Card size="small" title="已到期預測的真實誤差">
          <Descriptions size="small" column={4} bordered>
            <Descriptions.Item label="已比對天數">{fmtInt(runCompare.compared)}</Descriptions.Item>
            <Descriptions.Item label="ADR MAPE">
              {runCompare.adr.mape !== null ? fmtPct(runCompare.adr.mape) : EMPTY}
            </Descriptions.Item>
            <Descriptions.Item label="住房率 MAPE">
              {runCompare.occupancy.mape !== null ? fmtPct(runCompare.occupancy.mape) : EMPTY}
            </Descriptions.Item>
            <Descriptions.Item label="營收 MAPE">
              {runCompare.revenue.mape !== null ? fmtPct(runCompare.revenue.mape) : EMPTY}
            </Descriptions.Item>
          </Descriptions>
          <Text type="secondary" style={{ fontSize: 12 }}>{runCompare.note}</Text>
        </Card>
      )}

      <Card
        size="small"
        title="快照清單"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => load('runs')}>重新載入</Button>
            <Button type="primary" loading={busy} onClick={handleCompareRuns}>回填實際值</Button>
          </Space>
        }
      >
        <Table
          rowKey="id"
          size="small"
          dataSource={runs}
          pagination={{ pageSize: 20, showSizeChanger: false }}
          columns={[
            { title: '#', dataIndex: 'id', width: 70 },
            { title: '執行時間', dataIndex: 'run_at', width: 160 },
            {
              title: '預測期間',
              width: 210,
              render: (_, r) => `${r.horizon_start} ~ ${r.horizon_end}（${r.days} 天）`,
            },
            { title: '模型', dataIndex: 'model_label', width: 180 },
            { title: '預測 ADR', dataIndex: 'predicted_adr', width: 110, align: 'right',
              render: (v: number) => `$${fmtMoney(v)}` },
            { title: '預測住房率', dataIndex: 'predicted_occ', width: 110, align: 'right',
              render: (v: number) => fmtPct(v) },
            { title: '預測營收', dataIndex: 'predicted_revenue', width: 130, align: 'right',
              render: (v: number) => `$${fmtMoney(v)}` },
            { title: '建立者', dataIndex: 'created_by_name', width: 110 },
            { title: '備註', dataIndex: 'note', ellipsis: true },
          ]}
        />
      </Card>
    </Space>
  )

  // ══════════════════════════════════════════════════════════════════════════

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ color: BRAND }}>房價預測</Title>
      <Paragraph type="secondary" style={{ marginTop: -8 }}>
        可解釋的乘法分解模型：基準 × 星期 × 月份 × 年成長 × 事件。
        預測是輔助不是決策 —— 模型看不到競品價格、突發事件與你的促銷計畫。
      </Paragraph>

      <Card
        size="small"
        style={{ marginBottom: 16 }}
        extra={
          (tab === 'predict' || tab === 'scenario') ? (
            <Space>
              <Text type="secondary">預測期間</Text>
              <RangePicker
                value={range}
                allowClear={false}
                onChange={(r) => {
                  if (r && r[0] && r[1]) { setRange([r[0], r[1]]); setScenario(null) }
                }}
              />
              <Button icon={<ReloadOutlined />} onClick={() => load('predict')}>重新預測</Button>
            </Space>
          ) : null
        }
      >
        <Spin spinning={loading}>
          <Tabs
            activeKey={tab}
            onChange={setTab}
            items={[
              { key: 'predict', label: '期間預測', children: renderPredictTab() },
              { key: 'scenario', label: '情境模擬', children: renderScenarioTab() },
              { key: 'events', label: '事件月曆', children: <OperaEventsPage embedded /> },
              { key: 'coefficients', label: '模型係數', children: renderCoefTab() },
              { key: 'backtest', label: '回測', children: renderBacktestTab() },
              { key: 'runs', label: '預測快照', children: renderRunsTab() },
            ]}
          />
        </Spin>
      </Card>

      <ForecastDayDrawer open={!!drawerRow} row={drawerRow} onClose={() => setDrawerRow(null)} />
      <BackToTop />
    </div>
  )
}

export default OperaForecastPage
