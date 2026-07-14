import hashlib, sys

def load_verify(path, expected_sha):
    data = open(path, "r", encoding="utf-8").read()
    actual = hashlib.sha256(data.encode("utf-8")).hexdigest()
    if actual != expected_sha:
        print(f"SHA MISMATCH for {path}: actual={actual}")
        sys.exit(1)
    return data


# ── 1) MonthlyCalendarGrid.tsx: 新增可選 onCellClick prop（向下相容，不影響其他頁面）──

GRID_PATH = "frontend/src/components/MonthlyCalendarGrid.tsx"
grid = load_verify(GRID_PATH, "7665d495303d74a0bf5b17adc06a186a79736c1271871da22e13e90e86d6a254")

OLD_PROPS = '''export interface MonthlyCalendarGridProps {
  year:            number
  month:           number
  maxDay:          number
  rows:            CalendarRow[]
  rowHeaderLabel?: string                                                     // 預設「巡檢區域」
  renderCell?:     (day: number, data: CalendarCellData | undefined) => React.ReactNode
  cellStyle?:      (day: number, data: CalendarCellData | undefined) => React.CSSProperties
  legend?:         LegendItem[]                                               // 傳 [] 可隱藏圖例
}'''
assert grid.count(OLD_PROPS) == 1, f"grid props anchor count={grid.count(OLD_PROPS)}"
NEW_PROPS = '''export interface MonthlyCalendarGridProps {
  year:            number
  month:           number
  maxDay:          number
  rows:            CalendarRow[]
  rowHeaderLabel?: string                                                     // 預設「巡檢區域」
  renderCell?:     (day: number, data: CalendarCellData | undefined) => React.ReactNode
  cellStyle?:      (day: number, data: CalendarCellData | undefined) => React.CSSProperties
  legend?:         LegendItem[]                                               // 傳 [] 可隱藏圖例
  // 2026-07-14 新增：cell 點擊回呼（僅 has_record 的 cell 會觸發），供各模組串接明細 Drawer。
  // 選填、預設不啟用，不影響既有未傳入此 prop 的頁面。
  onCellClick?:    (day: number, rowKey: string, data: CalendarCellData) => void
}'''
grid = grid.replace(OLD_PROPS, NEW_PROPS, 1)

OLD_SIG = '''export default function MonthlyCalendarGrid({
  year,
  month,
  maxDay,
  rows,
  rowHeaderLabel = '巡檢區域',
  renderCell     = defaultRenderCell,
  cellStyle      = defaultCellStyle,
  legend         = DEFAULT_LEGEND,
}: MonthlyCalendarGridProps) {'''
assert grid.count(OLD_SIG) == 1, f"grid sig anchor count={grid.count(OLD_SIG)}"
NEW_SIG = '''export default function MonthlyCalendarGrid({
  year,
  month,
  maxDay,
  rows,
  rowHeaderLabel = '巡檢區域',
  renderCell     = defaultRenderCell,
  cellStyle      = defaultCellStyle,
  legend         = DEFAULT_LEGEND,
  onCellClick,
}: MonthlyCalendarGridProps) {'''
grid = grid.replace(OLD_SIG, NEW_SIG, 1)

OLD_TD = '''                {days.map((d) => {
                  const data = row.daily[String(d)]
                  return (
                    <td key={d} style={{
                      textAlign: 'center',
                      padding:   '3px 1px',
                      border:    '1px solid #e8e8e8',
                      overflow:  'hidden',
                      ...cellStyle(d, data),
                    }}>
                      {renderCell(d, data)}
                    </td>
                  )
                })}'''
assert grid.count(OLD_TD) == 1, f"grid td anchor count={grid.count(OLD_TD)}"
NEW_TD = '''                {days.map((d) => {
                  const data = row.daily[String(d)]
                  const clickable = !!onCellClick && !!data?.has_record
                  return (
                    <td
                      key={d}
                      onClick={clickable ? () => onCellClick!(d, row.key, data!) : undefined}
                      style={{
                        textAlign: 'center',
                        padding:   '3px 1px',
                        border:    '1px solid #e8e8e8',
                        overflow:  'hidden',
                        cursor:    clickable ? 'pointer' : 'default',
                        ...cellStyle(d, data),
                      }}
                    >
                      {renderCell(d, data)}
                    </td>
                  )
                })}'''
