# 超級行事曆（Command Calendar）開發規格書

> 版本：v1.24.0 | 日期：2026-04-15

---

## 一、功能定位

行事曆不是普通月曆，而是 **Portal 事件總覽中心 / 跨模組時間軸中心**。

高階主管打開即可看到：
- 今日有哪些待執行保養、巡檢、待簽核
- 各模組異常 / 逾期一目了然
- 可直接跳轉到原模組明細頁面
- 有顏色分層區分各模組事件類型

---

## 二、頁面資訊架構（IA）

```
/calendar
├── Breadcrumb（首頁 > 行事曆）
├── 頁面標題列（「行事曆」 + 重新整理 + 新增事件）
├── KPI 摘要列（6 個 Statistic 卡片）
│   ├── 今日事件總數
│   ├── 待執行
│   ├── 異常 / 退回
│   ├── 逾期
│   ├── 待簽核（全系統）
│   └── 高風險事件（異常 + 逾期）
├── 事件類型篩選器（CheckableTag 可多選）
│   └── 飯店保養 / 商場保養 / 保全巡檢 / 工務巡檢 / 簽核管理 / 公告牆 / 自訂事件
└── 主體（Row，左 6 / 右 18）
    ├── 今日重點面板（TodayPanel）
    │   └── 依類型分組，各顯示最多 5 筆，點擊開啟抽屜
    └── FullCalendar 主視圖
        ├── 月視圖（dayGridMonth）
        ├── 週視圖（timeGridWeek）
        ├── 日視圖（timeGridDay）
        └── 清單視圖（listMonth）
```

---

## 三、事件資料模型

### 3.1 聚合事件（CalendarEvent）

```typescript
interface CalendarEvent {
  id:           string    // 格式：{type}_{source_id}
  title:        string    // [類型前綴] 事件名稱
  start:        string    // ISO date "2026-04-15"
  end?:         string
  all_day:      boolean
  event_type:   CalendarEventType
  module_label: string    // 顯示用文字
  source_id:    string    // 原模組記錄 ID
  status:       string    // pending | completed | abnormal | overdue
  status_label: string
  responsible:  string    // 負責人
  description:  string    // 補充說明
  deep_link:    string    // React Router 路徑（跳轉連結）
  color:        string    // 顏色 hex
}
```

### 3.2 自訂事件資料表（`calendar_custom_events`）

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | String(36) | UUID 主鍵 |
| title | String(255) | 事件標題 |
| description | Text | 說明 |
| start_date | String(20) | 開始日期 YYYY-MM-DD |
| end_date | String(20) | 結束日期（選填） |
| all_day | Boolean | 是否全天 |
| start_time | String(8) | 開始時間 HH:MM |
| end_time | String(8) | 結束時間 HH:MM |
| color | String(20) | 事件顏色 hex |
| responsible | String(200) | 負責人 |
| created_by | String(100) | 建立者 |
| created_by_id | String(36) | 建立者 user.id |
| created_at / updated_at | DateTime | 時間戳 |

---

## 四、事件類型規格

| 類型 key | 中文標籤 | 顏色 | 資料來源 | 深連結 |
|----------|---------|------|----------|--------|
| `hotel_pm` | 飯店保養 | `#1B3A5C`（品牌主色） | `pm_batch_item.scheduled_date` + `pm_batch.period_month` | `/hotel/periodic-maintenance` |
| `mall_pm` | 商場保養 | `#4BA8E8`（品牌輔色） | `mall_pm_batch_item.scheduled_date` + `mall_pm_batch.period_month` | `/mall/periodic-maintenance` |
| `security` | 保全巡檢 | `#52c41a`（綠） | `security_patrol_batch.inspection_date` | `/security/patrol/{sheet_key}` |
| `inspection` | 工務巡檢 | `#1677ff`（Ant 藍） | `b1f/b2f/rf/b4f_inspection_batch.inspection_date` | `/mall/{floor}-inspection` |
| `approval` | 簽核管理 | `#fa8c16`（橙） | `approvals.submitted_at` | `/approvals/{id}` |
| `memo` | 公告牆 | `#722ed1`（紫） | `memos.created_at` | `/memos/{id}` |
| `custom` | 自訂事件 | `#13c2c2`（青） | `calendar_custom_events` | —（無深連結） |

### 日期格式處理

| 模組 | 日期欄位格式 | 轉換邏輯 |
|------|------------|---------|
| 飯店/商場 PM | `scheduled_date="04/23"` + `period_month="2026/04"` | `period_month[:5] + scheduled_date` → `"2026/04/23"` |
| 保全/工務巡檢 | `inspection_date="2026/04/15"` | `.replace("-","/")`→ `date()` |
| 簽核/公告 | `DateTime` | `.strftime("%Y-%m-%d")` |
| 自訂事件 | `start_date="2026-04-15"` | ISO 直接使用 |

---

## 五、API 規格

### 5.1 聚合事件查詢

```
GET /api/v1/calendar/events
  ?start=2026-04-01   (必填，YYYY-MM-DD)
  ?end=2026-04-30     (必填，YYYY-MM-DD)
  ?types=hotel_pm,mall_pm  (選填，逗號分隔；空=全部)

Response: CalendarEventsResponse
{
  "events": [CalendarEvent...],
  "total": 42
}
```

