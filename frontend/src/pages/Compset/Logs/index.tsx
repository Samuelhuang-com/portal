/**
 * 競品分析 — 抓取紀錄
 * Route: /compset/logs    Permission: compset_view
 *
 * 規格書：`docs/SPEC_compset_analysis.md` §9.7、§6.3
 *
 * 【這一頁在回答的問題】
 *   「昨天到底有沒有抓？抓了幾次？花了多少配額？為什麼某一天沒資料？」
 *
 * ⚠️ **警告（黃）與錯誤（紅）分開顯示，不可混在一起**（SPEC §6.3）。
 *    「某一家在地點查詢的前 N 名裡沒出現」是警告 —— 這是已知限制，不用修。
 *    「HTTP 401」是錯誤 —— 要人去處理。混成同一色，真正該修的會被淹沒。
 *
 * ⚠️ `skipped` 不是失敗。B 級每 3 天抓一次，其餘兩天本來就是 skipped；
 *    畫成紅色會讓人以為天天都在壞。同理 `quota_exceeded` 是**設定問題**
 *    （額度用完）不是程式錯誤，但它會讓資料真的斷掉，所以用紅色。
 *
 * ⚠️ `params` 裡**沒有 API key**（後端 `build_params()` 刻意不放）。
 *    這張表會展開整包參數給人看，key 要是混進來就等於印在畫面上。
 */
import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert, Card, Empty, Select, Space, Table, Tag, Tooltip, Typography,
  message,
} from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

import { fetchLogs } from '@/api/compset'
import type { FetchLogRow, FetchStatus } from '@/types/compset'
import { TierTag } from '../components'

const { Text, Paragraph } = Typography

const STATUS_META: Record<FetchStatus, { color: string; label: string; tip: string }> = {
  success:        { color: 'success',    label: '成功',      tip: '整批都拿到了' },
  partial:        { color: 'warning',    label: '部分成功',  tip: '有些家沒抓到（多半是地點查詢前 N 名沒出現），已寫入的部分有效' },
  failed:         { color: 'error',      label: '失敗',      tip: '這一批沒有任何資料寫入，需要處理' },
  quota_exceeded: { color: 'error',      label: '配額用盡',  tip: '硬停。不是程式錯誤，但資料會真的斷掉 —— 要手動加發才會恢復' },
  // ⚠️ 灰色不是紅色：「今天不該跑」是排程事實，不是壞掉
  skipped:        { color: 'default',    label: '未到期',    tip: '依頻率設定今天不跑（例如 B 級每 3 天一次），或該級別未開通。正常狀態。' },
  running:        { color: 'processing', label: '進行中',    tip: '正在跑' },
}

const CompsetLogsPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [rows, setRows] = useState<FetchLogRow[]>([])
  const [limit, setLimit] = useState(50)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchLogs(limit)
      setRows(data.items ?? [])
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [limit])

  useEffect(() => { load() }, [load])

  const failedCount = rows.filter(
    (r) => r.status === 'failed' || r.status === 'quota_exceeded').length

  const columns: ColumnsType<FetchLogRow> = [
    {
      title: '開始時間', dataIndex: 'started_at', width: 160, fixed: 'left',
      render: (v: string | null) => v || '—',
    },
    {
      title: '級別', dataIndex: 'tier', width: 90,
      render: (v: string) => <TierTag tier={v} />,
    },
    {
      title: '路徑', dataIndex: 'fetch_path', width: 110,
      render: (v: string) => (v === 'token'
        ? <Tooltip title="逐家查詢：每家一次 API，判得出滿房"><Tag color="blue">逐家</Tag></Tooltip>
        : v === 'location'
          ? <Tooltip title="地點查詢：一次拿回一整批，便宜但判不出滿房、也可能漏家"><Tag>地點</Tag></Tooltip>
          : <Text type="secondary">—</Text>),
    },
    {
      title: '狀態', dataIndex: 'status', width: 120,
      render: (v: FetchStatus) => {
        const m = STATUS_META[v] ?? { color: 'default', label: v, tip: '' }
        return <Tooltip title={m.tip}><Tag color={m.color}>{m.label}</Tag></Tooltip>
      },
    },
    {
      title: '入住日區間', width: 200,
      render: (_, r) => (r.stay_date_from
        ? <Text style={{ fontSize: 12 }}>{r.stay_date_from} 〜 {r.stay_date_to}</Text>
        : <Text type="secondary">—</Text>),
    },
    { title: '查詢次數', dataIndex: 'request_count', width: 90, align: 'right' },
    { title: '寫入筆數', dataIndex: 'row_count', width: 90, align: 'right' },
    {
      title: '配額', width: 130, align: 'right',
      render: (_, r) => (r.quota_before === null
        ? <Text type="secondary">—</Text>
        : <Tooltip title="這一批跑之前 → 跑之後的已用次數">
            <Text style={{ fontSize: 12 }}>{r.quota_before} → {r.quota_after}</Text>
          </Tooltip>),
    },
    {
      title: '訊息',
      render: (_, r) => (
        <Space direction="vertical" size={2}>
          {/* ⚠️ 黃色警告：已知限制，不用修 */}
          {r.warnings.map((w, i) => (
            <Text key={i} type="warning" style={{ fontSize: 12 }}>{w}</Text>
          ))}
          {/* ⚠️ 紅色錯誤：要人處理 */}
          {r.error_message && (
            <Text type="danger" style={{ fontSize: 12 }}>{r.error_message}</Text>
          )}
          {r.warnings.length === 0 && !r.error_message && (
            <Text type="secondary" style={{ fontSize: 12 }}>—</Text>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Space direction="vertical" size={0}>
          <Typography.Title level={4} style={{ margin: 0 }}>抓取紀錄</Typography.Title>
          <Text type="secondary">排程每天 04:10 跑一次；手動觸發也會記在這裡</Text>
        </Space>
        <Space>
          <Text type="secondary">顯示筆數</Text>
          {/* ⚠️ 用 Select 不用 InputNumber：InputNumber 每按一個鍵就觸發 onChange，
              打「1000」會依序送出 limit=1／10／100／1000 四次請求，
              而後端是 `Query(50, le=500)` —— 最後那次回 422，
              使用者只看到一個「載入失敗」，卻不知道自己打的數字超出上限
              （InputNumber 的 max 要 blur 才夾，來不及）。 */}
          <Select value={limit} onChange={setLimit} style={{ width: 110 }}
            options={[50, 100, 200, 500].map((n) => ({ value: n, label: `${n} 筆` }))} />
          <a onClick={load}><ReloadOutlined /> 重新整理</a>
        </Space>
      </Space>

      {failedCount > 0 && (
        <Alert type="error" showIcon style={{ marginBottom: 16 }}
          message={`最近 ${rows.length} 批裡有 ${failedCount} 批失敗或配額用盡`}
          description="失敗的批次不會自動重跑 —— 那一天的那一段就是沒有資料。
            配額用盡要到「訂閱與配額」手動加發才會恢復。" />
      )}

      <Card>
        <Table<FetchLogRow>
          rowKey="id" size="small" loading={loading} columns={columns}
          dataSource={rows} pagination={false} scroll={{ x: 1200 }}
          expandable={{
            // 展開看這一批用了什麼參數。查「為什麼價格突然變了」時很有用：
            // 多半是 adults／nights／currency 被改過（＝資料斷點）。
            expandedRowRender: (r) => (
              <div style={{ paddingLeft: 24 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>擷取參數：</Text>
                <pre style={{ margin: '4px 0 0', fontSize: 12, background: '#fafafa',
                  padding: 8, borderRadius: 4, overflow: 'auto' }}>
                  {r.params ? JSON.stringify(r.params, null, 2) : '（無）'}
                </pre>
              </div>
            ),
            rowExpandable: (r) => !!r.params,
          }}
          locale={{ emptyText: <Empty description="還沒有任何抓取紀錄" /> }} />
        <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}>
          <b>「未到期」是正常的</b>：B 級每 3 天、C 級每週各跑一次，其餘日子本來就會 skip。
          <b>黃色</b>是已知限制（例如某家在地點查詢的前 N 名沒出現），不用處理；
          <b>紅色</b>才需要有人去看。
        </Paragraph>
      </Card>
    </div>
  )
}

export default CompsetLogsPage
