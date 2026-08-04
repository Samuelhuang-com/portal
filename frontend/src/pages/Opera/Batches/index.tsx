/**
 * 匯入紀錄（/opera/batches）
 * 規格書：docs/SPEC_opera_analytics.md §11.7
 *
 * 點擊列開啟 Drawer，顯示 footer 對帳明細與錯誤清單。
 */
import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, Descriptions, Drawer, Empty, Select, Space, Spin,
  Table, Tag, Typography, message,
} from 'antd'
import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

import { batchErrorsCsvUrl, fetchBatch, fetchBatchErrors, fetchBatches } from '@/api/opera'
import type { ImportBatch, ImportIssue } from '@/types/opera'
import {
  BRAND, EMPTY, GREEN, ORANGE, QUALITY_TAG, RED, STATUS_TAG, fmtInt, fmtMoney,
} from '../components/formatters'

const { Title, Text } = Typography

const OperaBatchesPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<ImportBatch[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [sourceType, setSourceType] = useState<string>('')
  const [status, setStatus] = useState<string>('')

  const [detail, setDetail] = useState<ImportBatch | null>(null)
  const [issues, setIssues] = useState<ImportIssue[]>([])
  const [issueTotal, setIssueTotal] = useState(0)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerLoading, setDrawerLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchBatches({
        page, page_size: pageSize,
        source_type: sourceType || undefined,
        status: status || undefined,
      })
      setItems(res.items)
      setTotal(res.total)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入匯入紀錄失敗')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, sourceType, status])

  useEffect(() => { load() }, [load])

  const openDrawer = useCallback(async (row: ImportBatch) => {
    setDetail(row)
    setDrawerOpen(true)
    setDrawerLoading(true)
    try {
      const [full, errs] = await Promise.all([
        fetchBatch(row.id),
        fetchBatchErrors(row.id, { page: 1, page_size: 200 }),
      ])
      setDetail(full)
      setIssues(errs.items)
      setIssueTotal(errs.total)
    } catch {
      setIssues([])
      setIssueTotal(0)
    } finally {
      setDrawerLoading(false)
    }
  }, [])

  const columns: ColumnsType<ImportBatch> = [
    { title: '批次', dataIndex: 'id', width: 70, fixed: 'left', render: (v: number) => `#${v}` },
    {
      title: '來源報表', dataIndex: 'source_label', width: 170,
      render: (v: string) => <Tag color="blue">{v}</Tag>,
    },
    { title: '檔名', dataIndex: 'source_file_name', ellipsis: true },
    {
      title: '資料期間', width: 190,
      render: (_, r) => (r.report_start_date ? `${r.report_start_date} ～ ${r.report_end_date}` : EMPTY),
    },
    { title: '有效列數', dataIndex: 'row_count_source', align: 'right', width: 90, render: fmtInt },
    {
      title: '新增', dataIndex: 'row_count_inserted', align: 'right', width: 80,
      render: (v: number) => <Text style={{ color: v ? GREEN : undefined }}>{fmtInt(v)}</Text>,
    },
    {
      title: '更新', dataIndex: 'row_count_updated', align: 'right', width: 80,
      render: (v: number) => <Text style={{ color: v ? ORANGE : undefined }}>{fmtInt(v)}</Text>,
    },
    {
      title: '拒絕', dataIndex: 'row_count_rejected', align: 'right', width: 80,
      render: (v: number) => <Text style={{ color: v ? RED : undefined }}>{fmtInt(v)}</Text>,
    },
    {
      title: '品質', dataIndex: 'quality_result', width: 130,
      render: (v: string) => {
        const t = QUALITY_TAG[v]
        return t ? <Tag color={t.color}>{t.text}</Tag> : EMPTY
      },
    },
    {
      title: '狀態', dataIndex: 'status', width: 90,
      render: (v: string) => {
        const t = STATUS_TAG[v] || { color: 'default', text: v }
        return <Tag color={t.color}>{t.text}</Tag>
      },
    },
    { title: '上傳者', dataIndex: 'uploaded_by_name', width: 110, render: (v: string) => v || EMPTY },
    { title: '匯入時間', dataIndex: 'completed_at', width: 145, render: (v: string) => v || EMPTY },
  ]

  const reconcileItems = detail?.reconcile?.footer?.items || []
  const qualityChecks = detail?.reconcile?.quality_checks || []

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ color: BRAND }}>匯入紀錄</Title>

      <Card size="small">
        <Space wrap style={{ marginBottom: 12 }}>
          <Select
            allowClear placeholder="來源報表" style={{ width: 200 }}
            value={sourceType || undefined}
            onChange={(v) => { setSourceType(v || ''); setPage(1) }}
            options={[
              { value: 'DEPARTURE', label: 'Departure All' },
              { value: 'HISTORY_FORECAST', label: 'History and Forecast' },
            ]}
          />
          <Select
            allowClear placeholder="狀態" style={{ width: 140 }}
            value={status || undefined}
            onChange={(v) => { setStatus(v || ''); setPage(1) }}
            options={Object.entries(STATUS_TAG).map(([k, v]) => ({ value: k, label: v.text }))}
          />
          <Button icon={<ReloadOutlined />} onClick={load}>重新整理</Button>
        </Space>

        <Table
          rowKey="id"
          size="small"
          loading={loading}
          dataSource={items}
          columns={columns}
          scroll={{ x: 1500 }}
          pagination={{
            current: page, pageSize, total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 筆`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps) },
          }}
          onRow={(record) => ({ onClick: () => openDrawer(record), style: { cursor: 'pointer' } })}
        />
      </Card>

      {/* ── 批次明細 Drawer ─────────────────────────────────────────────── */}
      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={640}
        title={
          detail ? (
            <Space wrap>
              <Tag color="blue">{detail.source_label}</Tag>
              <Text strong style={{ color: BRAND }}>{`匯入批次：#${detail.id}`}</Text>
              {detail.quality_result && QUALITY_TAG[detail.quality_result] && (
                <Tag color={QUALITY_TAG[detail.quality_result].color}>
                  {QUALITY_TAG[detail.quality_result].text}
                </Tag>
              )}
            </Space>
          ) : '匯入批次'
        }
      >
        <Spin spinning={drawerLoading}>
          {!detail ? <Empty /> : (
            <>
              {detail.status === 'FAILED' && detail.error_message && (
                <Alert
                  type="error"
                  showIcon
                  style={{ marginBottom: 12 }}
                  message="這個批次匯入失敗，已整批復原"
                  description={detail.error_message}
                />
              )}

              {/* ① 基本欄位 */}
              <Descriptions size="small" column={1} bordered title="基本欄位">
                <Descriptions.Item label="來源報表">{detail.source_label}</Descriptions.Item>
                <Descriptions.Item label="檔案名稱">{detail.source_file_name}</Descriptions.Item>
                <Descriptions.Item label="資料期間">
                  {detail.report_start_date ? `${detail.report_start_date} ～ ${detail.report_end_date}` : EMPTY}
                </Descriptions.Item>
                <Descriptions.Item label="有效列數">{fmtInt(detail.row_count_source)}</Descriptions.Item>
                <Descriptions.Item label="新增／更新／略過／拒絕">
                  <Space size={8}>
                    <Text style={{ color: GREEN }}>{fmtInt(detail.row_count_inserted)}</Text>
                    <span>/</span>
                    <Text style={{ color: ORANGE }}>{fmtInt(detail.row_count_updated)}</Text>
                    <span>/</span>
                    <Text>{fmtInt(detail.row_count_skipped)}</Text>
                    <span>/</span>
                    <Text style={{ color: detail.row_count_rejected ? RED : undefined }}>
                      {fmtInt(detail.row_count_rejected)}
                    </Text>
                  </Space>
                </Descriptions.Item>
              </Descriptions>

              {/* ② 明細欄位 */}
              <Descriptions size="small" column={1} bordered title="明細欄位" style={{ marginTop: 16 }}>
                {Object.entries(detail.detail || {}).map(([k, v]) => (
                  <Descriptions.Item key={k} label={k}>
                    {v === '' ? <Text type="secondary">{EMPTY}</Text> : v}
                  </Descriptions.Item>
                ))}
              </Descriptions>

              {/* Footer 對帳 */}
              {reconcileItems.length > 0 && (
                <Card size="small" title="Footer 對帳" style={{ marginTop: 16 }}>
                  <Table
                    size="small"
                    rowKey="footer_key"
                    pagination={false}
                    dataSource={reconcileItems}
                    columns={[
                      { title: '項目', dataIndex: 'label', width: 100 },
                      { title: 'footer', dataIndex: 'footer_value', align: 'right', render: (v: number) => fmtMoney(v) },
                      { title: '程式彙總', dataIndex: 'computed_value', align: 'right', render: (v: number) => fmtMoney(v) },
                      {
                        title: '差異', dataIndex: 'diff', align: 'right',
                        render: (v: number, r) => <Text style={{ color: r.ok ? GREEN : RED }}>{r.ok ? '0' : fmtMoney(v)}</Text>,
                      },
                    ]}
                  />
                </Card>
              )}

              {/* 品質檢查 */}
              {qualityChecks.length > 0 && (
                <Card size="small" title="資料品質檢查" style={{ marginTop: 12 }}>
                  <Table
                    size="small"
                    rowKey="name"
                    pagination={false}
                    dataSource={qualityChecks}
                    columns={[
                      { title: '項目', dataIndex: 'name', width: 170 },
                      {
                        title: '結果', dataIndex: 'ok', width: 70,
                        render: (ok: boolean) => <Tag color={ok ? 'success' : 'warning'}>{ok ? '通過' : '未過'}</Tag>,
                      },
                      { title: '說明', dataIndex: 'detail' },
                    ]}
                  />
                </Card>
              )}

              {/* 錯誤明細 */}
              <Card
                size="small"
                title={`錯誤與警示（${fmtInt(issueTotal)} 筆）`}
                style={{ marginTop: 12 }}
                extra={
                  issueTotal > 0 && (
                    <Button
                      size="small"
                      icon={<DownloadOutlined />}
                      href={batchErrorsCsvUrl(detail.id)}
                      target="_blank"
                    >
                      下載 CSV
                    </Button>
                  )
                }
              >
                {issues.length === 0 ? <Empty description="無錯誤或警示" /> : (
                  <Table
                    size="small"
                    rowKey={(r, i) => `${r.source_row_no}-${r.error_code}-${i}`}
                    dataSource={issues}
                    pagination={{ pageSize: 10 }}
                    columns={[
                      {
                        title: '嚴重度', dataIndex: 'severity', width: 80,
                        render: (s: string) => <Tag color={s === 'ERROR' ? 'red' : 'orange'}>{s}</Tag>,
                      },
                      { title: '列號', dataIndex: 'source_row_no', width: 70, render: (n: number) => (n > 0 ? n : EMPTY) },
                      { title: '說明', dataIndex: 'error_message' },
                    ]}
                  />
                )}
              </Card>
            </>
          )}
        </Spin>
      </Drawer>
    </div>
  )
}

export default OperaBatchesPage
