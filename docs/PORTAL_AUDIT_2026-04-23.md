# Portal 專案理解與盤點報告

> 盤點日期：2026-04-23  
> 目標站台：http://127.0.0.1:5173/  
> 執行方式：實際網站畫面 + 專案程式碼雙向分析  
> 範圍：唯讀盤點，未修改程式碼

---

## 一句話總評

這個 portal 已經是「維春集團跨飯店、商場、保全、工務、預算」的營運管理總覽平台，但目前最大風險是權限邊界不一致、Dashboard 資訊過多且數字口徑說明不足、部分模組 API 與元件架構仍有重複與歷史債。

---

## A. 系統定位總結

這是維春集團內部管理 Portal，核心用途是把 Ragic 上的營運資料同步到本地 SQLite，再用 React Dashboard 呈現給主管與作業人員。

主要涵蓋預算管理、飯店客房保養、飯店/商場週期保養、商場巡檢、保全巡檢、樂群/大直工務報修、簽核、公告與行事曆。

主管使用首頁 Dashboard 看全域 KPI、待關注項目、預算風險、工務未結案與巡檢異常。

作業人員使用各模組頁進行查詢、明細追蹤、同步 Ragic、查看批次或工單。

資料來源大多是 Ragic 經同步服務落地到 `backend/portal.db`，預算模組則使用獨立 `backend/budget_system_v1.sqlite`。

前端已用 Vite proxy 把 `/api/v1` 轉到 FastAPI。

整體功能完整，但選單、權限、資料口徑與模組命名需要再整理成更像正式營運系統。

---

## B. 功能地圖

```text
/
├─ /login：登入頁，帳密登入，DEV 顯示略過認證按鈕
├─ /dashboard：集團管理總覽，高階主管首頁
├─ /budget
│  ├─ /dashboard：預算總覽、執行率、超支、資料品質
│  ├─ /plans：預算主表
│  ├─ /transactions：費用交易明細
│  ├─ /reports/budget-vs-actual：預算比較報表
│  ├─ /masters/departments：部門主檔
│  ├─ /masters/account-codes：會計科目主檔
│  ├─ /masters/budget-items：預算項目主檔
│  └─ /mappings：對照規則維護
├─ /calendar：跨模組行事曆，整合巡檢、保養、簽核、公告、自訂事件
├─ /hotel
│  ├─ /room-maintenance-detail：飯店客房保養管理、總表、明細、統計、人員工時
│  └─ /periodic-maintenance：飯店週期保養表
├─ /mall
│  ├─ /dashboard：商場管理 Dashboard
│  ├─ /periodic-maintenance：商場週期保養
│  ├─ /b4f-inspection：商場樓層巡檢 B4F
│  ├─ /rf-inspection：商場樓層巡檢 RF
│  ├─ /b2f-inspection：商場樓層巡檢 B2F
│  └─ /b1f-inspection：商場樓層巡檢 B1F
├─ /luqun-repair/dashboard：樂群工務報修 Dashboard 與統計 Tab
├─ /dazhi-repair/dashboard：大直工務部 Dashboard 與統計 Tab
├─ /mall-facility-inspection：春大直商場工務巡檢，5 個樓層頁
├─ /full-building-inspection：整棟巡檢，RF/B4F/B2F/B1F
├─ /security：保全巡檢 Dashboard 與 7 張 Sheet
├─ /approvals：簽核清單、新增簽核、簽核明細
├─ /memos：公告清單、新增公告、公告明細
└─ /settings：使用者、角色、Ragic 對應表、Ragic 連線
```

選單來源集中在：

- `frontend/src/components/Layout/MainLayout.tsx`
- `frontend/src/constants/navLabels.ts`

路由集中在：

- `frontend/src/router/index.tsx`

---

## C. 技術解讀

### 專案架構

| 面向 | 判讀 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + Ant Design 5 + Zustand auth store |
| 後端 | FastAPI + SQLAlchemy 2 同步模式 + Pydantic v2 + APScheduler |
| DB | 主系統 SQLite `portal.db`，預算獨立 SQLite `budget_system_v1.sqlite` |
| API | 統一 `/api/v1/`，定義在 `backend/app/main.py` |
| Ragic | `backend/app/services/ragic_adapter.py` 使用 `Authorization: Basic {RAGIC_API_KEY}`，未 base64 |
| Auth | JWT login，`sub=user.id`，前端 token 存 localStorage |
| 啟動 | `backend: uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`，`frontend: npm run dev` |

### 資料流

主要業務資料流：

```text
Ragic Cloud
→ backend/app/services/*_sync.py
→ backend/portal.db local tables
→ backend/app/routers/*.py
→ frontend/src/api/*.ts
→ frontend/src/pages/**/*.tsx
```

