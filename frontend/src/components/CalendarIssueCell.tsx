/**
 * 月曆格「⚠ 有異常/待處理」格子：Tooltip 直接列出是哪幾項（2026-10-05）
 *
 * 給 MonthlyCalendarGrid 的 renderCell 用。後端 cell 多帶 issues[]
 * （商場工務巡檢 /daily-calendar、整棟巡檢 /dashboard/calendar），判定與每日巡檢表 Drawer 同一套。
 * 沒有 issues 的格子（或舊後端）一律退回 defaultRenderCell，畫面與原本相同。
 */
import type { ReactNode } from 'react'
import { Tooltip } from 'antd'
import { defaultRenderCell, type CalendarCellData } from '@/components/MonthlyCalendarGrid'
import type { MallFIDailyIssue } from '@/api/mallFacilityInspection'

const ISSUE_TIP_MAX = 8

export type CalendarIssueCellData = CalendarCellData & { issues?: MallFIDailyIssue[] }

export function renderIssueCell(day: number, data: CalendarCellData | undefined): ReactNode {
  const issues = (data as CalendarIssueCellData | undefined)?.issues ?? []
  if (!data?.has_record || issues.length === 0) return defaultRenderCell(day, data)
  const tip = (
    <div style={{ maxWidth: 360 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>
        異常 {data.abnormal_count}　待處理 {data.pending_count}　完成率 {data.completion_rate}%
      </div>
      {issues.slice(0, ISSUE_TIP_MAX).map((x, i) => (
        <div key={i} style={{ fontSize: 12, lineHeight: '18px' }}>
          • {x.item}／{x.check_content}：{x.status === 'pending' ? '待處理' : '異常'}
          {x.note ? `（${x.note.replace(/\n/g, '；')}）` : ''}
        </div>
      ))}
      {issues.length > ISSUE_TIP_MAX && (
        <div style={{ fontSize: 12 }}>…另 {issues.length - ISSUE_TIP_MAX} 項</div>
      )}
      <div style={{ fontSize: 11, opacity: 0.75, marginTop: 4 }}>點格子看當日完整巡檢表</div>
    </div>
  )
  return (
    <Tooltip title={tip}>
      <span style={{ color: '#FF4D4F', fontSize: 16, cursor: 'pointer' }}>⚠</span>
    </Tooltip>
  )
}
