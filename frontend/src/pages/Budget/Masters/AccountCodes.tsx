/**
 * 會計科目主檔維護 (SCR-14)
 */
import { useEffect, useState } from 'react'
import {
  Button, Card, Form, Input, Modal, Popconfirm, Space, Switch, Table, Tag, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { getAccountCodes, createAccountCode, updateAccountCode, type AccountCode } from '@/api/budget'

const { Title } = Typography

export default function AccountCodesPage() {
  const [codes, setCodes] = useState<AccountCode[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editCode, setEditCode] = useState<AccountCode | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    getAccountCodes().then((r) => setCodes(r.data)).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const toggleActive = async (c: AccountCode) => {
    try {
      await updateAccountCode(c.id, { is_active: (c.is_active ?? 1) === 1 ? 0 : 1 })
      message.success((c.is_active ?? 1) === 1 ? '已停用' : '已啟用')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '操作失敗')
    }
  }

  const openCreate = () => {
    setEditCode(null)
    form.resetFields()
    form.setFieldsValue({ is_raw_group: false })
    setModalOpen(true)
  }

  const openEdit = (c: AccountCode) => {
    setEditCode(c)
    form.setFieldsValue({
      account_code_name: c.account_code_name,
      normalized_name: c.normalized_name,
      is_raw_group: c.is_raw_group === 1,
      notes: c.notes,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const payload = { ...values, is_raw_group: values.is_raw_group ? 1 : 0 }
      if (editCode) {
        await updateAccountCode(editCode.id, payload)
        message.success('更新成功')
      } else {
        await createAccountCode(payload)
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
        <Title level={4} style={{ margin: 0 }}>會計科目主檔維護</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增科目</Button>
      </div>
      <Card>
        <Table
          dataSource={codes}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 50, showTotal: (t) => `共 ${t} 筆` }}
          columns={[
            { title: '#', dataIndex: 'id', width: 60 },
            { title: '科目名稱', dataIndex: 'account_code_name' },
            { title: '正規化鍵', dataIndex: 'normalized_name', ellipsis: true },
            {
              title: '群組科目',
              dataIndex: 'is_raw_group',
              width: 90,
              render: (v: number) => v ? <Tag color="orange">群組</Tag> : null,
            },
            { title: '備註', dataIndex: 'notes', ellipsis: true },
            {
              title: '狀態',
              dataIndex: 'is_active',
              width: 80,
              render: (v: number | undefined) =>
                (v ?? 1) ? <Tag color="green">啟用</Tag> : <Tag color="default">停用</Tag>,
            },
            {
              title: '操作',
              key: 'actions',
              width: 160,
              render: (_: unknown, r: AccountCode) => (
                <Space>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
                  <Popconfirm
                    title={(r.is_active ?? 1) === 1 ? '確定停用此科目？' : '確定啟用此科目？'}
                    onConfirm={() => toggleActive(r)}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Button
                      size="small"
                      danger={(r.is_active ?? 1) === 1}
                      icon={(r.is_active ?? 1) === 1 ? <StopOutlined /> : <CheckCircleOutlined />}
                    >
                      {(r.is_active ?? 1) === 1 ? '停用' : '啟用'}
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editCode ? '編輯會計科目' : '新增會計科目'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="account_code_name" label="科目名稱" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="normalized_name" label="正規化鍵" rules={[{ required: true }]}>
            <Input placeholder="去除空白、符號後的標準鍵，例：郵電費電話費" />
          </Form.Item>
          <Form.Item name="is_raw_group" label="是否群組科目" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
