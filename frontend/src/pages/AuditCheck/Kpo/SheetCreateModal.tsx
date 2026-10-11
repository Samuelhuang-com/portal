/**
 * 現場營運稽核 — 新增公司別稽核單 Modal（期別清單與期別明細共用）
 *
 * 2026-10-11 裁示（比照 audit-check 建立方式）：
 *   建立期別 → 新增公司別稽核單 → 「受稽部門」選擇。
 *   受稽部門的來源＝「現場營運稽核項目」的部門（kpoDeptApi.list），**不依公司別過濾**：
 *   公司別與受稽部門未必連動（例如工務部春大直、日曜都有，兩家公司都可以選）。
 *   同一期同一家公司只能有一張稽核單（已建立的公司在下拉中停用）。
 */
import { useEffect, useState } from 'react'
import { Form, Modal, Select, message } from 'antd'

import { refOptionsApi } from '@/api/auditCheck'
import type { RefOption } from '@/api/auditCheck'
import { kpoDeptApi, kpoPeriodApi } from '@/api/auditKpo'
import type { KpoDept, KpoPeriodDetail } from '@/api/auditKpo'

interface Props {
  open: boolean
  periodId: number | null
  periodLabel?: string
  /** 本期已建立稽核單的公司 id（下拉中停用） */
  usedCompanyIds: number[]
  onClose: () => void
  /** 建立成功後回傳最新的期別明細 */
  onCreated: (detail: KpoPeriodDetail) => void
}

export default function SheetCreateModal({ open, periodId, periodLabel, usedCompanyIds, onClose, onCreated }: Props) {
  const [form] = Form.useForm()
  const [companies, setCompanies] = useState<RefOption[]>([])
  const [depts, setDepts] = useState<KpoDept[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    form.resetFields()
    Promise.all([refOptionsApi.companies(), kpoDeptApi.list()])
      .then(([c, d]) => {
        setCompanies(c)
        setDepts(d.data.filter((x) => x.is_active))
      })
      .catch(() => message.error('載入公司別／部門失敗'))
  }, [open, form])

  const submit = async () => {
    if (periodId == null) return
    const v = await form.validateFields()
    setSaving(true)
    try {
      const res = await kpoPeriodApi.createSheet(periodId, {
        company_id: v.company_id, department_ids: v.department_ids,
      })
      message.success('已建立公司稽核單，請為各部門選擇本期稽核項目')
      onCreated(res.data)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail ?? '建立失敗')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title={`新增公司別稽核單${periodLabel ? ` — ${periodLabel}` : ''}`}
      open={open} onOk={submit} onCancel={onClose} confirmLoading={saving}
      okText="建立" cancelText="取消" width={560} destroyOnClose
    >
      <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
        <Form.Item name="company_id" label="公司別" rules={[{ required: true, message: '請選擇公司別' }]}>
          <Select
            placeholder="選擇公司別"
            options={companies.map((c) => ({
              value: c.id, label: usedCompanyIds.includes(c.id) ? `${c.name}（本期已建立）` : c.name,
              disabled: usedCompanyIds.includes(c.id),
            }))}
          />
        </Form.Item>
        <Form.Item
          name="department_ids" label="受稽部門（顯示順序＝選取順序）"
          tooltip="部門來自「現場營運稽核項目」；與公司別無連動，任一公司都可選任一部門"
          rules={[{ required: true, message: '請至少選一個受稽部門' }]}
        >
          <Select
            mode="multiple" placeholder="選擇受稽部門" optionFilterProp="label"
            options={depts.map((d) => ({ value: d.id, label: d.display_name }))}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}
