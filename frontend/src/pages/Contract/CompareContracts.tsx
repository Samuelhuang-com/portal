/**
 * K5 — 合約並排比較
 * route: /contract/compare
 *
 * 選擇兩份合約，並排顯示所有欄位，差異欄位黃色高亮。
 */
import React, { useState, useCallback } from 'react'
import {
  Row, Col, Card, Select, Button, Table, Tag, Typography,
  Breadcrumb, Space, Spin, Empty, Badge, Tooltip,
} from 'antd'
import {
  HomeOutlined, SwapOutlined, SearchOutlined,
  CheckOutlined, WarningOutlined,
} from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import { fetchContracts, fetchContract } from '@/api/contract'
import type { ContractRecord } from '@/types/contract'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Text, Title } = Typography

// ── 欄位定義 ──────────────────────────────────────────────────────────────

interface FieldDef {
  key: keyof ContractRecord | string
  label: string
  group: string
  format?: (v: any) => string
}

const FIELDS: FieldDef[] = [
  // 基本資訊
  { key: 'contract_name',             label: '合約名稱',       group: '基本資訊' },
  { key: 'contract_type',             label: '合約類型',       group: '基本資訊' },
  { key: 'contract_status',           label: '合約狀態',       group: '基本資訊' },
  { key: 'risk_level',                label: '風險等級',       group: '基本資訊' },
  { key: 'responsible_dept',          label: '權責部門',       group: '基本資訊' },
  { key: 'using_depts',               label: '使用部門',       group: '基本資訊' },
  // 廠商
  { key: 'vendor_id',                 label: '廠商編號',       group: '廠商' },
  { key: 'vendor_name',               label: '廠商名稱',       group: '廠商' },
  // 期間
  { key: 'start_date',                label: '合約起日',       group: '期間' },
  { key: 'end_date',                  label: '合約迄日',       group: '期間' },
  { key: 'notification_days',         label: '通知天數',       group: '期間',  format: v => `${v} 天` },
  { key: 'auto_renewal',              label: '自動續約',       group: '期間',  format: v => v ? '是' : '否' },
  // 金額
  { key: 'currency',                  label: '幣別',           group: '金額' },
  { key: 'total_amount_tax_included', label: '合約總額（含稅）', group: '金額',
    format: v => `$${Number(v).toLocaleString('zh-TW')}` },
  { key: 'monthly_fixed_amount',      label: '月固定金額',     group: '金額',
    format: v => v ? `$${Number(v).toLocaleString('zh-TW')}` : '—' },
  { key: 'pricing_method',            label: '計價方式',       group: '金額' },
  // 預算
  { key: 'budget_year',               label: '預算年度',       group: '預算' },
  { key: 'budget_category_l1',        label: '預算大項',       group: '預算' },
  { key: 'budget_category_l2',        label: '預算細項',       group: '預算' },
  { key: 'accounting_code',           label: '會計科目',       group: '預算' },
  { key: 'budget_source',             label: '預算來源',       group: '預算' },
  // 公司/部門
  { key: 'signing_company',           label: '簽約公司',       group: '公司/部門' },
  { key: 'signing_dept',              label: '簽約部門',       group: '公司/部門' },
  { key: 'budget_company',            label: '預算公司',       group: '公司/部門' },
  { key: 'budget_dept',               label: '預算部門',       group: '公司/部門' },
  // 人員
  { key: 'manager',                   label: '管理人',         group: '人員' },
  { key: 'reviewer',                  label: '覆核人',         group: '人員' },
  // 設定
  { key: 'needs_purchase_order',      label: '需請購單',       group: '設定', format: v => v ? '是' : '否' },
  { key: 'require_acceptance',        label: '需驗收',         group: '設定', format: v => v ? '是' : '否' },
  { key: 'needs_allocation',          label: '需分攤',         group: '設定', format: v => v ? '是' : '否' },
]

// 欄位分組
const GROUPS = [...new Set(FIELDS.map(f => f.group))]

// ── 比較資料列型別 ─────────────────────────────────────────────────────────

interface CompareRow {
  key: string
  label: string
  group: string
  valueA: string
  valueB: string
  isDiff: boolean
}

function buildCompareRows(a: ContractRecord, b: ContractRecord): CompareRow[] {
  return FIELDS.map(f => {
    const rawA = (a as any)[f.key]
    const rawB = (b as any)[f.key]
    const valA = f.format ? f.format(rawA) : (rawA == null || rawA === '' ? '—' : String(rawA))
    const valB = f.format ? f.format(rawB) : (rawB == null || rawB === '' ? '—' : String(rawB))
    return {
      key: f.key as string,
      label: f.label,
      group: f.group,
      valueA: valA,
      valueB: valB,
      isDiff: valA !== valB,
    }
  })
}

