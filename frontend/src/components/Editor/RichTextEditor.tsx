/**
 * RichTextEditor — 共用富文字編輯器
 *
 * 使用 react-quill-new（React 18 相容的 Quill.js fork）
 * 圖片上傳：POST /api/v1/upload/image → 取得 URL 後插入編輯器
 */
import { useCallback, useMemo, useRef } from 'react'
import ReactQuill from 'react-quill-new'
import 'react-quill-new/dist/quill.snow.css'
import { message } from 'antd'
import axios from 'axios'

interface RichTextEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  minHeight?: number
  readOnly?: boolean
}

/**
 * 自訂圖片上傳處理：
 * 讓使用者選取圖片後上傳至後端，取得 URL 再插入 editor
 */
function useImageHandler(quillRef: React.RefObject<ReactQuill | null>) {
  return useCallback(() => {
    const input = document.createElement('input')
    input.setAttribute('type', 'file')
    input.setAttribute('accept', 'image/*')
    input.click()

    input.onchange = async () => {
      const file = input.files?.[0]
      if (!file) return

      const formData = new FormData()
      formData.append('file', file)

      try {
        const token = localStorage.getItem('token') ?? ''
        const res = await axios.post<{ url: string }>(
          '/api/v1/upload/image',
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
              Authorization: `Bearer ${token}`,
            },
          }
        )
        const url = res.data.url
        const quill = quillRef.current?.getEditor()
        if (!quill) return
        const range = quill.getSelection(true)
        quill.insertEmbed(range.index, 'image', url)
        quill.setSelection(range.index + 1, 0)
      } catch {
        message.error('圖片上傳失敗，請稍後再試')
      }
    }
  }, [quillRef])
}

export default function RichTextEditor({
  value,
  onChange,
  placeholder = '請輸入內容…',
  minHeight = 280,
  readOnly = false,
}: RichTextEditorProps) {
  const quillRef = useRef<ReactQuill | null>(null)
  const imageHandler = useImageHandler(quillRef)

  const modules = useMemo(
    () => ({
      toolbar: {
        container: [
          [{ header: [1, 2, 3, false] }],
          ['bold', 'italic', 'underline', 'strike'],
          [{ color: [] }, { background: [] }],
          [{ list: 'ordered' }, { list: 'bullet' }],
          [{ indent: '-1' }, { indent: '+1' }],
          [{ align: [] }],
          ['blockquote', 'code-block'],
          ['link', 'image'],
          ['clean'],
        ],
        handlers: {
          image: imageHandler,
        },
      },
      clipboard: { matchVisual: false },
    }),
    [imageHandler]
  )

  const formats = [
    'header',
    'bold', 'italic', 'underline', 'strike',
    'color', 'background',
    'list', 'bullet', 'indent',
    'align',
    'blockquote', 'code-block',
    'link', 'image',
  ]

  return (
    <div
      style={{
        borderRadius: 6,
        overflow: 'hidden',
      }}
    >
      <ReactQuill
        ref={quillRef}
        theme="snow"
        value={value}
        onChange={onChange}
        modules={modules}
        formats={formats}
        placeholder={placeholder}
        readOnly={readOnly}
        style={{ minHeight }}
      />
      <style>{`
        /* 讓 Quill editor 區域有最小高度 */
        .ql-container { font-size: 14px; }
        .ql-editor { min-height: ${minHeight - 42}px; }
        .ql-toolbar { border-top-left-radius: 6px; border-top-right-radius: 6px; }
        .ql-container { border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; }
      `}</style>
    </div>
  )
}
