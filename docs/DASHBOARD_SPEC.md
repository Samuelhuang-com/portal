# Dashboard 首頁開發規格書

> 版本：v1.26.0｜更新日期：2026-04-15  
> 路徑：`/dashboard`  
> 對應程式：`frontend/src/pages/Dashboard/index.tsx`

---

## 一、頁面定位

| 項目 | 說明 |
|------|------|
| 路由 | `/dashboard`（系統登入後預設首頁） |
| 角色定位 | 集團管理主管「每日開機第一眼」總覽頁 |
| 設計原則 | 三大管理群組（飯店 / 商場 / 保全）一頁看完，異常即時可見，快速進入子模組 |
| 不負責的事 | 詳細圖表、歷史趨勢、明細表格（這些留在各子 Dashboard） |

---

## 二、資料來源（零後端改動）

頁面透過 `Promise.allSettled` 平行呼叫 3 支已存在的 API，任一失敗不阻斷其他群組顯示。

| 變數名 | API 端點 | 用於 |
|--------|---------|------|
| `hotelKpi` | `GET /api/v1/dashboard/kpi` | 飯店客房保養完成率、待處理數、近期同步紀錄 |
| `mallData` | `GET /api/v1/mall/dashboard/summary?target_date=YYYY/MM/DD` | 商場 B1F / B2F / RF 巡檢、本月週期保養 |
| `secData` | `GET /api/v1/security/dashboard/summary?target_date=YYYY/MM/DD` | 保全巡檢 7 Sheet 今日摘要 |

### 衍生計算值

```ts
// 各群組完成率
const mallRate  = mallData?.inspection.completion_rate  ?? 0
const secRate   = secData?.completion_rate_all          ?? 0
const hotelRate = rm?.completion_rate                   ?? 0

// 全域待關注：商場異常 + PM 逾期 + 保全異常 + 客房未完成
const mallAbnormal = (mallData?.inspection.abnormal_items ?? 0)
                   + (mallData?.pm.overdue_items          ?? 0)
const secAbnormal  = secData?.abnormal_items_all ?? 0
const hotelPending = rm?.total_incomplete        ?? 0
const totalAlerts  = mallAbnormal + secAbnormal + hotelPending
```

---

## 三、版面結構

