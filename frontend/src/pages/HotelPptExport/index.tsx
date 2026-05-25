/**
 * 飯店 Dashboard PPT 匯出設定頁  v2.0
 * 路由：/ppt-export
 * Permission：hotel_overview_ppt_config
 *
 * 功能：
 * A-1  Dashboard 群組同步（KPI 組 / 圖表組合為一張投影片）
 * B-1  second_title 行內編輯
 * B-3  最近匯出歷史紀錄面板
 * C-2  模板選擇器
 * 拖曳  @dnd-kit/sortable 調整匯出順序
 */
import React, { useEffect, useState, useCallback } from 'react'
import {
  Card, Checkbox, Switch, Button, Space, Typography, Tag, Spin,
  message, Tooltip, Row, Col, Alert, Select, Collapse, Table,
  Input,
} from 'antd'
import {
  SaveOutlined, InfoCircleOutlined, DatabaseOutlined, DesktopOutlined,
  ReloadOutlined, HolderOutlined, EditOutlined, CheckOutlined,
  CloseOutlined, HistoryOutlined, AppstoreOutlined,
} from '@ant-design/icons'
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext, useSortable, verticalListSortingStrategy, arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  fetchPptConfig, savePptConfig, fetchPptHistory, fetchPptTemplates,
  type PptConfigItem, type PptExportHistoryItem, type PptTemplate,
} from '@/api/hotelPptExport'

const { Title, Text } = Typography
const { Panel } = Collapse

// ─── Dashboard 群組定義（A-1）─────────────────────────────────────────────────
const DASHBOARD_KPI_GROUP   = new Set([
  'dashboard_kpi_summary', 'dashboard_source_status', 'dashboard_repair_costs',
])
const DASHBOARD_CHART_GROUP = new Set([
  'dashboard_bar_chart', 'dashboard_rate_chart', 'dashboard_dazhi_trend', 'dashboard_hours_pie',
])

function getGroupSet(key: string): Set<string> | null {
  if (DASHBOARD_KPI_GROUP.has(key))   return DASHBOARD_KPI_GROUP
  if (DASHBOARD_CHART_GROUP.has(key)) return DASHBOARD_CHART_GROUP
  return null
}

// ─── Tab 分組顏色 ─────────────────────────────────────────────────────────────
const TAB_COLOR_MAP: Record<string, string> = {
  'Dashboard': 'blue', '報修管理': 'orange', '人員分析': 'purple',
  'B. 每日累計': 'cyan', 'C. 每月累計': 'green', 'D. 每年累計': 'gold',
  '人員工時%': 'magenta', '人員排名': 'volcano',
}
function tabColor(tab: string): string {
  return TAB_COLOR_MAP[tab] ?? 'default'
}

// ─────────────────────────────────────────────────────────────────────────────
// SortableRow
// ─────────────────────────────────────────────────────────────────────────────

interface SortableRowProps {
  item:       PptConfigItem
  groupNote:  string | null           // "合 1 張" note
  onToggle:   (key: string, field: 'enabled' | 'include_detail', value: boolean) => void
  onOverride: (key: string, value: string | null) => void
}

