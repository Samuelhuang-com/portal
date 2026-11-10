import React, { useEffect, useState, useCallback } from 'react';
import {
  Table, Button, Space, Tag, Modal, Form, Input, Select, Switch,
  message, Typography, Card, Popconfirm, Tooltip, Avatar, Row, Col, Alert,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, ReloadOutlined,
  KeyOutlined,
} from '@ant-design/icons';
import { usersApi, type CreateUserPayload, type UpdateUserPayload } from '../../api/users';
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
  // 可指派角色（後端 /users/grantable-roles）；null＝尚未載入或端點失敗
  const [grantable, setGrantable] = useState<string[] | null>(null);
  // 目前登入者是否為系統管理員（permissions 含 * 或持有 system_admin 角色）
  const isSuperAdmin = (me?.permissions?.includes('*') ?? false)
    || (me?.roles?.includes('system_admin') ?? false);
  // 刪除權限：獨立權限 settings_users_delete（角色管理指派）；系統管理員恆有
  const canDelete = isSuperAdmin || (me?.permissions?.includes('settings_users_delete') ?? false);
  const [total, setTotal]     = useState(0);
  const [loading, setLoading] = useState(false);
  const [search, setSearch]   = useState('');
  const [page, setPage]       = useState(1);
  const [modalOpen, setModalOpen]   = useState(false);
  const [editUser, setEditUser]     = useState<User | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  // ── 管理員直接設定密碼 Modal（不經 OTP，2026-11-10）──────────────────────
  const [pwdTarget,     setPwdTarget]     = useState<User | null>(null);
  const [pwdSubmitting, setPwdSubmitting] = useState(false);
  const [pwdForm]                         = Form.useForm();

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
    usersApi.grantableRoles().then(r => setGrantable(r.data)).catch(() => setGrantable(null));
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

  // 受保護列：對方持有 system_admin、而我不是系統管理員 → 不可編輯／停用／重設密碼／刪除
  const isProtectedRow = (u: User) =>
    !isSuperAdmin && (u.roles ?? []).includes('system_admin');

  // 角色下拉：只列出目前登入者可指派的角色（2026-09-30）
  //  - 非系統管理員看不到「系統管理員」，也看不到含有自己沒有權限的角色（後端同規則會回 403）
  //  - 編輯時對方已持有、但我無權指派的角色仍顯示為 disabled，避免 Tag 變成英文代碼
  //  - grantable 端點失敗（例如後端未重啟）時退回最低限度規則：非系統管理員隱藏 system_admin
  const roleOptions = React.useMemo(() => {
    const canGrant = (name: string) =>
      grantable ? grantable.includes(name) : (isSuperAdmin || name !== 'system_admin');
    const current: string[] = editUser?.roles ?? [];
    return allRoles
      .filter(r => canGrant(r.name) || current.includes(r.name))
      .map(r => ({
        value: r.name,
        label: getRoleLabel(r.name),
        disabled: !canGrant(r.name),
      }));
  }, [allRoles, grantable, isSuperAdmin, editUser]);

  const openCreate = () => {
    setEditUser(null);
    form.resetFields();
    // 預設「一般使用者」；若目前登入者無權指派 viewer 就不預帶
    if (!grantable || grantable.includes('viewer')) {
      form.setFieldValue('role_names', ['viewer']);
    }
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
  const openSetPassword = (user: User) => {
    setPwdTarget(user);
    pwdForm.resetFields();
  };

  const handleSetPassword = async () => {
    if (!pwdTarget) return;
    try {
      const values = await pwdForm.validateFields();
      setPwdSubmitting(true);
      await usersApi.setPassword(pwdTarget.id, values.new_password);
      message.success(`已更新 ${pwdTarget.full_name} 的密碼`);
      setPwdTarget(null);
    } catch (err: any) {
      if (err?.response?.data?.detail) {
        message.error(err.response.data.detail);
      }
    } finally {
      setPwdSubmitting(false);
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
          disabled={u.id === me?.id || isProtectedRow(u)}
          onChange={() => handleToggleActive(u)}
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, u: User) => isProtectedRow(u) ? (
        // 2026-09-30：非系統管理員不能編輯／重設密碼／刪除「系統管理員」（後端同樣會回 403）
        <Tooltip title="系統管理員帳號僅能由系統管理員維護">
          <Space>
            <Button type="text" size="small" icon={<EditOutlined />} disabled />
            <Button type="text" size="small" icon={<KeyOutlined />} disabled />
          </Space>
        </Tooltip>
      ) : (
        <Space>
          <Tooltip title="編輯">
            <Button type="text" size="small" icon={<EditOutlined />} onClick={() => openEdit(u)} />
          </Tooltip>
          {u.id !== me?.id && (
            <Tooltip title="設定新密碼">
              <Button
                type="text" size="small"
                icon={<KeyOutlined />}
                style={{ color: '#4BA8E8' }}
                onClick={() => openSetPassword(u)}
              />
            </Tooltip>
          )}
          {/* 刪除需 settings_users_delete（系統管理員恆有）；後端另擋對 system_admin 帳號的刪除 */}
          {u.id !== me?.id && canDelete && (
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
              options={roleOptions}
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

      {/* ── 管理員直接設定密碼 Modal（不經 OTP）── */}
      <Modal
        title={`設定密碼：${pwdTarget?.full_name ?? ''}`}
        open={!!pwdTarget}
        onOk={handleSetPassword}
        onCancel={() => setPwdTarget(null)}
        confirmLoading={pwdSubmitting}
        okText="確認設定"
        cancelText="取消"
        width={440}
        destroyOnClose
      >
        <Alert
          type="info"
          showIcon
          message="直接設定使用者的新密碼，設定後立即生效"
          description="不會強制使用者再次更改密碼；請另行告知對方新密碼。"
          style={{ marginBottom: 16 }}
        />
        <Form form={pwdForm} layout="vertical">
          <Form.Item
            name="new_password"
            label="新密碼"
            rules={[{ required: true, message: '請輸入新密碼' }, { min: 8, message: '至少 8 個字元' }]}
          >
            <Input.Password placeholder="至少 8 個字元" />
          </Form.Item>
          <Form.Item
            name="confirm_password"
            label="確認新密碼"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '請再輸入一次' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) return Promise.resolve();
                  return Promise.reject(new Error('兩次輸入的密碼不一致'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="再輸入一次" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default UserManagement;