```
┌─ Breadcrumb：首頁 > Dashboard ──────────────────────────────── [PROTECTED] ─┐
│                                                                              │
│  集團管理總覽   2026年04月15日 即時概況                      [重新整理]     │
│                                                                              │
│ ┌──────────────────────────────── ROW 1：KPI 卡片（4欄）──────────────────┐ │
│ │ [商場巡檢完成率] [保全巡檢完成率] [客房保養完成率] [全域待關注件數]     │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ ┌──────────────────────────── ROW 2：三大群組摘要卡（各8欄）──────────────┐ │
│ │ ┌─ 飯店管理 ──────┐ ┌─ 商場管理 ──────────┐ ┌─ 保全管理 ──────────┐  │ │
│ │ │完成率 Progress   │ │B1F / B2F / RF 進度   │ │整體完成率 Progress  │  │ │
│ │ │完成/待排/進行 Tag│ │本月PM 完成/逾期      │ │場次/異常/未查 Tags  │  │ │
│ │ │快速入口 ×3      │ │快速入口 ×5           │ │異常Sheet列表 ≤3條   │  │ │
│ │ └─────────────────┘ └──────────────────────┘ │快速入口 ×3         │  │ │
│ │                                               └────────────────────┘  │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ ┌──────────────────────────── ROW 3：近期同步紀錄（全寬）─────────────────┐ │
│ │ 狀態 / 觸發方式 / 筆數 / 時間 / 說明                                   │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ ┌──────────────────────── ROW 4：模組關聯圖譜 GraphView（全寬）───────────┐ │
│ │ 集團管理（中心）↔ 客房保養 / 週期保養 / 商場巡檢 / 工務巡檢 / 簽核 / 公告│ │
│ │ 連線粗細 = 待辦數；節點色 = 狀態；點擊跳轉；60 秒自動刷新              │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 四、各區塊詳細規格

### ROW 1：KPI 卡片

> **PROTECTED**：4 欄 `<Row>`、`<Card size="small">`、無 `bordered`、左側色帶 4px。

| 卡片 | 主要數字 | 輔助文字 | 色帶顏色邏輯 | 點擊行為 |
|------|---------|---------|------------|---------|
| 商場巡檢完成率 | `mallRate %` | `checked_items / total_items 項已查` | `rateColor(mallRate)` | navigate(`/mall/dashboard`) |
| 保全巡檢完成率 | `secRate %` | `今日 N 場次、異常 N 項` | `rateColor(secRate)` | navigate(`/security/dashboard`) |
| 客房保養完成率 | `hotelRate %` | `completed / total 間已完成` | `rateColor(hotelRate)` | navigate(`/hotel/room-maintenance`) |
| 全域待關注 | `totalAlerts 項` | Tags：商場 N / 保全 N / 客房 N | `>0 → danger，=0 → success` | — |

**完成率顏色函式 `rateColor(rate)`：**

```ts
rate >= 80  → #52c41a（success）
rate >= 50  → #faad14（warning）
rate  < 50  → #cf1322（danger）
```

**背景色對應：**

| 卡片 | background |
|------|-----------|
| 商場巡檢完成率 | `#f6ffed` |
| 保全巡檢完成率 | `#fff7e6` |
| 客房保養完成率 | `#e6f4ff` |
| 全域待關注 | 無（白底） |

---

### ROW 2：飯店管理群組卡

**資料來源：** `hotelKpi.room_maintenance`（型別 `RoomMaintenanceKPI`）

| 元素 | 內容 | 規格 |
|------|------|------|
| 完成率進度條 | `completion_rate %` + Progress Bar | `strokeColor = rateColor(hotelRate)`、`size="small"` |
| 狀態 Tags | 已完成 `completed`、待排程 `pending`、進行中 `in_progress` | `color="success"` / `"warning"` / `"processing"` |
| 快速入口 | 客房保養 → `/hotel/room-maintenance`<br>保養明細 → `/hotel/room-maintenance-detail`<br>週期保養表 → `/hotel/periodic-maintenance` | `QuickLink` 元件，藍底連結 |
| 資料失敗 | 顯示灰色提示文字 | 不阻斷整頁渲染 |

---

### ROW 2：商場管理群組卡

**資料來源：** `mallData.inspection`（型別 `InspectionSummary`）+ `mallData.pm`（型別 `PMSummary`）

| 元素 | 內容 | 規格 |
|------|------|------|
| 樓層進度列 | 動態渲染 `inspection.by_floor` 陣列（B1F / B2F / RF） | 每列：樓層標籤 + Progress Bar + 完成率 % + 異常 Tag |
| 樓層進度條 | 漸層 `{ '0%': #4BA8E8, '100%': #52c41a }` | `size="small"` |
| 異常 Tag | 僅在 `abnormal_items > 0` 時顯示 | `color="error"` |
| PM 摘要 | `完成 completed_items / total_items` + 逾期數 | 逾期僅在 `overdue_items > 0` 顯示 |
| 快速入口 | 商場 Dashboard、B1F 巡檢、B2F 巡檢、RF 巡檢、週期保養 | 5 個 QuickLink |

---

### ROW 2：保全管理群組卡

**資料來源：** `secData`（型別 `SecurityDashboardSummary`）

