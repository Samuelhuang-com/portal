/**
 * 競品分析 — 共用小元件
 *
 * 規格書：`docs/SPEC_compset_analysis.md` §7、§9
 *
 * 這裡只放「口徑相關」的元件。放在同一支的理由是：
 * 它們代表的是**同一組規則**（稅前／含稅、樣本數、三態滿房），
 * 拆成七支各自 import 遲早會有人在某一頁自己刻一個不一樣的版本。
 */
import React from 'react'
import { Radio, Space, Tag, Tooltip, Typography } from 'antd'
import dayjs from 'dayjs'
import {
  ExclamationCircleOutlined, QuestionCircleOutlined,
} from '@ant-design/icons'
import type { DailyStat, PriceBasis, SoldOutState, TaxState } from '@/types/compset'

const { Text } = Typography

/** 樣本數低於這個值就標警示。⚠️ 與後端 `compset_stats_service.MIN_SAMPLE` 對應。 */
export const MIN_SAMPLE = 3

// ══════════════════════════════════════════════════════════════════════════
// 口徑切換
// ══════════════════════════════════════════════════════════════════════════
/**
 * 稅前／含稅切換。
 *
 * ⚠️ **預設一律 pretax**（SPEC §5.2）。各家服務費政策不同
 *    （P0 實測 1.155／1.05／1.000 三種都有），含稅價互相比等於在比服務費率，
 *    不是在比房價。含稅價留著是因為「旅客實際看到多少錢」也是真問題。
 */
export const BasisSwitch: React.FC<{
  value: PriceBasis
  onChange: (v: PriceBasis) => void
  size?: 'small' | 'middle' | 'large'
}> = ({ value, onChange, size = 'small' }) => (
  <Space size={4}>
    <Radio.Group
      size={size}
      value={value}
      onChange={(e) => onChange(e.target.value as PriceBasis)}
      optionType="button"
      buttonStyle="solid"
      options={[
        { label: '稅前價', value: 'pretax' },
        { label: '含稅價', value: 'gross' },
      ]}
    />
    <Tooltip title={
      <div style={{ maxWidth: 320 }}>
        <div><b>稅前價</b>（預設）：排除各家不同的服務費／稅金政策，
          比較的是純房價。指數與名次建議都看這個。</div>
        <div style={{ marginTop: 6 }}><b>含稅價</b>：旅客實際付出的金額。
          但各家含稅率不同（實測有 1.155、1.05、1.000 三種），
          數字高不代表房價高。</div>
      </div>
    }>
      <QuestionCircleOutlined style={{ color: '#999' }} />
    </Tooltip>
  </Space>
)

// ══════════════════════════════════════════════════════════════════════════
// 指數
// ══════════════════════════════════════════════════════════════════════════
/**
 * 取出**當前口徑**的樣本數。
 *
 * ⚠️ 兩個口徑的樣本數**會不一樣**，而且差很多。地點查詢的第 2 頁沒有
 *    `before_taxes_fees`，那幾家有含稅價、沒有稅前價 ——
 *    「稅前只有 1 家、含稅有 4 家」是常態不是例外。
 *
 * ⚠️ **不要用 `stat.sample_count`**：那個欄位的語意是「稅前優先，稅前全缺才
 *    退回含稅」，是給 DB 快取欄位與 `is_low_sample` 用的。拿它來標含稅指數，
 *    會把一個 4 家算出來的好指數標成「樣本不足、僅供參考」——
 *    等於叫使用者不要相信一個沒問題的數字。
 *
 * 舊資料沒有這兩個欄位時退回 `sample_count`，不會變成 0。
 */
export function sampleCountOf(stat: DailyStat, basis: PriceBasis): number {
  const n = basis === 'pretax' ? stat.sample_count_pretax : stat.sample_count_gross
  return n ?? stat.sample_count ?? 0
}

/** 當前口徑的樣本數是否不足。⚠️ 同樣不可以用 `stat.is_low_sample`（那是稅前口徑的）。 */
export function isLowSample(stat: DailyStat, basis: PriceBasis): boolean {
  return sampleCountOf(stat, basis) < MIN_SAMPLE
}

