# Portal Dashboard 修改 Todo List
## hotel/overview vs mall/overview 差異修正清單

> 產出日期：2026-05-06
> 來源：`docs/COMPARE_hotel_overview_vs_mall_overview.md`
> 使用方式：找到要修的項目，複製「Claude 提示詞」欄直接貼給 Claude 執行

---

## 評分說明

**嚴重性（1–5）**
| 分數 | 說明 |
|:---:|------|
| 5 | 數據錯誤、功能完全壞掉、主管看到會誤判 |
| 4 | 重要功能不完整、統計有偏差 |
| 3 | 一致性問題、操作體驗差 |
| 2 | 命名不統一、UI細節差異 |
| 1 | 程式碼整理、可讀性問題 |

**容易度（1–5）**
| 分數 | 說明 |
|:---:|------|
| 5 | 極易（1–5行修改，不影響邏輯） |
| 4 | 容易（10行內，邏輯清楚） |
| 3 | 中等（需改前端或後端，邏輯需理解） |
| 2 | 較難（需同時改前後端，或重構邏輯） |
| 1 | 困難（架構調整、需大量測試） |

---

## 完整 Todo 大表

---

### 🔴 P0 — 必修（數據錯誤 / 功能壞掉）

---

#### T01 ｜ 飯店 PPTX 後端 endpoint 缺失

| 欄位 | 內容 |
|------|------|
| **優先級** | P0 |
| **嚴重性** | ⭐⭐⭐⭐⭐ 5 |
| **容易度** | ⭐⭐⭐ 3（builder 已存在，需掛接 endpoint） |
| **模組** | hotel/overview |
| **影響 TAB** | Dashboard（頁頂匯出按鈕） |
| **問題** | 前端有「匯出 PowerPoint」按鈕，API client 有 `exportHotelOverviewPptx()`，但後端 `hotel_overview.py` 只有 3 個 GET endpoint，沒有 `@router.post("/overview/export/pptx")`，點擊必定回傳 404 |
| **檔案位置** | `backend/app/routers/hotel_overview.py` |
| **預估工時** | 1–2 小時 |

**Claude 提示詞：**
```
請在 backend/app/routers/hotel_overview.py 補上 PPTX 匯出的 POST endpoint。

目前檔案只有：
  @router.get("/daily-hours")
  @router.get("/monthly-hours")
  @router.get("/person-hours")

需要新增：
  @router.post("/overview/export/pptx")

做法：
1. 在現有三個 GET endpoint 之後、PPTX 工具函式之前，新增一個 POST endpoint
2. 函式簽名參照現有的 HotelPptxPayload、_build_hotel_pptx、get_hotel_daily_hours、get_hotel_monthly_hours、get_hotel_person_hours
3. 參考 mall_overview.py 的結構（若 mall 已有此 endpoint），或自行建構：
   - 接收 year: int, month: int Query 參數
   - 接收 body: HotelPptxPayload
   - 呼叫 get_hotel_daily_hours / get_hotel_monthly_hours / get_hotel_person_hours 取得資料
   - 呼叫 _build_hotel_pptx(year, month, daily, monthly, persons, kpi_payload=body) 產生 BytesIO
   - 回傳 StreamingResponse，Content-Type = application/vnd.openxmlformats-officedocument.presentationml.presentation
   - 設定 Content-Disposition header，檔名為 飯店管理報告_{year}年{month:02d}月.pptx（URL encode）
4. 不修改任何現有邏輯，只新增此 endpoint
5. 更新 README.md 最後更新日期與最近變更，更新 docs/CHANGELOG.md
```

---

#### T02 ｜ 飯店 PPTX 報告佔位卡出現「商場」字眼

| 欄位 | 內容 |
|------|------|
| **優先級** | P0 |
| **嚴重性** | ⭐⭐⭐⭐⭐ 5 |
| **容易度** | ⭐⭐⭐⭐⭐ 5（2行修改） |
| **模組** | hotel/overview |
| **影響 TAB** | PPTX Slide 2 |
| **問題** | `hotel_overview.py` 第 760 行的 PPTX builder 將佔位卡名稱硬編碼為「商場主管交辦」「商場緊急事件」，這份報告是飯店管理報告，名稱應該是「飯店主管交辦」「飯店緊急事件」 |
| **檔案位置** | `backend/app/routers/hotel_overview.py` 第 760–761 行 |
| **預估工時** | 5 分鐘 |

