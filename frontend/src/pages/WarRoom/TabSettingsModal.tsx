/**
 * 戰情 KPI — 「編輯頁簽」對話框（2026-11-11 新增，僅系統管理員可開啟）
 *
 * 每個頁簽兩項設定：① 頁簽名稱（留空＝預設名稱）② 顯示／隱藏。
 * 儲存到 PUT /war-room/tab-config（後端另外檢查系統管理員；至少保留一個頁簽）。
 */
import React, { useEffect, useState } from 'react'
import { Button, Input, Modal, Space, Switch, Table, Typography, message } from 'antd'

import { saveWarRoomTabConfig, type WrTabConfig } from '@/api/warRoom'
import { WR_DEFAULT_HIDDEN, WR_TAB_DEFS } from './tabDefs'

const { Text } = Typography
const LABEL_MAX = 30

interface Props {
  open: boolean
  onClose: () => void
  config: WrTabConfig | null
  staffAllowed: boolean
  onSaved: (c: WrTabConfig) => void
  getContainer?: () => HTMLElement
}

export default function TabSettingsModal({ open, onClose, config, staffAllowed, onSaved, getContainer }: Props) {
  const defs = WR_TAB_DEFS.filter(t => t.key !== 'staff' || staffAllowed)
  const [labels, setLabels] = useState<Record<string, string>>({})
  const [hidden, setHidden] = useState<string[]>([])
  const [saving, setSaving] = useState(false)

  // 每次開啟時以目前的設定重新載入草稿
  useEffect(() => {
    if (!open) return
    setLabels({ ...(config?.labels ?? {}) })
    setHidden([...(config?.hidden ?? WR_DEFAULT_HIDDEN)])
  }, [open, config])

  const toggle = (key: string, show: boolean) =>
    setHidden(h => (show ? h.filter(k => k !== key) : [...new Set([...h, key])]))

  const resetDefaults = () => {
    setLabels({})
    setHidden([...WR_DEFAULT_HIDDEN])
  }

  const save = async () => {
    setSaving(true)
    try {
      const payload: Record<string, string | null> = {}
      for (const t of WR_TAB_DEFS) payload[t.key] = (labels[t.key] ?? '').trim() || null
      const saved = await saveWarRoomTabConfig({ labels: payload, hidden })
      onSaved(saved)
      message.success('已儲存頁簽設定')
      onClose()
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '儲存失敗')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title="編輯頁簽"
      onCancel={onClose}
      width={720}
      getContainer={getContainer}
      destroyOnClose
      footer={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Button onClick={resetDefaults}>全部還原預設</Button>
          <Space>
            <Button onClick={onClose}>取消</Button>
            <Button type="primary" loading={saving} onClick={save}>儲存</Button>
          </Space>
        </Space>
      }
    >
      <Text type="secondary" style={{ fontSize: 12 }}>
        名稱留空＝使用預設名稱。關閉「顯示」的頁簽會從戰情 KPI 隱藏（不刪除功能，之後可重新開啟）。至少要保留一個頁簽。
      </Text>
      <Table
        style={{ marginTop: 10 }}
        size="small"
        pagination={false}
        rowKey="key"
        dataSource={defs.map(t => ({ ...t }))}
        columns={[
          { title: '預設名稱', dataIndex: 'defaultLabel', width: 170 },
          {
            title: '頁簽名稱',
            key: 'label',
            render: (_: unknown, t: { key: string; defaultLabel: string }) => (
              <Input
                size="small"
                maxLength={LABEL_MAX}
                placeholder={t.defaultLabel}
                value={labels[t.key] ?? ''}
                onChange={e => setLabels(l => ({ ...l, [t.key]: e.target.value }))}
              />
            ),
          },
          {
            title: '顯示',
            key: 'show',
            width: 90,
            align: 'center' as const,
            render: (_: unknown, t: { key: string }) => (
              <Switch size="small" checked={!hidden.includes(t.key)} onChange={v => toggle(t.key, v)} />
            ),
          },
        ]}
      />
    </Modal>
  )
}
