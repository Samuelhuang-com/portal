/**
 * 週期採購 — 採購單清單（第三期，2026-07-11 新增）
 * 路由：/cycle-purchase/pos
 *
 * 採購單由「彙整單」頁面的「轉採購單」動作產生，這裡不提供手動新增，
 * 只做清單查詢與進入詳情頁（編輯備註／預計到貨日、變更狀態）。
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card, Select, Space, Table, Tag, Typography, message } from 'antd'
import { EyeOutlined } from '@ant-design/icons'
import { getCycles, getPos } from '@/api/cyclePurchase'
import type { CpCycle, CpPO } from '@/types/cyclePurchase'

const { Title } = Typography

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  draft:     { color: 'default', label: '草稿' },
  issued:    { color: 'blue',    label: '已發出' },
  cancelled: { color: 'red',     label: '已取消' },
}

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

export default function CpPOsPage() {
  const navigate = useNavigate()

  const [rows, setRows] = useState<CpPO[]>([])
  const [cycles, setCycles] = useState<CpCycle[]>([])
  const [cycleId, setCycleId] = useState<number | undefined>(undefined)
  const [periodLabel, setPeriodLabel] = useState<string | undefined>(undefined)
  const [company, setCompany] = useState<string | undefined>(undefined)
  const [status, setStatus] = useState<string | undefined>(undefined)
  const [loading, setLoading] = useState(false)

  const load = () => {
    setLoading(true)
    Promise.all([
      getPos({ cycle_id: cycleId, period_label: periodLabel, company, status }),
      getCycles(),
    ])
      .then(([pRes, cRes]) => {
        setRows(pRes.data)
        setCycles(cRes.data)
      })
      .catch((err) => message.error(errMsg(err, '載入失敗')))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [cycleId, periodLabel, company, status])

  const periodOptions = useMemo(
    () => Array.from(new Set(rows.map((r) => r.period_label))),
    [rows],
  )
  const companyOptions = useMemo(
    () => Array.from(new Set(rows.map((r) => r.company))),
    [rows],
  )

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>週期採購 — 採購單</Title>

      <Card>
        <Space wrap style={{ marginBottom: 12 }}>
          <Select
            allowClear
            placeholder="依週期篩選"
            style={{ width: 200 }}
            value={cycleId}
            onChange={setCycleId}
            showSearch
            optionFilterProp="label"
            options={cycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
          />
          <Select
            allowClear
            placeholder="依期別篩選"
            style={{ width: 140 }}
            value={periodLabel}
            onChange={setPeriodLabel}
            showSearch
            options={periodOptions.map((p) => ({ label: p, value: p }))}
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
            placeholder="依狀態篩選"
            style={{ width: 140 }}
            value={status}
            onChange={setStatus}
            options={[
              { label: '草稿', value: 'draft' },
              { label: '已發出', value: 'issued' },
              { label: '已取消', value: 'cancelled' },
            ]}
          />
        </Space>

        <Table
          dataSource={rows}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
          columns={[
            { title: '採購單號', dataIndex: 'po_no', width: 160 },
            { title: '週期', dataIndex: 'cycle_name', width: 140 },
            { title: '期別', dataIndex: 'period_label', width: 100 },
            { title: '公司', dataIndex: 'company', width: 110 },
            { title: '供應商', dataIndex: 'vendor_name', width: 140 },
            {
              title: '總金額',
              dataIndex: 'total_amount',
              width: 120,
              align: 'right',
              render: (v: number) => Number(v).toLocaleString(),
            },
            {
              title: '狀態',
              dataIndex: 'status',
              width: 90,
              render: (v: string) => <Tag color={STATUS_TAG[v]?.color}>{STATUS_TAG[v]?.label || v}</Tag>,
            },
            { title: '採購人員', dataIndex: 'buyer_name', width: 100, render: (v?: string | null) => v || '—' },
            { title: '預計到貨日', dataIndex: 'expected_date', width: 110, render: (v?: string | null) => v || '—' },
            {
              title: '操作',
              key: 'actions',
              width: 90,
              render: (_: unknown, r: CpPO) => (
                <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/cycle-purchase/pos/${r.id}`)}>
                  檢視
                </Button>
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}