/**
 * 價格指數 ＝ 自己 ÷ 競品中位數。
 *
 * ⚠️ **一定要跟樣本數一起顯示**（SPEC §7.3）。
 *    「4 家算出來的 1.05」和「1 家算出來的 1.05」在畫面上長得一模一樣，
 *    但後者根本不能當決策依據。這是本模組最容易誤導人的地方，
 *    所以樣本數不是選配資訊，是指數的一部分。
 */
export const IndexValue: React.FC<{
  stat: DailyStat | null | undefined
  basis: PriceBasis
  /** 緊湊模式（表格內用），只顯示數字＋小字樣本數 */
  compact?: boolean
}> = ({ stat, basis, compact }) => {
  if (!stat) return <Text type="secondary">—</Text>
  const idx = basis === 'pretax' ? stat.index_pretax : stat.index_gross
  if (idx === null || idx === undefined) {
    return (
      <Tooltip title="沒有可用的競品中位數（競品全數滿房或無報價）">
        <Text type="secondary">—</Text>
      </Tooltip>
    )
  }

  // 1.00 ＝ 與競品中位數同價。偏離 10% 以上才變色，避免整片都在閃。
  const color = idx >= 1.10 ? '#cf1322' : idx <= 0.90 ? '#389e0d' : undefined
  const n = sampleCountOf(stat, basis)
  const low = n < MIN_SAMPLE

  const body = (
    <Space size={4}>
      <Text strong style={{ color, fontSize: compact ? 13 : 20 }}>
        {idx.toFixed(3)}
      </Text>
      <Text type={low ? 'warning' : 'secondary'} style={{ fontSize: 12 }}>
        {low && <ExclamationCircleOutlined style={{ marginRight: 2 }} />}
        n={n}
      </Text>
    </Space>
  )

  return (
    <Tooltip title={
      <div style={{ maxWidth: 300 }}>
        <div>自己 ÷ 競品中位數（{basis === 'pretax' ? '稅前' : '含稅'}）</div>
        <div style={{ marginTop: 4 }}>
          進中位數的競品家數：<b>{n}</b>
          {low && <span style={{ color: '#faad14' }}>（低於 {MIN_SAMPLE} 家，僅供參考）</span>}
        </div>
        {stat.unknown_count > 0 && (
          <div>其中 {stat.unknown_count} 家滿房狀態未知（遠期資料，
            地點查詢判不出滿房）</div>
        )}
        {stat.sold_out_count > 0 && (
          <div>另有 {stat.sold_out_count} 家已滿房（不計入中位數）</div>
        )}
      </div>
    }>
      {body}
    </Tooltip>
  )
}

/**
 * 名次。
 *
 * ⚠️ 一律顯示成 `3 / 5`，**不可只寫「第 3 名」**（SPEC §7.4）。
 *    「第 3 名」在 5 家裡是中間，在 3 家裡是最後一名，意思完全相反。
 */
