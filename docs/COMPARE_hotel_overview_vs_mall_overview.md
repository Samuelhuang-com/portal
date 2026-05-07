# hotel/overview vs mall/overview — 完整差異比對報告

> 比對日期：2026-05-06
> 版本狀態：只讀取比對，未修改任何程式
> 比對範圍：前端 React 元件、後端 FastAPI Router、API Client、Router 設定、Permission 設定

---

## 比對摘要

| 維度 | hotel/overview | mall/overview | 狀態 |
|------|---------------|---------------|------|
| Tab 數量 | 6 | 6 | ✅ 相同 |
| 資料來源數 | 5 | 5（含2個固定0） | ⚠️ 設計不同 |
| KPI Card 結構 | 5個聚合KPI | 5個聚合KPI | ✅ 相同 |
| PPTX 後端 endpoint | ❌ 無 @router.post | ❌ 無 @router.post | ❌ 兩邊都缺 |
| PPTX 前端按鈕 | ✅ 有按鈕但404 | ❌ 函式存在但未渲染 | ❌ 狀態不一致 |
| 篩選器 | 年+月+日期選擇器 | 年+月（無日期選擇器） | ⚠️ 設計不同 |
| 人員排名資料來源 | 5來源彙整（person-hours API） | 僅報修一源（luqun top_hours） | ❌ 不一致 |
| 錯誤命名（商場/飯店） | 後端PPTX有商場字眼 | 正確 | ❌ Hotel端有錯 |
| cases_pct 欄位 | ❌ 無 | ✅ 有 | ⚠️ 不一致 |

**整體評分：61 / 100**（詳見第九節）

---

## 一、模組基本資料比對

| 項目 | hotel/overview | mall/overview |
|------|---------------|---------------|
| **模組名稱** | 飯店管理 Dashboard | 商場管理 Dashboard |
| **路由位置** | `/hotel/overview` | `/mall/overview` |
| **前端路由檔** | `frontend/src/router/index.tsx` | `frontend/src/router/index.tsx` |
| **前端元件** | `pages/HotelMgmtDashboard/index.tsx`（1676行） | `pages/MallMgmtDashboard/index.tsx`（1384行） |
| **API Client** | `api/hotelOverview.ts`（170行） | `api/mallOverview.ts`（167行） |
| **CSS/Style 來源** | Ant Design 5 + Inline style | Ant Design 5 + Inline style |
| **後端 Router** | `routers/hotel_overview.py`（1051行） | `routers/mall_overview.py`（1021行） |
| **後端 API prefix** | `/api/v1/hotel/` | `/api/v1/mall/` |
| **已有 API endpoint** | GET daily-hours, monthly-hours, person-hours | GET daily-hours, monthly-hours, person-hours |
| **PPTX endpoint** | ❌ 無（`@router.post` 缺失） | ❌ 無（`@router.post` 缺失） |
| **Permission Key** | 無（無 PermissionGuard） | 無（無 PermissionGuard） |
| **Ragic App Directory** | 未獨立登錄（各子模組分別登錄） | 未獨立登錄（各子模組分別登錄） |
| **Menu Config** | 須確認是否已設定 | 須確認是否已設定 |

---

## 二、TAB 結構逐一比對

| TAB | 順序 | hotel/overview | mall/overview | 名稱一致 | 功能一致 | 差異說明 | 建議 |
|-----|:----:|:-------------:|:-------------:|:--------:|:--------:|---------|------|
| Dashboard | 1 | ✅ key=`overview` | ✅ key=`dashboard` | ⚠️ | ⚠️ | Tab key 不同；hotel在Tab內含DatePicker，mall無 | 統一key命名 |
| B. 每日累計 | 2 | ✅ key=`daily` | ✅ key=`daily` | ✅ | ⚠️ | Mall多一欄`cases_pct`，Hotel無 | Hotel補上cases_pct |
| C. 每月累計 | 3 | ✅ key=`monthly` | ✅ key=`monthly` | ✅ | ⚠️ | Mall多一欄`cases_pct`，Hotel無 | Hotel補上cases_pct |
| D. 每年累計 | 4 | ✅ key=`yearly` | ✅ key=`yearly` | ✅ | ❌ | Hotel單年滾計；Mall三年並排比較 | 確認主管需求後統一 |
| 人員工時% | 5 | ✅ key=`person` | ✅ key=`person_pct` | ⚠️ | ✅ | Tab key 不同，功能設計一致 | 統一key命名 |
| 人員排名 | 6 | ✅ key=`ranking` | ✅ key=`ranking` | ✅ | ❌ | Hotel用person-hours API(5來源)；Mall用luqun top_hours(僅報修1來源) | P1 待統一 |

