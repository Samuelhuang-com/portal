/**
 * 稽核檢查 — 單格明細／編輯 Drawer
 *
 * ⚠️ CLAUDE.md §7 明細 Drawer 強制規範：
 *   - 寬度 480px
 *   - 標題列格式：[Category Tag]  [source_label]：[identifier]  [🔗 在 Ragic 查看]
 *     本模組資料由人工填寫、**沒有 Ragic 來源**，依規範「ragic_url 非空時才顯示」，
 *     故不顯示 Ragic 連結；標題列其餘格式照規範，不自創。
 *   - 分兩區：①基本欄位（Descriptions）②編輯區
 */
import { useEffect, useState } from 'react'
import {
  Alert, Button, Descriptions, Drawer, Input, Radio, Space, Tag, Typography, message,
} from 'antd'
import { LeftOutlined, RightOutlined, SaveOutlined } from '@ant-design/icons'

import { sheetsApi } from '@/api/auditCheck'
import type { Cell, ResultType, SheetDepartment, SheetDetail, SheetItem } from '@/api/auditCheck'

const { Text } = Typography

export interface CellDrawerProps {
  open: boolean
  sheetId: number
  period: string
  companyName: string
  item: SheetItem | null
  majorName: string
  department: SheetDepartment | null
  cell: Cell | undefined
  resultTypes: ResultType[]
  readOnly: boolean
  onClose: () => void
  onSaved: (detail: SheetDetail) => void
  /** -1 = 上一欄部門、1 = 下一欄部門 */
  onNavigate: (delta: number) => void
}

export default function CellDrawer(props: CellDrawerProps) {
  const {
    open, sheetId, period, companyName, item, majorName, department, cell,
    resultTypes, readOnly, onClose, onSaved, onNavigate,
  } = props

  const active = resultTypes.filter((t) => t.is_active)
  const defaultCode = active.find((t) => t.is_default)?.code ?? active[0]?.code ?? 'ok'

  const [comment, setComment] = useState('')
  const [code, setCode] = useState(defaultCode)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setComment(cell?.comment ?? '')
    setCode(cell?.result_code ?? defaultCode)
  }, [open, cell, defaultCode])

  const save = async (thenMove = 0) => {
    if (!item || !department) return
    setSaving(true)
    try {
      const res = await sheetsApi.upsertCell(sheetId, {
        sheet_item_id: item.id,
        sheet_department_id: department.id,
        comment,
        result_code: code,
      })
      onSaved(res.data)
      message.success(comment.trim() ? '已儲存' : '已清空（此格不計入分母）')
      if (thenMove !== 0) onNavigate(thenMove)
      else onClose()
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '儲存失敗')
    } finally {
      setSaving(false)
    }
  }

  const isTarget = !!(item && department && item.target_department_ids.includes(department.department_id))

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={480}
      destroyOnClose
      title={
        <Space size="small" wrap>
          <Tag color="#1B3A5C">{majorName || '檢查項'}</Tag>
          <span style={{ fontWeight: 600 }}>
            {item ? `${item.display_no ?? ''} ${item.name}${item.scope_note ?? ''}` : ''}
            ：{department?.name ?? ''}
          </span>
        </Space>
      }
      footer={
        readOnly ? null : (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Space>
              <Button icon={<LeftOutlined />} onClick={() => onNavigate(-1)}>上一欄</Button>
              <Button onClick={() => onNavigate(1)}>下一欄<RightOutlined /></Button>
            </Space>
            <Space>
              <Button onClick={onClose}>取消</Button>
              <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={() => save(0)}>儲存</Button>
              <Button type="primary" ghost loading={saving} onClick={() => save(1)}>儲存並下一欄</Button>
            </Space>
          </div>
        )
      }
    >
      {/* ① 基本欄位 */}
      <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}>
        <Descriptions.Item label="期別">{period}</Descriptions.Item>
        <Descriptions.Item label="公司別">{companyName}</Descriptions.Item>
        <Descriptions.Item label="大項">{majorName || '—'}</Descriptions.Item>
        <Descriptions.Item label="檢查項">
          {item ? `${item.display_no ?? ''} ${item.name}` : '—'}
          {item?.scope_note ? <Text type="secondary">{item.scope_note}</Text> : null}
        </Descriptions.Item>
        <Descriptions.Item label="部門">{department?.name ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="最後更新">{cell?.updated_at?.replace('T', ' ').slice(0, 16) ?? '—'}</Descriptions.Item>
      </Descriptions>

      {isTarget && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message="本期指定由此部門查核的項目"
        />
      )}

      {/* ② 編輯區 */}
      <div style={{ marginBottom: 8 }}>
        <Text strong>查核評語</Text>
        <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
          留空 ＝ 該部門本期不查此項，不計入分數分母
        </Text>
      </div>
      <Input.TextArea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        rows={8}
        disabled={readOnly}
        placeholder="例：2026.07.13更新"
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && !readOnly) {
            e.preventDefault()
            save(1)
          }
        }}
      />
      <Text type="secondary" style={{ fontSize: 12 }}>Ctrl + Enter：儲存並跳下一欄</Text>

      <div style={{ marginTop: 16, marginBottom: 8 }}>
        <Text strong>判定</Text>
        <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
          類型、顏色與是否算達標，可在「判定類型設定」自行調整
        </Text>
      </div>
      <Radio.Group
        value={code}
        onChange={(e) => setCode(e.target.value)}
        disabled={readOnly}
        optionType="button"
        buttonStyle="solid"
      >
        {active.map((t) => (
          <Radio.Button key={t.code} value={t.code}>
            <span style={{ color: code === t.code ? undefined : t.color }}>
              {t.label}{t.counts_as_pass ? '' : '（不達標）'}
            </span>
          </Radio.Button>
        ))}
      </Radio.Group>
    </Drawer>
  )
}
