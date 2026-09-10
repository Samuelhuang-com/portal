/**
 * 競品分析 — 價格矩陣
 * Route: /compset/matrix    Permission: compset_matrix_view
 *
 * 規格書：`docs/SPEC_compset_analysis.md` §9.2
 *
 * 【這一頁在回答的問題】
 *   在某一批快照裡，每一家 × 每一個入住日的價格排開來，哪幾天我明顯偏離。
 *
 * ── 版面是「轉置」的 ──────────────────────────────────────────────────────
 * 後端回的是「橫軸入住日、縱軸飯店」，但畫面做成**一列一個入住日**。
 * 理由：入住日有 120 天（C 級），飯店只有 6 家。把 120 個東西放在橫軸上
 * 一定要橫捲，使用者永遠看不到全貌；放縱軸則是自然的往下捲。
 *
 * ⚠️ 這一頁**刻意不用 `StandardRangePicker`**：它的六個快捷全是過去區間
 *    （本月／上月／最近 30 天／今年／去年），而競品分析看的是**還沒住的未來**。
 *    該元件註解第 3 條「未來導向的選擇」明列不適用。這裡改用單純的 RangePicker
 *    加上三個未來向快捷（A／B／C 級對應的窗格）。
 *
 * ⚠️ 空格不等於「沒抓到」。B／C 級是地點查詢，前 N 名裡沒出現的家就是沒有資料，
 *    這是設計上的已知限制（SPEC §6.5），畫面要說清楚，不要讓人以為系統壞了。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col, DatePicker, Descriptions, Drawer, Empty, Row,
  Space, Spin, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import { QuestionCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import { useSearchParams } from 'react-router-dom'

import { fetchMatrix, fetchRateDetail } from '@/api/compset'
import type {
  MatrixResult, PriceBasis, RateCell, RateDetail,
} from '@/types/compset'
import {
  BasisSwitch, IndexValue, RankValue, SnapshotStamp, SoldOutTag, StayDateLabel,
  TaxTag, TierTag, fmtMoney, priceOf,
} from '../components'

const { Text, Paragraph } = Typography
const { RangePicker } = DatePicker

/** 一列 ＝ 一個入住日。飯店價格攤平成 `h_<id>` 欄位。 */
interface MatrixRow {
  stay_date: string
  [key: string]: unknown
}

/**
 * 未來向快捷。
 * ⚠️ 與抓取分級對齊（A ＝ D+1〜14、B ＝ D+15〜45、C ＝ D+46〜120）。
 *    選了沒開通的級別會查到空資料 —— 這不是 bug，是那一級沒訂閱。
 */
const PRESETS: { label: string; value: () => [Dayjs, Dayjs] }[] = [
  { label: 'A 級（未來 14 天）', value: () => [dayjs().add(1, 'day'), dayjs().add(14, 'day')] },
  { label: 'B 級（15〜45 天）', value: () => [dayjs().add(15, 'day'), dayjs().add(45, 'day')] },
  { label: 'C 級（46〜120 天）', value: () => [dayjs().add(46, 'day'), dayjs().add(120, 'day')] },
]

