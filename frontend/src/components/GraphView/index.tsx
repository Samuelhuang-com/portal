/**
 * GraphView — 操作流程關聯圖譜
 * 套件：@xyflow/react v12（react-flow）
 *
 * 三群組 Layout（靜態位置，左→右流向）：
 *   Col 1 (x=0)   : 巡檢作業（B1F/B2F/RF/B4F/保全）
 *   Col 2 (x=310) : 保養作業（客房/飯店PM/商場PM）
 *   Col 3 (x=610) : 流程管理（簽核/公告）
 *
 * 邊類型：
 *   anomaly    → 紅色虛線（巡檢異常 → 保養需求，業務邏輯）
 *   escalation → 橙色虛線（異常/逾期 → 簽核，業務邏輯）
 *   workflow   → 紫色實線+動畫（Approval → Memo，DB 直接關聯）
 *
 * ⚠ FIXED：自訂節點需要 <Handle> 組件，否則邊無法渲染
 */
import { useEffect, useRef, useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  MarkerType,
  Panel,
  useNodesState,
  useEdgesState,
  type NodeTypes,
  type EdgeTypes,
  type Node,
  type Edge,
  type NodeProps,
  type EdgeProps,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Spin, Badge, Tooltip } from 'antd'
import {
  fetchDashboardGraph,
  type GraphNode,
  type GraphEdge,
  type GraphGroup,
} from '@/api/dashboardGraph'

// ── PROTECTED 色彩常數（禁止修改）─────────────────────────────────────────────
const C = {
  primary: '#1B3A5C',
  accent:  '#4BA8E8',
  normal:  '#52c41a',
  warning: '#faad14',
  danger:  '#cf1322',
}

// ── 群組樣式 ──────────────────────────────────────────────────────────────────
const GROUP_STYLE: Record<string, { bg: string; border: string; text: string }> = {
  inspection:  { bg: '#e6f4ff', border: '#4BA8E8', text: '#0958d9' },
  maintenance: { bg: '#f6ffed', border: '#52c41a', text: '#389e0d' },
  workflow:    { bg: '#f9f0ff', border: '#722ed1', text: '#531dab' },
}
const GROUP_LABEL: Record<string, string> = {
  inspection:  '巡檢作業',
  maintenance: '保養作業',
  workflow:    '流程管理',
}

function statusColor(status: string) {
  if (status === 'danger')  return C.danger
  if (status === 'warning') return C.warning
  return C.normal
}

// ── 靜態節點位置（左→右三欄）────────────────────────────────────────────────
const NODE_W = 148
const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
  // 巡檢（Col 1）
  b1f_insp:   { x: 0,   y: 0   },
  b2f_insp:   { x: 0,   y: 100 },
  rf_insp:    { x: 0,   y: 200 },
  b4f_insp:   { x: 0,   y: 315 },
  security:      { x: 0,   y: 415 },
  mall_facility: { x: 0,   y: 515 },
  full_building: { x: 0,   y: 615 },
  // 保養（Col 2）
  hotel_room: { x: 310, y: 0   },
  hotel_pm:   { x: 310, y: 155 },
  mall_pm:    { x: 310, y: 300 },
  // 流程（Col 3）
  approval:   { x: 610, y: 155 },
  memo:       { x: 610, y: 300 },
}

// ── 邊視覺設定 ────────────────────────────────────────────────────────────────
const EDGE_CFG: Record<string, { stroke: string; dash: string }> = {
  anomaly:    { stroke: '#ff4d4f', dash: '6,4' },
  escalation: { stroke: '#fa8c16', dash: '6,4' },
  workflow:   { stroke: '#722ed1', dash: '0'   },
}

// ══════════════════════════════════════════════════════════════════════════════
// 自訂節點：PortalModuleNode
// ⚠ 必須包含 <Handle> 才能讓邊連上去
// ══════════════════════════════════════════════════════════════════════════════
type NodeData = GraphNode & { onClick: () => void; [key: string]: unknown }

