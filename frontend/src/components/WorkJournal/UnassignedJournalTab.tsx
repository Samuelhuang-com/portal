/**
 * 未指定工作日誌 TAB（LuqunRepair / DazhiRepair Dashboard 共用）
 *
 * 顯示工作日誌中人員為「未指定」的工單，依 venue prop 過濾歸屬：
 *  - LuqunRepair（商場工務報修）→ venue="mall"
 *  - DazhiRepair（飯店工務報修）→ venue="hotel"
 * 歸屬判斷與工作日誌「飯/商」標籤一致（後端 _row_venue）。
 * 資料來源：GET /api/v1/work-journal/daily|range?person_scope=unassigned&venue=...
 *
 * 查詢模式：單日 / 區間 / 整月（不含「人員」模式 — 此 TAB 只有「未指定」一人，無篩選意義）。
 * 明細 Drawer / 表格渲染與 ExecWorkDashboard 工作日誌 TAB 共用 @/components/WorkJournal/shared。
 */
import { useState, useCallback } from 'react'
import {
  Typography, Tag, Collapse, Segmented, DatePicker, Select,
  Spin, Space, Button, Card,
} from 'antd'
import { ReloadOutlined, FileExcelOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'

import {
  fetchWorkJournalDaily, fetchWorkJournalRange,
  getJournalExcelUrl,
  type WorkJournalDaily, type WorkJournalRange, type JournalVenue,
} from '@/api/workJournal'
import { CATEGORY_TAG_COLORS } from '@/api/workCategoryAnalysis'
import { downloadFile } from '@/api/downloadFile'
import { CAT_COLS, DayPersonCollapse } from '@/components/WorkJournal/shared'

const { Text } = Typography

type UnassignedMode = 'single' | 'range' | 'month'

export default function UnassignedJournalTab({ venue }: { venue: JournalVenue }) {
  const [mode,       setMode]       = useState<UnassignedMode>('single')
  const [year,       setYear]       = useState<number>(dayjs().year())
  const [month,      setMonth]      = useState<number>(dayjs().month() + 1)
  const [day,        setDay]        = useState<number>(dayjs().date())
  const [rangeDates, setRangeDates] = useState<[Dayjs, Dayjs] | null>(null)
  const [monthDate,  setMonthDate]  = useState<Dayjs | null>(dayjs())
  const [singleData, setSingleData] = useState<WorkJournalDaily | null>(null)
  const [rangeData,  setRangeData]  = useState<WorkJournalRange | null>(null)
  const [loading,    setLoading]    = useState(false)
  const [globalCollapsed, setGlobalCollapsed] = useState(false)
  const [dateActiveKeys,  setDateActiveKeys]  = useState<string[]>([])

  const daysInMonth = dayjs(`${year}-${String(month).padStart(2, '0')}-01`).daysInMonth()
  const dayOptions  = Array.from({ length: daysInMonth }, (_, i) => ({ label: `${i + 1} 日`, value: i + 1 }))

  const handleLoad = useCallback(async () => {
    setLoading(true)
    try {
      setGlobalCollapsed(false)

      if (mode === 'single') {
        const journal = await fetchWorkJournalDaily(year, month, day, 'unassigned', venue)
        setSingleData(journal)
        setRangeData(null)
        setDateActiveKeys([])

      } else if (mode === 'range' && rangeDates) {
        const from = rangeDates[0].format('YYYY-MM-DD')
        const to   = rangeDates[1].format('YYYY-MM-DD')
        const journal = await fetchWorkJournalRange(from, to, 'unassigned', venue)
        setRangeData(journal)
        setSingleData(null)
        setDateActiveKeys(journal.days.map((_, i) => `day-${i}`))

      } else if (mode === 'month' && monthDate) {
        const from = monthDate.startOf('month').format('YYYY-MM-DD')
        const to   = monthDate.endOf('month').format('YYYY-MM-DD')
        const journal = await fetchWorkJournalRange(from, to, 'unassigned', venue)
        setRangeData(journal)
        setSingleData(null)
        setDateActiveKeys(journal.days.map((_, i) => `day-${i}`))
      }
    } catch {
      setSingleData(null)
      setRangeData(null)
    } finally {
      setLoading(false)
    }
  }, [mode, year, month, day, rangeDates, monthDate, venue])

  // 日期 pickers
  const renderPickers = () => {
    if (mode === 'single') return (
      <Space wrap>
        <Text type="secondary" style={{ fontSize: 15 }}>查詢日期：</Text>
        <Select value={year} onChange={v => setYear(v)} style={{ width: 90 }}
          options={Array.from({ length: 3 }, (_, i) => { const y = dayjs().year() - i; return { label: `${y} 年`, value: y } })} />
        <Select value={month} onChange={v => { setMonth(v); if (day > dayjs(`${year}-${String(v).padStart(2, '0')}-01`).daysInMonth()) setDay(1) }}
          style={{ width: 80 }}
          options={Array.from({ length: 12 }, (_, i) => ({ label: `${i + 1} 月`, value: i + 1 }))} />
        <Select value={day} onChange={v => setDay(v)} style={{ width: 80 }} options={dayOptions} />
      </Space>
    )
    if (mode === 'range') return (
      <Space wrap>
        <Text type="secondary" style={{ fontSize: 15 }}>查詢區間（最多 31 天）：</Text>
        <DatePicker.RangePicker
          value={rangeDates}
          onChange={v => setRangeDates(v as [Dayjs, Dayjs] | null)}
          format="YYYY/MM/DD"
          style={{ width: 260 }}
          disabledDate={cur => cur && cur > dayjs().endOf('day')}
        />
      </Space>
    )
    // month
    return (
      <Space wrap>
        <Text type="secondary" style={{ fontSize: 15 }}>查詢月份：</Text>
        <DatePicker
          picker="month"
          value={monthDate}
          onChange={v => setMonthDate(v)}
          format="YYYY 年 MM 月"
          style={{ width: 150 }}
          disabledDate={cur => cur && cur > dayjs().endOf('month')}
        />
      </Space>
    )
  }

  // 結果摘要文字
  const renderSummary = () => {
    if (singleData) return (
      <Text type="secondary" style={{ fontSize: 14 }}>
        {singleData.date} ｜ 未指定共 <Text strong>{singleData.total_rows}</Text> 筆
      </Text>
    )
    if (rangeData) return (
      <Text type="secondary" style={{ fontSize: 14 }}>
        {rangeData.date_from} ～ {rangeData.date_to} ｜ 未指定共 <Text strong>{rangeData.total_rows}</Text> 筆（{rangeData.days.length} 天）
      </Text>
    )
    return null
  }

  // 結果區域
  const renderResult = () => {
    if (loading) return (
      <div style={{ textAlign: 'center', paddingTop: 60 }}>
        <Spin tip="載入未指定工作日誌…" />
      </div>
    )

    // 單日
    if (singleData) {
      if (singleData.total_rows === 0) return (
        <div style={{ textAlign: 'center', paddingTop: 40, color: '#aaa', fontSize: 16 }}>
          {singleData.date} 無「未指定」工作記錄
        </div>
      )
      return (
        <DayPersonCollapse
          persons={singleData.persons}
          collapsed={globalCollapsed}
        />
      )
    }

    // 區間 / 整月
    if (rangeData) {
      if (rangeData.total_rows === 0) return (
        <div style={{ textAlign: 'center', paddingTop: 40, color: '#aaa', fontSize: 16 }}>
          查詢區間內無「未指定」工作記錄
        </div>
      )
      const dateItems = rangeData.days.map((daily, di) => {
        const totalWH = daily.persons.reduce(
          (acc, p) => acc + p.rows.reduce((a, r) => a + (r.work_min ?? 0), 0), 0
        )
        const allRows = daily.persons.flatMap(p => p.rows)
        return {
          key: `day-${di}`,
          label: (
            <Space wrap style={{ rowGap: 4 }}>
              <Text strong style={{ fontSize: 16, color: '#1B3A5C' }}>{daily.date}</Text>
              <Tag color="blue">{daily.total_rows} 筆</Tag>
              {totalWH > 0 && <Tag color="geekblue">{totalWH} min</Tag>}
              {CAT_COLS.map(cat => {
                const cnt = allRows.filter(r => r.category === cat).length
                return cnt > 0 ? (
                  <Tag key={cat} color={CATEGORY_TAG_COLORS[cat] ?? 'default'}
                       style={{ fontSize: 13, margin: 0 }}>{cat} {cnt}</Tag>
                ) : null
              })}
            </Space>
          ),
          children: (
            <DayPersonCollapse persons={daily.persons} />
          ),
        }
      })
      return (
        <Collapse
          activeKey={dateActiveKeys}
          onChange={keys => setDateActiveKeys(keys as string[])}
          items={dateItems}
          style={{ background: '#f0f4f8' }}
        />
      )
    }

    return (
      <div style={{ textAlign: 'center', paddingTop: 40, color: '#aaa', fontSize: 16 }}>
        請選擇日期後按下「查詢」
      </div>
    )
  }

  return (
    <div style={{ paddingBottom: 24 }}>
      {/* 模式切換 */}
      <div style={{ marginBottom: 12 }}>
        <Segmented
          value={mode}
          onChange={v => {
            setMode(v as UnassignedMode)
            setSingleData(null); setRangeData(null)
          }}
          options={[
            { label: '單日', value: 'single' },
            { label: '區間', value: 'range' },
            { label: '整月', value: 'month' },
          ]}
        />
      </div>

      {/* 日期選擇器 + 查詢按鈕 */}
      <Card size="small" style={{ marginBottom: 12, background: '#fafafa' }}>
        <Space wrap>
          {renderPickers()}
          <Button type="primary" icon={<ReloadOutlined />} onClick={handleLoad} loading={loading}>
            查詢
          </Button>
          {/* 縮合/展開按鈕：有資料才顯示 */}
          {(singleData || rangeData) && (
            <Button
              size="small"
              onClick={() => {
                const next = !globalCollapsed
                setGlobalCollapsed(next)
                if (rangeData) {
                  setDateActiveKeys(next ? [] : rangeData.days.map((_, i) => `day-${i}`))
                }
              }}
            >
              {globalCollapsed ? '全部展開' : '全部縮合'}
            </Button>
          )}
          {/* Excel 匯出按鈕：有資料才顯示 */}
          {(singleData || rangeData) && (() => {
            let from = '', to = ''
            if (mode === 'single' && singleData) {
              const d = singleData.date.replace(/\//g, '-')
              from = d; to = d
            } else if (rangeData) {
              from = rangeData.date_from; to = rangeData.date_to
            }
            if (!from) return null
            return (
              <Button
                icon={<FileExcelOutlined />}
                style={{ color: '#52c41a', borderColor: '#52c41a' }}
                onClick={() => downloadFile(
                  getJournalExcelUrl(from, to, undefined, 'unassigned', venue),
                  `未指定工作日誌_${venue === 'hotel' ? '飯店' : '商場'}_${from}_${to}.xlsx`,
                )}
              >
                匯出 Excel
              </Button>
            )
          })()}
          {renderSummary()}
        </Space>
      </Card>

      {/* 結果 */}
      {renderResult()}
    </div>
  )
}
