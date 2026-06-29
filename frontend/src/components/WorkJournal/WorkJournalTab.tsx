/**
 * WorkJournalTab — 工作日誌 TAB 元件（獨立可重用）
 *
 * 自 ExecWorkDashboard/index.tsx 抽出，供以下頁面共用：
 *  - ExecWorkDashboard  工作日誌 TAB（venue="all"，預設值）
 *  - HotelMgmtDashboard 工作日誌 TAB（venue="hotel"）
 *  - MallMgmtDashboard  工作日誌 TAB（venue="mall"）
 *
 * Props:
 *  - venue?:         'all' | 'hotel' | 'mall'，預設 'all'
 *  - onStatsChange?: 查詢後回傳各類別統計，供上層摘要卡片使用
 */
import React, { useState, useCallback, useEffect } from 'react'
import {
  Segmented, DatePicker, Select, Space, Button,
  Collapse, Typography, Tag, Spin, Card,
} from 'antd'
import {
  ReloadOutlined, UserOutlined, UserDeleteOutlined, FileExcelOutlined,
} from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-tw'

import {
  fetchWorkJournalDaily, fetchWorkJournalRange, getJournalExcelUrl,
  type WorkJournalDaily, type WorkJournalRange, type JournalVenue,
} from '@/api/workJournal'
import { fetchShiftsRange, type ShiftsRangeData } from '@/api/schedule'
import {
  CAT_COLS, DayPersonCollapse,
  isHotelRow as _isHotelRow, type JournalMode,
} from '@/components/WorkJournal/shared'
import { downloadFile } from '@/api/downloadFile'
import { CATEGORY_TAG_COLORS } from '@/api/workCategoryAnalysis'

dayjs.extend(relativeTime)
dayjs.locale('zh-tw')

const { Text } = Typography

// ── 工作日誌統計型別（供上層摘要卡片使用）────────────────────────────────────
export interface WJVenueStat { cases: number; hours: number }
export interface WJCatStat {
  cases: number; hours: number
  hotel: WJVenueStat
  mall:  WJVenueStat
}
export type WJStats = Record<string, WJCatStat>

export function _computeWJStats(days: WorkJournalDaily[]): WJStats {
  const stats: WJStats = {}
  const _empty = (): WJCatStat => ({
    cases: 0, hours: 0,
    hotel: { cases: 0, hours: 0 },
    mall:  { cases: 0, hours: 0 },
  })
  days.forEach(d => d.persons.forEach(p => p.rows.forEach(r => {
    if (!stats[r.category]) stats[r.category] = _empty()
    const s = stats[r.category]
    const min = (r.work_min ?? 0) / 60
    s.cases++
    s.hours += min
    const venue = _isHotelRow(r) ? s.hotel : s.mall
    venue.cases++
    venue.hours += min
  })))
  Object.keys(stats).forEach(k => {
    stats[k].hours = Math.round(stats[k].hours * 10) / 10
    stats[k].hotel.hours = Math.round(stats[k].hotel.hours * 10) / 10
    stats[k].mall.hours  = Math.round(stats[k].mall.hours  * 10) / 10
  })
  return stats
}

// ── WorkJournalTab 主元件 ─────────────────────────────────────────────────────
interface WorkJournalTabProps {
  /** 場所篩選：'all'（預設）| 'hotel' | 'mall' */
  venue?: JournalVenue
  /** 查詢後回傳各類別統計，供上層摘要卡片使用 */
  onStatsChange?: (s: WJStats) => void
}