// ── 主元件 ────────────────────────────────────────────────────────────────

export default function CompareContractsPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [searchA, setSearchA] = useState('')
  const [searchB, setSearchB] = useState('')
  const [optionsA, setOptionsA] = useState<ContractRecord[]>([])
  const [optionsB, setOptionsB] = useState<ContractRecord[]>([])
  const [selectedA, setSelectedA] = useState<ContractRecord | null>(null)
  const [selectedB, setSelectedB] = useState<ContractRecord | null>(null)
  const [loadingA, setLoadingA] = useState(false)
  const [loadingB, setLoadingB] = useState(false)
  const [filterGroup, setFilterGroup] = useState<string | null>(null)
  const [diffOnly, setDiffOnly] = useState(false)

  const searchContracts = useCallback(async (q: string, setOpts: (v: ContractRecord[]) => void, setLoad: (v: boolean) => void) => {
    if (!q.trim()) return
    setLoad(true)
    try {
      const res = await fetchContracts({ search: q, size: 20 })
      setOpts(res.items)
    } catch {
      //
    } finally {
      setLoad(false)
    }
  }, [])

  const swapContracts = () => {
    const tmp = selectedA
    setSelectedA(selectedB)
    setSelectedB(tmp)
  }

  // 比較資料
  const rows: CompareRow[] = selectedA && selectedB
    ? buildCompareRows(selectedA, selectedB)
    : []

  const filteredRows = rows
    .filter(r => !filterGroup || r.group === filterGroup)
    .filter(r => !diffOnly || r.isDiff)

  const diffCount = rows.filter(r => r.isDiff).length

  const STATUS_COLOR: Record<string, string> = {
    草稿: 'default', 審核中: 'processing', 生效中: 'success', 即將到期: 'warning', 已終止: 'error',
  }

  const columns: ColumnsType<CompareRow> = [
    {
      title: '欄位',
      dataIndex: 'label',
      key: 'label',
      width: 130,
      render: (v: string, r: CompareRow) => (
        <Space>
          {r.isDiff && <WarningOutlined style={{ color: '#faad14', fontSize: 12 }} />}
          <Text style={{ fontSize: 13 }}>{v}</Text>
        </Space>
      ),
    },
    {
      title: () => (
        <div>
          <Tag color="blue" style={{ marginBottom: 2 }}>A</Tag>
          <Text ellipsis style={{ maxWidth: 180, fontSize: 12 }}>
            {selectedA?.contract_id} {selectedA?.contract_name}
          </Text>
        </div>
      ),
      dataIndex: 'valueA',
      key: 'valueA',
      render: (v: string, r: CompareRow) => (
        <Text style={{
          fontSize: 13,
          background: r.isDiff ? '#fffbe6' : undefined,
          padding: r.isDiff ? '2px 6px' : undefined,
          borderRadius: r.isDiff ? 3 : undefined,
          display: 'inline-block',
        }}>
          {v}
        </Text>
      ),
    },
    {
      title: () => (
        <div>
          <Tag color="purple" style={{ marginBottom: 2 }}>B</Tag>
          <Text ellipsis style={{ maxWidth: 180, fontSize: 12 }}>
            {selectedB?.contract_id} {selectedB?.contract_name}
          </Text>
        </div>
      ),
      dataIndex: 'valueB',
      key: 'valueB',
      render: (v: string, r: CompareRow) => (
        <Text style={{
          fontSize: 13,
          background: r.isDiff ? '#fffbe6' : undefined,
          padding: r.isDiff ? '2px 6px' : undefined,
          borderRadius: r.isDiff ? 3 : undefined,
          display: 'inline-block',
        }}>
          {v}
        </Text>
      ),
    },
    {
      title: '',
      key: 'diff',
      width: 60,
      align: 'center' as const,
      render: (_: any, r: CompareRow) => r.isDiff
        ? <WarningOutlined style={{ color: '#faad14' }} />
        : <CheckOutlined style={{ color: '#52c41a' }} />,
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Breadcrumb style={{ marginBottom: 16 }}>
        <Breadcrumb.Item><HomeOutlined /></Breadcrumb.Item>
        <Breadcrumb.Item>{NAV_GROUP.contract}</Breadcrumb.Item>
        <Breadcrumb.Item><SwapOutlined /> {NAV_PAGE.contractCompare}</Breadcrumb.Item>
      </Breadcrumb>

      {/* 選擇合約 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex={1}>
            <Text type="secondary" style={{ display: 'block', marginBottom: 4, fontSize: 12 }}>
              合約 A
            </Text>
            <Select
              showSearch
              placeholder="搜尋合約編號或名稱"
              style={{ width: '100%' }}
              filterOption={false}
              onSearch={q => searchContracts(q, setOptionsA, setLoadingA)}
              loading={loadingA}
              value={selectedA?.contract_id}
              onChange={(v) => setSelectedA(optionsA.find(o => o.contract_id === v) || null)}
              notFoundContent={loadingA ? <Spin size="small" /> : '輸入關鍵字搜尋'}
              suffixIcon={<SearchOutlined />}
            >
              {optionsA.map(c => (
                <Select.Option key={c.contract_id} value={c.contract_id}>
                  <Tag color={STATUS_COLOR[c.contract_status] || 'default'} style={{ fontSize: 11 }}>
                    {c.contract_status}
                  </Tag>
                  {c.contract_id}　{c.contract_name}
                </Select.Option>
              ))}
            </Select>
            {selectedA && (
              <Space style={{ marginTop: 4 }}>
                <Tag color="blue">A</Tag>
                <Text style={{ fontSize: 12 }}>{selectedA.vendor_name}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  ${Number(selectedA.total_amount_tax_included).toLocaleString('zh-TW')}
                </Text>
              </Space>
            )}
          </Col>

          <Col flex="none">
            <Button
              icon={<SwapOutlined />}
              onClick={swapContracts}
              disabled={!selectedA && !selectedB}
              style={{ marginTop: 20 }}
            >
              對調
            </Button>
          </Col>

          <Col flex={1}>
            <Text type="secondary" style={{ display: 'block', marginBottom: 4, fontSize: 12 }}>
              合約 B
            </Text>
            <Select
              showSearch
              placeholder="搜尋合約編號或名稱"
              style={{ width: '100%' }}
              filterOption={false}
              onSearch={q => searchContracts(q, setOptionsB, setLoadingB)}
              loading={loadingB}
              value={selectedB?.contract_id}
              onChange={(v) => setSelectedB(optionsB.find(o => o.contract_id === v) || null)}
              notFoundContent={loadingB ? <Spin size="small" /> : '輸入關鍵字搜尋'}
              suffixIcon={<SearchOutlined />}
            >
              {optionsB.map(c => (
                <Select.Option key={c.contract_id} value={c.contract_id}>
                  <Tag color={STATUS_COLOR[c.contract_status] || 'default'} style={{ fontSize: 11 }}>
                    {c.contract_status}
                  </Tag>
                  {c.contract_id}　{c.contract_name}
                </Select.Option>
              ))}
            </Select>
            {selectedB && (
              <Space style={{ marginTop: 4 }}>
                <Tag color="purple">B</Tag>
                <Text style={{ fontSize: 12 }}>{selectedB.vendor_name}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  ${Number(selectedB.total_amount_tax_included).toLocaleString('zh-TW')}
                </Text>
              </Space>
            )}
          </Col>
        </Row>
      </Card>

      {/* 比較結果 */}
      {!selectedA || !selectedB ? (
        <Card>
          <Empty description="請選擇兩份合約以進行比較" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </Card>
      ) : (
        <Card>
          {/* 篩選工具列 */}
          <Space style={{ marginBottom: 16 }} wrap>
            <Text>
              共 <strong>{rows.length}</strong> 個欄位，
              差異 <strong style={{ color: diffCount > 0 ? '#faad14' : '#52c41a' }}>{diffCount}</strong> 個
            </Text>
            <Button
              size="small"
              type={diffOnly ? 'primary' : 'default'}
              onClick={() => setDiffOnly(v => !v)}
              style={diffOnly ? { background: '#faad14', borderColor: '#faad14' } : {}}
            >
              {diffOnly ? '✓ 僅顯示差異' : '僅顯示差異'}
            </Button>
            <Select
              size="small"
              placeholder="欄位分組"
              allowClear
              style={{ width: 120 }}
              value={filterGroup}
              onChange={setFilterGroup}
            >
              {GROUPS.map(g => <Select.Option key={g} value={g}>{g}</Select.Option>)}
            </Select>
          </Space>

          <Table
            dataSource={filteredRows}
            columns={columns}
            rowKey="key"
            size="small"
            pagination={false}
            rowClassName={(r: CompareRow) => r.isDiff ? 'contract-compare-diff-row' : ''}
          />

          <style>{`
            .contract-compare-diff-row td {
              background-color: #fffbe6 !important;
            }
            .contract-compare-diff-row:hover td {
              background-color: #fff1b8 !important;
            }
          `}</style>
        </Card>
      )}
    </div>
  )
}
