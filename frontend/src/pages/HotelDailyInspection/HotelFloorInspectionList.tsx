/**
 * 飯店每日巡檢 — 頁籤「巡檢紀錄」清單 + 明細 Drawer（2026-11-10）
 *
 * 照抄 pages/MallFacilityInspection/MallFloorInspectionList.tsx（Samuel 裁示：完全照商場模組）。
 * 差異：多「來源」欄（新表／封存舊表，新舊連結同時存在）與「預估時間」。
 * 明細 Drawer 依 CLAUDE.md §7 / WORK_JOURNAL_SPEC.md §9（寬 480px、標題列含 Ragic 連結、分基本欄位與明細兩區）。
 * 狀態判定由後端 item_status（services/hotel_daily_inspection_sheet.py）提供，
 * 與每日巡檢表 Drawer、Dashboard 月曆格同一套。
 * 附圖：sync 不收「拍照」欄位，DB 沒有檔名，因此 Drawer 不顯示附圖區（請用 Ragic 連結看照片）。
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Badge, Button, Col, DatePicker, Descriptions, Divider, Drawer, Progress,
  Row, Space, Table, Tag, Typography, message,
} from 'antd'
import { LinkOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { HOTEL_DAILY_INSPECTION_SHEETS } from '@/constants/hotelDailyInspection'
import {
  fetchHotelDailyBatchDetail,
  fetchHotelDailyBatches,
  type HotelDIBatchDetail,
  type HotelDIBatchRow,
} from '@/api/hotelDailyInspection'

const { Text } = Typography

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  normal:    { color: '#52C41A', label: '正常' },
  abnormal:  { color: '#FF4D4F', label: '異常' },
  pending:   { color: '#FAAD14', label: '待處理' },
  unchecked: { color: '#d9d9d9', label: '未填' },
  // 量測／記錄型欄位（溫度、濕度、電表度數…）—— 不是異常也不是合格
  measure:   { color: '#4BA8E8', label: '記錄值' },
}

export default function HotelFloorInspectionList({ sheetKey, tabLabel }: { sheetKey: string; tabLabel?: string }) {
  const sheet = HOTEL_DAILY_INSPECTION_SHEETS[sheetKey]
  // 頁籤名稱可在頁面上修改（2026-11-10）；Drawer 標題跟著目前名稱
  const label = tabLabel || sheet?.title
  const [yearMonth, setYearMonth] = useState<string>(dayjs().format('YYYY/MM'))
  const [loading,   setLoading]   = useState(false)
  const [rows,      setRows]      = useState<HotelDIBatchRow[]>([])
  const [error,     setError]     = useState<string | null>(null)

  // ── 明細 Drawer（CLAUDE.md §7 強制規範）─────────────────────────────────
  const [drawerOpen,    setDrawerOpen]    = useState(false)
  const [detail,        setDetail]        = useState<HotelDIBatchDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setRows(await fetchHotelDailyBatches(sheetKey, { year_month: yearMonth }))
    } catch (e) {
      setRows([])
      setError(e instanceof Error ? e.message : '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [sheetKey, yearMonth])

  useEffect(() => { load() }, [load])

  const openDetail = useCallback(async (batchId: string) => {
    setDrawerOpen(true)
    setDetailLoading(true)
    setDetail(null)
    try {
      setDetail(await fetchHotelDailyBatchDetail(sheetKey, batchId))
    } catch {
      message.error('載入場次明細失敗')
      setDrawerOpen(false)
    } finally {
      setDetailLoading(false)
    }
  }, [sheetKey])

  const columns = [
    {
      title: '巡檢日期',
      dataIndex: 'inspection_date',
      width: 110,
      render: (v: string) => v || '—',
      sorter: (a: HotelDIBatchRow, b: HotelDIBatchRow) => a.inspection_date.localeCompare(b.inspection_date),
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '來源',
      width: 150,
      render: (_: unknown, r: HotelDIBatchRow) => (
        <Tag color={r.archived ? 'default' : 'blue'} style={{ whiteSpace: 'normal' }}>
          {r.source_label || '—'}
        </Tag>
      ),
    },
    {
      title: '巡檢人員',
      dataIndex: 'inspector_name',
      width: 100,
      render: (v: string) => v || '—',
    },
    {
      title: '狀態',
      width: 90,
      render: (_: unknown, r: HotelDIBatchRow) => {
        if (r.abnormal > 0) return <Tag color="#FF4D4F">有異常</Tag>
        if (r.pending  > 0) return <Tag color="#FAAD14">待處理</Tag>
        if (r.checked >= r.total && r.total > 0) return <Tag color="#52C41A">已完成</Tag>
        return <Tag color="#4BA8E8">巡檢中</Tag>
      },
    },
    {
      title: '巡檢進度',
      width: 200,
      render: (_: unknown, r: HotelDIBatchRow) => (
        <div>
          <Progress
            percent={r.completion_rate}
            size="small"
            strokeColor={{ from: '#FAAD14', to: '#52C41A' }}
            format={() => `${r.completion_rate}%`}
          />
          <Text type="secondary" style={{ fontSize: 11 }}>
            {r.checked} / {r.total} 已巡檢
          </Text>
        </div>
      ),
    },
    {
      title: '工時',
      width: 90,
      render: (_: unknown, r: HotelDIBatchRow) => r.work_hours || <Text type="secondary">—</Text>,
    },
    {
      title: '預估時間',
      width: 90,
      render: (_: unknown, r: HotelDIBatchRow) =>
        r.estimated_minutes != null ? `${r.estimated_minutes} 分` : <Text type="secondary">—</Text>,
    },
    {
      title: '異常',
      dataIndex: 'abnormal',
      width: 65,
      align: 'center' as const,
      render: (v: number) => (v > 0 ? <Badge count={v} color="#FF4D4F" /> : <Text type="secondary">—</Text>),
    },
    {
      title: '待處理',
      dataIndex: 'pending',
      width: 65,
      align: 'center' as const,
      render: (v: number) => (v > 0 ? <Badge count={v} color="#FAAD14" /> : <Text type="secondary">—</Text>),
    },
  ]

  const allItems       = detail?.items ?? []
  const equipmentItems = allItems.filter((it) => it.status !== 'note')
  const metaItems      = allItems.filter((it) => it.status === 'note')

  return (
    <div>
      {error && (
        <Alert type="error" message={error} style={{ marginBottom: 16 }}
               closable onClose={() => setError(null)} />
      )}
      <Row gutter={8} style={{ marginBottom: 16 }} align="middle">
        <Col>
          <DatePicker
            picker="month"
            value={dayjs(yearMonth, 'YYYY/MM')}
            format="YYYY/MM"
            allowClear={false}
            onChange={(d) => { if (d) setYearMonth(d.format('YYYY/MM')) }}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            重新整理
          </Button>
        </Col>
        <Col flex="auto" style={{ textAlign: 'right' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>點擊任一列查看該場次的設備明細</Text>
        </Col>
      </Row>
      <Table<HotelDIBatchRow>
        dataSource={rows}
        rowKey="id"
        columns={columns}
        loading={loading}
        size="middle"
        onRow={(r) => ({
          onClick: () => openDetail(r.id),
          style:   { cursor: 'pointer' },
        })}
        pagination={{ pageSize: 30, showTotal: (t) => `共 ${t} 筆` }}
        locale={{ emptyText: '尚無巡檢紀錄（請先執行資料同步）' }}
      />

      {/* ── 明細 Drawer（CLAUDE.md §7 / WORK_JOURNAL_SPEC.md §9）───────────── */}
      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={480}
        title={
          <Space size={8} wrap>
            <Tag color={sheet?.color}>{detail?.batch.tab_label || label}</Tag>
            <span style={{ fontWeight: 600 }}>
              {detail?.batch.tab_label || label}：{detail?.batch.inspection_date ?? ''}
            </span>
            {detail?.batch.ragic_url && (
              <a
                href={detail.batch.ragic_url}
                target="_blank"
                rel="noreferrer"
                style={{ color: '#4BA8E8', fontSize: 12 }}
              >
                <LinkOutlined /> 在 Ragic 查看
              </a>
            )}
          </Space>
        }
      >
        {detailLoading && <Text type="secondary">載入中…</Text>}
        {detail && (
          <>
            <Descriptions column={1} size="small" bordered
                          labelStyle={{ width: 110, background: '#f5f7fa', fontWeight: 500 }} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="巡檢日期">
                <b>{detail.batch.inspection_date || '—'}</b>
              </Descriptions.Item>
              <Descriptions.Item label="巡檢人員">{detail.batch.inspector_name || '—'}</Descriptions.Item>
              <Descriptions.Item label="開始巡檢時間">{detail.batch.start_time || '—'}</Descriptions.Item>
              <Descriptions.Item label="巡檢結束時間">{detail.batch.end_time || '—'}</Descriptions.Item>
              <Descriptions.Item label="工時計算">{detail.batch.work_hours || '—'}</Descriptions.Item>
              <Descriptions.Item label="預估時間">
                {detail.batch.estimated_minutes != null ? `${detail.batch.estimated_minutes} 分` : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="來源">
                <Tag color={detail.batch.archived ? 'default' : 'blue'}>{detail.batch.source_label || '—'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="巡檢進度">
                <b>{detail.kpi.completion_rate}%</b>
                <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                  （{detail.kpi.checked} / {detail.kpi.total} 項）
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="異常 / 待處理">
                {detail.kpi.abnormal > 0 ? <Tag color="#FF4D4F">異常 {detail.kpi.abnormal}</Tag> : null}
                {detail.kpi.pending  > 0 ? <Tag color="#FAAD14">待處理 {detail.kpi.pending}</Tag> : null}
                {detail.kpi.abnormal === 0 && detail.kpi.pending === 0 ? <Text type="secondary">—</Text> : null}
              </Descriptions.Item>
            </Descriptions>

            {/* ② 設備巡檢明細（排除附註欄位）*/}
            <Text strong style={{ display: 'block', marginBottom: 8 }}>
              設備巡檢明細（{equipmentItems.length} 項）
            </Text>
            <Descriptions column={1} size="small" bordered
                          labelStyle={{ width: 200, background: '#f5f7fa', fontWeight: 500 }}>
              {equipmentItems.map((it) => {
                const st = STATUS_TAG[it.status] ?? STATUS_TAG.unchecked
                return (
                  <Descriptions.Item key={it.ragic_id} label={it.item_name}>
                    <Tag color={st.color}>{it.result_raw || st.label}</Tag>
                  </Descriptions.Item>
                )
              })}
            </Descriptions>

            {/* ③ 其他欄位（異常說明等）：純文字，不套狀態色 */}
            {metaItems.length > 0 && (
              <>
                <Divider style={{ margin: '16px 0 8px' }} />
                <Text strong style={{ display: 'block', marginBottom: 8 }}>
                  其他欄位（{metaItems.length} 項）
                </Text>
                <Descriptions column={1} size="small" bordered
                              labelStyle={{ width: 200, background: '#f5f7fa', fontWeight: 500 }}>
                  {metaItems.map((it) => (
                    <Descriptions.Item key={it.ragic_id} label={it.item_name}>
                      {it.result_raw
                        ? <Text style={{ whiteSpace: 'pre-wrap' }}>{it.result_raw}</Text>
                        : <Text type="secondary">—</Text>}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </>
            )}
          </>
        )}
      </Drawer>
    </div>
  )
}