**Claude 提示詞：**
```
請修改 backend/app/routers/hotel_overview.py 第 760 行附近的佔位卡名稱。

找到這段程式碼：
    for pname in ["商場主管交辦", "商場緊急事件"]:

改為：
    for pname in ["飯店主管交辦", "飯店緊急事件"]:

這段程式碼在 _build_slide2_kpi 函式內（hotel PPTX Slide 2 的 Layer 2 部分）。
這是一個命名錯誤，飯店管理報告不應出現「商場」字眼。
修改後更新 docs/CHANGELOG.md。
```

---

#### T03 ｜ 飯店 API 文件說「六項來源」實際只有五項

| 欄位 | 內容 |
|------|------|
| **優先級** | P0 |
| **嚴重性** | ⭐⭐⭐⭐ 4 |
| **容易度** | ⭐⭐⭐⭐⭐ 5（3行文字修改） |
| **模組** | hotel/overview |
| **影響 TAB** | API 文件（Swagger） |
| **問題** | `hotel_overview.py` 的三個 endpoint summary 都寫「六項來源」，但 `HOTEL_CATEGORIES` 只有 5 個元素（飯店週期保養、IHG客房保養、飯店每日巡檢、保全巡檢、飯店工務部）。檔案開頭 docstring 也說「五項來源」，summary 說「六項」，兩邊矛盾 |
| **檔案位置** | `backend/app/routers/hotel_overview.py` 第 80、270、443 行 |
| **預估工時** | 5 分鐘 |

**Claude 提示詞：**
```
請修改 backend/app/routers/hotel_overview.py 中三個 endpoint 的 summary 說明文字。

找到並修改：
  第 80 行：summary="飯店管理 — 每日工時彙總（六項來源）"
  改為：  summary="飯店管理 — 每日工時彙總（五項來源）"

  第 270 行：summary="飯店管理 — 每月工時彙總（六項來源）"
  改為：   summary="飯店管理 — 每月工時彙總（五項來源）"

  第 443 行：summary="飯店管理 — 人員工時佔比（六項來源，Top-15）"
  改為：   summary="飯店管理 — 人員工時佔比（五項來源，Top-15）"

背景：HOTEL_CATEGORIES 只有 5 個元素，與「六項」說法矛盾。
僅修改這 3 行的 summary 字串，不動其他邏輯。
修改後更新 docs/CHANGELOG.md。
```

---

#### T04 ｜ 商場人員排名僅統計報修人員，PM/巡檢隱形

| 欄位 | 內容 |
|------|------|
| **優先級** | P0 |
| **嚴重性** | ⭐⭐⭐⭐⭐ 5 |
| **容易度** | ⭐⭐ 2（需改前端渲染邏輯，並確認 API 資料格式） |
| **模組** | mall/overview |
| **影響 TAB** | 人員排名 Tab（E） |
| **問題** | `MallMgmtDashboard` 的人員排名 Tab 使用 `luqunData?.top_hours`（商場工務報修 Dashboard API），只能看到報修人員的排名。但 `/mall/person-hours` API 已彙整全部5來源（現場報修、例行維護、每日巡檢）的人員工時，PM執行人員與巡檢人員完全不在排名中，排名嚴重失真 |
| **檔案位置** | `frontend/src/pages/MallMgmtDashboard/index.tsx` 第 488–503 行 |
| **預估工時** | 3–4 小時 |

**Claude 提示詞：**
```
請修改 frontend/src/pages/MallMgmtDashboard/index.tsx 的人員排名 Tab（Tab E），將資料來源從 luqunData.top_hours 改為 /mall/person-hours API。

目前問題：
  第 488–503 行的 personRanking useMemo 使用 luqunData?.top_hours（僅報修1來源）
  導致 PM 執行人員、巡檢人員完全不在排名中

修改方向（參考飯店 HotelMgmtDashboard 的 TabRanking 實作）：
1. personRanking 的資料改用 personHoursData（已有的 MallPersonHoursData state，/mall/person-hours）
2. 人員排名的欄位：排名、人員姓名、全年工時(HR)、占比%、（各來源工時分解）
3. personHoursData.persons 即為 Top-15 人員名單，personHoursData.person_totals 為各人工時
4. 保留原有的 Alert 說明文字，但更新為：「人員工時排名彙整現場報修、例行維護、每日巡檢三項來源（Top-15，依全年合計工時降冪）」
5. 新增橫向 BarChart（可選，參考 HotelMgmtDashboard TabRanking 的圖表設計）
6. Tab E「人員排名」的 handleTabChange 已包含 person_pct key 的載入，確認 ranking Tab 也有正確載入 personHoursData

注意：
- 不刪除 luqunData 的報修排名，可保留作為其中一欄或保留在 Alert 提示中
- 不修改後端任何程式
- 修改後更新 README.md 最後更新與 docs/CHANGELOG.md
```

---

#### T05 ｜ 商場 TypeScript 型別缺少 person_totals 欄位

