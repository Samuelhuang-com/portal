import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Table, Tag, Typography, Tabs, Checkbox, Button,
  message, Spin, Space, Divider, Alert, Modal, Form, Input,
  Popconfirm, Tooltip,
} from 'antd';
import {
  SaveOutlined, LockOutlined, PlusOutlined, DeleteOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import {
  fetchPermissionKeys,
  fetchRolePermissions,
  saveRolePermissions,
  PermissionKeyDef,
} from '@/api/rolePermissions';
import {
  fetchRoles,
  createRole,
  deleteRole,
  RoleData,
} from '@/api/roles';

const { Title, Text } = Typography;

// ── 內建角色顯示設定 ──────────────────────────────────────────────────────────
const BUILTIN_DISPLAY: Record<string, { label: string; color: string; scopeLabel: string }> = {
  system_admin:   { label: '系統管理員', color: 'blue',    scopeLabel: '全域' },
  tenant_admin:   { label: '據點管理員', color: 'purple',  scopeLabel: '據點' },
  module_manager: { label: '模組主管',   color: 'cyan',    scopeLabel: '模組' },
  viewer:         { label: '一般使用者', color: 'default', scopeLabel: '模組' },
};

const SCOPE_LABELS: Record<string, string> = {
  global: '全域', tenant: '據點', module: '模組',
};

function getRoleDisplay(role: RoleData): { label: string; color: string; scopeLabel: string } {
  if (role.is_builtin && BUILTIN_DISPLAY[role.name]) {
    return BUILTIN_DISPLAY[role.name];
  }
  return {
    label: role.name,
    color: 'geekblue',
    scopeLabel: SCOPE_LABELS[role.scope ?? 'tenant'] ?? '據點',
  };
}

// ── 新增角色 Modal ────────────────────────────────────────────────────────────
interface CreateRoleModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (role: RoleData) => void;
}

function CreateRoleModal({ open, onClose, onCreated }: CreateRoleModalProps) {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      const created = await createRole({
        name: values.name.trim(),
        description: values.description?.trim() || undefined,
      });
      message.success(`角色「${created.name}」已建立`);
      form.resetFields();
      onCreated(created);
      onClose();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (detail) message.error(detail);
      // 若是 form 驗證失敗則 validateFields 本身會顯示
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    onClose();
  };

  return (
    <Modal
      title={
        <Space>
          <PlusOutlined style={{ color: '#1B3A5C' }} />
          新增自訂角色
        </Space>
      }
      open={open}
      onOk={handleOk}
      onCancel={handleCancel}
      okText="建立角色"
      cancelText="取消"
      okButtonProps={{ loading: submitting, style: { background: '#1B3A5C' } }}
      width={480}
    >
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item
          label="角色識別碼"
          name="name"
          rules={[
            { required: true, message: '請輸入角色識別碼' },
            {
              pattern: /^[a-z0-9_]+$/,
              message: '只允許小寫英文字母、數字和底線',
            },
            { min: 2, message: '至少 2 個字元' },
            { max: 50, message: '最多 50 個字元' },
          ]}
          extra={
            <span style={{ fontSize: 12, color: '#94a3b8' }}>
              例如：<code>hotel_manager</code>、<code>mall_manager</code>（只限小寫英文、數字、底線）
            </span>
          }
        >
          <Input placeholder="hotel_manager" autoComplete="off" />
        </Form.Item>
        <Form.Item
          label="說明（選填）"
          name="description"
          rules={[{ max: 200, message: '最多 200 字' }]}
        >
          <Input.TextArea rows={2} placeholder="簡短描述此角色的用途或存取範圍" />
        </Form.Item>
      </Form>
      <Alert
        type="info"
        showIcon
        style={{ marginTop: 8 }}
        message="建立後，請至「權限設定」Tab 為此角色指定功能權限，再至「人員管理」頁面將使用者指派至此角色。"
      />
    </Modal>
  );
}

