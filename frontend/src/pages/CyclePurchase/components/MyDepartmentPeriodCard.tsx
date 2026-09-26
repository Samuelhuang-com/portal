/**
 * 「我的部門本期」卡片（2026-09-25 Samuel 裁示）
 *
 * 週採是各部門自己填、自己關，買家再彙整。部門人員進來真正想知道的只有：
 * 「這個月我部門有哪幾張單、輪到我做什麼」。這張卡依登入者所屬部門
 * （部門成員 OR 承辦人，見後端 get_user_cp_department_ids）列出本月各啟用中
 * 週期的單，最後一欄白話告訴他「輪到你」還是「不用你動」。
 *
 * 資料：GET /requests/my-period。只列「該部門適用此週期」或「本期已有單」的
 * 組合，無關的週期不列。
 *
 * 放兩個地方：週採 Dashboard，以及請購單清單的「我的部門」模式——後者是因為
 * 只有填單權限（cycle_purchase_request）的部門人員，左側選單看不到 Dashboard。
 *
 * hideWhenNoDepartment：Dashboard 上的使用者多半是買家／管理者，本來就不屬於
 * 任何部門，沒有部門時整張卡不顯示；請購單頁的「我的部門」模式則要明講
 * 「你沒有被指派到任何週採部門」，不然使用者只會看到一片空白。
 */
