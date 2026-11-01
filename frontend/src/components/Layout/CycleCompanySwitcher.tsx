/**
 * 週採公司切換器（多公司隔離）
 * - 只列出目前使用者可見的公司（後端 GET /cycle-purchase/companies）
 * - 切換時把 co 寫入網址並整頁導向，確保所有資料重新以新公司載入
 */
import { useEffect, useState } from 'react'
import { Select } from 'antd'
import apiClient from '@/api/client'

interface VisibleCompanies {
  current: string
  companies: { code: string; name: string }[]
}

export default function CycleCompanySwitcher() {
  const [data, setData] = useState<VisibleCompanies | null>(null)

  useEffect(() => {
    apiClient
      .get<VisibleCompanies>('/cycle-purchase/companies')
      .then((r) => setData(r.data))
      .catch(() => setData(null))
  }, [])

  if (!data || data.companies.length === 0) return null

  return (
    <Select
      size="small"
      style={{ minWidth: 140 }}
      value={data.current}
      options={data.companies.map((c) => ({ value: c.code, label: c.name }))}
      onChange={(code: string) => {
        const url = new URL(window.location.href)
        url.searchParams.set('co', code)
        window.location.href = url.toString()
      }}
    />
  )
}