| 欄位 | 內容 |
|------|------|
| **優先級** | P0 |
| **嚴重性** | ⭐⭐⭐⭐ 4 |
| **容易度** | ⭐⭐⭐⭐⭐ 5（1行新增） |
| **模組** | mall/overview |
| **影響 TAB** | 人員工時% / 人員排名 |
| **問題** | `api/mallOverview.ts` 的 `MallPersonHoursData` interface 缺少 `person_totals: number[]` 欄位，但後端 `/mall/person-hours` 確實有回傳此欄位（`"person_totals": [round(person_totals[p], 1) for p in persons]`）。飯店的 `HotelPersonHoursData` 有此欄位 |
| **檔案位置** | `frontend/src/api/mallOverview.ts` MallPersonHoursData interface |
| **預估工時** | 5 分鐘 |

**Claude 提示詞：**
```
請修改 frontend/src/api/mallOverview.ts，在 MallPersonHoursData interface 補上缺少的 person_totals 欄位。

找到：
  export interface MallPersonHoursData {
    year:    number
    persons: string[]
    rows:    MallPersonRow[]
  }

改為：
  export interface MallPersonHoursData {
    year:          number
    persons:       string[]
    person_totals: number[]   // 各人員全年合計工時（HR），與 persons 索引對應
    rows:          MallPersonRow[]
  }

背景：後端 /mall/person-hours 已有回傳 person_totals，飯店 HotelPersonHoursData 也有此欄位，商場型別缺失導致型別不安全。
```

---

### 🟠 P1 — 建議修（一致性與維護性）

---

#### T06 ｜ 商場 PPTX 後端 endpoint 缺失且前端按鈕未渲染

| 欄位 | 內容 |
|------|------|
| **優先級** | P1 |
| **嚴重性** | ⭐⭐⭐⭐ 4 |
| **容易度** | ⭐⭐ 2（前後端都要補） |
| **模組** | mall/overview |
| **影響 TAB** | Dashboard |
| **問題** | 前端有 `handleExportPptx` 函式、API client 有 `exportMallOverviewPptx()`、後端有 `_build_mall_pptx()` builder，但：① 後端沒有 `@router.post` endpoint ② 前端 UI 沒有渲染匯出按鈕（`handleExportPptx` 從未被呼叫）。整個功能是死碼 |
| **檔案位置** | `backend/app/routers/mall_overview.py`；`frontend/src/pages/MallMgmtDashboard/index.tsx` |
| **預估工時** | 2–3 小時 |

**Claude 提示詞：**
```
商場管理 Dashboard 的 PPTX 匯出功能已有前端函式（handleExportPptx）和後端 builder（_build_mall_pptx），但缺少兩個關鍵：
① 後端沒有 @router.post endpoint
② 前端沒有渲染匯出按鈕

請同時補上這兩個部分：

【後端】backend/app/routers/mall_overview.py：
在現有三個 GET endpoint 之後新增 POST endpoint，參考 hotel_overview.py 的 export endpoint 結構：
- 路徑：POST /overview/export/pptx
- 參數：year: int, month: int（Query），body: MallPptxPayload
- 邏輯：呼叫 get_mall_daily_hours / get_mall_monthly_hours / get_mall_person_hours，再呼叫 _build_mall_pptx()
- 回傳：StreamingResponse，檔名「商場管理報告_{year}年{month:02d}月.pptx」

【前端】frontend/src/pages/MallMgmtDashboard/index.tsx：
在 TabDashboard 的篩選列 Card 右側補上匯出按鈕，參考 HotelMgmtDashboard 的按鈕樣式：
- Button，icon FilePptOutlined，loading={exportLoading}，disabled={month === 0}
- 樣式：background linear-gradient(135deg, #667eea, #764ba2)，color #fff，border none
- onClick：呼叫 handleExportPptx（函式已存在）
- 文字：匯出 PowerPoint

不修改任何現有邏輯，只新增 endpoint 與按鈕。
更新 README.md 最後更新日期、docs/CHANGELOG.md。
```

---

#### T07 ｜ Tab key 命名不統一（overview/person vs dashboard/person_pct）

| 欄位 | 內容 |
|------|------|
| **優先級** | P1 |
| **嚴重性** | ⭐⭐ 2 |
| **容易度** | ⭐⭐⭐⭐ 4（字串替換，需注意 handleTabChange） |
| **模組** | hotel/overview |
| **影響 TAB** | 全部 Tab |
| **問題** | Hotel Tab key：`overview`（Dashboard）、`person`（人員工時%）。Mall Tab key：`dashboard`、`person_pct`。命名不統一，增加維護負擔 |
| **檔案位置** | `frontend/src/pages/HotelMgmtDashboard/index.tsx` |
| **預估工時** | 30 分鐘 |