---

## 三、每個 TAB 功能比對

| TAB | 比對項目 | hotel/overview | mall/overview | 一致 | 差異說明 | 建議 |
|-----|---------|:--------------:|:-------------:|:----:|---------|------|
| 全頁 | 年份篩選 | ✅ | ✅ | ✅ | | |
| 全頁 | 月份篩選（含全年） | ✅ | ✅ | ✅ | | |
| 全頁 | 日期區間篩選 | ❌ | ❌ | ✅ | 均無日期區間 | |
| Dashboard | 巡檢日期 DatePicker | ✅（有） | ❌（無） | ❌ | Hotel有額外巡檢日期選擇，用於 hotel-daily-inspection API | Mall不需要此欄位 |
| Dashboard | 重設/清除按鈕 | ❌ | ❌ | ✅ | 均無專屬重設按鈕 | P2 可補充 |
| Dashboard | Loading 狀態 | ✅ | ✅ | ✅ | | |
| Dashboard | Error 狀態 | ✅ | ✅ | ✅ | | |
| Dashboard | KPI Card 同步更新 | ✅ | ✅ | ✅ | | |
| Dashboard | 來源狀態卡同步更新 | ✅ | ✅ | ✅ | | |
| Dashboard | 圖表同步更新 | ✅ | ✅ | ✅ | | |
| B.每日累計 | 月份獨立篩選 | ❌（沿用全頁） | ✅（Tab內可選月） | ❌ | Mall在TabB內可獨立選年月；Hotel沿用頁頂篩選 | 待確認設計偏好 |
| B.每日累計 | 重新整理按鈕 | ✅ | ✅ | ✅ | | |
| C.每月累計 | 年份獨立篩選 | ❌（沿用全頁） | ✅（Tab內可選年） | ❌ | Mall在TabC內可獨立選年 | |
| D.每年累計 | 年份選擇 | ✅（單年） | ✅（基準年，展3年） | ❌ | 設計意圖不同 | 確認主管需求 |
| 人員工時% | 年份獨立篩選 | ❌（沿用全頁） | ✅（Tab內可選年） | ❌ | | |
| 人員排名 | 年份篩選 | ❌（沿用全頁） | ✅（Tab內可選年） | ❌ | | |
| B/C/D | Cases_pct 欄位 | ❌ | ✅ | ❌ | Mall後端回傳cases_pct，Hotel無 | Hotel補充 |

---

## 四、Dashboard KPI Card 比對

### 4.1 聚合 KPI Cards（5個主 KPI）

| KPI 名稱 | hotel/overview | mall/overview | 一致 | 差異說明 |
|---------|:-------------:|:-------------:|:----:|---------|
| 本期總工項 | ✅ | ✅ | ✅ | |
| 已完成工項 | ✅ | ✅ | ✅ | |
| 本期工時合計 | ✅ | ✅ | ✅ | |
| 異常/未完成 | ✅ | ✅ | ✅ | |
| 逾期未完成 | ✅ | ✅ | ✅ | |
| 完成率 | 各來源卡內顯示 | 各來源卡內顯示 | ✅ | |

**KPI 計算來源：**
- Hotel：5個 NormalizedSource adapter（periodic/ihg/daily_inspection/security/dazhi）聚合
- Mall：7個 NormalizedSummary（mall_pm/full_bldg_pm/mall_facility/full_bldg_insp/luqun_repair + 2 placeholder）聚合

### 4.2 來源狀態卡（Source Cards）

| 來源卡 | hotel/overview | mall/overview | 備註 |
|--------|:--------------:|:-------------:|------|
| 卡片數量 | 7張（5實+2佔位） | 7張（5實含1佔位+2佔位） | |
| 佈局 | 單排（flex wrap） | 雙排（4+3） | ❌ 佈局不同 |
| 實際資料卡 | 飯店週期保養、IHG客房保養、飯店每日巡檢、保全巡檢、工務部 | 商場例行維護、全棟例行維護、商場工務巡檢、整棟巡檢（佔位）、商場工務報修 | ✅ 結構一致 |
| 佔位卡名稱 | 飯店主管交辦、飯店緊急事件 | 商場主管交辦、商場緊急事件 | ✅ 文字正確 |
| 每卡顯示內容 | 工項/完成數、完成率進度條、異常/逾期/工時 | 工項/完成數、完成率進度條、異常/逾期/工時 | ✅ |

