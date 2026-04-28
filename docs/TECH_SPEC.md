# 技術規格文件 (TECH_SPEC)

> 每次引入新套件、新架構模式、新服務時必須更新此文件。

---

## 版本紀錄

| 版本 | 日期 | 變更摘要 |
|------|------|---------|
| v1.0 | 2026-04-08 | 初始建立，FastAPI + React + SQLite + Ragic 同步架構 |
| v1.1 | 2026-04-09 | 加入 APScheduler 自動同步；加入 recharts 圖表儀表板 |
| v1.2 | 2026-04-09 | 新增倉庫庫存模組（Ragic ragicinventory/20008）|
| v1.3 | 2026-04-09 | Dashboard KPI 總覽：`/dashboard/kpi` 聚合端點、Pie + Bar + Table 視覺化 |
| v1.4 | 2026-04-10 | 客房保養明細模組（ap12 Ragic server、總表 Modal、12 項 X/V 檢查） |
| v1.5 | 2026-04-10 | 客房保養明細強化：Room 主檔（170 間）、日期區間聚合、工時合計、未保養灰底、KPI 可篩選 |
| v1.12 | 2026-04-11 | 導覽文字 SSOT：新增 `navLabels.ts`，Menu/Breadcrumb/Title 統一由此管理 |
| v1.13 | 2026-04-11 | 保養統計 Tab：新增 `GET /api/v1/room-maintenance-detail/maintenance-stats` 端點；前端 `MaintenanceStatsDashboard` 元件（Phase 1+2+3） |
| v1.14 | 2026-04-12 | 週期保養表：`pm_batch` + `pm_batch_item` 雙表；Ragic ap12 同步；`portal_edited_at` 寫入保護；主管儀表板 + 批次清單 + 工單明細 + Drawer 回填 |
| v1.22 | 2026-04-14 | 保全巡檢：`security_patrol_batch` + `security_patrol_item` 統一模型（sheet_key 區分 7 種 Sheet）；動態欄位偵測 Pivot 同步服務；`/api/v1/security/patrol/{sheet_key}/*` + `/api/v1/security/dashboard/*` 路由 |
| v1.24 | 2026-04-15 | 超級行事曆：`calendar_custom_events` 自訂事件表；聚合 API `/api/v1/calendar/events`（整合 6 大模組）；前端引入 `@fullcalendar/react` v6（月/週/日/清單視圖） |
| v1.25 | 2026-04-15 | Dashboard 關聯圖譜：`GET /api/v1/dashboard/graph` 聚合端點；純 SVG Hub-Spoke GraphView 組件；Dashboard ROW 4 嵌入 |
| v1.26 | 2026-04-15 | GraphView 升級為操作流程圖：`@xyflow/react` v12；11 節點 + 8 語意化關係邊；三群組（巡檢/保養/流程）；DB 直接關聯邊（Approval→Memo）|
| v1.33.6 | 2026-04-20 | Ragic 對應表：`ragic_app_portal_annotations` 資料表 + GET/PUT API；前端 `RagicAppDirectory.tsx`（219 筆靜態資料 + 可編輯 Portal 欄位）|
| v1.33.7 | 2026-04-20 | 商場工務每日巡檢本地 DB 化：`mall_fi_inspection_batch` + `mall_fi_inspection_item` 雙表；動態欄位偵測 Pivot；5 張 Sheet 全量同步；`/api/v1/mall-facility-inspection/{sheet_key}/stats|batches|sync` + `/sync/all` + `/dashboard/summary` |
| v1.33.9 | 2026-04-20 | **台灣時區統一**：新增 `app/core/time.py`（`twnow()` helper）；34 個服務/模型/路由檔案由 `datetime.now(timezone.utc)` / `datetime.utcnow` 全面改為 `twnow()`；`TECH_SPEC.md` 新增「Taiwan Time Policy」時區政策規格 |
| v1.34.0 | 2026-04-20 | **Dashboard 主管視角優化**：`BudgetSummaryCard`（P1-E）/ `TodaySummaryCard`（P1-C）新元件；`totalAlerts` 計算擴充工務+預算子項（P1-D）；群組卡一句話結論 helper（P1-B）；Login 頁環境標示 + loading 狀態 + DEV-only bypass（P1-A）；後端零改動，僅呼叫現有 `GET /api/v1/budget/dashboard` |
| v1.39.0 | 2026-04-24 | **IHG 客房保養模組**：`ihg_rm_master` + `ihg_rm_detail` 雙表（Ragic `periodic-maintenance/4`）；多候選欄位 key 自動挑選策略（`_pick()`）；年度保養矩陣 `/matrix`（房號×月份）；KPI `/stats`；`/debug-raw` 欄位結構診斷；Menu 位置：飯店管理→2.IHG客房保養 |
| v1.39.15 | 2026-04-27 | **ExecMetrics 共用元件**：`src/components/ExecMetrics/index.tsx` 抽取 `HeroKpi`/`ExecHeroLayer`/`ExecSourceCards`/`ExecMetricsCard`；Dashboard 頂部以 `ExecMetricsCard` 取代隱藏的 `BudgetSummaryCard`；ExecDashboard 重構使用共用元件，行為不變；補 `CategoryStats.meta.last_sync_at?` 型別 |
| v1.39.17 | 2026-04-28 | **選單管理**：新增 `menu_configs`（key/custom_label/sort_order）+ `menu_config_history`（diff_json/snapshot_json，最多 5 筆）資料表；後端 `routers/menu_config.py`（GET/PUT config, GET history）；前端 `pages/Settings/MenuConfig/index.tsx`（@dnd-kit 拖拉排序 + inline 改名 + 歷史 Drawer）；`MainLayout` 動態載入覆蓋設定，失敗 fallback 預設值；安裝 @dnd-kit/core v6 / @dnd-kit/sortable v10 / @dnd-kit/utilities v3 |
| v1.39.34 | 2026-04-28 | **全棟例行維護**：`full_bldg_pm_batch` + `full_bldg_pm_batch_item` 雙表（Ragic Sheet 21）；`full_building_maintenance_sync.py` 子表格四模式解析；`/api/v1/mall/full-building-maintenance` Router（共用 PM schema）；前端 `FullBuildingMaintenance` 頁 + `fullBuildingMaintenance.ts`；mall menu 重構為三層（mall-pm-group → 商場週期保養 / 商場例行維護 / 全棟例行維護） |

