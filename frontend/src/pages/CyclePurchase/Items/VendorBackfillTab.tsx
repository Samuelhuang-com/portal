/**
 * 週期採購 — 料號主檔 TAB「供應商資料回填」（2026-09-30 新增）
 *
 * 背景：料號主檔的「預設供應商」與料號對照的「叫貨供應商」很多指向當初匯入時用
 * **簡稱**建的週採供應商（未對照合約主檔），畫面顯示簡稱、拋轉 Ragic 時廠商欄會是空的。
 *
 * 流程（Samuel 2026-09-30 裁示）：
 *   1. 按「同步 Ragic 廠商資料」→ 後端依序跑 Ragic→合約廠商、合約廠商→週採供應商，
 *      再即時讀 Ragic 廠商資料表的「簡稱」產生比對預覽（這一步不改料號）。
 *   2. 簡稱相同 → 預設勾選；名稱相似 → 使用者自己從候選挑；Ragic 找不到 → 只列出不處理。
 *   3. 按「套用」才寫入：料號預設供應商＋料號對照叫貨供應商改指向全名正本。
 *      孤兒本身不停用（要整筆合併請到供應商主檔用「合併」）。
 *   4. 2026-09-30 追加：尚未拋轉 Ragic、尚未轉採購單的彙整列也一併改指全名，
 *      否則拋轉前的廠商防呆會把它們擋下。已拋轉／已轉採購單的彙整列不動。
 *
 * 權限：cycle_purchase_vendor_backfill（TAB 只對有此權限者顯示，後端同樣檢查）。
 * 後端：POST /cycle-purchase/items/vendor-backfill/sync、/apply
 */
