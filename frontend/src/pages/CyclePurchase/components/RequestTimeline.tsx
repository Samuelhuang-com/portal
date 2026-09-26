/**
 * 請購單生命週期時間軸（2026-09-25，草稿裁示「2」）
 *
 * 放在請購單詳情頁最上方（FlowSteps 下方）：這是「這一張單」自己走過的
 * 完整歷程，跟 FlowSteps 的「整個模組現在在哪一步」是兩個不同層次的資訊，
 * 兩者互補不重複。
 *
 * 只用 CpRequestDetail 現有欄位組出四個節點：建立／填寫、關閉、彙整、
 * 下一步提示。刻意不假裝知道「彙整單有沒有拋轉 Ragic、簽核進不進行」——
 * 那些狀態存在彙整單那邊（cycle_purchase_summary），請購單本身的欄位
 * 看不到，硬猜會顯示錯誤資訊，所以只給一個「前往彙整單查看」的連結，
 * 由使用者自己去看最新狀態。
 */
import React from 'react'
import { Card, Timeline, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import type { CpRequestDetail } from '@/types/cyclePurchase'

const { Text } = Typography

const DONE_COLOR = '#3aa76d'
const PENDING_COLOR = '#d7dbe2'

function fmt(dt?: string | null): string {
  if (!dt) return ''
  // 後端回傳的是 ISO 字串，這裡只取到分鐘，時間軸不需要秒
  return dt.replace('T', ' ').slice(0, 16)
}

interface Props {
  detail: CpRequestDetail
}

const RequestTimeline: React.FC<Props> = ({ detail }) => {
  const navigate = useNavigate()

  const items: { color: string; children: React.ReactNode }[] = []

  // 1. 建立
  items.push({
    color: DONE_COLOR,
    children: (
      <div>
        <Text strong>建立</Text>
        <div style={{ fontSize: 12, color: '#8a93a3' }}>
          {fmt(detail.created_at)}
          {detail.submitted_by_name ? `・${detail.submitted_by_name}` : ''}
        </div>
      </div>
    ),
  })

  // 2. 關閉／重新開啟
  if (detail.is_closed) {
    const byAuto = detail.close_kind === 'auto'
    items.push({
      color: DONE_COLOR,
      children: (
        <div>
          <Text strong>{byAuto ? '已關閉（系統自動）' : '已關閉'}</Text>
          <div style={{ fontSize: 12, color: '#8a93a3' }}>
            {fmt(detail.closed_at)}
            {byAuto ? '・期別已過，系統自動關閉' : detail.closed_by_name ? `・${detail.closed_by_name}` : ''}
          </div>
        </div>
      ),
    })
  } else if (detail.reopened_at) {
    // 曾經關閉過又被重新開啟，目前開放中
    items.push({
      color: '#4ba8e8',
      children: (
        <div>
          <Text strong style={{ color: '#2c7fbd' }}>已重新開啟・開放中</Text>
          <div style={{ fontSize: 12, color: '#8a93a3' }}>
            {fmt(detail.reopened_at)}
            {detail.reopened_by_name ? `・${detail.reopened_by_name}` : ''}
          </div>
        </div>
      ),
    })
  } else {
    items.push({
      color: PENDING_COLOR,
      children: (
        <div>
          <Text type="secondary">尚未關閉</Text>
          <div style={{ fontSize: 12, color: '#b6bcc6' }}>填寫完成後記得關閉，才能被彙整</div>
        </div>
      ),
    })
  }

  // 3. 彙整
  if (detail.is_summarized) {
    items.push({
      color: DONE_COLOR,
      children: (
        <div>
          <Text strong>已彙整</Text>
          <div style={{ fontSize: 12, color: '#8a93a3' }}>
            {fmt(detail.summarized_at)}
            {detail.summary_batch_no ? `・批次 ${detail.summary_batch_no}` : ''}
          </div>
        </div>
      ),
    })
  } else if (detail.unsummarize_reason) {
    items.push({
      color: '#e8a33d',
      children: (
        <div>
          <Text strong style={{ color: '#c9791f' }}>已從彙整單退回</Text>
          <div style={{ fontSize: 12, color: '#8a93a3' }}>
            {fmt(detail.unsummarized_at)}
            {detail.unsummarized_by_name ? `・${detail.unsummarized_by_name}` : ''}
          </div>
          <div style={{ fontSize: 12, color: '#8a93a3' }}>原因：{detail.unsummarize_reason}</div>
        </div>
      ),
    })
  } else {
    items.push({
      color: PENDING_COLOR,
      children: (
        <div>
          <Text type="secondary">尚未彙整</Text>
          {detail.is_closed && (
            <div style={{ fontSize: 12, color: '#b6bcc6' }}>已關閉，等買家彙整</div>
          )}
        </div>
      ),
    })
  }

  // 3.5 已拋轉 Ragic（2026-09-25：後端 flow_status 由彙整列的 ragic_pushed 推得）
  if (detail.flow_status === 'pushed') {
    items.push({
      color: DONE_COLOR,
      children: (
        <div>
          <Text strong>已拋轉 Ragic</Text>
          <div style={{ fontSize: 12, color: '#8a93a3' }}>簽核進度請到 Ragic 或彙整單「已彙整 Ragic 請購單」查看</div>
        </div>
      ),
    })
  }

  // 4. 下一步提示 / 前往彙整單（不假裝知道拋轉 Ragic 之後的狀態）
  if (detail.is_summarized && detail.flow_status !== 'pushed') {
    items.push({
      color: PENDING_COLOR,
      children: (
        <div>
          <Text type="secondary">後續進度（拋轉 Ragic／簽核）請到彙整單查看</Text>
          <div style={{ marginTop: 4 }}>
            <a onClick={() => navigate('/cycle-purchase/summary')}>前往彙整單 →</a>
          </div>
        </div>
      ),
    })
  }

  return (
    <Card size="small" title="這張單的生命週期" style={{ marginBottom: 16 }}>
      <Timeline items={items} />
    </Card>
  )
}

export default RequestTimeline
