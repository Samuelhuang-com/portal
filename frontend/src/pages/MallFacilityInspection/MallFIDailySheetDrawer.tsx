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
  Alert, Button, DatePicker, Drawer, Space, Spin, Table, Tag, Tooltip, Typography,
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

const { Text } = Typography

const WEEKDAY = ['日', '一', '二', '三', '四', '五', '六']

// ☑ 加 U+FE0E 強制文字樣式，否則部分瀏覽器會畫成彩色 emoji，顏色無法跟狀態走
const CHECKED = '\u2611\uFE0E'

const STATUS_COLOR: Record<string, string> = {
  normal:    '#52C41A',
  abnormal:  '#FF4D4F',
  pending:   '#FAAD14',
  unchecked: '#bfbfbf',
}

type RowWithKey = MallFIDailySheetRow & { _key: string }

// ── Excel 選項字串解析 ────────────────────────────────────────────────────────
// '□正常□異常'                     → ['正常', '異常']
// '□_______室內度數□_________濕度'  → ['_______室內度數', '_________濕度']
function parseOptions(opts: string): string[] {
  return opts.split('□').map((s) => s.trim()).filter(Boolean)
}

function stripBlank(opt: string): string {
  return opt.replace(/_+/g, '').trim()
}

// ── 單一場次的結果 ────────────────────────────────────────────────────────────

function StatusResult({ row, r }: { row: RowWithKey; r: MallFIDailySheetResult }) {
  const options = parseOptions(row.result_options)
  const text    = (r.text || '').trim()
  const tokens  = text.split(/[\s,、]+/).filter(Boolean)
  const hit     = (opt: string) => text === opt || tokens.includes(opt)
  const anyHit  = options.some(hit)
  const color   = STATUS_COLOR[r.status] ?? '#333'

  return (
    <span>
      {options.map((opt) => {
        const on = hit(opt)
        return (
          <span
            key={opt}
            style={{
              marginRight: 8,
              color:       on ? color : '#bfbfbf',
              fontWeight:  on ? 600 : 400,
            }}
          >
            {on ? CHECKED : '□'}{opt}
          </span>
        )
      })}
      {/* Ragic 值不在 Excel 選項裡 → 原值直接顯示，不吞掉 */}
      {text && !anyHit && (
        <Tag color={r.status === 'normal' ? 'success' : 'error'} style={{ marginLeft: 2 }}>
          {text}
        </Tag>
      )}
      {!text && <Text type="secondary" style={{ fontSize: 11 }}>（未填）</Text>}
    </span>
  )
}

function ReadingResult({ row, r }: { row: RowWithKey; r: MallFIDailySheetResult }) {
  const options = parseOptions(row.result_options)
  return (
    <span>
      {options.map((opt, i) => {
        const label = stripBlank(opt)
        const value = r.readings[i]?.value ?? ''
        return (
          <span key={opt} style={{ marginRight: 10, whiteSpace: 'nowrap' }}>
            {value ? (
              <>
                <span style={{ color: '#1B3A5C' }}>{CHECKED}</span>
                <span
                  style={{
                    display: 'inline-block', minWidth: 40, textAlign: 'center',
                    borderBottom: '1px solid #1B3A5C', fontWeight: 600, color: '#1B3A5C',
                    margin: '0 2px',
                  }}
                >
                  {value}
                </span>
              </>
            ) : (
              <span style={{ color: '#bfbfbf' }}>□______</span>
            )}
            <span style={{ color: value ? '#333' : '#bfbfbf' }}>{label}</span>
          </span>
        )
      })}
    </span>
  )
}

// 2026-10-04：樓層巡檢圖（FloorMapTab）右側明細共用同一套結果呈現
export function ResultCell({ row }: { row: RowWithKey }) {
  if (row.kind === 'separate' || row.kind === 'unmapped' || row.results.length === 0) {
    return (
      <Space size={4} wrap>
        <Text type="secondary" style={{ fontSize: 12 }}>{row.result_options}</Text>
        {row.kind === 'separate' && <Tag>另作表單</Tag>}
        {row.kind === 'unmapped' && (
          <Tooltip title="Ragic 表單目前沒有這個欄位，無資料可帶入">
            <Tag color="default">Ragic 無此欄位</Tag>
          </Tooltip>
        )}
      </Space>
    )
  }
  return (
    <Space direction="vertical" size={2}>
      {row.results.map((r) => (
        <div key={r.batch_ragic_id} style={{ fontSize: 12, lineHeight: '20px' }}>
          {r.time_label && (
            <Text type="secondary" style={{ fontSize: 11, marginRight: 4 }}>{r.time_label}</Text>
          )}
          {row.kind === 'reading'
            ? <ReadingResult row={row} r={r} />
            : <StatusResult row={row} r={r} />}
        </div>
      ))}
    </Space>
  )
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
}

export default function MallFIDailySheetDrawer({
  open, date, focusSheet, onClose, onDateChange,
}: MallFIDailySheetDrawerProps) {
  const [loading, setLoading] = useState(false)
  const [data,    setData]    = useState<MallFIDailySheetResponse | null>(null)
  const [error,   setError]   = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!date) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchMallFIDailySheet(date))
    } catch {
      setData(null)
      setError('取得每日巡檢表失敗，請稍後再試')
    } finally {
      setLoading(false)
    }
  }, [date])

  useEffect(() => { if (open) load() }, [open, load])

  const d       = date ? dayjs(date) : null
  const floors  = new Map((data?.floors ?? []).map((f) => [f.key, f]))
  const rows: RowWithKey[] = (data?.rows ?? []).map((r, i) => ({
    ...r, _key: `${r.source_tab}__${r.item}__${i}`,
  }))
  const s = data?.summary

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
      render: (_: unknown, r) => <ResultCell row={r} />,
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
            商場工務每日巡檢：{d ? `${d.format('YYYY/MM/DD')}（${WEEKDAY[d.day()]}）` : ''}
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
            <Tag color={s.abnormal + s.pending > 0 ? 'error' : 'default'}>
              異常／待處理 {s.abnormal + s.pending} 項
            </Tag>
            <Tag>未填 {s.unchecked} 項</Tag>
            {s.actual_minutes > 0 && <Tag color="blue">實際巡檢 {s.actual_minutes} 分</Tag>}
            <Text type="secondary" style={{ fontSize: 12 }}>
              ☑ ＝ Ragic 填報值；同日多場次時依開始時間逐筆列出
            </Text>
          </Space>
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
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={2} />
                <Table.Summary.Cell index={2} colSpan={4}>
                  <Text>{s.shift_times[0]?.label}:{s.shift_times[0]?.range}</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={6} align="center">
                  <Text strong>{s.std_minutes_routine}分</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={7}>
                  <Text type="secondary" style={{ fontSize: 11 }}>一般巡檢</Text>
                </Table.Summary.Cell>
              </Table.Summary.Row>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={2} />
                <Table.Summary.Cell index={2} colSpan={4}>
                  <Text>{s.shift_times[1]?.label}:{s.shift_times[1]?.range}</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={6} align="center">
                  <Text strong>{s.std_minutes_total}分</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={7}>
                  <Text type="secondary" style={{ fontSize: 11 }}>含櫃位抄表</Text>
                </Table.Summary.Cell>
              </Table.Summary.Row>
            </Table.Summary>
          ) : null}
        />
      </Spin>
    </Drawer>
  )
}
