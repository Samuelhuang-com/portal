import React, { useEffect, useState, useCallback } from 'react';
import {
  Table, Button, Space, Tag, Modal, Form, Input, Select, Switch,
  message, Typography, Card, Popconfirm, Tooltip, Avatar, Row, Col, Alert,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, ReloadOutlined,
  KeyOutlined, CopyOutlined,
} from '@ant-design/icons';
import { usersApi, type CreateUserPayload, type UpdateUserPayload, type AdminResetPasswordResponse } from '../../api/users';
import { tenantsApi } from '../../api/tenants';
import type { User, Tenant } from '../../types';
import { ROLE_LABELS } from '../../types';
import { useAuthStore } from '../../stores/authStore';
import { fetchRoles, type RoleData } from '@/api/roles';

const { Title, Text } = Typography;

const ROLE_COLORS: Record<string, string> = {
  system_admin: 'blue', tenant_admin: 'purple', module_manager: 'cyan', viewer: 'default',
};

/** 取得角色的顯示名稱（內建角色用中文，自訂角色顯示識別碼） */
function getRoleLabel(roleName: string): string {
  return ROLE_LABELS[roleName] || roleName;
}

const UserManagement: React.FC = () => {
  const { user: me } = useAuthStore();
  const isAdmin = me?.roles?.some(r => ['system_admin', 'tenant_admin'].includes(r)) ?? false;

  const [users, setUsers]     = useState<User[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [allRoles, setAllRoles] = useState<RoleData[]>([]);
  const [total, setTotal]     = useState(0);
  const [loading, setLoading] = useState(false);
  const [search, setSearch]   = useState('');
  const [page, setPage]       = useState(1);
  const [modalOpen, setModalOpen]   = useState(false);
  const [editUser, setEditUser]     = useState<User | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  // ── 管理員重設密碼 Modal ─────────────────────────────────────────────────
  const [resetTarget,   setResetTarget]   = useState<User | null>(null);
  const [resetLoading,  setResetLoading]  = useState(false);
  const [resetResult,   setResetResult]   = useState<AdminResetPasswordResponse | null>(null);

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
    fetchRoles().then(setAllRoles).catch(() => {});
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
      full_name:  user.full_name,
      is_active:  user.is_active,
      role_names: user.roles,
      tenant_id:  user.tenant_id,
      email:      user.email,
    });
    setModalOpen(true);
  };

  // ── 管理員重設密碼 ────────────────────────────────────────────────────────
  const openReset = (user: User) => {
    setResetTarget(user);
    setResetResult(null);
  };

  const handleResetPassword = async () => {
    if (!resetTarget) return;
    setResetLoading(true);
    try {
      const { data } = await usersApi.resetPassword(resetTarget.id);
      setResetResult(data);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '重設密碼失敗');
      setResetTarget(null);
    } finally {
      setResetLoading(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      if (editUser) {
        const payload: UpdateUserPayload = {
          full_name:  values.full_name,
          is_active:  values.is_active,
          role_names: values.role_names,
          email:      values.email !== editUser.email ? values.email : undefined,
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
            <Tag key={r} color={ROLE_COLORS[r] || 'geekblue'} style={{ fontSize: 12 }}>
              {getRoleLabel(r)}
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
          {u.id !== me?.id && isAdmin && (
            <Tooltip title="重設密碼（產生一次性密碼）">
              <Button
                type="text" size="small"
                icon={<KeyOutlined />}
                style={{ color: '#4BA8E8' }}
                onClick={() => openReset(u)}
              />
            </Tooltip>
          )}
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
            <Select
              mode="multiple"
              placeholder="選擇角色"
              options={allRoles.map(r => ({
                value: r.name,
                label: getRoleLabel(r.name),
              }))}
              optionRender={(opt) => {
                const color = ROLE_COLORS[opt.value as string] || 'geekblue';
                return (
                  <Space>
                    <Tag color={color} style={{ margin: 0, fontSize: 12 }} />
                    {opt.label}
                    {!ROLE_LABELS[opt.value as string] && (
                      <span style={{ fontSize: 11, color: '#94a3b8' }}>（自訂）</span>
                    )}
                  </Space>
                );
              }}
            />
          </Form.Item>
          {editUser && isAdmin && (
            <Form.Item
              name="email"
              label="Email（帳號識別碼）"
              extra="修改後使用者須使用新 Email 登入（舊 token 約 30 分鐘後失效）"
              rules={[{ required: true, message: '請輸入 Email' }]}
            >
              <Input placeholder="例：john@company.com 或 john（自動補 @portal.local）" />
            </Form.Item>
          )}
          {editUser && (
            <Form.Item name="is_active" label="帳號狀態" valuePropName="checked">
              <Switch checkedChildren="啟用" unCheckedChildren="停用" />
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* ── 管理員重設密碼 Modal ── */}
      <Modal
        title={`重設密碼：${resetTarget?.full_name ?? ''}`}
        open={!!resetTarget}
        onCancel={() => { setResetTarget(null); setResetResult(null); }}
        footer={
          resetResult ? (
            <Button type="primary" onClick={() => { setResetTarget(null); setResetResult(null); }}
              style={{ background: '#1B3A5C' }}>
              完成
            </Button>
          ) : [
            <Button key="cancel" onClick={() => setResetTarget(null)}>取消</Button>,
            <Button key="ok" type="primary" loading={resetLoading} onClick={handleResetPassword}
              danger>
              確認產生一次性密碼
            </Button>,
          ]
        }
        width={440}
        destroyOnClose
      >
        {resetResult ? (
          <div>
            <Alert
              type="warning"
              showIcon
              message="請將以下一次性密碼口頭告知使用者"
              description={`密碼 ${resetResult.expires_minutes} 分鐘後失效，使用者登入後系統將強制要求設定新密碼。`}
              style={{ marginBottom: 16 }}
            />
            <div style={{
              textAlign: 'center', background: '#f0f4f8', borderRadius: 8,
              padding: '20px 24px', border: '2px dashed #4BA8E8',
            }}>
              <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>一次性密碼</div>
              <div style={{
                fontSize: 40, fontWeight: 700, letterSpacing: 10,
                color: '#1B3A5C', fontFamily: 'monospace',
              }}>
                {resetResult.otp}
              </div>
            </div>
            <div style={{ textAlign: 'center', marginTop: 10 }}>
              <Button
                size="small"
                icon={<CopyOutlined />}
                onClick={() => {
                  navigator.clipboard.writeText(resetResult.otp);
                  message.success('已複製到剪貼簿');
                }}
              >
                複製 OTP
              </Button>
            </div>
          </div>
        ) : (
          <div>
            <Alert
              type="info"
              showIcon
              message="此操作將為該使用者產生一次性登入密碼"
              description={
                <>
                  <div>• OTP 有效期 15 分鐘</div>
                  <div>• 使用者以 OTP 登入後，系統將強制要求設定新密碼</div>
                  <div>• OTP 僅顯示一次，請口頭告知使用者</div>
                </>
              }
            />
          </div>
        )}
      </Modal>
    </div>
  );
};

export default UserManagement;