function SortableRow({ item, groupNote, onToggle, onOverride }: SortableRowProps) {
  const [editing, setEditing]   = useState(false)
  const [draft,   setDraft]     = useState('')

  const {
    attributes, listeners, setNodeRef,
    transform, transition, isDragging,
  } = useSortable({ id: item.export_key })

  const rowStyle: React.CSSProperties = {
    transform:    CSS.Transform.toString(transform),
    transition,
    opacity:      isDragging ? 0.55 : 1,
    background:   isDragging ? '#f0f7ff' : '#fff',
    borderBottom: '1px solid #f0f0f0',
    padding:      '9px 16px',
    userSelect:   'none',
    position:     isDragging ? 'relative' : undefined,
    zIndex:       isDragging ? 9999    : undefined,
  }

  const startEdit = () => {
    setDraft(item.second_title_override || '')
    setEditing(true)
  }
  const commitEdit = () => {
    onOverride(item.export_key, draft.trim() || null)
    setEditing(false)
  }
  const cancelEdit = () => setEditing(false)

  const dsBadge = (ds: string) =>
    ds === 'backend_db' ? (
      <Tooltip title="後端查詢 DB">
        <Tag icon={<DatabaseOutlined />} color="blue" style={{ fontSize: 11 }}>DB</Tag>
      </Tooltip>
    ) : (
      <Tooltip title="由前端 Dashboard 傳入">
        <Tag icon={<DesktopOutlined />} color="default" style={{ fontSize: 11 }}>前端</Tag>
      </Tooltip>
    )

  return (
    <div ref={setNodeRef} style={rowStyle}>
      <Row align="middle" gutter={[8, 0]} wrap={false}>

        {/* 拖曳把手 */}
        <Col flex="none">
          <span
            {...attributes} {...listeners}
            style={{
              cursor:  isDragging ? 'grabbing' : 'grab',
              color:   '#ccc', fontSize: 16, display: 'flex',
              alignItems: 'center', padding: '0 4px',
            }}
          >
            <HolderOutlined />
          </span>
        </Col>

        {/* 分組 Tag */}
        <Col flex="none" style={{ minWidth: 88 }}>
          <Tag color={tabColor(item.tab_name)} style={{ fontSize: 11, margin: 0, whiteSpace: 'nowrap' }}>
            {item.tab_name}
          </Tag>
        </Col>

        {/* 區塊名稱（B-1 行內編輯）*/}
        <Col flex="auto" style={{ minWidth: 0 }}>
          {editing ? (
            <Space size={4}>
              <Input
                size="small"
                value={draft}
                onChange={e => setDraft(e.target.value)}
                onPressEnter={commitEdit}
                placeholder={item.second_title_default}
                style={{ width: 180, fontSize: 12 }}
                autoFocus
              />
              <Tooltip title="確認">
                <Button type="text" size="small" icon={<CheckOutlined />}
                        style={{ color: '#52c41a' }} onClick={commitEdit} />
              </Tooltip>
              <Tooltip title="取消">
                <Button type="text" size="small" icon={<CloseOutlined />}
                        style={{ color: '#ff4d4f' }} onClick={cancelEdit} />
              </Tooltip>
            </Space>
          ) : (
            <Space size={6} align="center">
              <Text
                style={{
                  fontWeight: item.enabled ? 600 : 400,
                  color:      item.enabled ? '#1B3A5C' : '#bbb',
                  cursor:     'default',
                }}
              >
                {item.second_title}
                {item.second_title_override && (
                  <Tag color="purple" style={{ fontSize: 10, marginLeft: 4 }}>已自訂</Tag>
                )}
              </Text>
              {dsBadge(item.data_source)}
              {groupNote && (
                <Tag color="geekblue" style={{ fontSize: 10 }}>{groupNote}</Tag>
              )}
              {item.description && (
                <Tooltip title={item.description}>
                  <InfoCircleOutlined style={{ color: '#ccc', fontSize: 13 }} />
                </Tooltip>
              )}
              {/* B-1 編輯按鈕 */}
              <Tooltip title={`自訂投影片標題（預設：${item.second_title_default}）`}>
                <Button
                  type="text" size="small" icon={<EditOutlined />}
                  style={{ color: '#aaa', padding: '0 2px' }}
                  onClick={startEdit}
                />
              </Tooltip>
            </Space>
          )}
        </Col>

        {/* include_detail Switch */}
        <Col flex="none" style={{ minWidth: 88, textAlign: 'right' }}>
          {item.supports_detail ? (
            <Tooltip title={item.detail_description || '勾選後會附加一張明細投影片'}>
              <Space size={4}>
                <Text style={{ fontSize: 12, color: '#888' }}>含明細</Text>
                <Switch
                  size="small"
                  checked={item.include_detail}
                  disabled={!item.enabled}
                  onChange={v => onToggle(item.export_key, 'include_detail', v)}
                />
              </Space>
            </Tooltip>
          ) : (
            <span style={{ display: 'inline-block', width: 88 }} />
          )}
        </Col>

        {/* 啟用 Checkbox */}
        <Col flex="none" style={{ textAlign: 'center', minWidth: 40 }}>
          <Checkbox
            checked={item.enabled}
            onChange={e => onToggle(item.export_key, 'enabled', e.target.checked)}
          />
        </Col>

      </Row>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// HistoryPanel（B-3）
// ─────────────────────────────────────────────────────────────────────────────

function HistoryPanel() {
  const [history, setHistory] = useState<PptExportHistoryItem[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setHistory(await fetchPptHistory(30))
    } catch {
      message.error('載入歷史紀錄失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  // 在 Collapse 展開時才載入
  const handleChange = (keys: string | string[]) => {
    if ((Array.isArray(keys) ? keys : [keys]).includes('history')) load()
  }

  const columns = [
    {
      title: '時間', dataIndex: 'exported_at', width: 160,
      render: (v: string) => new Date(v).toLocaleString('zh-TW'),
    },
    { title: '操作者', dataIndex: 'exported_by', width: 120 },
    {
      title: '年月', width: 80,
      render: (_: unknown, r: PptExportHistoryItem) => `${r.year}年${String(r.month).padStart(2,'0')}月`,
    },
    {
      title: '模板', dataIndex: 'template_id', width: 100,
      render: (v: string | null) => v || 'default',
    },
    {
      title: '匯出區塊', dataIndex: 'section_count', width: 80,
      render: (v: number, r: PptExportHistoryItem) => (
        <Tooltip title={r.sections.join('、')}>
          <Tag color="blue">{v} 個</Tag>
        </Tooltip>
      ),
    },
  ]

  return (
    <Collapse
      ghost
      onChange={handleChange}
      style={{ marginTop: 16, background: '#fafafa', borderRadius: 8, border: '1px solid #f0f0f0' }}
    >
      <Panel
        header={
          <Space>
            <HistoryOutlined style={{ color: '#888' }} />
            <Text style={{ color: '#666', fontWeight: 600 }}>最近匯出紀錄</Text>
          </Space>
        }
        key="history"
      >
        <Spin spinning={loading}>
          <Table
            size="small"
            dataSource={history}
            columns={columns}
            rowKey="id"
            pagination={false}
            locale={{ emptyText: '尚無匯出紀錄' }}
          />
        </Spin>
      </Panel>
    </Collapse>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 主元件
// ─────────────────────────────────────────────────────────────────────────────

const HotelPptExportPage: React.FC = () => {
  const [loading,    setLoading]    = useState(true)
  const [saving,     setSaving]     = useState(false)
  const [templateId, setTemplateId] = useState('default')
  const [templates,  setTemplates]  = useState<PptTemplate[]>([])
  const [updatedBy,  setUpdatedBy]  = useState<string | null>(null)
  const [updatedAt,  setUpdatedAt]  = useState<string | null>(null)
  const [config,     setConfig]     = useState<PptConfigItem[]>([])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  )

  // ── 載入 ──────────────────────────────────────────────────────────────────
  const loadConfig = useCallback(async () => {
    try {
      setLoading(true)
      const [data, tpls] = await Promise.all([fetchPptConfig(), fetchPptTemplates()])
      setConfig(Array.isArray(data?.config) ? data.config : [])
      setTemplateId(data.template_id)
      setUpdatedBy(data.updated_by)
      setUpdatedAt(data.updated_at)
      setTemplates(tpls.filter(t => t.available))
    } catch {
      message.error('載入設定失敗，請重試')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadConfig() }, [loadConfig])

  // ── 啟用切換（A-1：Dashboard 群組同步）───────────────────────────────────
  const handleToggle = (
    exportKey: string,
    field: 'enabled' | 'include_detail',
    value: boolean,
  ) => {
    setConfig(prev => {
      const group = field === 'enabled' ? getGroupSet(exportKey) : null
      return prev.map(item => {
        if (item.export_key === exportKey) return { ...item, [field]: value }
        if (group && group.has(item.export_key)) return { ...item, enabled: value }
        return item
      })
    })
  }

  // ── B-1：second_title 覆寫 ────────────────────────────────────────────────
  const handleOverride = (exportKey: string, value: string | null) => {
    setConfig(prev =>
      prev.map(item => {
        if (item.export_key !== exportKey) return item
        return {
          ...item,
          second_title:          value || item.second_title_default,
          second_title_override: value,
        }
      }),
    )
  }

  // ── 拖曳排序 ──────────────────────────────────────────────────────────────
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    setConfig(prev => {
      const oldIdx = prev.findIndex(i => i.export_key === active.id)
      const newIdx = prev.findIndex(i => i.export_key === over.id)
      return arrayMove(prev, oldIdx, newIdx)
    })
  }

  // ── 儲存 ──────────────────────────────────────────────────────────────────
  const handleSave = async () => {
    try {
      setSaving(true)
      await savePptConfig({
        template_id: templateId,
        config: config.map((item, index) => ({
          export_key:            item.export_key,
          enabled:               item.enabled,
          include_detail:        item.include_detail,
          sort_order:            index + 1,
          second_title_override: item.second_title_override || null,
        })),
      })
      message.success('設定已儲存')
      await loadConfig()
    } catch {
      message.error('儲存失敗，請重試')
    } finally {
      setSaving(false)
    }
  }

  const handleSelectAll = (enabled: boolean) =>
    setConfig(prev => prev.map(item => ({ ...item, enabled })))

  // ── 計算群組 note（A-1）──────────────────────────────────────────────────
  const groupNoteMap = new Map<string, string>()
  // 找出 KPI 組與圖表組各自的排序代表（最小 sort_order 者）
  const kpiMembers   = config.filter(c => DASHBOARD_KPI_GROUP.has(c.export_key))
  const chartMembers = config.filter(c => DASHBOARD_CHART_GROUP.has(c.export_key))
  if (kpiMembers.length > 0) {
    kpiMembers.forEach(c => groupNoteMap.set(c.export_key, `合 1 張（KPI 組，共 ${kpiMembers.length} 項）`))
  }
  if (chartMembers.length > 0) {
    chartMembers.forEach(c => groupNoteMap.set(c.export_key, `合 1 張（圖表組，共 ${chartMembers.length} 項）`))
  }

  const enabledCount = config.filter(c => c.enabled).length

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div style={{ padding: '24px', maxWidth: 960, margin: '0 auto' }}>

      {/* ── 頁首 ── */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
            飯店 Dashboard — PPT 匯出設定
          </Title>
          {updatedBy && updatedAt && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              上次儲存：{updatedBy}　{new Date(updatedAt).toLocaleString('zh-TW')}
            </Text>
          )}
        </Col>
        <Col>
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={loadConfig} size="small" loading={loading}>
              重新載入
            </Button>
            <Button onClick={() => handleSelectAll(true)} size="small">全選</Button>
            <Button onClick={() => handleSelectAll(false)} size="small">全不選</Button>
            <Button
              type="primary" icon={<SaveOutlined />} onClick={handleSave}
              loading={saving} style={{ background: '#1B3A5C', borderColor: '#1B3A5C' }}
            >
              儲存設定
            </Button>
          </Space>
        </Col>
      </Row>

      {/* ── C-2：模板選擇 ── */}
      {templates.length > 0 && (
        <Row align="middle" gutter={12} style={{ marginBottom: 12 }}>
          <Col flex="none">
            <Space>
              <AppstoreOutlined style={{ color: '#888' }} />
              <Text style={{ fontSize: 13, color: '#555' }}>投影片模板：</Text>
            </Space>
          </Col>
          <Col flex="none">
            <Select
              value={templateId}
              onChange={setTemplateId}
              size="small"
              style={{ minWidth: 200 }}
              options={templates.map(t => ({ value: t.id, label: t.label }))}
            />
          </Col>
          <Col flex="none">
            {templates.find(t => t.id === templateId) && (
              <Text type="secondary" style={{ fontSize: 11 }}>
                {templates.find(t => t.id === templateId)!.description}
              </Text>
            )}
          </Col>
        </Row>
      )}

      <Alert
        type="info" showIcon
        message={
          `目前已勾選 ${enabledCount} / ${config.length} 個區塊。` +
          '拖曳 ⣿ 調整順序；點擊 ✏️ 自訂投影片標題；Dashboard 群組標示「合 1 張」的 section 共用一張投影片。'
        }
        style={{ marginBottom: 16, fontSize: 12 }}
      />

      {/* ── 排序清單 ── */}
      <Spin spinning={loading}>
        <Card style={{ borderRadius: 8, overflow: 'hidden' }} styles={{ body: { padding: 0 } }}>
          {/* 表頭 */}
          <div style={{
            display: 'flex', padding: '8px 16px',
            background: '#fafafa', borderBottom: '1px solid #f0f0f0',
            fontSize: 12, color: '#aaa', fontWeight: 600, gap: 8,
          }}>
            <span style={{ width: 28 }}></span>
            <span style={{ minWidth: 88 }}>分組</span>
            <span style={{ flex: 1 }}>區塊名稱</span>
            <span style={{ minWidth: 88, textAlign: 'right' }}>含明細</span>
            <span style={{ minWidth: 40, textAlign: 'center' }}>啟用</span>
          </div>

          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={config.map(c => c.export_key)} strategy={verticalListSortingStrategy}>
              {config.map(item => (
                <SortableRow
                  key={item.export_key}
                  item={item}
                  groupNote={groupNoteMap.get(item.export_key) ?? null}
                  onToggle={handleToggle}
                  onOverride={handleOverride}
                />
              ))}
            </SortableContext>
          </DndContext>

          {config.length === 0 && !loading && (
            <div style={{ padding: 32, textAlign: 'center', color: '#bbb' }}>
              尚無可匯出的區塊
            </div>
          )}
        </Card>
      </Spin>

      {/* ── B-3：歷史紀錄面板 ── */}
      <HistoryPanel />

      {/* ── 底部儲存 ── */}
      {!loading && config.length > 0 && (
        <Row justify="end" style={{ marginTop: 16 }}>
          <Button
            type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}
            style={{ background: '#1B3A5C', borderColor: '#1B3A5C' }}
          >
            儲存設定
          </Button>
        </Row>
      )}

    </div>
  )
}

export default HotelPptExportPage