### 4.3 KPI 命名問題（P0 警告）

❌ **`hotel_overview.py` 第 760 行**：後端 PPTX builder 中佔位卡硬編碼為「商場主管交辦」、「商場緊急事件」，與飯店模組不符。應為「飯店主管交辦」、「飯店緊急事件」。

```python
# hotel_overview.py 第760行（錯誤）
for pname in ["商場主管交辦", "商場緊急事件"]:

# 應改為
for pname in ["飯店主管交辦", "飯店緊急事件"]:
```

---

## 五、表格內容與欄位比對

### 5.1 B. 每日累計 表格欄位

| 欄位 | hotel/overview | mall/overview | 一致 | 差異 |
|------|:--------------:|:-------------:|:----:|------|
| 工項類別（固定左欄） | ✅ | ✅ | ✅ | |
| 每日 HR（動態日期欄） | ✅ | ✅ | ✅ | |
| 合計 HR | ✅ | ✅ | ✅ | |
| 工時% | ✅ | ✅ | ✅ | |
| 每日案件數 | ✅ | ✅ | ✅ | |
| 案件合計 | ✅ | ✅ | ✅ | |
| 案件% | ❌ 無 | ✅ 有 | ❌ | Mall後端回傳cases_pct欄位，Hotel未回傳亦未顯示 |
| 橫向捲動 | ✅ | ✅ | ✅ | |
| TOTAL 列 | ✅ | ✅ | ✅ | |
| 匯出按鈕 | ❌ | ❌ | ✅ | 均無Excel/CSV匯出 |

### 5.2 C. 每月累計 表格欄位

| 欄位 | hotel/overview | mall/overview | 一致 | 差異 |
|------|:--------------:|:-------------:|:----:|------|
| 工項類別 | ✅ | ✅ | ✅ | |
| 1月～12月 HR | ✅ | ✅ | ✅ | |
| 合計 HR | ✅ | ✅ | ✅ | |
| 工時% | ✅ | ✅ | ✅ | |
| 每月案件數 | ✅ | ✅ | ✅ | |
| 案件合計 | ✅ | ✅ | ✅ | |
| 案件% | ❌ 無 | ✅ 有 | ❌ | |

### 5.3 D. 每年累計 表格欄位

| 欄位 | hotel/overview | mall/overview | 一致 | 差異 |
|------|:--------------:|:-------------:|:----:|------|
| 工項類別 | ✅ | ✅ | ✅ | |
| 月份欄（滾計） | ✅（1~12月累計） | ❌（不同年份並排） | ❌ | Hotel為單年滾計；Mall為多年比較 |
| 年份維度 | 單年 | 3年並排（baseyear-2~0） | ❌ | 設計意圖不同 |

### 5.4 人員工時% 表格欄位

| 欄位 | hotel/overview | mall/overview | 一致 | 差異 |
|------|:--------------:|:-------------:|:----:|------|
| 工項類別 | ✅ | ✅ | ✅ | |
| 人員名稱欄（動態） | ✅（Top-15） | ✅（Top-15） | ✅ | |
| 百分比顯示 | ✅ | ✅ | ✅ | |
| 資料來源 | `/hotel/person-hours`（5來源） | `/mall/person-hours`（5來源） | ✅ | |

### 5.5 人員排名 表格欄位

| 欄位 | hotel/overview | mall/overview | 一致 | 差異 |
|------|:--------------:|:-------------:|:----:|------|
| 排名 | ✅ | ✅ | ✅ | |
| 人員姓名 | ✅ | ✅ | ✅ | |
| 工時(HR) | ✅ | ✅ | ✅ | |
| 占比% | ✅ | ✅ | ✅ | |
| 案件數 | ✅ | ✅ | ✅ | |
| 資料來源 | `/hotel/person-hours`（全5來源） | `luqunData.top_hours`（**僅報修**） | ❌ | **P1重大差異**：Mall排名只反映報修人員，PM/巡檢人員不在排名中 |
| 圖表 | ✅ 橫向Bar Chart | ❌ 無圖表 | ❌ | Hotel額外有橫向柱狀圖 |

