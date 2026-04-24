import React, { useEffect, useState, useCallback } from 'react';
import {
  Table, Button, Space, Tag, Modal, Form, Input, Select, Switch,
  message, Typography, Card, Popconfirm, Tooltip, Avatar, Row, Col,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, ReloadOutlined,
} from '@ant-design/icons';
import { usersApi, type CreateUserPayload, type UpdateUserPayload } from '../../api/users';
import { tenantsApi } from '../../api/tenants';
import type { User, Tenant } from '../../types';
import { ROLE_LABELS } from '../../types';
import { useAuthStore } from '../../stores/authStore';

const { Title, Text } = Typography;

const ROLE_OPTIONS = Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }));
const ROLE_COLORS: Record<string, string> = {
  system_admin: 'blue', tenant_admin: 'purple', module_manager: 'cyan', viewer: 'default',
};

const UserManagement: React.FC = () => {
  const { user: me } = useAuthStore();
  const [users, setUsers]     = useState<User[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [total, setTotal]     = useState(0);
  const [loading, setLoading] = useState(false);
  const [search, setSearch]   = useState('');
  const [page, setPage]       = useState(1);
  const [modalOpen, setModalOpen]   = useState(false);
  const [editUser, setEditUser]     = useState<User | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await usersApi.list({ page, per_page: 20, search: search || undefined });
      setUsers(data.items);
      setTotal(data.total);
    } catch {
      message.error('載入使用者列表失敗');
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  useEffect(() => {
    tenantsApi.list().then(r => setTenants(r.data)).catch(() => {});
  }, []);

  const openCreate = () => {
    setEditUser(null);
    form.resetFields();
    form.setFieldValue('role_names', ['viewer']);
    setModalOpen(true);
  };

  const openEdit = (user: User) => {
    setEditUser(user);
    form.setFieldsValue({
      full_name: user.full_name,
      is_active: user.is_active,
      role_names: user.roles,
      tenant_id: user.tenant_id,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      if (editUser) {
        const payload: UpdateUserPayload = {
          full_name: values.full_name,
          is_active: values.is_active,
          role_names: values.role_names,
        };
        await usersApi.update(editUser.id, payload);
        message.success('使用者已更新');
      } else {
        const email = values.email.toLowerCase().trim();
        const payload: CreateUserPayload = {
          email: email.includes('@') ? email : `${email}@portal.local`,
          full_name: values.full_name,
          password: values.password,
          tenant_id: values.tenant_id,
          role_names: values.role_names,
        };
        await usersApi.create(payload);
        message.success('使用者已建立');
      }

      setModalOpen(false);
      fetchUsers();
    } catch (err: any) {
      if (err?.response?.data?.detail) {
        message.error(err.response.data.detail);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await usersApi.delete(id);
      message.success('使用者已刪除');
      fetchUsers();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '刪除失敗');
    }
  };

  const handleToggleActive = async (user: User) => {
    try {
      await usersApi.update(user.id, { is_active: !user.is_active });
      message.success(`已${user.is_active ? '停用' : '啟用'} ${user.full_name}`);
      fetchUsers();
    } catch {
      message.error('操作失敗');
    }
  };

  const columns = [
    {
      title: '使用者',
      key: 'user',
      render: (_: unknown, u: User) => (
        <Space>
          <Avatar style={{ background: '#1B3A5C', fontSize: 13 }}>
            {u.full_name.charAt(0).toUpperCase()}
          </Avatar>
          <div>
            <div style={{ fontWeight: 500, color: '#0f172a' }}>{u.full_name}</div>
            <Text type="secondary" style={{ fontSize: 12 }}>{u.email}</Text>
          </div>
        </Space>
      ),
    },
    {
      title: '據點',
      dataIndex: 'tenant_name',
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: '角色',
      dataIndex: 'roles',
      render: (roles: string[]) => (
        <Space size={4} wrap>
          {roles.map(r => (
            <Tag key={r} color={ROLE_COLORS[r] || 'default'} style={{ fontSize: 12 }}>
              {ROLE_LABELS[r] || r}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '狀態',
      dataIndex: 'is_active',
      render: (active: boolean, u: User) => (
        <Switch
          checked={active}
          size="small"
          disabled={u.id === me?.id}
          onChange={() => handleToggleActive(u)}
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, u: User) => (
        <Space>
          <Tooltip title="編輯">
            <Button type="text" size="small" icon={<EditOutlined />} onClick={() => openEdit(u)} />
          </Tooltip>
          {u.id !== me?.id && (
            <Popconfirm
              title="確認刪除此使用者？"
              onConfirm={() => handleDelete(u.id)}
              okText="刪除" cancelText="取消" okButtonProps={{ danger: true }}
            >
              <Tooltip title="刪除">
                <Button type="text" size="small" danger icon={<DeleteOutlined />} />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>人員管理</Title>
          <Text style={{ color: '#64748b' }}>管理所有據點的使用者帳號與權限</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}
          style={{ background: '#1B3A5C', borderColor: '#1B3A5C' }}>
          新增人員
        </Button>
      </div>

      <Card bordered={false} style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
        <Row gutter={8} style={{ marginBottom: 16 }}>
          <Col flex="auto">
            <Input.Search
              placeholder="搜尋姓名或 Email..."
              prefix={<SearchOutlined />}
              value={search}
              onChange={e => setSearch(e.target.value)}
              onSearch={() => { setPage(1); fetchUsers(); }}
              allowClear
            />
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={fetchUsers}>重新整理</Button>
          </Col>
        </Row>

        <Table
          dataSource={users}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            total, pageSize: 20, current: page,
            onChange: p => setPage(p),
            showTotal: t => `共 ${t} 位使用者`,
          }}
          size="middle"
        />
      </Card>

      {/* Create / Edit Modal */}
      <Modal
        title={editUser ? `編輯：${editUser.full_name}` : '新增使用者'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        okText={editUser ? '更新' : '建立'}
        cancelText="取消"
        width={480}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {!editUser && (
            <>
              <Form.Item name="email" label="帳號（Email 或 username）"
                rules={[{ required: true, message: '請輸入帳號' }]}>
                <Input placeholder="例：john.doe 或 john@company.com" />
              </Form.Item>
              <Form.Item name="password" label="密碼"
                rules={[{ required: true, message: '請輸入密碼' }, { min: 8, message: '至少 8 個字元' }]}>
                <Input.Password placeholder="至少 8 個字元" />
              </Form.Item>
            </>
          )}
          <Form.Item name="full_name" label="姓名"
            rules={[{ required: true, message: '請輸入姓名' }]}>
            <Input placeholder="真實姓名" />
          </Form.Item>
          {!editUser && (
            <Form.Item name="tenant_id" label="所屬據點"
              rules={[{ required: true, message: '請選擇據點' }]}>
              <Select placeholder="選擇據點" options={tenants.map(t => ({ value: t.id, label: `${t.name}（${t.code}）` }))} />
            </Form.Item>
          )}
          <Form.Item name="role_names" label="角色"
            rules={[{ required: true, message: '請選擇至少一個角色' }]}>
            <Select mode="multiple" placeholder="選擇角色" options={ROLE_OPTIONS} />
          </Form.Item>
          {editUser && (
            <Form.Item name="is_active" label="帳號狀態" valuePropName="checked">
              <Switch checkedChildren="啟用" unCheckedChildren="停用" />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default UserManagement;
