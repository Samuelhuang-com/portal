# 工時計算邏輯變更規劃報告

> 版本：v1.0 | 日期：2026-04-27 | 狀態：**草稿，等待確認**

---

## 1. 目前程式盤點

### 1-A. 各模組工時計算彙整表

| 模組 | 檔案 | 目前工時計算位置 | 使用欄位 | 目前公式 | 是否需要修改 | 建議修改方式 |
|------|------|----------------|---------|---------|------------|------------|
| **ExecMetrics / WorkCategoryAnalysis（"本期總工時"）** | `backend/app/routers/work_category_analysis.py` line 254<br>`frontend/src/components/ExecMetrics/index.tsx` line 111<br>`frontend/src/pages/WorkCategoryAnalysis/index.tsx` line 135 | 後端 service 加總，前端直接顯示 | `work_hours`（來自 luqun + dazhi + hotel_room + ihg_room 四個來源） | `SUM(work_hours)` 四個來源合計，rounded to 1 decimal | **是** | 改名為「花費時間」；新增「本期總工時 = 1432 HR（固定值）」 |
| **樂群 luqun-repair/dashboard（"本月工時統計"）** | `backend/app/services/luqun_repair_service.py` line 917<br>`frontend/src/pages/LuqunRepair/index.tsx` | 後端 service 加總，前端直接顯示 | 主：`花費工時`（Ragic 欄位，HR）<br>備：`工務處理天數 × 24` | `SUM(c.work_hours)` for this_month_cases，rounded to 2 decimal | **是** | 改名為「本月花費時間」；新增「待辦工時」欄位 |
| **大直 dazhi-repair/dashboard（"本月工時統計"）** | `backend/app/services/dazhi_repair_service.py` line 663<br>`frontend/src/pages/DazhiRepair/index.tsx` | 後端 service 加總，前端直接顯示 | 主：`維修天數 × 24`（Ragic 欄位）<br>備：`花費工時`（HR） | `SUM(c.work_hours)` for this_month_cases，rounded to 2 decimal | **是** | 改名為「本月花費時間」；新增「待辦工時」欄位 |

### 1-B. 共用邏輯彙整

| 邏輯 | 位置 | 說明 |
|------|------|------|
| 天數→小時轉換 | `ragic_data_service.py` `safe_work_days_to_hours()` | `days × 24`，上限 365 天，防止誤植年份 |
| 月份過濾 | `luqun_repair_service.py` `_stat_month()` / `dazhi_repair_service.py` 同邏輯 | 已完工 → 用 `completed_at`；未完工 → 用 `occurred_at` |
| 四個來源整合 | `work_category_analysis.py` | luqun + dazhi + hotel_room + ihg_room 統一加總 |

---

## 2. 欄位對應檢查

### 2-A. 時間欄位對應表

| 模組 | 報修時間欄位 | 完工時間欄位 | 目前程式是否正確 | 問題說明 |
|------|------------|------------|----------------|---------|
| **樂群工務報修** | `RK_OCCURRED_AT = "發生時間"`<br>aliases: `報修日期 / 發生時間 / 實際報修時間 / 報修時間 / 申報時間 / 建立時間` | `RK_COMPLETED_AT = "結案時間"`<br>aliases: `完工時間 / 結案時間 / 完成時間`<br>Fallback: `結案日期` → `驗收日期` | ✅ 有 alias 機制，欄位映射正確 | 主欄位為「發生時間」而非「報修時間」，兩者語意略有差異；建議確認 Ragic 實際欄位名稱 |
| **大直工務報修** | `RK_OCCURRED_AT = "報修日期"`<br>aliases: `報修日期 / 發生時間 / 報修時間 / 申報時間` | `RK_COMPLETED_AT = "維修日期"`<br>aliases: `完工時間 / 維修日期 / 結案時間 / 完成時間`<br>Fallback: `驗收日期` | ✅ 有 alias 機制，欄位映射正確 | 主欄位為「維修日期」，語意為「維修完成日期」，等同完工時間 |
| **Dashboard 匯總（ExecMetrics）** | 不直接使用時間欄位 | 不直接使用時間欄位 | ✅ 依賴子模組已計算的 `work_hours` | Dashboard 自身不做時間差運算，只加總 |

