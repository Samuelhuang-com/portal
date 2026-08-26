/**
 * 每日警示條帶（2026-08-25）
 *
 * 一天一格，顏色深淺 = 當天發生幾件警示。橫著看就是「哪幾天出事」。
 * 做法參考 `docs/TABLER_UI_NOTES.md` §I 的 `.tracking` / `.tracking-squares`
 * （uptime bar）—— ⚠️ 抄的是**做法**不是 markup，Tabler 的 class 依賴整套
 * Bootstrap CSS，單抄 class 不會有樣式（§N.3）。
 *
 * ═══════════════════════════════════════════════════════════════════════
 * ⚠️⚠️ 與「積壓天數」的口徑不同 —— 同一頁上必須講清楚
 * ═══════════════════════════════════════════════════════════════════════
 *   · 積壓分桶 ＝ **還沒處理的存量**（open + acknowledged）
 *   · 這張條帶 ＝ **當天發生了幾件**（不論後來處理了沒）
 *
 * 如果條帶也只算未處理，處理完的日子會變乾淨 ——
 * 看起來像「那幾天沒出事」，但事情確實發生過。
 * 兩個口徑都對，混為一談就變成「兩個數字對不起來」的老問題。
 *
 * ═══════════════════════════════════════════════════════════════════════
 * ⚠️⚠️ 「沒有資料」與「沒有警示」必須長得不一樣
 * ═══════════════════════════════════════════════════════════════════════
 * OTA 評論落後現實好幾天（客人退房後才留言 + 爬蟲每日才跑），
 * 所以最右邊幾格本來就還沒抓到。把它們畫成跟「0 件」一樣的空白格，
 * 看起來就是「這幾天很平靜」—— **那是這個模組最容易誤導人的一種呈現**，
 * 而且完全不會有錯誤訊息。斜線底紋 + tooltip 明說「尚無資料」。
 */
import React from 'react'
import { Card, Empty, Space, Tooltip, Typography } from 'antd'
import { CalendarOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'
import type { AlertDailyPoint, AlertDailyResult } from '@/types/ota'

const { Text } = Typography

/** 0 件用淺灰；有件數時依密度加深（品牌紅系，與警示一致） */
const EMPTY_COLOR = '#f0f0f0'
const ACTIVE_COLOR = '#ff4d4f'

/**
 * 一格的底色。
 *
 * ⚠️ 用**相對於最大值**的四階，不要用絕對件數 ——
 *    不同飯店的量級差很多（誠品行旅 3,977 則 vs 瀚寓 612 則），
 *    寫死「3 件以上就深紅」在小館會整條紅、在大館會整條淺。
 */
function cellColor(p: AlertDailyPoint, max: number): string {
  if (p.no_data) return 'transparent'
  if (p.count <= 0) return EMPTY_COLOR
  const ratio = max > 0 ? p.count / max : 0
  const alpha = ratio > 0.66 ? 1 : ratio > 0.33 ? 0.66 : 0.38
  return `rgba(255, 77, 79, ${alpha})`
}

export interface AlertDailyStripProps {
  data: AlertDailyResult | null
  loading?: boolean
  /** 點某一天 → 把清單篩到那一天 */
  onPick?: (range: [Dayjs, Dayjs] | null, date: string) => void
  activeDate?: string
}

export default function AlertDailyStrip(props: AlertDailyStripProps) {
  const { data, loading, onPick, activeDate } = props
  const days = data?.days ?? []
  const max = data?.max_count ?? 0
  const noDataCount = days.filter((d) => d.no_data).length

  return (
    <Card
      size="small"
      loading={loading}
      style={{ marginBottom: 16 }}
      title={
        <Space size={6}>
          <CalendarOutlined />
          <span>每日發生量</span>
          <Tooltip
            placement="bottomLeft"
            title={
              <span>
                每格一天，顏色越深代表當天發生越多件警示。點一格可以把清單篩到那天。
                <br /><br />
                ⚠️ <b>與上方「積壓天數」的口徑不同</b>：
                <br />・積壓天數＝<b>還沒處理</b>的存量
                <br />・這一條　＝當天<b>發生</b>了幾件（不論後來處理了沒）
                <br />只算未處理的話，處理完的日子會變乾淨，
                看起來像那幾天沒出事。
                <br /><br />
                ⚠️ <b>斜線格＝還沒有資料</b>，不是「沒有警示」。
                OTA 評論落後現實好幾天（客人退房後才留言、爬蟲每日才跑）。
                <br /><br />
                顏色深淺是<b>相對於這段期間的最大值</b>，不是絕對件數 ——
                各館評論量級差很多，用絕對值會讓小館整條紅、大館整條淺。
              </span>
            }
          >
            <QuestionCircleOutlined style={{ color: '#bbb', cursor: 'help' }} />
          </Tooltip>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
            最近 {days.length} 天・共 {data?.total ?? 0} 件
          </Text>
        </Space>
      }
      extra={activeDate && onPick ? <a onClick={() => onPick(null, '')}>清除日期篩選</a> : undefined}
    >
      {days.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="沒有資料"
               style={{ margin: '8px 0' }} />
      ) : (
        <div>
          <div style={{ display: 'flex', gap: 2, alignItems: 'flex-end' }}>
            {days.map((p) => {
              const active = activeDate === p.date
              const clickable = Boolean(onPick) && !p.no_data && p.count > 0
              return (
                <Tooltip
                  key={p.date}
                  title={p.no_data
                    ? `${p.date}　尚無資料（評論還沒抓到這一天）`
                    : `${p.date}　${p.count} 件`}
                >
                  <div
                    onClick={clickable
                      ? () => onPick?.([dayjs(p.date), dayjs(p.date)], p.date)
                      : undefined}
                    style={{
                      flex: 1, minWidth: 4, height: 26, borderRadius: 2,
                      background: cellColor(p, max),
                      // ⚠️ 斜線 = 還沒有資料。與「0 件」的淺灰**必須**看得出差別
                      backgroundImage: p.no_data
                        ? 'repeating-linear-gradient(45deg, #e8e8e8 0 3px, transparent 3px 6px)'
                        : undefined,
                      border: active ? '2px solid #1B3A5C' : '1px solid transparent',
                      cursor: clickable ? 'pointer' : 'default',
                    }}
                  />
                </Tooltip>
              )
            })}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
            <Text type="secondary" style={{ fontSize: 11 }}>{days[0]?.date}</Text>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {days[days.length - 1]?.date}
            </Text>
          </div>

          {/* ⚠️ 有斜線格時一定要說明，否則使用者只會看到右邊一片「空的」 */}
          {noDataCount > 0 && (
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
              右側 {noDataCount} 格為斜線＝**尚無資料**（評論資料最後更新至
              {' '}{data?.data_end || '—'}），不是「沒有警示」
            </Text>
          )}
        </div>
      )}
    </Card>
  )
}
