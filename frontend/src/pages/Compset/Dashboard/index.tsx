/**
 * 競品分析 — Dashboard
 * Route: /compset/dashboard    Permission: compset_view
 *
 * 規格書：`docs/SPEC_compset_analysis.md` §9.1
 *
 * 【這一頁在回答的四個問題】
 *   ① 最近一個有資料的入住日，我的房價跟競品比是貴還是便宜（價格指數）
 *   ② 未來 7 天，哪幾天我偏離競品最多（該調價的日子）
 *   ③ 有沒有競品已經賣完（賣完 ＝ 我可以往上試）
 *   ④ 這個月的抓取配額還剩多少（用完就沒有新資料了）
 *
 * ⚠️ **指數旁邊一定要有樣本數**。只顯示 1.05 的話，「4 家算出來的」跟
 *    「1 家算出來的」長得一模一樣，但後者不能拿來調價。
 *    這是本模組最容易誤導人的地方（SPEC §7.3）。
 *
 * ⚠️ 這一頁**不做期間篩選**，所以刻意不用 `StandardRangePicker`。
 *    競品分析是**未來導向**（看還沒住的日子），而標準快捷「本月／上月／去年」
 *    全是過去（該元件註解第 3 條明列此情境不適用）。未來 7 天是固定窗格。
 */
import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert, Card, Col, Empty, Progress, Row, Space, Spin, Statistic, Table,
  Tag, Tooltip, Typography, message,
} from 'antd'
import {
  ArrowRightOutlined, QuestionCircleOutlined, ReloadOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useNavigate } from 'react-router-dom'
import {
  CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer,
  Tooltip as ReTooltip, XAxis, YAxis,
} from 'recharts'

import dayjs from 'dayjs'

import { fetchDashboard } from '@/api/compset'
import type { DailyStat, DashboardResult, PriceBasis } from '@/types/compset'
import {
  BasisSwitch, IndexValue, RankValue, SnapshotStamp, SoldOutCell,
  StayDateLabel, fmtMoney, isLowSample, sampleCountOf,
} from '../components'

const { Text, Paragraph } = Typography

// 品牌色（CLAUDE.md 受保護元素），不要改
const BRAND = '#1B3A5C'
const ACCENT = '#4BA8E8'