function PortalModuleNode({ data }: NodeProps & { data: NodeData }) {
  const gs    = GROUP_STYLE[data.group] ?? GROUP_STYLE.inspection
  const color = statusColor(data.status)

  return (
    <>
      {/* 左側：作為 edge 的目標連接點 */}
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: color, width: 8, height: 8, border: 'none' }}
      />

      <Tooltip title={`${GROUP_LABEL[data.group]}・點擊進入`} placement="top">
        <div
          onClick={data.onClick}
          style={{
            background: gs.bg,
            border: `2px solid ${color}`,
            borderRadius: 10,
            padding: '7px 12px',
            width: NODE_W,
            cursor: 'pointer',
            boxShadow: data.status !== 'normal'
              ? `0 0 8px ${color}55` : '0 1px 4px rgba(0,0,0,0.07)',
            transition: 'all 0.2s',
            userSelect: 'none',
          }}
          onMouseEnter={e => {
            const el = e.currentTarget as HTMLDivElement
            el.style.transform = 'scale(1.05)'
            el.style.boxShadow = `0 4px 16px ${color}66`
          }}
          onMouseLeave={e => {
            const el = e.currentTarget as HTMLDivElement
            el.style.transform = 'scale(1)'
            el.style.boxShadow = data.status !== 'normal'
              ? `0 0 8px ${color}55` : '0 1px 4px rgba(0,0,0,0.07)'
          }}
        >
          {/* 群組小標籤 */}
          <div style={{ fontSize: 9, color: gs.text, fontWeight: 700, marginBottom: 3, opacity: 0.85 }}>
            {GROUP_LABEL[data.group]}
          </div>

          {/* 模組名 */}
          <div style={{ fontSize: 13, fontWeight: 700, color: C.primary, marginBottom: 4 }}>
            {data.label}
          </div>

          {/* Alert badge */}
          {data.alert > 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <Badge
                count={data.alert}
                style={{ backgroundColor: color, fontSize: 10, minWidth: 18, height: 18, lineHeight: '18px' }}
              />
              <span style={{ fontSize: 10, color }}>
                {data.status === 'normal' ? '則' : '待處理'}
              </span>
            </div>
          ) : (
            <div style={{ fontSize: 10, color: C.normal }}>✓ 正常</div>
          )}

          {/* 副標籤（逾期/異常分項） */}
          {data.sub && (
            <div style={{ fontSize: 10, color: '#8c8c8c', marginTop: 2 }}>
              {data.sub}
            </div>
          )}
        </div>
      </Tooltip>

      {/* 右側：作為 edge 的來源連接點 */}
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: color, width: 8, height: 8, border: 'none' }}
      />
    </>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// 自訂邊：PortalEdge（Bezier 曲線 + 中間標籤）
// ══════════════════════════════════════════════════════════════════════════════
type EdgeData = { label: string; type: string; weight: number }