預算資料流：

```text
backend/budget_system_v1.sqlite
→ backend/app/core/budget_database.py
→ backend/app/routers/budget.py
→ frontend/src/api/budget.ts
→ frontend/src/pages/Budget/**
```

### 關鍵檔案

| 類別 | 檔案 |
|---|---|
| App router | `frontend/src/router/index.tsx` |
| Layout/Menu | `frontend/src/components/Layout/MainLayout.tsx` |
| Login | `frontend/src/pages/Login/index.tsx` |
| 首頁 Dashboard | `frontend/src/pages/Dashboard/index.tsx` |
| Axios client | `frontend/src/api/client.ts` |
| Auth store | `frontend/src/stores/authStore.ts` |
| FastAPI app | `backend/app/main.py` |
| Auth dependency | `backend/app/dependencies.py` |
| Dashboard API | `backend/app/routers/dashboard.py` |
| Budget API | `backend/app/routers/budget.py` |
| Ragic sync | `backend/app/services/ragic_adapter.py` |

### 啟動方式與依賴

後端：

```bash
cd backend
pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

快速啟動腳本：

- `start-dev.bat`
- `start-prod.bat`

---

## D. 畫面與流程判讀

### 實際登入結果

實際使用 `admin / Admin@2026` 登入 `http://127.0.0.1:5173/` 成功。

登入頁顯示：

- `集團管理 Portal DEV`
- `維春集團內部作業與管理平台`
- 帳號 / Email
- 密碼
- 登入
- 開發用捷徑：略過認證（Dev only）

實測截圖：

- `Temp/portal-login.png`
- `Temp/portal-dashboard.png`

### Dashboard 實際可見資訊

Dashboard 實際看到的首頁重點包含：

- 預算管理摘要
- 樂群工務報修摘要
- 大直工務部摘要
- 今日重點摘要
- 商場/保全/客房完成率
- 飯店/商場/保全群組卡
- 近期同步紀錄
- 完成率趨勢
- 結案率追蹤
- 模組關聯圖譜

### Dashboard 實際數字摘要

| 區塊 | 畫面數字 |
|---|---|
| 預算管理 | 年度總預算 75,171,624，年度總實績 17,089,256，執行率 22.7%，超支 1 項，即將超支 4 項，資料異常 206 筆 |
| 樂群工務 | 4 月報修 34，已結案 11，未結案 23，結案率 32%，最久未結 13 天 |
| 大直工務 | 4 月報修 136，已結案 79，未結案 57，結案率 58%，最久未結 45 天 |
| 今日重點 | 全域待關注 130 項，商場 0、保全 1、客房 44、工務 80、預算 5 |
| 客房保養 | 完成率 40%，2 / 5 間已完成 |
| 保全巡檢 | 今日 5 場次、55/55 已巡檢、異常 1、完成率 100% |
| 商場巡檢 | 今日 0 場次，0 / 0 項，畫面顯示完成率 0% |
| 結案追蹤 | 客房保養結案率 20%，保全近 30 日異常 20，簽核待審 2 |

### 使用者實際操作流程推測

主管流程：

```text
登入
→ Dashboard 看今日重點、預算風險、工務未結案、巡檢異常
→ 點擊預算 / 工務 / 保全 / 客房快速入口
→ 進入模組 Dashboard 或明細頁
→ 指派作業或追蹤未完成
```

作業人員流程：

```text
登入
→ 從左側 Menu 進入所屬模組
→ 查詢年月或樓層
→ 查看批次、明細、異常項目
→ 必要時點擊同步 Ragic
→ 匯出或進入 Drawer/Detail 查看完整資料
```

### 主管資訊是否凸顯

目前主管視角已經有「預算 + 工務 + 今日重點」前置，方向正確。

主要問題是首頁一次放太多層級，圖譜、趨勢、結案、群組卡全部展開後，主管第一眼不容易判斷「今天最該處理哪 3 件事」。

商場 `0/0` 顯示 `0%` 也會造成誤判，應顯示「今日無資料」或「尚未同步」，不是低完成率。

---

## E. 問題清單

### 高嚴重度

