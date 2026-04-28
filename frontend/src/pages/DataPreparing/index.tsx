/**
 * 數據準備中頁面
 * 當使用者點擊自訂選單（custom_* key）且尚未對應實際模組時顯示
 */
import { SyncOutlined } from '@ant-design/icons'
import { Typography } from 'antd'

const { Title, Text } = Typography

export default function DataPreparingPage() {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
        gap: 16,
      }}
    >
      <SyncOutlined
        spin
        style={{ fontSize: 56, color: '#4BA8E8' }}
      />
      <Title level={3} style={{ margin: 0, color: '#1B3A5C' }}>
        數據準備中
      </Title>
      <Text type="secondary" style={{ fontSize: 14 }}>
        此功能模組正在建置，敬請期待
      </Text>
    </div>
  )
}
