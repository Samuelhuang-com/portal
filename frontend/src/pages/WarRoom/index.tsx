/**
 * 戰情 KPI（War Room）— 第一階模組（2026-10-10 新增）
 *
 * 中文名稱：戰情 KPI　英文名稱：War Room
 * 前端路由：/war-room　後端 router：backend/app/routers/war_room.py（/api/v1/war-room）
 * 權限：war_room_view ＋ .env WAR_ROOM_ALLOWED_EMAILS 白名單（系統管理員也受限，CLAUDE.md §11.7）
 *
 * TAB（第一個固定為 Dashboard）：
 *   1. 值班總覽          每個巡檢模組一張卡：燈號、今日異常／未填、涵蓋率、近 7 日趨勢（2026-10-15 新增，第一位）
 *   2. Dashboard        整棟戰情圖：各樓層人員工作／巡檢異常・未填／未完成報修，點擊即檢視
 *   ─  3D 樓層          等角整棟模型（客房逐間、巡檢點位、時間軸人員），2026-10-10 新增
 *   ─  告警            異常告警清單 A1～A5＋預覽寄送＋設定（2026-10-10 新增）
 *   4. 人員動態          與 exec-work-dashboard 同一個元件（StaffPathTab），兩邊功能完全相同；
 *                        另受 STAFF_PATH_ALLOWED_EMAILS 白名單限制
 *   5. 房間／設備履歷    輸入房號或選設備，看報修、IHG 保養、巡檢紀錄
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AutoComplete, Button, Card, Col, ConfigProvider, Result, Row, Select, Space, Spin, Tabs, Tag, Typography } from 'antd'
import { FullscreenExitOutlined, FullscreenOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { fetchWarRoomAccess, fetchWarRoomPoints, type WrPoint } from '@/api/warRoom'
import { fetchStaffPathAccess } from '@/api/staffPath'
import StaffPathTab from '@/pages/ExecWorkDashboard/StaffPathTab'
import FloorBoard from './FloorBoard'
import FloorIso from './FloorIso'
import AlertsTab from './AlertsTab'
import OverviewTab from './OverviewTab'
import { AssetHistoryPanel, RepairDrawer, type AssetTarget } from './AssetHistory'
import type { WrRepair } from '@/api/warRoom'

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

export default function WarRoomPage() {
  const [allowed, setAllowed] = useState<boolean | null>(null)
  const [staffAllowed, setStaffAllowed] = useState(false)
  const [tab, setTab] = useState('overview')

  useEffect(() => {
    fetchWarRoomAccess().then(setAllowed)
    fetchStaffPathAccess().then(setStaffAllowed)
  }, [])

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
            <Button size="small" type={isFs ? 'default' : 'primary'} ghost={!isFs}
                    icon={isFs ? <FullscreenExitOutlined /> : <FullscreenOutlined />} onClick={toggleFs}>
              {isFs ? '離開全螢幕' : '全螢幕'}
            </Button>
          </Space>
          <Tabs
            activeKey={tab}
            onChange={setTab}
            items={[
              { key: 'overview', label: '值班總覽', children: <OverviewTab getContainer={getContainer} /> },
              { key: 'dashboard', label: 'Dashboard', children: <FloorBoard getContainer={getContainer} /> },
              { key: 'iso', label: '3D 樓層', children: <FloorIso getContainer={getContainer} /> },
              { key: 'alerts', label: '告警', children: <AlertsTab getContainer={getContainer} /> },
              ...(staffAllowed ? [{ key: 'staff', label: '人員動態', children: <StaffPathTab /> }] : []),
              { key: 'history', label: '房間／設備履歷', children: <HistoryTab getContainer={getContainer} /> },
            ]}
          />
        </div>
      </div>
    </ConfigProvider>
  )
}