| 問題現象 | 可能原因 | 影響對象 | 建議修正方向 |
|---|---|---|---|
| 多數營運模組 API 未要求 JWT，未登入也可直接讀取商場、保全、工務、行事曆部分資料 | 許多 router 未使用 `Depends(get_current_user)`，例如 `luqun_repair.py`、`security_dashboard.py`、`room_maintenance_detail.py` | 全體使用者與部署環境 | 建立 router-level auth dependency，至少所有 `/api/v1` 業務資料預設需登入；公開 debug endpoint 應移除或限 system_admin |
| 前端選單不依角色過濾，所有人都看到系統設定、Ragic、預算、工務等入口 | `MainLayout.tsx` 的 `menuItems` 是固定陣列，未使用 `user.roles` | 非管理員、主管、作業人員 | 建立 `routeMeta`/`menuMeta`，把 requiredRoles 與 menu 合併管理 |
| DEV bypass 寫入 `dev-token`，但後端 protected API 會拒絕，容易導致登入後又被 401 導回 | `Login/index.tsx` 的 `devLogin()` 沒有取得真 JWT | 開發者 | DEV bypass 應呼叫後端測試登入或只在 mock API 模式使用 |
| 未登入即可呼叫部分 `POST /sync`，理論上可觸發 Ragic 同步 | 多數 sync endpoint 無 auth，例如巡檢、保養、工務 router | 系統穩定性、Ragic API 額度 | 所有 sync endpoint 改為 `system_admin/module_manager` 角色可用 |

### 中嚴重度

| 問題現象 | 可能原因 | 影響對象 | 建議修正方向 |
|---|---|---|---|
| 首頁資訊很多，但數字口徑沒有足夠說明 | Dashboard 聚合多個 API，但 UI 只顯示結果，少顯示「資料期間 / 計算公式 / 最後同步」 | 主管 | 每張 KPI 補 tooltip 或「數字來源」小字，例如報修以報修月、結案月或本月查詢條件計算 |
| 商場巡檢 0/0 被顯示成 0.0%，今日重點判斷它完成率最低 | `total_items=0` 時 completion_rate 回 0 | 主管 | 無資料應與低完成率分開，回傳 `has_data=false`，前端顯示「尚無今日資料」 |
| 同一頁初次載入 API 多且重複，Dashboard 首次載入約 8 支業務 API，再加 GraphView 自動更新 | `Dashboard/index.tsx` 同時拉 `kpi/mall/security/trend/closure/luqun/dazhi/budget`，GraphView 另外拉 graph | 一般使用者 | 首頁拆成 summary endpoint 或 BFF，低優先資訊延後 lazy load |
| 工務模組大直與樂群頁面高度相似，重複邏輯多 | `LuqunRepair/index.tsx` 與 `DazhiRepair/index.tsx` 近似 | 開發維護者 | 抽出共用 `RepairDashboardPage`、Tab component、fee/stat table |
| 部分前端 API 直接用 `axios`，未走統一 interceptor | `securityPatrol.ts`、`mallFacilityInspection.ts` | 後續權限修正時會壞 | 全部改用 `frontend/src/api/client.ts` |

### 低嚴重度

| 問題現象 | 可能原因 | 影響對象 | 建議修正方向 |
|---|---|---|---|
| Console 有 Ant Design deprecated warning | 使用 `bordered`、`bodyStyle`、`destroyOnClose`、舊 Breadcrumb API | 開發者 | 後續配合 AntD 5 新 API 批次修 |
| React Router v7 future flag warning | React Router v6 預設提示 | 開發者 | 可加入 future flags 或升級前整理 |
| Menu 命名混雜，例如「春大直商場工務巡檢」與「整棟巡檢」和「商場管理」關係不夠清楚 | 模組持續新增後未重新資訊架構整理 | 新使用者 | 用「據點 / 業務類型 / 作業」重整選單 |
| 部分舊註解與現況不一致，例如 MallFacilityInspection 註解仍寫尚未 sync | 註解未隨 v1.33.7 後更新 | 開發者 | 修註解，降低誤判 |

---

## F. 主管視角優化建議

### 首頁應突出 KPI

| KPI | 理由 |
|---|---|
| 今日/本月待處理總數 | 主管第一眼要知道今天有多少問題 |
| 最久未結案天數與案件 | 比平均值更能驅動管理動作 |
| 預算超支與即將超支 | 直接對管理責任與成本有影響 |
| 各群組健康燈號 | 飯店、商場、保全、工務、預算用紅黃綠狀態即可 |
| 最後同步時間與資料可信度 | 讓主管知道數字是不是最新 |

### 應前移資訊

| 資訊 | 建議 |
|---|---|
| 今日重點摘要 | 放最上方第一區，預算卡之上或與預算並列 |
| 工務最久未結案 | 從文字摘要變成可點擊卡片，直接進入案件 |
| 資料異常 206 筆 | 顯示拆分：公式異常 17、金額缺漏 165、未對應 24 |
| 商場無資料 | 改成「今日尚無巡檢資料」狀態，不納入最低完成率比較 |

### 不必急著動

| 區塊 | 理由 |
|---|---|
| 預算摘要卡 | 已有主管視角，且數字清楚 |
| 樂群/大直工務摘要 | 數字與行動方向明確 |
| 保全巡檢摘要 | 今日場次、異常、完成率清楚 |
| 快速入口 | 對作業跳轉有價值 |

