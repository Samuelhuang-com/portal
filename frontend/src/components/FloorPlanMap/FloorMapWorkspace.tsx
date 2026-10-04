/**
 * 樓層巡檢圖 — 完整工作區（工具列＋地圖＋右側面板＋新增 Modal）
 * 規格：docs/DEV_SPEC_floor_plan_map.md §7（CLAUDE.md §12）
 *
 * 模組端只要：
 *   <FloorMapWorkspace module="full_building_inspection" />
 * 樓層、設備組、系統、屬性欄位、編輯權限 key、資料最後一天，全部由後端 Provider 的 /meta 提供。
 * 版面、顏色、點位樣式固定，不得在模組內另做。
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
import { useAuthStore } from '@/stores/authStore'
import FloorPlanMap, { type Ratio } from './FloorPlanMap'
import CheckRowResult from './CheckRowResult'
import {
  createFloorMapPoint, deleteFloorMapPoint, fetchFloorMapMeta, fetchFloorMapMonth,
  fetchFloorMapStatus, fetchFloorPlanImageUrl, fetchFloorPlans, updateFloorMapPoint,
  type FloorMapDayCell, type FloorMapModuleMeta, type FloorMapPoint, type FloorMapPointInput,
  type FloorMapStatusResponse, type FloorPlan,
} from './api'
import {
  FLOOR_MAP_STATUS, FLOOR_MAP_STATUS_KEYS, PLACEMENT_LABEL,
  type FloorMapPlacement, type FloorMapStatus,
} from './status'

const { Text } = Typography
const WEEKDAY = ['日', '一', '二', '三', '四', '五', '六']

export interface FloorMapWorkspaceProps {
  module:        string    // Provider.module
  defaultFloor?: string    // 不給就用 Provider.default_floor
}

export default function FloorMapWorkspace({ module, defaultFloor }: FloorMapWorkspaceProps) {
  const [meta,   setMeta]   = useState<FloorMapModuleMeta | null>(null)
  const [plans,  setPlans]  = useState<FloorPlan[]>([])
  const [floorKey, setFloorKey] = useState<string>('')
  const [date,     setDate]     = useState<Dayjs | null>(null)
  const [system,   setSystem]   = useState<string>('全部')

  const canEdit = useAuthStore((s) => (meta ? s.hasPermission(meta.edit_permission) : false))

  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const imageCache = useRef<Record<string, string>>({})

  const [loading, setLoading] = useState(false)
  const [data,    setData]    = useState<FloorMapStatusResponse | null>(null)
  const [error,   setError]   = useState<string | null>(null)
  const [selId,   setSelId]   = useState<number | null>(null)

  const [monthDays,    setMonthDays]    = useState<FloorMapDayCell[]>([])
  const [monthLoading, setMonthLoading] = useState(false)

  const [editing, setEditing] = useState(false)
  const [placing, setPlacing] = useState(false)
  const [newAt,   setNewAt]   = useState<Ratio | null>(null)
  const [saving,  setSaving]  = useState(false)
  const [addForm]  = Form.useForm()
  const [editForm] = Form.useForm()

  // ── 模組設定＋樓層登錄表；日期預設＝資料最後一天（§7.3）──────────────────────
  useEffect(() => {
    Promise.all([fetchFloorMapMeta(module), fetchFloorPlans()])
      .then(([m, p]) => {
        setMeta(m)
        setPlans(p)
        setFloorKey(defaultFloor && m.floors.includes(defaultFloor) ? defaultFloor : m.default_floor)
        setDate(m.data_end ? dayjs(m.data_end.replace(/\//g, '-')) : dayjs())
      })
      .catch(() => setError('取得樓層巡檢圖設定失敗'))
  }, [module, defaultFloor])

  const floor = plans.find((f) => f.key === floorKey)
  const floorOptions = (meta?.floors ?? [])
    .map((k) => plans.find((p) => p.key === k))
    .filter((p): p is FloorPlan => !!p)
    .map((p) => ({ value: p.key, label: p.label }))

  // ── 底圖（需登入，blob → object URL，各樓層快取一次）─────────────────────────
  useEffect(() => {
    if (!floorKey) return
    let alive = true
    const cached = imageCache.current[floorKey]
    if (cached) { setImageUrl(cached); return }
    setImageUrl(null)
    fetchFloorPlanImageUrl(floorKey)
      .then((u) => { imageCache.current[floorKey] = u; if (alive) setImageUrl(u) })
      .catch(() => alive && setError('取得底圖失敗'))
    return () => { alive = false }
  }, [floorKey])

  useEffect(() => () => { Object.values(imageCache.current).forEach((u) => URL.revokeObjectURL(u)) }, [])

  // ── 點位＋當日狀態 ────────────────────────────────────────────────────────
  const load = useCallback(async () => {
    if (!floorKey || !date) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchFloorMapStatus(module, floorKey, date.format('YYYY-MM-DD')))
    } catch {
      setData(null)
      setError('取得點位狀態失敗，請稍後再試')
    } finally {
      setLoading(false)
    }
  }, [module, floorKey, date])

  useEffect(() => { load() }, [load])

  const points = useMemo(
    () => (data?.points ?? []).filter((p) => system === '全部' || p.system === system),
    [data, system],
  )
  const sel      = data?.points.find((p) => p.id === selId) ?? null
  const selGroup = sel ? data?.groups[sel.source_ref] : undefined

  // ── 本月每日狀況 ──────────────────────────────────────────────────────────
  const monthKey = sel && date ? `${sel.source_ref}|${date.format('YYYY-MM')}` : ''
  useEffect(() => {
    if (!sel || !date) { setMonthDays([]); return }
    setMonthLoading(true)
    fetchFloorMapMonth(module, sel.source_ref, date.year(), date.month() + 1)
      .then(setMonthDays)
      .catch(() => setMonthDays([]))
      .finally(() => setMonthLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [module, monthKey])

  useEffect(() => {
    if (sel && editing) {
      editForm.setFieldsValue({
        source_ref: sel.source_ref, label: sel.label, equipment_code: sel.equipment_code,
        placement: sel.placement, attrs: sel.attrs, note: sel.note,
      })
    }
  }, [sel?.id, editing]) // eslint-disable-line react-hooks/exhaustive-deps

  const changeFloor = (k: string) => { setFloorKey(k); setSelId(null); setPlacing(false) }

  // ── 編輯 ──────────────────────────────────────────────────────────────────
  const formToInput = (v: Record<string, any>): Omit<FloorMapPointInput, 'x' | 'y'> => ({
    source_ref:     v.source_ref,
    label:          v.label,
    equipment_code: v.equipment_code || null,
    placement:      v.placement || 'confirmed',
    attrs:          Object.fromEntries((meta?.attr_fields ?? []).map((k) => [k, v.attrs?.[k] || null])),
    note:           v.note || null,
  })

  const handleMove = async (p: FloorMapPoint, to: Ratio) => {
    try {
      // 拖過的點視為已校正
      await updateFloorMapPoint(module, p.id, { ...to, placement: 'confirmed' })
      message.success(`已移動「${p.label}」`)
    } catch {
      message.error('移動失敗')
    }
    load()
  }

  const handleAdd = async () => {
    const v = await addForm.validateFields()
    if (!newAt || !floorKey) return
    setSaving(true)
    try {
      const p = await createFloorMapPoint(module, floorKey, { ...newAt, ...formToInput(v) })
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
      await updateFloorMapPoint(module, sel.id, formToInput(v))
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
      await deleteFloorMapPoint(module, sel.id)
      message.success(`已停用「${sel.label}」`)
      setSelId(null)
      load()
    } catch {
      message.error('停用失敗')
    }
  }

  const counts = useMemo(() => {
    const c: Record<FloorMapStatus, number> = { normal: 0, abnormal: 0, unchecked: 0, no_record: 0 }
    points.forEach((p) => { c[p.status ?? 'no_record'] += 1 })
    return c
  }, [points])

  const pointFields = (
    <>
      <Form.Item name="source_ref" label="對應 Ragic 設備組" rules={[{ required: true, message: '請選擇設備組' }]}>
        <Select
          placeholder="這個點要看哪一組 Ragic 巡檢欄位"
          options={(meta?.groups ?? []).map((g) => ({
            value: g.source_ref,
            label: `${g.label}${g.shared_label ? `（${g.shared_label}）` : ''}`,
          }))}
        />
      </Form.Item>
      <Form.Item name="label" label="顯示名稱" rules={[{ required: true, message: '請輸入名稱' }]}>
        <Input maxLength={100} />
      </Form.Item>
      <Form.Item name="equipment_code" label="設備編號"><Input maxLength={50} /></Form.Item>
      <Form.Item name="placement" label="位置狀態" initialValue="confirmed">
        <Select options={(Object.keys(PLACEMENT_LABEL) as FloorMapPlacement[]).map((k) => ({ value: k, label: PLACEMENT_LABEL[k] }))} />
      </Form.Item>
      {(meta?.attr_fields ?? []).map((f) => (
        <Form.Item key={f} name={['attrs', f]} label={f}><Input maxLength={200} /></Form.Item>
      ))}
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
                const st = FLOOR_MAP_STATUS[p.status ?? 'no_record']
                return (
                  <div key={p.id} onClick={() => setSelId(p.id)}
                       style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between',
                                padding: '4px 6px', borderBottom: '1px solid #f0f0f0' }}>
                    <span>
                      <span style={{ color: st.color, marginRight: 6 }}>●</span>{p.label}
                      {p.placement !== 'confirmed' && <Tag style={{ marginLeft: 6 }}>{p.placement === 'pending' ? '待定位' : '草稿'}</Tag>}
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

    const st = FLOOR_MAP_STATUS[sel.status ?? 'no_record']
    const note = selGroup?.rows.find((r) => r.abnormal_note)?.abnormal_note
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
            <Tooltip title="Ragic 這組欄位涵蓋多台設備或多層樓；同組點位顯示同一筆結果">
              <Tag color="orange">{sel.shared_label}</Tag>
            </Tooltip>
          )}
          {Object.entries(sel.attrs).map(([k, v]) => <Tag key={k}>{k}：{v}</Tag>)}
        </Space>

        {sel.placement !== 'confirmed' && (
          <Alert type={sel.placement === 'pending' ? 'warning' : 'info'} showIcon style={{ marginBottom: 8, fontSize: 12 }}
                 message={sel.note || PLACEMENT_LABEL[sel.placement]} />
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
                拖曳圖上的點即可移動（移動後視為已校正）。最後修改：{sel.updated_by} {sel.updated_at}
              </Text>
            </div>
          </Form>
        ) : (
          <>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {date?.format('YYYY/MM/DD')}
              {selGroup?.inspectors.length ? `　${selGroup.inspectors.join('、')}` : ''}
              {selGroup?.actual_minutes ? `　實際 ${selGroup.actual_minutes} 分` : ''}
            </Text>
            <div style={{ marginTop: 6 }}>
              {selGroup && selGroup.batches.length > 0 ? (
                selGroup.rows.map((r, i) => (
                  <div key={i} style={{ padding: '5px 0', borderBottom: '1px solid #f0f0f0' }}>
                    <div style={{ fontSize: 12, marginBottom: 2 }}>{r.check_content}</div>
                    <CheckRowResult row={r} />
                  </div>
                ))
              ) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="當日無巡檢紀錄" />
              )}
              {note && <Alert type="error" style={{ marginTop: 8, whiteSpace: 'pre-wrap' }} message={`異常說明：${note}`} />}
            </div>
          </>
        )}

        <div style={{ marginTop: 14 }}>
          <Text strong style={{ color: '#1B3A5C' }}>{date?.format('YYYY年M月')}每日狀況</Text>
          <Text type="secondary" style={{ fontSize: 11, marginLeft: 6 }}>點格子切換日期</Text>
          <Spin spinning={monthLoading}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 3, marginTop: 6 }}>
              {monthDays.map((d) => {
                const s  = FLOOR_MAP_STATUS[d.status]
                const on = !!date && d.day === date.date()
                return (
                  <Tooltip key={d.day} title={`${d.date}　${s.label}${d.abnormal_rows ? `（${d.abnormal_rows} 項）` : ''}`}>
                    <div onClick={() => date && setDate(date.date(d.day))}
                         style={{
                           cursor: 'pointer', height: 22, borderRadius: 3, fontSize: 11,
                           display: 'flex', alignItems: 'center', justifyContent: 'center',
                           background: s.color, color: '#fff',
                           outline: on ? '2px solid #1B3A5C' : 'none', outlineOffset: 1,
                         }}>
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
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap size={[12, 8]}>
          <Space>
            <Text strong>樓層</Text>
            <Segmented value={floorKey} onChange={(v) => changeFloor(String(v))} options={floorOptions} />
          </Space>
          <Space>
            <Text strong>日期</Text>
            <Button size="small" icon={<LeftOutlined />} disabled={!date} onClick={() => date && setDate(date.subtract(1, 'day'))} />
            <DatePicker
              size="small"
              allowClear={false}
              value={date}
              format={(d) => `${d.format('YYYY/MM/DD')}（${WEEKDAY[d.day()]}）`}
              onChange={(d) => d && setDate(d)}
            />
            <Button size="small" icon={<RightOutlined />} disabled={!date} onClick={() => date && setDate(date.add(1, 'day'))} />
            <Button size="small" icon={<ReloadOutlined />} onClick={load} loading={loading} />
            {meta?.data_end && (
              <Tooltip title="日期預設為資料最後一天（資料會落後於今天）">
                <Text type="secondary" style={{ fontSize: 11 }}>資料至 {meta.data_end}</Text>
              </Tooltip>
            )}
          </Space>
          {(meta?.systems.length ?? 0) > 0 && (
            <Space>
              <Text strong>系統</Text>
              <Segmented size="small" value={system} onChange={(v) => setSystem(String(v))}
                         options={['全部', ...(meta?.systems ?? [])]} />
            </Space>
          )}
          <Space size={10}>
            {FLOOR_MAP_STATUS_KEYS.map((k) => (
              <span key={k} style={{ fontSize: 12 }}>
                <span style={{ color: FLOOR_MAP_STATUS[k].color }}>●</span> {FLOOR_MAP_STATUS[k].label} {counts[k]}
              </span>
            ))}
          </Space>
          {canEdit && (
            <Space>
              <Button size="small" type={editing ? 'primary' : 'default'} icon={<EditOutlined />}
                      onClick={() => { setEditing(!editing); setPlacing(false) }}
                      style={editing ? { background: '#1B3A5C', borderColor: '#1B3A5C' } : undefined}>
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

      {error && <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} style={{ marginBottom: 12 }} />}
      {editing && (
        <Alert type="info" showIcon style={{ marginBottom: 12 }}
               message="編輯模式：拖曳點位可移動；點選點位可在右側修改或停用；按「新增點位」後點圖上位置新增。" />
      )}

      <Row gutter={12}>
        <Col xs={24} lg={16}>
          {floor ? (
            <FloorPlanMap
              floor={floor}
              imageUrl={imageUrl}
              points={points}
              selectedId={selId}
              editing={editing}
              placing={placing}
              onSelect={(p) => setSelId(p.id)}
              onMove={handleMove}
              onPlace={(at) => setNewAt(at)}
            />
          ) : (
            <Card style={{ height: 640 }}><Spin /></Card>
          )}
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
