/**
 * 單列檢查結果（☑ 勾選呈現）—— 樓層巡檢圖與「每日巡檢表」Drawer 共用
 * 規格：docs/DEV_SPEC_floor_plan_map.md §5.1（CheckRow）、§7
 *
 * 2026-10-04 由 pages/MallFacilityInspection/MallFIDailySheetDrawer.tsx 的 ResultCell 抽出（行為不變），
 * 另補 status = measure（整棟巡檢的量測／程度型欄位，例水位高中低）以中性色顯示、不當異常。
 */
import { Space, Tag, Tooltip, Typography } from 'antd'

const { Text } = Typography

// ☑ 加 U+FE0E 強制文字樣式，否則部分瀏覽器會畫成彩色 emoji，顏色無法跟狀態走
const CHECKED = '☑︎'

const RESULT_COLOR: Record<string, string> = {
  normal:    '#52C41A',
  abnormal:  '#FF4D4F',
  pending:   '#FAAD14',
  unchecked: '#bfbfbf',
  measure:   '#1B3A5C',
  reading:   '#1B3A5C',
}
const NEUTRAL = new Set(['measure', 'reading'])

export interface CheckRowReading {
  field?: string
  label:  string
  value:  string
}

export interface CheckRowBatchResult {
  batch_ragic_id: string
  time_label:     string      // 同日多場次時為開始時間 HH:MM
  status:         string      // normal / abnormal / pending / unchecked / measure / reading
  text:           string
  readings:       CheckRowReading[]
}

export interface CheckRow {
  check_content:  string
  result_options: string      // Excel 原文，例 '□正常□異常'、'□_______室內度數□_________濕度'
  kind:           'status' | 'reading' | 'separate' | 'unmapped' | string
  status:         string
  results:        CheckRowBatchResult[]
  abnormal:       boolean
  abnormal_note:  string
}

// '□正常□異常' → ['正常', '異常']；'□_______室內度數□___濕度' → ['_______室內度數', '___濕度']
function parseOptions(opts: string): string[] {
  return (opts || '').split('□').map((s) => s.trim()).filter(Boolean)
}

function stripBlank(opt: string): string {
  return opt.replace(/_+/g, '').trim()
}

function StatusResult({ row, r }: { row: CheckRow; r: CheckRowBatchResult }) {
  const options = parseOptions(row.result_options)
  const text    = (r.text || '').trim()
  const tokens  = text.split(/[\s,、]+/).filter(Boolean)
  const hit     = (opt: string) => text === opt || tokens.includes(opt)
  const anyHit  = options.some(hit)
  const color   = RESULT_COLOR[r.status] ?? '#333'

  return (
    <span>
      {options.map((opt) => {
        const on = hit(opt)
        return (
          <span key={opt} style={{ marginRight: 8, color: on ? color : '#bfbfbf', fontWeight: on ? 600 : 400 }}>
            {on ? CHECKED : '□'}{opt}
          </span>
        )
      })}
      {/* Ragic 值不在 Excel 選項裡 → 原值直接顯示，不吞掉 */}
      {text && !anyHit && (
        <Tag
          color={r.status === 'normal' ? 'success' : NEUTRAL.has(r.status) ? 'blue' : 'error'}
          style={{ marginLeft: 2 }}
        >
          {text}
        </Tag>
      )}
      {!text && <Text type="secondary" style={{ fontSize: 11 }}>（未填）</Text>}
    </span>
  )
}

function ReadingResult({ row, r }: { row: CheckRow; r: CheckRowBatchResult }) {
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
                <span style={{
                  display: 'inline-block', minWidth: 40, textAlign: 'center',
                  borderBottom: '1px solid #1B3A5C', fontWeight: 600, color: '#1B3A5C', margin: '0 2px',
                }}>
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

export default function CheckRowResult({ row }: { row: CheckRow }) {
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
          {r.time_label && <Text type="secondary" style={{ fontSize: 11, marginRight: 4 }}>{r.time_label}</Text>}
          {row.kind === 'reading' ? <ReadingResult row={row} r={r} /> : <StatusResult row={row} r={r} />}
        </div>
      ))}
    </Space>
  )
}