---

## 六、版型與 UI 視覺比對

| 區塊 | 比對項目 | hotel/overview | mall/overview | 一致 | 差異說明 |
|------|---------|:--------------:|:-------------:|:----:|---------|
| 頁面標題 | 樣式 | 🏨 + Title level 4 | 標題+副標題 | ⚠️ | 內容不同但結構相似 |
| 頁面標題 | 副標題說明 | 6項來源說明 | 5來源說明 | ⚠️ | |
| 篩選列 | 位置 | 頁頂Card（所有Tab共用） | Tab A內Card + 各Tab獨立 | ❌ | Hotel篩選在頁頂，Mall各Tab可獨立篩選 |
| PPTX按鈕 | 位置 | 頁頂右側（已渲染） | 無按鈕（函式存在未渲染） | ❌ | |
| PPTX按鈕 | 樣式 | 漸層紫（#667eea, #764ba2） | — | — | 與PROTECTED.md圖表按鈕一致 ✅ |
| KPI Card | 品牌主色 | #1B3A5C | #1B3A5C | ✅ | |
| KPI Card | 輔色 | #4BA8E8 | #4BA8E8 | ✅ | |
| 來源卡 | 完成率進度條顏色 | 綠/橘/紅三段 | 綠/橘/紅三段 | ✅ | |
| 費用摘要 | 第3格 | 本月費用合計 | 扣款專櫃（家數） | ❌ | 設計意圖不同 |
| 圖表 | 類型 | Bar+Pie+Line+Rate Bar | Bar+Pie+Line+Rate Bar | ✅ | |
| 圖表 | Trend Line | DazhiRepair 12月趨勢 | LuqunRepair 12月趨勢 | ✅ 概念相同 | |
| 空資料 | 提示 | Alert message | Alert message | ✅ | |
| Loading | 顯示 | Spin | Spin | ✅ | |
| Tab | 懶載入 | ✅（useRef loadedTabs） | ✅（handleTabChange） | ✅ | |
| 元件 | 共用 component | ❌ 各自實作 | ❌ 各自實作 | ❌ | SourceCard等未抽共用元件 |

---

## 七、字詞與命名一致性檢查

| 檔案 | 行數/區塊 | 發現文字 | 問題說明 | 建議修正 |
|------|----------|---------|---------|---------|
| `backend/app/routers/hotel_overview.py` | 第760行 | `"商場主管交辦"` | Hotel PPTX builder裡佔位卡名稱誤用「商場」，應為「飯店」 | 改為`"飯店主管交辦"` |
| `backend/app/routers/hotel_overview.py` | 第761行 | `"商場緊急事件"` | 同上 | 改為`"飯店緊急事件"` |
| `backend/app/routers/hotel_overview.py` | 第80行（summary） | `"六項來源"` | `HOTEL_CATEGORIES`只有5個元素，API doc說六項 | 改為`"五項來源"` |
| `backend/app/routers/hotel_overview.py` | 第270行（summary） | `"六項來源"` | 同上 | 改為`"五項來源"` |
| `backend/app/routers/hotel_overview.py` | 第443行（summary） | `"六項來源，Top-15"` | 同上 | 改為`"五項來源，Top-15"` |
| `frontend/src/api/mallOverview.ts` | MallPersonHoursData interface | `person_totals`欄位缺失 | 後端`mall/person-hours`有回傳`person_totals`，TS型別缺此欄位 | 補上`person_totals: number[]` |
| `frontend/src/pages/HotelMgmtDashboard/index.tsx` | 第113行附近 | `HOTEL_SOURCE_ROUTES.security` | 路由值`'/hotel/security/dashboard'`，但router設定的路徑是`/security/dashboard`，不含/hotel前綴 | 確認路由路徑是否正確 |
| `frontend/src/pages/HotelMgmtDashboard/index.tsx` | `source_name: '工務部'` | `adaptDazhi`回傳`source_name: '工務部'`，但category應為`飯店工務部` | 與後端HOTEL_CATEGORIES不一致 | 改為`'飯店工務部'` |

---

## 八、計算邏輯比對

### 8.1 每日工時計算