**Claude 提示詞：**
```
請修改 frontend/src/pages/HotelMgmtDashboard/index.tsx 的 Tab key 命名，與 mall/overview 統一。

修改對應：
  key: 'overview'  →  key: 'dashboard'
  key: 'person'    →  key: 'person_pct'

需要同時修改以下幾處（用搜尋替換確保不遺漏）：
1. tabItems 陣列中的 key 欄位
2. handleTabChange 函式中的字串比較（if key === 'overview' → 'dashboard'，if key === 'person' → 'person_pct'）
3. loadedTabs.current 相關的 key 字串（若有用到）
4. useState 初始值（若有 defaultActiveKey）

注意：只修改 Tab key 字串，不修改 label、children 或任何邏輯。
不修改後端任何程式。更新 docs/CHANGELOG.md。
```

---

#### T08 ｜ 每日/每月累計表缺少 cases_pct 欄位

| 欄位 | 內容 |
|------|------|
| **優先級** | P1 |
| **嚴重性** | ⭐⭐⭐ 3 |
| **容易度** | ⭐⭐ 2（需同時改後端 API 回傳 + 前端表格欄位） |
| **模組** | hotel/overview |
| **影響 TAB** | B. 每日累計、C. 每月累計 |
| **問題** | 商場的 B/C Tab 每列有 `cases_pct` 欄位（案件佔比%），飯店後端未回傳、前端表格也無此欄。兩邊應一致 |
| **檔案位置** | `backend/app/routers/hotel_overview.py`；`frontend/src/pages/HotelMgmtDashboard/index.tsx` |
| **預估工時** | 2 小時 |

**Claude 提示詞：**
```
請為飯店管理 Dashboard 的 B. 每日累計 和 C. 每月累計 補上 cases_pct（案件佔比%）欄位，與商場 mall/overview 對齊。

【後端】backend/app/routers/hotel_overview.py：

1. get_hotel_daily_hours 函式：
   - 計算 grand_cases_tot（所有來源案件加總），仿照 mall_overview.py 的寫法
   - 在每個 result_rows 的 row 加入 "cases_pct": round(row["cases_total"] / grand_cases_tot * 100, 1) if grand_cases_tot else 0.0
   - TOTAL 列的 cases_pct 設為 100.0

2. get_hotel_monthly_hours 函式：
   - 同樣的邏輯，計算各月 cases_pct

【前端】frontend/src/pages/HotelMgmtDashboard/index.tsx：

1. HotelDailyRow interface（或 type）：補上 cases_pct: number
2. HotelMonthlyRow interface：補上 cases_pct: number
3. buildDailyCols()：在「案件合計」欄後面加一欄「%」，dataIndex: 'cases_pct'，寬度參考商場的做法（54px）
4. buildMonthlyCols()：同樣在案件合計後加 cases_pct 欄

不修改其他任何邏輯。更新 README.md 與 docs/CHANGELOG.md。
```

---

#### T09 ｜ 飯店篩選在頁頂，商場各 Tab 可獨立篩選

| 欄位 | 內容 |
|------|------|
| **優先級** | P1 |
| **嚴重性** | ⭐⭐ 2 |
| **容易度** | ⭐⭐ 2（需在各 Tab 內加篩選元件，邏輯改動較大） |
| **模組** | hotel/overview |
| **影響 TAB** | B. 每日累計、C. 每月累計、D. 每年累計、人員工時%、人員排名 |
| **問題** | Hotel 所有 Tab 共用頁頂的 year/month 篩選，切換月份會影響所有 Tab。Mall 的 B/C/D/人員 Tab 各自有獨立篩選，更彈性。主管可能希望「月報」和「年報」同時顯示不同期間 |
| **檔案位置** | `frontend/src/pages/HotelMgmtDashboard/index.tsx` |
| **預估工時** | 4–6 小時 |

