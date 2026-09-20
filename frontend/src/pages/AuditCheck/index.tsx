/**
 * 稽核檢查 — 期別清單（模組首頁）
 * route: /audit-check     permissionKey: audit_check_view
 *
 * 一期 = 一個月，底下每家公司一張稽核單（Excel 的一個 Sheet 內兩個區塊）。
 * 這頁負責：建立期別、建立各公司的稽核單（勾選檢查項與部門欄）、進入填寫。
 *
 * ⚠️ 期間選擇用原生 DatePicker picker="month"：本模組選的是「單一月份」而非
 *    區間，屬 CLAUDE.md §8.4 明列的不適用情境，不套 StandardRangePicker。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert, Button, Card, Checkbox, Col, DatePicker, Empty, Form, Input, InputNumber,
  Modal, Popconfirm, Progress, Row, Select, Space, Spin, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  DeleteOutlined, EditOutlined, FileAddOutlined, PlusOutlined, ReloadOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'

import { itemsApi, periodsApi, sheetsApi } from '@/api/auditCheck'
import type { AuditItem, Period, SheetItemSpec } from '@/api/auditCheck'
import { companiesApi, departmentsApi } from '@/api/referenceData'
import type { CompanyRecord, DepartmentRecord } from '@/api/referenceData'
import { useAuthStore } from '@/stores/authStore'

const { Title, Text, Paragraph } = Typography

function rateColor(rate: number | null): string {
  if (rate == null) return '#94a3b8'
  if (rate >= 1) return '#52c41a'
  if (rate >= 0.8) return '#4BA8E8'
  return '#cf1322'
}

export default function AuditCheckPeriodsPage() {
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canEdit = hasPermission('audit_check_edit')
  const canAdmin = hasPermission('audit_check_admin')

  const [periods, setPeriods] = useState<Period[]>([])
  const [companies, setCompanies] = useState<CompanyRecord[]>([])
  const [items, setItems] = useState<AuditItem[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [p, c, i] = await Promise.all([
        periodsApi.list(),
        companiesApi.list(),
        itemsApi.list(),
      ])
      setPeriods(p.data)
      setCompanies(c.data.filter((x) => x.is_active))
      setItems(i.data)
    } catch {
      message.error('載入稽核期別失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // ── 新增期別 ────────────────────────────────────────────────────────────
  const [periodOpen, setPeriodOpen] = useState(false)
  const [periodForm] = Form.useForm()
  const [editingPeriod, setEditingPeriod] = useState<Period | null>(null)

  const openPeriod = (p?: Period) => {
    setEditingPeriod(p ?? null)
    periodForm.setFieldsValue({
      month: p ? dayjs(`${p.period}-01`) : dayjs(),
      title: p?.title ?? '財#3系統建置稽核',
      goal_major: p?.goal_major ?? 3,
      goal_minor: p?.goal_minor ?? 3,
      review_counts_in_score: p ? p.review_counts_in_score : true,
      note: p?.note ?? '',
    })
    setPeriodOpen(true)
  }

  const savePeriod = async () => {
    const v = await periodForm.validateFields()
    try {
      if (editingPeriod) {
        await periodsApi.update(editingPeriod.id, {
          title: v.title, goal_major: v.goal_major, goal_minor: v.goal_minor,
          review_counts_in_score: !!v.review_counts_in_score, note: v.note || null,
        })
      } else {
        await periodsApi.create({
          period: v.month.format('YYYY-MM'),
          title: v.title,
          goal_major: v.goal_major,
          goal_minor: v.goal_minor,
          review_counts_in_score: !!v.review_counts_in_score,
          note: v.note || undefined,
        })
      }
      message.success('已儲存')
      setPeriodOpen(false)
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '儲存失敗')
    }
  }

  // ── 新增稽核單 ──────────────────────────────────────────────────────────
  const [sheetOpen, setSheetOpen] = useState(false)
  const [sheetForm] = Form.useForm()
  const [targetPeriod, setTargetPeriod] = useState<Period | null>(null)
  const [depts, setDepts] = useState<DepartmentRecord[]>([])
  const [pickedItems, setPickedItems] = useState<number[]>([])
  const [saving, setSaving] = useState(false)

  const openSheet = (p: Period) => {
    setTargetPeriod(p)
    setPickedItems([])
    setDepts([])
    sheetForm.resetFields()
    sheetForm.setFieldsValue({
      audited_on: dayjs(`${p.period}-01`),
      audited_session: '上午',
      carry_over: true,
    })
    setSheetOpen(true)
  }

  const onCompanyChange = async (companyId: number) => {
    sheetForm.setFieldsValue({ department_ids: [] })
    try {
      const res = await departmentsApi.list(companyId)
      setDepts(res.data.filter((d) => d.is_active))
    } catch {
      message.error('載入部門失敗')
    }
  }

  const usedCompanyIds = useMemo(
    () => new Set((targetPeriod?.sheets ?? []).map((s) => s.company_id)),
    [targetPeriod],
  )

  const saveSheet = async () => {
    const v = await sheetForm.validateFields()
    if (pickedItems.length === 0) {
      message.warning('請至少勾選一個檢查子項')
      return
    }
    const specs: SheetItemSpec[] = pickedItems.map((id) => ({
      item_id: id,
      target_department_ids: [],
    }))
    setSaving(true)
    try {
      const res = await sheetsApi.create({
        period_id: targetPeriod!.id,
        company_id: v.company_id,
        audited_on: v.audited_on ? v.audited_on.format('YYYY-MM-DD') : null,
        audited_session: v.audited_session ?? null,
        executor_label: v.executor_label || null,
        department_ids: v.department_ids ?? [],
        items: specs,
        carry_over: !!v.carry_over,
      })
      message.success('稽核單已建立')
      setSheetOpen(false)
      navigate(`/audit-check/sheets/${res.data.id}`)
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '建立失敗')
    } finally {
      setSaving(false)
    }
  }

  const minorOptions = useMemo(() => {
    return items.map((major) => ({
      major,
      children: (major.children ?? []).filter((c) => c.is_active),
    })).filter((g) => g.major.is_active)
  }, [items])

  const deletePeriod = async (p: Period) => {
    try {
      await periodsApi.remove(p.id)
      message.success('已刪除')
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '刪除失敗')
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>稽核檢查</Title>
          <Text type="secondary">財#3 系統建置稽核 — 每期各公司抽檢 3 大項 × 3 子項</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重整</Button>
          {canEdit && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => openPeriod()}>新增期別</Button>
          )}
        </Space>
      </div>

      {items.length === 0 && !loading && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="尚未建立檢查項主檔"
          description={
            <span>
              請先到「檢查項主檔」建立 1 階大項與 2 階子項（例如「廠商/客戶管理 → 聯絡簿」），
              才能建立稽核單。
              {canAdmin && (
                <Button type="link" onClick={() => navigate('/audit-check/masters/items')}>前往設定</Button>
              )}
            </span>
          }
        />
      )}

      <Spin spinning={loading}>
        {periods.length === 0 && !loading ? (
          <Empty description="尚無稽核期別" />
        ) : (
          <Row gutter={[16, 16]}>
            {periods.map((p) => (
              <Col key={p.id} xs={24} md={12} xl={8}>
                <Card
                  size="small"
                  title={
                    <Space>
                      <Tag color="#1B3A5C">{p.period}</Tag>
                      <span>{p.title}</span>
                    </Space>
                  }
                  extra={
                    <Space size="small">
                      {canEdit && (
                        <Tooltip title="編輯期別">
                          <Button size="small" type="text" icon={<EditOutlined />} onClick={() => openPeriod(p)} />
                        </Tooltip>
                      )}
                      {canAdmin && (
                        <Popconfirm title="確認刪除此期別？（底下有稽核單時無法刪除）" onConfirm={() => deletePeriod(p)} okText="刪除" cancelText="取消">
                          <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                        </Popconfirm>
                      )}
                    </Space>
                  }
                >
                  {p.sheets.length === 0 ? (
                    <Text type="secondary">尚未建立任何公司的稽核單</Text>
                  ) : (
                    p.sheets.map((s) => (
                      <div
                        key={s.id}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 12,
                          padding: '8px 0', borderBottom: '1px solid #f0f0f0', cursor: 'pointer',
                        }}
                        onClick={() => navigate(`/audit-check/sheets/${s.id}`)}
                      >
                        <Tag color="blue" style={{ margin: 0 }}>{s.company_name}</Tag>
                        <div style={{ flex: 1 }}>
                          <Progress
                            percent={Math.round((s.completion_rate ?? 0) * 100)}
                            size="small"
                            strokeColor={rateColor(s.completion_rate)}
                          />
                          <Text type="secondary" style={{ fontSize: 12 }}>{s.completion_label || '尚未填寫'}</Text>
                        </div>
                        <Text type="secondary" style={{ fontSize: 12 }}>{s.audited_on ?? '—'}</Text>
                      </div>
                    ))
                  )}
                  {canEdit && (
                    <Button
                      block
                      type="dashed"
                      icon={<FileAddOutlined />}
                      style={{ marginTop: 12 }}
                      onClick={() => openSheet(p)}
                    >
                      新增公司稽核單
                    </Button>
                  )}
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Spin>

      {/* ── 期別 Modal ─────────────────────────────────────────────────── */}
      <Modal
        title={editingPeriod ? '編輯稽核期別' : '新增稽核期別'}
        open={periodOpen}
        onOk={savePeriod}
        onCancel={() => setPeriodOpen(false)}
        okText="儲存"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={periodForm} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item name="month" label="期別（月）" rules={[{ required: true, message: '請選擇月份' }]}>
            {/* §8.4：單期選擇，用原生 DatePicker，不用 StandardRangePicker */}
            <DatePicker picker="month" style={{ width: '100%' }} disabled={!!editingPeriod} />
          </Form.Item>
          <Form.Item name="title" label="標題" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="goal_major" label="目標大項數" rules={[{ required: true }]}>
                <InputNumber min={1} max={20} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="goal_minor" label="每大項目標子項數" rules={[{ required: true }]}
                tooltip="稽核完成率的分母 = 勾選大項數 × 這個數字">
                <InputNumber min={1} max={20} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="review_counts_in_score" valuePropName="checked"
            extra="Excel 原表的人工計數是把覆核算進去的（17 個部門欄中 13 欄因此對得上）；若貴單位認為覆核不該影響分數，取消勾選即可。改動會即時重算該期所有分數。">
            <Checkbox>覆核區（待補正項目／結果）計為一個稽核子項</Checkbox>
          </Form.Item>
          <Form.Item name="note" label="稽核方式說明（顯示於分數統計頁）">
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>

      {/* ── 稽核單 Modal ───────────────────────────────────────────────── */}
      <Modal
        title={`新增稽核單 — ${targetPeriod?.period ?? ''}`}
        open={sheetOpen}
        onOk={saveSheet}
        confirmLoading={saving}
        onCancel={() => setSheetOpen(false)}
        okText="建立"
        cancelText="取消"
        width={760}
        destroyOnClose
      >
        <Form form={sheetForm} layout="vertical" style={{ marginTop: 12 }}>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="company_id" label="公司別" rules={[{ required: true, message: '請選擇公司' }]}>
                <Select
                  placeholder="選擇公司"
                  onChange={onCompanyChange}
                  options={companies.map((c) => ({
                    value: c.id,
                    label: c.name,
                    disabled: usedCompanyIds.has(c.id),
                  }))}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="audited_on" label="查核日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="audited_session" label="時段">
                <Select options={[{ value: '上午', label: '上午' }, { value: '下午', label: '下午' }]} allowClear />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="executor_label" label="執行標記" tooltip="Excel 的「台北執行:項數」欄，可留空">
            <Input placeholder="例：台北執行:項數" />
          </Form.Item>

          <Form.Item name="department_ids" label="受稽部門（表格欄位順序＝選取順序）" rules={[{ required: true, message: '請至少選一個部門' }]}>
            <Select
              mode="multiple"
              placeholder="先選公司別，再選部門"
              options={depts.map((d) => ({ value: d.id, label: d.name }))}
              disabled={depts.length === 0}
            />
          </Form.Item>

          <Form.Item label={`本期抽檢項目（已選 ${pickedItems.length} 項）`} required>
            <div style={{ maxHeight: 280, overflow: 'auto', border: '1px solid #f0f0f0', borderRadius: 6, padding: 12 }}>
              {minorOptions.length === 0 && <Empty description="尚無檢查項主檔" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
              {minorOptions.map((g) => (
                <div key={g.major.id} style={{ marginBottom: 12 }}>
                  <Text strong style={{ color: '#1B3A5C' }}>{g.major.name}</Text>
                  <div style={{ paddingLeft: 16, marginTop: 4 }}>
                    <Checkbox.Group
                      value={pickedItems}
                      onChange={(vals) => {
                        const others = pickedItems.filter(
                          (id) => !g.children.some((c) => c.id === id),
                        )
                        setPickedItems([...others, ...(vals as number[])])
                      }}
                      options={g.children.map((c) => ({ value: c.id, label: c.name }))}
                    />
                  </div>
                </div>
              ))}
            </div>
            <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 6, marginBottom: 0 }}>
              勾選子項即可，所屬大項會自動帶入並重新編號（1、1.1、1.2…）。
            </Paragraph>
          </Form.Item>

          <Form.Item name="carry_over" valuePropName="checked">
            <Checkbox>自動帶入上一期未達標項目，作為本期「待補正項目」</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