| 來源 | hotel/overview | mall/overview | 一致 | 差異說明 |
|------|:--------------:|:-------------:|:----:|---------|
| 週期保養工時 | `estimated_minutes / 60`（預估） | `start_time~end_time`（實際） | ❌ | Hotel用預估工時，Mall用實際保養時間 |
| 報修/工務工時 | `work_hours` 或 `close_days` | `work_hours`（含is_excluded排除） | ⚠️ | Hotel有fallback to close_days；Mall無此fallback |
| 巡檢工時 | start/end_time差值 / 60 | start/end_time差值 / 60 | ✅ | |
| 時間格式解析 | `_parse_minutes()` | `_parse_minutes()`（複製版） | ✅ | 兩邊各自複製一份，邏輯完全相同 |
| 跨日處理 | `diff + 24*60 if diff < 0` | `diff + 24*60 if diff < 0` | ✅ | |
| IHG客房保養 | 每筆固定 0.5 HR | — | N/A | Mall無此來源 |

### 8.2 每日案件數計算

| 來源 | hotel/overview | mall/overview | 一致 | 差異說明 |
|------|:--------------:|:-------------:|:----:|---------|
| 報修案件口徑 | `_stat_year/_stat_month`（已結案→completed_at，未結案→occurred_at） | 已結案→completed_at，未結案→occurred_at；**排除is_excluded_flag=True** | ⚠️ | Mall多一個排除條件 |
| 週期保養案件 | frequency=monthly + exec_months過濾 | 直接計item數（無frequency過濾） | ❌ | 口徑不同 |
| 每日巡檢案件 | 直接計batch數 | 直接計batch數 + **缺漏場次補計** | ❌ | Mall有缺漏計算（MALL_FI_SHEET_COUNT=5），Hotel無 |
| IHG案件口徑 | 本月不重複房號數（去重） | — | N/A | |

### 8.3 完成率計算

| 來源 | hotel/overview | mall/overview | 一致 |
|------|:--------------:|:-------------:|:----:|
| 聚合完成率 | `totalCompleted / totalCases * 100`（前端計算） | `totalCompleted / totalCases * 100`（前端計算） | ✅ |
| 週期保養 | 後端`/stats` completion_rate | 後端`/stats` completion_rate | ✅ |
| 巡檢 | 後端monthly-summary completion_rate | 後端monthly-summary completion_rate | ✅ |
| 報修 | `completed / total * 100` | `completed / total * 100` | ✅ |

### 8.4 時間維度口徑

| 維度 | hotel/overview | mall/overview | 一致 | 差異說明 |
|------|:--------------:|:-------------:|:----:|---------|
| 月份前綴格式 | `YYYY/MM`（零填充） | `YYYY/MM`，容錯`YYYY/M`（兩種格式） | ⚠️ | Hotel不做容錯；Mall有非零填充容錯 |
| 日期格式 | `YYYY/MM/DD` | `YYYY/MM/DD`，容錯`YYYY/M/DD` | ⚠️ | 同上 |

### 8.5 跨模組統計風險

| 風險 | hotel/overview | mall/overview | 說明 |
|------|:--------------:|:-------------:|------|
| 重複計算 | ❌ 無（各來源獨立） | ❌ 無（各來源獨立） | 設計正確 |
| 報修來源區分 | `DazhiRepairCase`（飯店工務部） | `LuqunRepairCase`（商場工務報修） | ✅ 正確區分 |
| 週期保養區分 | `PeriodicMaintenanceBatch`（飯店PM） | `MallPeriodicMaintenanceBatch` + `FullBldgPMBatch` | ✅ 正確區分 |
| 巡檢來源區分 | `HotelDIBatch` + `SecurityPatrolBatch` | `MallFIBatch` + `RFInspectionBatch` | ✅ 正確區分 |

---

## 九、標準化程度評分

