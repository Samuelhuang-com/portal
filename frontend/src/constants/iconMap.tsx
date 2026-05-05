/**
 * 選單圖示對照表 — 統一真相來源
 *
 * key  = 儲存在 DB icon_key 的字串（如 'DashboardOutlined'）
 * 特殊值：
 *   ''       = 使用 base 結構預設圖示（不覆寫）
 *   'none'   = 不顯示任何圖示
 */
import React from 'react'
import {
  DashboardOutlined,
  BarChartOutlined,
  FundOutlined,
  PieChartOutlined,
  RiseOutlined,
  LineChartOutlined,
  HomeOutlined,
  ShopOutlined,
  EnvironmentOutlined,
  BuildOutlined,
  BulbOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  SettingOutlined,
  ApiOutlined,
  CloudOutlined,
  DatabaseOutlined,
  WifiOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  ScheduleOutlined,
  FileTextOutlined,
  FileDoneOutlined,
  FileSearchOutlined,
  FileOutlined,
  UserOutlined,
  TeamOutlined,
  SafetyOutlined,
  LockOutlined,
  AuditOutlined,
  IdcardOutlined,
  DollarOutlined,
  ShoppingOutlined,
  CarOutlined,
  NotificationOutlined,
  MailOutlined,
  TagOutlined,
  StarOutlined,
  GlobalOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  FireOutlined,
} from '@ant-design/icons'

/** icon_key → React element */
export const ICON_MAP: Record<string, React.ReactElement> = {
  // 統計 / 儀表
  DashboardOutlined:    <DashboardOutlined />,
  BarChartOutlined:     <BarChartOutlined />,
  FundOutlined:         <FundOutlined />,
  PieChartOutlined:     <PieChartOutlined />,
  RiseOutlined:         <RiseOutlined />,
  LineChartOutlined:    <LineChartOutlined />,
  // 建築 / 設施
  HomeOutlined:         <HomeOutlined />,
  ShopOutlined:         <ShopOutlined />,
  EnvironmentOutlined:  <EnvironmentOutlined />,
  BuildOutlined:        <BuildOutlined />,
  BulbOutlined:         <BulbOutlined />,
  ThunderboltOutlined:  <ThunderboltOutlined />,
  // 維護 / 系統
  ToolOutlined:         <ToolOutlined />,
  SettingOutlined:      <SettingOutlined />,
  ApiOutlined:          <ApiOutlined />,
  CloudOutlined:        <CloudOutlined />,
  DatabaseOutlined:     <DatabaseOutlined />,
  WifiOutlined:         <WifiOutlined />,
  // 行事 / 文件
  CalendarOutlined:     <CalendarOutlined />,
  ClockCircleOutlined:  <ClockCircleOutlined />,
  ScheduleOutlined:     <ScheduleOutlined />,
  FileTextOutlined:     <FileTextOutlined />,
  FileDoneOutlined:     <FileDoneOutlined />,
  FileSearchOutlined:   <FileSearchOutlined />,
  FileOutlined:         <FileOutlined />,
  // 人員 / 安全
  UserOutlined:         <UserOutlined />,
  TeamOutlined:         <TeamOutlined />,
  SafetyOutlined:       <SafetyOutlined />,
  LockOutlined:         <LockOutlined />,
  AuditOutlined:        <AuditOutlined />,
  IdcardOutlined:       <IdcardOutlined />,
  // 商業 / 財務
  DollarOutlined:       <DollarOutlined />,
  ShoppingOutlined:     <ShoppingOutlined />,
  CarOutlined:          <CarOutlined />,
  NotificationOutlined: <NotificationOutlined />,
  MailOutlined:         <MailOutlined />,
  TagOutlined:          <TagOutlined />,
  // 其他
  StarOutlined:         <StarOutlined />,
  GlobalOutlined:       <GlobalOutlined />,
  AppstoreOutlined:     <AppstoreOutlined />,
  UnorderedListOutlined:<UnorderedListOutlined />,
  CheckCircleOutlined:  <CheckCircleOutlined />,
  WarningOutlined:      <WarningOutlined />,
  InfoCircleOutlined:   <InfoCircleOutlined />,
  FireOutlined:         <FireOutlined />,
}

/** 分組標籤（供 picker 顯示）*/
export const ICON_GROUPS: Array<{ label: string; keys: string[] }> = [
  { label: '統計 / 儀表', keys: ['DashboardOutlined','BarChartOutlined','FundOutlined','PieChartOutlined','RiseOutlined','LineChartOutlined'] },
  { label: '建築 / 設施', keys: ['HomeOutlined','ShopOutlined','EnvironmentOutlined','BuildOutlined','BulbOutlined','ThunderboltOutlined'] },
  { label: '維護 / 系統', keys: ['ToolOutlined','SettingOutlined','ApiOutlined','CloudOutlined','DatabaseOutlined','WifiOutlined'] },
  { label: '行事 / 文件', keys: ['CalendarOutlined','ClockCircleOutlined','ScheduleOutlined','FileTextOutlined','FileDoneOutlined','FileSearchOutlined','FileOutlined'] },
  { label: '人員 / 安全', keys: ['UserOutlined','TeamOutlined','SafetyOutlined','LockOutlined','AuditOutlined','IdcardOutlined'] },
  { label: '商業 / 財務', keys: ['DollarOutlined','ShoppingOutlined','CarOutlined','NotificationOutlined','MailOutlined','TagOutlined'] },
  { label: '其他',        keys: ['StarOutlined','GlobalOutlined','AppstoreOutlined','UnorderedListOutlined','CheckCircleOutlined','WarningOutlined','InfoCircleOutlined','FireOutlined'] },
]

/** 解析 icon_key → React element（供 sidebar 使用）
 *  - ''     → fallback（呼叫端自行處理）
 *  - 'none' → undefined（不顯示圖示）
 *  - 其他   → ICON_MAP 查找，找不到也 fallback
 */
export function resolveIcon(
  iconKey: string | null | undefined,
  fallback?: React.ReactElement,
): React.ReactElement | undefined {
  if (!iconKey) return fallback
  if (iconKey === 'none') return undefined
  return ICON_MAP[iconKey] ?? fallback
}
