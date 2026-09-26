/**
 * 請購單流程狀態標籤（2026-09-25，0924 會議）
 *
 * 會議上最主要的困惑：「已彙整」出現在「開放中」清單裡，看不出這張單到底
 * 彙整過沒有、拋轉過沒有。改成**一張單只有一個狀態**，四種互斥：
 *
 *   開放中         可以追加、修改（未關閉、未彙整）
 *   已關閉／關閉    已關閉、等採購彙整（人工關閉灰色；系統自動關閉淺粉，沿用 CloseStatusTag）
 *   已彙整         已放進彙整單、還沒拋轉 Ragic
 *   已拋轉 Ragic   已拋到 Ragic，這張單在 Portal 就結束了
 *
 * 另有一種只會出現在舊資料的異常：「已彙整卻被重新開啟」（2026-09-25 前
 * 重新開啟沒有擋已彙整的單）。橘色標出來，讓人找得到、去處理。
 *
 * 狀態值來自後端衍生欄位 flow_status（service 的 flow_status_of()）。
 * 舊版後端沒有這個欄位時，退回原本的 CloseStatusTag，不會壞。
 */
import React from 'react'
import { Tag, Tooltip } from 'antd'
import { CloudUploadOutlined, WarningOutlined } from '@ant-design/icons'
import CloseStatusTag from './CloseStatusTag'
import type { CpRequest } from '@/types/cyclePurchase'

interface Props {
  request: Pick<CpRequest, 'is_closed' | 'close_kind' | 'period_label' | 'flow_status' | 'summary_batch_no'>
}

const FlowStatusTag: React.FC<Props> = ({ request: r }) => {
  switch (r.flow_status) {
    case 'pushed':
      return (
        <Tooltip title="已拋轉到 Ragic，這張單在 Portal 已經結束；要重拋需先在 Ragic 整筆退回">
          <Tag color="green" icon={<CloudUploadOutlined />}>已拋轉 Ragic</Tag>
        </Tooltip>
      )
    case 'summarized':
      return (
        <Tooltip title={`已放進彙整單${r.summary_batch_no ? `（批次 ${r.summary_batch_no}）` : ''}，等待拋轉 Ragic`}>
          <Tag color="cyan">已彙整</Tag>
        </Tooltip>
      )
    case 'summarized_reopened':
      return (
        <Tooltip title="已經在彙整單裡，卻又被重新開啟（舊版漏洞留下的資料）。這張單不能再編輯；要修改請先到彙整單「退回請購單」，再關閉、重新彙整。">
          <Tag color="orange" icon={<WarningOutlined />}>已彙整（被重開）</Tag>
        </Tooltip>
      )
    default:
      // open / closed，或舊後端沒有 flow_status
      return <CloseStatusTag isClosed={r.is_closed} closeKind={r.close_kind} periodLabel={r.period_label} />
  }
}

export default FlowStatusTag