export default function WorkJournalTab({
  venue = 'all',
  onStatsChange,
}: WorkJournalTabProps) {
  const [mode,      setMode]      = useState<JournalMode>('single')
  const [year,      setYear]      = useState<number>(dayjs().year())
  const [month,     setMonth]     = useState<number>(dayjs().month() + 1)
  const [day,       setDay]       = useState<number>(dayjs().date())
  const [rangeDates, setRangeDates] = useState<[Dayjs, Dayjs] | null>(null)
  const [monthDate,  setMonthDate]  = useState<Dayjs | null>(dayjs())
  const [singleData,      setSingleData]      = useState<WorkJournalDaily | null>(null)
  const [rangeData,       setRangeData]       = useState<WorkJournalRange | null>(null)
  const [shiftMapByDate,  setShiftMapByDate]  = useState<ShiftsRangeData>({})
  const [loading,         setLoading]         = useState(false)
  const [personFilter,     setPersonFilter]     = useState<string>('')
  const [personList,       setPersonList]       = useState<string[]>([])
  const [personSubMode,    setPersonSubMode]    = useState<'range'|'month'>('month')
  const [personRangeDates, setPersonRangeDates] = useState<[Dayjs, Dayjs] | null>(null)
  const [personMonthDate,  setPersonMonthDate]  = useState<Dayjs | null>(dayjs())
  const [globalCollapsed,  setGlobalCollapsed]  = useState(false)
  const [dateActiveKeys,   setDateActiveKeys]   = useState<string[]>([])
  // 「未指定」模式的子模式（單日/區間/整月）
  const [unSubMode, setUnSubMode] = useState<'single'|'range'|'month'>('single')

  const daysInMonth = dayjs(`${year}-${String(month).padStart(2,'0')}-01`).daysInMonth()
  const dayOptions  = Array.from({ length: daysInMonth }, (_, i) => ({ label: `${i + 1} 日`, value: i + 1 }))

  const handleLoad = useCallback(async () => {
    setLoading(true)
    try {
      setGlobalCollapsed(false)

      if (mode === 'single') {
        const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
        const [journal, shifts] = await Promise.all([
          fetchWorkJournalDaily(year, month, day, 'named', venue),
          fetchShiftsRange(dateStr, dateStr).catch(() => ({} as ShiftsRangeData)),
        ])
        setSingleData(journal)
        setRangeData(null)
        setShiftMapByDate(shifts)
        setDateActiveKeys([])

      } else if (mode === 'range' && rangeDates) {
        const from = rangeDates[0].format('YYYY-MM-DD')
        const to   = rangeDates[1].format('YYYY-MM-DD')
        const [journal, shifts] = await Promise.all([
          fetchWorkJournalRange(from, to, 'named', venue),
          fetchShiftsRange(from, to).catch(() => ({} as ShiftsRangeData)),
        ])
        setRangeData(journal)
        setSingleData(null)
        setShiftMapByDate(shifts)
        setDateActiveKeys(journal.days.map((_, i) => `day-${i}`))
        onStatsChange?.(_computeWJStats(journal.days))

      } else if (mode === 'month' && monthDate) {
        const from = monthDate.startOf('month').format('YYYY-MM-DD')
        const to   = monthDate.endOf('month').format('YYYY-MM-DD')
        const [journal, shifts] = await Promise.all([
          fetchWorkJournalRange(from, to, 'named', venue),
          fetchShiftsRange(from, to).catch(() => ({} as ShiftsRangeData)),
        ])
        setRangeData(journal)
        setSingleData(null)
        setShiftMapByDate(shifts)
        setDateActiveKeys(journal.days.map((_, i) => `day-${i}`))
        onStatsChange?.(_computeWJStats(journal.days))

      } else if (mode === 'person') {
        let from = '', to = ''
        if (personSubMode === 'range' && personRangeDates) {
          from = personRangeDates[0].format('YYYY-MM-DD')
          to   = personRangeDates[1].format('YYYY-MM-DD')
        } else if (personSubMode === 'month' && personMonthDate) {
          from = personMonthDate.startOf('month').format('YYYY-MM-DD')
          to   = personMonthDate.endOf('month').format('YYYY-MM-DD')
        }
        if (!from) return
        const [journal, shifts] = await Promise.all([
          fetchWorkJournalRange(from, to, 'named', venue),
          fetchShiftsRange(from, to).catch(() => ({} as ShiftsRangeData)),
        ])
        setRangeData(journal)
        setSingleData(null)
        setShiftMapByDate(shifts)
        setDateActiveKeys(journal.days.map((_, i) => `pday-${i}`))
        onStatsChange?.(_computeWJStats(journal.days))
        const names: string[] = []
        const seen = new Set<string>()
        journal.days.forEach(dy => dy.persons.forEach(p => {
          if (!seen.has(p.person)) { names.push(p.person); seen.add(p.person) }
        }))
        setPersonList(names)
        if (names.length > 0 && !names.includes(personFilter)) setPersonFilter(names[0])

      } else if (mode === 'unassigned') {
        if (unSubMode === 'single') {
          const journal = await fetchWorkJournalDaily(year, month, day, 'unassigned', venue)
          setSingleData(journal)
          setRangeData(null)
          setShiftMapByDate({})
          setDateActiveKeys([])
        } else {
          let from = '', to = ''
          if (unSubMode === 'range' && rangeDates) {
            from = rangeDates[0].format('YYYY-MM-DD')
            to   = rangeDates[1].format('YYYY-MM-DD')
          } else if (unSubMode === 'month' && monthDate) {
            from = monthDate.startOf('month').format('YYYY-MM-DD')
            to   = monthDate.endOf('month').format('YYYY-MM-DD')
          }
          if (!from) return
          const journal = await fetchWorkJournalRange(from, to, 'unassigned', venue)
          setRangeData(journal)
          setSingleData(null)
          setShiftMapByDate({})
          setDateActiveKeys(journal.days.map((_, i) => `day-${i}`))
        }
      }
    } catch {
      setSingleData(null)
      setRangeData(null)
      setShiftMapByDate({})
    } finally {
      setLoading(false)
    }
  }, [mode, year, month, day, rangeDates, monthDate, personSubMode, personRangeDates, personMonthDate, personFilter, unSubMode, venue])

  // 掛載時自動載入當月份統計，供上方摘要卡片立即顯示；不觸碰表格狀態
  useEffect(() => {
    const from = dayjs().startOf('month').format('YYYY-MM-DD')
    const to   = dayjs().format('YYYY-MM-DD')
    fetchWorkJournalRange(from, to, 'named', venue)
      .then(j => onStatsChange?.(_computeWJStats(j.days)))
      .catch(() => {})
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 日期 pickers
  const renderPickers = () => {
    const effMode = mode === 'unassigned' ? unSubMode : mode
    const unSubSeg = mode === 'unassigned' ? (
      <Segmented
        size="small"
        value={unSubMode}
        onChange={v => { setUnSubMode(v as 'single'|'range'|'month'); setSingleData(null); setRangeData(null) }}
        options={[
          { label: '單日', value: 'single' },
          { label: '區間', value: 'range' },
          { label: '整月', value: 'month' },
        ]}
      />
    ) : null
    if (effMode === 'single') return (
      <Space wrap>
        {unSubSeg}
        <Text type="secondary" style={{ fontSize: 15 }}>查詢日期：</Text>
        <Select value={year} onChange={v => setYear(v)} style={{ width: 90 }}
          options={Array.from({ length: 3 }, (_, i) => { const y = dayjs().year() - i; return { label: `${y} 年`, value: y } })} />
        <Select value={month} onChange={v => { setMonth(v); if (day > dayjs(`${year}-${String(v).padStart(2,'0')}-01`).daysInMonth()) setDay(1) }}
          style={{ width: 80 }}
          options={Array.from({ length: 12 }, (_, i) => ({ label: `${i + 1} 月`, value: i + 1 }))} />
        <Select value={day} onChange={v => setDay(v)} style={{ width: 80 }} options={dayOptions} />
      </Space>
    )
    if (effMode === 'range') return (
      <Space wrap>
        {unSubSeg}
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
    if (effMode === 'month') return (
      <Space wrap>
        {unSubSeg}
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
    // person mode
    return (
      <Space wrap>
        <Segmented
          size="small"
          value={personSubMode}
          onChange={v => { setPersonSubMode(v as 'range'|'month'); setRangeData(null); setPersonList([]) }}
          options={[{ label: '整月', value: 'month' }, { label: '區間', value: 'range' }]}
        />
        {personSubMode === 'month' ? (
          <DatePicker
            picker="month"
            value={personMonthDate}
            onChange={v => setPersonMonthDate(v)}
            format="YYYY 年 MM 月"
            style={{ width: 150 }}
            disabledDate={cur => cur && cur > dayjs().endOf('month')}
          />
        ) : (
          <DatePicker.RangePicker
            value={personRangeDates}
            onChange={v => setPersonRangeDates(v as [Dayjs, Dayjs] | null)}
            format="YYYY/MM/DD"
            style={{ width: 260 }}
            disabledDate={cur => cur && cur > dayjs().endOf('day')}
          />
        )}
        {personList.length > 0 && (
          <Select
            value={personFilter}
            onChange={v => setPersonFilter(v)}
            style={{ width: 120 }}
            placeholder="選擇人員"
            options={personList.map(p => ({ label: p, value: p }))}
            suffixIcon={<UserOutlined />}
          />
        )}
      </Space>
    )
  }

  // 結果摘要文字
  const renderSummary = () => {
    if (singleData) return (
      <Text type="secondary" style={{ fontSize: 14 }}>
        {singleData.date} ｜ 共 <Text strong>{singleData.total_rows}</Text> 筆
      </Text>
    )
    if (rangeData && mode !== 'person') return (
      <Text type="secondary" style={{ fontSize: 14 }}>
        {rangeData.date_from} ～ {rangeData.date_to} ｜ 共 <Text strong>{rangeData.total_rows}</Text> 筆（{rangeData.days.length} 天）
      </Text>
    )
    if (rangeData && mode === 'person' && personFilter) {
      const personRows = rangeData.days.reduce((acc, d) => {
        const p = d.persons.find(p => p.person === personFilter)
        return acc + (p?.rows.length ?? 0)
      }, 0)
      return (
        <Text type="secondary" style={{ fontSize: 14 }}>
          <UserOutlined style={{ marginRight: 4 }} /><Text strong>{personFilter}</Text>
          　{rangeData.date_from} ～ {rangeData.date_to} ｜ 共 <Text strong>{personRows}</Text> 筆（{rangeData.days.length} 天）
        </Text>
      )
    }
    return null
  }

  // 結果區域
  const renderResult = () => {
    if (loading) return (
      <div style={{ textAlign: 'center', paddingTop: 60 }}>
        <Spin tip="載入工作日誌…" />
      </div>
    )

    // 單日
    if (singleData) {
      if (singleData.total_rows === 0) return (
        <div style={{ textAlign: 'center', paddingTop: 40, color: '#aaa', fontSize: 16 }}>
          {singleData.date} 無工作記錄
        </div>
      )
      return (
        <DayPersonCollapse
          persons={singleData.persons}
          collapsed={globalCollapsed}
          shiftMap={shiftMapByDate[singleData.date.replace(/\//g, '-')]}
        />
      )
    }

    // 人員模式
    if (mode === 'person' && rangeData) {
      if (!personFilter) return (
        <div style={{ textAlign: 'center', paddingTop: 40, color: '#aaa', fontSize: 16 }}>
          請選擇人員後按下「查詢」
        </div>
      )
      const filteredDays = rangeData.days
        .map(daily => ({
          ...daily,
          persons: daily.persons.filter(p => p.person === personFilter),
        }))
        .filter(daily => daily.persons.length > 0)

      if (filteredDays.length === 0) return (
        <div style={{ textAlign: 'center', paddingTop: 40, color: '#aaa', fontSize: 16 }}>
          {personFilter} 在此區間內無工作記錄
        </div>
      )
      const personDateItems = filteredDays.map((daily, di) => {
        const personRows = daily.persons[0]?.rows ?? []
        const dayMin = personRows.reduce((a, r) => a + (r.work_min ?? 0), 0)
        const rowCount = personRows.length
        return {
          key: `pday-${di}`,
          label: (
            <Space wrap style={{ rowGap: 4 }}>
              <Text strong style={{ fontSize: 16, color: '#1B3A5C' }}>{daily.date}</Text>
              <Tag color="blue">{rowCount} 項</Tag>
              {dayMin > 0 && <Tag color="geekblue">{dayMin} min</Tag>}
              {CAT_COLS.map(cat => {
                const cnt = personRows.filter(r => r.category === cat).length
                return cnt > 0 ? (
                  <Tag key={cat} color={CATEGORY_TAG_COLORS[cat] ?? 'default'}
                       style={{ fontSize: 13, margin: 0 }}>{cat} {cnt}</Tag>
                ) : null
              })}
            </Space>
          ),
          children: (
            <DayPersonCollapse
              persons={daily.persons}
              shiftMap={shiftMapByDate[daily.date.replace(/\//g, '-')]}
            />
          ),
        }
      })
      return (
        <Collapse
          activeKey={dateActiveKeys}
          onChange={keys => setDateActiveKeys(keys as string[])}
          items={personDateItems}
          style={{ background: '#f0f4f8' }}
        />
      )
    }

    // 區間 / 整月
    if (rangeData) {
      if (rangeData.total_rows === 0) return (
        <div style={{ textAlign: 'center', paddingTop: 40, color: '#aaa', fontSize: 16 }}>
          查詢區間內無工作記錄
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
              <Text type="secondary" style={{ fontSize: 14 }}>{daily.persons.length} 位人員</Text>
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
            <DayPersonCollapse
              persons={daily.persons}
              shiftMap={shiftMapByDate[daily.date.replace(/\//g, '-')]}
            />
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
            setMode(v as JournalMode)
            setSingleData(null); setRangeData(null)
            setPersonList([]); setPersonFilter('')
          }}
          options={[
            { label: '單日',  value: 'single' },
            { label: '區間',  value: 'range' },
            { label: '整月',  value: 'month' },
            { label: <Space size={4}><UserOutlined />人員</Space>, value: 'person' },
            { label: <Space size={4}><UserDeleteOutlined />未指定</Space>, value: 'unassigned' },
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
                  const prefix = mode === 'person' ? 'pday' : 'day'
                  setDateActiveKeys(next ? [] : rangeData.days.map((_, i) => `${prefix}-${i}`))
                }
              }}
            >
              {globalCollapsed ? '全部展開' : '全部縮合'}
            </Button>
          )}
          {/* Excel 匯出按鈕：有資料才顯示 */}
          {(singleData || rangeData) && (() => {
            let from = '', to = '', exportPerson: string | undefined
            if (singleData) {
              const d = singleData.date.replace(/\//g, '-')
              from = d; to = d
            } else if (rangeData) {
              from = rangeData.date_from; to = rangeData.date_to
              if (mode === 'person') exportPerson = personFilter || undefined
            }
            if (!from) return null
            const scope = mode === 'unassigned' ? 'unassigned' as const : 'named' as const
            const label = exportPerson
              ? `${exportPerson}_${from}_${to}`
              : `${mode === 'unassigned' ? '未指定_' : ''}${from}_${to}`
            return (
              <Button
                icon={<FileExcelOutlined />}
                style={{ color: '#52c41a', borderColor: '#52c41a' }}
                onClick={() => downloadFile(
                  getJournalExcelUrl(from, to, exportPerson, scope, venue === 'all' ? undefined : venue),
                  `工作日誌_${label}.xlsx`,
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