| 評分項目 | 滿分 | 得分 | 扣分原因 |
|---------|----:|----:|---------|
| TAB 結構一致性 | 20 | 13 | Tab key命名不統一（overview vs dashboard, person vs person_pct）；D.每年累計設計意圖完全不同；人員排名資料來源不同 |
| 篩選功能一致性 | 15 | 9 | Hotel篩選在頁頂，Mall各Tab獨立篩選；Hotel有DatePicker，Mall無；B/C/D Tab篩選機制不同 |
| KPI Card 一致性 | 15 | 11 | 5個主KPI完全一致；來源卡數量/佈局不同；Hotel PPTX佔位名稱有「商場」錯字 |
| 表格欄位一致性 | 15 | 9 | Mall B/C多cases_pct欄；D.每年累計欄位設計完全不同；人員排名表Hotel多柱狀圖 |
| UI / 版型一致性 | 15 | 10 | KPI Card顏色一致；費用摘要第3欄不同；PPTX按鈕一個有一個無；來源卡佈局不同 |
| 計算邏輯清楚度 | 10 | 5 | _parse_minutes重複複製；週期保養工時口徑不同（預估vs實際）；月份格式容錯邏輯不對稱 |
| 程式碼可維護性 | 10 | 4 | SourceCard未抽共用元件；PPTX工具函式分別命名（_pptx_txt vs _mall_pptx_txt）；前端型別定義不完整（MallPersonHoursData缺person_totals） |
| **總分** | **100** | **61** | |

**結論：** 兩個模組採用相似架構骨架，但在細節實作上存在大量不一致，特別是人員排名資料來源、PPTX endpoint缺失、計算口徑不同等問題，需要系統性修正。

---

## 十、Ragic Portal 三項設定檢查

| 檢查項目 | hotel/overview | mall/overview | 一致 | 問題 | 建議 |
|---------|:--------------:|:-------------:|:----:|-----|------|
| **settings/menu-config** | 需確認是否已設定路由入口 | 需確認是否已設定路由入口 | — | 須至 `/settings/menu-config` 確認 hotel/overview 與 mall/overview 是否已掛載於側欄選單 | 確認並補充 |
| **settings/roles 權限設定** | 無 PermissionGuard（任何登入者可看） | 無 PermissionGuard（任何登入者可看） | ✅ | 兩者均無細粒度 permission key，若需限制特定角色須補上 | 視業務需求補充 permission key |
| **settings/ragic-app-directory** | 未有獨立 Overview 登錄（各子模組分別登錄） | 未有獨立 Overview 登錄（各子模組分別登錄） | ✅ | Overview 為本地 DB 彙整，不直接對應單一 Ragic 表單，無需獨立登錄 | 維持現狀，各子模組已登錄即可 |

---

## 十一、P0 / P1 / P2 修改優先順序

### P0：數據錯誤或主管會誤解

| # | 模組 | TAB/位置 | 問題 | 影響 | 建議處理 |
|---|------|---------|------|------|---------|
| 1 | hotel/overview | Dashboard（全頁頂部按鈕） | PPTX匯出按鈕存在但後端無 `@router.post("/overview/export/pptx")` endpoint，點擊必定 404 | 主管匯出時報錯，形象問題 | hotel_overview.py 補上 `@router.post` 端點 |
| 2 | hotel/overview | PPTX Slide 2 | 後端 PPTX builder 第760行佔位卡名稱寫「商場主管交辦」、「商場緊急事件」，出現在飯店報告中 | 主管看到商場字眼以為數據錯誤 | 改為「飯店主管交辦」、「飯店緊急事件」 |
| 3 | hotel/overview | API 文件 | `/hotel/daily-hours`、`/monthly-hours`、`/person-hours` 的 summary 說「六項來源」但實際只有5項 | 誤導API使用者 | summary 改為「五項來源」 |
| 4 | mall/overview | 人員排名 Tab | 人員排名僅用 `luqunData.top_hours`（報修單一來源），PM執行人員、巡檢人員完全不計入排名 | 排名嚴重失真，PM/巡檢人員隱形 | 改用 `/mall/person-hours` API 資料，與hotel做法一致 |
| 5 | frontend `api/mallOverview.ts` | MallPersonHoursData | TypeScript 型別缺少 `person_totals: number[]`，後端有回傳，前端型別不完整 | 後續開發者使用時易出錯 | 補上 `person_totals: number[]` |

### P1：影響一致性與維護性