### 適合改版區塊

| 區塊 | 改法 |
|---|---|
| 今日重點 | 改成「風險 Inbox」卡片，每條可點擊、有負責模組、有嚴重度 |
| 趨勢圖 | 預設收合或移到第二屏 |
| 關聯圖譜 | 適合做「流程分析」頁，不一定放首頁底部 |
| 近期同步紀錄 | 首頁只放最後同步與異常，詳細列表移到 Ragic 連線頁 |
| 全域待關注 | 拆成工務、預算、保全、客房 4 張小卡 |

---

## G. 開發優先順序

### Phase 1：最快提升體感與安全

1. 全部業務 router 補 `get_current_user`，sync/debug endpoint 補角色限制。
2. 前端 `securityPatrol.ts`、`mallFacilityInspection.ts` 改走 `apiClient`。
3. 修正商場 `0/0 = 0%` 的資料語意，改顯示「尚無資料」。
4. Dashboard 的今日重點排序改為紅色風險優先，並讓每條可點擊。
5. 修正 DEV bypass，避免假 token 造成錯誤登入體驗。

### Phase 2：結構整理

6. 建立 menu/route 權限 metadata，讓選單與路由守衛共用。
7. 抽共用 Repair 模組，合併大直/樂群重複 UI 與統計元件。
8. 建立 Dashboard BFF endpoint，減少首頁多 API 聚合與前端計算。
9. 把「數字口徑」集中到 docs 與 API response metadata，例如 `period_basis`、`last_sync_at`、`source_table`。
10. 清理 AntD deprecated API 與過期註解。

### Phase 3：長期優化

| 項目 | 方向 |
|---|---|
| 資料治理 | 每個模組定義資料新鮮度、同步狀態、口徑版本 |
| 權限模型 | 不只 role，還要 module permission 與 tenant scope |
| 效能 | 大表查詢加索引、首頁快取、GraphView 延後載入 |
| 部署 | 正式環境改 PostgreSQL，避免 OneDrive + SQLite 鎖定風險 |
| 監控 | API 錯誤、同步失敗、資料落後加入系統警示 |

---

## Top 3

### 最值得先處理的 3 個 Bug

| Bug | 建議 |
|---|---|
| 業務 API 未登入可讀 | 先補 auth dependency |
| DEV bypass token 無效 | 改成真登入或移除 |
| 商場無資料被當成 0% 完成率 | `has_data=false` 與 0% 分開 |

### 最值得先處理的 3 個 UX 問題

| UX | 建議 |
|---|---|
| 首頁資訊過多 | 第一屏只放今日重點、預算風險、最久未結案 |
| KPI 口徑不明 | 每張卡加 tooltip 與最後同步時間 |
| 選單層級太長 | 依「主管總覽 / 作業模組 / 系統設定」重整 |

### 最值得先處理的 3 個架構問題

| 架構 | 建議 |
|---|---|
| 權限散落且不一致 | route/menu/API 用同一份 permission metadata |
| 大直/樂群重複 | 抽共用工務報修模組 |
| API client 不一致 | 全部使用 `apiClient` 與 interceptor |

---

## 實測與驗證

已實際用 Chrome headless 登入並瀏覽首頁與主要頁面。

截圖：

- `Temp/portal-login.png`
- `Temp/portal-dashboard.png`

驗證：

```bash
cd frontend
npx tsc --noEmit
```

結果：通過。

```bash
cd backend
python -m compileall -q app
```

結果：通過。

Console 主要訊息：

- Ant Design deprecated warning：`bordered`、`bodyStyle`、`destroyOnClose`、舊 Breadcrumb API
- React Router v7 future flag warning
- 未看到核心 API request failed

API 實測：

- 多數 Dashboard API 約 10-50ms
- 大直 Dashboard 約 265ms
- 屬可接受，但可列入後續效能優化

---

## 給主管看的摘要版

這套 Portal 已能把預算、工務報修、飯店保養、商場巡檢、保全巡檢、簽核與公告整合成一個管理首頁。

現在最有價值的是首頁已能直接指出預算超支、工務未結案、保全異常與全域待關注數，具備主管決策雛形。

短期最應先處理的是權限安全與首頁判讀品質：

1. 目前部分 API 未登入也能讀資料，正式部署前必須修。
2. 商場沒有今日資料時不應顯示為 0% 完成率。
3. 首頁應把「今天最需要主管處理的 3-5 件事」放到最上方。

完成這三件事後，再整理選單與共用元件，Portal 會更像正式營運系統，而不是多個功能頁的集合。
