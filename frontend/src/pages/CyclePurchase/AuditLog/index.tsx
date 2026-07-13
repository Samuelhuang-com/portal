/**
 * 週期採購 — 異常稽核紀錄查詢頁（第五期，2026-07-11 新增）
 * 路由：/cycle-purchase/audit-log
 *
 * 純查詢頁，沒有新增／修改／刪除功能——紀錄一律由系統內部在驗收單／請款單
 * 送出時自動寫入（見 cycle_purchase_receiving_service.submit_receiving／
 * cycle_purchase_payment_service.submit_payment）。這期只有「驗收差異」
 * 「請款差異」兩種事件類型會被觸發，其餘 4 種（補填／逾期／缺貨／替代品）
 * 保留在篩選選單裡但目前不會有資料。查看權限 cycle_purchase_admin。
 */
import { useEffect, useState } from 'react'
import { Card, DatePicker, Select, Space, Table, Tag, Typography, message } from 'antd'
import dayjs from 'dayjs'
import { getAuditLog } from '@/api/cyclePurchase'
import type { CpAuditLog } from '@/types/cyclePurchase'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

const DOCUMENT_TYPE_LABEL: Record<string, string> = {
  request: '請購單', po: '採購單', receiving: '驗收單', payment: '請款單',
}

const EVENT_TYPE_LABEL: Record<string, { label: string; color: string }> = {
  backfill:            { label: '補填',   color: 'default' },
  overdue:             { label: '逾期',   color: 'default' },
  shortage:            { label: '缺貨',   color: 'default' },
  substitute:          { label: '替代品', color: 'default' },
  receiving_variance:  { label: '驗收差異', color: 'orange' },
  payment_variance:    { label: '請款差異', color: 'red' },
}

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

export default function CpAuditLogPage() {
  const [rows, setRows] = useState<CpAuditLog[]>([])
  const [documentType, setDocumentType] = useState<string | undefined>(undefined)
  const [eventType, setEventType] = useState<string | undefined>(undefined)
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)
  const [loading, setLoading] = useState(false)

  const load = () => {
    setLoading(true)
    getAuditLog({
      document_type: documentType,
      event_type: eventType,
      date_from: dateRange?.[0]?.format('YYYY-MM-DD'),
      date_to: dateRange?.[1]?.format('YYYY-MM-DD'),
    })
      .then((r) => setRows(r.data))
      .catch((err) => message.error(errMsg(err, '載入失敗')))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [documentType, eventType, dateRange])

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>週期採購 — 異常稽核紀錄</Title>

      <Card>
        <Space wrap style={{ marginBottom: 12 }}>
          <Select
            allowClear
            placeholder="依關聯類型篩選"
            style={{ width: 160 }}
            value={documentType}
            onChange={setDocumentType}
            options={Object.entries(DOCUMENT_TYPE_LABEL).map(([value, label]) => ({ label, value }))}
          />
          <Select
            allowClear
            placeholder="依事件類型篩選"
            style={{ width: 160 }}
            value={eventType}
            onChange={setEventType}
            options={Object.entries(EVENT_TYPE_LABEL).map(([value, meta]) => ({ label: meta.label, value }))}
          />
          <RangePicker
            value={dateRange}
            onChange={(v) => setDateRange(v as [dayjs.Dayjs, dayjs.Dayjs] | null)}
            placeholder={['發生日期起', '發生日期迄']}
          />
        </Space>

        <div style={{ marginBottom: 12 }}>
          <Text type="secondary">共 {rows.length} 筆。目前只有「驗收差異」「請款差異」會由系統自動記錄。</Text>
        </div>

        <Table
          dataSource={rows}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 30 }}
          columns={[
            { title: '時間', dataIndex: 'created_at', width: 160, render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm') },
            {
              title: '關聯類型',
              dataIndex: 'document_type',
              width: 100,
              render: (v: string) => DOCUMENT_TYPE_LABEL[v] || v,
            },
            { title: '關聯單號', dataIndex: 'document_no', width: 150 },
            {
              title: '事件類型',
              dataIndex: 'event_type',
              width: 110,
              render: (v: string) => <Tag color={EVENT_TYPE_LABEL[v]?.color}>{EVENT_TYPE_LABEL[v]?.label || v}</Tag>,
            },
            { title: '說明', dataIndex: 'description' },
            { title: '操作人員', dataIndex: 'operator_name', width: 100, render: (v?: string | null) => v || '—' },
          ]}
        />
      </Card>
    </div>
  )
}
