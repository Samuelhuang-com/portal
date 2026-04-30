/**
 * 保全巡檢 Sheet 頁（通用，支援所有 7 張 Sheet）
 *
 * ── 2026-04-30 整合重構 ──────────────────────────────────────────────────────
 * - 拆出 SecurityPatrolContent({ sheetKey, returnPath }) 供 SecurityDashboard 嵌入
 * - 移除「主管儀表板」Tab（已整合至 SecurityDashboard 一頁式 Dashboard）
 * - 直接呈現「巡檢紀錄」清單（月份篩選 + 批次表格 + 明細連結）
 * - returnPath prop：控制 Detail 頁「返回清單」要回到哪裡
 *     - 嵌入 Dashboard 時傳 '/security/dashboard'
 *     - 舊路由獨立使用時不傳，fallback 到 /security/patrol/:sheetKey
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Row, Col, Card, Table, Tag, Button, Space,
  Typography, Progress, message, Badge, DatePicker,
} from 'antd'
import {
  SyncOutlined, ReloadOutlined, RightOutlined,
  SafetyOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import { fetchPatrolBatches, syncPatrolFromRagic } from '@/api/securityPatrol'
import type { PatrolBatchListItem } from '@/types/securityPatrol'
import { SECURITY_SHEETS } from '@/constants/securitySheets'

const { Title, Text } = Typography

// ── 場次狀態推導 ──────────────────────────────────────────────────────────────
function deriveBatchStatus(kpi: PatrolBatchListItem['kpi']): { label: string; color: string } {
  if (!kpi || kpi.total === 0) return { label: '草稿',   color: '#999' }
  if (kpi.abnormal > 0)        return { label: '有異常', color: '#FF4D4F' }
  if (kpi.pending > 0)         return { label: '待處理', color: '#FAAD14' }
  if (kpi.unchecked === 0)     return { label: '已完成', color: '#52C41A' }
  if (kpi.completion_rate > 0) return { label: '巡檢中', color: '#4BA8E8' }
  return { label: '未開始', color: '#999' }
}

// ── 核心元件（接受 prop，供嵌入使用）────────────────────────────────────────────
export function SecurityPatrolContent({
  sheetKey,
  returnPath,
}: {
  sheetKey: string
  returnPath?: string
}) {
  const navigate  = useNavigate()
  const sheetName = SECURITY_SHEETS[sheetKey]?.name ?? sheetKey
  // 決定明細頁「返回清單」的目標路徑
  const backPath  = returnPath ?? `/security/patrol/${sheetKey}`

  const [batches,   setBatches]   = useState<PatrolBatchListItem[]>([])
  const [yearMonth, setYearMonth] = useState<string>(dayjs().format('YYYY/MM'))
  const [loading,   setLoading]   = useState(false)
  const [syncing,   setSyncing]   = useState(false)

  const loadBatches = useCallback(async () => {
    if (!sheetKey) return
    setLoading(true)
    try {
      const data = await fetchPatrolBatches(sheetKey, { year_month: yearMonth })
      setBatches(data)
    } catch {
      message.error('載入巡檢紀錄失敗')
    } finally {
      setLoading(false)
    }
  }, [sheetKey, yearMonth])

  // sheetKey 切換時重置資料
  useEffect(() => { setBatches([]) }, [sheetKey])
  useEffect(() => { loadBatches() }, [loadBatches])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncPatrolFromRagic(sheetKey)
      message.success('同步完成')
      await loadBatches()
    } catch {
      message.error('同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  // 導向明細頁（攜帶 returnPath state）
  const goDetail = (batchId: string) =>
    navigate(`/security/patrol/${sheetKey}/${batchId}`, { state: { returnPath: backPath } })

  // ── 批次清單欄位 ────────────────────────────────────────────────────────────
  const batchColumns: ColumnsType<PatrolBatchListItem> = [
    {
      title: '巡檢日期',
      dataIndex: ['batch', 'inspection_date'],
      width: 110,
      sorter: (a, b) => a.batch.inspection_date.localeCompare(b.batch.inspection_date),
      defaultSortOrder: 'descend',
    },
    {
      title: '開始時間',
      dataIndex: ['batch', 'start_time'],
      width: 130,
      render: (v) => <Text type="secondary" style={{ fontSize: 12 }}>{v || '—'}</Text>,
    },
    {
      title: '結束時間',
      dataIndex: ['batch', 'end_time'],
      width: 130,
      render: (v) => <Text type="secondary" style={{ fontSize: 12 }}>{v || '—'}</Text>,
    },
    {
      title: '工時',
      dataIndex: ['batch', 'work_hours'],
      width: 80,
      render: (v) => v ? <Tag color="geekblue">{v}</Tag> : <Text type="secondary">—</Text>,
    },
    {
      title: '巡檢人員',
      dataIndex: ['batch', 'inspector_name'],
      width: 100,
      render: (v, row) => (
        <Button type="link" style={{ padding: 0, fontWeight: 600 }}
          onClick={() => goDetail(row.batch.ragic_id)}>
          {v || row.batch.ragic_id}
        </Button>
      ),
    },
    {
      title: '狀態',
      width: 90,
      render: (_, row) => {
        const s = deriveBatchStatus(row.kpi)
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    {
      title: '巡檢進度',
      width: 190,
      render: (_, row) => {
        const { completion_rate, total, unchecked } = row.kpi
        return (
          <div>
            <Progress
              percent={completion_rate} size="small"
              strokeColor={{ from: '#FAAD14', to: '#52C41A' }}
              format={() => `${completion_rate}%`}
            />
            <Text type="secondary" style={{ fontSize: 11 }}>
              {total - unchecked} / {total} 已巡檢
            </Text>
          </div>
        )
      },
    },
    {
      title: '異常',
      dataIndex: ['kpi', 'abnormal'],
      width: 60,
      align: 'center',
      render: (v) => v > 0 ? <Badge count={v} color="#FF4D4F" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '待處理',
      dataIndex: ['kpi', 'pending'],
      width: 65,
      align: 'center',
      render: (v) => v > 0 ? <Badge count={v} color="#FAAD14" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '操作',
      width: 90,
      render: (_, row) => (
        <Button type="primary" size="small" icon={<RightOutlined />}
          style={{ background: '#1B3A5C' }}
          onClick={() => goDetail(row.batch.ragic_id)}>
          查看明細
        </Button>
      ),
    },
  ]

  // ── 渲染 ───────────────────────────────────────────────────────────────────
  return (
    <div style={{ padding: '0 2px' }}>
      <Row align="middle" justify="space-between" style={{ marginBottom: 12 }}>
        <Col>
          <Space>
            <SafetyOutlined style={{ color: '#1B3A5C' }} />
            <Title level={5} style={{ margin: 0, color: '#1B3A5C' }}>{sheetName}</Title>
          </Space>
        </Col>
        <Col>
          <Button size="small" icon={<SyncOutlined spin={syncing} />} loading={syncing} onClick={handleSync}>
            同步 Ragic
          </Button>
        </Col>
      </Row>

      <Row gutter={8} style={{ marginBottom: 12 }}>
        <Col>
          <DatePicker
            picker="month"
            value={dayjs(yearMonth, 'YYYY/MM')}
            format="YYYY/MM"
            allowClear={false}
            size="small"
            onChange={(d) => { if (d) setYearMonth(d.format('YYYY/MM')) }}
          />
        </Col>
        <Col>
          <Button size="small" icon={<ReloadOutlined />} onClick={loadBatches} loading={loading}>
            重新整理
          </Button>
        </Col>
        <Col>
          <Text type="secondary" style={{ fontSize: 12, lineHeight: '24px' }}>
            共 {batches.length} 筆
          </Text>
        </Col>
      </Row>

      <Table<PatrolBatchListItem>
        dataSource={batches}
        rowKey={(r) => r.batch.ragic_id}
        columns={batchColumns}
        loading={loading}
        size="middle"
        pagination={{ pageSize: 30, showTotal: (t) => `共 ${t} 筆` }}
        locale={{ emptyText: '尚無巡檢紀錄' }}
      />
    </div>
  )
}

// ── 路由包裝層（向下相容 /security/patrol/:sheetKey）─────────────────────────
export default function SecurityPatrolPage() {
  const { sheetKey = '' } = useParams<{ sheetKey: string }>()
  return <SecurityPatrolContent sheetKey={sheetKey} />
}