### 5.2 今日摘要 KPI

```
GET /api/v1/calendar/today

Response: TodaySummary
{
  "today": "2026/04/15",
  "total_events": 12,
  "pending_count": 5,
  "abnormal_count": 2,
  "overdue_count": 1,
  "approval_pending": 3,
  "high_risk_count": 3,
  "event_by_type": {"hotel_pm": 4, "approval": 3, ...}
}
```

### 5.3 自訂事件 CRUD

```
GET    /api/v1/calendar/custom        — 清單（?start= ?end=）
POST   /api/v1/calendar/custom        — 新增（201）
PUT    /api/v1/calendar/custom/{id}   — 更新
DELETE /api/v1/calendar/custom/{id}   — 刪除（204）
```

---

## 六、Menu / Route / Permission 設計

### 6.1 navLabels.ts

```typescript
NAV_GROUP.calendar = '行事曆'          // 在 dashboard 之後、hotel 之前
NAV_PAGE.calendarMain = '行事曆總覽'
```

### 6.2 React Router

```
/calendar  → CalendarPage（單一頁面，視圖切換由 FullCalendar 內部處理）
```

### 6.3 MainLayout Menu Key

```
key: '/calendar'
icon: <CalendarOutlined />
```

### 6.4 Permission Keys（第二階段）

| Key | 說明 |
|-----|------|
| `calendar_view` | 基本瀏覽 |
| `calendar_manage` | 管理自訂事件 |
| `calendar_admin` | 管理所有事件/設定 |

> 第一階段未實作權限控管，預留 Key 供後續擴充。

---

## 七、檔案清單

### 新增檔案

| 檔案路徑 | 說明 |
|---------|------|
| `backend/app/models/calendar_event.py` | CalendarCustomEvent ORM 模型 |
| `backend/app/schemas/calendar.py` | Pydantic 型別定義 |
| `backend/app/routers/calendar.py` | 聚合 API Router |
| `frontend/src/types/calendar.ts` | TypeScript 型別定義 |
| `frontend/src/api/calendar.ts` | API 呼叫函式 |
| `frontend/src/pages/Calendar/index.tsx` | 主頁面（KPI + 篩選器 + FullCalendar）|
| `frontend/src/pages/Calendar/components/TodayPanel.tsx` | 今日重點側邊面板 |
| `frontend/src/pages/Calendar/components/EventDrawer.tsx` | 事件詳情右側抽屜 |
| `docs/CALENDAR_SPEC.md` | 本規格書 |

### 修改檔案

| 檔案路徑 | 修改內容 |
|---------|---------|
| `backend/app/main.py` | 新增 `calendar` router import + `include_router` + `calendar_event` model import |
| `frontend/src/constants/navLabels.ts` | 新增 `NAV_GROUP.calendar`、`NAV_PAGE.calendarMain` |
| `frontend/src/components/Layout/MainLayout.tsx` | 新增 Calendar menu item（CalendarOutlined）|
| `frontend/src/router/index.tsx` | 新增 `/calendar` route |
| `docs/CHANGELOG.md` | 新增 v1.24.0 記錄 |
| `docs/TECH_SPEC.md` | 新增 @fullcalendar 套件 + v1.24 版本紀錄 |
| `README.md` | 更新最後更新日期與最近變更 |
| `frontend/package.json` | 新增 @fullcalendar/* 套件（v6.1.20）|

### 未動檔案（完全不修改）

- 所有現有 models（無欄位改動）
- 所有現有 routers（無修改）
- 所有現有 frontend pages（無修改）
- `.env`、`PROTECTED.md`

---

## 八、DB Migration

**無需手動 Migration。**

`CalendarCustomEvent` 是全新資料表（`calendar_custom_events`），在 `main.py` 的 lifespan 中，`Base.metadata.create_all(bind=engine)` 會自動建立此表，不影響任何既有資料表。

---

## 九、第二階段擴充計畫

| 功能 | 說明 | 優先度 |
|------|------|--------|
| 逾期事件計算 | 飯店/商場 PM 逾期（past month + is_completed=False）整合進 Calendar 事件 | 高 |
| 週/日視圖時間段 | 為保養/巡檢補充 start_time / end_time，讓 timeGrid 視圖有時間條 | 中 |
| 稽核日誌整合 | 新增 `audit` 事件來源 | 中 |
| 權限控管 | `calendar_view` / `calendar_manage` / `calendar_admin` 角色控管 | 中 |
| 事件訂閱 / 提醒 | 事件 N 天前提醒（Email / Portal 通知） | 低 |
| Google Calendar 同步 | 匯出 iCal / 連接 Google Calendar MCP | 低 |

---

## 十、設計原則確認

- ✅ 不修改現有資料表欄位
- ✅ 不使用附件中的舊 DB 連線
- ✅ 顏色系統遵守 PROTECTED.md（新增事件類型色彩不屬於凍結範圍）
- ✅ API 前綴遵守 `/api/v1/`
- ✅ 後端使用 `Depends(get_db)` 同步 Session
- ✅ 前端使用 `@/api/calendar.ts` 封裝，不在元件直接使用 axios
- ✅ Menu / Breadcrumb / Title 遵守 `navLabels.ts` SSOT
- ✅ 不大規模重構既有系統（最小改動）