// ── 角色列表 Tab ──────────────────────────────────────────────────────────────
interface RoleListTabProps {
  roles: RoleData[];
  loading: boolean;
  onCreateClick: () => void;
  onDeleted: (roleId: string) => void;
}

function RoleListTab({ roles, loading, onCreateClick, onDeleted }: RoleListTabProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (role: RoleData) => {
    setDeletingId(role.id);
    try {
      await deleteRole(role.id);
      message.success(`角色「${role.name}」已刪除`);
      onDeleted(role.id);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '刪除失敗');
    } finally {
      setDeletingId(null);
    }
  };

  const columns = [
    {
      title: '角色名稱',
      dataIndex: 'name',
      width: 160,
      render: (_: string, r: RoleData) => {
        const { label, color } = getRoleDisplay(r);
        return (
          <Space>
            <Tag color={color} style={{ fontSize: 13, padding: '2px 10px' }}>
              {label}
            </Tag>
            {r.is_builtin && (
              <Tooltip title="系統內建角色，不可刪除">
                <LockOutlined style={{ color: '#94a3b8', fontSize: 12 }} />
              </Tooltip>
            )}
          </Space>
        );
      },
    },
    {
      title: '識別碼',
      dataIndex: 'name',
      width: 200,
      render: (v: string) => <code style={{ fontSize: 12, color: '#64748b' }}>{v}</code>,
    },
    {
      title: '範圍',
      dataIndex: 'scope',
      width: 80,
      render: (v: string) => <Tag>{SCOPE_LABELS[v] || v || '據點'}</Tag>,
    },
    {
      title: '說明',
      dataIndex: 'description',
      render: (v: string | null) => v || <span style={{ color: '#94a3b8' }}>—</span>,
    },
    {
      title: '操作',
      width: 80,
      render: (_: unknown, r: RoleData) => {
        if (r.is_builtin) return null;
        return (
          <Popconfirm
            title="確定要刪除此角色嗎？"
            description={
              <span>
                角色「<b>{r.name}</b>」的所有權限設定與使用者關聯將一併清除，此操作不可復原。
              </span>
            }
            onConfirm={() => handleDelete(r)}
            okText="確定刪除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            icon={<ExclamationCircleOutlined style={{ color: '#ef4444' }} />}
          >
            <Button
              danger
              size="small"
              icon={<DeleteOutlined />}
              loading={deletingId === r.id}
            >
              刪除
            </Button>
          </Popconfirm>
        );
      },
    },
  ];

  return (
    <Card
      bordered={false}
      style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={onCreateClick}
          style={{ background: '#1B3A5C' }}
        >
          新增自訂角色
        </Button>
      }
      title={
        <Text style={{ fontSize: 14, color: '#374151' }}>
          共 {roles.length} 個角色（{roles.filter((r) => r.is_builtin).length} 個內建，
          {roles.filter((r) => !r.is_builtin).length} 個自訂）
        </Text>
      }
    >
      <Table
        dataSource={roles}
        columns={columns}
        rowKey="id"
        pagination={false}
        loading={loading}
        rowClassName={(r) => (r.is_builtin ? '' : 'custom-role-row')}
      />
    </Card>
  );
}

// ── 權限設定 Tab ──────────────────────────────────────────────────────────────
interface PermissionSettingsTabProps {
  roles: RoleData[];
}

