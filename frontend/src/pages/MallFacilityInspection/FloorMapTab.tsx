/**
 * 商場工務巡檢 —「樓層巡檢圖」TAB
 *
 * 中文名稱：樓層巡檢圖　英文名稱：Floor Plan Inspection Map
 * 路由：/mall-facility-inspection/dashboard?tab=floor-map
 * 後端：/api/v1/mall-floor-map（backend/app/routers/mall_floor_map.py）
 * 規格：docs/SPEC_floor_plan_inspection.md
 *
 * 底圖用 Leaflet CRS.Simple（平面圖當地圖用）：
 *   座標範圍 [[0,0],[H,W]]，Leaflet 是 [lat, lng]＝[y 由下往上, x]；
 *   點位存比例 (x, y)，y 由上往下 → lat = (1 - y) * H、lng = x * W。
 *
 * 判定（正常／異常／未填）與「每日巡檢表」Drawer 同一套（後端 build_daily_sheet）。
 * 一個 Ragic Sheet 涵蓋多層（1F~3F、B1~B4）時，點位結果是共用的，畫面會標示。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert, Button, Card, Col, DatePicker, Empty, Form, Input, Modal, Popconfirm,
  Row, Segmented, Select, Space, Spin, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  AimOutlined, EditOutlined, LeftOutlined, LinkOutlined, PlusOutlined,
  ReloadOutlined, RightOutlined, SaveOutlined, StopOutlined,
} from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { ImageOverlay, MapContainer, Marker, useMap, useMapEvents } from 'react-leaflet'
import { useAuthStore } from '@/stores/authStore'
import {
  createFloorMapPoint, deleteFloorMapPoint, fetchFloorMapFloors, fetchFloorMapGroupMonth,
  fetchFloorMapImageUrl, fetchFloorMapStatus, updateFloorMapPoint,
  type FloorMapFloor, type FloorMapGroupMeta, type FloorMapMonthDay, type FloorMapPoint,
  type FloorMapStatus, type FloorMapStatusResponse,
} from '@/api/mallFloorMap'
import { ResultCell } from './MallFIDailySheetDrawer'

const { Text } = Typography

const EDIT_KEY = 'mall_floor_map_edit'
const WEEKDAY  = ['日', '一', '二', '三', '四', '五', '六']

const STATUS: Record<FloorMapStatus, { color: string; label: string; mark: string }> = {
  normal:    { color: '#52C41A', label: '正常',   mark: '✓' },
  abnormal:  { color: '#FF4D4F', label: '異常',   mark: '!' },
  unchecked: { color: '#FAAD14', label: '未填',   mark: '?' },
  no_record: { color: '#bfbfbf', label: '無紀錄', mark: '—' },
}

const esc = (s: string) =>
  s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!))

function markerIcon(p: FloorMapPoint, selected: boolean, editing: boolean): L.DivIcon {
  const st      = STATUS[p.status ?? 'no_record']
  const pending = p.note.startsWith('待定位')
  return L.divIcon({
    className:  'mfm-marker',
    iconSize:   [28, 28],
    iconAnchor: [14, 14],
    html: `
      <div class="mfm-dot${selected ? ' mfm-dot--sel' : ''}${pending ? ' mfm-dot--pending' : ''}${editing ? ' mfm-dot--edit' : ''}"
           style="background:${st.color}">${st.mark}</div>
      <div class="mfm-label">${esc(p.label)}</div>`,
  })
}

// ── Leaflet 子元件 ────────────────────────────────────────────────────────────

function FitBounds({ bounds }: { bounds: L.LatLngBoundsExpression }) {
  const map = useMap()
  useEffect(() => { map.fitBounds(bounds) }, [map, bounds])
  return null
}

function ClickToPlace({ active, onPlace }: { active: boolean; onPlace: (ll: L.LatLng) => void }) {
  useMapEvents({ click: (e) => { if (active) onPlace(e.latlng) } })
  return null
}

// ── 主元件 ────────────────────────────────────────────────────────────────────

export default function FloorMapTab() {
  const canEdit = useAuthStore((s) => s.hasPermission(EDIT_KEY))

  const [floors,  setFloors]  = useState<FloorMapFloor[]>([])
  const [groups,  setGroups]  = useState<FloorMapGroupMeta[]>([])
  const [systems, setSystems] = useState<string[]>([])
  const [floorKey, setFloorKey] = useState('3f')
  const [date,     setDate]     = useState<Dayjs>(dayjs())
  const [system,   setSystem]   = useState<string>('全部')

  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const imageCache = useRef<Record<string, string>>({})

  const [loading, setLoading] = useState(false)
  const [data,    setData]    = useState<FloorMapStatusResponse | null>(null)
  const [error,   setError]   = useState<string | null>(null)
  const [selId,   setSelId]   = useState<number | null>(null)

  const [monthDays,    setMonthDays]    = useState<FloorMapMonthDay[]>([])
  const [monthLoading, setMonthLoading] = useState(false)

  const [editing,  setEditing]  = useState(false)
  const [placing,  setPlacing]  = useState(false)
  const [newAt,    setNewAt]    = useState<{ x: number; y: number } | null>(null)
  const [saving,   setSaving]   = useState(false)
  const [addForm]  = Form.useForm()
  const [editForm] = Form.useForm()

  const floor  = floors.find((f) => f.key === floorKey)
  const bounds = useMemo<L.LatLngBoundsExpression>(
    () => [[0, 0], [floor?.height ?? 1000, floor?.width ?? 1000]],
    [floor?.height, floor?.width],
  )

  const toLatLng = (p: { x: number; y: number }): L.LatLngExpression =>
    [(1 - p.y) * (floor?.height ?? 1), p.x * (floor?.width ?? 1)]
  const toRatio = (ll: L.LatLng) => ({
    x: Math.min(1, Math.max(0, ll.lng / (floor?.width ?? 1))),
    y: Math.min(1, Math.max(0, 1 - ll.lat / (floor?.height ?? 1))),
  })

  // ── 樓層／設備組清單 ──────────────────────────────────────────────────────
  useEffect(() => {
    fetchFloorMapFloors()
      .then((r) => { setFloors(r.floors); setGroups(r.groups); setSystems(r.systems) })
      .catch(() => setError('取得樓層清單失敗'))
  }, [])

  // ── 底圖（需登入，blob → object URL，各樓層快取一次）────────────────────────
  useEffect(() => {
    let alive = true
    const cached = imageCache.current[floorKey]
    if (cached) { setImageUrl(cached); return }
    setImageUrl(null)
    fetchFloorMapImageUrl(floorKey)
      .then((u) => { imageCache.current[floorKey] = u; if (alive) setImageUrl(u) })
      .catch(() => alive && setError('取得底圖失敗'))
    return () => { alive = false }
  }, [floorKey])

  useEffect(() => () => { Object.values(imageCache.current).forEach((u) => URL.revokeObjectURL(u)) }, [])

  // ── 點位＋當日狀態 ────────────────────────────────────────────────────────
  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchFloorMapStatus(floorKey, date.format('YYYY-MM-DD')))
    } catch {
      setData(null)
      setError('取得點位狀態失敗，請稍後再試')
    } finally {
      setLoading(false)
    }
  }, [floorKey, date])

  useEffect(() => { load() }, [load])

  const points = useMemo(
    () => (data?.points ?? []).filter((p) => system === '全部' || p.system === system),
    [data, system],
  )
  const sel      = data?.points.find((p) => p.id === selId) ?? null
  const selGroup = sel ? data?.groups[sel.group_key] : undefined

  // ── 本月每日狀況（依選中點位的設備組）──────────────────────────────────────
  const monthKey = sel ? `${sel.group_key}|${date.format('YYYY-MM')}` : ''
  useEffect(() => {
    if (!sel) { setMonthDays([]); return }
    setMonthLoading(true)
    fetchFloorMapGroupMonth(sel.sheet_key, sel.item, date.year(), date.month() + 1)
      .then((r) => setMonthDays(r.days))
      .catch(() => setMonthDays([]))
      .finally(() => setMonthLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [monthKey])

  // 編輯模式選中點位 → 帶入表單
  useEffect(() => {
    if (sel && editing) {
      editForm.setFieldsValue({
        label: sel.label, equipment_code: sel.equipment_code, group: sel.group_key,
        location_desc: sel.location_desc, supply_area: sel.supply_area, note: sel.note,
      })
    }
  }, [sel?.id, editing]) // eslint-disable-line react-hooks/exhaustive-deps

  const changeFloor = (k: string) => { setFloorKey(k); setSelId(null); setPlacing(false) }

  // ── 編輯動作 ──────────────────────────────────────────────────────────────
  const splitGroup = (gk: string) => {
    const g = groups.find((x) => x.key === gk)!
    return { sheet_key: g.sheet_key, item: g.item }
  }

  const handleDragEnd = async (p: FloorMapPoint, ll: L.LatLng) => {
    try {
      await updateFloorMapPoint(p.id, toRatio(ll))
      message.success(`已移動「${p.label}」`)
      load()
    } catch {
      message.error('移動失敗')
      load()
    }
  }

  const handleAdd = async () => {
    const v = await addForm.validateFields()
    if (!newAt) return
    setSaving(true)
    try {
      const p = await createFloorMapPoint(floorKey, {
        ...newAt, ...splitGroup(v.group),
        label: v.label, equipment_code: v.equipment_code || null,
        location_desc: v.location_desc || null, supply_area: v.supply_area || null, note: v.note || null,
      })
      message.success('已新增點位')
      setNewAt(null); setPlacing(false); addForm.resetFields()
      await load()
      setSelId(p.id)
    } catch {
      message.error('新增失敗')
    } finally {
      setSaving(false)
    }
  }

  const handleSave = async () => {
    if (!sel) return
    const v = await editForm.validateFields()
    setSaving(true)
    try {
      await updateFloorMapPoint(sel.id, {
        ...splitGroup(v.group),
        label: v.label, equipment_code: v.equipment_code || null,
        location_desc: v.location_desc || null, supply_area: v.supply_area || null, note: v.note || null,
      })
      message.success('已儲存')
      load()
    } catch {
      message.error('儲存失敗')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!sel) return
    try {
      await deleteFloorMapPoint(sel.id)
      message.success(`已停用「${sel.label}」`)
      setSelId(null)
      load()
    } catch {
      message.error('停用失敗')
    }
  }

  // ── 統計 ──────────────────────────────────────────────────────────────────
  const counts = useMemo(() => {
    const c: Record<FloorMapStatus, number> = { normal: 0, abnormal: 0, unchecked: 0, no_record: 0 }
    points.forEach((p) => { c[p.status ?? 'no_record'] += 1 })
    return c
  }, [points])

  const groupOptions = groups.map((g) => ({
    value: g.key,
    label: `${g.sheet_label}｜${g.item}${g.shared_label ? `（${g.shared_label}）` : ''}`,
  }))

  const pointFields = (
    <>
      <Form.Item name="group" label="對應 Ragic 設備組" rules={[{ required: true, message: '請選擇設備組' }]}>
        <Select options={groupOptions} placeholder="選擇這個點要看哪一組 Ragic 巡檢欄位" />
      </Form.Item>
      <Form.Item name="label" label="顯示名稱" rules={[{ required: true, message: '請輸入名稱' }]}>
        <Input maxLength={100} placeholder="例：AH-R33 空調箱" />
      </Form.Item>
      <Form.Item name="equipment_code" label="設備編號"><Input maxLength={50} placeholder="例：AH-R33" /></Form.Item>
      <Form.Item name="location_desc" label="機房位置"><Input maxLength={100} /></Form.Item>
      <Form.Item name="supply_area" label="供應區域"><Input maxLength={200} /></Form.Item>
      <Form.Item name="note" label="備註"><Input.TextArea maxLength={300} rows={2} /></Form.Item>
    </>
  )

  // ── 右側面板 ──────────────────────────────────────────────────────────────
  const renderSide = () => {
    if (!sel) {
      return (
        <Card size="small" title={`${floor?.label ?? ''} 點位（${points.length}）`}>
          {points.length === 0 ? (
            <Empty description={editing ? '按「新增點位」後點圖上位置' : '這層還沒有點位'} />
          ) : (
            <Space direction="vertical" style={{ width: '100%' }} size={4}>
              {points.map((p) => {
                const st = STATUS[p.status ?? 'no_record']
                return (
                  <div
                    key={p.id}
                    onClick={() => setSelId(p.id)}
                    style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between',
                             padding: '4px 6px', borderBottom: '1px solid #f0f0f0' }}
                  >
                    <span>
                      <span style={{ color: st.color, marginRight: 6 }}>●</span>{p.label}
                      {p.note.startsWith('待定位') && <Tag style={{ marginLeft: 6 }}>待定位</Tag>}
                    </span>
                    <Text style={{ color: st.color }}>{st.label}</Text>
                  </div>
                )
              })}
            </Space>
          )}
        </Card>
      )
    }

    const st = STATUS[sel.status ?? 'no_record']
    return (
      <Card
        size="small"
        title={
          <Space wrap size={4}>
            <Tag color={st.color}>{st.label}</Tag>
            <span>{sel.label}</span>
            {selGroup?.batches.map((b) => (
              <a key={b.ragic_id} href={b.ragic_url} target="_blank" rel="noreferrer"
                 style={{ color: '#4BA8E8', fontSize: 12, fontWeight: 400 }}>
                <LinkOutlined /> 在 Ragic 查看{selGroup.batches.length > 1 ? `（${b.start_hhmm}）` : ''}
              </a>
            ))}
          </Space>
        }
        extra={<Button size="small" type="text" onClick={() => setSelId(null)}>返回清單</Button>}
      >
        <Space wrap size={[4, 4]} style={{ marginBottom: 8 }}>
          {sel.system && <Tag color="blue">{sel.system}</Tag>}
          {sel.shared_label && (
            <Tooltip title="Ragic 這張表只有一組欄位，涵蓋多層、多台設備；同組點位顯示同一筆結果">
              <Tag color="orange">{sel.shared_label}</Tag>
            </Tooltip>
          )}
          {sel.location_desc && <Tag>機房：{sel.location_desc}</Tag>}
          {sel.supply_area && <Tag>供應：{sel.supply_area}</Tag>}
        </Space>

        {sel.note && (
          <Alert type={sel.note.startsWith('待定位') ? 'warning' : 'info'} showIcon
                 message={sel.note} style={{ marginBottom: 8, fontSize: 12 }} />
        )}

        {editing && canEdit ? (
          <Form form={editForm} layout="vertical" size="small">
            {pointFields}
            <Space>
              <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}
                      style={{ background: '#1B3A5C', borderColor: '#1B3A5C' }}>儲存</Button>
              <Popconfirm title={`停用「${sel.label}」？`} description="停用後圖上不再顯示（不會刪除紀錄）"
                          okText="停用" cancelText="取消" onConfirm={handleDelete}>
                <Button danger icon={<StopOutlined />}>停用點位</Button>
              </Popconfirm>
            </Space>
            <div style={{ marginTop: 6 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>
                直接拖曳圖上的點即可移動位置。最後修改：{sel.updated_by} {sel.updated_at}
              </Text>
            </div>
          </Form>
        ) : (
          <>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {date.format('YYYY/MM/DD')}
              {selGroup?.inspectors.length ? `　${selGroup.inspectors.join('、')}` : ''}
              {selGroup?.actual_minutes ? `　實際 ${selGroup.actual_minutes} 分` : ''}
            </Text>
            <div style={{ marginTop: 6 }}>
              {selGroup && selGroup.batches.length > 0 ? (
                selGroup.rows.map((r, i) => (
                  <div key={i} style={{ padding: '5px 0', borderBottom: '1px solid #f0f0f0' }}>
                    <div style={{ fontSize: 12, marginBottom: 2 }}>{r.check_content}</div>
                    <ResultCell row={{ ...r, _key: String(i) }} />
                  </div>
                ))
              ) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="當日無巡檢紀錄" />
              )}
              {selGroup?.rows.find((r) => r.abnormal_note) && (
                <Alert type="error" style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}
                       message={`異常說明：${selGroup.rows.find((r) => r.abnormal_note)!.abnormal_note}`} />
              )}
            </div>
          </>
        )}

        <div style={{ marginTop: 14 }}>
          <Text strong style={{ color: '#1B3A5C' }}>
            {date.format('YYYY年M月')}每日狀況
          </Text>
          <Text type="secondary" style={{ fontSize: 11, marginLeft: 6 }}>點格子切換日期</Text>
          <Spin spinning={monthLoading}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 3, marginTop: 6 }}>
              {monthDays.map((d) => {
                const s  = STATUS[d.status]
                const on = d.day === date.date()
                return (
                  <Tooltip key={d.day} title={`${d.date}　${s.label}${d.abnormal_rows ? `（${d.abnormal_rows} 項）` : ''}`}>
                    <div
                      onClick={() => setDate(date.date(d.day))}
                      style={{
                        cursor: 'pointer', height: 22, borderRadius: 3, fontSize: 11,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: s.color, color: '#fff',
                        outline: on ? '2px solid #1B3A5C' : 'none', outlineOffset: 1,
                      }}
                    >
                      {d.day}
                    </div>
                  </Tooltip>
                )
              })}
            </div>
          </Spin>
        </div>
      </Card>
    )
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div>
      <style>{`
        .mfm-map { height: 640px; background: #fff; border-radius: 6px; }
        .mfm-map .leaflet-container { background: #fff; }
        .mfm-marker { background: transparent; border: none; }
        .mfm-dot {
          width: 28px; height: 28px; border-radius: 50%; border: 3px solid #fff;
          box-shadow: 0 1px 4px rgba(0,0,0,.45); color: #fff; font-weight: 700; font-size: 13px;
          display: flex; align-items: center; justify-content: center; box-sizing: border-box;
        }
        .mfm-dot--sel     { outline: 3px solid #4BA8E8; outline-offset: 2px; }
        .mfm-dot--pending { border-style: dashed; border-color: #1B3A5C; }
        .mfm-dot--edit    { cursor: move; }
        .mfm-label {
          position: absolute; top: 30px; left: 50%; transform: translateX(-50%);
          white-space: nowrap; font-size: 12px; background: rgba(255,255,255,.92);
          border: 1px solid #d9d9d9; border-radius: 3px; padding: 0 4px; color: #222;
        }
        .mfm-placing .leaflet-container { cursor: crosshair; }
      `}</style>

      {/* ── 操作列 ── */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap size={[12, 8]}>
          <Space>
            <Text strong>樓層</Text>
            <Segmented
              value={floorKey}
              onChange={(v) => changeFloor(String(v))}
              options={floors.map((f) => ({ value: f.key, label: f.label }))}
            />
          </Space>
          <Space>
            <Text strong>日期</Text>
            <Button size="small" icon={<LeftOutlined />} onClick={() => setDate(date.subtract(1, 'day'))} />
            <DatePicker
              size="small"
              allowClear={false}
              value={date}
              format={(d) => `${d.format('YYYY/MM/DD')}（${WEEKDAY[d.day()]}）`}
              onChange={(d) => d && setDate(d)}
            />
            <Button size="small" icon={<RightOutlined />} onClick={() => setDate(date.add(1, 'day'))} />
            <Button size="small" icon={<ReloadOutlined />} onClick={load} loading={loading} />
          </Space>
          <Space>
            <Text strong>系統</Text>
            <Segmented
              size="small"
              value={system}
              onChange={(v) => setSystem(String(v))}
              options={['全部', ...systems]}
            />
          </Space>
          <Space size={10}>
            {(Object.keys(STATUS) as FloorMapStatus[]).map((k) => (
              <span key={k} style={{ fontSize: 12 }}>
                <span style={{ color: STATUS[k].color }}>●</span> {STATUS[k].label} {counts[k]}
              </span>
            ))}
          </Space>
          {canEdit && (
            <Space>
              <Button
                size="small"
                type={editing ? 'primary' : 'default'}
                icon={<EditOutlined />}
                onClick={() => { setEditing(!editing); setPlacing(false) }}
                style={editing ? { background: '#1B3A5C', borderColor: '#1B3A5C' } : undefined}
              >
                {editing ? '結束編輯' : '編輯點位'}
              </Button>
              {editing && (
                <Button size="small" icon={placing ? <AimOutlined /> : <PlusOutlined />}
                        onClick={() => setPlacing(!placing)} danger={placing}>
                  {placing ? '點圖上位置…（再按取消）' : '新增點位'}
                </Button>
              )}
            </Space>
          )}
        </Space>
      </Card>

      {error && <Alert type="error" message={error} showIcon closable onClose={() => setError(null)}
                       style={{ marginBottom: 12 }} />}
      {editing && (
        <Alert type="info" showIcon style={{ marginBottom: 12 }}
               message="編輯模式：拖曳點位可移動；點選點位可在右側修改或停用；按「新增點位」後點圖上位置新增。" />
      )}

      <Row gutter={12}>
        <Col xs={24} lg={16}>
          <div className={`mfm-map${placing ? ' mfm-placing' : ''}`}>
            {floor && imageUrl ? (
              <MapContainer
                key={floorKey}
                crs={L.CRS.Simple}
                bounds={bounds}
                minZoom={-3}
                maxZoom={2}
                zoomSnap={0.25}
                zoomDelta={0.5}
                attributionControl={false}
                style={{ height: '100%', width: '100%', borderRadius: 6 }}
              >
                <FitBounds bounds={bounds} />
                <ImageOverlay url={imageUrl} bounds={bounds} />
                <ClickToPlace active={editing && placing} onPlace={(ll) => setNewAt(toRatio(ll))} />
                {points.map((p) => (
                  <Marker
                    key={`${p.id}-${p.x}-${p.y}-${editing}`}
                    position={toLatLng(p)}
                    icon={markerIcon(p, p.id === selId, editing)}
                    draggable={editing}
                    eventHandlers={{
                      click:   () => setSelId(p.id),
                      dragend: (e) => handleDragEnd(p, (e.target as L.Marker).getLatLng()),
                    }}
                  />
                ))}
              </MapContainer>
            ) : (
              <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Spin tip="載入底圖…"><div style={{ width: 120, height: 60 }} /></Spin>
              </div>
            )}
          </div>
        </Col>
        <Col xs={24} lg={8}>
          <Spin spinning={loading}>{renderSide()}</Spin>
        </Col>
      </Row>

      <Modal
        open={!!newAt}
        title={`新增點位（${floor?.label ?? ''}）`}
        okText="新增"
        cancelText="取消"
        confirmLoading={saving}
        onOk={handleAdd}
        onCancel={() => { setNewAt(null); addForm.resetFields() }}
        destroyOnClose
      >
        <Form form={addForm} layout="vertical" size="small">{pointFields}</Form>
      </Modal>
    </div>
  )
}