export const RankValue: React.FC<{ stat: DailyStat | null | undefined }> = ({ stat }) => {
  if (!stat || stat.self_rank === null || stat.rank_total === null) {
    return <Text type="secondary">—</Text>
  }
  return (
    <Tooltip title="含稅價由低到高的名次（含自己）。1 ＝ 全場最便宜。">
      <Text>{stat.self_rank} / {stat.rank_total}</Text>
    </Tooltip>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// 三態標籤
// ══════════════════════════════════════════════════════════════════════════
const SOLD_OUT_META: Record<SoldOutState, { color: string; label: string; tip: string }> = {
  yes:     { color: 'red',     label: '滿房', tip: '該日查無任何報價（property_token 路徑實測）' },
  no:      { color: 'green',   label: '有房', tip: '該日有報價' },
  unknown: { color: 'default', label: '未知', tip: '地點查詢路徑（B／C 級）判斷不出滿房，一律未知。不是資料缺漏。' },
}

/** ⚠️ 三態，不是布林。`unknown` 是常態不是異常 —— B／C 級全部都是 unknown。 */
export const SoldOutTag: React.FC<{ value: SoldOutState }> = ({ value }) => {
  const m = SOLD_OUT_META[value] ?? SOLD_OUT_META.unknown
  return <Tooltip title={m.tip}><Tag color={m.color}>{m.label}</Tag></Tooltip>
}

const TAX_META: Record<TaxState, { color: string; label: string; tip: string }> = {
  yes:     { color: 'blue',    label: '含稅', tip: '報價已含稅與服務費' },
  no:      { color: 'orange',  label: '未稅', tip: '報價未含稅（只有 CSV 匯入會出現）' },
  unknown: { color: 'default', label: '不明', tip: '來源未標示含稅與否；含稅價與稅前價相同時一律歸為不明，不臆測為未稅。' },
}

export const TaxTag: React.FC<{ value: TaxState }> = ({ value }) => {
  const m = TAX_META[value] ?? TAX_META.unknown
  return <Tooltip title={m.tip}><Tag color={m.color}>{m.label}</Tag></Tooltip>
}

// ══════════════════════════════════════════════════════════════════════════
// 格式化
// ══════════════════════════════════════════════════════════════════════════
export function fmtMoney(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  return `$${Math.round(v).toLocaleString('en-US')}`
}

/** 從 `RateCell` 取出當前口徑的價格。 */
export function priceOf(
  cell: { price_pretax: number | null; price_gross: number | null } | null | undefined,
  basis: PriceBasis,
): number | null {
  if (!cell) return null
  return basis === 'pretax' ? cell.price_pretax : cell.price_gross
}

/** 階層標籤。A ＝ 近期逐日，B ＝ 中期，C ＝ 遠期。 */
export const TierTag: React.FC<{ tier: string }> = ({ tier }) => {
  const meta: Record<string, { color: string; tip: string }> = {
    A: { color: 'geekblue', tip: 'A 級：D+1〜14，每日抓，逐家 property_token（可判滿房）' },
    B: { color: 'cyan',     tip: 'B 級：D+15〜45，每 3 天抓一次，地點查詢' },
    C: { color: 'purple',   tip: 'C 級：D+46〜120，每週抓一次，地點查詢' },
  }
  // 人工搜尋競爭組候選不屬於任何級別，`compset_search_service` 寫的是 "-"
  if (tier === '-') {
    return <Tooltip title="人工搜尋競爭組候選（不是排程抓取）">
      <Tag color="magenta">搜尋</Tag></Tooltip>
  }
  const m = meta[tier]
  if (!m) return <Tag>{tier || '—'}</Tag>
  return <Tooltip title={m.tip}><Tag color={m.color}>{tier} 級</Tag></Tooltip>
}


// ══════════════════════════════════════════════════════════════════════════
// 入住日
// ══════════════════════════════════════════════════════════════════════════
/** 星期的單字表示。index 對 `dayjs().day()`（0 ＝ 週日）。 */
const WEEKDAY = '日一二三四五六'

/**
 * ⚠️ **週五、週六算旺日**（不是一般認知的週六、週日）。
 *
 * 飯店賣的是「住哪一晚」：週五晚上住、週六退房 —— 那是週末行程的第一晚。
 * 週日晚上反而是平日價。所以旺日是 `day() === 5 || day() === 6`，
 * 照一般「週末 ＝ 六日」去寫會把週日誤標成旺日、把週五漏掉。
 */
export function isPeakNight(dateStr: string): boolean {
  const d = dayjs(dateStr).day()
  return d === 5 || d === 6
}

/**
 * 入住日 ＋ 星期。
 *
 * ⚠️ **星期是必要資訊不是裝飾。** 競品分析的每一列都是某一個入住日，
 *    而飯店訂價是「看星期幾」不是「看幾號」—— 只顯示 `2026-09-20`
 *    的話，使用者得自己心算那天是週幾才知道該不該跟進調價。
 *
 * ⚠️ 兩個頁面（Dashboard 的未來 7 天明細、價格矩陣）共用這一支，
 *    不要各自刻 —— 旺日的判定規則只能有一份（見 `isPeakNight`）。
 *
 * @param onClick 有帶就渲染成連結（Dashboard 用來下鑽到價格軌跡）
 */
export const StayDateLabel: React.FC<{
  date: string
  onClick?: () => void
}> = ({ date, onClick }) => {
  const peak = isPeakNight(date)
  const wd = WEEKDAY[dayjs(date).day()]
  const body = (
    <Space size={4}>
      <span style={{ fontWeight: peak ? 700 : undefined }}>{date}</span>
      <Text type="secondary" style={{ fontSize: 12 }}>({wd})</Text>
    </Space>
  )
  const wrapped = onClick
    ? <a onClick={onClick}>{body}</a>
    : body
  return peak
    ? <Tooltip title="週五／週六入住 ＝ 旺日。訂價邏輯與平日不同，比價時分開看。">{wrapped}</Tooltip>
    : wrapped
}


// ══════════════════════════════════════════════════════════════════════════
// 滿房
// ══════════════════════════════════════════════════════════════════════════
/**
 * 滿房家數 ＋ **是哪幾家**。
 *
 * ⚠️ 只給「2 家滿房」是不夠的 —— 使用者要知道**是哪兩家**才能決定怎麼做。
 *    地板錨點的青旅賣完，跟上檔天花板的飯店賣完，代表的意義完全相反：
 *    前者只是便宜的房型先被吃掉，後者才是整個市場在收緊、可以往上試價。
 *
 * ⚠️ `sold_out_hotel_ids` 只有 id，名字要靠 `hotels` 對照表查。
 *    查不到的 id **不靜默丟掉** —— 顯示 `#id` 讓人看得出資料有問題，
 *    直接跳過會讓家數與標籤數對不起來，而且完全沒有線索。
 */
export const SoldOutCell: React.FC<{
  stat: DailyStat | null | undefined
  hotels: { id: number; short_name: string; name: string }[]
}> = ({ stat, hotels }) => {
  if (!stat || stat.sold_out_count === 0) return <Text type="secondary">—</Text>

  const ids = stat.sold_out_hotel_ids ?? []
  const named = ids.map((id) => {
    const h = hotels.find((x) => x.id === id)
    return { id, short: h?.short_name || `#${id}`, full: h?.name || `id=${id}` }
  })

  return (
    <Tooltip title={
      <div style={{ maxWidth: 280 }}>
        <div>該日已滿房的競品（不計入中位數）：</div>
        <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>
          {named.map((h) => <li key={h.id}>{h.full}</li>)}
        </ul>
        <div style={{ marginTop: 6 }}>
          競品賣完 ＝ 市場在收緊，可以考慮往上試價。
        </div>
      </div>
    }>
      <Space size={2} wrap style={{ justifyContent: 'center' }}>
        <Tag color="red" style={{ marginInlineEnd: 2 }}>{stat.sold_out_count} 家</Tag>
        {named.map((h) => (
          <Tag key={h.id} color="volcano" style={{ marginInlineEnd: 2 }}>
            {h.short}
          </Tag>
        ))}
      </Space>
    </Tooltip>
  )
}


// ══════════════════════════════════════════════════════════════════════════
// 資料時點
// ══════════════════════════════════════════════════════════════════════════
/**
 * 「資料快照日 ＋ 最後更新時間」。
 *
 * ⚠️ **時間是必要資訊不是裝飾。** 使用者拿畫面對 Google 對不上時，
 *    第一個要問的就是「這是幾點抓的」—— 房價一天內會動，
 *    早上 04:10 的快照跟現在的 Google 本來就不會一樣。
 *
 * ⚠️ `fetched_at` 已經是**台灣時間字串**，**直接印**。
 *    不要餵給 `dayjs()` 再 `format()` —— 那會把它當本地時間再轉一次，
 *    在非台灣時區的瀏覽器上會平白差 8 小時，而且畫面上看不出來。
 */
export const SnapshotStamp: React.FC<{
  snapshotDate: string | null | undefined
  fetchedAt: string | null | undefined
}> = ({ snapshotDate, fetchedAt }) => {
  if (!snapshotDate) return <Text type="secondary">尚無資料</Text>
  return (
    <Tooltip title={
      <div style={{ maxWidth: 300 }}>
        <div>這批資料是 <b>{fetchedAt || snapshotDate}</b> 抓的。</div>
        <div style={{ marginTop: 4 }}>
          排程每天 04:10 跑一次；手動觸發也會更新這個時間。
        </div>
        <div style={{ marginTop: 4 }}>
          ⚠️ 房價一天之內會變動 —— 拿這裡的數字去對<b>現在</b>的 Google，
          本來就會有落差。
        </div>
      </div>
    }>
      <Text type="secondary">
        資料快照日：{snapshotDate}
        {fetchedAt && <>　｜　最後更新：{fetchedAt.slice(11) || fetchedAt}</>}
      </Text>
    </Tooltip>
  )
}