---

## 後端技術棧

| 類別 | 套件 | 版本 | 用途 |
|------|------|------|------|
| Web Framework | FastAPI | 0.111.1 | REST API |
| ASGI Server | uvicorn[standard] | 0.30.1 | 生產伺服器 |
| ORM | SQLAlchemy | 2.0.31 | 資料庫存取（**同步模式**） |
| DB | SQLite | — | 本地快照資料庫 |
| DB Driver | — | — | 原生 sqlite3（非 aiosqlite） |
| Schema | Pydantic v2 | 2.7.4 | 資料驗證 |
| Settings | pydantic-settings | 2.3.4 | `.env` 設定讀取 |
| Auth | PyJWT | 2.8.0 | JWT token 簽發/驗證 |
| Password | passlib[bcrypt] | 1.7.4 | 密碼 hash |
| HTTP Client | httpx | 0.27.0 | 非同步呼叫 Ragic API |
| Scheduler | APScheduler | 3.10.4 | 每 30 分鐘自動同步 |
| Excel | openpyxl + pandas | — | 報表匯出（待實作） |

## 前端技術棧

| 類別 | 套件 | 版本 | 用途 |
|------|------|------|------|
| Framework | React | 18.3.1 | UI |
| Build Tool | Vite | 5.3.3 | 開發/打包 |
| Language | TypeScript | 5.5.3 | 型別安全 |
| UI Library | Ant Design | 5.18.3 | 元件庫 |
| Pro Components | @ant-design/pro-components | 2.7.8 | 進階元件 |
| Routing | React Router DOM | 6.24.1 | SPA 路由 |
| State | Zustand | 4.5.4 | 全域狀態（auth） |
| HTTP | Axios | 1.7.2 | API 呼叫 |
| Charts | recharts | 2.12.7 | 管理圖表儀表板 |
| Calendar | @fullcalendar/react + plugins | 6.1.20 | 超級行事曆月/週/日/清單視圖 |
| Graph | @xyflow/react | 12.10.2 | Dashboard 操作流程關聯圖譜（react-flow v12） |
| Date | dayjs | 1.11.11 | 日期處理 |
| DnD | @dnd-kit/core + sortable + utilities | 6/10/3 | 選單管理拖拉排序 |

