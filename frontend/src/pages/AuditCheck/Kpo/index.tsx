/**
 * 現場營運稽核 — 期別清單
 * route: /audit-check/kpo     permissionKey: audit_check_view
 *
 * 中文名稱：現場營運稽核　英文名稱：Audit KPO　後端 router：audit_kpo.py
 * 對應 Excel：財#1稽核系統建構（整合／2026.11執行）
 *
 * 一期 = 一個月。流程（2026-10-11，比照 audit-check）：
 *   ① 建立期別 → ② 新增公司別稽核單並選「受稽部門」→ ③ 進入期別，依「公司 → 部門 → 稽核項目」
 *   為每個部門選定本期要稽核的項目（通常 1★＋3 項＝25 分），系統自動算出部門／公司／整期小計與本期分數。
 *
 * ⚠️ 選的是「單一月份」，屬 CLAUDE.md §8.4 不適用 StandardRangePicker 的情境。
 */
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button, Card, DatePicker, Form, Input, Modal, Popconfirm, Space, Table, Tag, Typography, message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { BankOutlined, DeleteOutlined, PlusOutlined, ReloadOutlined, UnorderedListOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { kpoPeriodApi } from '@/api/auditKpo'
import type { KpoPeriodSummary } from '@/api/auditKpo'
import { useAuthStore } from '@/stores/authStore'
import SheetCreateModal from './SheetCreateModal'

const { Title, Text } = Typography

export default function AuditKpoIndexPage() {
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canEdit = hasPermission('audit_check_edit')
  const canAdmin = hasPermission('audit_check_admin')

  const [rows, setRows] = useState<KpoPeriodSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()
  const [sheetPeriod, setSheetPeriod] = useState<KpoPeriodSummary | null>(null)   // 正在新增公司稽核單的期別

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await kpoPeriodApi.list()
      setRows(res.data)
    } catch {
      message.error('載入 現場營運稽核期別失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const openCreate = () => {
    form.setFieldsValue({ month: dayjs(), title: '財#1稽核系統建構', note: '' })
    setOpen(true)
  }

  const submit = async () => {
    const v = await form.validateFields()
    setSaving(true)
    try {
      const res = await kpoPeriodApi.create({
        period: (v.month as dayjs.Dayjs).format('YYYY-MM'),
        title: v.title,
        note: v.note || null,
      })
      message.success('已建立期別，請新增公司別稽核單')
      setOpen(false)
      navigate(`/audit-check/kpo/periods/${res.data.id}`)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail ?? '建立失敗')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (id: number) => {
    try {
      await kpoPeriodApi.remove(id)
      message.success('已刪除期別')
      load()
    } catch {
      message.error('刪除失敗')
    }
  }

  const columns: ColumnsType<KpoPeriodSummary> = [
    { title: '期別', dataIndex: 'period', width: 100, render: (v: string) => <b>{v}</b> },
    { title: '標題', dataIndex: 'title' },
    {
      title: '公司別稽核單', width: 220,
      render: (_, r) => (r.sheets.length === 0
        ? <Text type="secondary">尚未建立</Text>
        : (
          <Space size={[4, 4]} wrap>
            {r.sheets.map((sh) => (
              <Tag key={sh.id} color="blue" icon={<BankOutlined />}>{sh.company_name}（{sh.dept_count} 部門）</Tag>
            ))}
          </Space>
        )),
    },
    { title: '選定項數', width: 90, align: 'right', render: (_, r) => r.total.item_count },
    { title: '★ 重點項', width: 90, align: 'right', render: (_, r) => r.total.key_count },
    { title: '滿分', width: 80, align: 'right', render: (_, r) => r.total.full_score },
    { title: '得分', width: 80, align: 'right', render: (_, r) => r.total.earned_score },
    { title: '本期分數', width: 90, align: 'right', render: (_, r) => r.total.score100 ?? '—' },
    {
      title: '符合 / 不符合 / 未查核', width: 170, align: 'center',
      render: (_, r) => (
        <Space size={4}>
          <Tag color="green">{r.total.pass_count}</Tag>
          <Tag color="red">{r.total.fail_count}</Tag>
          <Tag>{r.total.pending_count}</Tag>
        </Space>
      ),
    },
    {
      title: '操作', width: 260, align: 'center',
      render: (_, r) => (
        <Space size={4} onClick={(e) => e.stopPropagation()}>
          {canEdit && (
            <Button size="small" type="link" icon={<PlusOutlined />} onClick={() => setSheetPeriod(r)}>新增公司稽核單</Button>
          )}
          <Button size="small" type="link" icon={<UnorderedListOutlined />}
            onClick={() => navigate(`/audit-check/kpo/periods/${r.id}`)}>開啟</Button>
          {canAdmin && (
            <Popconfirm title="刪除整個期別？該期選定項目與判定都會一併刪除" okText="刪除" okButtonProps={{ danger: true }}
              onConfirm={() => remove(r.id)}>
              <Button size="small" type="text" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }} wrap>
        <div>
          <Title level={4} style={{ margin: 0 }}>現場營運稽核</Title>
          <Text type="secondary">財#1 稽核系統建構：建立期別 → 新增公司別稽核單 → 依受稽部門選定本期稽核項目，並自動小計</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>重新整理</Button>
          {canEdit && <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增期別</Button>}
        </Space>
      </Space>

      <Card size="small">
        <Table rowKey="id" size="small" loading={loading} columns={columns} dataSource={rows}
          pagination={{ pageSize: 20, hideOnSinglePage: true }} scroll={{ x: 1300 }}
          onRow={(r) => ({ onClick: () => navigate(`/audit-check/kpo/periods/${r.id}`), style: { cursor: 'pointer' } })} />
      </Card>

      <SheetCreateModal
        open={!!sheetPeriod} periodId={sheetPeriod?.id ?? null} periodLabel={sheetPeriod?.period}
        usedCompanyIds={(sheetPeriod?.sheets ?? []).map((sh) => sh.company_id)}
        onClose={() => setSheetPeriod(null)}
        onCreated={(d) => { setSheetPeriod(null); navigate(`/audit-check/kpo/periods/${d.id}`) }}
      />

      <Modal title="新增現場營運稽核期別" open={open} onOk={submit} onCancel={() => setOpen(false)}
        confirmLoading={saving} okText="建立" destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="month" label="稽核月份" rules={[{ required: true, message: '請選擇月份' }]}>
            <DatePicker picker="month" style={{ width: '100%' }} allowClear={false} />
          </Form.Item>
          <Form.Item name="title" label="標題" rules={[{ required: true, message: '請輸入標題' }]}>
            <Input maxLength={100} />
          </Form.Item>
          <Form.Item name="note" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
