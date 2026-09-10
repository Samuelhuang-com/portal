/**
 * 競品分析 — 訂閱與配額
 * Route: /compset/subscribers    Permission: compset_subscriber_admin
 *
 * 規格書：`docs/SPEC_compset_analysis.md` §9.6、§3、§11
 *
 * 【這一頁在做什麼】
 *   管理訂閱客戶（誰有這個模組、開通到哪一級、每月幾次配額），
 *   以及唯一能把額度加上去的動作：手動加發。
 *
 * ⚠️⚠️ **`compset_subscriber_admin` 是敏感權限**（CLAUDE.md §11.1）。
 *      它能改配額、能加發 —— 也就是能決定要花多少錢。不要隨手授權。
 *
 * ── 防提權的三條規則（都在後端強制，這裡只是說明）─────────────────────────
 *   P-1 **不得對自己所屬的訂閱加發**。否則有這個權限的人可以無限自我加值。
 *       前端把按鈕收起來只是體貼，**不是安全機制** —— 後端 403 才是。
 *   P-2 加發端點要求 `compset_subscriber_admin`。
 *   P-3 每一筆加發都留雙份紀錄（加發表 ＋ 稽核日誌），含理由與來源 IP。
 *       所以 `reason` 是必填 —— 沒有理由，事後沒人查得出這筆錢為什麼花掉。
 *
 * ⚠️ 加發**不會改 `monthly_quota`**，只加在當期。這是刻意的：
 *    「這個月臨時多抓一點」不應該悄悄變成「以後每個月都貴一點」。
 */
import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, Descriptions, Drawer, Form, Input, InputNumber, Modal,
  Progress, Select, Space, Switch, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  EditOutlined, HistoryOutlined, PlusCircleOutlined, ReloadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

import {
  fetchGrants, fetchSubscribers, grantQuota, updateSubscriber,
} from '@/api/compset'
import type { PlanLevel, QuotaGrantRow, SubscriberDetail } from '@/types/compset'

const { Text, Paragraph } = Typography

const PLAN_LABEL: Record<PlanLevel, string> = {
  A: 'A 級（近期）', B: 'B 級（近＋中期）', C: 'C 級（全開）',
}

const CompsetSubscribersPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [rows, setRows] = useState<SubscriberDetail[]>([])

  const [editRow, setEditRow] = useState<SubscriberDetail | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const [grantRow, setGrantRow] = useState<SubscriberDetail | null>(null)
  const [granting, setGranting] = useState(false)
  const [grantForm] = Form.useForm()

  const [historyRow, setHistoryRow] = useState<SubscriberDetail | null>(null)
  const [grants, setGrants] = useState<QuotaGrantRow[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchSubscribers()
      setRows(data.items ?? [])
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  /**
   * ⚠️ **不要在這裡 `form.setFieldsValue()`** —— Modal 有 `destroyOnClose`，
   *    此刻 Form 是卸載狀態，寫進去的值會在重新掛載時被 `initialValues` 覆寫回去。
   *    第一次開正常、第二次開變空白，是很難查的症狀。
   *    改用 `initialValues` 當唯一資料來源（同 `pages/Compset/Hotels`）。
   */
  const openEdit = (row: SubscriberDetail) => setEditRow(row)

  /** Form 的 `initialValues`。⚠️ 月配額在 `quota` 底下，不在頂層。 */
  const editInitial = editRow ? {
    name: editRow.name, plan_level: editRow.plan_level,
    monthly_quota: editRow.quota.monthly_quota,
    location_query: editRow.location_query,
    contact_name: editRow.contact_name, contact_email: editRow.contact_email,
    note: editRow.note, is_active: editRow.is_active,
  } : undefined

  const doSave = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      await updateSubscriber(editRow!.id, values)
      message.success('已更新')
      setEditRow(null)
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '儲存失敗')
    } finally {
      setSaving(false)
    }
  }

  const doGrant = async () => {
    const values = await grantForm.validateFields()
    setGranting(true)
    try {
      await grantQuota(grantRow!.id, values.granted_qty, values.reason)
      message.success(`已加發 ${values.granted_qty} 次`)
      setGrantRow(null)
      grantForm.resetFields()
      load()
    } catch (e: any) {
      // 403 ＝ P-1 擋下（對自己所屬的訂閱加發）。訊息本身講得很清楚，直接顯示。
      message.error(e?.response?.data?.detail || '加發失敗')
    } finally {
      setGranting(false)
    }
  }

  const openHistory = async (row: SubscriberDetail) => {
    setHistoryRow(row)
    setGrants([])
    try {
      const data = await fetchGrants(row.id)
      setGrants(data.items ?? [])
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入加發紀錄失敗')
    }
  }

  const columns: ColumnsType<SubscriberDetail> = [
    {
      title: '訂閱客戶', width: 220,
      render: (_, r) => (
        <Space direction="vertical" size={0}>
          <Space size={4}>
            <Text strong>{r.name}</Text>
            {!r.is_active && <Tag>停用</Tag>}
          </Space>
          <Text type="secondary" style={{ fontSize: 11 }}>{r.code}</Text>
        </Space>
      ),
    },
    {
      title: '開通等級', dataIndex: 'plan_level', width: 150,
      render: (v: PlanLevel) => (
        <Tooltip title="累積制：C ＝ A＋B＋C 全開">
          <Tag color={v === 'C' ? 'purple' : v === 'B' ? 'cyan' : 'geekblue'}>
            {PLAN_LABEL[v] ?? v}
          </Tag>
        </Tooltip>
      ),
    },
    {
      title: '本期配額', width: 240,
      render: (_, r) => {
        const q = r.quota
        return (
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <Text style={{ fontSize: 12 }}>
              {q.used} / {q.limit}
              {q.granted > 0 && (
                <Text type="secondary"> （月配額 {q.monthly_quota} ＋ 加發 {q.granted}）</Text>
              )}
            </Text>
            <Progress percent={Math.round(q.usage_ratio * 100)} size="small"
              status={q.is_exhausted ? 'exception' : q.usage_ratio > 0.85 ? 'active' : 'normal'} />
            <Text type="secondary" style={{ fontSize: 11 }}>本期起算 {q.period_start}</Text>
          </Space>
        )
      },
    },
    {
      title: '狀態', width: 110, align: 'center',
      render: (_, r) => (r.quota.is_exhausted
        ? <Tooltip title="已硬停。不會自動恢復，要手動加發才會繼續抓。">
            <Tag color="red">配額用盡</Tag>
          </Tooltip>
        : <Tag color="green">正常</Tag>),
    },
    { title: '聯絡人', dataIndex: 'contact_name', width: 120 },
    {
      title: '操作', width: 230, fixed: 'right',
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
          <Button size="small" type="primary" ghost icon={<PlusCircleOutlined />}
            onClick={() => setGrantRow(r)}>加發</Button>
          <Button size="small" icon={<HistoryOutlined />}
            onClick={() => openHistory(r)} />
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Space direction="vertical" size={0}>
          <Typography.Title level={4} style={{ margin: 0 }}>訂閱與配額</Typography.Title>
          <Text type="secondary">誰有這個模組、開通到哪一級、每月幾次</Text>
        </Space>
        <Button icon={<ReloadOutlined />} onClick={load}>重新整理</Button>
      </Space>

      <Alert type="warning" showIcon style={{ marginBottom: 16 }}
        message="這一頁的操作會直接影響費用"
        description={<>
          手動加發是本模組唯一能提高額度的動作，每一筆都會留下理由、操作者與來源 IP。
          <br />
          <b>不得對自己所屬的訂閱加發</b> —— 這條由後端強制，按下去會被擋（403），
          不是靠畫面隱藏。
          <br />
          加發<b>只加在當期</b>，不會改月配額；要永久調整請用「編輯」改月配額。
        </>} />

      <Card>
        <Table<SubscriberDetail>
          rowKey="id" size="small" loading={loading} columns={columns}
          dataSource={rows} pagination={false} scroll={{ x: 1150 }} />
      </Card>

      {/* ── 編輯訂閱 ─────────────────────────────────────────────────── */}
      <Modal open={!!editRow} title={`編輯訂閱：${editRow?.name ?? ''}`}
        onOk={doSave} confirmLoading={saving} onCancel={() => setEditRow(null)}
        width={600} destroyOnClose>
        <Form form={form} layout="vertical" preserve={false}
          key={editRow?.id ?? 'none'} initialValues={editInitial}>
          <Form.Item name="name" label="名稱" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="plan_level" label="開通等級"
            tooltip="累積制。降級不會刪掉已抓到的歷史資料，只是不再抓新的。">
            <Select options={(['A', 'B', 'C'] as PlanLevel[]).map((v) => ({
              value: v, label: PLAN_LABEL[v],
            }))} />
          </Form.Item>
          <Form.Item name="monthly_quota" label="每月配額（次）"
            tooltip="每期重置的基準值。改這個是永久的；只想這期多一點請用「加發」。"
            rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="location_query" label="地點查詢字串"
            tooltip="B／C 級用這個字串去查一整批飯店。例：台北市大安區 飯店">
            <Input placeholder="例：台北 公館 飯店" />
          </Form.Item>
          <Form.Item name="contact_name" label="聯絡人"><Input /></Form.Item>
          <Form.Item name="contact_email" label="聯絡信箱"><Input /></Form.Item>
          <Form.Item name="note" label="備註"><Input.TextArea rows={2} /></Form.Item>
          {/* ⚠️ 這個欄位必須存在。`validateFields()` 只會回傳**有註冊 Form.Item**
              的欄位，只放進 initialValues 而沒有欄位的話，停用／啟用永遠送不出去
              （畫面看起來有這個設定，實際上按了沒反應）。 */}
          <Form.Item name="is_active" label="啟用中" valuePropName="checked"
            tooltip="停用後排程不再為這個訂閱客戶抓資料，歷史資料保留。">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* ── 手動加發 ─────────────────────────────────────────────────── */}
      <Modal open={!!grantRow} title={`手動加發配額：${grantRow?.name ?? ''}`}
        onOk={doGrant} confirmLoading={granting}
        onCancel={() => { setGrantRow(null); grantForm.resetFields() }}
        okText="確定加發" okButtonProps={{ danger: true }} destroyOnClose>
        <Alert type="error" showIcon style={{ marginBottom: 16 }}
          message="加發等於花錢"
          description={<>
            每一次查詢都是實際的 API 費用。這筆加發會記錄你的帳號與來源 IP，
            並寫進稽核日誌。
            <br />
            只加在<b>當期</b>（{grantRow?.quota.period_start} 起算），
            下一期會回到月配額 {grantRow?.quota.monthly_quota} 次。
          </>} />
        <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}>
          <Descriptions.Item label="目前上限">{grantRow?.quota.limit}</Descriptions.Item>
          <Descriptions.Item label="已使用">{grantRow?.quota.used}</Descriptions.Item>
          <Descriptions.Item label="剩餘">{grantRow?.quota.available}</Descriptions.Item>
        </Descriptions>
        <Form form={grantForm} layout="vertical" preserve={false}>
          <Form.Item name="granted_qty" label="加發次數"
            rules={[{ required: true, message: '請填加發次數' }]}>
            <InputNumber min={1} max={100000} style={{ width: '100%' }}
              placeholder="例：500" />
          </Form.Item>
          <Form.Item name="reason" label="理由"
            tooltip="必填。沒有理由的話，事後沒有人查得出這筆錢為什麼花掉。"
            rules={[{ required: true, message: '請填加發理由' },
                    { min: 4, message: '請寫清楚一點（至少 4 個字）' }]}>
            <Input.TextArea rows={3}
              placeholder="例：9 月連假前臨時要補抓一週遠期資料，經 XXX 同意" />
          </Form.Item>
        </Form>
      </Modal>

      {/* ── 加發紀錄 ─────────────────────────────────────────────────── */}
      <Drawer open={!!historyRow} width={620} onClose={() => setHistoryRow(null)}
        title={`加發紀錄：${historyRow?.name ?? ''}`}>
        <Paragraph type="secondary" style={{ fontSize: 12 }}>
          每一筆加發都留雙份紀錄（這張表 ＋ 系統稽核日誌）。
          這裡看得到理由與操作者；來源 IP 在稽核日誌裡。
        </Paragraph>
        <Table<QuotaGrantRow>
          rowKey="id" size="small" pagination={false} dataSource={grants}
          columns={[
            { title: '加發時間', dataIndex: 'granted_at', width: 160,
              render: (v: string | null) => v || '—' },
            { title: '次數', dataIndex: 'granted_qty', width: 80, align: 'right' },
            { title: '期別', dataIndex: 'period_start', width: 110 },
            { title: '操作者', dataIndex: 'granted_by_user_id', width: 120 },
            { title: '理由', dataIndex: 'reason' },
          ]}
          locale={{ emptyText: '沒有加發紀錄' }} />
      </Drawer>
    </div>
  )
}

export default CompsetSubscribersPage
