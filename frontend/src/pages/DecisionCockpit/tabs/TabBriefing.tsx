/**
 * TAB H — 主管晨會摘要
 * Phase 6：規則式文字模板生成（無 AI API）
 *
 * 生成邏輯：
 *   1. 彙整各模組完成率 → 文字句型
 *   2. 逾期件數 > 閾值 → 警告句
 *   3. 費用彙整 → 費用句
 *   4. 未完成項目 → 提醒句
 * 輸出：純文字（適合貼到 LINE/Email）+ 一鍵複製
 */
import { useEffect, useState, useCallback } from 'react'
import {
  Button, Card, Col, Row, Spin, Typography, Space,
  Divider, Tag, message,
} from 'antd'
import {
  CopyOutlined, ReloadOutlined, CheckCircleOutlined,
  WarningOutlined, InfoCircleOutlined,
} from '@ant-design/icons'
import { fetchDashboard as fetchLuqun } from '@/api/luqunRepair'
import { fetchDashboard as fetchDazhi } from '@/api/dazhiRepair'
import { dashboardApi }                 from '@/api/dashboard'
import { fetchPMStats }                 from '@/api/periodicMaintenance'
import { fetchMallPMStats }             from '@/api/mallPeriodicMaintenance'
import type { DashboardData as LuqunData } from '@/types/luqunRepair'
import type { DashboardData as DazhiData  } from '@/types/dazhiRepair'
import type { DashboardKPI }                from '@/api/dashboard'
import type { PMStats }                     from '@/types/periodicMaintenance'
import { getTrafficLight, TRAFFIC_LIGHT_COLOR } from '../utils/healthScore'

const { Title, Text, Paragraph } = Typography

const T = {
  primary:   '#1B3A5C',
  accent:    '#4BA8E8',
  bg:        '#f0f4f8',
  textMuted: '#8c8c8c',
  success:   '#52c41a',
  warning:   '#faad14',
  danger:    '#ff4d4f',
}

interface TabBriefingProps {
  year: number; month: number; monthStr: string; refreshKey: number
}

interface BriefingData {
  loading: boolean
  luqun:   LuqunData | null
  dazhi:   DazhiData  | null
  dashKpi: DashboardKPI | null
  hotelPM: PMStats | null
  mallPM:  PMStats | null
}