### 2-B. 工時欄位對應表

| 模組 | 主要工時來源 | 備用工時來源 | 轉換邏輯 |
|------|------------|------------|---------|
| **樂群** | `花費工時`（Ragic 直接填 HR） | `工務處理天數 × 24` | 若 `花費工時 ≤ 0` 才用天數換算 |
| **大直** | `維修天數 × 24` | `花費工時`（Ragic 直接填 HR） | 先算天數，若 `≤ 0` 才用直接工時 |
| **Dashboard** | luqun + dazhi 各自的 `work_hours` | + hotel_room + ihg_room（分鐘 ÷ 60） | 四來源全部合計 |

> ⚠️ **注意**：樂群與大直的優先順序相反。樂群優先用「直接填寫工時」，大直優先用「天數換算」。這是設計決策，並非 Bug。

---

## 3. 現況試算

> ⚠️ **說明**：本次程式碼盤點時，資料庫（`portal.db`）目前為空（尚未同步 Ragic 資料），無法取得本月實際數值。以下試算表以公式說明為主，待資料庫同步後可由 API 取得實際數字。

### 3-A. 試算表（待補實際數值）

| 模組 | 原本顯示名稱 | 原本數值 | 新名稱 | 新數值 | 差異說明 |
|------|------------|--------|-------|-------|---------|
| 樂群本月 | 本月工時統計 | *(需同步 Ragic 後查詢)* | 本月花費時間 | *(同原本數值，僅改名)* | 數值不變，改名 |
| 樂群本月 | —（新增） | — | 待辦工時 | *(需 `completed_at - occurred_at` 計算)* | 全新欄位 |
| 樂群本月 | —（新增） | — | 本期總工時 | **1,432 HR**（固定值） | 人工輸入，不來自報修資料 |
| 大直本月 | 本月工時統計 | *(需同步 Ragic 後查詢)* | 本月花費時間 | *(同原本數值，僅改名)* | 數值不變，改名 |
| 大直本月 | —（新增） | — | 待辦工時 | *(需 `completed_at - occurred_at` 計算)* | 全新欄位 |
| 大直本月 | —（新增） | — | 本期總工時 | **1,432 HR**（固定值） | 人工輸入，不來自報修資料 |
| Dashboard / ExecMetrics | 本期總工時 | *(需同步 Ragic 後查詢)* | 花費時間 | *(同原本計算，僅改名)* | 數值不變，改名 |
| Dashboard / ExecMetrics | —（新增） | — | 本期總工時 | **1,432 HR**（固定值） | 人工輸入 |

### 3-B. 待辦工時計算說明

```
待辦工時（per case）= completed_at - occurred_at（單位：小時）

本月待辦工時合計 = SUM(case.completed_at - case.occurred_at)
                   where case 屬於本月，且 completed_at IS NOT NULL
```

> **現有程式已有 `occurred_at` 和 `completed_at` 欄位**，後端的 `RepairCase` 物件已解析並儲存這兩個時間，計算待辦工時不需要新增欄位或修改 Ragic 同步邏輯，只需要在 service 層新增計算即可。

---

## 4. 新舊定義差異表

| 項目 | 舊定義 | 新定義 | 資料來源 | 是否需調整 | 畫面名稱變更 |
|------|-------|-------|---------|-----------|------------|
| **本期總工時** | 所有報修案件 work_hours 合計（luqun + dazhi + hotel + IHG） | 工程人員總工數，**固定值 1,432 HR** | 人工輸入（前期：常數；後期：設定檔或資料庫） | **是** | 維持「本期總工時」，但數值來源改變 |
| **本月工時統計**（樂群/大直各自） | 各模組本月報修案件 work_hours 合計 | 重新定位為「本月花費時間」 | 既有 API（`kpi.total_work_hours`），不改計算邏輯 | **是（改名）** | 本月工時統計 → **本月花費時間** |
| **花費時間** | 原本未獨立命名（即本月工時統計） | 明確定義為原本工時計算值，名稱統一 | 既有 API / service，不改計算邏輯 | 輕微調整 | Dashboard 層：原「本期總工時」→ **花費時間** |
| **待辦工時** | 無此欄位 | `completed_at - occurred_at`（案件從報修到完工的歷程時間） | Ragic 報修時間 + 完工時間（已存入 DB） | **是（新增）** | 新增「待辦工時」 |

