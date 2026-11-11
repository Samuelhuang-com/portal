/**
 * 戰情 KPI（War Room）— 第一階模組（2026-10-10 新增）
 *
 * 中文名稱：戰情 KPI　英文名稱：War Room
 * 前端路由：/war-room　後端 router：backend/app/routers/war_room.py（/api/v1/war-room）
 * 權限：war_room_view ＋ .env WAR_ROOM_ALLOWED_EMAILS 白名單（系統管理員也受限，CLAUDE.md §11.7）
 *
 * TAB（第一個固定為 Dashboard）：
 *   1. 值班總覽          每個巡檢模組一張卡：燈號、今日異常／未填、涵蓋率、近 7 日趨勢（2026-10-15 新增，第一位）
 *   ─  工務營運中控台    大螢幕用：KPI 列＋3D 樓層＋人員即時清單＋模組燈號＋事件日誌，只看今天、自動刷新（2026-11-10 新增，docs/SPEC_ops_control_center.md）
 *   2. Dashboard        整棟戰情圖：各樓層人員工作／巡檢異常・未填／未完成報修，點擊即檢視
 *   ─  3D 樓層          等角整棟模型（客房逐間、巡檢點位、時間軸人員），2026-10-10 新增
 *   ─  告警            異常告警清單 A1～A5＋預覽寄送＋設定（2026-10-10 新增）
 *   4. 人員動態          與 exec-work-dashboard 同一個元件（StaffPathTab），兩邊功能完全相同；
 *                        另受 STAFF_PATH_ALLOWED_EMAILS 白名單限制
 *   5. 房間／設備履歷    輸入房號或選設備，看報修、IHG 保養、巡檢紀錄
 *   6. 人員工作日誌      人員×日期（MM/DD）全月／區間工作，可篩人員（2026-11-06 新增，口徑同工作日誌 TAB）
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AutoComplete, Button, Card, Col, ConfigProvider, Empty, Result, Row, Select, Space, Spin, Tabs, Tag, Typography } from 'antd'
import { FullscreenExitOutlined, FullscreenOutlined, SettingOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { fetchWarRoomAccess, fetchWarRoomPoints, fetchWarRoomTabConfig, type WrPoint, type WrTabConfig } from '@/api/warRoom'
import { useAuthStore } from '@/stores/authStore'
import { fetchStaffPathAccess } from '@/api/staffPath'
import StaffPathTab from '@/pages/ExecWorkDashboard/StaffPathTab'
import FloorBoard from './FloorBoard'
import FloorIso from './FloorIso'
import AlertsTab from './AlertsTab'
import OverviewTab from './OverviewTab'
import ControlCenterTab from './ControlCenterTab'
import PersonJournalTab from './PersonJournalTab'
import { AssetHistoryPanel, RepairDrawer, type AssetTarget } from './AssetHistory'
import type { WrRepair } from '@/api/warRoom'
import TabSettingsModal from './TabSettingsModal'
import { WR_DEFAULT_HIDDEN, WR_TAB_DEFS } from './tabDefs'

const { Title, Text } = Typography

function HistoryTab({ getContainer }: { getContainer?: () => HTMLElement }) {
  const [rooms, setRooms] = useState<string[]>([])
  const [points, setPoints] = useState<WrPoint[]>([])
  const [roomInput, setRoomInput] = useState('')
  const [target, setTarget] = useState<AssetTarget | null>(null)
  const [repair, setRepair] = useState<WrRepair | null>(null)
  const today = dayjs().format('YYYY-MM-DD')

  useEffect(() => {
    fetchWarRoomPoints()
      .then(d => { setPoints(d.points); setRooms(d.rooms) })
      .catch(() => { setPoints([]); setRooms([]) })
  }, [])

  const pointOptions = useMemo(() => {
    const groups = new Map<string, WrPoint[]>()
    points.forEach(p => {
      const k = `${p.floor_key.toUpperCase()}｜${p.module_label}`
      groups.set(k, [...(groups.get(k) ?? []), p])
    })
    return [...groups.entries()].map(([label, ps]) => ({
      label,
      options: ps.map(p => ({ value: p.id, label: `${p.label}${p.equipment_code ? `（${p.equipment_code}）` : ''}` })),
    }))
  }, [points])

  const goRoom = (r: string) => {
    const v = r.trim()
    if (rooms.includes(v)) setTarget({ type: 'room', room: v })
  }

  return (
    <Row gutter={[12, 12]}>
      <Col xs={24} lg={7}>
        <Card size="small" title="查詢">
          <Text strong>房號</Text>
          <AutoComplete
            style={{ width: '100%', marginTop: 4 }} value={roomInput} placeholder="例：613"
            getPopupContainer={getContainer}
            options={rooms.filter(r => r.startsWith(roomInput.trim())).slice(0, 30).map(r => ({ value: r }))}
            onChange={setRoomInput} onSelect={(v: string) => { setRoomInput(v); goRoom(v) }}
            onKeyDown={e => { if (e.key === 'Enter') goRoom(roomInput) }}
          />
          {roomInput && !rooms.includes(roomInput.trim()) && roomInput.trim().length >= 3 && (
            <Text type="secondary" style={{ fontSize: 12 }}>不在 IHG 規範房號清單</Text>
          )}
          <div style={{ marginTop: 16 }}><Text strong>設備（樓層巡檢圖點位）</Text></div>
          <Select
            showSearch style={{ width: '100%', marginTop: 4 }} placeholder="搜尋設備名稱或編號"
            options={pointOptions} optionFilterProp="label" getPopupContainer={getContainer}
            onChange={(id: number) => {
              const p = points.find(x => x.id === id)
              setTarget({ type: 'point', id, label: p?.label })
            }}
          />
          <div style={{ marginTop: 16, fontSize: 12, color: '#888' }}>
            房間：報修（未完成全列、已完成近 180 天）＋ IHG 客房保養最近 12 次。<br />
            設備：今天的檢查結果＋本月每日狀況。
          </div>
        </Card>
      </Col>
      <Col xs={24} lg={17}>
        <Card size="small" title={target ? (target.type === 'room' ? `房間履歷：${target.room}` : `設備履歷：${target.label ?? ''}`) : '履歷'}>
          <AssetHistoryPanel target={target} date={today} onOpenRepair={setRepair} />
        </Card>
      </Col>
      <RepairDrawer repair={repair} onClose={() => setRepair(null)} getContainer={getContainer}
                    onOpenRoom={r => { setRepair(null); setRoomInput(r); setTarget({ type: 'room', room: r }) }} />
    </Row>
  )
}

/** 各頁簽內容（工務營運中控台只在選中時掛載，離開即停止自動刷新） */
function renderTab(key: string, activeKey: string, getContainer?: () => HTMLElement) {
  switch (key) {
    case 'overview': return <OverviewTab getContainer={getContainer} />
    case 'control': return activeKey === 'control' ? <ControlCenterTab getContainer={getContainer} /> : null
    case 'dashboard': return <FloorBoard getContainer={getContainer} />
    case 'iso': return <FloorIso getContainer={getContainer} />
    case 'alerts': return <AlertsTab getContainer={getContainer} />
    case 'staff': return <StaffPathTab />
    case 'person-journal': return <PersonJournalTab />
    case 'history': return <HistoryTab getContainer={getContainer} />
    default: return null
  }
}

