# 受保護設計規格 — 未經明確指示，禁止修改

> ⚠️ 此文件定義的所有規格屬於「凍結設計」。
> 如需修改，使用者必須明確說明「請修改 XXX 為 YYY」。
> 不得因為「看起來更好」或「更現代」等理由自行調整。

---

## 一、色彩系統

| 用途 | 變數 / 說明 | 值 |
|------|------------|-----|
| 品牌主色 | Primary blue | `#1B3A5C` |
| 品牌輔色 | Accent blue | `#4BA8E8` |
| Sidebar 背景 | Dark sidebar | `#111827` |
| 頁面背景 | Content bg | `#f0f4f8` |
| 成功色 | Green | `#52c41a` |
| 危險色 | Red | `#cf1322` |
| 警告色 | Orange | `#faad14` |
| 未完成附表底色 | Red tint | `#fff5f5` |
| 未完成附表框線 | Red border | `#ffccc7` |

## 二、排版與尺寸

| 元素 | 規格 |
|------|------|
| Sidebar 寬度（展開） | `220px` |
| Sidebar 寬度（收合） | `64px` 或 `80px` |
| Header 高度 | `56px` |
| 頁面內距 | `padding: 24px` |
| Logo 圓角 | `border-radius: 8px` |

## 三、元件設計

| 元件 | 凍結規格 |
|------|---------|
| KPI 卡片 | 4 欄、`Card size="small"`、無 border |
| 主表格 | `Table size="middle"`、`scroll={{ x: 1400 }}` |
| 未完成附表 | 橙紅漸層標題列 `linear-gradient(135deg, #c0392b, #e74c3c, #e67e22)` |
| 圖表按鈕 | 紫色漸層 `linear-gradient(135deg, #667eea, #764ba2)` |
| Breadcrumb | 每頁頂部，不可移除 |

## 四、工作狀態顏色映射

```typescript
// 此映射禁止修改（影響圖表與列表一致性）
'已完成檢視及保養': { color: 'success', hex: '#52c41a' }
'非本月排程':       { color: 'default', hex: '#8c8c8c' }
'進行中':           { color: 'processing', hex: '#1677ff' }
'待排程':           { color: 'warning', hex: '#faad14' }
```

## 五、API 路由前綴

| 路由前綴 | 說明 |
|---------|------|
| `/api/v1/auth` | 認證 |
| `/api/v1/users` | 使用者管理 |
| `/api/v1/tenants` | 據點 |
| `/api/v1/room-maintenance` | 客房保養 |
| `/api/v1/ragic` | Ragic 原始 API |
| `/api/v1/dashboard` | Dashboard |

## 六、資料庫規則

- 主資料庫：SQLite，路徑 `backend/portal.db`
- 客房保養快照表：`room_maintenance_records`
- **不得變更已存在欄位名稱**（會破壞歷史資料）
- 新增欄位須給 `nullable=True` 或 `default` 值

## 七、Ragic 連線規格

- Server：`ap16.ragic.com`
- Account：`intraragicapp`
- API Key：從 `.env` 讀取，不得 hardcode
- Auth header：`Basic {api_key}`（不做二次 base64 編碼）
- Naming 參數：`naming=`（空值，Ragic 回傳中文欄位標籤）
