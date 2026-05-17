import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',   // 明確 IPv4，避免 Windows 11 解析成 ::1
        changeOrigin: true,
      },
      '/kg-files': {
        target: 'http://127.0.0.1:8000',   // 知識圖譜靜態輸出目錄
        changeOrigin: true,
      },
      '/docs-static': {
        target: 'http://127.0.0.1:8000',   // portal/docs/ 靜態說明文件
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 4173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/kg-files': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/docs-static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
