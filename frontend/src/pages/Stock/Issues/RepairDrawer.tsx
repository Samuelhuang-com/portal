/**
 * 商場報修單明細 Drawer（CLAUDE.md §7 格式：標題列 [Tag] 來源：識別碼 [🔗 在 Ragic 查看]）
 * 2026-11-20：領用／雜收單的關聯報修單、單據明細共用；資料即時從 luqun_repair 讀取
 */
import { useEffect, useState } from 'react'
import { Descriptions, Drawer, Space, Spin, Table, Tag, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { LinkOutlined } from '@ant-design/icons'
import { errMsg, fetchRepairDetail, fetchRepairLinks, type RepairCase, type RepairDocLink } from '@/api/stock'

const { Text } = Typography

// 基本欄位（上方 Descriptions）；其餘 detail 欄位進明細區
const BASIC_KEYS = ['報修編號', '標題', '報修人姓名', '報修類型', '發生樓層', '房號', '發生時間', '處理狀況']

function renderValue(k: string, v: string | number | null | undefined) {
  if (v === null || v === undefined || v === '') return '—'
  if (k === '處理狀況' || k === '狀態') return <Tag>{String(v)}</Tag>
  const text = typeof v === 'number' && k.includes('費用')
    ? `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
    : String(v)
  return k === '總費用' ? <b>{text}</b> : text
}

const money = (v: number | null) => (v == null ? '—' : `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`)

export default function RepairDrawer({ code, ragicId, onClose }: {
  code: string; ragicId: string | null; onClose: () => void
}) {
  const [item, setItem] = useState<RepairCase | null>(null)
  const [links, setLinks] = useState<RepairDocLink[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!ragicId) return
    let alive = true
    setLoading(true)
    setItem(null)
    setLinks([])
    Promise.all([
      fetchRepairDetail(code, ragicId).then((r) => r.data),
      fetchRepairLinks(code, ragicId).then((r) => r.data).catch(() => [] as RepairDocLink[]),
    ])
      .then(([c, l]) => {
        if (!alive) return
        setItem(c)
        setLinks(l)
      })
      .catch((e) => message.error(errMsg(e, '讀取報修單失敗')))
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [code, ragicId])

  const identifier = String(item?.detail['報修編號'] ?? item?.case_no ?? ragicId ?? '')
  const title = (
    <Space wrap>
      <Tag color="orange">報修</Tag>
      <span>{`商場報修：${identifier}`}</span>
      {item?.ragic_url && (
        <a href={item.ragic_url} target="_blank" rel="noreferrer" style={{ color: '#4BA8E8' }}>
          <LinkOutlined /> 在 Ragic 查看
        </a>)}
    </Space>)

  const detailKeys = item ? Object.keys(item.detail).filter((k) => !BASIC_KEYS.includes(k)) : []
  const linkCols: ColumnsType<RepairDocLink> = [
    { title: '單號', dataIndex: 'doc_no' },
    { title: '類型', dataIndex: 'doc_type_label', width: 80 },
    { title: '倉庫', dataIndex: 'warehouse_name' },
    { title: '單據日', dataIndex: 'doc_date', width: 100 },
    { title: '狀態', dataIndex: 'status_label', width: 90 },
    { title: '金額', dataIndex: 'total_amount', width: 100, align: 'right', render: (v: number | null) => money(v) },
  ]

  return (
    <Drawer open={!!ragicId} width={480} onClose={onClose} title={title} destroyOnClose>
      {loading && <Spin />}
      {item && (
        <>
          <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
            {BASIC_KEYS.map((k) => (
              <Descriptions.Item key={k} label={k}>{renderValue(k, item.detail[k])}</Descriptions.Item>))}
          </Descriptions>
          {detailKeys.length > 0 && (
            <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
              {detailKeys.map((k) => (
                <Descriptions.Item key={k} label={k}>{renderValue(k, item.detail[k])}</Descriptions.Item>))}
            </Descriptions>
          )}
          <Text strong>關聯的領用／雜收單</Text>
          <Table<RepairDocLink> size="small" rowKey="id" pagination={false} dataSource={links} columns={linkCols}
            style={{ marginTop: 8 }} locale={{ emptyText: '尚無關聯單據' }} />
        </>
      )}
    </Drawer>
  )
}