| 元素 | 內容 | 規格 |
|------|------|------|
| 整體完成率 | `completion_rate_all %` + Progress Bar | `strokeColor = rateColor(secRate)` |
| 統計 Tags | 場次 `total_batches_all`、異常 `abnormal_items_all`、未查 `total_items_all - checked_items_all` | `color="blue"` / `"error"` / `"default"` |
| 異常 Sheet 列表 | `secData.sheets.filter(s => s.has_data && (s.abnormal_items > 0 || s.unchecked_items > 0)).slice(0, 3)` | 顯示 Sheet 簡稱（去除「保全巡檢 - 」前綴）+ 異常/未查 Tag |
| 快速入口 | 保全 Dashboard → `/security/dashboard`<br>B1F~B4F → `/security/patrol/b1f-b4f`<br>1F~3F → `/security/patrol/1f-3f` | 3 個 QuickLink |

---

### ROW 3：近期同步紀錄

**資料來源：** `hotelKpi.system.recent_syncs`（型別 `SyncRecord[]`）

| 欄位 | 顯示邏輯 |
|------|---------|
| 狀態 | `SyncBadge` 元件：`success/error/running/partial → Badge status + 文字` |
| 觸發方式 | `scheduler → 排程`、`manual → 手動`、`api → API` |
| 筆數 | `records_fetched`，null 時顯示 `—` |
| 時間 | `dayjs(started_at).fromNow()`；Tooltip 顯示完整時間 |
| 說明 | `error_msg`，有值時以紅字顯示 |
| 卡片 Extra | 最後同步時間（fromNow 格式），Tooltip 完整時間 |

---

## 五、共用元件

### `rateColor(rate: number): string`
完成率轉顏色的純函式，全頁一致使用。

### `SyncBadge({ status })`
同步狀態 Badge，status 字串映射至 Ant Design Badge 顏色。

### `QuickLink({ label, onClick })`
快速入口連結樣式，藍底 `#e6f4ff`、accent 文字 `#4BA8E8`、圓角 4px。

### `GroupCardTitle({ icon, label, color })`
群組卡片標題，icon + 文字，固定品牌色。

---

## 六、凍結規格（來自 PROTECTED.md）

以下設計不得自行修改：

| 規格項目 | 凍結值 |
|---------|-------|
| KPI 卡欄數 | 4 欄 `<Row>`，`<Col xs={24} sm={12} lg={6}>` |
| KPI Card 規格 | `size="small"`、`bordered={false}` |
| 品牌主色 | `#1B3A5C` |
| 品牌輔色 | `#4BA8E8` |
| Breadcrumb | 每頁頂部，不可移除 |
| 已完成顏色 | `#52c41a` |
| 進行中顏色 | `#1677ff` |
| 待排程顏色 | `#faad14` |
| 非本月顏色 | `#8c8c8c` |
| 危險色 | `#cf1322` |

---

## 七、狀態管理

```ts
// 三個互相獨立的 state，任一失敗不影響其他
const [hotelKpi,  setHotelKpi]  = useState<DashboardKPI | null>(null)
const [mallData,  setMallData]  = useState<MallSummary | null>(null)
const [secData,   setSecData]   = useState<SecurityDashboardSummary | null>(null)
const [loading,   setLoading]   = useState(true)
const [refreshed, setRefreshed] = useState<Date>(new Date())
```

- 載入中：全頁 `<Spin size="large">`
- 個別群組載入失敗：顯示灰色提示文字，其他群組正常呈現
- 手動重整：點擊「重新整理」按鈕重新呼叫 `loadAll()`

---

## 八、未來擴充指引

> 如需在首頁新增第四個管理群組（例如：倉庫管理），請遵循以下原則：

1. 在 `loadAll()` 的 `Promise.allSettled` 中新增一個 API 呼叫
2. 新增對應的 `useState`
3. ROW 2 改為 4 欄（`<Col xs={24} sm={12} lg={6}>`）或拆成兩 Row
4. ROW 1 KPI 卡若需新增，須同步調整 4 欄邏輯（可改為 5 欄換行，或合併現有卡）
5. 不得引入新的外部套件
6. 不得改動 `navLabels.ts` 的 key 值