| # | 模組 | TAB/位置 | 問題 | 影響 | 建議處理 |
|---|------|---------|------|------|---------|
| 6 | mall/overview | Dashboard（全頁） | 前端 `handleExportPptx` 函式已寫好、API client 也有 `exportMallOverviewPptx`，但後端無 `@router.post` endpoint，且前端 UI 未渲染匯出按鈕（死碼） | 功能白寫 | 補上後端 endpoint 並渲染按鈕 |
| 7 | hotel/overview | 人員工時% / 人員排名 | Tab key 命名為 `person`，Mall 為 `person_pct`，不統一 | 程式碼維護混亂 | 統一為 `person_pct` |
| 8 | hotel/overview | Dashboard Tab | Tab key 命名為 `overview`，Mall 為 `dashboard`，不統一 | 同上 | 統一為 `dashboard` |
| 9 | hotel/overview | B/C Tab | 後端回傳資料無 `cases_pct` 欄位，表格也無此欄，Mall 有 | 主管無法橫向比較兩邊案件比例 | Hotel 後端補上 cases_pct，前端補欄位 |
| 10 | hotel/overview | Dashboard | 篩選列在頁頂，所有Tab共用；Mall各Tab有獨立篩選 | 操作體驗不一致 | 評估是否統一為 Tab 內篩選 |
| 11 | hotel/overview | B Tab | Hotel 的 B Tab 沿用頁頂 year/month，無法在 Tab 內獨立選月 | 操作不如 Mall 彈性 | 補上 Tab 內月份選擇 |
| 12 | 兩邊後端 | 工具函式 | `_parse_minutes` 在 hotel_overview.py 和 mall_overview.py 各自複製一份 | 若邏輯有 bug 需兩邊修 | 抽到 `app/services/time_utils.py` 共用 |
| 13 | 兩邊後端 | 工具函式 | PPTX 工具函式分別命名（`_pptx_txt` vs `_mall_pptx_txt`），邏輯完全相同 | 程式碼膨脹，維護成本高 | 抽到共用模組 |

### P2：版型、體驗、程式碼整理

| # | 模組 | TAB/位置 | 問題 | 影響 | 建議處理 |
|---|------|---------|------|------|---------|
| 14 | hotel/overview | Dashboard | `adaptDazhi` 回傳 `source_name: '工務部'`，但HOTEL_CATEGORIES是`飯店工務部` | 輕微命名不一致 | 改為`'飯店工務部'` |
| 15 | 兩邊前端 | 全部 | `SourceCard` 元件各自在元件函式內實作，未抽成共用 React component | 程式碼重複 | 抽成 `components/SourceCard/index.tsx` |
| 16 | 兩邊前端 | 全部 | KPI 聚合計算邏輯（totalCases/totalCompleted等）各自實作 | 同上 | 抽成共用 hook `useAggregatedKpi()` |
| 17 | hotel/overview | D Tab | 每年累計為單年滾計；Mall 為3年並排，設計意圖不同 | 主管橫向比較困難 | 討論後統一設計 |
| 18 | hotel/overview | Dashboard篩選 | Hotel有巡檢日期 DatePicker，Mall無 | 操作不一致（但 hotel 有必要） | 維持現狀，於說明文件記錄設計差異 |
| 19 | 兩邊後端 | 月份容錯 | Hotel 月份格式不做容錯（僅 YYYY/MM），Mall 容錯 YYYY/M | 若資料有舊格式，Hotel 可能遺漏 | Hotel 補上相同的容錯邏輯 |
| 20 | 兩邊前端 | 全部 | 均無 Excel/CSV 匯出功能 | 主管需要時須手動複製 | P2 可評估補充 |

---

## 十二、待確認問題

