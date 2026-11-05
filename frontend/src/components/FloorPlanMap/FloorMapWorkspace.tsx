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
  InputNumber, Row, Segmented, Select, Space, Spin, Tag, Tooltip, Typography, Upload, message,
} from 'antd'
import {
  AimOutlined, EditOutlined, LeftOutlined, LinkOutlined, PlusOutlined,
  ReloadOutlined, RightOutlined, SaveOutlined, StopOutlined, UploadOutlined,
} from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'
import { useAuthStore } from '@/stores/authStore'
import FloorPlanMap, { type Ratio } from './FloorPlanMap'
import CheckRowResult from './CheckRowResult'
import {
  createFloorMapPoint, deleteFloorMapPoint, fetchFloorMapMeta, fetchFloorMapMonth,
  fetchFloorMapStatus, fetchFloorPlanImageUrl, fetchFloorPlans, setFloorMapSourceDisabled, updateFloorMapPoint,
  uploadFloorPlanImage,
  type FloorMapChildDay, type FloorMapDayCell, type FloorMapModuleMeta, type FloorMapPoint, type FloorMapPointInput,
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
  // 置換底圖：全站共用權限（權限設定 → 樓層巡檢圖：置換底圖）
  const canReplaceImage = useAuthStore((s) => s.hasPermission('floor_map_image_manage'))
  const [replaceOpen, setReplaceOpen] = useState(false)
  const [replaceFile, setReplaceFile] = useState<File | null>(null)
  const [replacing,   setReplacing]   = useState(false)
  const [replacePage, setReplacePage] = useState<number>(1)
  // 錯誤留在對話框內（message 約 3 秒即消失，容易漏看）
  const [replaceError, setReplaceError] = useState<string | null>(null)
  const [replaceDpi,  setReplaceDpi]  = useState<number>(150)

  const [imageUrl, setImageUrl] = useState<string | null>(null)
  // 底圖尚未提供（後端 404）：不是錯誤，畫面顯示「無底圖，待補」
  const [noImage, setNoImage] = useState(false)
  const imageCache = useRef<Record<string, string>>({})

  const [loading, setLoading] = useState(false)
  const [data,    setData]    = useState<FloorMapStatusResponse | null>(null)
  const [error,   setError]   = useState<string | null>(null)
  const [selId,   setSelId]   = useState<number | null>(null)
  const [selChildRef, setSelChildRef] = useState<string | null>(null)   // two_level：選中的子項

  const [monthDays,    setMonthDays]    = useState<FloorMapDayCell[]>([])
  const [monthLoading, setMonthLoading] = useState(false)

  const [editing, setEditing] = useState(false)
  const [placing, setPlacing] = useState(false)
  const [newAt,   setNewAt]   = useState<Ratio | null>(null)
  // 從「未對應」清單放點時預填的資料來源（2026-11-04）
  const [prefill, setPrefill] = useState<{ source_ref: string; label: string } | null>(null)
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
    if (cached) { setImageUrl(cached); setNoImage(false); return }
    setImageUrl(null)
    setNoImage(false)
    fetchFloorPlanImageUrl(floorKey)
      .then((u) => { imageCache.current[floorKey] = u; if (alive) setImageUrl(u) })
      .catch((e) => {
        if (!alive) return
        if (e?.response?.status === 404) setNoImage(true)
        else setError('取得底圖失敗')
      })
    return () => { alive = false }
  }, [floorKey])

  useEffect(() => () => { Object.values(imageCache.current).forEach((u) => URL.revokeObjectURL(u)) }, [])

  // ── 置換底圖：上傳成功後清除快取、重新載入底圖與尺寸 ───────────────────────
  const handleReplaceImage = async () => {
    if (!replaceFile || !floorKey) return
    setReplacing(true)
    setReplaceError(null)
    try {
      const isPdf = /\.pdf$/i.test(replaceFile.name)
      await uploadFloorPlanImage(floorKey, replaceFile, isPdf ? { page: replacePage, dpi: replaceDpi } : {})
      const old = imageCache.current[floorKey]
      if (old) { URL.revokeObjectURL(old); delete imageCache.current[floorKey] }
      const url = await fetchFloorPlanImageUrl(floorKey)
      imageCache.current[floorKey] = url
      setImageUrl(url)
      setNoImage(false)
      setPlans(await fetchFloorPlans())
      message.success('底圖已置換')
      setReplaceOpen(false)
      setReplaceFile(null)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      const text = typeof detail === 'string' ? detail : (e?.message ?? '置換底圖失敗')
      setReplaceError(`${e?.response?.status ? `HTTP ${e.response.status}：` : ''}${text}`)
      message.error('置換底圖失敗，請見對話框內說明')
    } finally {
      setReplacing(false)
    }
  }

  // ── 點位＋當日狀態 ────────────────────────────────────────────────────────
  const load = useCallback(async () => {
    if (!floorKey || !date) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchFloorMapStatus(module, floorKey, date.format('YYYY-MM-DD')))
    } catch (e: any) {
      setData(null)
      const status = e?.response?.status
      const detail = e?.response?.data?.detail
      const text = typeof detail === 'string' ? detail : (e?.message ?? '')
      setError(`取得點位狀態失敗${status ? `（HTTP ${status}）` : ''}：${text || '請稍後再試'}`)
    } finally {
      setLoading(false)
    }
  }, [module, floorKey, date])

  useEffect(() => { load() }, [load])

  const twoLevel = !!meta?.two_level
  const points = useMemo(
    // hidden：two_level 母項在該層子項全部停用 → 只在編輯模式顯示
    () => (data?.points ?? []).filter((p) => (editing || !p.hidden) && (system === '全部' || p.system === system)),
    [data, system, editing],
  )
  const sel      = data?.points.find((p) => p.id === selId) ?? null
  const selGroup = sel ? data?.groups[sel.source_ref] : undefined
  const selChild = twoLevel && selChildRef ? selGroup?.children?.find((c) => c.source_ref === selChildRef) : undefined
  useEffect(() => { setSelChildRef(null) }, [selId])

  // ── 本月每日狀況（two_level：選中子項才查）─────────────────────────────────
  const monthRef = twoLevel ? selChildRef : (sel?.source_ref ?? null)
  const monthKey = monthRef && date ? `${monthRef}|${date.format('YYYY-MM')}` : ''
  useEffect(() => {
    if (!monthRef || !date) { setMonthDays([]); return }
    setMonthLoading(true)
    fetchFloorMapMonth(module, monthRef, date.year(), date.month() + 1)
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

  useEffect(() => {
    if (newAt && prefill) addForm.setFieldsValue({ source_ref: prefill.source_ref, label: prefill.label })
  }, [newAt]) // eslint-disable-line react-hooks/exhaustive-deps

  const changeFloor = (k: string) => { setFloorKey(k); setSelId(null); setPlacing(false); setPrefill(null) }

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
      setNewAt(null); setPlacing(false); setPrefill(null); addForm.resetFields()
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

  // 資料來源欄位名稱：Provider 未提供時維持原文字（巡檢模組不受影響）
  const srcLabel = meta?.source_label ?? '對應 Ragic 設備組'
  const isDefaultSrc = srcLabel === '對應 Ragic 設備組'
  const pointFields = (
    <>
      <Form.Item name="source_ref" label={srcLabel}
                 rules={[{ required: true, message: isDefaultSrc ? '請選擇設備組' : `請選擇${srcLabel.replace(/^對應/, '')}` }]}>
        <Select
          placeholder={isDefaultSrc ? '這個點要看哪一組 Ragic 巡檢欄位' : `請選擇${srcLabel.replace(/^對應/, '')}`}
          showSearch
          optionFilterProp="label"
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
  const unmapped = data?.unmapped ?? []
  const renderUnmapped = () => (
    <Card size="small" style={{ marginTop: 12 }}
          title={<span style={{ color: '#d46b08' }}>未對應項目（{unmapped.length}）</span>}
          extra={<Tooltip title="所選月份的資料中，還沒有任何點位的項目（已停用的點位視為刻意不放，不列入）"><Text type="secondary" style={{ fontSize: 11 }}>{date?.format('YYYY年M月')}</Text></Tooltip>}>
      {!(canEdit && editing) && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {canEdit ? '按「編輯點位」後，可把項目直接放到圖上。' : '需要「編輯點位」權限才能放到圖上。'}
        </Text>
      )}
      <Space direction="vertical" style={{ width: '100%', marginTop: 4 }} size={4}>
        {unmapped.map((g) => (
          <div key={g.source_ref}
               style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        gap: 6, padding: '4px 6px', borderBottom: '1px solid #f0f0f0' }}>
            <span style={{ fontSize: 12 }}>
              {g.system && <Tag style={{ marginRight: 4 }}>{g.system}</Tag>}{g.label}
            </span>
            {canEdit && editing && (
              <Button size="small" icon={<AimOutlined />}
                      type={placing && prefill?.source_ref === g.source_ref ? 'primary' : 'default'}
                      onClick={() => { setPrefill({ source_ref: g.source_ref, label: g.label }); setPlacing(true); setSelId(null) }}>
                放到圖上
              </Button>
            )}
          </div>
        ))}
      </Space>
    </Card>
  )

  // ── 本月每日狀況格（一般點位／two_level 的子項共用）────────────────────────────
  const renderMonthGrid = () => (
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
  )

  // ── two_level（例行維護類，2026-11-05）：母項 → 子項清單 → 子項明細＋每日狀況 ──────────
  const handleToggleChild = async (k: FloorMapChildDay) => {
    try {
      await setFloorMapSourceDisabled(module, k.source_ref, !k.disabled)
      message.success(k.disabled ? `已恢復「${k.label}」` : `已停用「${k.label}」`)
      load()
    } catch {
      message.error('變更失敗')
    }
  }

  const renderChild = (k: FloorMapChildDay) => {
    const kst  = FLOOR_MAP_STATUS[k.status]
    const note = k.rows.find((r) => r.abnormal_note)?.abnormal_note
    const links = k.batches.length > 0
      ? k.batches.map((b) => ({ key: b.ragic_id, url: b.ragic_url, hint: k.batches.length > 1 ? `（${b.start_hhmm}）` : '' }))
      : (k.ragic_url ? [{ key: k.source_ref, url: k.ragic_url, hint: '' }] : [])
    return (
      <Card
        size="small"
        title={
          <Space wrap size={4}>
            <Tag color={kst.color}>{kst.label}</Tag>
            <span>{k.label}</span>
            {links.map((l) => (
              <a key={l.key} href={l.url} target="_blank" rel="noreferrer"
                 style={{ color: '#4BA8E8', fontSize: 12, fontWeight: 400 }}>
                <LinkOutlined /> 在 Ragic 查看{l.hint}
              </a>
            ))}
          </Space>
        }
        extra={<Button size="small" type="text" onClick={() => setSelChildRef(null)}>返回母項</Button>}
      >
        <Space wrap size={[4, 4]} style={{ marginBottom: 8 }}>
          <Tag>{sel?.label}</Tag>
          {k.system && <Tag color="blue">{k.system}</Tag>}
          {k.frequency && <Tag>{k.frequency}</Tag>}
          {k.schedule_label && <Tag>排定 {k.schedule_label}</Tag>}
          {k.disabled && <Tag color="default">已停用（不計入母項狀態）</Tag>}
          {!k.in_batch && <Tag color="default">本月批次無此項</Tag>}
        </Space>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {date?.format('YYYY/MM/DD')}
          {k.inspectors.length ? `　${k.inspectors.join('、')}` : ''}
          {k.actual_minutes ? `　實際 ${k.actual_minutes} 分` : ''}
        </Text>
        <div style={{ marginTop: 6 }}>
          {k.rows.length > 0 ? (
            k.rows.map((r, i) => (
              <div key={i} style={{ padding: '5px 0', borderBottom: '1px solid #f0f0f0' }}>
                <div style={{ fontSize: 12, marginBottom: 2 }}>{r.check_content}</div>
                <CheckRowResult row={r} />
              </div>
            ))
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={meta?.empty_day_text ?? '當日無巡檢紀錄'} />
          )}
          {note && <Alert type="error" style={{ marginTop: 8, whiteSpace: 'pre-wrap' }} message={`異常說明：${note}`} />}
        </div>
        {renderMonthGrid()}
      </Card>
    )
  }

  const renderParent = () => {
    if (!sel) return null
    const st   = FLOOR_MAP_STATUS[sel.status ?? 'no_record']
    const kids = selGroup?.children ?? []
    return (
      <Card
        size="small"
        title={
          <Space wrap size={4}>
            <Tag color={st.color}>{st.label}</Tag>
            <span>{sel.label}</span>
            {sel.hidden && <Tag>子項全停用</Tag>}
          </Space>
        }
        extra={<Button size="small" type="text" onClick={() => setSelId(null)}>返回清單</Button>}
      >
        <Space wrap size={[4, 4]} style={{ marginBottom: 8 }}>
          {sel.system && <Tag color="blue">{sel.system}</Tag>}
          {Object.entries(sel.attrs).map(([k, v]) => <Tag key={k}>{k}：{v}</Tag>)}
        </Space>

        {sel.placement !== 'confirmed' && (
          <Alert type={sel.placement === 'pending' ? 'warning' : 'info'} showIcon style={{ marginBottom: 8, fontSize: 12 }}
                 message={sel.note || PLACEMENT_LABEL[sel.placement]} />
        )}

        {editing && canEdit && (
          <Form form={editForm} layout="vertical" size="small">
            {pointFields}
            <Space>
              <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}
                      style={{ background: '#1B3A5C', borderColor: '#1B3A5C' }}>儲存</Button>
              <Popconfirm title={`停用「${sel.label}」這個點位？`} description="停用後圖上不再顯示（不會刪除紀錄）"
                          okText="停用" cancelText="取消" onConfirm={handleDelete}>
                <Button danger icon={<StopOutlined />}>停用點位</Button>
              </Popconfirm>
            </Space>
            <div style={{ marginTop: 6, marginBottom: 8 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>
                拖曳圖上的點即可移動（移動後視為已校正）。最後修改：{sel.updated_by} {sel.updated_at}
              </Text>
            </div>
          </Form>
        )}

        <div>
          <Text strong style={{ color: '#1B3A5C' }}>{floor?.label} 子項（{kids.length}）</Text>
          <Text type="secondary" style={{ fontSize: 11, marginLeft: 6 }}>
            {date?.format('YYYY/MM/DD')}　點子項看明細與每日狀況
          </Text>
        </div>
        {kids.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="這個母項沒有子項" />
        ) : (
          <Space direction="vertical" style={{ width: '100%', marginTop: 4 }} size={2}>
            {kids.map((k) => {
              const kst = FLOOR_MAP_STATUS[k.status]
              return (
                <div key={k.source_ref} onClick={() => setSelChildRef(k.source_ref)}
                     style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                              gap: 6, padding: '4px 6px', borderBottom: '1px solid #f0f0f0', opacity: k.disabled ? 0.55 : 1 }}>
                  <span style={{ fontSize: 12 }}>
                    <span style={{ color: k.disabled ? '#bfbfbf' : kst.color, marginRight: 6 }}>●</span>
                    {k.label}
                    {k.disabled && <Tag style={{ marginLeft: 6 }}>已停用</Tag>}
                    {k.schedule_label && <Text type="secondary" style={{ fontSize: 11, marginLeft: 6 }}>排定 {k.schedule_label}</Text>}
                  </span>
                  <Space size={4}>
                    {!k.disabled && <Text style={{ color: kst.color, fontSize: 12 }}>{kst.label}</Text>}
                    {editing && canEdit && (
                      k.disabled ? (
                        <Button size="small" onClick={(ev) => { ev.stopPropagation(); handleToggleChild(k) }}>恢復</Button>
                      ) : (
                        <Popconfirm title={`停用子項「${k.label}」？`}
                                    description="所有樓層都停用；仍顯示在清單，但不計入母項狀態"
                                    okText="停用" cancelText="取消"
                                    onConfirm={(ev) => { ev?.stopPropagation(); handleToggleChild(k) }}
                                    onCancel={(ev) => ev?.stopPropagation()}>
                          <Button size="small" danger onClick={(ev) => ev.stopPropagation()}>停用</Button>
                        </Popconfirm>
                      )
                    )}
                  </Space>
                </div>
              )
            })}
          </Space>
        )}
      </Card>
    )
  }

  const renderSide = () => {
    if (!sel) {
      return (
        <>
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
                      {p.hidden && <Tag style={{ marginLeft: 6 }}>子項全停用</Tag>}
                    </span>
                    <Text style={{ color: st.color }}>{st.label}</Text>
                  </div>
                )
              })}
            </Space>
          )}
        </Card>
        {unmapped.length > 0 && renderUnmapped()}
        </>
      )
    }

    if (twoLevel) return selChild ? renderChild(selChild) : renderParent()

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
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={meta?.empty_day_text ?? '當日無巡檢紀錄'} />
              )}
              {note && <Alert type="error" style={{ marginTop: 8, whiteSpace: 'pre-wrap' }} message={`異常說明：${note}`} />}
            </div>
          </>
        )}

        {renderMonthGrid()}
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
          <Space>
            {canReplaceImage && (
              <Button size="small" icon={<UploadOutlined />} onClick={() => setReplaceOpen(true)}>
                置換圖檔
              </Button>
            )}
            {canEdit && (
            <>
              <Button size="small" type={editing ? 'primary' : 'default'} icon={<EditOutlined />}
                      onClick={() => { setEditing(!editing); setPlacing(false); setPrefill(null) }}
                      style={editing ? { background: '#1B3A5C', borderColor: '#1B3A5C' } : undefined}>
                {editing ? '結束編輯' : '編輯點位'}
              </Button>
              {editing && (
                <Button size="small" icon={placing ? <AimOutlined /> : <PlusOutlined />}
                        onClick={() => { setPrefill(null); setPlacing(!placing) }} danger={placing}>
                  {placing ? '點圖上位置…（再按取消）' : '新增點位'}
                </Button>
              )}
              {editing && placing && prefill && <Tag color="orange">放置：{prefill.label}</Tag>}
            </>
            )}
          </Space>
        </Space>
      </Card>

      {error && <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} style={{ marginBottom: 12 }} />}
      <Modal
        title={`置換底圖：${floor?.label ?? floorKey}`}
        open={replaceOpen}
        onCancel={() => { setReplaceOpen(false); setReplaceFile(null) }}
        onOk={handleReplaceImage}
        okText="確認置換"
        cancelText="取消"
        okButtonProps={{ disabled: !replaceFile, loading: replacing }}
        destroyOnClose
      >
        <Alert type="warning" showIcon style={{ marginBottom: 12 }}
               message="置換後所有使用者會立即看到新底圖；舊圖會保留為備份。支援 WebP、PNG、JPG、PDF（統一轉為 WebP）。" />
        <Upload
          accept=".webp,.png,.jpg,.jpeg,.pdf,image/webp,image/png,image/jpeg,application/pdf"
          maxCount={1}
          beforeUpload={(file) => {
            const ok = /\.(webp|png|jpe?g|pdf)$/i.test(file.name)
            if (!ok) { message.error('僅接受 WebP、PNG、JPG、PDF'); return Upload.LIST_IGNORE }
            if (file.size > 40 * 1024 * 1024) { message.error('檔案超過 40 MB'); return Upload.LIST_IGNORE }
            setReplaceFile(file)
            setReplaceError(null)
            return false
          }}
          onRemove={() => setReplaceFile(null)}
        >
          <Button icon={<UploadOutlined />}>選擇檔案</Button>
        </Upload>
        {replaceError && (
          <Alert type="error" showIcon style={{ marginTop: 12 }} message="置換失敗" description={replaceError} />
        )}
        {replaceFile && /\.pdf$/i.test(replaceFile.name) && (
          <Space style={{ marginTop: 12 }} wrap>
            <span>PDF 頁碼</span>
            <InputNumber min={1} precision={0} value={replacePage} onChange={(v) => setReplacePage(v ?? 1)} />
            <span>解析度（DPI）</span>
            <InputNumber min={72} max={300} precision={0} value={replaceDpi} onChange={(v) => setReplaceDpi(v ?? 150)} />
          </Space>
        )}
      </Modal>
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
              noImage={noImage}
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
        onCancel={() => { setNewAt(null); setPrefill(null); setPlacing(false); addForm.resetFields() }}
        destroyOnClose
      >
        <Form form={addForm} layout="vertical" size="small">{pointFields}</Form>
      </Modal>
    </div>
  )
}
