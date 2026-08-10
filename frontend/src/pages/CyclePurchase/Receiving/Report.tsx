/**
 * 週期採購 — 進貨數量報表（第四期，2026-07-11 新增）
 * 路由：/cycle-purchase/receiving-report
 *
 * 依月份＋公司＋供應商＋料號彙總已送出（completed／discrepancy）驗收單的
 * 驗收數量，草稿驗收單不算。獨立權限 cycle_purchase_report。
 *
 * 2026-08-07：日期區間改用全站標準元件 StandardRangePicker（CLAUDE.md §8），
 * 原本是各自刻的 antd RangePicker，沒有六個標準快捷、也沒有資料基準日。
 */
import { useEffect, useMemo, useState } from 'react'
import { Card, Select, Space, Table, Typography, message } from 'antd'
import dayjs from 'dayjs'
import StandardRangePicker, { type StandardRange } from '@/components/StandardRangePicker'
import { getReceivingList, getReceivingReport, getVendors } from '@/api/cyclePurchase'
import type { CpReceivingReportRow, CpVendor } from '@/types/cyclePurchase'

const { Title, Text } = Typography

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

export default function CpReceivingReportPage() {
  const [rows, setRows] = useState<CpReceivingReportRow[]>([])
  const [vendors, setVendors] = useState<CpVendor[]>([])
  const [dateRange, setDateRange] = useState<StandardRange>(null)
  const [company, setCompany] = useState<string | undefined>(undefined)
  const [vendorId, setVendorId] = useState<number | undefined>(undefined)
  const [loading, setLoading] = useState(false)
  // 快捷區間的基準日（CLAUDE.md §8.2：以「資料最後一天」為準，不是今天）。
  // 本頁篩的是驗收日期，所以基準日要取最後一張驗收單的 received_date。
  const [dataEnd, setDataEnd] = useState<string>('')

  useEffect(() => {
    getVendors().then((r) => setVendors(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    // 備援來源：報表自己的最後月份。period 是 YYYY-MM，只能推到月底，
    // 但資料不可能晚於今天，所以取兩者較早的那一個。
    const fallbackFromReport = async () => {
      try {
        const r = await getReceivingReport()
        const periods = r.data.map((x) => x.period).filter(Boolean).sort()
        if (periods.length === 0) return
        const monthEnd = dayjs(`${periods[periods.length - 1]}-01`).endOf('month')
        const today = dayjs()
        setDataEnd((monthEnd.isAfter(today) ? today : monthEnd).format('YYYY-MM-DD'))
      } catch {
        /* 取不到基準日不影響查詢 */
      }
    }

    // 主要來源：驗收單清單的最大 received_date（與本頁篩選的是同一個欄位，最精確）
    getReceivingList()
      .then((r) => {
        const dates = r.data.map((x) => x.received_date).filter(Boolean).sort()
        if (dates.length > 0) setDataEnd(dates[dates.length - 1])
        else void fallbackFromReport()
      })
      // 驗收單清單要 cycle_purchase_view，只有 cycle_purchase_report 的人會拿到 403，
      // 這時退而求其次用報表推。兩邊都取不到就不傳 anchor，元件會在下拉底部標明
      // 「暫以今天為基準」，不會靜默用錯基準。
      .catch(() => void fallbackFromReport())
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
          <StandardRangePicker
            value={dateRange}
            anchor={dataEnd}
            onChange={setDateRange}
            footerNote="篩選的是驗收日期"
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
