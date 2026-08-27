/**
 * OTA 口碑分析 — 主題輪動熱力圖（2026-08-27）
 *
 * 資料來源：`GET /api/v1/ota/stats/topic-rotation`
 *
 * 【這張圖回答什麼】
 *   月度趨勢圖回答「分數在變好還是變差」，
 *   本圖回答「**變差的是哪一件事**，而且它是最近才變差的嗎」。
 *
 * ⚠️ **格子看的是佔比與名次，不是絕對數**。
 *    OTA 評論則數本身有淡旺季，旺季每個主題都會變多。看絕對數只會看到
 *    「暑假什麼都在漲」，看不出重心移動 —— 而重心移動才是可行動的訊號。
 *
 * ⚠️ **沒有格子 ≠ 那個月沒問題**。可能是那個月根本沒幾則評論。
 *    所以月份標頭要把樣本數一起顯示，樣本少的月份整欄變灰。
 *
 * ⚠️ 不用 recharts —— recharts 沒有熱力圖，硬用 ScatterChart 疊色塊
 *    會失去「表格可以掃視」這個熱力圖唯一的優點。這裡用 CSS grid。
 *
 * ═══════════════════════════════════════════════════════════════════════
 * 2026-08-27 使用者要求的三件事
 * ═══════════════════════════════════════════════════════════════════════
 * 1. **主題固定不被移動** —— 兩層意思，兩層都做了：
 *    ① 左欄 `position: sticky` 凍結，橫向捲月份時主題名不會跑掉
 *    ② 列序改由後端給字典順序（見 `_topic_dict_order()`），
 *       不隨 basis／篩選重排
 * 2. **播放／暫停** —— 時間游標逐月掃過整張圖，其餘月份淡出，
 *    右側同步顯示該月名次。整張圖保持在畫面上，才看得出「重心從哪移到哪」
 * 3. **全螢幕** —— Fullscreen API
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Button, Empty, Slider, Space, Tag, Tooltip, Typography } from 'antd'
import {
  CaretRightOutlined, FullscreenExitOutlined, FullscreenOutlined,
  PauseOutlined, StepBackwardOutlined,
} from '@ant-design/icons'

import type {
  TopicRotationBasis, TopicRotationCell, TopicRotationResult,
} from '@/types/ota'

const { Text } = Typography

/** 低於這個評論則數的月份要標出來 —— 與 Trend 頁的 THIN_SAMPLE 同一個門檻 */
const THIN_REVIEWS = 5

const TOPIC_COL = 104
const MONTH_COL = 62

/** negative 基準用紅、all 基準用品牌藍（`#4BA8E8`，CLAUDE.md 受保護色，不要改） */
const SCALE: Record<TopicRotationBasis, [number, number, number]> = {
  negative: [207, 19, 34],   // #cf1322
  all: [75, 168, 232],       // #4BA8E8
}

/** 播放速度 → 每格停留毫秒。⚠️ 最快不低於 400ms，再快就只剩閃爍看不出變化 */
const SPEEDS: { label: string; ms: number }[] = [
  { label: '慢', ms: 1600 },
  { label: '中', ms: 900 },
  { label: '快', ms: 450 },
]

interface Props {
  data: TopicRotationResult | null
  basis: TopicRotationBasis
  /**
   * 全螢幕時要放大的元素。
   *
   * ⚠️ **請傳外層 Card 的 ref**，不要讓它退回預設值。
   *    只放大熱力圖本身的話，「只看負面／正負都看」與「顯示主題數」兩個
   *    控制項留在 Card 的 extra 裡沒被放大 —— 進了全螢幕就調不到，
   *    使用者只能退出、調完、再進去一次。
   */
  fullscreenRef?: React.RefObject<HTMLElement>
}

