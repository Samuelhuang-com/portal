/**
 * 人員管理頁
 * 路由：/schedule/staff
 * 權限：schedule_admin
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Button, Card, Form, Input, Modal, Select, Space,
  Switch, Table, Tag, message, Popconfirm, Typography,
} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { fetchStaff, createStaff, updateStaff, deleteStaff, fetchDepartments } from '@/api/schedule'
import type { StaffMember, StaffMemberInput, Department } from '@/types/schedule'

const { Title } = Typography

const EMP_TYPES = ['正職', 'PT', '支援人員']

export default function StaffPage() {
  const [data, setData]         = useState<StaffMember[]>([])
  const [depts, setDepts]       = useState<Department[]>([])
  const [loading, setLoading]   = useState(false)
  const [modalOpen, setModalOpen]   = useState(false)
  const [editing, setEditing]       = useState<StaffMember | null>(null)
  const [filterDept, setFilterDept] = useState<string | undefined>()
  const [filterType, setFilterType] = useState<string | undefined>()
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [staffList, deptList] = await Promise.all([
        fetchStaff({ department_id: filterDept, employment_type: filterType }),
        fetchDepartments(),
      ])
      setData(staffList)
      setDepts(deptList)
    } finally {
      setLoading(false)
    }
  }, [filterDept, filterType])

  useEffect(() => { load() }, [load])

  const openAdd = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ employment_type: '正職', is_active: true })
    setModalOpen(true)
  }

  const openEdit = (row: StaffMember) => {
    setEditing(row)
    form.setFieldsValue({ ...row })
    setModalOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields() as StaffMemberInput
      if (!values.source_name) values.source_name = values.name
      if (editing) {
        await updateStaff(editing.id, values)
        message.success('人員已更新')
      } else {
        await createStaff(values)
        message.success('人員已新增')
      }
      setModalOpen(false)
      load()
    } catch { /* form validation */ }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteStaff(id)
      message.success('人員已停用')
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '操作失敗')
    }
  }

  const EMP_COLOR: Record<string, string> = { 正職: 'blue', PT: 'orange', 支援人員: 'purple' }

  const columns: ColumnsType<StaffMember> = [
    { title: '姓名', dataIndex: 'name', width: 120 },
    { title: 'Excel 原始名稱', dataIndex: 'source_name', width: 140, render: v => v || '—' },
    {
      title: '雇用類型', dataIndex: 'employment_type', width: 100,
      render: v => <Tag color={EMP_COLOR[v] || 'default'}>{v}</Tag>,
    },
    { title: '部門', dataIndex: 'department_name', width: 100, render: v => v || '—' },
    { title: '備註', dataIndex: 'remark', render: v => v || '—' },
    { title: '人員代碼', dataIndex: 'staff_code', width: 100, render: v => v || '—' },
    {
      title: '狀態', dataIndex: 'is_active', width: 80,
      render: v => v ? <Tag color="green">啟用</Tag> : <Tag color="default">停用</Tag>,
    },
    {
      title: '操作', width: 130,
      render: (_, row) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>編輯</Button>
          <Popconfirm title="確認停用此人員？" onConfirm={() => handleDelete(row.id)} okText="確認" cancelText="取消">
            <Button size="small" danger icon={<DeleteOutlined />}>停用</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title={<Title level={4} style={{ margin: 0 }}>人員管理</Title>}
        extra={
          <Space>
            <Select
              allowClear placeholder="篩選部門"
              style={{ width: 130 }}
              value={filterDept}
              onChange={setFilterDept}
              options={depts.map(d => ({ label: d.name, value: d.id }))}
            />
            <Select
              allowClear placeholder="篩選類型"
              style={{ width: 120 }}
              value={filterType}
              onChange={setFilterType}
              options={EMP_TYPES.map(t => ({ label: t, value: t }))}
            />
            <Button icon={<SearchOutlined />} onClick={load}>查詢</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>新增人員</Button>
          </Space>
        }
      >
        <Table
          rowKey="id" columns={columns} dataSource={data}
          loading={loading} size="small"
          pagination={{ pageSize: 50, showSizeChanger: true }}
        />
      </Card>

      <Modal
        title={editing ? '編輯人員' : '新增人員'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        okText="儲存" cancelText="取消" destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="姓名" rules={[{ required: true, message: '請輸入姓名' }]}>
            <Input placeholder="如：陳志明" />
          </Form.Item>
          <Form.Item name="source_name" label="Excel 原始名稱（用於匯入比對）">
            <Input placeholder="如：陳志明(PT)，留空則同姓名" />
          </Form.Item>
          <Form.Item name="staff_code" label="人員代碼（選填）">
            <Input placeholder="如：A001" />
          </Form.Item>
          <Form.Item name="department_id" label="部門">
            <Select
              allowClear placeholder="請選擇部門"
              options={depts.filter(d => d.is_active).map(d => ({ label: d.name, value: d.id }))}
            />
          </Form.Item>
          <Form.Item name="employment_type" label="雇用類型" rules={[{ required: true }]}>
            <Select options={EMP_TYPES.map(t => ({ label: t, value: t }))} />
          </Form.Item>
          <Form.Item name="remark" label="備註">
            <Input placeholder="如：福群、支援" />
          </Form.Item>
          <Form.Item name="is_active" label="狀態" valuePropName="checked">
            <Switch checkedChildren="啟用" unCheckedChildren="停用" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
