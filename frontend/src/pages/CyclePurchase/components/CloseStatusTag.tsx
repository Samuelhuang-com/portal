/**
 * 週採請購單 — 關閉狀態標籤（2026-08-07 新增）
 *
 * 三種狀態，用不同的視覺區分「誰把這張單關掉的」：
 *
 *   開放中     綠色 Tag                        還可以編輯
 *   已關閉     灰色 Tag ＋ 鎖頭                 有人按了「關閉」
 *   關閉       淺粉色 Tag ＋ 時鐘               期別已過，系統自動關的
 *
 * 為什麼要分：兩者的「為什麼被關」完全不同。人工關閉是有人做了決定；
 * 系統關閉只是月份過了，沒有人經手（closed_by_name 是空的）。
 * 使用者看到「關閉」而不是「已關閉」時，就知道不用去找是誰關的。
 *
 * 色碼取自 CLAUDE.md 受保護色的淺粉配對（底 #fff5f5 / 框 #ffccc7），
 * 與全站「需要注意但不是錯誤」的用色一致。
 *
 * 抽成共用元件是因為清單頁與詳情頁都要用，兩邊各刻一次遲早會不一致。
 */
import React from 'react'
import { Tag, Tooltip } from 'antd'
import { ClockCircleOutlined, LockOutlined } from '@ant-design/icons'
import type { CpCloseKind } from '@/types/cyclePurchase'

/** CLAUDE.md 受保護色：淺粉底／框線 */
const PINK_BG = '#fff5f5'
const PINK_BORDER = '#ffccc7'
const PINK_TEXT = '#c0392b'

export interface CloseStatusTagProps {
  isClosed: boolean
  closeKind?: CpCloseKind
  /** 期別標籤（如 2026-07），系統自動關閉時放進 tooltip 說明 */
  periodLabel?: string
}

const CloseStatusTag: React.FC<CloseStatusTagProps> = ({ isClosed, closeKind, periodLabel }) => {
  if (!isClosed) {
    return <Tag color="green">開放中</Tag>
  }

  if (closeKind === 'auto') {
    return (
      <Tooltip
        title={
          periodLabel
            ? `期別「${periodLabel}」已過，由系統自動關閉（沒有經手人）`
            : '期別已過，由系統自動關閉（沒有經手人）'
        }
      >
        <Tag
          icon={<ClockCircleOutlined />}
          style={{ background: PINK_BG, borderColor: PINK_BORDER, color: PINK_TEXT }}
        >
          關閉
        </Tag>
      </Tooltip>
    )
  }

  // closeKind === 'manual'，或舊資料沒有 close_kind 時的預設（一律視為人工關閉，
  // 因為系統自動關閉是 2026-08-07 才有的行為，在那之前關的一定是人）
  return (
    <Tooltip title="由人工關閉">
      <Tag color="default" icon={<LockOutlined />}>已關閉</Tag>
    </Tooltip>
  )
}

export default CloseStatusTag
