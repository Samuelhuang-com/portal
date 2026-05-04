/**
 * 知識庫圖譜視圖
 * 使用 @xyflow/react（React Flow）繪製文章關聯圖
 * 邊的來源：標籤重疊（虛線）、[[連結]] 引用（實線）
 */
import { useEffect, useCallback, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  type Node,
  type NodeTypes,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Spin, Tag, Empty } from 'antd'
import { BookOutlined, CodeOutlined } from '@ant-design/icons'
import { fetchWikiGraph, type WikiGraphNode } from '@/api/wiki'

// ── 顏色常數（與 PROTECTED.md 一致）─────────────────────────────────────────
const COLOR_SOP = '#1B3A5C'
const COLOR_DEV = '#4BA8E8'
const COLOR_BG  = '#f0f4f8'

// ── 自訂節點元件 ──────────────────────────────────────────────────────────────
function WikiArticleNode({ data, selected }: { data: any; selected: boolean }) {
  const isSop = data.category === 'sop'
  const accent = isSop ? COLOR_SOP : COLOR_DEV

  return (
    <div
      style={{
        background: '#fff',
        border: `2px solid ${selected ? '#faad14' : accent}`,
        borderRadius: 10,
        padding: '10px 14px',
        minWidth: 150,
        maxWidth: 200,
        boxShadow: selected
          ? '0 0 0 3px rgba(250,173,20,0.3)'
          : '0 2px 8px rgba(0,0,0,0.10)',
        cursor: 'pointer',
        transition: 'box-shadow 0.15s, border-color 0.15s',
      }}
    >
      <Handle type="target" position={Position.Top}    style={{ opacity: 0, pointerEvents: 'none' }} />
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: 'none' }} />

      {/* 分類標籤 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 5 }}>
        {isSop
          ? <BookOutlined style={{ color: accent, fontSize: 11 }} />
          : <CodeOutlined style={{ color: accent, fontSize: 11 }} />
        }
        <span style={{ fontSize: 10, color: accent, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5 }}>
          {isSop ? 'SOP' : 'DEV'}
        </span>
      </div>

      {/* 標題 */}
      <div style={{ fontSize: 13, color: '#1B3A5C', fontWeight: 600, lineHeight: 1.4, marginBottom: 6 }}>
        {data.title}
      </div>

      {/* 標籤（最多 2 個）*/}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
        {(data.tags as string[]).slice(0, 2).map((t: string) => (
          <Tag key={t} style={{ fontSize: 10, padding: '0 4px', margin: 0, lineHeight: '16px' }}>{t}</Tag>
        ))}
        {data.tags.length > 2 && (
          <Tag style={{ fontSize: 10, padding: '0 4px', margin: 0, lineHeight: '16px', color: '#aaa' }}>
            +{data.tags.length - 2}
          </Tag>
        )}
      </div>
    </div>
  )
}

const NODE_TYPES: NodeTypes = { wiki: WikiArticleNode }

// ── 佈局計算：SOP 左側環形 / DEV 右側環形 ───────────────────────────────────
function computeLayout(graphNodes: WikiGraphNode[]): Node[] {
  const sop = graphNodes.filter((n) => n.category === 'sop')
  const dev = graphNodes.filter((n) => n.category === 'dev')

  const circleLayout = (
    group: WikiGraphNode[],
    cx: number,
    cy: number,
    radius: number,
  ): Node[] =>
    group.map((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(group.length, 1) - Math.PI / 2
      return {
        id:       node.id,
        type:     'wiki',
        position: {
          x: cx + radius * Math.cos(angle) - 85,  // 85 = node half-width
          y: cy + radius * Math.sin(angle) - 40,  // 40 = node half-height
        },
        data: { ...node },
      }
    })

  const sopRadius = Math.max(180, sop.length * 32)
  const devRadius = Math.max(150, dev.length * 32)
  const gap       = 160  // 兩群組間距

  return [
    ...circleLayout(sop, sopRadius + 50,                    350, sopRadius),
    ...circleLayout(dev, sopRadius * 2 + gap + devRadius,   350, devRadius),
  ]
}

// ── 主元件 ────────────────────────────────────────────────────────────────────
interface WikiGraphProps {
  category: 'sop' | 'dev' | 'all'
  onNodeClick: (articleId: string) => void
}

export default function WikiGraph({ category, onNodeClick }: WikiGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading] = useState(false)
  const [empty, setEmpty]     = useState(false)

  useEffect(() => {
    setLoading(true)
    setEmpty(false)
    fetchWikiGraph(category)
      .then((data) => {
        if (data.nodes.length === 0) { setEmpty(true); return }

        // nodes
        setNodes(computeLayout(data.nodes))

        // edges
        setEdges(
          data.edges.map((e) => ({
            id:     `${e.source}-${e.target}-${e.type}`,
            source: e.source,
            target: e.target,
            animated: e.type === 'link',
            style: {
              stroke:          e.type === 'link' ? COLOR_DEV : '#bbb',
              strokeWidth:     e.type === 'link' ? 2 : 1.5,
              strokeDasharray: e.type === 'tag'  ? '5 3' : undefined,
            },
            label:        e.shared_tags?.slice(0, 1).join('') ?? undefined,
            labelStyle:   { fontSize: 10, fill: '#999' },
            labelBgStyle: { fill: '#fff', opacity: 0.85 },
            labelBgPadding: [3, 4] as [number, number],
          })),
        )
      })
      .catch(() => setEmpty(true))
      .finally(() => setLoading(false))
  }, [category])

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => { onNodeClick(node.id) },
    [onNodeClick],
  )

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <Spin size="large" tip="載入圖譜中…" />
      </div>
    )
  }

  if (empty) {
    return (
      <Empty description="尚無文章或連結關係" style={{ paddingTop: 80 }} />
    )
  }

  return (
    <div style={{ width: '100%', height: '100%' }}>
      {/* 圖例 */}
      <div style={{
        position: 'absolute', top: 12, right: 12, zIndex: 10,
        background: 'rgba(255,255,255,0.92)', borderRadius: 8,
        padding: '8px 14px', boxShadow: '0 1px 6px rgba(0,0,0,0.1)',
        fontSize: 12, lineHeight: 2,
      }}>
        <div style={{ fontWeight: 700, color: '#555', marginBottom: 2 }}>圖例</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: COLOR_SOP }} />
          員工 SOP
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: COLOR_DEV }} />
          開發者 Wiki
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 24, borderTop: '2px dashed #bbb' }} />
          標籤重疊
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 24, borderTop: `2px solid ${COLOR_DEV}` }} />
          [[連結]]引用
        </div>
        <div style={{ fontSize: 11, color: '#aaa', marginTop: 4 }}>點節點開啟文章</div>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        style={{ background: COLOR_BG }}
        minZoom={0.3}
        maxZoom={2}
      >
        <Background color="#c8d4e0" gap={24} size={1} />
        <Controls style={{ bottom: 16, left: 16 }} />
        <MiniMap
          nodeColor={(n) => n.data?.category === 'sop' ? COLOR_SOP : COLOR_DEV}
          maskColor="rgba(240,244,248,0.75)"
          style={{ bottom: 16, right: 16 }}
        />
      </ReactFlow>
    </div>
  )
}