---

## 5. 建議畫面命名

### 5-A. 各模組建議命名

| 現在畫面名稱 | 建議新名稱 | 所在模組 | 原因 |
|------------|---------|---------|------|
| 本期總工時（ExecMetrics） | **花費時間** | Dashboard / WorkCategoryAnalysis | 原本計算的是「案件花費時間加總」，並非工程人員出勤工數，改名以符合實際語意 |
| 本月工時統計（樂群） | **本月花費時間** | luqun-repair/dashboard | 避免與人工輸入的「本期總工時（1432）」混淆；「花費時間」強調是案件消耗時間 |
| 本月工時統計（大直） | **本月花費時間** | dazhi-repair/dashboard | 同上 |
| —（新增） | **本期總工時** | 所有模組 | 新增欄位，代表工程人員實際可用工時（1,432 HR）；數值固定，不依報修資料變動 |
| —（新增） | **待辦工時** | luqun-repair/dashboard, dazhi-repair/dashboard | 顯示每月案件從報修到完工的歷程時間合計；適合主管追蹤處理效率 |

### 5-B. 命名邏輯說明（給主管 Dashboard 閱讀）

```
本期總工時（1,432 HR）
  └─ 代表「工程團隊本期可用工時總量」（人工設定）

本月花費時間（XX HR）
  └─ 代表「本月所有報修案件花費的工時加總」（來自 Ragic 花費工時 / 維修天數）

待辦工時（XX HR）
  └─ 代表「本月案件從報修到完工的歷程時間合計」（完工時間 - 報修時間）
     → 數值通常遠大於花費時間（含等待、協調時間）
```

> **建議**：三個數字同時呈現，讓主管可以直觀比較：
> - 「花了多少工？」（花費時間）
> - 「歷程多久？」（待辦工時）
> - 「總共可用多少工？」（本期總工時）

---

## 6. 建議修改檔案清單

### 後端

| 檔案 | 修改內容 | 影響範圍 |
|------|---------|---------|
| `backend/app/services/luqun_repair_service.py` | 在 `compute_dashboard()` 新增 `total_pending_hours` 計算（`SUM(completed_at - occurred_at)` for 已完工案件） | 樂群 dashboard API 回傳值增加欄位 |
| `backend/app/services/dazhi_repair_service.py` | 同上，新增 `total_pending_hours` 計算 | 大直 dashboard API 回傳值增加欄位 |
| `backend/app/routers/work_category_analysis.py` | 新增 `total_hours_fixed = 1432` 常數，加入 API response | Dashboard 本期總工時改來源 |

### 前端

| 檔案 | 修改內容 | 影響範圍 |
|------|---------|---------|
| `frontend/src/pages/LuqunRepair/index.tsx` | KPI 卡片：「本月工時統計」改名「本月花費時間」；新增「待辦工時」卡片 | 樂群 dashboard 顯示 |
| `frontend/src/pages/DazhiRepair/index.tsx` | 同上 | 大直 dashboard 顯示 |
| `frontend/src/components/ExecMetrics/index.tsx` | 「本期總工時」改為「花費時間」（顯示原計算值）；新增「本期總工時 = 1432」 | 主管 Dashboard 顯示 |
| `frontend/src/pages/WorkCategoryAnalysis/index.tsx` | 「本期總工時」改為「花費時間」；新增「本期總工時 = 1432」 | 工作類別分析頁顯示 |
| `frontend/src/api/luqunRepair.ts` | 新增 `total_pending_hours` 型別定義 | TypeScript 型別 |
| `frontend/src/api/dazhiRepair.ts` | 同上 | TypeScript 型別 |