grid = grid.replace(OLD_TD, NEW_TD, 1)

open(GRID_PATH.replace(".tsx", "_tmp_v43.tsx"), "w", encoding="utf-8").write(grid)
print("grid OK", len(grid))


# ── 2) MallPeriodicMaintenance/index.tsx: 新增月曆格點擊 → 明細 Drawer（共用既有 kpiDrawer）──

PAGE_PATH = "frontend/src/pages/MallPeriodicMaintenance/index.tsx"
page = load_verify(PAGE_PATH, "9760796cc5bde8198d7c8fc0c9edcf5951eb2a17f7776688ca4258d7808f23ec")

# 2a) 新增 handler：緊接在 openKpiDrawer 定義之後
OLD_HANDLER_ANCHOR = '''      setKpiDrawerItems(filtered)
    } catch {
      setKpiDrawerItems([])
      message.error('讀取明細失敗')
    } finally {
      setKpiDrawerLoading(false)
    }
  }, [stats])'''
assert page.count(OLD_HANDLER_ANCHOR) == 1, f"page handler anchor count={page.count(OLD_HANDLER_ANCHOR)}"

NEW_HANDLER = '''      setKpiDrawerItems(filtered)
    } catch {
      setKpiDrawerItems([])
      message.error('讀取明細失敗')
    } finally {
      setKpiDrawerLoading(false)
    }
  }, [stats])

  // ── Dashboard 月曆格點擊 → 明細 Drawer（2026-07-14 新增，共用上方 KPI 卡片同一個
  // Drawer state，篩選條件改為「類別 + 排定日期」，對齊月曆格本身依 scheduled_date
  // 分組的口徑，避免點進去的清單跟格子本身顯示的統計對不起來）───────────────────
  const openCalendarCellDrawer = useCallback(async (day: number, category: string) => {
    if (!stats?.current_batch) {
      message.warning('尚無批次資料，請先同步')
      return
    }
    const mmdd = `${String(dashMonth).padStart(2, '0')}/${String(day).padStart(2, '0')}`
    setKpiDrawerTitle(`${dashYear}/${mmdd} ${category}`)
    setKpiDrawerOpen(true)
    setKpiDrawerLoading(true)
    try {
      const detail = await fetchMallPMBatchDetail(stats.current_batch.ragic_id)
      const filtered = detail.items.filter(
        (it) => it.category === category && it.scheduled_date === mmdd,
      )
      setKpiDrawerItems(filtered)
    } catch {
      setKpiDrawerItems([])
      message.error('讀取明細失敗')
    } finally {
      setKpiDrawerLoading(false)
    }
  }, [stats, dashYear, dashMonth])'''

page = page.replace(OLD_HANDLER_ANCHOR, NEW_HANDLER, 1)

# 2b) 串接到 MonthlyCalendarGrid
OLD_GRID_USAGE = '''          <MonthlyCalendarGrid
            year={parseInt(dashYear)}
            month={dashMonth}
            maxDay={calMaxDay}
            rows={calRows}
            rowHeaderLabel="保養類別"
          />'''
assert page.count(OLD_GRID_USAGE) == 1, f"page grid usage anchor count={page.count(OLD_GRID_USAGE)}"
NEW_GRID_USAGE = '''          <MonthlyCalendarGrid
            year={parseInt(dashYear)}
            month={dashMonth}
            maxDay={calMaxDay}
            rows={calRows}
            rowHeaderLabel="保養類別"
            onCellClick={(day, rowKey) => openCalendarCellDrawer(day, rowKey)}
          />'''
page = page.replace(OLD_GRID_USAGE, NEW_GRID_USAGE, 1)

open(PAGE_PATH.replace(".tsx", "_tmp_v43.tsx"), "w", encoding="utf-8").write(page)
print("page OK", len(page))
