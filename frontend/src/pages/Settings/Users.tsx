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
import { departmentsApi, type DepartmentOption } from '@/api/referenceData';
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
  // 部門選項（含 id／公司），供「部門（多選）」按公司分組（2026-09-01）
  const [deptOptions, setDeptOptions] = useState<DepartmentOption[]>([]);
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
    departmentsApi.options().then(r => setDeptOptions(r.data)).catch(() => {});
  }, []);

  // 部門多選：按公司分組（AntD Select 的 options 支援群組格式）
  const deptGroupOptions = React.useMemo(() => {
    const groups = new Map<string, { label: string; options: { value: number; label: string }[] }>();
    for (const d of deptOptions) {
      if (d.id == null) continue;               // 舊版後端沒帶 id 就跳過
      const company = d.company || '（未分類）';
      if (!groups.has(company)) groups.set(company, { label: company, options: [] });
      groups.get(company)!.options.push({ value: d.id, label: d.label });
    }
    return Array.from(groups.values());
  }, [deptOptions]);

  const openCreate = () => {
    setEditUser(null);
    form.resetFields();
    form.setFieldValue('role_names', ['viewer']);
    setModalOpen(true);
  };

  const openEdit = (user: User) => {
    setEditUser(user);
    form.setFieldsValue({
      full_name:      user.full_name,
      is_active:      user.is_active,
      role_names:     user.roles,
      tenant_id:      user.tenant_id,
      email:          user.email,
      department_ids: (user.departments ?? []).map(d => d.id),
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
          full_name:    values.full_name,
          is_active:    values.is_active,
          role_names:   values.role_names,
          email:        values.email !== editUser.email ? values.email : undefined,
          new_password: values.new_password || undefined, // 留空則不傳
          // 沒變就不傳：後端只在值不同時才動 user_roles 的 tenant_id，
          // 少送一個欄位就少一次沒必要的搬移。
          tenant_id:    values.tenant_id !== editUser.tenant_id ? values.tenant_id : undefined,
          department_ids: values.department_ids ?? [],
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
          department_ids: values.department_ids ?? [],
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
      // 2026-09-01 起這一欄的值來自「系統設定 → 公司/部門管理」的公司名稱，
      // 欄名改用「公司別」與該頁一致（原本叫「據點」）。
      title: '主要公司別',
      dataIndex: 'tenant_name',
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      // 2026-09-01：多公司多部門（user_departments）。顯示「公司／部門」。
      title: '部門',
      dataIndex: 'departments',
      render: (depts: User['departments']) => (
        <Space size={4} wrap>
          {(depts ?? []).length
            ? (depts ?? []).map(d => (
                <Tag key={d.id} color="blue" style={{ fontSize: 12 }}>{d.company}／{d.name}</Tag>
              ))
            : <Text type="secondary" style={{ fontSize: 12 }}>—</Text>}
        </Space>
      ),
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
          <Text style={{ color: '#64748b' }}>管理所有公司別的使用者帳號與權限</Text>
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
          {/*
            2026-09-01 起「公司別」的選項＝「系統設定 → 公司/部門管理」的
            公司名稱（由 backend/app/services/tenant_company_sync.py 單向鏡像
            到 tenants，GET /tenants 只回 is_active 的列）。

            ⚠️ 欄位名稱原本是「所屬據點」，2026-09-01 改為「公司別」與公司/部門
            管理頁面一致。**只改顯示文字**：`name="tenant_id"`、API 欄位、資料表
            名稱一律不動（那是 tenants 表，語意上仍是據點，只是現在的內容來自
            公司主檔）。

            label 刻意只顯示 t.name、不再帶「（t.code）」：鏡像新增的據點 code
            是自動產生的 CMP-{公司id} 佔位值，顯示出來只是雜訊，也會讓下拉
            看起來跟公司/部門管理的清單對不起來。

            ⚠️ 2026-09-01：這個欄位原本包在 `{!editUser && (...)}` 裡，只有
            「新增」看得到 —— 於是同仁調公司時只能砍帳號重建。改成建立與編輯
            都顯示（後端 UserUpdate.tenant_id 同步開放）。
          */}
          <Form.Item name="tenant_id" label="主要公司別"
            extra="顯示與稽核歸屬用；實際的公司/部門權限看下方「部門」"
            rules={[{ required: true, message: '請選擇公司別' }]}>
            <Select
              placeholder="選擇公司"
              showSearch
              optionFilterProp="label"
              options={[
                // ⚠️ 若這個人目前掛在已停用的舊據點上，該筆不在 `GET /tenants`
                //    的回傳裡，Select 會找不到對應選項而直接顯示原始 UUID。
                //    補一筆唯讀用的選項讓它顯示得出名稱。沒改就不會送出
                //    tenant_id（見 handleSubmit），所以不會被後端的「停用據點
                //    不可指派」擋下來。
                ...(editUser && !tenants.some(t => t.id === editUser.tenant_id)
                  ? [{ value: editUser.tenant_id, label: `${editUser.tenant_name}（已停用）` }]
                  : []),
                ...tenants.map(t => ({ value: t.id, label: t.name })),
              ]}
            />
          </Form.Item>
          {/*
            部門（多選，按公司分組）— 2026-09-01 多公司多部門。
            存 RefDepartment.id 進 user_departments；週採「同部門可操作請購單」
            的權限判斷走這裡（見 cycle_purchase_requests._ensure_own_department）。
          */}
          <Form.Item name="department_ids" label="部門"
            extra="可跨公司多選；週期採購等模組以此判斷可操作的部門">
            <Select
              mode="multiple"
              placeholder="選擇部門（可多選）"
              showSearch
              optionFilterProp="label"
              options={deptGroupOptions}
            />
          </Form.Item>
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
          {editUser && isAdmin && (
            <Form.Item
              name="new_password"
              label="重設密碼"
              extra="留空表示不修改密碼；至少 8 個字元"
              rules={[{ min: 8, message: '至少 8 個字元' }]}
            >
              <Input.Password placeholder="輸入新密碼（選填）" />
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
