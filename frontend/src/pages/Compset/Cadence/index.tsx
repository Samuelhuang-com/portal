/**
 * 競品分析 — 抓取節奏設定
 * Route: /compset/cadence    Permission: compset_settings_admin
 *
 * 規格書：`docs/SPEC_compset_analysis.md` §9.5、§3、§6.2
 *
 * 【這一頁在做什麼】
 *   決定「抓多遠、多密」—— 也就是決定這個月要花多少錢。
 *   A／B／C 三級是**累積**的：訂 C 級 ＝ A＋B＋C 全開，不是只抓遠期。
 *
 * ── 三個必須擋在存檔之前的坑 ─────────────────────────────────────────────
 * ① **改擷取參數 ＝ 資料斷點**（SPEC §5.6）。把入住人數從 2 改成 1，
 *    之後抓到的價格跟之前的不是同一個東西，畫在同一條線上會是假訊號。
 *    後端會回 `data_break_warning`，這一頁**一定要顯示出來**。
 * ② **窗口必須遞增**（A < B < C）。寫反了該級別會整個不跑，而且**沒有錯誤訊息**
 *    —— 是靜默失效，最難查。後端擋 400，這裡先用即時試算提示。
 * ③ **估算超過配額 ＝ 月中會被硬停**。硬停之後不會自動恢復，要人工加發。
 *    所以要在存檔前就看到數字，不是等到斷料才發現。
 *
 * 「立即抓取」按鈕**會真的花錢**（每次查詢都扣配額），所以有二次確認。
 */
import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, Col, Descriptions, Divider, Form, InputNumber, Modal,
  Progress, Row, Space, Spin, Statistic, Table, Tag, Tooltip,
  Typography, message,
} from 'antd'
import {
  ExclamationCircleOutlined, PlayCircleOutlined, ReloadOutlined,
  SaveOutlined, ThunderboltOutlined,
} from '@ant-design/icons'

import { Link } from 'react-router-dom'

import { fetchCadence, recomputeStats, runFetch, saveCadence } from '@/api/compset'
import type { CadenceResult, FetchRunResult, PlanLevel } from '@/types/compset'
import { useAuthStore } from '@/stores/authStore'
import { TierTag } from '../components'

const { Text, Paragraph } = Typography

const PLAN_OPTIONS: { value: PlanLevel; label: string; desc: string }[] = [
  { value: 'A', label: 'A 級', desc: '只抓近期（D+1〜14），每日一次。最省，但看不到遠期趨勢。' },
  { value: 'B', label: 'B 級（A＋B）', desc: '再加中期（D+15〜45），每 3 天一次。' },
  { value: 'C', label: 'C 級（A＋B＋C）', desc: '再加遠期（D+46〜120），每週一次。全開。' },
]

