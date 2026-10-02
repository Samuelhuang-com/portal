// 全站連結游標提示（Sample，尚未接入 App.tsx）
// 用法：在 App.tsx 的 <BrowserRouter> 內加一行 <CursorHint />
// 個別元素可加 data-cursor-hint="開啟 Ragic" 自訂文字；data-cursor-hint="off" 可排除。
import { useEffect, useRef } from 'react'
import './CursorHint.css'

type Props = {
  /** auto：所有連結都顯示；optin：只顯示標了 data-cursor-hint 的元素 */
  mode?: 'auto' | 'optin'
  /** bang：只顯示 !；text：! + 文字 */
  variant?: 'bang' | 'text'
  defaultText?: string
}

const AUTO = 'a[href], .ant-btn-link, .ant-typography a, [data-cursor-hint]'
const OPTIN = '[data-cursor-hint]'

export default function CursorHint({ mode = 'auto', variant = 'bang', defaultText = '點擊前往' }: Props) {
  const boxRef = useRef<HTMLDivElement>(null)
  const txtRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (window.matchMedia('(pointer: coarse)').matches) return // 手機/平板不顯示
    const box = boxRef.current!, txt = txtRef.current!
    const selector = mode === 'auto' ? AUTO : OPTIN
    let current: Element | null = null, x = 0, y = 0, raf = 0

    const place = () => { raf = 0; box.style.transform = `translate(${x + 14}px, ${y + 14}px)` }
    const onMove = (e: MouseEvent) => {
      x = e.clientX; y = e.clientY
      let el = (e.target as Element)?.closest?.(selector) ?? null
      if (el?.getAttribute('data-cursor-hint') === 'off' || el?.closest('[disabled], .ant-btn-disabled')) el = null
      if (el !== current) {
        current = el
        if (el) { txt.textContent = el.getAttribute('data-cursor-hint') || defaultText; box.classList.add('on') }
        else box.classList.remove('on')
      }
      if (current && !raf) raf = requestAnimationFrame(place)
    }
    const hide = () => { current = null; box.classList.remove('on') }

    document.addEventListener('mousemove', onMove, { passive: true })
    document.addEventListener('mouseleave', hide)
    window.addEventListener('blur', hide)
    return () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseleave', hide)
      window.removeEventListener('blur', hide)
      cancelAnimationFrame(raf)
    }
  }, [mode, defaultText])

  return (
    <div ref={boxRef} className="cursor-hint" data-variant={variant} aria-hidden="true">
      <span className="cursor-hint__bang">!</span>
      <span ref={txtRef} className="cursor-hint__txt" />
    </div>
  )
}
