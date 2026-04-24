import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Layout, Menu, Avatar, Dropdown, Typography, Space, Tag, Tooltip,
} from 'antd';
import {
  DashboardOutlined, TeamOutlined, SafetyOutlined, ApiOutlined,
  AuditOutlined, LogoutOutlined, UserOutlined, MenuFoldOutlined,
  MenuUnfoldOutlined, SettingOutlined, HomeOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import { authApi } from '../../api/auth';
import type { MenuProps } from 'antd';

const { Sider, Header, Content } = Layout;
const { Text } = Typography;

const SIDEBAR_BG = '#111827';
const SIDEBAR_WIDTH = 220;
const COLLAPSED_WIDTH = 64;

type MenuItem = Required<MenuProps>['items'][number];

const AppLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const isAdmin = user?.roles?.includes('system_admin');

  const menuItems: MenuItem[] = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
      onClick: () => navigate('/'),
    },
    isAdmin ? {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系統設定',
      children: [
        { key: '/settings/users', icon: <TeamOutlined />, label: '人員管理', onClick: () => navigate('/settings/users') },
        { key: '/settings/roles', icon: <SafetyOutlined />, label: '角色管理', onClick: () => navigate('/settings/roles') },
        { key: '/settings/ragic', icon: <ApiOutlined />, label: 'Ragic 連線', onClick: () => navigate('/settings/ragic') },
      ],
    } : null,
    {
      key: '/audit',
      icon: <AuditOutlined />,
      label: '稽核日誌',
      onClick: () => navigate('/audit'),
    },
  ].filter(Boolean) as MenuItem[];

  const userMenu: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '個人資料',
      onClick: () => navigate('/profile'),
    },
    { type: 'divider' },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '登出',
      danger: true,
      onClick: async () => {
        try { await authApi.logout(); } catch { /* ignore */ }
        logout();
        navigate('/login');
      },
    },
  ];

  const selectedKeys = [location.pathname];
  const openKeys = location.pathname.startsWith('/settings') ? ['settings'] : [];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* Sidebar */}
      <Sider
        collapsed={collapsed}
        width={SIDEBAR_WIDTH}
        collapsedWidth={COLLAPSED_WIDTH}
        style={{ background: SIDEBAR_BG, position: 'fixed', height: '100vh', left: 0, top: 0, zIndex: 100 }}
      >
        {/* Logo */}
        <div style={{
          height: 56, display: 'flex', alignItems: 'center',
          padding: collapsed ? '0 20px' : '0 20px', gap: 10,
          borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: 'linear-gradient(135deg, #1B3A5C, #4BA8E8)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>
            <HomeOutlined style={{ color: '#fff', fontSize: 16 }} />
          </div>
          {!collapsed && (
            <Text strong style={{ color: '#f9fafb', fontSize: 15, whiteSpace: 'nowrap' }}>
              集團入口
            </Text>
          )}
        </div>

        {/* Navigation Menu */}
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={selectedKeys}
          defaultOpenKeys={openKeys}
          items={menuItems}
          style={{
            background: SIDEBAR_BG,
            border: 'none',
            padding: '8px 0',
          }}
        />

        {/* User info at bottom */}
        {!collapsed && user && (
          <div style={{
            position: 'absolute', bottom: 0, left: 0, right: 0,
            padding: '12px 16px',
            borderTop: '1px solid rgba(255,255,255,0.06)',
            background: 'rgba(0,0,0,0.2)',
          }}>
            <Space size={8}>
              <Avatar size={28} style={{ background: '#1B3A5C', fontSize: 12 }}>
                {user.full_name.charAt(0).toUpperCase()}
              </Avatar>
              <div style={{ minWidth: 0 }}>
                <div style={{ color: '#f9fafb', fontSize: 13, fontWeight: 500, lineHeight: 1.3 }}>
                  {user.full_name}
                </div>
                <div style={{ color: '#6b7280', fontSize: 11 }}>{user.tenant_name}</div>
              </div>
            </Space>
          </div>
        )}
      </Sider>

      {/* Main Layout */}
      <Layout style={{ marginLeft: collapsed ? COLLAPSED_WIDTH : SIDEBAR_WIDTH, transition: 'margin 0.2s' }}>
        {/* Header */}
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #e2e8f0',
          height: 56,
          position: 'sticky',
          top: 0,
          zIndex: 99,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              onClick={() => setCollapsed(!collapsed)}
              style={{ cursor: 'pointer', color: '#64748b', fontSize: 18, lineHeight: 1 }}
            >
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </div>
          </div>

          <Space size={16}>
            {user?.roles?.map(r => (
              <Tag key={r} color={r === 'system_admin' ? 'blue' : 'default'} style={{ margin: 0 }}>
                {r === 'system_admin' ? '系統管理員' :
                 r === 'tenant_admin' ? '據點管理員' :
                 r === 'module_manager' ? '模組主管' : '使用者'}
              </Tag>
            ))}
            <Dropdown menu={{ items: userMenu }} placement="bottomRight" trigger={['click']}>
              <Space style={{ cursor: 'pointer' }}>
                <Avatar style={{ background: '#1B3A5C', fontSize: 14 }}>
                  {user?.full_name?.charAt(0).toUpperCase()}
                </Avatar>
                <Text style={{ fontSize: 14 }}>{user?.full_name}</Text>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        {/* Content */}
        <Content style={{ background: '#f0f4f8', minHeight: 'calc(100vh - 56px)', padding: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