function PortalEdge(props: EdgeProps) {
  const data    = props.data as EdgeData | undefined
  const type    = data?.type ?? 'anomaly'
  const cfg     = EDGE_CFG[type] ?? EDGE_CFG.anomaly
  const weight  = data?.weight ?? 1
  const strokeW = Math.min(4, Math.max(1.5, weight * 0.6))

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition,
  })

  return (
    <>
      <BaseEdge
        path={edgePath}
        markerEnd={props.markerEnd}
        style={{
          stroke: cfg.stroke,
          strokeWidth: strokeW,
          strokeDasharray: cfg.dash,
          opacity: 0.8,
        }}
      />
      {data?.label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%,-50%) translate(${labelX}px,${labelY}px)`,
              fontSize: 9,
              background: '#fff',
              border: `1px solid ${cfg.stroke}`,
              borderRadius: 4,
              padding: '1px 5px',
              color: cfg.stroke,
              fontWeight: 600,
              pointerEvents: 'none',
              whiteSpace: 'pre',
              lineHeight: 1.4,
              textAlign: 'center',
            }}
            className="nodrag nopan"
          >
            {data.label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}

// ── NodeTypes / EdgeTypes 宣告 ────────────────────────────────────────────────
const nodeTypes: NodeTypes = { portalModule: PortalModuleNode as any }
const edgeTypes: EdgeTypes = { portalEdge:   PortalEdge   as any }

// ══════════════════════════════════════════════════════════════════════════════
// API 資料 → ReactFlow 格式轉換
// ══════════════════════════════════════════════════════════════════════════════
function toRFNodes(
  apiNodes: GraphNode[],
  navigate: ReturnType<typeof useNavigate>,
): Node[] {
  return apiNodes.map(n => ({
    id: n.id,
    type: 'portalModule',
    position: NODE_POSITIONS[n.id] ?? { x: 300, y: 200 },
    // ⚠ 左→右流向：source 在右，target 在左
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: { ...n, onClick: () => navigate(n.path) } as NodeData,
  }))
}

function toRFEdges(apiEdges: GraphEdge[]): Edge[] {
  return apiEdges.map(e => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: 'portalEdge',
    data: { label: e.label, type: e.type, weight: e.weight } as EdgeData,
    animated: e.type === 'workflow',
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: EDGE_CFG[e.type]?.stroke ?? '#aaa',
      width: 14,
      height: 14,
    },
  }))
}

// ══════════════════════════════════════════════════════════════════════════════
// 主組件
// ══════════════════════════════════════════════════════════════════════════════
interface Props {
  refreshInterval?: number
}

export default function GraphView({ refreshInterval = 60_000 }: Props) {
  const navigate = useNavigate()
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [groups,      setGroups]      = useState<GraphGroup[]>([])
  const [totalAlerts, setTotalAlerts] = useState(0)
  const [loading,     setLoading]     = useState(true)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await fetchDashboardGraph()
      setGroups(data.groups)
      setNodes(toRFNodes(data.nodes, navigate))
      setEdges(toRFEdges(data.edges))
      setTotalAlerts(data.meta.total_alerts)
    } catch {
      // 靜默失敗，保留舊資料
    } finally {
      setLoading(false)
    }
  }, [navigate, setNodes, setEdges])

  useEffect(() => {
    load()
    timerRef.current = setInterval(load, refreshInterval)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [load, refreshInterval])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin tip="載入關聯圖譜中…" />
      </div>
    )
  }

  return (
    <div style={{ width: '100%', height: 720 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.35}
        maxZoom={2}
        style={{ background: '#f8faff', borderRadius: 8 }}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#dde3f0" gap={20} size={1} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={n => statusColor((n.data as unknown as GraphNode)?.status ?? 'normal')}
          style={{ background: '#f0f4f8' }}
        />

        {/* 左上角圖例 */}
        <Panel position="top-left">
          <div style={{
            background: 'rgba(255,255,255,0.93)',
            border: '1px solid #e5e7eb',
            borderRadius: 8,
            padding: '8px 12px',
            fontSize: 11,
            minWidth: 140,
          }}>
            {/* 總告警 */}
            <div style={{ fontWeight: 700, marginBottom: 7, fontSize: 12 }}>
              {totalAlerts > 0
                ? <span style={{ color: C.danger }}>⚠ 全域待處理 {totalAlerts} 項</span>
                : <span style={{ color: C.normal }}>✓ 全系統正常</span>}
            </div>

            {/* 群組圖例 */}
            {groups.map(g => {
              const gs = GROUP_STYLE[g.id]
              return (
                <div key={g.id} style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 3 }}>
                  <div style={{
                    width: 10, height: 10, borderRadius: 2,
                    background: gs?.bg, border: `1.5px solid ${gs?.border}`,
                  }} />
                  <span style={{ color: '#555' }}>{g.label}</span>
                </div>
              )
            })}

            {/* 邊類型圖例 */}
            <div style={{ marginTop: 7, borderTop: '1px solid #f0f0f0', paddingTop: 6 }}>
              {[
                { color: '#ff4d4f', dash: true,  label: '異常觸發保養' },
                { color: '#fa8c16', dash: true,  label: '異常升級簽核' },
                { color: '#722ed1', dash: false, label: 'DB直接關聯'   },
              ].map(({ color, dash, label }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                  <svg width={22} height={8}>
                    <line x1={0} y1={4} x2={22} y2={4}
                      stroke={color} strokeWidth={2}
                      strokeDasharray={dash ? '4,3' : '0'}
                    />
                    <polygon points="18,1 22,4 18,7" fill={color} />
                  </svg>
                  <span style={{ color: '#555' }}>{label}</span>
                </div>
              ))}
            </div>

            <div style={{ color: '#9ca3af', fontSize: 10, marginTop: 5 }}>
              點擊節點可進入模組
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  )
}
