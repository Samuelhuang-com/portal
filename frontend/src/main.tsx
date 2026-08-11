import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import zhTW from 'antd/locale/zh_TW'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-tw'
import App from './App'
import { loadSiteConfig } from './config/siteConfig'
import './index.css'

dayjs.locale('zh-tw')

// 先載入站台執行期設定（public/config.json）再掛載，避免品牌名稱先顯示預設值再跳動。
// loadSiteConfig() 內部已吞掉所有錯誤並退回預設值，故此處不需 catch。
loadSiteConfig().then(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <ConfigProvider
        locale={zhTW}
        theme={{
          token: {
            colorPrimary: '#1677ff',
            borderRadius: 6,
            fontFamily:
              '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans TC", sans-serif',
          },
        }}
      >
        <App />
      </ConfigProvider>
    </React.StrictMode>,
  )
})