---

## 九、相關檔案索引

| 檔案 | 說明 |
|------|------|
| `frontend/src/pages/Dashboard/index.tsx` | 本頁主程式（ROW 1–4） |
| `frontend/src/components/GraphView/index.tsx` | ROW 4 關聯圖譜組件（純 SVG，NEW v1.25） |
| `frontend/src/api/dashboard.ts` | `dashboardApi.kpi()` + TypeScript 型別 |
| `frontend/src/api/dashboardGraph.ts` | `fetchDashboardGraph()` + GraphView 型別（NEW v1.25） |
| `frontend/src/api/mallDashboard.ts` | `fetchDashboardSummary()` |
| `frontend/src/api/securityPatrol.ts` | `fetchSecurityDashboardSummary()` |
| `frontend/src/types/mallDashboard.ts` | `DashboardSummary`、`InspectionSummary`、`PMSummary` |
| `frontend/src/types/securityPatrol.ts` | `SecurityDashboardSummary`、`SheetStats` |
| `frontend/src/constants/navLabels.ts` | 所有導覽文字 SSOT（只讀，不修改） |
| `frontend/src/router/index.tsx` | 路由設定（不修改） |
| `backend/app/routers/dashboard.py` | `GET /api/v1/dashboard/kpi` + `GET /api/v1/dashboard/graph`（NEW v1.25） |
| `backend/app/routers/mall_dashboard.py` | `GET /api/v1/mall/dashboard/summary` |
| `backend/app/routers/security_dashboard.py` | `GET /api/v1/security/dashboard/summary` |
| `docs/PROTECTED.md` | 凍結設計規格 |

---

## 十、ROW 4 — 關聯圖譜 GraphView（v1.26 升級）

### 10.1 設計理念

原 Hub-Spoke 無業務意義，v1.26 改為「**操作流程鏈**」：

```
[巡檢作業] ──異常觸發──→ [保養作業] ──異常升級──→ [流程管理]
                                                  （簽核 → 公告）
```

### 10.2 套件

**`@xyflow/react` v12.10.2**（react-flow）

| 特性 | 說明 |
|------|------|
| 純 React/SVG | 與 Ant Design 無衝突 |
| TypeScript native | 型別完整 |
| 自訂節點 | 用 React 組件渲染節點（可套用 AntD 樣式）|
| 自訂邊 | `getBezierPath` + `EdgeLabelRenderer` |
| 互動 | 內建 zoom、pan、drag；Controls、MiniMap |

### 10.3 API 規格

**端點：** `GET /api/v1/dashboard/graph`

**Response 結構：**

```json
{
  "groups": [
    { "id": "inspection",  "label": "巡檢作業", "color": "#4BA8E8" },
    { "id": "maintenance", "label": "保養作業", "color": "#52c41a" },
    { "id": "workflow",    "label": "流程管理", "color": "#722ed1" }
  ],
  "nodes": [...],   // 13 個
  "edges": [...],   // 10 條
  "meta": { "generated_at": "...", "total_alerts": 8 }
}
```

### 10.4 節點定義（13 個）

| 節點 ID | 模組名稱 | 群組 | alert 計數邏輯 |
|---------|---------|------|--------------|
| `b1f_insp` | B1F 商場巡檢 | inspection | `B1FInspectionItem.abnormal_flag=True` |
| `b2f_insp` | B2F 商場巡檢 | inspection | `B2FInspectionItem.abnormal_flag=True` |
| `rf_insp` | RF 商場巡檢 | inspection | `RFInspectionItem.abnormal_flag=True` |
| `b4f_insp` | B4F 工務巡檢 | inspection | `B4FInspectionItem.abnormal_flag=True` |
| `security` | 保全巡檢 | inspection | `SecurityPatrolItem.abnormal_flag=True` |
| `mall_facility` | 商場工務巡檢 | inspection | 固定 0（Ragic 直連，無本地 DB） |
| `full_building` | 整棟巡檢 | inspection | 固定 0（Ragic 直連，無本地 DB） |
| `hotel_room` | 客房保養 | maintenance | 待排程 + 進行中 數量 |
| `hotel_pm` | 飯店週期保養 | maintenance | 逾期未完成 + `abnormal_flag=True` |
| `mall_pm` | 商場週期保養 | maintenance | 逾期未完成 + `abnormal_flag=True` |
| `approval` | 簽核管理 | workflow | `Approval.status='pending'` |
| `memo` | 公告備忘 | workflow | 近 7 天新增數（僅顯示，不算 total_alerts） |

