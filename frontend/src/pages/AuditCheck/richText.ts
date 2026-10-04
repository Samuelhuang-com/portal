/**
 * 稽核檢查「查核評語」富文字工具（2026-10-04）
 *
 * 白名單與後端 services/audit_check_html.py 一致：只留排版標籤與排版用 style。
 * 舊資料是純文字（含換行）→ 顯示時轉義後把換行改成 <br>。
 */

const ALLOWED_TAGS = new Set([
  'B', 'STRONG', 'I', 'EM', 'U', 'S', 'STRIKE', 'DEL', 'SPAN', 'FONT', 'BR',
  'P', 'DIV', 'UL', 'OL', 'LI', 'SUB', 'SUP', 'BLOCKQUOTE',
])
const DROP_WITH_CONTENT = new Set(['SCRIPT', 'STYLE', 'HEAD', 'TITLE', 'IFRAME', 'OBJECT', 'NOSCRIPT'])
const ALLOWED_STYLE = [
  'color', 'background-color', 'font-size', 'font-weight', 'font-style',
  'text-decoration', 'text-decoration-line', 'text-align',
]
const SAFE_VALUE = /^[#\w\s.,%()-]+$/

export function isHtml(s: string | null | undefined): boolean {
  return !!s && /<\s*\/?\s*[a-zA-Z][^>]*>/.test(s)
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function cleanNode(node: Node, doc: Document): Node | null {
  if (node.nodeType === Node.TEXT_NODE) return doc.createTextNode(node.textContent ?? '')
  if (node.nodeType !== Node.ELEMENT_NODE) return null
  const el = node as HTMLElement
  const tag = el.tagName.toUpperCase()
  if (DROP_WITH_CONTENT.has(tag)) return null

  const children = Array.from(el.childNodes)
    .map((c) => cleanNode(c, doc))
    .filter((c): c is Node => c != null)

  if (!ALLOWED_TAGS.has(tag)) {
    // 不在白名單的標籤（如 <a>、<img>、Word 貼上的 <o:p>）只留內容
    const frag = doc.createDocumentFragment()
    children.forEach((c) => frag.appendChild(c))
    return frag
  }
  const out = doc.createElement(tag.toLowerCase())
  const styles: string[] = []
  ALLOWED_STYLE.forEach((prop) => {
    const v = el.style?.getPropertyValue(prop)?.trim()
    if (v && SAFE_VALUE.test(v) && !/url|expression/i.test(v)) styles.push(`${prop}: ${v}`)
  })
  if (styles.length) out.setAttribute('style', styles.join('; '))
  if (tag === 'FONT') {
    ;['color', 'size'].forEach((a) => {
      const v = el.getAttribute(a)
      if (v && SAFE_VALUE.test(v)) out.setAttribute(a, v)
    })
  }
  children.forEach((c) => out.appendChild(c))
  return out
}

/** 白名單清理；實質空白（只剩排版標籤）回傳空字串 */
export function sanitizeHtml(html: string | null | undefined): string {
  if (!html) return ''
  if (!isHtml(html)) {
    const t = html.trim()
    return t ? escapeHtml(t).replace(/\r?\n/g, '<br>') : ''
  }
  const doc = new DOMParser().parseFromString(`<body>${html}</body>`, 'text/html')
  const box = doc.createElement('div')
  Array.from(doc.body.childNodes).forEach((c) => {
    const n = cleanNode(c, doc)
    if (n) box.appendChild(n)
  })
  return htmlToPlain(box.innerHTML) ? box.innerHTML : ''
}

/** 轉純文字（判斷是否空白、做摘要用） */
export function htmlToPlain(html: string | null | undefined): string {
  if (!html) return ''
  if (!isHtml(html)) return html.trim()
  const doc = new DOMParser().parseFromString(
    `<body>${html.replace(/<br\s*\/?>/gi, '\n').replace(/<\/(p|div|li)>/gi, '\n')}</body>`,
    'text/html',
  )
  return (doc.body.textContent ?? '').replace(/ /g, ' ').trim()
}

/** 顯示用：舊純文字轉成 HTML；新資料再清一次 */
export function toDisplayHtml(s: string | null | undefined): string {
  return sanitizeHtml(s)
}

/** 富文字顯示區塊共用樣式（矩陣格、手機卡片） */
export const RICH_TEXT_CSS = `
  .audit-rich p, .audit-rich div { margin: 0; }
  .audit-rich ul, .audit-rich ol { margin: 0; padding-left: 18px; }
  .audit-rich blockquote { margin: 0 0 0 12px; padding-left: 8px; border-left: 3px solid #d9d9d9; }
`