---

## 7. 最小修改方案

| 修改項目 | 建議位置 | 修改原因 | 是否必要 | 備註 |
|---------|---------|---------|---------|------|
| **本期總工時改為 1,432（固定值）** | 後端 `work_category_analysis.py` 加常數 `FIXED_TOTAL_HOURS = 1432`，前端 `ExecMetrics` 與 `WorkCategoryAnalysis` 顯示 | 新定義要求 | ✅ 必要 | 建議後端傳固定值，避免前端各自寫死；未來可升級為設定檔或 DB 維護 |
| **原本工時改名為「花費時間」** | 前端 Label 修改（`ExecMetrics` / `WorkCategoryAnalysis`） | 語意準確，避免與新「本期總工時」混淆 | ✅ 必要 | 後端 API key 可先不改（向下相容），只改前端顯示 label |
| **本月工時統計改名為「本月花費時間」** | 前端 Label 修改（`LuqunRepair` / `DazhiRepair`） | 語意準確 | ✅ 必要 | 後端 API key `total_work_hours` 先不改 |
| **待辦工時計算（新增）** | 後端 service 層：`luqun_repair_service.py` + `dazhi_repair_service.py` 新增計算；前端新增 KPI 卡片 | 新需求 | ✅ 必要 | 計算欄位 `occurred_at` / `completed_at` 已存在，不需新增同步欄位 |
| **Dashboard 顯示調整** | `ExecMetrics/index.tsx`：原「本期總工時」→「花費時間」；新增「本期總工時 = 1432」 | 新定義要求 | ✅ 必要 | 兩個卡片並排 |
| **luqun-repair/dashboard 顯示調整** | `LuqunRepair/index.tsx` | 新定義要求 | ✅ 必要 | — |
| **dazhi-repair/dashboard 顯示調整** | `DazhiRepair/index.tsx` | 新定義要求 | ✅ 必要 | — |

### 建議優先執行順序

```
Step 1：後端 service 新增 total_pending_hours（樂群 + 大直）
Step 2：後端 work_category_analysis 新增 FIXED_TOTAL_HOURS 常數並加入 response
Step 3：前端 API 型別新增 total_pending_hours
Step 4：前端各頁面改名（Label 調整）
Step 5：前端各頁面新增「待辦工時」KPI 卡片
Step 6：前端 ExecMetrics / WorkCategoryAnalysis 新增「本期總工時 = 1432」卡片
```

---

## 8. 風險與確認事項

### 8-1. 未完工案件如何計算待辦工時？

**現況**：`completed_at IS NULL` 的案件目前在 `work_hours` 加總時仍被計入。

**待辦工時的問題**：若案件未完工，`completed_at` 為空，`完工時間 - 報修時間` 無法計算。

**建議選項**：
| 選項 | 說明 | 優點 | 缺點 |
|------|------|------|------|
| A. 排除未完工案件 | 只計算已完工案件的歷程時間 | 數值穩定，不隨時間變動 | 未反映在途案件 |
| B. 以「現在時間」暫算 | 未完工案件以 `NOW() - occurred_at` 計算 | 反映即時處理狀況 | 數值會隨時間變動，每次計算結果不同 |
| C. 分開顯示 | 已完工：`completed_at - occurred_at`；未完工：顯示「進行中 X 小時」 | 資訊最完整 | 畫面較複雜 |

> ❓ **需使用者確認**：請確認未完工案件的待辦工時計算方式。**建議選 A（排除）**，較為保守且穩定。

---

### 8-2. 完工時間早於報修時間（異常資料）

**現況**：`completed_at < occurred_at` 的案件目前程式沒有特別處理，可能導致負數工時被計入 `work_hours`（若有直接填寫負數工時的話）。

**待辦工時的問題**：`completed_at - occurred_at < 0` → 負數工時。

