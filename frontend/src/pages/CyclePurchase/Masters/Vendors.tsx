/**
 * 週期採購 — 供應商主檔維護
 *
 * 2026-07-10 決策：週期採購自建獨立供應商主檔，不與合約模組的 Vendors 共用。
 * 2026-08-10 修訂：改為「單向鏡像同步」——合約模組的廠商主檔是唯一真實來源
 * （其上游是 Ragic 廠商資料表），本頁只是它在 cycle-purchase.db 的副本。
 *
 * 因此本頁的列分兩種：
 *   - 同步（source_vendor_id 非空）：代碼／名稱／統編／聯絡人／電話唯讀，
 *     要改請到「合約管理 → 廠商主檔」或 Ragic 改；付款條件／備註／啟用狀態
 *     仍屬週採自維護，可以編輯。
 *   - 本地自建（source_vendor_id 為 null）：全部欄位可編，同步不會覆蓋。
 *
 * 唯讀限制後端也有擋（cycle_purchase_service.update_vendor），這裡的 disabled
 * 只是提示用途。
 */
import { useEffect, useState } from 'react'
import {
  Alert, Button, Card, Form, Input, Modal, Popconfirm, Space, Switch, Table, Tag, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined, SyncOutlined, CloudDownloadOutlined } from '@ant-design/icons'
import { createVendor, getVendors, syncVendorsFromContract, updateVendor } from '@/api/cyclePurchase'
import type { CpVendor } from '@/types/cyclePurchase'

const { Title } = Typography

/** 是否為「鏡像自合約模組」的供應商 */
const isSynced = (v: CpVendor | null): boolean => !!v?.source_vendor_id

export default function CpVendorsPage() {
  const [vendors, setVendors] = useState<CpVendor[]>([])
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CpVendor | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    getVendors().then((r) => setVendors(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const toggleActive = async (v: CpVendor) => {
    try {
      await updateVendor(v.id, { is_active: !v.is_active })
      message.success(v.is_active ? '已停用' : '已啟用')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '操作失敗')
    }
  }

  /**
   * 自合約模組把廠商主檔同步過來。同步等待（不是背景執行），完成後直接把
   * 這次的異動統計顯示出來——使用者按下去就知道到底同步了什麼，
   * 不用再跑到「設定 → Ragic 連線」看紀錄。
   */
  const handleSync = async () => {
    setSyncing(true)
    try {
      const { data } = await syncVendorsFromContract()
      message.success(
        `同步完成：合約模組共 ${data.fetched} 家，新增 ${data.created} 家、`
        + `更新 ${data.updated} 家、無異動 ${data.unchanged} 家`,
      )
      if (data.skipped > 0) {
        Modal.warning({
          title: `有 ${data.skipped} 家廠商被略過`,
          width: 560,
          content: (
            <div>
              {data.warnings.map((w, i) => <p key={i} style={{ marginBottom: 8 }}>{w}</p>)}
            </div>
          ),
        })
      }
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true })
    setModalOpen(true)
  }

  const openEdit = (v: CpVendor) => {
    setEditing(v)
    // 先清空再填，避免上一次開啟殘留的欄位值被誤送出
    form.resetFields()
    form.setFieldsValue(v)
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      // validateFields() 會回傳整個 form store，而 openEdit 的 setFieldsValue(v)
      // 連 id / created_at / source_vendor_id 都塞了進去。用白名單只挑表單欄位
      // 送出（後端 VendorUpdate 目前會忽略多餘欄位，但不該依賴這件事）。
      const payload = {
        vendor_code: values.vendor_code,
        vendor_name: values.vendor_name,
        tax_id: values.tax_id,
        contact_name: values.contact_name,
        contact_phone: values.contact_phone,
        payment_terms: values.payment_terms,
        notes: values.notes,
        is_active: values.is_active,
      }
      if (editing) {
        await updateVendor(editing.id, payload)
        message.success('更新成功')
      } else {
        await createVendor(payload)
        message.success('新增成功')
      }
      setModalOpen(false)
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (detail) message.error(detail)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>週期採購 — 供應商主檔</Title>
        <Space>
          <Button
            icon={<CloudDownloadOutlined />}
            loading={syncing}
            onClick={handleSync}
          >
            自合約模組同步
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增供應商</Button>
        </Space>
      </div>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="廠商資料來源：合約管理 → 廠商主檔（上游為 Ragic 廠商資料表）"
        description="標示「同步」的供應商，其代碼／名稱／統編／聯絡人／電話由來源端維護，在此為唯讀；付款條件、備註、啟用狀態則屬週期採購自行維護，可直接編輯。要新增或修改廠商基本資料，請到合約管理或 Ragic 操作後，回到這裡按「自合約模組同步」。"
      />

      <Card>
        <Table
          dataSource={vendors}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          columns={[
            {
              title: '來源',
              key: 'source',
              width: 90,
              render: (_: unknown, r: CpVendor) => (isSynced(r)
                ? <Tag icon={<SyncOutlined />} color="blue">同步</Tag>
                : <Tag color="default">本地自建</Tag>),
            },
            { title: '代碼', dataIndex: 'vendor_code', width: 100 },
            { title: '供應商名稱', dataIndex: 'vendor_name' },
            { title: '統編', dataIndex: 'tax_id', width: 110 },
            { title: '聯絡人', dataIndex: 'contact_name', width: 100 },
            { title: '聯絡電話', dataIndex: 'contact_phone', width: 120 },
            { title: '付款條件', dataIndex: 'payment_terms', width: 120 },
            {
              title: '狀態',
              dataIndex: 'is_active',
              width: 80,
              render: (v: boolean) => (v ? <Tag color="green">啟用</Tag> : <Tag color="default">停用</Tag>),
            },
            {
              title: '操作',
              key: 'actions',
              width: 160,
              render: (_: unknown, r: CpVendor) => (
                <Space>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
                  <Popconfirm
                    title={r.is_active ? '確定停用此供應商？' : '確定啟用此供應商？'}
                    onConfirm={() => toggleActive(r)}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Button size="small" danger={r.is_active} icon={r.is_active ? <StopOutlined /> : <CheckCircleOutlined />}>
                      {r.is_active ? '停用' : '啟用'}
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editing ? '編輯供應商' : '新增供應商'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {isSynced(editing) && (
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
              message={`此供應商鏡像自合約模組（${editing?.source_vendor_id}）`}
              description="上方欄位由來源端維護，在此修改無效（下次同步會被覆蓋）。僅付款條件、備註、啟用狀態可在週期採購維護。"
            />
          )}
          <Form.Item name="vendor_code" label="供應商代碼" rules={[{ required: true }]}>
            <Input disabled={!!editing} />
          </Form.Item>
          <Form.Item name="vendor_name" label="供應商名稱" rules={[{ required: true }]}>
            <Input disabled={isSynced(editing)} />
          </Form.Item>
          <Form.Item name="tax_id" label="統一編號">
            <Input disabled={isSynced(editing)} />
          </Form.Item>
          <Form.Item name="contact_name" label="聯絡人">
            <Input disabled={isSynced(editing)} />
          </Form.Item>
          <Form.Item name="contact_phone" label="聯絡電話">
            <Input disabled={isSynced(editing)} />
          </Form.Item>
          <Form.Item name="payment_terms" label="付款條件">
            <Input />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="is_active" label="是否啟用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