const TopicRotationHeatmap: React.FC<Props> = ({ data, basis, fullscreenRef }) => {
  // ── 播放狀態 ──────────────────────────────────────────────────────
  // `cursor === null` ＝ 沒在播，整張圖等亮度顯示（預設狀態）
  const [cursor, setCursor] = useState<number | null>(null)
  const [playing, setPlaying] = useState(false)
  const [speedIdx, setSpeedIdx] = useState(1)
  const [isFull, setIsFull] = useState(false)

  const rootRef = useRef<HTMLDivElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const { months, topics, cellMap, maxShare } = useMemo(() => {
    const ms = data?.months ?? []
    // ⚠️ **不要在這裡再排序一次**。順序是後端給的字典順序（使用者要求固定），
    //    前端一排就白費了，而且兩邊排序規則遲早會不一致。
    const ts = data?.topics ?? []
    const map = new Map<string, TopicRotationCell>()
    let max = 0
    ;(data?.cells ?? []).forEach((c) => {
      map.set(`${c.review_month}|${c.topic}`, c)
      if (c.share > max) max = c.share
    })
    return { months: ms, topics: ts, cellMap: map, maxShare: max }
  }, [data])

  const lastIndex = months.length - 1

  // ── 播放計時器 ────────────────────────────────────────────────────
  // ⚠️ 播到最後一格就**停下來**，不自動回頭重播。
  //    循環播放會讓人搞不清楚現在是第幾輪、剛剛看到的是哪個月。
  useEffect(() => {
    if (!playing || months.length === 0) return undefined
    const timer = window.setInterval(() => {
      setCursor((prev) => {
        const next = prev === null ? 0 : prev + 1
        if (next > lastIndex) {
          setPlaying(false)
          return lastIndex
        }
        return next
      })
    }, SPEEDS[speedIdx].ms)
    return () => window.clearInterval(timer)
  }, [playing, speedIdx, lastIndex, months.length])

  // 篩選變了就把播放重置 —— 不然游標會指到一個已經不存在的月份
  useEffect(() => {
    setPlaying(false)
    setCursor(null)
  }, [data])

  // 游標移動時把該欄捲進視野（欄位可能遠在畫面外）
  useEffect(() => {
    if (cursor === null || !scrollRef.current) return
    const el = scrollRef.current
    const target = TOPIC_COL + cursor * MONTH_COL - el.clientWidth / 2 + MONTH_COL / 2
    el.scrollTo({ left: Math.max(0, target), behavior: 'smooth' })
  }, [cursor])

  // ── 全螢幕 ────────────────────────────────────────────────────────
  // ⚠️ 用 `fullscreenchange` 事件同步狀態，不要只信自己按下去的那一下 ——
  //    使用者按 Esc 離開全螢幕不會經過我們的按鈕，狀態會卡在 true。
  const fsTarget = useCallback(
    () => fullscreenRef?.current ?? rootRef.current, [fullscreenRef])

  useEffect(() => {
    const onChange = () => setIsFull(
      document.fullscreenElement !== null
      && document.fullscreenElement === fsTarget())
    document.addEventListener('fullscreenchange', onChange)
    return () => document.removeEventListener('fullscreenchange', onChange)
  }, [fsTarget])

  const toggleFull = useCallback(() => {
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => undefined)
    } else {
      fsTarget()?.requestFullscreen().catch(() => undefined)
    }
  }, [fsTarget])

  const play = useCallback(() => {
    // 停在最後一格時再按播放 ＝ 從頭再看一次
    setCursor((prev) => (prev === null || prev >= lastIndex ? 0 : prev))
    setPlaying(true)
  }, [lastIndex])

  const reset = useCallback(() => {
    setPlaying(false)
    setCursor(null)
  }, [])

  const hasData = Boolean(data) && months.length > 0 && topics.length > 0

  const [r, g, b] = SCALE[basis]

  /** 用相對強度上色。分母取全圖最大值而非 1，否則整張圖會淡到看不出差別。 */
  const bgOf = (share: number) => {
    if (share <= 0 || maxShare <= 0) return 'transparent'
    // 下限 0.12：有值就要看得見，不然「1 次提及」與「沒提及」在畫面上一樣
    const alpha = 0.12 + 0.78 * (share / maxShare)
    return `rgba(${r}, ${g}, ${b}, ${alpha.toFixed(3)})`
  }

  /** 深底色配白字，否則數字會糊在色塊裡 */
  const fgOf = (share: number) =>
    (maxShare > 0 && share / maxShare > 0.55 ? '#fff' : '#333')

  const cellH = isFull ? 34 : 28
  const gridTemplate = `${TOPIC_COL}px repeat(${months.length}, minmax(${MONTH_COL}px, 1fr))`

  /** 凍結欄的共用樣式。⚠️ 背景必須不透明，否則捲過去的格子會透出來。 */
  const stickyStyle: React.CSSProperties = {
    position: 'sticky',
    left: 0,
    zIndex: 2,
    background: '#fff',
    // 第一層陰影補滿 grid 的 2px gap（不補的話會有一條格子從縫隙透出來），
    // 第二層才是視覺上的分隔線
    boxShadow: '3px 0 0 0 #fff, 5px 0 5px -4px rgba(0, 0, 0, 0.18)',
  }

  /** 播放中該月的名次清單（右側面板用） */
  const cursorMonth = cursor !== null ? months[cursor] : undefined
  const cursorRanking = useMemo(() => {
    if (!cursorMonth) return []
    const prevMonth = cursor !== null && cursor > 0 ? months[cursor - 1] : undefined
    return topics
      .map((t) => {
        const cell = cellMap.get(`${cursorMonth.review_month}|${t.topic}`)
        const prev = prevMonth
          ? cellMap.get(`${prevMonth.review_month}|${t.topic}`)
          : undefined
        return { topic: t.topic, cell, prevRank: prev?.rank ?? null }
      })
      .filter((x) => x.cell?.rank != null)
      .sort((a, b) => (a.cell!.rank ?? 0) - (b.cell!.rank ?? 0))
  }, [cursorMonth, cursor, months, topics, cellMap])

  return (
    <div
      ref={rootRef}
      style={{
        background: '#fff',
        // 只有在「放大元件自己」時才需要自己補內距；放大整張 Card 的話
        // 交給下面那段 `:fullscreen` CSS 處理（Card 有自己的內距）
        ...(isFull && !fullscreenRef
          ? { padding: 20, overflow: 'auto', height: '100%' }
          : {}),
      }}
    >
      {/* ⚠️ 這段**不能**寫成 inline style —— `:fullscreen` 是虛擬類別，
          inline style 表達不出來。全螢幕元素在部分瀏覽器的 UA 預設背景是黑色，
          不蓋掉的話整張圖會浮在黑底上。 */}
      <style>{`
        .ota-rotation-fs:fullscreen {
          background: #fff;
          overflow: auto;
          padding: 20px;
        }
      `}</style>

      {isFull && !fullscreenRef && (
        <Text strong style={{ fontSize: 16, display: 'block', marginBottom: 12 }}>
          主題輪動・客訴重心怎麼移
        </Text>
      )}

      {/* ── 播放與全螢幕控制列 ──────────────────────────────────────
          ⚠️ 全螢幕按鈕**不能**放在外層 Card 的 extra —— 全螢幕的是這個
             元件的 root，Card 的標題列不在裡面，進去之後按鈕就消失了。 */}
      <Space size={8} wrap style={{ marginBottom: 10 }}>
        <Button
          size="small"
          type={playing ? 'default' : 'primary'}
          icon={playing ? <PauseOutlined /> : <CaretRightOutlined />}
          onClick={() => (playing ? setPlaying(false) : play())}
          disabled={!hasData}
        >
          {playing ? '暫停' : '播放'}
        </Button>
        <Tooltip title="回到「整張圖等亮度」的預設狀態">
          <Button
            size="small" icon={<StepBackwardOutlined />} onClick={reset}
            disabled={!hasData || (cursor === null && !playing)}
          />
        </Tooltip>

        <Space size={2}>
          {SPEEDS.map((s, i) => (
            <Button
              key={s.label} size="small"
              type={speedIdx === i ? 'primary' : 'text'}
              onClick={() => setSpeedIdx(i)}
              style={{ paddingInline: 8 }}
            >
              {s.label}
            </Button>
          ))}
        </Space>

        <div style={{ width: isFull ? 320 : 200, paddingInline: 4 }}>
          <Slider
            min={0} max={Math.max(lastIndex, 0)} step={1}
            value={cursor ?? 0}
            disabled={!hasData}
            tooltip={{ formatter: (v) => months[v ?? 0]?.review_month ?? '' }}
            onChange={(v) => { setPlaying(false); setCursor(v) }}
            style={{ margin: 0 }}
          />
        </div>

        <Text type="secondary" style={{ fontSize: 12, minWidth: 96 }}>
          {cursorMonth
            ? `${cursorMonth.review_month}（${cursor! + 1}/${months.length}）`
            : '全期間'}
        </Text>

        <Tooltip title={isFull ? '離開全螢幕（或按 Esc）' : '全螢幕'}>
          <Button
            size="small"
            icon={isFull ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            onClick={toggleFull}
          />
        </Tooltip>
      </Space>

      {!hasData ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="這個範圍沒有主題資料 —— 評論可能還沒跑過分析"
        />
      ) : (
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <div ref={scrollRef} style={{ overflowX: 'auto', paddingBottom: 4, flex: 1 }}>
            <div style={{ minWidth: TOPIC_COL + months.length * MONTH_COL }}>
              {/* ── 月份標頭 ────────────────────────────────────── */}
              <div style={{
                display: 'grid', gridTemplateColumns: gridTemplate, gap: 2,
                position: 'sticky', top: 0, zIndex: 3, background: '#fff',
              }}>
                <div style={{ ...stickyStyle, zIndex: 4 }} />
                {months.map((m, mi) => {
                  const thin = m.review_count > 0 && m.review_count < THIN_REVIEWS
                  const active = cursor === mi
                  const dim = cursor !== null && !active
                  return (
                    <Tooltip
                      key={m.review_month}
                      title={`${m.review_month}：${m.review_count} 則評論、${m.mention_total} 次主題提及${
                        thin ? '（樣本太少，名次容易被單一評論帶動）' : ''}`}
                    >
                      <div
                        onClick={() => { setPlaying(false); setCursor(mi) }}
                        style={{
                          textAlign: 'center', fontSize: 11, padding: '2px 0',
                          color: active ? '#1B3A5C' : thin ? '#bbb' : '#666',
                          fontWeight: active ? 700 : 400,
                          opacity: dim ? 0.35 : 1,
                          borderBottom: active
                            ? '2px solid #1B3A5C'
                            : thin ? '2px solid #f0f0f0' : '2px solid #d9d9d9',
                          cursor: 'pointer',
                          transition: 'opacity .25s',
                        }}
                      >
                        {m.review_month.slice(2).replace('-', '/')}
                      </div>
                    </Tooltip>
                  )
                })}
              </div>

              {/* ── 主題列（順序來自後端字典順序，前端不重排）────────── */}
              {topics.map((t) => (
                <div
                  key={t.topic}
                  style={{
                    display: 'grid', gridTemplateColumns: gridTemplate,
                    gap: 2, marginTop: 2,
                  }}
                >
                  <div style={{
                    ...stickyStyle,
                    fontSize: 12, display: 'flex', alignItems: 'center',
                    justifyContent: 'flex-end', paddingRight: 6, gap: 4,
                    overflow: 'hidden', height: cellH,
                  }}>
                    {/* ⚠️ 中途才進字典的主題，前面的月份是**沒有統計**而不是「沒發生」。
                        不標出來的話會被讀成「這個問題最近才出現」。 */}
                    {t.since_month && (
                      <Tooltip title={`此主題自 ${t.since_month} 才進入字典，之前的月份沒有回頭重跑分析，空白不代表沒發生`}>
                        <Tag color="warning" style={{ marginInlineEnd: 0, fontSize: 10, lineHeight: '16px', padding: '0 3px' }}>
                          新
                        </Tag>
                      </Tooltip>
                    )}
                    <Text ellipsis style={{ fontSize: 12 }} title={t.topic}>{t.topic}</Text>
                  </div>

                  {months.map((m, mi) => {
                    const cell = cellMap.get(`${m.review_month}|${t.topic}`)
                    const share = cell?.share ?? 0
                    const prev = mi > 0
                      ? cellMap.get(`${months[mi - 1].review_month}|${t.topic}`)
                      : undefined
                    // 名次「往前」＝提及佔比升高。negative 基準下這是變糟，不是變好。
                    const climbed = cell?.rank != null && prev?.rank != null
                      && cell.rank < prev.rank
                    const active = cursor === mi
                    const dim = cursor !== null && !active

                    return (
                      <Tooltip
                        key={m.review_month}
                        title={cell ? (
                          <span>
                            <b>{t.topic}</b>・{m.review_month}
                            <br />第 {cell.rank} 名，佔該月提及 {(cell.share * 100).toFixed(1)}%
                            <br />負面 {cell.negative_count} 次、正面 {cell.positive_count} 次
                            {climbed && <><br />⚠️ 名次比上個月往前（提及變密集）</>}
                          </span>
                        ) : `${t.topic}・${m.review_month}：沒有提及`}
                      >
                        <div style={{
                          height: cellH, borderRadius: 3,
                          background: bgOf(share),
                          border: share > 0 ? 'none' : '1px dashed #f0f0f0',
                          boxShadow: active ? 'inset 0 0 0 1px rgba(27, 58, 92, .45)' : undefined,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: 11, fontWeight: climbed ? 700 : 400,
                          color: fgOf(share), cursor: 'help',
                          opacity: dim ? 0.28 : 1,
                          transition: 'opacity .25s',
                        }}>
                          {cell ? `${(cell.share * 100).toFixed(0)}%` : ''}
                        </div>
                      </Tooltip>
                    )
                  })}
                </div>
              ))}
            </div>
          </div>

          {/* ── 播放中的名次面板 ────────────────────────────────────
              ⚠️ 熱力圖本身**不重排**（使用者要求主題固定），所以「這個月誰
                 排第一」在圖上要靠比顏色深淺才看得出來。這個面板補的就是
                 那件事：圖給你趨勢，面板給你當月的確切名次。 */}
          {cursorMonth && (
            <div style={{
              width: isFull ? 260 : 200, flexShrink: 0,
              border: '1px solid #f0f0f0', borderRadius: 4, padding: '8px 10px',
            }}>
              <Text strong style={{ fontSize: 12 }}>{cursorMonth.review_month} 名次</Text>
              <div style={{ marginTop: 2, marginBottom: 6 }}>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {cursorMonth.review_count} 則評論・{cursorMonth.mention_total} 次提及
                  {cursorMonth.review_count > 0 && cursorMonth.review_count < THIN_REVIEWS
                    && <><br />⚠️ 樣本太少，名次僅供參考</>}
                </Text>
              </div>
              {cursorRanking.length === 0 ? (
                <Text type="secondary" style={{ fontSize: 11 }}>這個月沒有主題提及</Text>
              ) : cursorRanking.slice(0, 8).map((x) => {
                const rank = x.cell!.rank as number
                // ⚠️ 名次數字變小 ＝ 往前 ＝ 被提得更密集。negative 基準下是變糟。
                const delta = x.prevRank === null ? null : x.prevRank - rank
                return (
                  <div key={x.topic} style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    fontSize: 12, padding: '2px 0',
                  }}>
                    <span style={{ width: 16, color: '#999' }}>{rank}</span>
                    <span style={{ flex: 1 }}>{x.topic}</span>
                    <span style={{ color: '#666' }}>
                      {(x.cell!.share * 100).toFixed(0)}%
                    </span>
                    <span style={{ width: 26, textAlign: 'right', fontSize: 11 }}>
                      {delta === null
                        ? <Text type="secondary">新</Text>
                        : delta > 0
                          ? <span style={{ color: '#cf1322' }}>▲{delta}</span>
                          : delta < 0
                            ? <span style={{ color: '#52c41a' }}>▼{-delta}</span>
                            : <Text type="secondary">—</Text>}
                    </span>
                  </div>
                )
              })}
              <Text type="secondary" style={{ fontSize: 10, display: 'block', marginTop: 6 }}>
                ▲＝名次往前（被提得更密集）。
                {basis === 'negative' ? '在「只看負面」下代表變糟。' : ''}
              </Text>
            </div>
          )}
        </div>
      )}

      {/* ── 圖例與警語 ──────────────────────────────────────────── */}
      {hasData && (
        <>
          <Space size={12} wrap style={{ marginTop: 10 }}>
            <Space size={4}>
              <Text type="secondary" style={{ fontSize: 11 }}>佔比低</Text>
              {[0.2, 0.4, 0.6, 0.8, 1].map((v) => (
                <span key={v} style={{
                  display: 'inline-block', width: 16, height: 10, borderRadius: 2,
                  background: `rgba(${r}, ${g}, ${b}, ${0.12 + 0.78 * v})`,
                }} />
              ))}
              <Text type="secondary" style={{ fontSize: 11 }}>高</Text>
            </Space>
            <Text type="secondary" style={{ fontSize: 11 }}>
              粗體 ＝ 名次比上個月往前（該主題被提得更密集）
            </Text>
          </Space>

          <div style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              ⚠️ 格子是<b>佔該月全部主題提及的比例</b>，不是則數 ——
              旺季評論多，看絕對數只會看到「什麼都在漲」。
              <br />
              ⚠️ 空白格代表那個月<b>沒有被提到</b>；若整欄都很淡，先看月份標頭的樣本數，
              可能只是那個月評論太少。
              <br />
              ⚠️ 主題列固定照<b>字典順序</b>排，不隨篩選或基準重排 ——
              要比較的是同一列在不同月份的變化，列自己在跳就沒得比。
              {data!.truncated_topics > 0 && (
                <>
                  <br />
                  ⚠️ 另有 {data!.truncated_topics} 個主題未顯示（依總量取前 {topics.length} 名），
                  調高「顯示主題數」可以看到全部。
                </>
              )}
            </Text>
          </div>
        </>
      )}
    </div>
  )
}

export default TopicRotationHeatmap