| # | 問題 | 影響 | 建議確認方式 |
|---|------|------|------------|
| Q1 | Hotel `HOTEL_SOURCE_ROUTES.security` 路徑是 `/hotel/security/dashboard`，但 router 設定的路徑是 `/security/dashboard`（無hotel前綴），點擊來源卡的「查看明細」是否能正確導航？ | 若路徑錯誤，使用者點擊無法跳轉 | 在瀏覽器實測點擊後的跳轉行為 |
| Q2 | Hotel `HOTEL_SOURCE_ROUTES.daily_inspection` 路徑是 `/hotel/hotel-daily-inspection/dashboard`，router 設定的是 `/hotel/daily-inspection`，是否正確？ | 同上 | 同上 |
| Q3 | D.每年累計的設計是否已確認：Hotel 要單年滾計？Mall 要三年並排？主管偏好哪種？ | 若主管希望一致，需決定統一哪種設計 | 與主管確認 |
| Q4 | menu-config 是否已正確設定 hotel/overview 和 mall/overview 的選單入口、群組、排序？ | 若未設定，使用者找不到入口 | 至 `/settings/menu-config` 確認 |
| Q5 | hotel/overview 的 PPTX `_build_hotel_pptx` 函式在 hotel_overview.py 中有完整實作，但無 `@router.post` 端點——是否因為曾有計劃但尚未接上？ | 確認是否需要補上 endpoint | 查 git log |
| Q6 | Mall 費用摘要第3格顯示「扣款專櫃（家數）」，Hotel 顯示「本月費用合計」——此設計差異是業務決定還是開發遺漏？ | 若是遺漏，Mall應改一致 | 與業主確認 |
| Q7 | Mall 人員工時% Tab 已有 `/mall/person-hours` API（5來源），但人員排名 Tab 卻用 `luqunData.top_hours`（僅1來源）。是否已知此限制，或是開發遺漏？ | 若遺漏，排名嚴重失真 | 確認後改用 person-hours API |

---

## 十三、後續開發建議

### 可直接共用 mall/overview 版型的部分

1. **Tab B/C 表格結構** — Mall 的 `buildMallDailyCols()` 已有 `cases_pct` 欄位，Hotel 可參考補上同欄位（需後端也補 cases_pct）
2. **KPI Card 計算邏輯** — 兩邊的 totalCases/totalCompleted/totalWorkHours 計算方式相同，可抽共用 hook
3. **PPTX Payload 結構** — `KpiSummaryIn`、`SourceCardIn`、`RepairCostsIn` 兩邊完全一致，可抽成共用型別

### 不建議共用的部分（資料來源不同）

1. **來源卡 SourceCard 資料邏輯** — Hotel 的 adapter function（adaptPeriodic/adaptIHG/adaptHotelDI/adaptSecurity/adaptDazhi）與 Mall 完全不同，資料結構各異，建議各自維護 adapter，僅抽共用 UI 元件外殼
2. **工時計算** — Hotel PM 用預估工時（`estimated_minutes`），Mall PM 用實際工時（start/end_time），計算口徑不同，不可共用計算函式

### 應抽成共用 Component 的部分

1. `SourceCard` 外層 UI（顏色條、工項數、完成率進度條、異常/逾期/工時展示）
2. PPTX 工具函式（`_pptx_txt`、`_pptx_rect`、`_pptx_header`、`_pptx_cell`）→ 建議移至 `app/services/pptx_utils.py`
3. `_parse_minutes()` → 建議移至 `app/services/time_utils.py`

### 可沿用的 API

- `/hotel/daily-hours`、`/hotel/monthly-hours`、`/hotel/person-hours` 設計良好，僅需補 `cases_pct`
- `/mall/daily-hours`、`/mall/monthly-hours`、`/mall/person-hours` 設計良好

### 不建議新增的 API

- 不建議建立「統一跨飯店+商場彙整」的單一 API，因兩邊資料模型、口徑差異太大，容易造成邏輯混亂

### 計算邏輯應集中管理的部分

- `_parse_minutes()` 時間解析 → `app/services/time_utils.py`
- 月份前綴容錯（YYYY/MM vs YYYY/M）→ `app/services/time_utils.py`
- 報修案件口徑（已結案→completed_at，未結案→occurred_at）→ `app/services/repair_stats.py`

### 僅文字或 UI 差異（不影響統計正確性）

- Tab key 命名（`overview` vs `dashboard`；`person` vs `person_pct`）
- 費用摘要第3格文字
- 頁頂 PPTX 按鈕有無
- 來源卡佈局（單排 vs 雙排）

### 會影響統計正確性的差異

1. **P0** 飯店 PPTX 後端 endpoint 缺失 → 匯出報告功能壞掉
2. **P0** 飯店 PPTX 佔位卡名稱「商場」錯字 → 主管誤判
3. **P0** 商場人員排名僅統計報修人員 → 排名嚴重失真
4. **P1** Hotel 月份格式無容錯 → 若資料有 YYYY/M 格式則遺漏統計
5. **P1** Hotel 週期保養工時用預估，Mall 用實際 → 兩邊工時數字本質不同，主管比較時需知曉此差異

---

*報告產出時間：2026-05-06*
*比對工具：Claude（Cowork mode），直接讀取原始碼，未執行任何修改*