// ── 規則式摘要生成器 ─────────────────────────────────────────────────────────
function generateBriefing(params: {
  monthStr: string
  year:     number
  month:    number
  luqun:    LuqunData | null
  dazhi:    DazhiData  | null
  dashKpi:  DashboardKPI | null
  hotelPM:  PMStats | null
  mallPM:   PMStats | null
}): string {
  const { monthStr, year, month, luqun, dazhi, dashKpi, hotelPM, mallPM } = params
  const lines: string[] = []
  const now = new Date().toLocaleDateString('zh-TW', { year: 'numeric', month: 'long', day: 'numeric' })

  lines.push(`【主管晨會摘要】${now}`)
  lines.push(`查詢期間：${monthStr}（${year} 年 ${month} 月）`)
  lines.push('')

  // ── 一、工務報修狀況 ─────────────────────────────────────────────────────
  lines.push('▌ 一、工務報修狀況')
  const lk = luqun?.kpi
  const dk = dazhi?.kpi
  if (lk) {
    const rate = lk.total > 0 ? Math.round((lk.completed / lk.total) * 100) : null
    const status = rate === null ? '無資料' : rate >= 80 ? '正常' : rate >= 60 ? '需關注' : '警告'
    lines.push(`  • 樂群工務報修：本月 ${lk.total} 件，已完成 ${lk.completed} 件，完成率 ${rate ?? '—'}%（${status}）`)
    if (lk.uncompleted > 0) lines.push(`    ⚠ 未完成 ${lk.uncompleted} 件，待驗收 ${lk.pending_verify} 件，請督促跟進`)
    if (lk.month_total_fee > 0) lines.push(`    本月費用：NT$ ${lk.month_total_fee.toLocaleString()}`)
  } else {
    lines.push('  • 樂群工務報修：資料準備中')
  }
  if (dk) {
    const rate = dk.total > 0 ? Math.round((dk.completed / dk.total) * 100) : null
    const status = rate === null ? '無資料' : rate >= 80 ? '正常' : rate >= 60 ? '需關注' : '警告'
    lines.push(`  • 大直工務部：本月 ${dk.total} 件，已完成 ${dk.completed} 件，完成率 ${rate ?? '—'}%（${status}）`)
    if (dk.uncompleted > 0) lines.push(`    ⚠ 未完成 ${dk.uncompleted} 件，待驗收 ${dk.pending_verify} 件`)
    if (dk.month_total_fee > 0) lines.push(`    本月費用：NT$ ${dk.month_total_fee.toLocaleString()}`)
  } else {
    lines.push('  • 大直工務部：資料準備中')
  }
  if (lk && dk) {
    const totalFee = lk.month_total_fee + dk.month_total_fee
    lines.push(`  ▸ 工務費用合計：NT$ ${totalFee.toLocaleString()}`)
  }
  lines.push('')

  // ── 二、客房保養狀況 ─────────────────────────────────────────────────────
  lines.push('▌ 二、客房保養狀況')
  if (dashKpi?.room_maintenance) {
    const rm = dashKpi.room_maintenance
    const status = rm.completion_rate >= 80 ? '正常' : rm.completion_rate >= 60 ? '需關注' : '警告'
    lines.push(`  • 客房保養：完成率 ${Math.round(rm.completion_rate)}%（${status}）`)
    if (rm.total_incomplete > 0)
      lines.push(`    ⚠ 尚有 ${rm.total_incomplete} 項未完成，請確認重點房型`)
    else
      lines.push(`    ✓ 全部保養項目均已完成`)
  } else {
    lines.push('  • 客房保養：資料準備中')
  }
  lines.push('')

  // ── 三、飯店週期保養 ─────────────────────────────────────────────────────
  lines.push('▌ 三、飯店週期保養')
  if (hotelPM?.current_kpi) {
    const k = hotelPM.current_kpi
    const status = k.completion_rate >= 80 ? '正常' : k.completion_rate >= 60 ? '需關注' : '警告'
    lines.push(`  • 週期保養：${k.total} 項，已完成 ${k.completed} 項，完成率 ${Math.round(k.completion_rate)}%（${status}）`)
    if (k.overdue > 0) lines.push(`    ⚠ 逾期 ${k.overdue} 項，請優先安排`)
    lines.push(`    工時：預估 ${Math.round(k.planned_minutes / 60)} hr，實際 ${Math.round(k.actual_minutes / 60)} hr`)
  } else {
    lines.push('  • 飯店週期保養：資料準備中')
  }
  lines.push('')

  // ── 四、商場例行維護 ─────────────────────────────────────────────────────
  lines.push('▌ 四、商場例行維護')
  if (mallPM?.current_kpi) {
    const k = mallPM.current_kpi
    const status = k.completion_rate >= 80 ? '正常' : k.completion_rate >= 60 ? '需關注' : '警告'
    lines.push(`  • 商場例行維護：${k.total} 項，已完成 ${k.completed} 項，完成率 ${Math.round(k.completion_rate)}%（${status}）`)
    if (k.overdue > 0) lines.push(`    ⚠ 逾期 ${k.overdue} 項，請優先安排`)
  } else {
    lines.push('  • 商場例行維護：資料準備中')
  }
  lines.push('')

  // ── 五、需主管特別關注 ───────────────────────────────────────────────────
  lines.push('▌ 五、需主管特別關注')
  const alerts: string[] = []
  const totalUncomp = (lk?.uncompleted ?? 0) + (dk?.uncompleted ?? 0)
  if (totalUncomp >= 10) alerts.push(`工務未完成件數偏高（${totalUncomp} 件），請督促各單位跟進結案`)
  if ((lk?.pending_verify ?? 0) + (dk?.pending_verify ?? 0) > 0)
    alerts.push(`工務待驗收 ${(lk?.pending_verify ?? 0) + (dk?.pending_verify ?? 0)} 件，請安排驗收確認`)
  if (dashKpi?.room_maintenance && dashKpi.room_maintenance.total_incomplete > 10)
    alerts.push(`客房保養未完成項目較多（${dashKpi.room_maintenance.total_incomplete} 項），建議本週加強巡查`)
  if (hotelPM?.current_kpi && hotelPM.current_kpi.overdue > 0)
    alerts.push(`飯店週期保養逾期 ${hotelPM.current_kpi.overdue} 項，請安排補做`)
  if (mallPM?.current_kpi && mallPM.current_kpi.overdue > 0)
    alerts.push(`商場例行維護逾期 ${mallPM.current_kpi.overdue} 項，請安排補做`)

  if (alerts.length === 0) {
    lines.push('  ✓ 本期各指標均在正常範圍，無需特別關注')
  } else {
    alerts.forEach(a => lines.push(`  ⚠ ${a}`))
  }
  lines.push('')
  lines.push(`── 本摘要由系統規則自動生成，僅供參考，請主管確認後使用 ──`)

  return lines.join('\n')
}

