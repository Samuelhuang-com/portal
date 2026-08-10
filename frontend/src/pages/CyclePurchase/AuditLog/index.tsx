/**
 * 週期採購 — 異常稽核紀錄查詢頁（第五期，2026-07-11 新增）
 * 路由：/cycle-purchase/audit-log
 *
 * 純查詢頁，沒有新增／修改／刪除功能——紀錄一律由系統內部在驗收單／請款單
 * 送出時自動寫入。查看權限 cycle_purchase_admin。
 *
 * 目前會被觸發的事件類型（2026-08-09）：
 *   驗收差異／請款差異（驗收單、請款單送出時）
 *   退回彙整／採購單退回／拋轉 Ragic／取消拋轉（週採「退回」系列，v1.90.24~26）
 * 仍無觸發點：補填／逾期／缺貨／替代品（保留在篩選選單裡，選了會是空的）。
 *
 * 2026-08-07：日期區間改用全站標準元件 StandardRangePicker（CLAUDE.md §8），
 * 原本是各自刻的 antd RangePicker，沒有六個標準快捷、也沒有資料基準日。
 */
import { useEffect, useState } from 'react'
import { Card, Select, Space, Table, Tag, Typography, message } from 'antd'
import dayjs from 'dayjs'
import StandardRangePicker, { type StandardRange } from '@/components/StandardRangePicker'
import { getAuditLog } from '@/api/cyclePurchase'
import type { CpAuditLog } from '@/types/cyclePurchase'

const { Title, Text } = Typography

const DOCUMENT_TYPE_LABEL: Record<string, string> = {
  request: '請購單', po: '採購單', receiving: '驗收單', payment: '請款單',
  // 2026-08-09：彙整單的 Ragic 拋轉／取消拋轉。⚠️ 拋轉是對「一整個週期＋期別＋
  // 公司範圍」的批次動作，沒有單一主鍵，document_no 放的是拋轉批次號（CPSUM-...）。
  summary: '彙整單',
}

const EVENT_TYPE_LABEL: Record<string, { label: string; color: string }> = {
  backfill:            { label: '補填',   color: 'default' },
  overdue:             { label: '逾期',   color: 'default' },
  shortage:            { label: '缺貨',   color: 'default' },
  substitute:          { label: '替代品', color: 'default' },
  receiving_variance:  { label: '驗收差異', color: 'orange' },
  payment_variance:    { label: '請款差異', color: 'red' },
  // 2026-08-09 新增的兩種「退回」。⚠️ 這裡沒對應到的 event_type 會直接顯示英文原字串，
  // 後端新增事件類型時記得回來補（v1.90.26 就漏過 revert_to_summary 一次）。
  unsummarize:         { label: '退回彙整', color: 'purple' },   // 請購單被退出彙整單
  revert_to_summary:   { label: '採購單退回', color: 'purple' }, // 採購單退回彙整單
  ragic_push:          { label: '拋轉 Ragic', color: 'blue' },
  ragic_push_cancel:   { label: '取消拋轉',   color: 'gold' },
}

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

export default function CpAuditLogPage() {
  const [rows, setRows] = useState<CpAuditLog[]>([])
  const [documentType, setDocumentType] = useState<string | undefined>(undefined)
  const [eventType, setEventType] = useState<string | undefined>(undefined)
  const [dateRange, setDateRange] = useState<StandardRange>(null)
  const [loading, setLoading] = useState(false)
  // 快捷區間的基準日（CLAUDE.md §8.2：以「資料最後一天」為準，不是今天）。
  // 稽核紀錄的資料來源就是本表的 created_at，所以掛載時另外抓一次「完全不帶
  // 篩選」的清單取最新一筆——不能用畫面上的 rows，因為 rows 本身已被日期
  // 篩選過，會讓基準日隨著使用者選的區間一起縮，快捷就跟著失準。
  const [dataEnd, setDataEnd] = useState<string>('')

  useEffect(() => {
    getAuditLog()
      .then((r) => {
        // service 端已 order_by(created_at.desc())，第一筆即最新
        if (r.data.length > 0) setDataEnd(r.data[0].created_at)
      })
      .catch(() => {})   // 取不到基準日不影響查詢；元件會在下拉底部標明退回以今天為基準
  }, [])

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
          <StandardRangePicker
            value={dateRange}
            anchor={dataEnd}
            onChange={setDateRange}
            footerNote="基準日為最新一筆稽核紀錄的時間"
          />
        </Space>

        <div style={{ marginBottom: 12 }}>
          <Text type="secondary">共 {rows.length} 筆。紀錄一律由系統自動寫入，這一頁不能新增或修改。
            「補填／逾期／缺貨／替代品」目前還沒有觸發點，選了會是空的。</Text>
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