const CompsetMatrixPage: React.FC = () => {
  const [params] = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<MatrixResult | null>(null)
  const [basis, setBasis] = useState<PriceBasis>('pretax')
  /**
   * ⚠️ URL 參數要在 **useState 初始值**裡吃掉，不能放進 `useEffect`。
   *    放 effect 的話，首次 render 後兩個 effect 依序執行：
   *    第一個 `setRange(URL 區間)`（排隊中），第二個 `load()` 已經抓住了
   *    **預設區間**的閉包並送出請求 —— 白打一次 API，畫面還會閃一下錯的 14 天。
   *    （`Trend` 頁一開始就是這樣寫的，這裡對齊它。）
   */
  const [range, setRange] = useState<[Dayjs, Dayjs]>(() => {
    const from = params.get('stay_from')
    const to = params.get('stay_to')
    if (from && to && dayjs(from).isValid() && dayjs(to).isValid()) {
      return [dayjs(from), dayjs(to)]
    }
    return [dayjs().add(1, 'day'), dayjs().add(14, 'day')]
  })
  const [snapshotDate, setSnapshotDate] = useState<Dayjs | null>(null)

  const [detail, setDetail] = useState<RateDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setData(await fetchMatrix({
        stayFrom: range[0].format('YYYY-MM-DD'),
        stayTo: range[1].format('YYYY-MM-DD'),
        snapshotDate: snapshotDate ? snapshotDate.format('YYYY-MM-DD') : undefined,
      }))
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [range, snapshotDate])

  useEffect(() => { load() }, [load])

  const openDetail = useCallback(async (snapshotId: number) => {
    setDetailLoading(true)
    try {
      setDetail(await fetchRateDetail(snapshotId))
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入明細失敗')
    } finally {
      setDetailLoading(false)
    }
  }, [])

  const rows = useMemo<MatrixRow[]>(
    () => (data?.stay_dates ?? []).map((d) => ({ stay_date: d })),
    [data],
  )

  const columns = useMemo<ColumnsType<MatrixRow>>(() => {
    if (!data) return []
    const hotelCols: ColumnsType<MatrixRow> = data.hotels.map((h) => ({
      // ⚠️ 標題用簡稱：中文全名 8～12 字塞不進 130px 的欄位，會擠成兩三行。
      //    全名與房數放 tooltip。
      title: (
        <Tooltip title={
          <div>{h.name}{h.room_count ? `（${h.room_count} 間房）` : ''}</div>
        }>
          <span style={{ fontWeight: h.is_self ? 700 : 400 }}>
            {h.is_self && <Tag color="blue" style={{ marginRight: 4 }}>自己</Tag>}
            {h.short_name}
          </span>
        </Tooltip>
      ),
      key: `h_${h.id}`,
      width: 130,
      align: 'right',
      onCell: () => ({ style: h.is_self ? { background: '#f0f7ff' } : undefined }),
      render: (_: unknown, row: MatrixRow) => {
        const cell = data.cells[`${row.stay_date}|${h.id}`] as RateCell | undefined
        if (!cell) {
          return (
            <Tooltip title="這一批快照沒有這家的資料。B／C 級走地點查詢，前 N 名沒出現就沒有 —— 這是已知限制，不是系統故障。">
              <Text type="secondary">—</Text>
            </Tooltip>
          )
        }
        if (cell.is_sold_out === 'yes') {
          return <Tooltip title="該日查無任何報價"><Tag color="red">滿房</Tag></Tooltip>
        }
        const p = priceOf(cell, basis)
        if (p === null) {
          return <Tooltip title={`只有${basis === 'pretax' ? '含稅' : '稅前'}價，這個口徑沒有`}>
            <Text type="secondary">—</Text>
          </Tooltip>
        }
        // ⚠️ 這格的數字**不是**任何一個通路的牌價，是 Google 的 `rate_per_night`
        //    頭條最低價。使用者拿它去對 Google 頁面上的「官網」那一列一定對不上，
        //    所以來源要寫在 tooltip 上，不要逼人來問。
        return (
          <Tooltip title={
            <div style={{ maxWidth: 300 }}>
              <div><b>{basis === 'pretax' ? '稅前價' : '含稅價'}</b>
                {' '}{fmtMoney(p)}</div>
              <div style={{ marginTop: 4 }}>
                這是 Google 當時的<b>最低可訂價</b>（跨所有通路），
                不是官網價、也不是某一家 OTA 的價。
              </div>
              <div style={{ marginTop: 4 }}>
                提供者：{cell.ota_name || '未能判定（有兩家以上同價）'}
                {cell.is_official && '（官網）'}
              </div>
              <div>
                入住人數：{cell.num_guests ?? '未標示'}
                {cell.num_guests != null && cell.num_guests !== 2 && (
                  <b style={{ color: '#faad14' }}>　⚠️ 與查詢的 2 人不同</b>
                )}
              </div>
              <div>抓取批次：{data.fetched_at || data.snapshot_date}　
                {cell.fetch_path === 'token' ? '逐家查詢' : '地點查詢'}</div>
              <div style={{ marginTop: 4 }}>點一下看各通路報價明細。</div>
            </div>
          }>
            <a onClick={() => openDetail(cell.snapshot_id)}>
              {fmtMoney(p)}
              {cell.is_official && (
                <Tag color="green"
                  style={{ marginLeft: 4, transform: 'scale(0.85)' }}>官</Tag>
              )}
            </a>
          </Tooltip>
        )
      },
    }))

    return [
      {
        // 與 Dashboard 共用 `StayDateLabel` —— 旺日判定與星期格式只能有一份
        title: '入住日', dataIndex: 'stay_date', key: 'stay_date',
        width: 150, fixed: 'left',
        render: (v: string) => <StayDateLabel date={v} />,
      },
      ...hotelCols,
      {
        title: (
          <Tooltip title="自己 ÷ 競品中位數。n ＝ 進中位數的競品家數，一定要一起看。">
            指數 <QuestionCircleOutlined style={{ color: '#999' }} />
          </Tooltip>
        ),
        key: 'index', width: 120, align: 'center', fixed: 'right',
        render: (_: unknown, row: MatrixRow) =>
          <IndexValue stat={data.daily[row.stay_date]} basis={basis} compact />,
      },
      {
        title: '名次', key: 'rank', width: 80, align: 'center', fixed: 'right',
        render: (_: unknown, row: MatrixRow) =>
          <RankValue stat={data.daily[row.stay_date]} />,
      },
    ]
  }, [data, basis, openDetail])

  return (
    <div style={{ padding: 24 }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Typography.Title level={4} style={{ margin: 0 }}>價格矩陣</Typography.Title>
          <SnapshotStamp snapshotDate={data?.snapshot_date}
            fetchedAt={data?.fetched_at} />
        </Col>
        <Col>
          <Space wrap>
            <BasisSwitch value={basis} onChange={setBasis} />
            <Tooltip title="留空 ＝ 最新一批。指定某一天可以回看當時的報價。">
              <DatePicker value={snapshotDate} onChange={setSnapshotDate}
                placeholder="快照日（留空 ＝ 最新）" allowClear />
            </Tooltip>
            <RangePicker
              value={range} allowClear={false}
              onChange={(v) => v && v[0] && v[1] && setRange([v[0], v[1]])}
              presets={PRESETS.map((p) => ({ label: p.label, value: p.value() }))} />
            <Button icon={<ReloadOutlined />} onClick={load}>重新整理</Button>
          </Space>
        </Col>
      </Row>

      {(data?.warnings ?? []).length > 0 && (
        <Alert type="warning" showIcon style={{ marginBottom: 16 }}
          message="資料品質提醒"
          description={<ul style={{ margin: 0, paddingLeft: 18 }}>
            {data!.warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>} />
      )}

      <Card>
        <Spin spinning={loading}>
          <Table<MatrixRow>
            rowKey="stay_date" size="small" columns={columns} dataSource={rows}
            pagination={false} scroll={{ x: 'max-content', y: 560 }}
            locale={{
              emptyText: <Empty description="這個區間沒有資料。可能是該級別尚未開通，或還沒跑過抓取。" />,
            }} />
        </Spin>
        <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}>
          <b>格子裡的數字是 Google 當時的「最低可訂價」，不是官網價</b> ——
          拿去對 Google 頁面上的官網那一列會對不上，要對就對<b>最便宜的那一列</b>。
          而且預設是<b>稅前價</b>，Google 畫面預設是「每晚總價」（含稅），
          先把右上角切到「含稅價」再比。
          「—」＝ 這一批快照沒有該家的報價（B／C 級走地點查詢，前 N 名沒出現就沒有）。
          「滿房」只有 A 級判得出來，B／C 級一律當作有房但狀態未知。
          點價格可以看單筆明細與各通路報價。
        </Paragraph>
      </Card>

      {/* ── 明細 Drawer（CLAUDE.md §7）───────────────────────────────── */}
      <Drawer title="報價明細" width={560} open={!!detail}
        onClose={() => setDetail(null)} destroyOnClose>
        <Spin spinning={detailLoading}>
          {detail && (
            <>
              <Descriptions column={1} size="small" bordered>
                <Descriptions.Item label="飯店">
                  {detail.hotel.is_self && <Tag color="blue">自己</Tag>}
                  {detail.hotel.name}
                  {detail.hotel.room_count ? `（${detail.hotel.room_count} 間房）` : ''}
                </Descriptions.Item>
                <Descriptions.Item label="入住日">{detail.stay_date}</Descriptions.Item>
                <Descriptions.Item label="快照日">{detail.snapshot_date}</Descriptions.Item>
                <Descriptions.Item label="抓取級別">
                  <Space><TierTag tier={detail.tier} />
                    <Text type="secondary">{detail.fetch_path === 'token' ? '逐家查詢' : '地點查詢'}</Text>
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="含稅價">{fmtMoney(detail.price_gross)}</Descriptions.Item>
                <Descriptions.Item label="稅前價">{fmtMoney(detail.price_pretax)}</Descriptions.Item>
                <Descriptions.Item label="口徑">
                  <Space><TaxTag value={detail.tax_included} />
                    <SoldOutTag value={detail.is_sold_out} /></Space>
                </Descriptions.Item>
                <Descriptions.Item label="通路">
                  {detail.ota_name || '—'}
                  {detail.is_official && <Tag color="green" style={{ marginLeft: 6 }}>官網</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="房型">{detail.room_type_raw || '—'}</Descriptions.Item>
                <Descriptions.Item label="入住人數">{detail.num_guests ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="免費取消">
                  {detail.free_cancellation ? '是' : '否'}
                </Descriptions.Item>
                <Descriptions.Item label="來源">{detail.source}</Descriptions.Item>
              </Descriptions>

              <Typography.Title level={5} style={{ marginTop: 24 }}>各通路報價</Typography.Title>
              {/* ⚠️ 這是日後做 rate parity（官網有沒有比 OTA 貴）的原料。
                  P0 實測：官網 $1,900 是 16 個通路裡最便宜，
                  Expedia／Hotels.com 掛 $3,666（1.93 倍）。 */}
              {detail.offers.length === 0
                ? <Empty description="沒有通路明細（地點查詢路徑不回這個）" />
                : (
                  <Table size="small" pagination={false} rowKey={(_, i) => String(i)}
                    dataSource={detail.offers}
                    columns={[
                      { title: '通路', dataIndex: 'source',
                        render: (v: string, r: any) => <Space size={4}>{v}
                          {r.official && <Tag color="green">官網</Tag>}</Space> },
                      { title: '含稅', dataIndex: 'gross', align: 'right',
                        render: (v: number | null) => fmtMoney(v) },
                      { title: '稅前', dataIndex: 'pretax', align: 'right',
                        render: (v: number | null) => fmtMoney(v) },
                      { title: '可退', dataIndex: 'free_cancellation', align: 'center',
                        render: (v: boolean) => (v ? '✓' : '') },
                    ]} />
                )}
            </>
          )}
        </Spin>
      </Drawer>
    </div>
  )
}

export default CompsetMatrixPage