---

## 架構模式

### 資料流（客房保養明細）
```
https://ap12.ragic.com/soutlet001/report2/2
    ↓ (每30分鐘 APScheduler / 手動 POST /sync)
room_maintenance_detail_sync.py  ← 中文欄位 key（naming="" 時）
    ↓ upsert
SQLite room_maintenance_detail_records
    ↓ db.query()
room_maintenance_detail router
    ↓ JSON（列表 / 總表聚合）
React Frontend（總表 Modal + X/V Tag 顯示）
```

### 資料流（客房保養）
```
Ragic Cloud API
    ↓ (每30分鐘 APScheduler / 手動 POST /sync)
room_maintenance_sync.py  ←  中文欄位 key（naming="" 時）
    ↓ upsert
SQLite room_maintenance_records
    ↓ db.query()
room_maintenance_service.py
    ↓
FastAPI Router
    ↓ JSON
React Frontend
```

### 認證流
```
POST /auth/login
    → create_access_token(subject=user.id, extra_claims={email, roles})
    → JWT { sub: uuid, email, roles, exp }
    
每個受保護 API →  Bearer token → decode_token → payload.get("sub") → DB lookup
```

### 時區政策（Taiwan Time Policy）

**原則：Portal 系統一律使用台灣時間（UTC+8）進行時間戳記儲存與顯示。**

| 層面 | 做法 |
|------|------|
| **後端儲存** | 所有 `DateTime` 欄位儲存 naive datetime（不含 tz），值代表台灣當地時間（UTC+8） |
| **後端工具函式** | 統一使用 `from app.core.time import twnow`，回傳 `datetime.now(TW_TZ).replace(tzinfo=None)` |
| **JWT exp** | JWT 到期時間例外：繼續使用 UTC（`datetime.now(timezone.utc)`），因 PyJWT 標準 |
| **前端顯示** | 後端回傳的 ISO 字串（無 tz suffix）直接解析顯示，不透過 `new Date()` 以避免 browser UTC 轉換 |
| **前端格式化** | 使用字串正規表示式解析 `YYYY-MM-DDTHH:MM` 格式，輸出 `MM/DD HH:MM`（台灣慣用格式） |
| **例外** | Ragic API 回傳的時間欄位依 Ragic 原始值處理，不做時區換算 |

```python
# ✅ 正確：後端寫入時間
from app.core.time import twnow
record.created_at = twnow()

# ❌ 錯誤：勿直接用 utcnow 或 UTC timezone
from datetime import datetime, timezone
record.created_at = datetime.now(timezone.utc).replace(tzinfo=None)  # 差 8 小時
```

```typescript
// ✅ 正確：前端格式化台灣時間字串（後端已存台灣時間）
const m = iso.match(/(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/)
return `${m[1]}/${m[2]} ${m[3]}:${m[4]}`

// ❌ 錯誤：勿用 new Date(iso)——browser 會將無 tz 的 ISO string 當 UTC 解析
new Date("2026-04-20T20:16:00")  // 實際顯示為 04/21 04:16（UTC+8 轉換後）
```

---

### 重要設計決策

