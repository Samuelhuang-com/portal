import React from 'react';
import { Card, Table, Tag, Typography } from 'antd';
import { ROLE_LABELS } from '../../types';

const { Title, Text } = Typography;

const ROLE_DETAILS = [
  {
    name: 'system_admin', label: '系統管理員', scope: 'global',
    description: '可操作所有據點、所有模組，最高權限',
    color: 'blue',
  },
  {
    name: 'tenant_admin', label: '據點管理員', scope: 'tenant',
    description: '可操作指定據點的所有模組與使用者',
    color: 'purple',
  },
  {
    name: 'module_manager', label: '模組主管', scope: 'module',
    description: '可跨據點存取特定模組（如集團財務長）',
    color: 'cyan',
  },
  {
    name: 'viewer', label: '一般使用者', scope: 'module',
    description: '唯讀存取指定據點與模組',
    color: 'default',
  },
];

const SCOPE_LABELS: Record<string, string> = {
  global: '全域', tenant: '據點', module: '模組',
};

const Roles: React.FC = () => {
  const columns = [
    {
      title: '角色名稱',
      dataIndex: 'name',
      render: (name: string, r: typeof ROLE_DETAILS[0]) => (
        <Tag color={r.color} style={{ fontSize: 13, padding: '2px 10px' }}>
          {r.label}
        </Tag>
      ),
    },
    {
      title: '識別碼',
      dataIndex: 'name',
      render: (v: string) => <code style={{ fontSize: 12, color: '#64748b' }}>{v}</code>,
    },
    {
      title: '範圍',
      dataIndex: 'scope',
      render: (v: string) => <Tag>{SCOPE_LABELS[v] || v}</Tag>,
    },
    { title: '說明', dataIndex: 'description' },
  ];

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0 }}>角色管理</Title>
        <Text style={{ color: '#64748b' }}>系統內建角色定義，透過人員管理頁面指派</Text>
      </div>

      <Card bordered={false} style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
        <Table
          dataSource={ROLE_DETAILS}
          columns={columns}
          rowKey="name"
          pagination={false}
        />
      </Card>
    </div>
  );
};

export default Roles;
