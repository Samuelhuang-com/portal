/**
 * 庫存管理 › 領用單 — 常用品領用範本（Phase 4b，2026-11-17，SPEC §7.4）
 *
 * 範本＝某個倉（部門）固定領的料號與預設數量，開單時一鍵帶出；只是預設清單，不影響庫存。
 *   - TemplatesModal：依倉庫列出範本、看內容、刪除
 *   - SaveTemplateModal：把目前開單畫面的明細存成範本（名稱與既有範本相同＝覆寫該範本）
 * 權限：開單者只能管理所屬部門倉的範本；倉管可管理全部（後端強制）
 */
import { useCallback, useEffect, useState } from 'react'
import { Alert, AutoComplete, Button, Empty, Input, List, Modal, Popconfirm, Select, Space, Tag, Typography, message } from 'antd'
import { DeleteOutlined } from '@ant-design/icons'
import {
  createIssueTemplate, deleteIssueTemplate, errMsg, fetchIssueTemplates, updateIssueTemplate,
  type IssueMeta, type IssueTemplate,
} from '@/api/stock'

const { Text } = Typography
const num = (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 4 })

export function TemplatesModal({ code, meta, open, onClose }: { code: string; meta: IssueMeta; open: boolean; onClose: () => void }) {
  const [whId, setWhId] = useState<number | undefined>()
  const [rows, setRows] = useState<IssueTemplate[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try { setRows((await fetchIssueTemplates(code, whId)).data) }
    catch (e) { message.error(errMsg(e, '讀取範本失敗')) } finally { setLoading(false) }
  }, [code, whId])
  useEffect(() => { if (open) load() }, [open, load])

  const doDelete = async (t: IssueTemplate) => {
    try { await deleteIssueTemplate(code, t.id); message.success(`已刪除範本「${t.name}」`); load() }
    catch (e) { message.error(errMsg(e, '刪除失敗')) }
  }

  return (
    <Modal open={open} title="常用品領用範本" width={720} onCancel={onClose} footer={<Button onClick={onClose}>關閉</Button>}>
      <Alert type="info" showIcon style={{ marginBottom: 12 }}
        message="新增或修改範本：在「新增領用單」裡選好料號與數量後按「存成範本」；名稱和既有範本相同就是覆寫。" />
      <Select allowClear placeholder="全部倉庫" style={{ width: 260, marginBottom: 12 }} value={whId} onChange={setWhId}
        options={meta.my_warehouses.map((w) => ({ value: w.id, label: w.department_name ? `${w.name}（${w.department_name}）` : w.name }))} />
      <List loading={loading} dataSource={rows} locale={{ emptyText: <Empty description="還沒有範本" /> }}
        renderItem={(t) => (
          <List.Item actions={[
            <Popconfirm key="del" title={`刪除範本「${t.name}」？`} description="只刪範本，不影響任何單據與庫存" onConfirm={() => doDelete(t)}>
              <Button type="text" danger icon={<DeleteOutlined />} aria-label="刪除範本" />
            </Popconfirm>,
          ]}>
            <List.Item.Meta
              title={<Space><span>{t.name}</span><Tag>{t.warehouse_name}</Tag></Space>}
              description={(
                <Space direction="vertical" size={2}>
                  <Text type="secondary">{t.lines.map((l) => `${l.item_name} × ${num(l.qty)}${l.unit ?? ''}`).join('、')}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>{`${t.updated_by ?? t.created_by ?? ''} ${t.updated_at ?? ''}`}</Text>
                </Space>)} />
          </List.Item>)} />
    </Modal>
  )
}

export function SaveTemplateModal({ code, warehouseId, lines, open, onClose }: {
  code: string; warehouseId?: number; lines: { item_id?: number; qty?: number }[]; open: boolean; onClose: () => void
}) {
  const [name, setName] = useState('')
  const [existing, setExisting] = useState<IssueTemplate[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open || !warehouseId) return
    setName('')
    fetchIssueTemplates(code, warehouseId).then((r) => setExisting(r.data)).catch(() => setExisting([]))
  }, [open, code, warehouseId])

  const use = lines.filter((l) => l.item_id && (l.qty ?? 0) > 0) as { item_id: number; qty: number }[]
  const hit = existing.find((t) => t.name === name.trim())

  const save = async () => {
    if (!warehouseId) { message.warning('請先選倉庫'); return }
    if (!name.trim()) { message.warning('請輸入範本名稱'); return }
    if (!use.length) { message.warning('至少要有一筆料號與數量'); return }
    setSaving(true)
    try {
      const body = { warehouse_id: warehouseId, name: name.trim(), lines: use.map((l) => ({ item_id: l.item_id, qty: l.qty })) }
      if (hit) await updateIssueTemplate(code, hit.id, body)
      else await createIssueTemplate(code, body)
      message.success(hit ? `已覆寫範本「${name.trim()}」` : `已存成範本「${name.trim()}」`)
      onClose()
    } catch (e) { message.error(errMsg(e, '存範本失敗')) } finally { setSaving(false) }
  }

  return (
    <Modal open={open} title="存成領用範本" onCancel={onClose} onOk={save} confirmLoading={saving} okText={hit ? '覆寫範本' : '儲存'}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Text type="secondary">{`共 ${use.length} 筆料號，會記下料號與數量。`}</Text>
        <AutoComplete style={{ width: '100%' }} value={name} onChange={setName}
          options={existing.map((t) => ({ value: t.name }))}>
          <Input placeholder="範本名稱（例：每週清潔用品）" maxLength={100} />
        </AutoComplete>
        {hit && <Alert type="warning" showIcon message={`已有同名範本，儲存會覆寫「${hit.name}」原本的 ${hit.lines.length} 筆內容`} />}
      </Space>
    </Modal>
  )
}
