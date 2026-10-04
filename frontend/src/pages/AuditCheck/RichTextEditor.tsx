/**
 * 原生富文字編輯器（2026-10-04）— 稽核檢查「查核評語」用
 *
 * 只用瀏覽器原生 contentEditable + document.execCommand，不引入第三方編輯器套件。
 * 工具列：復原／重做、字級、粗體／斜體／底線／刪除線、文字顏色、螢光底色、
 *         對齊、項目／編號清單、清除格式。Ctrl+B / I / U 等快捷鍵由瀏覽器原生處理。
 * 貼上時先經白名單清理（richText.sanitizeHtml），Word / 網頁貼過來的雜訊會被濾掉。
 * 輸出 HTML；存檔前後端會再清一次（services/audit_check_html.py）。
 */
import { useCallback, useEffect, useRef } from 'react'
import type React from 'react'
import { Button, Divider, Popover, Select, Tooltip } from 'antd'
import {
  AlignCenterOutlined, AlignLeftOutlined, AlignRightOutlined, BoldOutlined, ClearOutlined,
  FontColorsOutlined, HighlightOutlined, ItalicOutlined,
  OrderedListOutlined, RedoOutlined, StrikethroughOutlined, UnderlineOutlined, UndoOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons'

import { sanitizeHtml, toDisplayHtml } from './richText'

// 文字顏色預設色盤：前幾個是系統既有語意色（與網頁稽核單一致）
const TEXT_COLORS = [
  '#262626', '#cf1322', '#1677ff', '#52c41a', '#fa8c16', '#722ed1',
  '#000000', '#8c8c8c', '#d4380d', '#08979c', '#c41d7f', '#1B3A5C',
]
const HIGHLIGHT_COLORS = ['#ffff00', '#fff1b8', '#ffccc7', '#d9f7be', '#bae0ff', '#efdbff']
const FONT_SIZES = [
  { value: '2', label: '小' },
  { value: '3', label: '標準' },
  { value: '4', label: '中' },
  { value: '5', label: '大' },
  { value: '6', label: '特大' },
]

export interface RichTextEditorProps {
  value: string
  onChange: (html: string) => void
  disabled?: boolean
  minHeight?: number
  placeholder?: string
  onKeyDown?: (e: React.KeyboardEvent<HTMLDivElement>) => void
}

export default function RichTextEditor(props: RichTextEditorProps) {
  const { value, onChange, disabled, minHeight = 180, placeholder, onKeyDown } = props
  const ref = useRef<HTMLDivElement>(null)
  const rangeRef = useRef<Range | null>(null)
  const lastEmitted = useRef<string | null>(null)

  // 外部 value 變了（開新格子、上一欄/下一欄）才重設內容，打字時不重設，避免游標亂跳
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (value !== lastEmitted.current) {
      el.innerHTML = toDisplayHtml(value)
      lastEmitted.current = value
    }
  }, [value])

  // 記住編輯區內最後的選取範圍：點顏色、字級等工具列元件會搶走焦點，執行前要還原
  useEffect(() => {
    const onSel = () => {
      const el = ref.current
      const sel = document.getSelection()
      if (!el || !sel || sel.rangeCount === 0) return
      const r = sel.getRangeAt(0)
      if (el.contains(r.commonAncestorContainer)) rangeRef.current = r.cloneRange()
    }
    document.addEventListener('selectionchange', onSel)
    return () => document.removeEventListener('selectionchange', onSel)
  }, [])

  const emit = useCallback(() => {
    const html = ref.current?.innerHTML ?? ''
    lastEmitted.current = html
    onChange(html)
  }, [onChange])

  const exec = (cmd: string, arg?: string) => {
    const el = ref.current
    if (!el || disabled) return
    el.focus()
    const sel = document.getSelection()
    if (rangeRef.current && sel) {
      sel.removeAllRanges()
      sel.addRange(rangeRef.current)
    }
    document.execCommand('styleWithCSS', false, 'true')
    document.execCommand(cmd, false, arg)
    emit()
  }

  const onPaste = (e: React.ClipboardEvent<HTMLDivElement>) => {
    e.preventDefault()
    const html = e.clipboardData.getData('text/html')
    const text = e.clipboardData.getData('text/plain')
    const safe = html
      ? sanitizeHtml(html)
      : text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\r?\n/g, '<br>')
    if (safe) document.execCommand('insertHTML', false, safe)
    emit()
  }

  // 工具列按鈕：onMouseDown 擋掉預設行為，點按鈕時選取範圍不會跑掉
  const tb = (title: string, icon: React.ReactNode, cmd: string, arg?: string) => (
    <Tooltip title={title} mouseEnterDelay={0.4}>
      <Button
        size="small"
        type="text"
        icon={icon}
        disabled={disabled}
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => exec(cmd, arg)}
      />
    </Tooltip>
  )

  const palette = (colors: string[], cmd: 'foreColor' | 'hiliteColor', allowNone: boolean) => (
    <div style={{ width: 168 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 22px)', gap: 6 }}>
        {colors.map((c) => (
          <span
            key={c}
            title={c}
            onMouseDown={(e) => { e.preventDefault(); exec(cmd, c) }}
            style={{
              width: 22, height: 22, borderRadius: 4, background: c, cursor: 'pointer',
              border: '1px solid #d9d9d9', display: 'inline-block',
            }}
          />
        ))}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
        <span style={{ fontSize: 12, color: '#8c8c8c' }}>自訂</span>
        <input type="color" onChange={(e) => exec(cmd, e.target.value)} style={{ width: 36, height: 22, padding: 0, border: 0 }} />
        {allowNone && (
          <Button size="small" type="link" style={{ padding: 0 }} onMouseDown={(e) => e.preventDefault()}
            onClick={() => exec(cmd, 'transparent')}>
            無底色
          </Button>
        )}
      </div>
    </div>
  )

  return (
    <div
      style={{
        border: '1px solid #d9d9d9', borderRadius: 6,
        background: disabled ? '#f5f5f5' : '#fff',
      }}
    >
      {!disabled && (
        <div
          style={{
            display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2,
            padding: '4px 6px', borderBottom: '1px solid #f0f0f0', background: '#fafafa',
            borderRadius: '6px 6px 0 0',
          }}
        >
          {tb('復原', <UndoOutlined />, 'undo')}
          {tb('重做', <RedoOutlined />, 'redo')}
          <Divider type="vertical" style={{ margin: '0 2px' }} />
          <Select
            size="small"
            placeholder="字級"
            style={{ width: 72 }}
            options={FONT_SIZES}
            value={null as string | null}
            onChange={(v: string | null) => { if (v) exec('fontSize', v) }}
          />
          <Divider type="vertical" style={{ margin: '0 2px' }} />
          {tb('粗體 (Ctrl+B)', <BoldOutlined />, 'bold')}
          {tb('斜體 (Ctrl+I)', <ItalicOutlined />, 'italic')}
          {tb('底線 (Ctrl+U)', <UnderlineOutlined />, 'underline')}
          {tb('刪除線', <StrikethroughOutlined />, 'strikeThrough')}
          <Popover trigger="click" content={palette(TEXT_COLORS, 'foreColor', false)}>
            <Tooltip title="文字顏色" mouseEnterDelay={0.4}>
              <Button size="small" type="text" icon={<FontColorsOutlined />} onMouseDown={(e) => e.preventDefault()} />
            </Tooltip>
          </Popover>
          <Popover trigger="click" content={palette(HIGHLIGHT_COLORS, 'hiliteColor', true)}>
            <Tooltip title="螢光底色" mouseEnterDelay={0.4}>
              <Button size="small" type="text" icon={<HighlightOutlined />} onMouseDown={(e) => e.preventDefault()} />
            </Tooltip>
          </Popover>
          <Divider type="vertical" style={{ margin: '0 2px' }} />
          {tb('靠左', <AlignLeftOutlined />, 'justifyLeft')}
          {tb('置中', <AlignCenterOutlined />, 'justifyCenter')}
          {tb('靠右', <AlignRightOutlined />, 'justifyRight')}
          <Divider type="vertical" style={{ margin: '0 2px' }} />
          {tb('項目清單', <UnorderedListOutlined />, 'insertUnorderedList')}
          {tb('編號清單', <OrderedListOutlined />, 'insertOrderedList')}
          <Divider type="vertical" style={{ margin: '0 2px' }} />
          {tb('清除格式', <ClearOutlined />, 'removeFormat')}
        </div>
      )}
      <div
        ref={ref}
        className="audit-rich audit-rich-editor"
        contentEditable={!disabled}
        suppressContentEditableWarning
        data-placeholder={placeholder ?? ''}
        onInput={emit}
        onBlur={emit}
        onPaste={onPaste}
        onKeyDown={onKeyDown}
        style={{
          minHeight, maxHeight: 420, overflowY: 'auto', padding: '8px 11px',
          outline: 'none', fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap',
          wordBreak: 'break-word', cursor: disabled ? 'not-allowed' : 'text',
        }}
      />
      <style>{`
        .audit-rich-editor:empty:before { content: attr(data-placeholder); color: #bfbfbf; }
        .audit-rich p, .audit-rich div { margin: 0; }
        .audit-rich ul, .audit-rich ol { margin: 0; padding-left: 20px; }
        .audit-rich blockquote { margin: 0 0 0 24px; padding: 0; border: 0; }
      `}</style>
    </div>
  )
}
