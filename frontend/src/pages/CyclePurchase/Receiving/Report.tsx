/**
 * 週期採購 — 進貨數量報表（第四期，2026-07-11 新增）
 * 路由：/cycle-purchase/receiving-report
 *
 * 依月份＋公司＋供應商＋料號彙總已送出（completed／discrepancy）驗收單的
 * 驗收數量，草稿驗收單不算。獨立權限 cycle_purchase_report。
 */
import { useEffect, useMemo, useState } from 'react'
import { Card, DatePicker, Select, Space, Table, Typography, message } from 'antd'
import dayjs from 'dayjs'
import { getReceivingReport, getVendors } from '@/api/cyclePurchase'
import type { CpReceivingReportRow, CpVendor } from '@/types/cyclePurchase'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

export default function CpReceivingReportPage() {
  const [rows, setRows] = useState<CpReceivingReportRow[]>([])
  const [vendors, setVendors] = useState<CpVendor[]>([])
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)
  const [company, setCompany] = useState<string | undefined>(undefined)
  const [vendorId, setVendorId] = useState<number | undefined>(undefined)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getVendors().then((r) => setVendors(r.data)).catch(() => {})
  }, [])

  const load = () => {
    setLoading(true)
    getReceivingReport({
      date_from: dateRange?.[0]?.format('YYYY-MM-DD'),
      date_to: dateRange?.[1]?.format('YYYY-MM-DD'),
      company,
      vendor_id: vendorId,
    })
      .then((r) => setRows(r.data))
      .catch((err) => message.error(errMsg(err, '載入報表失敗')))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [dateRange, company, vendorId])

  const companyOptions = useMemo(
    () => Array.from(new Set(rows.map((r) => r.company))),
    [rows],
  )

  const totalAmount = useMemo(
    () => rows.reduce((sum, r) => sum + Number(r.total_amount), 0),
    [rows],
  )

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>週期採購 — 進貨數量報表</Title>

      <Card>
        <Space wrap style={{ marginBottom: 12 }}>
          <RangePicker
            value={dateRange}
            onChange={(v) => setDateRange(v as [dayjs.Dayjs, dayjs.Dayjs] | null)}
            placeholder={['驗收日期起', '驗收日期迄']}
          />
          <Select
            allowClear
            placeholder="依公司篩選"
            style={{ width: 140 }}
            value={company}
            onChange={setCompany}
            options={companyOptions.map((c) => ({ label: c, value: c }))}
          />
          <Select
            allowClear
            placeholder="依供應商篩選"
            style={{ width: 180 }}
            value={vendorId}
            onChange={setVendorId}
            showSearch
            optionFilterProp="label"
            options={vendors.map((v) => ({ label: v.vendor_name, value: v.id }))}
          />
        </Space>

        <div style={{ marginBottom: 12 }}>
          <Text type="secondary">
            只統計已送出（完成／有差異）的驗收單，草稿不算。共 {rows.length} 筆，總金額 {totalAmount.toLocaleString()}
          </Text>
        </div>

        <Table
          dataSource={rows}
          rowKey={(r) => `${r.period}|${r.company}|${r.vendor_id ?? 'none'}|${r.item_id}`}
          loading={loading}
          size="small"
          pagination={{ pageSize: 30 }}
          columns={[
            { title: '月份', dataIndex: 'period', width: 90 },
            { title: '公司', dataIndex: 'company', width: 110 },
            { title: '供應商', dataIndex: 'vendor_name', width: 140, render: (v?: string | null) => v || '—' },
            { title: '料號', dataIndex: 'item_code', width: 110 },
            { title: '品名', dataIndex: 'item_name' },
            { title: '單位', dataIndex: 'unit', width: 70 },
            { title: '累計驗收數量', dataIndex: 'total_received_qty', width: 110, align: 'right' as const },
            {
              title: '金額',
              dataIndex: 'total_amount',
              width: 120,
              align: 'right' as const,
              render: (v: number) => Number(v).toLocaleString(),
            },
            { title: '驗收單數', dataIndex: 'receiving_count', width: 90, align: 'right' as const },
          ]}
        />
      </Card>
    </div>
  )
}
