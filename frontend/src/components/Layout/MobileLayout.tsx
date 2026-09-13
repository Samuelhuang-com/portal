/**
 * MobileLayout — 手機殼層（2026-09-13 新增）
 *
 * 與 MainLayout 平行的第二套殼層，掛在 /m/* 路由底下。
 * 桌面版 MainLayout 完全不受影響，本檔不 import 也不修改它。
 *
 * 結構：
 *   ┌──────────────────────────┐
 *   │ Header 56px（品牌色 #1B3A5C）│  ← 標題 + 使用者選單
 *   ├──────────────────────────┤
 *   │        <Outlet />         │  ← padding 12（桌面是 24）
 *   ├──────────────────────────┤
 *   │ 底部 TabBar（≥2 項才顯示）  │
 *   └──────────────────────────┘
 *
 * ⚠️ 這裡必須自己呼叫 /me 補 permissions（見下方註解），
 *    否則非 system_admin 使用者在手機版重新整理後會看到永久空白畫面。
 */
import { useCallback, useEffect, useMemo } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Avatar, Button, Dropdown, Modal, Space, Typography } from 'antd'
import {
  UserOutlined,
  LogoutOutlined,
  DesktopOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'

import { useAuthStore } from '@/stores/authStore'
import { authApi } from '@/api/auth'
import { useIdleTimeout } from '@/hooks/useIdleTimeout'
import { setUiMode } from '@/utils/uiMode'
import { mobileNavItems } from '@/components/Layout/mobileMenuItems'
import { getSiteTitle } from '@/config/siteConfig'

const { Text } = Typography

// ── 版型常數（沿用 CLAUDE.md §2 受保護色碼／尺寸，不另創一套）──────────────
const HEADER_HEIGHT = 56
const TABBAR_HEIGHT = 56
const BRAND_COLOR   = '#1B3A5C'
const ACCENT_COLOR  = '#4BA8E8'
const PAGE_BG       = '#f0f4f8'

export default function MobileLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const user    = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const logout  = useAuthStore((s) => s.logout)
  const hasPermission = useAuthStore((s) => s.hasPermission)

  // ── 登出 ──────────────────────────────────────────────────────────────────
  const handleLogout = useCallback(async () => {
    try { await authApi.logout() } catch { /* ignore */ }
    logout()
    navigate('/login')
  }, [logout, navigate])

  // ── 閒置自動登出（與桌面版同一套規則：15 分鐘 + 2 分鐘倒數）──────────────
  const { warningVisible, countdown, resetTimer } = useIdleTimeout(
    handleLogout,
    !!user,
  )

  // ── 補載 permissions ──────────────────────────────────────────────────────
  // JWT 不含 permissions，頁面重新整理後 user.permissions 會是 undefined。
  // 桌面版是由 MainLayout 負責呼叫 /me 補回；手機殼層不經過 MainLayout，
  // 所以必須自己做一份，否則 PermissionGuard 的
  // `permissions === undefined → return null` 會讓畫面永久空白。
  useEffect(() => {
    const u = useAuthStore.getState().user
    if (!u?.id || u.permissions !== undefined) return

    authApi.me().then((res) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const me = res.data as any
      setUser({
        id:          me.id          || u.id,
        email:       me.email       || u.email,
        name:        me.full_name   || u.name || '',
        full_name:   me.full_name   || '',
        tenant_id:   me.tenant_id   || '',
        tenant_name: me.tenant_name || '',
        roles:       Array.isArray(me.roles)       ? me.roles       : u.roles,
        permissions: Array.isArray(me.permissions) ? me.permissions : [],
        is_active:   me.is_active ?? true,
      })
    }).catch(() => {
      // /me 失敗時也必須把 permissions 從 undefined 改成 []，
      // 否則 PermissionGuard 會永遠等下去（同桌面版的處理）。
      const current = useAuthStore.getState().user
      if (current && current.permissions === undefined) {
        setUser({ ...current, permissions: [] })
      }
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── 底部導覽（依權限過濾）─────────────────────────────────────────────────
  const visibleNav = useMemo(
    () => mobileNavItems.filter(
      (it) => !it.permissionKey || hasPermission(it.permissionKey),
    ),
    // user.permissions 變動時要重算
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [hasPermission, user?.permissions],
  )

  // 只有一個項目時不顯示 TabBar（一顆按鈕的導覽列沒有意義，只是佔掉 56px）
  const showTabBar = visibleNav.length >= 2

  // ── 切換到桌面版 ──────────────────────────────────────────────────────────
  const goDesktop = useCallback(() => {
    setUiMode('desktop')
    navigate('/', { replace: true })
  }, [navigate])

  const displayName = user?.full_name || user?.name || user?.email || '使用者'

  return (
    <div style={{ minHeight: '100vh', background: PAGE_BG }}>
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header
        style={{
          position: 'fixed',
          top: 0, left: 0, right: 0,
          height: HEADER_HEIGHT,
          background: BRAND_COLOR,
          color: '#fff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 12px',
          zIndex: 100,
        }}
      >
        <span style={{ fontSize: 16, fontWeight: 600, letterSpacing: 0.5 }}>
          {getSiteTitle()}
        </span>

        <Dropdown
          trigger={['click']}
          menu={{
            items: [
              {
                key: 'desktop',
                icon: <DesktopOutlined />,
                label: '切換到桌面版',
                onClick: goDesktop,
              },
              { type: 'divider' },
              {
                key: 'logout',
                icon: <LogoutOutlined />,
                label: '登出',
                danger: true,
                onClick: handleLogout,
              },
            ],
          }}
        >
          <Space size={6} style={{ cursor: 'pointer' }}>
            <Avatar size={28} icon={<UserOutlined />} style={{ background: ACCENT_COLOR }} />
            <span style={{ fontSize: 13, maxWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {displayName}
            </span>
          </Space>
        </Dropdown>
      </header>

      {/* ── 內容 ─────────────────────────────────────────────────────────── */}
      <main
        style={{
          paddingTop: HEADER_HEIGHT + 12,
          paddingLeft: 12,
          paddingRight: 12,
          paddingBottom: (showTabBar ? TABBAR_HEIGHT : 0) + 16,
        }}
      >
        <Outlet />
      </main>

      {/* ── 底部 TabBar ──────────────────────────────────────────────────── */}
      {showTabBar && (
        <nav
          style={{
            position: 'fixed',
            bottom: 0, left: 0, right: 0,
            height: TABBAR_HEIGHT,
            background: '#fff',
            borderTop: '1px solid #e8eaed',
            display: 'flex',
            zIndex: 100,
          }}
        >
          {visibleNav.map((it) => {
            const active = location.pathname.startsWith(it.key)
            return (
              <div
                key={it.key}
                onClick={() => navigate(it.key)}
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 2,
                  color: active ? BRAND_COLOR : '#8c8c8c',
                  fontSize: 11,
                  cursor: 'pointer',
                }}
              >
                <span style={{ fontSize: 18 }}>{it.icon}</span>
                <span>{it.label}</span>
              </div>
            )
          })}
        </nav>
      )}

      {/* ── 閒置警告（與桌面版同一套規則）───────────────────────────────── */}
      <Modal
        open={warningVisible}
        closable={false}
        maskClosable={false}
        centered
        width="90%"
        title={
          <Space>
            <ExclamationCircleOutlined style={{ color: '#FAAD14' }} />
            <span>閒置逾時提醒</span>
          </Space>
        }
        footer={
          <Button type="primary" block onClick={resetTimer}>繼續使用</Button>
        }
      >
        <Text>
          您已閒置一段時間，<Text strong style={{ color: '#FF4D4F' }}>{countdown}</Text> 秒後將自動登出。
        </Text>
      </Modal>
    </div>
  )
}
