/**
 * 庫存管理共用：公司選擇（依 stock_company_<代碼> 權限，後端 /stock/companies 回傳可見公司）
 * 選擇記在 sessionStorage（stock_co），在庫存各頁間切換不用重選。
 */
import { useEffect, useState } from 'react'
import { Select, message } from 'antd'
import { fetchStockCompanies, errMsg, type StockCompany } from '@/api/stock'

const KEY = 'stock_co'

export function useStockCompany() {
  const [companies, setCompanies] = useState<StockCompany[]>([])
  const [code, setCodeState] = useState<string>('')
  const [error, setError] = useState<string>('')

  useEffect(() => {
    fetchStockCompanies()
      .then((res) => {
        const list = res.data.companies
        setCompanies(list)
        let saved = ''
        try { saved = sessionStorage.getItem(KEY) || '' } catch { /* 無痕模式等情況 */ }
        setCodeState(list.some((c) => c.code === saved) ? saved : res.data.default)
      })
      .catch((e) => {
        const m = errMsg(e, '讀取可見公司失敗')
        setError(m)
        message.error(m)
      })
  }, [])

  const setCode = (c: string) => {
    setCodeState(c)
    try { sessionStorage.setItem(KEY, c) } catch { /* ignore */ }
  }
  return { companies, code, setCode, error }
}

export default function StockCompanySelect({ companies, value, onChange }: {
  companies: StockCompany[]; value: string; onChange: (v: string) => void
}) {
  return (
    <Select style={{ width: 120 }} value={value || undefined} onChange={onChange} placeholder="公司別"
      options={companies.map((c) => ({ value: c.code, label: c.name }))} />
  )
}
