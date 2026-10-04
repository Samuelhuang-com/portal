/**
 * 商場工務每日巡檢表 Drawer（Dashboard 月曆格的下一層）
 *
 * 版型來源：2.2商場-每日巡檢表.xlsx（#2.2商場-每日巡檢表）
 *   欄位：樓層 | 項目 | 檢查內容 | 實際巡檢人員 | 運轉狀況(結果) | 異常說明 | 時間(分) | 備註
 *   樓層／項目／時間(分) 依 Excel 合併儲存格做 rowSpan；
 *   運轉狀況沿用 Excel 的「□正常□異常」選項，Ragic 填報值打勾（☑）。
 *
 * 資料：GET /api/v1/mall-facility-inspection/daily-sheet?date=YYYY-MM-DD
 *   一天可能有早班／晚班兩筆場次 → 結果逐場次列出（前綴開始時間）。
 *
 * 🔗 在 Ragic 查看：一張表跨 5 張 Ragic Sheet、每樓層各自一筆紀錄，
 *   因此連結放在「樓層」格（每個場次一個），不是 Drawer 標題列。
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, DatePicker, Drawer, Space, Spin, Switch, Table, Tag, Tooltip, Typography,
} from 'antd'
import { LeftOutlined, LinkOutlined, ReloadOutlined, RightOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { type Dayjs } from 'dayjs'
import {
  fetchMallFIDailySheet,
  type MallFIDailySheetFloor,
  type MallFIDailySheetResponse,
  type MallFIDailySheetResult,
  type MallFIDailySheetRow,
} from '@/api/mallFacilityInspection'
// 2026-10-04：結果呈現（☑ 勾選）抽到共用元件，樓層巡檢圖也用同一個（CLAUDE.md §12）
import CheckRowResult from '@/components/FloorPlanMap/CheckRowResult'

const { Text } = Typography

const WEEKDAY = ['日', '一', '二', '三', '四', '五', '六']

type RowWithKey = MallFIDailySheetRow & { _key: string }

// 「只看異常／待處理」篩選後，樓層／項目的合併儲存格要依篩選結果重算（2026-10-05）
function withSpans(list: RowWithKey[]): RowWithKey[] {
  const run = (i: number, same: (a: RowWithKey, b: RowWithKey) => boolean) => {
    let n = 0
    while (i + n < list.length && same(list[i], list[i + n])) n += 1
    return n
  }
  const sameFloor = (a: RowWithKey, b: RowWithKey) => a.source_tab === b.source_tab
  const sameItem  = (a: RowWithKey, b: RowWithKey) => sameFloor(a, b) && a.item === b.item
  return list.map((r, i) => {
    const prev = i > 0 ? list[i - 1] : undefined
    const floorFirst = !prev || !sameFloor(prev, r)
    const itemFirst  = !prev || !sameItem(prev, r)
    return {
      ...r,
      floor_first_row: floorFirst,
      floor_row_count: floorFirst ? run(i, sameFloor) : 0,
      item_first_row:  itemFirst,
      item_row_count:  itemFirst ? run(i, sameItem) : 0,
    }
  })
}

// ── 樓層格（含 Ragic 連結與實際時間）─────────────────────────────────────────

function FloorCell({ floor }: { floor: MallFIDailySheetFloor | undefined; }) {
  if (!floor) return null
  return (
    <Space direction="vertical" size={2} style={{ width: '100%', alignItems: 'center' }}>
      <Text strong style={{ fontSize: 14, color: '#1B3A5C' }}>{floor.floor}</Text>
      {!floor.has_record && <Tag color="warning" style={{ marginRight: 0 }}>未登錄</Tag>}
      {floor.batches.map((b) => (
        <a
          key={b.ragic_id}
          href={b.ragic_url}
          target="_blank"
          rel="noreferrer"
          style={{ color: '#4BA8E8', fontSize: 11, whiteSpace: 'nowrap' }}
          title="在 Ragic 查看"
        >
          <LinkOutlined /> {b.start_hhmm || 'Ragic'}
        </a>
      ))}
      {floor.actual_minutes > 0 && (
        <Text type="secondary" style={{ fontSize: 11 }}>實際 {floor.actual_minutes} 分</Text>
      )}
    </Space>
  )
}

// ── 主元件 ────────────────────────────────────────────────────────────────────

export interface MallFIDailySheetDrawerProps {
  open:       boolean
  date:       string | null   // YYYY-MM-DD
  focusSheet?: string | null  // 從月曆格點進來的樓層（sheet key），該樓層列底色標示
  onClose:    () => void
  onDateChange?: (date: string) => void
  // 2026-10-05：整棟巡檢共用同一個 Drawer（回傳格式相同）。不給就是商場工務巡檢。
  fetchSheet?: (date: string) => Promise<MallFIDailySheetResponse>
  titleText?:  string
}

type SheetSummary = MallFIDailySheetResponse['summary']

// 表尾時間列：後端有給 footer（整棟巡檢）就照用；否則是商場 Excel #2.2 的早晚班兩列
function footerRows(s: SheetSummary): { text: string; minutes: number; note: string }[] {
  if (s.footer && s.footer.length) return s.footer
  return [
    { text: `${s.shift_times[0]?.label ?? ''}:${s.shift_times[0]?.range ?? ''}`, minutes: s.std_minutes_routine, note: '一般巡檢' },
    { text: `${s.shift_times[1]?.label ?? ''}:${s.shift_times[1]?.range ?? ''}`, minutes: s.std_minutes_total,   note: '含櫃位抄表' },
  ]
}

export default function MallFIDailySheetDrawer({
  open, date, focusSheet, onClose, onDateChange,
  fetchSheet = fetchMallFIDailySheet, titleText = '商場工務每日巡檢',
}: MallFIDailySheetDrawerProps) {
  const [loading, setLoading] = useState(false)
  const [data,    setData]    = useState<MallFIDailySheetResponse | null>(null)
  const [error,   setError]   = useState<string | null>(null)
  const [onlyIssues, setOnlyIssues] = useState(false)

  const load = useCallback(async () => {
    if (!date) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchSheet(date))
    } catch {
      setData(null)
      setError('取得每日巡檢表失敗，請稍後再試')
    } finally {
      setLoading(false)
    }
  }, [date, fetchSheet])

  useEffect(() => { if (open) load() }, [open, load])

  const d       = date ? dayjs(date) : null
  const floors  = new Map((data?.floors ?? []).map((f) => [f.key, f]))
  const allRows: RowWithKey[] = (data?.rows ?? []).map((r, i) => ({
    ...r, _key: `${r.source_tab}__${r.item}__${i}`,
  }))
  const rows = onlyIssues ? withSpans(allRows.filter((r) => r.abnormal)) : allRows
  const s = data?.summary
  const extra = data?.extra_issues ?? []
  const issueCount = s ? s.abnormal + s.pending + (s.extra_issues ?? extra.length) : 0

  const shift = (n: number) => {
    if (d && onDateChange) onDateChange(d.add(n, 'day').format('YYYY-MM-DD'))
  }

  const columns: ColumnsType<RowWithKey> = [
    {
      title: '樓層', dataIndex: 'floor', width: 84, align: 'center',
      onCell: (r) => ({ rowSpan: r.floor_first_row ? r.floor_row_count : 0 }),
      render: (_: unknown, r) => <FloorCell floor={floors.get(r.source_tab)} />,
    },
    {
      title: '項目', dataIndex: 'item', width: 104, align: 'center',
      onCell: (r) => ({ rowSpan: r.item_first_row ? r.item_row_count : 0 }),
      render: (v: string) => <Text strong style={{ fontSize: 12 }}>{v}</Text>,
    },
    {
      title: '檢查內容', dataIndex: 'check_content', width: 230,
      render: (v: string) => <Text style={{ fontSize: 12 }}>{v}</Text>,
    },
    {
      title: '實際巡檢人員', width: 104, align: 'center',
      onCell: (r) => ({ rowSpan: r.floor_first_row ? r.floor_row_count : 0 }),
      render: (_: unknown, r) => {
        const names = floors.get(r.source_tab)?.inspectors ?? []
        return names.length
          ? <Text style={{ fontSize: 12 }}>{names.join('、')}</Text>
          : <Text type="secondary">—</Text>
      },
    },
    {
      title: '運轉狀況(結果)', width: 270,
      render: (_: unknown, r) => <CheckRowResult row={r} />,
    },
    {
      title: '異常說明', dataIndex: 'abnormal_note', width: 170,
      onCell: (r) => ({ rowSpan: r.item_first_row ? r.item_row_count : 0 }),
      render: (v: string) => v
        ? <Text style={{ fontSize: 12, color: '#c0392b', whiteSpace: 'pre-wrap' }}>{v}</Text>
        : <Text type="secondary">—</Text>,
    },
    {
      title: '時間(分)', dataIndex: 'minutes', width: 70, align: 'center',
      onCell: (r) => ({ rowSpan: r.item_first_row ? r.item_row_count : 0 }),
      render: (v: number) => (v > 0 ? <Text strong style={{ color: '#1B3A5C' }}>{v}</Text> : null),
    },
    {
      title: '備註', dataIndex: 'remark', width: 110,
      render: (v: string) => (v ? <Text style={{ fontSize: 12 }}>{v}</Text> : null),
    },
  ]

  const rowClassName = (r: RowWithKey) => {
    if (r.abnormal) return 'mfi-sheet-row--abnormal'
    if (focusSheet && r.source_tab === focusSheet) return 'mfi-sheet-row--focus'
    return ''
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width="min(1220px, 96vw)"
      destroyOnClose
      title={
        <Space wrap>
          <Tag color="#1B3A5C">每日巡檢表</Tag>
          <span>
            {titleText}：{d ? `${d.format('YYYY/MM/DD')}（${WEEKDAY[d.day()]}）` : ''}
          </span>
        </Space>
      }
      extra={
        <Space>
          <Button size="small" icon={<LeftOutlined />} onClick={() => shift(-1)} disabled={!onDateChange}>
            前一天
          </Button>
          <DatePicker
            size="small"
            allowClear={false}
            value={d}
            format="YYYY/MM/DD"
            onChange={(v: Dayjs | null) => { if (v && onDateChange) onDateChange(v.format('YYYY-MM-DD')) }}
          />
          <Button size="small" onClick={() => shift(1)} disabled={!onDateChange}>
            後一天 <RightOutlined />
          </Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={load} loading={loading} />
        </Space>
      }
    >
      <style>{`
        .mfi-sheet-table .ant-table-thead > tr > th {
          background: #f0f4f8; color: #1B3A5C; font-weight: 600;
          text-align: center; white-space: nowrap;
        }
        .mfi-sheet-table .ant-table-cell { vertical-align: middle; padding: 5px 8px !important; }
        .mfi-sheet-row--abnormal > td { background: #fff1f0 !important; }
        .mfi-sheet-row--focus > td    { background: #f0f7ff; }
      `}</style>

      {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 12 }} />}

      <Spin spinning={loading}>
        {s && (
          <Space wrap size={[8, 8]} style={{ marginBottom: 12 }}>
            <Tag color={s.floors_logged === s.floors_total ? 'success' : 'warning'}>
              已登錄樓層 {s.floors_logged} / {s.floors_total}
            </Tag>
            <Tag color={issueCount > 0 ? 'error' : 'default'}>
              異常／待處理 {issueCount} 項
            </Tag>
            <Tag>未填 {s.unchecked} 項</Tag>
            {s.actual_minutes > 0 && <Tag color="blue">實際巡檢 {s.actual_minutes} 分</Tag>}
            <Space size={4}>
              <Switch size="small" checked={onlyIssues} onChange={setOnlyIssues} />
              <Text style={{ fontSize: 12 }}>只看異常／待處理</Text>
            </Space>
            <Text type="secondary" style={{ fontSize: 12 }}>
              ☑ ＝ Ragic 填報值；同日多場次時依開始時間逐筆列出
            </Text>
          </Space>
        )}

        {extra.length > 0 && (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 12 }}
            message={`另有 ${extra.length} 項異常／待處理在 Excel 版型以外的 Ragic 欄位`}
            description={
              <div>
                {extra.map((x, i) => (
                  <div key={i} style={{ fontSize: 12 }}>
                    • {x.floor}{x.time_label ? ` [${x.time_label}]` : ''}　{x.field}：
                    <Text style={{ color: '#c0392b', fontSize: 12 }}>{x.text}</Text>
                  </div>
                ))}
              </div>
            }
          />
        )}

        {onlyIssues && data && rows.length === 0 && (
          <Alert
            type="success"
            showIcon
            style={{ marginBottom: 12 }}
            message={extra.length > 0 ? 'Excel 版型內沒有異常／待處理項目' : '當日沒有異常／待處理項目'}
          />
        )}

        {data && s && s.floors_logged === 0 && (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 12 }}
            message={`${data.date} 無任何樓層巡檢紀錄`}
            description="以下為空白標準表（Excel 原版型）。"
          />
        )}

        <Table<RowWithKey>
          className="mfi-sheet-table"
          dataSource={rows}
          rowKey="_key"
          columns={columns}
          size="small"
          bordered
          pagination={false}
          rowClassName={rowClassName}
          scroll={{ x: 1140 }}
          summary={() => s ? (
            <Table.Summary>
              {footerRows(s).map((f, i) => (
                <Table.Summary.Row key={i}>
                  <Table.Summary.Cell index={0} colSpan={2} />
                  <Table.Summary.Cell index={2} colSpan={4}>
                    <Text>{f.text}</Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={6} align="center">
                    <Text strong>{f.minutes}分</Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={7}>
                    <Text type="secondary" style={{ fontSize: 11 }}>{f.note}</Text>
                  </Table.Summary.Cell>
                </Table.Summary.Row>
              ))}
            </Table.Summary>
          ) : null}
        />
      </Spin>
    </Drawer>
  )
}