**Claude 提示詞：**
```
請為飯店管理 Dashboard（frontend/src/pages/HotelMgmtDashboard/index.tsx）的各工時統計 Tab 加上獨立篩選，參考商場 MallMgmtDashboard 的設計。

目前問題：B/C/D/人員 Tab 共用頁頂的 year/month state，切換任一篩選會影響所有 Tab。

需要修改：

1. B. 每日累計 Tab（key='daily'）：
   - 在 TabBDaily 函式內頂部加一個篩選 Card（參考 mall 的 dailyYear/dailyMonth 設計）
   - 新增獨立 state：tabBYear, tabBMonth（預設值 = 當前頁頂 year/month）
   - 篩選觸發時呼叫 fetchHotelDailyHours(tabBYear, tabBMonth)

2. C. 每月累計 Tab（key='monthly'）：
   - 新增獨立 state：tabCYear
   - 在 TabCMonthly 函式內頂部加年份篩選

3. D. 每年累計 Tab（key='yearly'）：維持現有的 yearlyYear 獨立 state，不需改動

4. 人員工時% Tab（key='person_pct'）：
   - 新增獨立 state：personYear
   - 在 TabDPerson 內頂部加年份篩選

5. 人員排名 Tab（key='ranking'）：
   - 與人員工時% 共用 personYear state

頁頂的 year/month 篩選保留，供 Dashboard Tab 主視圖使用（各來源 KPI 卡）。

注意：
- 不修改後端
- 不修改 Dashboard Tab 的邏輯
- 更新 README.md 最後更新與 docs/CHANGELOG.md
```

---

#### T10 ｜ 商場人員排名 Tab 缺少橫向 BarChart

| 欄位 | 內容 |
|------|------|
| **優先級** | P1 |
| **嚴重性** | ⭐⭐ 2 |
| **容易度** | ⭐⭐⭐ 3 |
| **模組** | mall/overview |
| **影響 TAB** | 人員排名 Tab（E） |
| **問題** | 飯店人員排名 Tab 有橫向 BarChart（展示各人員各來源工時分解），商場只有表格，視覺化較差（此項建議先完成 T04 再做） |
| **檔案位置** | `frontend/src/pages/MallMgmtDashboard/index.tsx` |
| **預估工時** | 2–3 小時（需先完成 T04） |

**Claude 提示詞：**
```
請在商場管理 Dashboard（frontend/src/pages/MallMgmtDashboard/index.tsx）的人員排名 Tab（TabRanking）補上橫向 BarChart，參考飯店 HotelMgmtDashboard TabRanking 的圖表設計。

前提：T04 已完成（人員排名改用 /mall/person-hours API，personHoursData 已有正確資料）

圖表設計：
1. 使用 recharts BarChart（layout="vertical"）
2. X 軸：工時（HR）
3. Y 軸：人員姓名（personHoursData.persons）
4. Bar：各來源顏色與 MALL_CATEGORY_TAG_COLORS 對應（現場報修/例行維護/每日巡檢）
5. 圖表放在表格上方，高度 220px，用 ResponsiveContainer 包覆
6. Card 標題：「人員工時分解（HR）」

商場來源顏色參考（MALL_CATEGORY_TAG_COLORS）：
  現場報修：#FA8C16
  上級交辦：#52C41A（固定0，可省略）
  緊急事件：#FF4D4F（固定0，可省略）
  例行維護：#1B3A5C
  每日巡檢：#722ED1

不修改後端。更新 docs/CHANGELOG.md。
```

---

#### T11 ｜ _parse_minutes 重複複製，應抽共用

| 欄位 | 內容 |
|------|------|
| **優先級** | P1 |
| **嚴重性** | ⭐ 1 |
| **容易度** | ⭐⭐⭐ 3（需確認 import 路徑不影響現有邏輯） |
| **模組** | 兩邊後端 |
| **影響 TAB** | 無（維護性問題） |
| **問題** | `_parse_minutes()` 函式在 `hotel_overview.py` 與 `mall_overview.py` 各複製一份，連註解都一樣（「複製自 mall_overview.py 同名函式，避免跨 router import」）。若有 bug 需兩邊同步修改 |
| **檔案位置** | `backend/app/routers/hotel_overview.py`；`backend/app/routers/mall_overview.py` |
| **預估工時** | 1 小時 |

**Claude 提示詞：**
```
請將 hotel_overview.py 和 mall_overview.py 中重複的 _parse_minutes() 函式抽到共用的 service 模組。

步驟：
1. 在 backend/app/services/ 建立 time_utils.py（若已存在則新增函式）
2. 將 _parse_minutes() 函式移入 time_utils.py，保留完整 docstring
3. 在 hotel_overview.py 刪除重複的 _parse_minutes 定義，改為：
   from app.services.time_utils import parse_minutes as _parse_minutes
4. 在 mall_overview.py 同樣替換

注意：
- 函式簽名、邏輯、跨日處理邏輯（diff + 24*60 if diff < 0）必須完全相同
- 不修改任何呼叫端的程式碼
- 更新 docs/TECH_SPEC.md 在「服務層」表格加入 time_utils.py
- 更新 docs/CHANGELOG.md
```

---

#### T12 ｜ PPTX 工具函式重複，應抽共用