import { useMemo, useState } from 'react'
import {
  Alert, Button, Card, Empty, Popconfirm, Segmented, Select, Space, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import { LinkOutlined, SyncOutlined, CheckOutlined } from '@ant-design/icons'
import { applyVendorBackfill, syncVendorBackfill } from '@/api/cyclePurchase'
import type {
  CpBackfillApplyResult, CpBackfillCandidate, CpBackfillMatchType, CpBackfillPreview, CpBackfillRow,
} from '@/types/cyclePurchase'

const { Text } = Typography

const MATCH_TAG: Record<CpBackfillMatchType, { color: string; label: string; tip: string }> = {
  short: { color: 'green', label: '簡稱相同', tip: 'Ragic 廠商資料表的「簡稱」與週採供應商名稱完全相同，預設勾選' },
  similar: { color: 'blue', label: '名稱相似・請選定', tip: 'Ragic 沒有相同簡稱，但有名稱相似的廠商，請自行選定正確的一家' },
  none: { color: 'orange', label: 'Ragic 找不到', tip: '請先到 Ragic 廠商資料表建檔（可順便填簡稱），再按一次同步' },
}

type Filter = 'all' | CpBackfillMatchType

function errDetail(e: unknown): string {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof d === 'string' ? d : (e as Error)?.message || '未知錯誤'
}

function candidateLabel(c: CpBackfillCandidate): string {
  const short = c.short_name ? `（簡稱：${c.short_name}）` : ''
  return `${c.ragic_code ? c.ragic_code + ' ' : ''}${c.name}${short}`
}

export default function VendorBackfillTab({ onApplied }: { onApplied?: () => void }) {
  const [syncing, setSyncing] = useState(false)
  const [applying, setApplying] = useState(false)
  const [preview, setPreview] = useState<CpBackfillPreview | null>(null)
  const [choice, setChoice] = useState<Record<number, string | undefined>>({})
  const [selected, setSelected] = useState<number[]>([])
  const [filter, setFilter] = useState<Filter>('all')
  const [lastResult, setLastResult] = useState<CpBackfillApplyResult | null>(null)

  const runSync = async () => {
    setSyncing(true)
    try {
      const { data } = await syncVendorBackfill()
      setPreview(data)
      const init: Record<number, string | undefined> = {}
      const sel: number[] = []
      data.rows.forEach((r) => {
        if (r.suggested_ragic_id) {
          init[r.vendor_id] = r.suggested_ragic_id
          sel.push(r.vendor_id)
        }
      })
      setChoice(init)
      setSelected(sel)
      message.success(`同步完成：待處理 ${data.summary.orphan_count} 家供應商`)
    } catch (e) {
      message.error(`同步失敗：${errDetail(e)}`)
    } finally {
      setSyncing(false)
    }
  }

  const chosenCandidate = (r: CpBackfillRow): CpBackfillCandidate | undefined =>
    r.candidates.find((c) => c.ragic_id === choice[r.vendor_id])

  const rows = useMemo(
    () => (preview?.rows || []).filter((r) => filter === 'all' || r.match_type === filter),
    [preview, filter],
  )

  const readyToApply = useMemo(
    () => (preview?.rows || []).filter((r) => selected.includes(r.vendor_id) && chosenCandidate(r)?.selectable),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [preview, selected, choice],
  )

  const onPick = (r: CpBackfillRow, ragicId: string | undefined) => {
    setChoice((prev) => ({ ...prev, [r.vendor_id]: ragicId }))
    const c = r.candidates.find((x) => x.ragic_id === ragicId)
    setSelected((prev) => {
      const rest = prev.filter((id) => id !== r.vendor_id)
      return c?.selectable ? [...rest, r.vendor_id] : rest
    })
  }

  const runApply = async () => {
    const decisions = readyToApply.map((r) => ({ vendor_id: r.vendor_id, ragic_id: choice[r.vendor_id] as string }))
    if (!decisions.length) return
    setApplying(true)
    try {
      const { data } = await applyVendorBackfill(decisions)
      setLastResult(data)
      message.success(`已回填：料號 ${data.items_updated} 筆、料號對照 ${data.mappings_updated} 筆、未拋轉彙整列 ${data.summaries_updated} 筆`)
      // 已套用的列不再是孤兒引用，直接從預覽移除（要看最新全貌再按一次同步）
      const done = new Set(data.results.map((x) => x.vendor_id))
      setPreview((p) => (p ? { ...p, rows: p.rows.filter((r) => !done.has(r.vendor_id)) } : p))
      setSelected((prev) => prev.filter((id) => !done.has(id)))
      onApplied?.()
    } catch (e) {
      message.error(`套用失敗（全部未寫入）：${errDetail(e)}`)
    } finally {
      setApplying(false)
    }
  }

  const s = preview?.summary

  return (
    <Card>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 12 }}
        message="以 Ragic 廠商資料表的「簡稱」比對，把料號的預設供應商與料號對照的叫貨供應商改指向正確的全名廠商"
        description={
          <div>
            ① 簡稱相同 → 預設勾選　② 無相同簡稱、名稱相似 → 請自行選定　③ Ragic 找不到 → 請先到 Ragic 建檔後再同步。
            <br />
            按「同步」只會更新廠商主檔並產生預覽，<Text strong>按「套用」才會修改料號</Text>；
            尚未拋轉 Ragic 的彙整列也會一併更新；已拋轉或已轉採購單的不受影響，原本的簡稱供應商也不會停用。
          </div>
        }
      />

      <Space wrap style={{ marginBottom: 12 }}>
        <Button type="primary" icon={<SyncOutlined />} loading={syncing} onClick={runSync}>
          同步 Ragic 廠商資料
        </Button>
        <Popconfirm
          title={`確定回填 ${readyToApply.length} 家供應商？`}
          description={`將改動料號 ${readyToApply.reduce((a, r) => a + r.item_count, 0)} 筆、料號對照 ${readyToApply.reduce((a, r) => a + r.mapping_count, 0)} 筆、未拋轉彙整列 ${readyToApply.reduce((a, r) => a + r.summary_count, 0)} 筆`}
          onConfirm={runApply}
          disabled={!readyToApply.length}
        >
          <Button icon={<CheckOutlined />} loading={applying} disabled={!readyToApply.length}>
            套用勾選（{readyToApply.length}）
          </Button>
        </Popconfirm>
        {preview && (
          <Segmented<Filter>
            value={filter}
            onChange={setFilter}
            options={[
              { label: `全部 ${s?.orphan_count ?? 0}`, value: 'all' },
              { label: `簡稱相同 ${s?.short_count ?? 0}`, value: 'short' },
              { label: `名稱相似 ${s?.similar_count ?? 0}`, value: 'similar' },
              { label: `Ragic 找不到 ${s?.none_count ?? 0}`, value: 'none' },
            ]}
          />
        )}
      </Space>

      {preview && (
        <div style={{ marginBottom: 12 }}>
          <Space wrap size={[8, 4]}>
            {preview.sync_steps.map((st) => (
              <Tag key={st.name} color={st.ok ? 'green' : 'red'}>{st.name}：{st.message}</Tag>
            ))}
            <Tag>Ragic 廠商 {s?.ragic_vendor_count} 家（有簡稱 {s?.ragic_short_name_count} 家）</Tag>
            {!!s?.items_without_vendor && (
              <Tag color="orange">另有 {s.items_without_vendor} 筆料號沒有預設供應商（不在本功能範圍）</Tag>
            )}
          </Space>
        </div>
      )}

      {lastResult && (
        <Alert
          type="success"
          showIcon
          closable
          onClose={() => setLastResult(null)}
          style={{ marginBottom: 12 }}
          message={`上次套用：料號 ${lastResult.items_updated} 筆、料號對照 ${lastResult.mappings_updated} 筆、未拋轉彙整列 ${lastResult.summaries_updated} 筆`}
          description={lastResult.results
            .map((x) => `${x.vendor_name} → ${x.target_vendor_name}（料號 ${x.items_updated}／對照 ${x.mappings_updated}／彙整 ${x.summaries_updated}）`)
            .join('；')}
        />
      )}

      {!preview ? (
        <Empty description="按「同步 Ragic 廠商資料」開始比對" />
      ) : (
        <Table<CpBackfillRow>
          rowKey="vendor_id"
          size="small"
          dataSource={rows}
          pagination={false}
          rowSelection={{
            selectedRowKeys: selected,
            onChange: (keys) => setSelected(keys as number[]),
            getCheckboxProps: (r) => ({ disabled: !chosenCandidate(r)?.selectable }),
          }}
          columns={[
            {
              title: '週採供應商（目前）',
              key: 'vendor',
              width: 200,
              render: (_, r) => (
                <div>
                  <Text strong>{r.vendor_name}</Text>
                  <div><Text type="secondary" style={{ fontSize: 12 }}>{r.vendor_code}{r.is_active ? '' : '（停用）'}</Text></div>
                </div>
              ),
            },
            { title: '料號', dataIndex: 'item_count', width: 70, align: 'right' },
            { title: '料號對照', dataIndex: 'mapping_count', width: 90, align: 'right' },
            {
              title: <Tooltip title="尚未拋轉 Ragic、尚未轉採購單的彙整列">未拋轉彙整列</Tooltip>,
              dataIndex: 'summary_count',
              width: 110,
              align: 'right',
            },
            {
              title: '比對結果',
              key: 'match',
              width: 150,
              render: (_, r) => (
                <Tooltip title={MATCH_TAG[r.match_type].tip}>
                  <Tag color={MATCH_TAG[r.match_type].color}>{MATCH_TAG[r.match_type].label}</Tag>
                </Tooltip>
              ),
            },
            {
              title: '對應 Ragic 廠商',
              key: 'ragic',
              render: (_, r) => {
                if (r.match_type === 'none') return <Text type="secondary">—（請先到 Ragic 建檔）</Text>
                const c = chosenCandidate(r)
                return (
                  <Space direction="vertical" size={2} style={{ width: '100%' }}>
                    <Space>
                      <Select
                        style={{ minWidth: 340 }}
                        placeholder="請選擇 Ragic 廠商"
                        allowClear
                        value={choice[r.vendor_id]}
                        onChange={(v) => onPick(r, v)}
                        options={r.candidates.map((cd) => ({
                          value: cd.ragic_id,
                          disabled: !cd.selectable,
                          label: `${candidateLabel(cd)}${r.match_type === 'similar' ? `　相似度 ${Math.round(cd.score * 100)}%` : ''}`,
                        }))}
                      />
                      {c && (
                        <a href={c.ragic_url} target="_blank" rel="noreferrer" style={{ color: '#4BA8E8' }}>
                          <LinkOutlined /> Ragic
                        </a>
                      )}
                    </Space>
                    {c && !c.selectable && <Text type="danger" style={{ fontSize: 12 }}>{c.block_reason}</Text>}
                  </Space>
                )
              },
            },
            {
              title: '套用後改為',
              key: 'target',
              width: 240,
              render: (_, r) => {
                const c = chosenCandidate(r)
                if (!c?.target_vendor_name) return <Text type="secondary">—</Text>
                return (
                  <div>
                    <Text>{c.target_vendor_name}</Text>
                    <div><Text type="secondary" style={{ fontSize: 12 }}>{c.target_vendor_code}</Text></div>
                  </div>
                )
              },
            },
          ]}
        />
      )}
    </Card>
  )
}
