/**
 * StandardRangePicker — 全站標準日期區間選擇器（2026-08-05 訂為規範）
 *
 * 規範見 CLAUDE.md「§8 日期區間選擇器（月曆）標準元件」。
 * **任何模組要做「期間篩選」一律用這支，不要自己刻 RangePicker。**
 *
 * ── 六個快捷（順序與文字固定，不可各模組自訂）──────────────────────────────
 *   本月 / 上月 / 最近 30 天 / 今年 / 去年 / 全部
 *
 * ── 最重要的一條規則：快捷以「資料最後一天」為基準，不是今天 ────────────────
 * 很多模組的資料會落後現實（OPERA 匯出落後幾天、Ragic 同步有排程間隔）。
 * 若用 `dayjs()` 當基準，「本月」會選到還沒有資料的日子，使用者會誤以為資料缺漏。
 * 所以呼叫端**應該**傳入 `anchor`（該頁資料來源的最後一天）。
 * 沒傳會退回以今天為基準，並在下拉選單底部標明，不會靜默用錯基準。
 *
 * ── 「全部」的語意 ──────────────────────────────────────────────────────────
 * 回傳 `null`，呼叫端就不要帶 start／end，由後端套用完整資料範圍。
 * 是「全部資料」而不是「不篩選」。若某個 API 的起迄為必填，
 * 呼叫端應自行把 `null` 對應成已知的完整資料範圍（不要改這支元件）。
 *
 * ── 不適用的情境（請直接用 antd 的 DatePicker／RangePicker）─────────────────
 *   1. 表單欄位（在填某件事的實際日期，例如事件起迄）—— 快捷幫不上忙反而是干擾
 *   2. 未來導向的選擇（例如預測期間）—— 「本月／上月／去年」都是過去
 *   3. 單日選擇 —— 本元件是區間用的
 */
import React, { useMemo } from 'react'
import { DatePicker, Typography } from 'antd'
import dayjs, { Dayjs } from 'dayjs'

const { RangePicker } = DatePicker
const { Text } = Typography

export type StandardRange = [Dayjs, Dayjs] | null

/** 六個標準快捷的識別字（要隱藏某幾個時用 `hidePresets` 指定） */
export type PresetKey = 'thisMonth' | 'lastMonth' | 'last30' | 'thisYear' | 'lastYear' | 'all'

export interface StandardRangePickerProps {
  value: StandardRange
  onChange: (value: StandardRange) => void
  /**
   * 資料最後一天（ISO 字串或 Dayjs）。快捷區間以它為基準。
   * **強烈建議傳入**；未傳時退回今天並在下拉選單底部標明。
   */
  anchor?: string | Dayjs | null
  /**
   * 要隱藏的快捷。預設六個全開。
   * 例：API 起迄必填又不想自行處理時可傳 `['all']`。
   */
  hidePresets?: PresetKey[]
  disabled?: boolean
  allowClear?: boolean
  style?: React.CSSProperties
  /** 額外說明，會接在下拉選單底部的基準日說明之後 */
  footerNote?: string
}

const StandardRangePicker: React.FC<StandardRangePickerProps> = ({
  value, onChange, anchor, hidePresets, disabled, allowClear = true, style, footerNote,
}) => {
  const anchorDay = useMemo<Dayjs>(() => {
    if (!anchor) return dayjs()
    const d = dayjs(anchor)
    return d.isValid() ? d : dayjs()
  }, [anchor])

  const hasAnchor = !!anchor && dayjs(anchor).isValid()
  const lagDays = hasAnchor
    ? dayjs().startOf('day').diff(anchorDay.startOf('day'), 'day')
    : 0

  const presets = useMemo(() => {
    const a = anchorDay
    const hidden = new Set(hidePresets || [])
    const all: { key: PresetKey; label: string; value: [Dayjs, Dayjs] }[] = [
      { key: 'thisMonth', label: '本月',
        value: [a.startOf('month'), a] },
      { key: 'lastMonth', label: '上月',
        value: [a.subtract(1, 'month').startOf('month'), a.subtract(1, 'month').endOf('month')] },
      { key: 'last30', label: '最近 30 天',
        value: [a.subtract(29, 'day'), a] },
      { key: 'thisYear', label: '今年',
        value: [a.startOf('year'), a] },
      { key: 'lastYear', label: '去年',
        value: [a.subtract(1, 'year').startOf('year'), a.subtract(1, 'year').endOf('year')] },
      // 「全部」用 [null, null]，在 onChange 會被正規化成 null
      { key: 'all', label: '全部',
        value: [null as never, null as never] },
    ]
    return all.filter((p) => !hidden.has(p.key)).map(({ label, value: v }) => ({ label, value: v }))
  }, [anchorDay, hidePresets])

  return (
    <RangePicker
      style={style}
      disabled={disabled}
      allowClear={allowClear}
      value={value as never}
      allowEmpty={[true, true]}
      presets={presets}
      // 參數刻意標成 unknown 再自行縮型：antd RangePicker 的 onChange 簽名在版本間
      // 有差異，寫死會綁在特定版本；標 unknown 一定相容，且下一行立刻縮成執行期
      // 實際型別，型別安全並沒有變差。
      onChange={(v: unknown) => {
        const r = v as [Dayjs | null, Dayjs | null] | null
        // 「全部」會給 [null, null]；統一正規化成 null，
        // 呼叫端才能用同一個判斷式決定要不要帶 start／end
        if (!r || (!r[0] && !r[1])) {
          onChange(null)
          return
        }
        if (!r[0] || !r[1]) return       // 只選了一端，等使用者選完
        onChange([r[0], r[1]])
      }}
      renderExtraFooter={() => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {hasAnchor
            ? `快捷區間以資料最後一天 ${anchorDay.format('YYYY-MM-DD')} 為基準`
              + (lagDays > 0 ? `（比今天早 ${lagDays} 天，資料匯入通常會落後）` : '')
            : '尚未取得資料範圍，快捷區間暫以今天為基準'}
          {footerNote ? `　${footerNote}` : ''}
        </Text>
      )}
    />
  )
}

export default StandardRangePicker