| 欄位 | 內容 |
|------|------|
| **優先級** | P1 |
| **嚴重性** | ⭐ 1 |
| **容易度** | ⭐⭐ 2（需重構，但邏輯清楚） |
| **模組** | 兩邊後端 |
| **影響 TAB** | 無（維護性問題） |
| **問題** | Hotel 有 `_pptx_txt / _pptx_rect / _pptx_header / _pptx_cell / _pptx_header_row`，Mall 有 `_mall_pptx_txt / _mall_pptx_rect / _mall_pptx_header / _mall_pptx_cell / _mall_pptx_header_row`，邏輯完全相同，只差函式名稱前綴 |
| **檔案位置** | `backend/app/routers/hotel_overview.py`；`backend/app/routers/mall_overview.py` |
| **預估工時** | 1.5 小時 |

**Claude 提示詞：**
```
請將 hotel_overview.py 和 mall_overview.py 中重複的 PPTX 工具函式抽到共用模組。

步驟：
1. 建立 backend/app/services/pptx_utils.py
2. 將以下函式從 hotel_overview.py 移入（使用不帶前綴的名稱）：
   _pptx_txt     → pptx_txt
   _pptx_rect    → pptx_rect
   _pptx_header  → pptx_header
   _pptx_cell    → pptx_cell
   _pptx_header_row → pptx_header_row

3. hotel_overview.py：刪除重複定義，改為：
   from app.services.pptx_utils import pptx_txt as _pptx_txt, pptx_rect as _pptx_rect, ...

4. mall_overview.py：刪除 _mall_pptx_txt 等5個函式，改用相同的 import（別名為 _mall_pptx_txt 等保持呼叫端不變）

5. 注意 _pptx_header 中 hotel/mall 有不同的 footer 文字（「飯店管理系統」vs「商場管理系統」），
   _pptx_header 抽出後需加入 system_name: str 參數，預設值可設 "管理系統"，
   hotel 傳入 "飯店管理系統"，mall 傳入 "商場管理系統"

更新 docs/TECH_SPEC.md，更新 docs/CHANGELOG.md。
```

---

#### T13 ｜ 飯店每年累計設計與商場不同

| 欄位 | 內容 |
|------|------|
| **優先級** | P1 |
| **嚴重性** | ⭐⭐ 2 |
| **容易度** | ⭐⭐ 2（需確認主管需求後才能動） |
| **模組** | hotel/overview |
| **影響 TAB** | D. 每年累計 |
| **問題** | Hotel 的每年累計 Tab 顯示單一年份的月累計滾計（1月累計、2月累計…12月累計）；Mall 的每年累計 Tab 顯示過去3年並排比較（baseyear-2、-1、0年）。兩種設計意圖不同，需主管確認偏好 |
| **檔案位置** | `frontend/src/pages/HotelMgmtDashboard/index.tsx` TabDYearly 函式 |
| **預估工時** | 需業主確認後才能估計 |

**Claude 提示詞（待業主確認後使用）：**
```
【等待業主確認設計需求後執行】

請將飯店管理 Dashboard（frontend/src/pages/HotelMgmtDashboard/index.tsx）的 D. 每年累計 Tab 改為「三年並排比較」設計，與商場 MallMgmtDashboard 對齊。

改動範圍：
1. 新增獨立 state：yearlyBaseYear（預設今年）、yearlyDataMap（Record<number, HotelMonthlyHoursData | null>）
2. 載入函式：同時 fetch baseyear-2、baseyear-1、baseyear 三年的 /hotel/monthly-hours
3. 表格欄位：工項類別 | 1月 | 2月 | … | 12月 | 全年合計（三年各一份，或三年並排顯示）
4. 年份選擇器：Select 選擇基準年
5. 參考 MallMgmtDashboard 的 TabYearly / buildMallYearlyCols() 實作

保留原有的 TabDYearly 程式碼先注解不刪，確認正確後再移除。
不修改後端。更新 docs/CHANGELOG.md。
```

---

#### T14 ｜ 飯店月份格式無容錯邏輯

| 欄位 | 內容 |
|------|------|
| **優先級** | P1 |
| **嚴重性** | ⭐⭐⭐ 3 |
| **容易度** | ⭐⭐⭐⭐ 4（模式清楚，照 mall 做法複製） |
| **模組** | hotel/overview |
| **影響 TAB** | B. 每日累計、C. 每月累計 |
| **問題** | `hotel_overview.py` 查詢月份批次時使用 `period_month == period_prefix`（exact match，YYYY/MM 零填充），若資料庫有 YYYY/M 格式（如 `2026/4`）則遺漏。商場有容錯邏輯 |
| **檔案位置** | `backend/app/routers/hotel_overview.py` |
| **預估工時** | 1 小時 |