**建議**：
- 異常資料（負數歷程時間）應從加總中排除（設為 0）
- 後端 service 新增資料品質檢查，記錄異常案件數量
- 可在 API response 中新增 `invalid_date_cases: int` 供前端顯示警示

> ❓ **需使用者確認**：是否需要在畫面上顯示「資料品質異常筆數」？

---

### 8-3. 時區問題

| 層面 | 現況 | 風險 |
|------|------|------|
| Ragic 時間格式 | 字串格式（如 `"2026/04/15 14:30:00"`），由 `_parse_dt()` 解析 | Ragic 為台灣時間（UTC+8）；若後端環境為 UTC，解析後需確認時區標記 |
| 後端 Python | SQLite 儲存為字串或 naive datetime | `julianday()` 計算不含時區，需確認兩個時間欄位的時區一致 |
| 前端 JavaScript | 顯示時直接用後端傳回的小時數，不做時區換算 | 低風險（只顯示小時數） |

**建議**：待辦工時計算建議在後端完成，避免前端跨時區問題。

> ❓ **需使用者確認**：Ragic 回傳的時間是否為台灣本地時間？後端環境時區設定是否為 UTC+8？

---

### 8-4. 日期格式問題

| 問題 | 現況 | 建議 |
|------|------|------|
| 空白值 | `_get_field()` 回傳 `""` 時，`_parse_dt()` 回傳 `None` | 已有處理，低風險 |
| 格式不一致 | `_parse_dt()` 支援多種格式（`%Y/%m/%d %H:%M:%S`、`%Y-%m-%d` 等） | 現有 alias 機制已覆蓋，低風險 |
| 中文日期格式 | 目前未見中文日期（如「2026年4月15日」），若 Ragic 有此格式需注意 | 建議確認 Ragic 不會回傳中文日期 |
| 只有日期無時間 | 部分欄位只有 `YYYY/MM/DD`，無時間部分 | 計算待辦工時時，若只有日期將產生精度損失（最小單位為天） |

> ❓ **需使用者確認**：樂群「結案時間」與大直「維修日期」是否包含時分秒？若只有日期，待辦工時精度僅到「天」。

---

### 8-5. 樂群與大直欄位名稱不同

**已確認差異**：

| 欄位 | 樂群 | 大直 |
|------|------|------|
| 報修時間主欄位 | `發生時間` | `報修日期` |
| 完工時間主欄位 | `結案時間` | `維修日期` |
| 工時主來源 | `花費工時`（HR，直接填） | `維修天數`（天，×24 換算） |

**現況評估**：
- ✅ 兩個 service 各自有 alias 機制，**不需要共用 mapping table**
- ✅ Dashboard 匯總不依賴欄位名稱，只用已計算的 `work_hours`
- ⚠️ 待辦工時計算也各自由 service 處理，不會互相影響
- 低風險

---

### 8-6. 單位問題

| 面向 | 現況 | 建議 |
|------|------|------|
| 顯示單位 | 樂群/大直：`hr`；ExecMetrics：`HR` | 建議統一為 `hr`（小寫），或依設計規範決定 |
| 小數位數 | 樂群/大直：2位小數；ExecMetrics：1位小數 | 建議統一為 **1位小數**（主管閱讀不需過細） |
| 待辦工時單位 | 未定義 | 建議以 `hr` 顯示，精度 1 位小數 |
| 本期總工時（1432） | — | 顯示為整數 `1,432 HR`（無小數） |

> ❓ **需使用者確認**：單位是否統一為 `hr`？小數位數是否統一？

---

### 8-7. 資料來源一致性

**風險說明**：

| 場景 | 風險 |
|------|------|
| 主管在 Dashboard 看到「花費時間 XX hr」 | 這是 luqun + dazhi + hotel_room + ihg_room 四個來源合計 |
| 主管在樂群 dashboard 看到「本月花費時間 YY hr」 | 這只是樂群的部分 |
| 兩個數字相加不等於 Dashboard 的數字 | 正常（Dashboard 還含 hotel_room + ihg_room） |