const CompsetCadencePage: React.FC = () => {
  const hasPermission = useAuthStore((st) => st.hasPermission)
  const canRun = hasPermission('compset_fetch_run')
  const canSubAdmin = hasPermission('compset_subscriber_admin')

  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [running, setRunning] = useState(false)
  const [data, setData] = useState<CadenceResult | null>(null)
  const [runResult, setRunResult] = useState<FetchRunResult | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchCadence()
      setData(res)
      const s = res.subscriber
      // ⚠️ 刻意**不**放 `plan_level`：`PUT /settings/cadence` 不接受它（見下方說明）
      form.setFieldsValue({
        window_a_days: s.windows.A, window_b_days: s.windows.B, window_c_days: s.windows.C,
        freq_a_days: s.freqs.A, freq_b_days: s.freqs.B, freq_c_days: s.freqs.C,
        param_adults: s.params.adults, param_nights: s.params.nights,
        param_gl: s.params.gl, param_hl: s.params.hl, param_currency: s.params.currency,
      })
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [form])

  useEffect(() => { load() }, [load])

  const doSave = async () => {
    const values = await form.validateFields()
    // ② 先在前端擋一次遞增檢查 —— 後端也會擋，但這裡能立刻講清楚為什麼
    if (!(values.window_a_days < values.window_b_days
          && values.window_b_days < values.window_c_days)) {
      message.error(`窗口必須遞增：A(${values.window_a_days}) < `
        + `B(${values.window_b_days}) < C(${values.window_c_days})。`
        + '寫反的話該級別會整個不跑而且沒有任何錯誤訊息。')
      return
    }
    setSaving(true)
    try {
      const res = await saveCadence(values)
      setData(res)
      // ① 資料斷點警告必須顯示，不能只 message.success 就過去
      if (res.data_break_warning) {
        Modal.warning({
          title: '擷取參數已變更 —— 這是資料斷點',
          width: 560,
          content: <>
            <Paragraph>{res.data_break_warning}</Paragraph>
            <Paragraph type="secondary" style={{ marginBottom: 0 }}>
              變更之後抓到的價格，與變更之前的<b>不是同一個口徑</b>。
              價格軌跡圖會把兩段畫在同一條線上，看起來像是市場在某一天突然跳動，
              實際上是設定變了。請記下今天的日期，日後看到斷點時才對得起來。
            </Paragraph>
          </>,
        })
      } else {
        message.success('已儲存')
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '儲存失敗')
    } finally {
      setSaving(false)
    }
  }

  const doRun = () => {
    Modal.confirm({
      title: '立即抓取？',
      icon: <ExclamationCircleOutlined />,
      width: 520,
      content: <>
        <Paragraph>
          這會<b>真的去打 SerpApi，每一次查詢都扣配額</b>。
        </Paragraph>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          目前剩餘 <b>{data?.subscriber.quota.available ?? '—'}</b> 次。
          排程本來每天 04:10 會自己跑一次，除非是要驗證設定或補抓，
          否則不需要手動觸發。
        </Paragraph>
      </>,
      okText: '確定抓取',
      onOk: async () => {
        setRunning(true)
        setRunResult(null)
        try {
          const res = await runFetch()
          setRunResult(res)
          const rows = res.results.reduce((a, r) => a + r.row_count, 0)
          if (rows > 0) message.success(`抓到 ${rows} 筆`)
          else message.warning('沒有抓到任何資料，請看下方批次結果')
          load()
        } catch (e: any) {
          message.error(e?.response?.data?.detail || '抓取失敗')
        } finally {
          setRunning(false)
        }
      },
    })
  }

  const est = data?.estimate
  const quota = data?.subscriber.quota

  return (
    <div style={{ padding: 24 }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Typography.Title level={4} style={{ margin: 0 }}>抓取節奏設定</Typography.Title>
          <Text type="secondary">
            {data?.subscriber.name || '—'} ｜ 決定抓多遠、多密，也就是決定花多少錢
          </Text>
        </Col>
        <Col>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load}>重新整理</Button>
            {canRun && (
              <Button type="primary" danger icon={<PlayCircleOutlined />}
                loading={running} onClick={doRun}>
                立即抓取（會扣配額）
              </Button>
            )}
          </Space>
        </Col>
      </Row>

      {/* ③ 超額警告：硬停不會自動恢復，所以講在最上面 */}
      {est?.over_quota && (
        <Alert type="error" showIcon style={{ marginBottom: 16 }}
          message="以目前設定，本月會在月中被硬停"
          description={`估算每月需要 ${est.total} 次查詢，但配額只有 ${est.monthly_quota} 次。`
            + '用完之後系統會停止抓取且不會自動恢復，要管理員手動加發才能繼續。'
            + '請調低頻率、縮短窗口，或請管理員提高配額。'} />
      )}
      {quota?.is_exhausted && (
        <Alert type="error" showIcon style={{ marginBottom: 16 }}
          message="本期配額已用盡，目前沒有在抓資料"
          description={`已用 ${quota.used} / ${quota.limit} 次。`
            + `下一期從 ${quota.period_start} 起算；要立刻恢復請找管理員手動加發。`} />
      )}

      <Spin spinning={loading}>
        <Row gutter={16}>
          {/* ── 設定 ─────────────────────────────────────────────────── */}
          <Col xs={24} lg={14}>
            <Card title="分級與窗口" style={{ marginBottom: 16 }}
              extra={<Button type="primary" icon={<SaveOutlined />}
                loading={saving} onClick={doSave}>儲存</Button>}>
              {/* ⚠️ 開通等級在這一頁是**唯讀**的。
                  它是商業條件（決定客戶付多少錢），改它要 `compset_subscriber_admin`，
                  而這一頁只要 `compset_settings_admin`。做成可編輯的話，
                  只有節奏權限的人就能把自己從 A 級升到 C 級 ——
                  那是繞過訂閱、直接把成本翻倍，正是 P-2 要擋的事。
                  後端 `PUT /settings/cadence` 也**不接受** `plan_level`
                  （它只寫 window_*／freq_*／param_*），所以放一個 Select 在這裡
                  只會讓人以為改成功了、其實什麼都沒發生。 */}
              <div style={{ marginBottom: 24 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>開通等級</Text>
                <div style={{ marginTop: 4 }}>
                  <Tag color={data?.subscriber.plan_level === 'C' ? 'purple'
                    : data?.subscriber.plan_level === 'B' ? 'cyan' : 'geekblue'}>
                    {PLAN_OPTIONS.find((o) => o.value === data?.subscriber.plan_level)?.label
                      ?? data?.subscriber.plan_level ?? '—'}
                  </Tag>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {PLAN_OPTIONS.find((o) => o.value === data?.subscriber.plan_level)?.desc}
                  </Text>
                </div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  等級是商業條件，要在
                  {canSubAdmin
                    ? <Link to="/compset/subscribers">「訂閱與配額管理」</Link>
                    : <b>「訂閱與配額管理」</b>}
                  改（需要 <code>compset_subscriber_admin</code> 權限）。
                </Text>
              </div>

              <Form form={form} layout="vertical">
                <Divider orientation="left" plain>窗口（抓到未來第幾天）</Divider>
                <Alert type="warning" showIcon style={{ marginBottom: 16 }}
                  message="必須遞增：A < B < C"
                  description="寫反的話該級別會整個不跑，而且不會有任何錯誤訊息 —— 是靜默失效。" />
                <Row gutter={12}>
                  <Col span={8}>
                    <Form.Item name="window_a_days" label="A 級到 D+"
                      rules={[{ required: true }]}>
                      <InputNumber min={1} max={365} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="window_b_days" label="B 級到 D+"
                      rules={[{ required: true }]}>
                      <InputNumber min={2} max={365} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="window_c_days" label="C 級到 D+"
                      rules={[{ required: true }]}>
                      <InputNumber min={3} max={365} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>

                <Divider orientation="left" plain>頻率（幾天抓一次）</Divider>
                <Paragraph type="secondary" style={{ fontSize: 12 }}>
                  ⚠️ 頻率是以<b>本期起算日</b>取模，不是「距離上次成功幾天」。
                  這樣某天失敗不會讓之後每一天的節奏整個位移。
                </Paragraph>
                <Row gutter={12}>
                  <Col span={8}>
                    <Form.Item name="freq_a_days" label="A 級每 N 天"
                      rules={[{ required: true }]}>
                      <InputNumber min={1} max={30} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="freq_b_days" label="B 級每 N 天"
                      rules={[{ required: true }]}>
                      <InputNumber min={1} max={30} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="freq_c_days" label="C 級每 N 天"
                      rules={[{ required: true }]}>
                      <InputNumber min={1} max={30} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>

                <Divider orientation="left" plain>
                  擷取參數
                  <Tooltip title="改這一區的任何一個欄位都會造成資料斷點">
                    <Tag color="red" style={{ marginLeft: 8 }}>改了會斷點</Tag>
                  </Tooltip>
                </Divider>
                <Alert type="warning" showIcon style={{ marginBottom: 16 }}
                  message="改這幾個欄位，前後期的價格不再可比"
                  description="「2 人房一晚」跟「1 人房一晚」不是同一個東西。改了之後，
                    價格軌跡圖上會出現一個看起來像市場跳動、其實是設定變更的斷點。" />
                <Row gutter={12}>
                  <Col span={12}>
                    <Form.Item name="param_adults" label="入住人數">
                      <InputNumber min={1} max={10} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="param_nights" label="住宿晚數">
                      <InputNumber min={1} max={30} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>
              </Form>
            </Card>
          </Col>

          {/* ── 試算 ─────────────────────────────────────────────────── */}
          <Col xs={24} lg={10}>
            <Card title="每月查詢次數試算" style={{ marginBottom: 16 }}>
              {est ? (
                <>
                  <Statistic title="估算每月需要"
                    value={est.total} suffix={`/ ${est.monthly_quota} 次`}
                    valueStyle={{ color: est.over_quota ? '#cf1322' : '#389e0d' }} />
                  <Progress style={{ marginTop: 12 }}
                    percent={est.usage_ratio ? Math.round(est.usage_ratio * 100) : 0}
                    status={est.over_quota ? 'exception' : 'normal'} />
                  <Table size="small" pagination={false} style={{ marginTop: 16 }}
                    rowKey="tier"
                    dataSource={Object.entries(est.per_tier).map(([tier, n]) =>
                      ({ tier, n }))}
                    columns={[
                      { title: '級別', dataIndex: 'tier', width: 90,
                        render: (v: string) => <TierTag tier={v} /> },
                      { title: '每月次數', dataIndex: 'n', align: 'right' },
                    ]} />
                  <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}>
                    A 級是<b>逐家</b>查詢，次數 ＝ 天數 × 有 token 的家數；
                    B／C 級是<b>地點</b>查詢，一次拿回一整批，次數 ＝ 天數 ÷ 頻率。
                    所以競爭組多加一家，只會讓 A 級變貴。
                  </Paragraph>
                </>
              ) : <Text type="secondary">尚無資料</Text>}
            </Card>

            <Card title="本期配額" style={{ marginBottom: 16 }}>
              {quota ? (
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="本期起算">{quota.period_start}</Descriptions.Item>
                  <Descriptions.Item label="月配額">{quota.monthly_quota}</Descriptions.Item>
                  <Descriptions.Item label="手動加發">{quota.granted}</Descriptions.Item>
                  <Descriptions.Item label="本期上限"><b>{quota.limit}</b></Descriptions.Item>
                  <Descriptions.Item label="已使用">{quota.used}</Descriptions.Item>
                  <Descriptions.Item label="剩餘">
                    <Text strong type={quota.available <= 0 ? 'danger' : undefined}>
                      {quota.available}
                    </Text>
                  </Descriptions.Item>
                </Descriptions>
              ) : <Text type="secondary">尚無資料</Text>}
              {!canSubAdmin && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  配額用盡需要管理員手動加發，這一頁改不了。
                </Text>
              )}
            </Card>

            <Card title="彙總快取" size="small">
              <Paragraph type="secondary" style={{ fontSize: 12 }}>
                指數與名次是從快照即時算的，但每日彙總有一份快取。
                數字看起來怪怪的，先按這個重算 —— <b>不會打外部 API、不花配額</b>。
              </Paragraph>
              <Button icon={<ThunderboltOutlined />} onClick={async () => {
                try {
                  await recomputeStats()
                  message.success('已重算')
                } catch (e: any) {
                  message.error(e?.response?.data?.detail || '重算失敗')
                }
              }}>重算彙總</Button>
            </Card>
          </Col>
        </Row>

        {/* ── 手動抓取結果 ──────────────────────────────────────────── */}
        {runResult && (
          <Card title="這次抓取的結果" style={{ marginTop: 16 }}>
            <Table size="small" pagination={false} rowKey="tier"
              dataSource={runResult.results}
              columns={[
                { title: '級別', dataIndex: 'tier', width: 90,
                  render: (v: string) => <TierTag tier={v} /> },
                { title: '狀態', dataIndex: 'status', width: 120,
                  render: (v: string) => {
                    const meta: Record<string, [string, string]> = {
                      success: ['success', '成功'], partial: ['warning', '部分成功'],
                      failed: ['error', '失敗'], quota_exceeded: ['error', '配額用盡'],
                      skipped: ['default', '未到期／未開通'], running: ['processing', '進行中'],
                    }
                    const [c, l] = meta[v] ?? ['default', v]
                    return <Tag color={c}>{l}</Tag>
                  } },
                { title: '入住日區間', width: 200,
                  render: (_: unknown, r: any) => `${r.stay_date_from} 〜 ${r.stay_date_to}` },
                { title: '查詢次數', dataIndex: 'request_count', width: 90, align: 'right' },
                { title: '寫入筆數', dataIndex: 'row_count', width: 90, align: 'right' },
                { title: '訊息',
                  render: (_: unknown, r: any) => (
                    <Space direction="vertical" size={0}>
                      {/* ⚠️ 警告黃色、錯誤紅色，不可混在一起 */}
                      {(r.warnings ?? []).map((w: string, i: number) =>
                        <Text key={i} type="warning" style={{ fontSize: 12 }}>{w}</Text>)}
                      {r.error_message &&
                        <Text type="danger" style={{ fontSize: 12 }}>{r.error_message}</Text>}
                    </Space>
                  ) },
              ]} />
          </Card>
        )}
      </Spin>
    </div>
  )
}

export default CompsetCadencePage
