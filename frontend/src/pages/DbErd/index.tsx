/**
 * 資料庫 ERD 頁（系統管理員）
 * 內容為靜態互動式 HTML：frontend/public/portal_erd.html（由 backend/app/models 解析產生，只含結構、不含資料）。
 * 路由：/settings/erd
 * 「全畫面」以瀏覽器 Fullscreen API 讓整個 ERD 區塊填滿螢幕（Esc 或按鈕可離開）。
 */
import { useEffect, useRef, useState } from 'react'
import { Button } from 'antd'
import { FullscreenOutlined, FullscreenExitOutlined } from '@ant-design/icons'

export default function DbErdPage() {
  const boxRef = useRef<HTMLDivElement>(null)
  const [isFs, setIsFs] = useState(false)

  useEffect(() => {
    const onChange = () => setIsFs(document.fullscreenElement === boxRef.current)
    document.addEventListener('fullscreenchange', onChange)
    return () => document.removeEventListener('fullscreenchange', onChange)
  }, [])

  const toggleFs = () => {
    if (document.fullscreenElement) {
      document.exitFullscreen()
    } else {
      boxRef.current?.requestFullscreen().catch(() => {})
    }
  }

  return (
    <div
      ref={boxRef}
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: isFs ? '100vh' : 'calc(100vh - 140px)',
        minHeight: isFs ? undefined : 600,
        background: '#fff',
        borderRadius: isFs ? 0 : 8,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '6px 8px', borderBottom: '1px solid #f0f0f0' }}>
        <Button
          size="small"
          icon={isFs ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
          onClick={toggleFs}
        >
          {isFs ? '離開全畫面' : '全畫面'}
        </Button>
      </div>
      <iframe
        src="/portal_erd.html"
        title="Portal 資料庫 ERD"
        style={{ flex: 1, minHeight: 0, width: '100%', border: 0 }}
      />
    </div>
  )
}
