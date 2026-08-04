/**
 * 分析門檻設定（/opera/settings）
 * 規格書：docs/SPEC_opera_analytics.md §5.7、§10.4
 *
 * 門檻集中管理，禁止散落程式碼。變更會寫入 audit_log（記錄前後值）。
 */
import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, InputNumber, Space, Table, Tag, Typography, message,
} from 'antd'
import { ReloadOutlined, SaveOutlined, UndoOutlined } from '@ant-design/icons'

import { fetchAnalysisSettings, updateAnalysisSettings } from '@/api/opera'
import type { AnalysisSetting } from '@/types/opera'
import { BRAND, EMPTY, ORANGE } from '../components/formatters'

const { Title, Text } = Typography

/** 百分比型門檻：DB 存 0~1，畫面用 % 呈現比較好懂 */
const PERCENT_KEYS = new Set([
  'high_occupancy_threshold',
  'opportunity_occupancy_threshold',
  'annual_occupancy_diff_pp',
])

const UNIT: Record<string, string> = {
  high_occupancy_threshold: '%',
  opportunity_occupancy_threshold: '%',
  annual_occupancy_diff_pp: '個百分點',
  adr_low_multiplier: '倍',
  adr_high_multiplier: '倍',
  long_stay_nights: '晚',
}

const OperaSettingsPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [items, setItems] = useState<AnalysisSetting[]>([])
  const [draft, setDraft] = useState<Record<string, number>>({})

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchAnalysisSettings()
      setItems(res.items)
      setDraft({})
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入設定失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const currentValue = (row: AnalysisSetting): number =>
    draft[row.setting_key] !== undefined ? draft[row.setting_key] : row.setting_value

  const displayValue = (row: AnalysisSetting): number => {
    const v = currentValue(row)
    return PERCENT_KEYS.has(row.setting_key) ? Number((v * 100).toFixed(2)) : v
  }

  const handleChange = (row: AnalysisSetting, shown: number | null) => {
    if (shown === null || Number.isNaN(shown)) return
    const stored = PERCENT_KEYS.has(row.setting_key) ? shown / 100 : shown
    setDraft((prev) => ({ ...prev, [row.setting_key]: stored }))
  }

  const dirtyKeys = Object.keys(draft).filter((k) => {
    const row = items.find((i) => i.setting_key === k)
    return row && draft[k] !== row.setting_value
  })

  const handleSave = async () => {
    if (dirtyKeys.length === 0) {
      message.info('沒有變更需要儲存')
      return
    }
    setSaving(true)
    try {
      const payload: Record<string, number> = {}
      dirtyKeys.forEach((k) => { payload[k] = draft[k] })
      const res = await updateAnalysisSettings(payload)
      setItems(res.items)
      setDraft({})
      message.success(`已更新 ${res.changed.length} 項設定`)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '儲存失敗')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ color: BRAND }}>分析門檻設定</Title>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="這些門檻只影響「營收異常」與「長住客」的判定，不會改動已匯入的原始資料"
        description="調整後重新開啟營收分析頁即會套用新的判定結果。每次變更都會寫入稽核日誌（記錄變更前後的值與操作者）。"
      />

      <Card
        size="small"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load}>重新載入</Button>
            <Button
              icon={<UndoOutlined />}
              disabled={dirtyKeys.length === 0}
              onClick={() => setDraft({})}
            >
              放棄變更
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={saving}
              disabled={dirtyKeys.length === 0}
              onClick={handleSave}
            >
              {dirtyKeys.length > 0 ? `儲存（${dirtyKeys.length} 項）` : '儲存'}
            </Button>
          </Space>
        }
      >
        <Table
          rowKey="setting_key"
          size="small"
          loading={loading}
          dataSource={items}
          pagination={false}
          columns={[
            { title: '設定項目', dataIndex: 'description', width: 260 },
            {
              title: '設定鍵',
              dataIndex: 'setting_key',
              width: 250,
              render: (v: string) => <Text code style={{ fontSize: 12 }}>{v}</Text>,
            },
            {
              title: '目前值',
              width: 200,
              render: (_, row) => (
                <Space>
                  <InputNumber
                    size="small"
                    style={{ width: 110 }}
                    value={displayValue(row)}
                    min={0}
                    step={PERCENT_KEYS.has(row.setting_key) ? 1 : row.value_type === 'int' ? 1 : 0.1}
                    precision={row.value_type === 'int' ? 0 : 2}
                    onChange={(v) => handleChange(row, v as number | null)}
                  />
                  <Text type="secondary">{UNIT[row.setting_key] || ''}</Text>
                </Space>
              ),
            },
            {
              title: '預設值',
              dataIndex: 'default_value',
              width: 110,
              align: 'right',
              render: (v: number, row) =>
                `${PERCENT_KEYS.has(row.setting_key) ? (v * 100).toFixed(0) : v}${UNIT[row.setting_key] || ''}`,
            },
            {
              title: '狀態',
              width: 110,
              align: 'center',
              render: (_, row) => {
                const isDirty = dirtyKeys.includes(row.setting_key)
                if (isDirty) return <Tag color={ORANGE}>未儲存</Tag>
                return row.is_default ? <Tag>使用預設</Tag> : <Tag color="blue">已自訂</Tag>
              },
            },
            {
              title: '最後更新',
              width: 200,
              render: (_, row) =>
                row.updated_at
                  ? `${row.updated_at}${row.updated_by_name ? `（${row.updated_by_name}）` : ''}`
                  : EMPTY,
            },
          ]}
        />
      </Card>
    </div>
  )
}

export default OperaSettingsPage