**建議**：在 Dashboard 的「花費時間」卡片加上 tooltip 或副標，說明「包含工務報修 + 客房保養」，避免主管誤解。

---

## 9. 本期總工時固定值建議存放位置

**選項比較**：

| 選項 | 位置 | 優點 | 缺點 | 建議優先序 |
|------|------|------|------|-----------|
| A. 前端常數 | `ExecMetrics/index.tsx` 或共用 `constants.ts` | 最快實作 | 後端/API 不知道這個值；若需記錄歷史則困難 | 3（不建議） |
| B. 後端 service 常數 | `work_category_analysis.py` 頂部 `FIXED_TOTAL_HOURS = 1432` | 快速，後端統一管理；API response 可回傳此值 | 修改需要重新部署後端 | 2（短期可用） |
| C. 後端設定檔（.env） | `.env` 加入 `TOTAL_ENGINEER_HOURS=1432` | 不需改程式就能修改 | 需要重啟服務 | 1（**建議**） |
| D. 資料庫設定表（未來） | `system_config` 表，key-value 結構 | 可在後台 UI 修改，不需部署 | 需新增 model + API | 未來可升級 |

**建議**：**短期用選項 C（.env）**，在 `.env` 加入 `TOTAL_ENGINEER_HOURS=1432`，後端 `settings.py` 讀取，並加入 API response。未來業務需求增加時可升級為選項 D。

---

## 9. 等待確認事項

請確認以下問題後，再開始 coding：

| # | 問題 | 選項 | 預設建議 |
|---|------|------|---------|
| 1 | 未完工案件的待辦工時計算方式？ | A. 排除 / B. 以現在時間暫算 / C. 分開顯示 | 建議 **A（排除）** |
| 2 | 完工時間早於報修時間的異常資料如何處理？ | 排除 / 計入（負數）/ 顯示警示 | 建議 **排除，後端記錄筆數** |
| 3 | 是否需要在畫面上顯示「資料品質異常筆數」？ | 是 / 否 | 建議 **否（第一版先不顯示）** |
| 4 | Ragic 「結案時間」（樂群）與「維修日期」（大直）是否含時分秒？ | 確認格式 | 待確認 |
| 5 | 後端環境時區是否為 UTC+8？ | 確認 | 待確認 |
| 6 | 顯示單位是否統一為 `hr`？小數位數統一為 1 位？ | 確認 | 建議 **是** |
| 7 | 「本期總工時 1,432 HR」存放位置？ | .env / 後端常數 / 前端常數 / DB | 建議 **.env** |
| 8 | 待辦工時是否只顯示在樂群/大直子頁面，還是也要出現在主 Dashboard？ | 確認 | 待確認 |
| 9 | Dashboard「花費時間」是否要加副標說明包含 hotel_room + ihg_room？ | 確認 | 建議 **是** |

---

## 附錄：資料流程圖（文字版）

```
Ragic 報修資料（樂群 / 大直）
  │
  ├─ 報修時間（occurred_at）
  └─ 完工時間（completed_at）
        │
        ├─ 待辦工時（新）
        │    = completed_at - occurred_at
        │    → 後端 service 新增計算
        │    → 只計入已完工且時間合理的案件
        │
        └─ 花費工時（原本工時欄位）
             = 花費工時 HR（樂群主）or 維修天數×24（大直主）
             → 後端已有計算，不改邏輯
             → 改名為「本月花費時間」

Ragic 報修資料 + 房務保養資料
  │
  └─ 花費時間（Dashboard 層，原「本期總工時」）
       = SUM(work_hours, 四個來源)
       → 後端 work_category_analysis.py 已有計算，不改邏輯
       → 改名為「花費時間」

人工設定
  └─ 本期總工時（新定義）
       = 1,432 HR（固定值）
       → 後端從 .env 讀取
       → 加入 API response
       → 前端顯示為新的「本期總工時」
```

---

*本報告為規劃草稿，不含任何程式修改。請確認上述等待確認事項後，再進行 coding。*