function PermissionSettingsTab({ roles }: PermissionSettingsTabProps) {
  const [selectedRole, setSelectedRole] = useState<RoleData | null>(null);
  const [permDefs, setPermDefs] = useState<PermissionKeyDef[]>([]);
  const [checkedKeys, setCheckedKeys] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // 取得所有 permission key 定義
  useEffect(() => {
    fetchPermissionKeys().then(setPermDefs).catch(() => {});
  }, []);

  // 角色清單載入後預設選第一個
  useEffect(() => {
    if (roles.length > 0 && !selectedRole) {
      setSelectedRole(roles[0]);
    }
  }, [roles]);

  // 選中角色變更時載入其 permissions
  const loadRolePermissions = useCallback(async (role: RoleData) => {
    if (role.name === 'system_admin') {
      setCheckedKeys(new Set(['__all__']));
      return;
    }
    setLoading(true);
    try {
      const data = await fetchRolePermissions(role.id);
      setCheckedKeys(new Set(data.permissions));
    } catch {
      message.error('取得角色權限失敗');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedRole) loadRolePermissions(selectedRole);
  }, [selectedRole, loadRolePermissions]);

  const handleSave = async () => {
    if (!selectedRole || selectedRole.name === 'system_admin') return;
    setSaving(true);
    try {
      await saveRolePermissions(selectedRole.id, Array.from(checkedKeys));
      const { label } = getRoleDisplay(selectedRole);
      message.success(`「${label}」的權限已更新`);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '儲存失敗');
    } finally {
      setSaving(false);
    }
  };

  // 依 group 分組
  const groups = Array.from(new Set(permDefs.map((d) => d.group)));
  const isSystemAdmin = selectedRole?.name === 'system_admin';

  return (
    <div style={{ display: 'flex', gap: 20 }}>
      {/* 左側：角色選擇清單 */}
      <Card
        size="small"
        style={{ width: 190, flexShrink: 0 }}
        bodyStyle={{ padding: 8 }}
      >
        <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8, paddingLeft: 4 }}>
          選擇角色
        </div>

        {roles.length === 0 && (
          <div style={{ color: '#94a3b8', fontSize: 12, padding: 8 }}>載入中...</div>
        )}

        {/* 內建角色 */}
        {roles.filter((r) => r.is_builtin).map((r) => {
          const { label, color } = getRoleDisplay(r);
          const isSelected = selectedRole?.id === r.id;
          return (
            <div
              key={r.id}
              onClick={() => setSelectedRole(r)}
              style={{
                padding: '7px 10px',
                borderRadius: 6,
                cursor: 'pointer',
                backgroundColor: isSelected ? '#eff6ff' : 'transparent',
                color: isSelected ? '#1B3A5C' : '#374151',
                fontWeight: isSelected ? 600 : 400,
                marginBottom: 2,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <Tag color={color} style={{ marginRight: 0, fontSize: 11, lineHeight: '18px' }} />
              <span style={{ fontSize: 13 }}>{label}</span>
            </div>
          );
        })}

        {/* 自訂角色分隔 */}
        {roles.some((r) => !r.is_builtin) && (
          <>
            <Divider style={{ margin: '8px 0', fontSize: 11, color: '#94a3b8' }}>自訂角色</Divider>
            {roles.filter((r) => !r.is_builtin).map((r) => {
              const { label, color } = getRoleDisplay(r);
              const isSelected = selectedRole?.id === r.id;
              return (
                <div
                  key={r.id}
                  onClick={() => setSelectedRole(r)}
                  style={{
                    padding: '7px 10px',
                    borderRadius: 6,
                    cursor: 'pointer',
                    backgroundColor: isSelected ? '#eff6ff' : 'transparent',
                    color: isSelected ? '#1B3A5C' : '#374151',
                    fontWeight: isSelected ? 600 : 400,
                    marginBottom: 2,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  <Tag color={color} style={{ marginRight: 0, fontSize: 11, lineHeight: '18px' }} />
                  <span style={{ fontSize: 13 }}>{label}</span>
                </div>
              );
            })}
          </>
        )}
      </Card>

      {/* 右側：權限 checkbox */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {!selectedRole ? (
          <div style={{ color: '#94a3b8', padding: 20 }}>請選擇左側角色</div>
        ) : isSystemAdmin ? (
          <Alert
            icon={<LockOutlined />}
            type="info"
            message="system_admin 擁有所有權限（萬用符 *），無法個別設定"
            description="若需限制管理員存取範圍，請建立新角色並指派適當權限。"
            showIcon
          />
        ) : (
          <Spin spinning={loading}>
            <Card
              bordered={false}
              style={{ boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}
              extra={
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSave}
                  loading={saving}
                  style={{ background: '#1B3A5C' }}
                >
                  儲存權限
                </Button>
              }
              title={
                <Space>
                  {(() => {
                    const { label, color } = getRoleDisplay(selectedRole);
                    return <Tag color={color}>{label}</Tag>;
                  })()}
                  <Text style={{ fontSize: 13, color: '#64748b' }}>的功能權限設定</Text>
                </Space>
              }
            >
              {groups.map((group) => {
                const groupDefs = permDefs.filter((d) => d.group === group);
                const groupKeys = groupDefs.map((d) => d.key);
                const allChecked = groupKeys.every((k) => checkedKeys.has(k));
                const someChecked = groupKeys.some((k) => checkedKeys.has(k));

                return (
                  <div key={group} style={{ marginBottom: 20 }}>
                    <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Checkbox
                        indeterminate={someChecked && !allChecked}
                        checked={allChecked}
                        onChange={(e) => {
                          const next = new Set(checkedKeys);
                          if (e.target.checked) groupKeys.forEach((k) => next.add(k));
                          else groupKeys.forEach((k) => next.delete(k));
                          setCheckedKeys(next);
                        }}
                      >
                        <span style={{ fontWeight: 600, color: '#1B3A5C' }}>{group}</span>
                      </Checkbox>
                    </div>
                    <div style={{ paddingLeft: 24, display: 'flex', flexWrap: 'wrap', gap: '6px 0' }}>
                      {groupDefs.map((def) => (
                        <div key={def.key} style={{ width: '33%', minWidth: 200 }}>
                          <Checkbox
                            checked={checkedKeys.has(def.key)}
                            onChange={(e) => {
                              const next = new Set(checkedKeys);
                              if (e.target.checked) next.add(def.key);
                              else next.delete(def.key);
                              setCheckedKeys(next);
                            }}
                          >
                            <span style={{ fontSize: 13 }}>{def.label}</span>
                            <code style={{ fontSize: 10, color: '#94a3b8', marginLeft: 4 }}>
                              {def.key}
                            </code>
                          </Checkbox>
                        </div>
                      ))}
                    </div>
                    <Divider style={{ margin: '12px 0 0' }} />
                  </div>
                );
              })}
            </Card>
          </Spin>
        )}
      </div>
    </div>
  );
}

// ── 主元件 ────────────────────────────────────────────────────────────────────
const Roles: React.FC = () => {
  const [roles, setRoles] = useState<RoleData[]>([]);
  const [rolesLoading, setRolesLoading] = useState(true);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('roles');

  const loadRoles = useCallback(async () => {
    setRolesLoading(true);
    try {
      const data = await fetchRoles();
      setRoles(data);
    } catch {
      message.error('無法取得角色清單，請確認後端服務正常');
    } finally {
      setRolesLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRoles();
  }, [loadRoles]);

  const handleRoleCreated = (newRole: RoleData) => {
    setRoles((prev) => [...prev, newRole]);
  };

  const handleRoleDeleted = (roleId: string) => {
    setRoles((prev) => prev.filter((r) => r.id !== roleId));
  };

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0 }}>角色管理</Title>
        <Text style={{ color: '#64748b' }}>
          管理系統角色與功能權限。內建角色不可刪除；可新增自訂角色並透過「權限設定」Tab 指派所需功能存取範圍。
        </Text>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'roles',
            label: '角色清單',
            children: (
              <RoleListTab
                roles={roles}
                loading={rolesLoading}
                onCreateClick={() => setCreateModalOpen(true)}
                onDeleted={handleRoleDeleted}
              />
            ),
          },
          {
            key: 'permissions',
            label: '權限設定',
            children: <PermissionSettingsTab roles={roles} />,
          },
        ]}
      />

      <CreateRoleModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onCreated={handleRoleCreated}
      />
    </div>
  );
};

export default Roles;