import React, { useEffect, useMemo, useState } from 'react'
import { Alert, Card, Select, Table, Tag, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import { getMyPeriod } from '@/api/cyclePurchase'
import type { CpMyPeriodResult, CpMyPeriodRow } from '@/types/cyclePurchase'

const { Text } = Typography

type Tone = 'todo' | 'doing' | 'wait' | 'done' | 'none'

const TONE_COLOR: Record<Tone, string> = {
  todo: '#c9791f',  // 輪到你、還沒開始
  doing: '#2c7fbd', // 輪到你、進行中
  wait: '#6b7280',  // 不用你動，等別人
  done: '#2f8a5c',  // 完成
  none: '#9aa2b1',  // 本期沒有單
}

function nextAction(r: CpMyPeriodRow): { text: string; tone: Tone } {
  if (!r.request_id) {
    return { text: '本期還沒有你部門的單，請通知採購產生本期請購單', tone: 'none' }
  }
  if (r.is_summarized) {
    return { text: '已彙整，後續由採購處理，你這邊不用做事', tone: 'done' }
  }
  if (r.is_closed) {
    return { text: '已關閉，等採購彙整，你這邊不用做事', tone: 'wait' }
  }
  if (r.filled_item_count === 0) {
    return { text: '輪到你：還沒填任何品項，請進去填寫', tone: 'todo' }
  }
  return { text: `輪到你：已填 ${r.filled_item_count} 項，填完請關閉（送出）`, tone: 'doing' }
}

function statusTag(r: CpMyPeriodRow) {
  if (!r.request_id) return <Tag>本期無單</Tag>
  if (r.is_summarized) return <Tag color="cyan">已彙整</Tag>
  if (r.is_closed) return <Tag>{r.close_kind === 'auto' ? '關閉（系統）' : '已關閉'}</Tag>
  return <Tag color="blue">開放中</Tag>
}

interface Props {
  hideWhenNoDepartment?: boolean
  style?: React.CSSProperties
}

const MyDepartmentPeriodCard: React.FC<Props> = ({ hideWhenNoDepartment = false, style }) => {
  const navigate = useNavigate()
  const [data, setData] = useState<CpMyPeriodResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [deptFilter, setDeptFilter] = useState<number | undefined>(undefined)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getMyPeriod()
      .then((res) => { if (!cancelled) { setData(res.data); setFailed(false) } })
      .catch(() => { if (!cancelled) setFailed(true) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  const rows = useMemo(
    () => (data?.rows ?? []).filter((r) => deptFilter === undefined || r.department_id === deptFilter),
    [data, deptFilter],
  )

  // 2026-09-25（Samuel 裁示）：卡片一律顯示、0 筆也顯示表格，不再整張藏起來——
  // 原本 Dashboard 上沒有部門的人（含管理者）看到的是一個空標題「我的部門本期（）」。
  // 管理者（system_admin）由後端直接回全部啟用中部門（scope='all'）。
  if (failed) {
    return (
      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 16, ...style }}
        message="無法取得「部門本期」資料"
        description="若剛更新程式，請確認後端已經重啟（這是新增的查詢）。"
      />
    )
  }
  void hideWhenNoDepartment

  const isAll = data?.scope === 'all'
  const noDept = !loading && !!data && data.departments.length === 0
  const multiDept = (data?.departments.length ?? 0) > 1
  const deptLabel = (data?.departments ?? []).map((d) => `${d.company} ${d.name}`).join('、')
  const period = data?.period_label || `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`

  return (
    <Card
      size="small"
      loading={loading}
      style={{ marginBottom: 16, ...style }}
      title={
        <span>
          {isAll ? '全部門本期' : '我的部門本期'}（{period}）
          {isAll && (
            <Text type="secondary" style={{ fontWeight: 400, marginLeft: 8, fontSize: 13 }}>
              管理者檢視・共 {data?.departments.length ?? 0} 個部門
            </Text>
          )}
          {!isAll && !multiDept && deptLabel && (
            <Text type="secondary" style={{ fontWeight: 400, marginLeft: 8, fontSize: 13 }}>{deptLabel}</Text>
          )}
        </span>
      }
      extra={
        multiDept ? (
          <Select
            size="small"
            style={{ width: 220 }}
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder={isAll ? '全部部門' : '全部我的部門'}
            value={deptFilter}
            onChange={setDeptFilter}
            options={(data?.departments ?? []).map((d) => ({ label: `${d.company} ${d.name}`, value: d.id }))}
          />
        ) : null
      }
    >
      <Table
        size="small"
        pagination={false}
        dataSource={rows}
        rowKey={(r) => `${r.cycle_id}-${r.department_id}-${r.request_id ?? 'none'}`}
        locale={{
          emptyText: noDept
            ? (isAll
              ? '目前沒有任何啟用中的週採部門'
              : '你目前沒有被指派到任何週採部門，請聯絡管理員把你加入所屬部門')
            : (isAll ? '本月沒有任何週期適用這些部門' : '本月沒有任何週期適用你的部門'),
        }}
        columns={[
          { title: '週期', dataIndex: 'cycle_name', width: 160 },
          ...(multiDept
            ? [{ title: '部門', key: 'dept', width: 150, render: (_: unknown, r: CpMyPeriodRow) => `${r.company} ${r.department_name}` }]
            : []),
          {
            title: '我的單',
            key: 'request_no',
            width: 150,
            render: (_: unknown, r: CpMyPeriodRow) => {
              if (!r.request_id) return <Text type="secondary">—</Text>
              // 已關閉的單，沒有權限的人點進去會 403，就不給連結
              const canOpen = !r.is_closed || data?.can_open_closed
              return canOpen
                ? <a onClick={() => navigate(`/cycle-purchase/requests/${r.request_id}`)}>{r.request_no}</a>
                : <span>{r.request_no}</span>
            },
          },
          { title: '狀態', key: 'status', width: 110, render: (_: unknown, r: CpMyPeriodRow) => statusTag(r) },
          {
            title: '下一步',
            key: 'next',
            render: (_: unknown, r: CpMyPeriodRow) => {
              const n = nextAction(r)
              return (
                <span style={{ color: TONE_COLOR[n.tone], fontWeight: n.tone === 'todo' || n.tone === 'doing' ? 600 : 400 }}>
                  {n.text}
                </span>
              )
            },
          },
        ]}
      />
    </Card>
  )
}

export default MyDepartmentPeriodCard
