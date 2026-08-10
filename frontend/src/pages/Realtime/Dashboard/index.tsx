/**
 * 即時營運 — 即時營運看板（/realtime/dashboard）
 *
 * 規格書：docs/SPEC_realtime_operations.md §8.2
 * 使用手冊：docs/MANUAL_realtime_operations.md §3
 *
 * ⚠️ 與 `/opera/*`（人工上傳 TXT）刻意分成兩個一級選單：
 *    兩者資料時點不同（本頁即時 vs 上傳落後數天），放同一群組會被誤讀為同一份資料。
 *
 * 面板本體共用 `pages/Realtime/components/LiveStatusPanel`，
 * 與「營運分析 Dashboard」頂端那一份是**同一個元件**，不重複實作。
 */
import React from 'react'
import { Alert, Space, Typography } from 'antd'

import LiveStatusPanel from '../components/LiveStatusPanel'
import { BRAND } from '@/pages/Opera/components/formatters'

const { Title, Text } = Typography

const RealtimeDashboardPage: React.FC = () => (
  <div style={{ padding: 24 }}>
    <Space direction="vertical" size={4} style={{ marginBottom: 16 }}>
      <Title level={4} style={{ margin: 0, color: BRAND }}>即時營運看板</Title>
      <Text type="secondary" style={{ fontSize: 12 }}>
        資料直接來自 OPERA Cloud（OHIP）REST API，每次查詢都會實際呼叫（按呼叫量計費），
        同一組查詢 5 分鐘內共用快取。
      </Text>
    </Space>

    <Alert
      type="info"
      showIcon
      style={{ marginBottom: 16 }}
      message="這一頁與「營運分析」的資料是兩回事"
      description={
        <span>
          本頁是 <Text strong>此刻</Text>的 OPERA 房況；「營運分析」各頁來自
          <Text strong>人工上傳的 TXT</Text>，會落後現實數天。
          兩者<Text strong>時點不同，請勿混用比較</Text> ——
          若要確認兩邊數字是否一致，請用「與營運分析比對」頁。
        </span>
      }
    />

    <LiveStatusPanel />
  </div>
)

export default RealtimeDashboardPage