### 10.5 關係邊定義（10 條）

| 邊 ID | 來源 → 目標 | 類型 | 視覺 | 觸發條件 |
|------|-----------|------|------|---------|
| e_b1f_mallpm | B1F → 商場PM | anomaly | 紅虛線 | B1F 異常數 |
| e_b2f_mallpm | B2F → 商場PM | anomaly | 紅虛線 | B2F 異常數 |
| e_rf_mallpm | RF → 商場PM | anomaly | 紅虛線 | RF 異常數 |
| e_b4f_hotelpm | B4F → 飯店PM | anomaly | 紅虛線 | B4F 異常數 |
| e_mf_mallpm | 商場工務巡檢 → 商場PM | anomaly | 紅虛線 | Ragic 直連（weight=1） |
| e_fb_hotelpm | 整棟巡檢 → 飯店PM | anomaly | 紅虛線 | Ragic 直連（weight=1） |
| e_sec_appr | 保全 → 簽核 | escalation | 橙虛線 | 保全異常數 |
| e_hpm_appr | 飯店PM → 簽核 | escalation | 橙虛線 | PM逾期+異常數 |
| e_mpm_appr | 商場PM → 簽核 | escalation | 橙虛線 | PM逾期+異常數 |
| e_appr_memo | 簽核 → 公告 | **workflow** | **紫實線+動畫** | `Memo.source='approval'`（**DB直接關聯**） |

> `workflow` 邊（e_appr_memo）是唯一的 DB 外鍵關聯，其餘為業務邏輯。

### 10.6 狀態色彩（PROTECTED）

| 狀態 | 條件 | 顏色 |
|------|------|------|
| `normal` | alert = 0 | `#52c41a` |
| `warning` | alert 1–4 | `#faad14` |
| `danger` | alert ≥ 5 | `#cf1322` |

### 10.7 靜態 Layout（節點位置）

```
Col 1 (x=0):   巡檢（7 節點，y=0~615）
Col 2 (x=300): 保養（3 節點，y=0~285）
Col 3 (x=590): 流程（2 節點，y=145~285）
容器高度：720px（v1.28.1 升級，原 540px）
```

### 10.8 互動行為

| 動作 | 效果 |
|------|------|
| Hover 節點 | scale 1.04 + drop-shadow |
| Click 節點 | `navigate(node.path)` |
| workflow 邊 | 動畫流動（`animated: true`）|
| 邊線寬 | `min(4, max(1.5, weight × 0.6))` |
| 60s 計時器 | `fetchDashboardGraph()`，靜默失敗 |
| MiniMap | 右下角節點狀態色縮覽 |
| Controls | 左下角縮放 / 置中 |
| Panel（圖例）| 左上角群組色例 + 邊類型說明 |

### 10.9 第二階段擴充計劃

| 功能 | 說明 | 優先度 |
|------|------|-------|
| 人員節點 | 誰的待辦最集中，連線到對應模組 | 中 |
| 客房保養→飯店PM 邊 | 客房異常觸發週期保養工單 | 高 |
| 獨立路由 | `/dashboard/graph` 全螢幕（抽組件即可） | 低 |
| Tooltip 時間戳 | Hover 顯示最近異常/更新時間 | 中 |
