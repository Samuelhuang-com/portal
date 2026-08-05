/**
 * 回到最上方 — 右下角浮動按鈕
 *
 * 營運分析的幾個頁面（使用手冊、營收分析、住客與通路分析）內容都很長，
 * 統一抽成共用元件，避免三個頁面各自維護一份設定而漸漸走鐘。
 *
 * 實作備註：
 *   Portal 的捲動容器是 **window**（`.ant-layout-content` 本身不捲，
 *   `scrollHeight === clientHeight`），所以用 antd 的預設 target 即可，
 *   不需要傳 `target`。若日後版面改成 Content 內部捲動，這裡要一併改。
 */
import React from 'react'
import { FloatButton } from 'antd'
import { VerticalAlignTopOutlined } from '@ant-design/icons'

interface Props {
  /** 捲動超過多少像素才浮現。預設 300，避免一進頁面就擋住內容 */
  visibilityHeight?: number
}

const BackToTop: React.FC<Props> = ({ visibilityHeight = 300 }) => (
  <FloatButton.BackTop
    visibilityHeight={visibilityHeight}
    duration={400}
    icon={<VerticalAlignTopOutlined />}
    tooltip="回到最上方"
    style={{ right: 32, bottom: 32 }}
  />
)

export default BackToTop
