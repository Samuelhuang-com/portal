/**
 * 週採公司切換器（多公司隔離）
 * - 只列出目前使用者可見的公司（後端 GET /cycle-purchase/companies）
 * - 切換時記住公司（sessionStorage）並把 co 寫入網址、整頁導向，確保所有資料重新以新公司載入
 * - 2026-11-17：顯示值與 API 都以「網址 co → 記住的公司」為準，點側邊選單換頁（網址 co 消失）
 *   後下拉仍顯示目前公司、資料也維持同一公司，不用重選。
 */
import { useEffect, useState } from 'react'
import { Select } from 'antd'
import apiClient, { getCpCompany, setCpCompany } from '@/api/client'

interface VisibleCompanies {
  current: string
  companies: { code: string; name: string }[]
}

export default function CycleCompanySwitcher() {
  const [data, setData] = useState<VisibleCompanies | null>(null)

  useEffect(() => {
    apiClient
      .get<VisibleCompanies>('/cycle-purchase/companies')
      .then((r) => {
        setData(r.data)
        // 後端實際採用的公司就是目前公司；與記住的不同（例如已無權限被退回預設）就校正
        setCpCompany(r.data.current)
      })
      .catch(() => {
        // 記住的公司已無權限（403）→ 清掉重載，退回預設公司
        if (getCpCompany()) {
          setCpCompany(null)
          const url = new URL(window.location.href)
          url.searchParams.delete('co')
          window.location.href = url.toString()
        }
        setData(null)
      })
  }, [])

  if (!data || data.companies.length === 0) return null

  return (
    <Select
      size="small"
      style={{ minWidth: 140 }}
      value={new URLSearchParams(window.location.search).get('co') || getCpCompany() || data.current}
      options={data.companies.map((c) => ({ value: c.code, label: c.name }))}
      onChange={(code: string) => {
        setCpCompany(code)
        const url = new URL(window.location.href)
        url.searchParams.set('co', code)
        window.location.href = url.toString()
      }}
    />
  )
}
