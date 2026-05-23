/**
 * useIdleTimeout — 閒置自動登出 Hook
 *
 * 行為：
 *   1. 使用者超過 IDLE_MINUTES 分鐘無任何互動 → 顯示警告 Modal
 *   2. 警告出現後超過 WARN_SECONDS 秒未回應   → 強制登出
 *
 * 監聽事件：mousemove / mousedown / keydown / touchstart / scroll / click
 * 任一事件觸發即重置計時器。
 *
 * 使用方式：
 *   在 MainLayout 中呼叫 useIdleTimeout()，取得 warningVisible / resetTimer
 */

import { useEffect, useRef, useCallback, useState } from 'react'

const IDLE_MINUTES  = 15          // 無操作幾分鐘後顯示警告
const WARN_SECONDS  = 120         // 警告出現後幾秒強制登出
const IDLE_MS       = IDLE_MINUTES * 60 * 1000
const WARN_MS       = WARN_SECONDS * 1000

const ACTIVITY_EVENTS = [
  'mousemove', 'mousedown', 'keydown',
  'touchstart', 'scroll', 'click',
] as const

interface IdleTimeoutReturn {
  /** 警告 Modal 是否可見 */
  warningVisible: boolean
  /** 剩餘秒數（倒數計時用） */
  countdown: number
  /** 使用者點「繼續使用」後呼叫，重置計時器並關閉 Modal */
  resetTimer: () => void
}

export function useIdleTimeout(
  onLogout: () => void,
  enabled = true,
): IdleTimeoutReturn {
  const [warningVisible, setWarningVisible] = useState(false)
  const [countdown, setCountdown]           = useState(WARN_SECONDS)

  const idleTimerRef    = useRef<ReturnType<typeof setTimeout> | null>(null)
  const warnTimerRef    = useRef<ReturnType<typeof setTimeout> | null>(null)
  const countdownRef    = useRef<ReturnType<typeof setInterval> | null>(null)

  const clearAllTimers = useCallback(() => {
    if (idleTimerRef.current)    clearTimeout(idleTimerRef.current)
    if (warnTimerRef.current)    clearTimeout(warnTimerRef.current)
    if (countdownRef.current)    clearInterval(countdownRef.current)
  }, [])

  const startCountdown = useCallback(() => {
    setCountdown(WARN_SECONDS)
    countdownRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          if (countdownRef.current) clearInterval(countdownRef.current)
          return 0
        }
        return prev - 1
      })
    }, 1000)
  }, [])

  const resetTimer = useCallback(() => {
    if (!enabled) return
    clearAllTimers()
    setWarningVisible(false)
    setCountdown(WARN_SECONDS)

    // 重新設定閒置計時器
    idleTimerRef.current = setTimeout(() => {
      setWarningVisible(true)
      startCountdown()

      // 再過 WARN_MS 後強制登出
      warnTimerRef.current = setTimeout(() => {
        onLogout()
      }, WARN_MS)
    }, IDLE_MS)
  }, [enabled, clearAllTimers, startCountdown, onLogout])

  useEffect(() => {
    if (!enabled) return

    // 初始化計時器
    resetTimer()

    // 綁定活動事件
    ACTIVITY_EVENTS.forEach((evt) =>
      window.addEventListener(evt, resetTimer, { passive: true })
    )

    return () => {
      clearAllTimers()
      ACTIVITY_EVENTS.forEach((evt) =>
        window.removeEventListener(evt, resetTimer)
      )
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled])

  return { warningVisible, countdown, resetTimer }
}
