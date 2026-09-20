/**
 * 稽核檢查 — 手機版稽核單清單（2026-09-20 新增）
 *
 * 路由：/m/audit-check        權限：audit_check_view（與桌面版同一個 key，不新增 key）
 * 資料：GET /audit-check/my-sheets（輕量端點，不回傳整張矩陣，避免 4G 下載一大包）
 *
 * 手機版刻意捨棄的東西（不是漏做）：
 *   - 九欄 × 十幾列的矩陣表格 → 手機看不了，改成「先選部門、再逐項填寫」的流程
 *   - Excel 匯出、版面調整、期別管理 → 留在桌面版
 */
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Empty, List, Progress, Space, Spin, Tag, Typography, message } from 'antd'
import { AuditOutlined, RightOutlined } from '@ant-design/icons'

import { mobileApi } from '@/api/auditCheck'
import type { MobileSheetRow } from '@/api/auditCheck'

const { Text, Title } = Typography

function rateColor(rate: number | null): string {
  if (rate == null) return '#94a3b8'
  if (rate >= 1) return '#52c41a'
  if (rate >= 0.8) return '#4BA8E8'
  return '#cf1322'
}

export default function MobileAuditCheckList() {
  const navigate = useNavigate()
  const [rows, setRows] = useState<MobileSheetRow[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await mobileApi.sheets(20)
      setRows(res.data)
    } catch {
      message.error('載入稽核單失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div>
      <Title level={5} style={{ color: '#1B3A5C', marginTop: 0 }}>
        <AuditOutlined /> 稽核檢查
      </Title>
      <Text type="secondary" style={{ fontSize: 12 }}>選一張稽核單進入填寫</Text>

      <Spin spinning={loading}>
        {rows.length === 0 && !loading ? (
          <Empty description="尚無稽核單" style={{ marginTop: 40 }} />
        ) : (
          <List
            style={{ marginTop: 12 }}
            dataSource={rows}
            renderItem={(r) => (
              <Card
                size="small"
                style={{ marginBottom: 10 }}
                onClick={() => navigate(`/m/audit-check/${r.id}`)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Space direction="vertical" size={2} style={{ flex: 1, minWidth: 0 }}>
                    <Space size={4} wrap>
                      <Tag color="#1B3A5C" style={{ margin: 0 }}>{r.period}</Tag>
                      <Tag color="blue" style={{ margin: 0 }}>{r.company_name}</Tag>
                      {r.status === 'reviewed' && <Tag color="success" style={{ margin: 0 }}>已覆核</Tag>}
                    </Space>
                    <Text style={{ fontSize: 13 }}>{r.title}</Text>
                    <Progress
                      percent={Math.round((r.completion_rate ?? 0) * 100)}
                      size="small"
                      strokeColor={rateColor(r.completion_rate)}
                    />
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {r.completion_label || '尚未填寫'}　{r.audited_on ?? ''}
                    </Text>
                  </Space>
                  <RightOutlined style={{ color: '#bfbfbf' }} />
                </div>
              </Card>
            )}
          />
        )}
      </Spin>
    </div>
  )
}