// ════════════════════════════════════════════════════════════════════════════
// 主元件
// ════════════════════════════════════════════════════════════════════════════
export default function TabBriefing({ year, month, monthStr, refreshKey }: TabBriefingProps) {
  const [st, setSt] = useState<BriefingData>({
    loading: true, luqun: null, dazhi: null, dashKpi: null, hotelPM: null, mallPM: null,
  })
  const [copied, setCopied] = useState(false)

  const load = useCallback(async () => {
    setSt(s => ({ ...s, loading: true }))
    const [r1, r2, r3, r4, r5] = await Promise.allSettled([
      fetchLuqun(year, month),
      fetchDazhi(year, month),
      dashboardApi.kpi(),
      fetchPMStats(String(year), month),
      fetchMallPMStats(String(year), month),
    ])
    setSt({
      loading: false,
      luqun:   r1.status === 'fulfilled' ? r1.value       : null,
      dazhi:   r2.status === 'fulfilled' ? r2.value       : null,
      dashKpi: r3.status === 'fulfilled' ? r3.value.data  : null,
      hotelPM: r4.status === 'fulfilled' ? r4.value       : null,
      mallPM:  r5.status === 'fulfilled' ? r5.value       : null,
    })
  }, [year, month, refreshKey]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  const { loading, luqun, dazhi, dashKpi, hotelPM, mallPM } = st

  const briefingText = loading ? '' : generateBriefing({ monthStr, year, month, luqun, dazhi, dashKpi, hotelPM, mallPM })

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(briefingText)
      setCopied(true)
      message.success('已複製到剪貼簿')
      setTimeout(() => setCopied(false), 2000)
    } catch {
      message.error('複製失敗，請手動選取文字')
    }
  }

  // 計算有資料的模組數
  const readyCount = [luqun, dazhi, dashKpi, hotelPM, mallPM].filter(Boolean).length

  return (
    <div style={{ paddingBottom: 24 }}>
      <Card
        style={{ borderRadius: 8 }}
        bodyStyle={{ padding: '20px 24px' }}
        title={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Space>
              <Text strong style={{ color: T.primary }}>H. 主管晨會摘要 — {monthStr}</Text>
              <Tag color="blue">{readyCount}/5 個來源就緒</Tag>
            </Space>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                size="small"
                onClick={load}
                loading={loading}
              >
                重新生成
              </Button>
              <Button
                type="primary"
                icon={copied ? <CheckCircleOutlined /> : <CopyOutlined />}
                size="small"
                onClick={handleCopy}
                disabled={loading}
                style={{ background: copied ? T.success : undefined }}
              >
                {copied ? '已複製' : '一鍵複製'}
              </Button>
            </Space>
          </div>
        }
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
        ) : (
          <>
            {/* 摘要文字區 */}
            <div
              style={{
                background:    T.bg,
                borderRadius:  8,
                padding:       '16px 20px',
                fontFamily:    'monospace',
                fontSize:      13,
                lineHeight:    1.8,
                whiteSpace:    'pre-wrap',
                userSelect:    'text',
                border:        '1px solid #d9d9d9',
                maxHeight:     520,
                overflowY:     'auto',
                color:         T.primary,
              }}
            >
              {briefingText}
            </div>

            <Divider style={{ margin: '12px 0' }} />
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Tag icon={<InfoCircleOutlined />} color="blue">規則式生成，無 AI</Tag>
              <Tag icon={<InfoCircleOutlined />} color="default">適合貼到 LINE 或 Email</Tag>
              {readyCount < 5 && (
                <Tag icon={<WarningOutlined />} color="warning">
                  {5 - readyCount} 個模組資料未就緒，摘要可能不完整
                </Tag>
              )}
            </div>
          </>
        )}
      </Card>
    </div>
  )
}