**Claude 提示詞：**
```
請為飯店管理 Dashboard 後端（backend/app/routers/hotel_overview.py）的週期保養批次查詢補上月份格式容錯邏輯，與商場 mall_overview.py 對齊。

目前飯店使用 exact match：
  PeriodicMaintenanceBatch.period_month == period_prefix  （YYYY/MM）

商場的做法是先用 LIKE 查全年，再用 Python 過濾月份：
  .filter(MallPeriodicMaintenanceBatch.period_month.like(f"{year}/%"))
  .all()
  然後 int(b.period_month.split("/")[1]) == month 過濾

請在 get_hotel_daily_hours 和 get_hotel_monthly_hours 兩個函式中：
1. 將飯店週期保養批次查詢改為 LIKE 方式：
   PeriodicMaintenanceBatch.period_month.like(f"{year}/%")
2. 再用 Python 判斷月份是否符合

不修改其他來源（IHG、巡檢、報修等）的查詢邏輯。
不修改前端。更新 docs/CHANGELOG.md。
```

---

### 🟡 P2 — 可優化（版型、體驗、整理）

---

#### T15 ｜ 飯店工務部來源名稱不一致

| 欄位 | 內容 |
|------|------|
| **優先級** | P2 |
| **嚴重性** | ⭐⭐ 2 |
| **容易度** | ⭐⭐⭐⭐⭐ 5（1行修改） |
| **模組** | hotel/overview |
| **影響 TAB** | Dashboard（來源卡） |
| **問題** | `adaptDazhi` 函式回傳 `source_name: '工務部'`，但後端 `HOTEL_CATEGORIES` 第5項是 `'飯店工務部'`，前後端命名不一致 |
| **檔案位置** | `frontend/src/pages/HotelMgmtDashboard/index.tsx` adaptDazhi 函式 |
| **預估工時** | 5 分鐘 |

**Claude 提示詞：**
```
請修改 frontend/src/pages/HotelMgmtDashboard/index.tsx 中 adaptDazhi 函式的 source_name 欄位。

找到：
  source_name: '工務部',

改為：
  source_name: '飯店工務部',

這樣與後端 HOTEL_CATEGORIES 的第5項「飯店工務部」一致。
只修改這1行，不動其他邏輯。
```

---

#### T16 ｜ SourceCard 未抽成共用 React Component

| 欄位 | 內容 |
|------|------|
| **優先級** | P2 |
| **嚴重性** | ⭐ 1 |
| **容易度** | ⭐ 1（重構量大，需測試兩個模組） |
| **模組** | 兩邊前端 |
| **影響 TAB** | Dashboard |
| **問題** | Hotel 和 Mall 的來源狀態卡（SourceCard：顏色條、工項數、完成率進度條、異常/工時顯示）各自在元件內實作，程式碼重複，維護成本高 |
| **檔案位置** | `frontend/src/pages/HotelMgmtDashboard/index.tsx`；`frontend/src/pages/MallMgmtDashboard/index.tsx` |
| **預估工時** | 4–6 小時 |

**Claude 提示詞：**
```
請將飯店管理與商場管理 Dashboard 共用的「來源狀態卡」UI 抽成共用 React Component。

步驟：
1. 建立 frontend/src/components/SourceStatusCard/index.tsx
2. Props interface（參考兩邊現有的 NormalizedSource / NormalizedSummary）：
   interface SourceStatusCardProps {
     source_key:      string
     source_name:     string
     source_color:    string
     case_count:      number      // -1 = 不適用（顯示佔位）
     completed_count: number
     work_hours:      number      // -1 = 不適用
     actual_hours?:   number
     completion_rate: number      // -1 = 不適用
     abnormal_count:  number
     overdue_count:   number
     status_label:    string
     is_placeholder?: boolean
     loading?:        boolean
     error?:          string | null
     onClick?:        () => void  // 點擊後導航到子模組
   }
3. 實作：顏色條、工項/完成數、進度條、異常/逾期/工時資訊列
4. HotelMgmtDashboard：將 SourceCards 函式中每張卡片改用 <SourceStatusCard ... />
5. MallMgmtDashboard：將 SourceCard component 改用 <SourceStatusCard ... />

不修改後端。確保兩個模組畫面不變後再更新 docs/CHANGELOG.md。
```

---

#### T17 ｜ 確認 Hotel 來源卡路由路徑是否正確