export default function WarRoomPage() {
  const [allowed, setAllowed] = useState<boolean | null>(null)
  const [staffAllowed, setStaffAllowed] = useState(false)
  const [tab, setTab] = useState('')
  const [config, setConfig] = useState<WrTabConfig | null>(null)
  const [editOpen, setEditOpen] = useState(false)
  // 「編輯頁簽」只給系統管理員（後端 PUT 另有 is_system_admin 檢查）
  const isAdmin = useAuthStore(s => !!s.user?.roles?.includes('system_admin'))

  useEffect(() => {
    fetchWarRoomAccess().then(setAllowed)
    fetchStaffPathAccess().then(setStaffAllowed)
    fetchWarRoomTabConfig().then(setConfig).catch(() => setConfig(null))
  }, [])

  // 頁簽：依設定隱藏／改名；載入前或失敗時採預設隱藏清單
  const hidden = new Set(config?.hidden ?? WR_DEFAULT_HIDDEN)
  const visibleTabs = WR_TAB_DEFS.filter(t => (t.key !== 'staff' || staffAllowed) && !hidden.has(t.key))
  const activeKey = visibleTabs.some(t => t.key === tab) ? tab : (visibleTabs[0]?.key ?? '')

  // 全螢幕（整個模組；彈出層掛在容器內，見人員動態 TAB 的同一做法）
  const rootRef = useRef<HTMLDivElement>(null)
  const [isFs, setIsFs] = useState(false)
  useEffect(() => {
    const on = () => setIsFs(document.fullscreenElement === rootRef.current && !!rootRef.current)
    document.addEventListener('fullscreenchange', on)
    return () => document.removeEventListener('fullscreenchange', on)
  }, [])
  const toggleFs = () => {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => undefined)
    else rootRef.current?.requestFullscreen().catch(() => undefined)
  }
  const popup = useCallback(() => rootRef.current ?? document.body, [])
  const getContainer = isFs ? popup : undefined

  if (allowed === null) return <div style={{ padding: 48, textAlign: 'center' }}><Spin /></div>
  if (!allowed) {
    return <Result status="403" title="戰情 KPI 尚未開放" subTitle="此功能目前只開放給指定帳號，如需使用請聯繫系統管理員。" />
  }

  return (
    <ConfigProvider getPopupContainer={popup}>
      <div ref={rootRef} style={isFs ? { position: 'relative', background: '#f0f4f8', height: '100vh', overflow: 'hidden' } : undefined}>
        <div style={isFs ? { height: '100%', overflowY: 'auto', overflowX: 'hidden', padding: 16 } : undefined}>
          <Space align="center" style={{ width: '100%', justifyContent: 'space-between', marginBottom: 4 }} wrap>
            <Space align="baseline">
              <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>戰情 KPI</Title>
              <Tag color="blue">春大直</Tag>
              <Text type="secondary" style={{ fontSize: 12 }}>人員工作 × 巡檢點位 × 未完成報修，依樓層整合</Text>
            </Space>
            <Space size={8}>
              {isAdmin && <Button size="small" icon={<SettingOutlined />} onClick={() => setEditOpen(true)}>編輯頁簽</Button>}
              <Button size="small" type={isFs ? 'default' : 'primary'} ghost={!isFs}
                      icon={isFs ? <FullscreenExitOutlined /> : <FullscreenOutlined />} onClick={toggleFs}>
                {isFs ? '離開全螢幕' : '全螢幕'}
              </Button>
            </Space>
          </Space>
          {visibleTabs.length ? (
            <Tabs
              activeKey={activeKey}
              onChange={setTab}
              items={visibleTabs.map(t => ({
                key: t.key,
                label: config?.labels[t.key] || t.defaultLabel,
                children: renderTab(t.key, activeKey, getContainer),
              }))}
            />
          ) : (
            <Empty description="目前所有頁簽都已隱藏，請系統管理員按「編輯頁簽」開啟" />
          )}
          <TabSettingsModal
            open={editOpen}
            onClose={() => setEditOpen(false)}
            config={config}
            staffAllowed={staffAllowed}
            onSaved={setConfig}
            getContainer={getContainer}
          />
        </div>
      </div>
    </ConfigProvider>
  )
}
