/**
 * 手機殼層底部導覽清單（2026-09-13 新增）
 *
 * ⚠️ 這份清單刻意**與 MainLayout.menuItems 完全分離**。
 *    CLAUDE.md §3 備註：「選單管理頁面自動從 MainLayout.menuItems 派生」，
 *    若把 /m/* 路由加進 menuItems，手機路由會跑進桌面側邊欄與「選單管理」頁面。
 *
 * ⚠️ permissionKey 一律**沿用桌面既有的 key**，不新增任何 key。
 *    這樣 role_permissions.py、navLabels.ts、CLAUDE.md §11.1 的敏感權限計數
 *    都不需要更動，手機版的可見範圍自動與桌面版一致。
 */
import React from 'react'
import { AuditOutlined, ToolOutlined } from '@ant-design/icons'

export interface MobileNavItem {
  /** 路由（必須以 /m 開頭） */
  key: string
  label: string
  icon: React.ReactNode
  /** 沿用桌面版既有的 permission_key；未設定表示所有登入者皆可見 */
  permissionKey?: string
}

export const mobileNavItems: MobileNavItem[] = [
  {
    key: '/m/luqun-repair',
    label: '商場報修',
    icon: <ToolOutlined />,
    permissionKey: 'luqun_repair_view',
  },
  {
    key: '/m/audit-check',
    label: '稽核檢查',
    icon: <AuditOutlined />,
    permissionKey: 'audit_check_view',
  },
]