| 欄位 | 內容 |
|------|------|
| **優先級** | P2 |
| **嚴重性** | ⭐⭐⭐ 3 |
| **容易度** | ⭐⭐⭐⭐⭐ 5（確認後改路徑字串） |
| **模組** | hotel/overview |
| **影響 TAB** | Dashboard（來源卡點擊跳轉） |
| **問題** | `HOTEL_SOURCE_ROUTES.security` 設為 `'/hotel/security/dashboard'`，但 router 設定的路徑是 `/security/dashboard`（無 `/hotel` 前綴）。`HOTEL_SOURCE_ROUTES.daily_inspection` 設為 `'/hotel/hotel-daily-inspection/dashboard'`，但 router 設定的是 `/hotel/daily-inspection`（有多餘的 `hotel-` 前綴）。點擊來源卡的跳轉功能可能失效 |
| **檔案位置** | `frontend/src/pages/HotelMgmtDashboard/index.tsx` HOTEL_SOURCE_ROUTES |
| **預估工時** | 15 分鐘（確認 + 修改） |

**Claude 提示詞：**
```
請確認並修正 frontend/src/pages/HotelMgmtDashboard/index.tsx 中 HOTEL_SOURCE_ROUTES 的路由路徑。

目前路徑：
  security: '/hotel/security/dashboard'
  daily_inspection: '/hotel/hotel-daily-inspection/dashboard'

請對照 frontend/src/router/index.tsx 中的實際路由設定：
  <Route path="hotel">
    <Route path="daily-inspection" ...>   → 實際路徑：/hotel/daily-inspection
  <Route path="security">
    <Route path="dashboard" ...>          → 實際路徑：/security/dashboard

若確認路徑不符，請修正為：
  security: '/security/dashboard'
  daily_inspection: '/hotel/daily-inspection'

只修改這兩行路徑字串，不動其他邏輯。
```

---

#### T18 ｜ 兩邊均無 Excel/CSV 匯出功能

| 欄位 | 內容 |
|------|------|
| **優先級** | P2 |
| **嚴重性** | ⭐ 1 |
| **容易度** | ⭐⭐⭐ 3 |
| **模組** | 兩邊前端 |
| **影響 TAB** | B. 每日累計、C. 每月累計 |
| **問題** | B/C Tab 的大型交叉表格目前無匯出功能，主管若要分析需手動複製 |
| **預估工時** | 2–3 小時 |

**Claude 提示詞：**
```
請為飯店管理與商場管理 Dashboard 的 B. 每日累計 和 C. 每月累計 Tab 加上 CSV 匯出功能。

做法：
1. 在 TabBDaily 和 TabCMonthly 的表格上方篩選列右側加一個「匯出 CSV」Button（icon: DownloadOutlined）
2. 點擊時將表格資料轉換為 CSV 格式（標題列 + 資料列）
3. 觸發瀏覽器下載，檔名格式：「飯店管理_每日累計_{year}年{month}月.csv」或「商場管理_每月累計_{year}年.csv」
4. CSV 使用 BOM（﻿ 開頭）確保 Excel 開啟時中文不亂碼

使用純前端實作（不新增後端 API）：
  const blob = new Blob(['﻿' + csvContent], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click()

不修改後端。更新 docs/CHANGELOG.md。
```

---

## 修改順序建議

依「嚴重性高 + 容易度高」優先，建議執行順序：

| 順序 | 編號 | 預估時間 | 原因 |
|:----:|------|:-------:|------|
| 1 | T02 | 5 分鐘 | 2行修改，P0問題 |
| 2 | T03 | 5 分鐘 | 3行修改，P0問題 |
| 3 | T05 | 5 分鐘 | 1行修改，P0問題 |
| 4 | T15 | 5 分鐘 | 1行修改，P2 |
| 5 | T17 | 15 分鐘 | 確認路由，P2 |
| 6 | T07 | 30 分鐘 | Tab key統一，P1 |
| 7 | T11 | 1 小時 | 抽共用函式，P1 |
| 8 | T14 | 1 小時 | 月份容錯，P1 |
| 9 | T01 | 1–2 小時 | 飯店PPTX endpoint，P0 |
| 10 | T06 | 2–3 小時 | 商場PPTX完整補齊，P1 |
| 11 | T08 | 2 小時 | cases_pct補齊，P1 |
| 12 | T04 | 3–4 小時 | 商場人員排名資料來源，P0 |
| 13 | T12 | 1.5 小時 | PPTX工具函式共用，P1（T01/T06完成後） |
| 14 | T10 | 2–3 小時 | 商場人員排名圖表（T04完成後）|
| 15 | T09 | 4–6 小時 | 飯店Tab獨立篩選，P1 |
| 16 | T13 | 討論後定 | 飯店每年累計設計，待業主確認 |
| 17 | T18 | 2–3 小時 | CSV匯出，P2 |
| 18 | T16 | 4–6 小時 | SourceCard共用化，P2 |

---

*此文件由 Claude（Cowork mode）依程式碼比對自動產出，提示詞可直接複製使用*
*2026-05-06*