const CompsetDashboardPage: React.FC = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<DashboardResult | null>(null)
  const [basis, setBasis] = useState<PriceBasis>('pretax')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setData(await fetchDashboard())
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const head = data?.today ?? null
  const quota = data?.quota

  /**
   * ⚠️ `data.today` 是**視窗內第一個有資料的入住日**，不保證是明天。
   *    後端取 `[今天+1, 今天+7]` 裡最早有資料的那天（`stats[0]`）——
   *    最新那批快照如果沒涵蓋到明天，這張卡顯示的就是別天。
   *    所以標題直接寫出日期，不要寫死「明天」。
   */
  const headLabel = (() => {
    if (!head) return '最近一天'
    return dayjs(head.stay_date).isSame(dayjs().add(1, 'day'), 'day')
      ? '明天'
      : head.stay_date.slice(5)      // MM-DD
  })()

  /**
   * ⚠️ 用**當前口徑**重算樣本不足的天數，不用後端的 `low_sample_days`。
   *    後端那個數字是稅前口徑算的（跟著 `is_low_sample`）。切到含稅口徑時
   *    兩者會對不起來 —— 表格裡每一列都沒有黃色驚嘆號，上面卻寫著
   *    「有 3 天樣本不足」，使用者會以為畫面壞了。
   */
  const lowSampleDays = (data?.next_7d ?? []).filter((s) => isLowSample(s, basis)).length

  // 折線圖資料：未來 7 天的指數
  const chartData = (data?.next_7d ?? []).map((s) => ({
    stay_date: s.stay_date.slice(5),          // MM-DD
    index: basis === 'pretax' ? s.index_pretax : s.index_gross,
    self: basis === 'pretax' ? s.self_pretax : s.self_gross,
    median: basis === 'pretax' ? s.median_pretax : s.median_gross,
    sample: sampleCountOf(s, basis),   // ⚠️ 當前口徑的家數，不是 s.sample_count
  }))

  const columns: ColumnsType<DailyStat> = [
    {
      // 入住日一律帶星期（共用 `StayDateLabel`）—— 飯店訂價看的是星期幾，
      // 只給日期的話使用者得自己心算。旺日（五／六）會加粗。
      title: '入住日', dataIndex: 'stay_date', width: 150, fixed: 'left',
      render: (v: string) => (
        <StayDateLabel date={v}
          onClick={() => navigate(`/compset/trend?stay_date=${v}`)} />
      ),
    },
    {
      title: '自己', width: 100, align: 'right',
      render: (_, r) => fmtMoney(basis === 'pretax' ? r.self_pretax : r.self_gross),
    },
    {
      title: '競品中位數', width: 110, align: 'right',
      render: (_, r) => fmtMoney(basis === 'pretax' ? r.median_pretax : r.median_gross),
    },
    {
      title: '競品區間', width: 150, align: 'right',
      render: (_, r) => {
        const lo = basis === 'pretax' ? r.min_pretax : r.min_gross
        const hi = basis === 'pretax' ? r.max_pretax : r.max_gross
        if (lo === null || hi === null) return <Text type="secondary">—</Text>
        return <Text type="secondary">{fmtMoney(lo)} 〜 {fmtMoney(hi)}</Text>
      },
    },
    {
      title: (
        <Tooltip title="自己 ÷ 競品中位數。n ＝ 進中位數的競品家數。">
          價格指數 <QuestionCircleOutlined style={{ color: '#999' }} />
        </Tooltip>
      ),
      width: 130, align: 'center',
      render: (_, r) => <IndexValue stat={r} basis={basis} compact />,
    },
    {
      title: (
        <Tooltip title="含稅價由低到高的名次（含自己）">
          名次 <QuestionCircleOutlined style={{ color: '#999' }} />
        </Tooltip>
      ),
      width: 90, align: 'center',
      render: (_, r) => <RankValue stat={r} />,
    },
    {
      // 家數 ＋ 簡稱。只給「2 家」不夠 —— 地板錨點賣完與天花板賣完意義相反。
      title: '滿房', width: 200, align: 'center',
      render: (_, r) => <SoldOutCell stat={r} hotels={data?.hotels ?? []} />,
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Space direction="vertical" size={0}>
            <Typography.Title level={4} style={{ margin: 0 }}>
              ★ 競品分析 Dashboard
            </Typography.Title>
            <Space size={4}>
              <Text type="secondary">{data?.subscriber?.name || '—'}</Text>
              {data?.snapshot_date && <Text type="secondary">｜</Text>}
              <SnapshotStamp snapshotDate={data?.snapshot_date}
                fetchedAt={data?.fetched_at} />
            </Space>
          </Space>
        </Col>
        <Col>
          <Space>
            <BasisSwitch value={basis} onChange={setBasis} />
            <a onClick={load}><ReloadOutlined /> 重新整理</a>
          </Space>
        </Col>
      </Row>

      {/* ⚠️ 警告與錯誤分開。這裡是黃色警告（資料品質），不是紅色錯誤（系統壞了）。 */}
      {(data?.warnings ?? []).length > 0 && (
        <Alert type="warning" showIcon style={{ marginBottom: 16 }}
          message="資料品質提醒"
          description={<ul style={{ margin: 0, paddingLeft: 18 }}>
            {data!.warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>} />
      )}

      {/* 配額用盡是硬停 —— 不會自動恢復，要有人手動加發，所以用 error 不用 warning */}
      {quota?.is_exhausted && (
        <Alert type="error" showIcon style={{ marginBottom: 16 }}
          message="本期抓取配額已用盡"
          description={`已用 ${quota.used} / ${quota.limit} 次。系統已停止抓取，`
            + `在下一期（${quota.period_start} 起算）之前不會有新資料。`
            + '需要立即恢復請找管理員在「訂閱與配額」手動加發。'} />
      )}

      <Spin spinning={loading}>
        {/* ── KPI ────────────────────────────────────────────────────── */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title={`${headLabel}的價格指數`}
                valueRender={() => <IndexValue stat={head} basis={basis} />} />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {head ? `入住日 ${head.stay_date}` : '尚無資料'}
              </Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title={`${headLabel}的名次`}
                valueRender={() => <RankValue stat={head} />} />
              <Text type="secondary" style={{ fontSize: 12 }}>由低到高，含自己</Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="未來 7 天有競品滿房"
                value={data?.sold_out_days ?? 0} suffix="天"
                valueStyle={{ color: (data?.sold_out_days ?? 0) > 0 ? '#cf1322' : undefined }} />
              <Text type="secondary" style={{ fontSize: 12 }}>競品賣完 ＝ 可往上試價</Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="本期配額"
                value={quota ? quota.used : 0}
                suffix={quota ? `/ ${quota.limit}` : ''} />
              {quota && (
                <Progress percent={Math.round(quota.usage_ratio * 100)} size="small"
                  status={quota.is_exhausted ? 'exception'
                    : quota.usage_ratio > 0.85 ? 'active' : 'normal'}
                  strokeColor={quota.usage_ratio > 0.85 ? '#faad14' : ACCENT} />
              )}
            </Card>
          </Col>
        </Row>

        {/* 樣本不足的天數：不是錯誤，但足以讓人誤判，要主動講 */}
        {lowSampleDays > 0 && (
          <Alert type="warning" showIcon style={{ marginBottom: 16 }}
            icon={<WarningOutlined />}
            message={`未來 7 天中有 ${lowSampleDays} 天樣本不足 3 家`
              + `（${basis === 'pretax' ? '稅前' : '含稅'}口徑）`}
            description="樣本太少時中位數會被單一家帶著跑，指數僅供參考，先不要據此調價。" />
        )}

        {/* ── 指數折線 ───────────────────────────────────────────────── */}
        <Card title="未來 7 天價格指數" style={{ marginBottom: 16 }}
          extra={<Text type="secondary" style={{ fontSize: 12 }}>
            1.00 ＝ 與競品中位數同價
          </Text>}>
          {chartData.length === 0
            ? <Empty description="尚無資料。請先到「抓取節奏設定」按一次「立即抓取」。" />
            : (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="stay_date" />
                  <YAxis domain={['auto', 'auto']} />
                  <ReferenceLine y={1} stroke="#999" strokeDasharray="4 4"
                    label={{ value: '與競品同價', position: 'right', fontSize: 11 }} />
                  <ReTooltip formatter={(v: any, name: string, p: any) => {
                    if (name === '價格指數') {
                      return [`${v?.toFixed?.(3) ?? v}（n=${p?.payload?.sample}）`, name]
                    }
                    return [fmtMoney(v), name]
                  }} />
                  <Line type="monotone" dataKey="index" name="價格指數"
                    stroke={BRAND} strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
        </Card>

        {/* ── 明細 ───────────────────────────────────────────────────── */}
        <Card title="未來 7 天明細"
          extra={<a onClick={() => navigate('/compset/matrix')}>
            價格矩陣 <ArrowRightOutlined />
          </a>}>
          <Table<DailyStat>
            rowKey="stay_date" size="small" pagination={false}
            columns={columns} dataSource={data?.next_7d ?? []}
            scroll={{ x: 950 }}
            locale={{ emptyText: <Empty description="尚無資料" /> }} />
          <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}>
            指數 ＝ 自己 ÷ 競品中位數（{basis === 'pretax' ? '稅前價' : '含稅價'}）。
            滿房的競品不計入中位數；<b>n</b> 是實際進中位數的競品家數。
          </Paragraph>
        </Card>
      </Spin>
    </div>
  )
}

export default CompsetDashboardPage