| 決策 | 原因 |
|------|------|
| SQLAlchemy **同步**模式 | 既有 routers 均用 `db.query()` 同步 API |
| Ragic API Key 不做 base64 | Key 已是 base64 格式，再編碼會失敗 |
| JWT sub = user UUID | 早期 bug：傳 dict 進 `create_access_token` 導致 sub 被字串化 |
| SQLite 本地快照 | Ragic 欄位格式不穩定（`"1000006房號"` 複合 key），先 sync 再讀 DB 最穩 |
| 客房保養明細使用不同 Ragic server | 資料在 ap12.ragic.com/soutlet001，與主帳號 ap16 不同；RagicAdapter 支援傳入 server_url & account 覆寫 |
| maintenance-stats 端點置於 /{record_id} 之前 | FastAPI 路由按定義順序匹配；若在 catch-all 之後，"maintenance-stats" 會被誤解析為 record_id 參數 |
| 保養統計採懶載入 | 切換到 Tab 5 時才呼叫 API，避免初次載入多餘請求；與 staff-hours 行為一致 |
| 保全巡檢採統一模型（SecurityPatrolBatch/Item）| 7 張 Sheet 結構相同，以 `sheet_key` 欄位區分，避免重複建立 14 張資料表；PK 格式為 `{sheet_key}_{ragic_row_id}` 防止不同 Sheet 的 ID 衝突 |
| 保全巡檢同步採動態欄位偵測 | Ragic 欄位隨業務調整時無需修改程式碼；僅排除已知場次 metadata 欄位，其餘自動 pivot 成巡檢點 |
| Ragic 對應表靜態清單 + DB 標註分離 | 219 筆 Ragic 應用程式資料在前端靜態嵌入（不需 API），只有 Portal 對應的兩個欄位存 DB；減少 migration 複雜度並讓 Ragic 清單版本由代碼管理 |
| 商場工務巡檢採統一模型（MallFIBatch/Item）| 5 張 Sheet 結構相同，以 `sheet_key` 欄位區分，避免重複建 10 張資料表；PK 格式 `{sheet_key}_{ragic_row_id}` 防衝突；動態欄位偵測與保全巡檢模組保持一致 |

---

## 環境變數（.env）

```env
# 應用
ENV=development
DEBUG=true
SECRET_KEY=...
JWT_SECRET_KEY=...

# Ragic
RAGIC_API_KEY=...
RAGIC_SERVER_URL=ap16.ragic.com
RAGIC_ACCOUNT_NAME=intraragicapp
RAGIC_API_VERSION=2025-01-01
RAGIC_NAMING=
RAGIC_ROOM_MAINTENANCE_PATH=ragicsales-order-management/1

# DB
DATABASE_URL=sqlite:///./portal.db
```

---

## 導覽文字維護指南

> 修改 Menu / Breadcrumb / 頁面 Title 的唯一入口是 `frontend/src/constants/navLabels.ts`。
> 改完後三處自動同步，**不需再分別修改** MainLayout、頁面元件。

### 架構說明

```
frontend/src/constants/navLabels.ts   ← 唯一真相來源（SSOT）
    ├─ SITE_TITLE         → MainLayout Sidebar 標題
    ├─ NAV_GROUP.*        → MainLayout menuItems 一級群組 label
    └─ NAV_PAGE.*         → MainLayout menuItems 二級頁面 label
                             + 各 Page 元件的 <Breadcrumb> / <Title>
```

### 如何修改文字

1. 開啟 `frontend/src/constants/navLabels.ts`
2. 找到對應的 `NAV_GROUP` 或 `NAV_PAGE` 的 **value 值**（右側中文字），直接改
3. **不可改** key 名稱（左側英文），也不可改任何路由相關欄位
4. 存檔後 Vite HMR 熱更新，Menu、Breadcrumb、Title 全部即時同步

**範例**：將「保養管理」改回「客房保養明細」
```ts
// navLabels.ts
roomMaintenanceDetail: '客房保養明細',   // ← 只改這個值
```

### 已接入的頁面元件

| 元件 | 接入欄位 |
|------|---------|
| `MainLayout.tsx` | `SITE_TITLE`、`NAV_GROUP.*`、`NAV_PAGE.*` |
| `pages/RoomMaintenanceDetail/index.tsx` | `NAV_GROUP.hotel`、`NAV_PAGE.roomMaintenanceDetail` |

> 新增頁面時，請在頁面元件中 `import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'`，
> 並將 Breadcrumb / Title 的文字替換為常數，再於上表補記。

### 維護紀錄

| 日期 | 變更內容 |
|------|---------|
| 2026-04-11 | 初始建立；`roomMaintenanceDetail` 從「客房保養明細」改為「保養管理」 |

---

## 新增技術時的更新要求

1. 在上方表格加一行
2. 說明版本號與用途
3. 若影響架構，在「架構模式」補充說明
4. 若有重要設計決策，加入「重要設計決策」表格
