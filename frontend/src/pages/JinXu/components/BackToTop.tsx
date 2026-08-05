/**
 * 回到最上方 — 右下角浮動按鈕
 *
 * 金旭分析的使用手冊與幾個明細頁內容很長，統一抽成共用元件。
 *
 * 實作備註：Portal 的捲動容器是 **window**（`.ant-layout-content` 本身不捲），
 * 所以用 antd 預設 target 即可，不需要傳 `target`。
 *
 * ⚠️ 刻意不從 `@/pages/Opera/components/BackToTop` 匯入——業主指定金旭模組與
 *    營運分析完全獨立，不共用程式碼，避免動到一邊時誤傷另一邊。
 */
import React from 'react'
import { FloatButton } from 'antd'
import { VerticalAlignTopOutlined } from '@ant-design/icons'

interface Props {
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
