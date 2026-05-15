# 工作日誌模組 — 技術規格文件

**版本：v1.0**  
**建立日期：2026-05-15**  
**路徑：`exec-work-dashboard` → TAB「工作日誌」**

---

## 1. 功能概述

「工作日誌」整合集團 10 個工務模組的每日工作記錄，依人員分組呈現當日完整作業清單。主管可依日期查詢任意一天的全員工作狀況，取代手動彙整各模組報表。

---

## 2. 資料來源（10 個模組）

| 代號 | 中文名稱 | DB Table / 主要欄位 | 日期欄位 |
|------|---------|-------------------|---------|
| `dazhi` | 飯店工務 | `dazhi_repair_case` | `occurred_at.date()` |
| `luqun` | 商場工務 | `luqun_repair_case` | `occurred_at.date()` |
| `hotel_pm` | 飯店週期保養 | `pm_batch` + `pm_item` | `batch.period_month` + `item.scheduled_date`（MM/DD） |
| `ihg` | IHG客房保養 | `ihg_room_maintenance` | `maint_date` |
| `hotel_di` | 飯店每日巡檢 | `hotel_daily_inspection` | `inspection_date` |
| `security` | 保全巡檢 | `security_inspection` | `inspection_date` |
| `mall_pm` | 商場週期保養 | `mall_pm_batch` + `mall_pm_item` | `batch.period_month` + `item.scheduled_date` |
| `full_bldg_pm` | 整棟保養 | `full_building_pm_batch` + `full_building_pm_item` | `batch.period_month` + `item.scheduled_date` |
| `mall_fi` | 商場設施巡檢 | `mall_facility_inspection` | `inspection_date` |
| `full_bi` | 整棟巡檢 | `full_building_inspection` | `inspection_date` |

### 2.1 日期匹配規則

- **報修類**（dazhi / luqun）：使用 `occurred_at.date()` 匹配；已取消案件（`status == 'cancelled'`）不納入
- **週期保養類**（hotel_pm / mall_pm / full_bldg_pm）：`batch.period_month`（YYYY-MM）= 查詢月，且 `item.scheduled_date`（MM/DD）= 查詢日
- **巡檢類**（hotel_di / security / mall_fi / full_bi）：`inspection_date` 精確匹配
- **IHG**（ihg）：`maint_date` 精確匹配

---

## 3. 後端 API 規格

### 端點

```
GET /api/v1/work-journal/daily
```

### 查詢參數

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `year` | int | ✓ | 年份（如 2026） |
| `month` | int | ✓ | 月份（1～12） |
| `day` | int | ✓ | 日（1～31） |

### 回傳格式

```json
{
  "date": "2026/05/15",
  "total_rows": 42,
  "persons": [
    {
      "person": "王小明",
      "rows": [
        {
          "seq": 1,
          "source": "dazhi",
          "source_label": "飯店工務",
          "category": "現場報修",
          "task": "設備修繕說明",
          "person": "王小明",
          "est_min": 60,
          "start_time": "09:00",
          "end_time": "10:00",
          "work_hours": 1.0,
          "remark": "備註",
          "report": "回報事項"
        }
      ]
    }
  ]
}
```

### 人員排序規則

1. Named person（非「未指定」）依 `work_hours` 合計降冪
2. 「未指定」永遠排最後

### 每人 row 排序規則

1. 有 `start_time` 的 row 優先，依 `start_time` 升冪
2. 無 `start_time` 的 row 依 source 定義順序排列

---

## 4. 前端 API 型別（`frontend/src/api/workJournal.ts`）

```typescript
export const JOURNAL_CATEGORIES = ['現場報修', '上級交辦', '緊急事件', '例行維護', '每日巡檢'] as const
export type JournalCategory = typeof JOURNAL_CATEGORIES[number]

export const JOURNAL_SOURCES = [
  'dazhi', 'luqun', 'hotel_pm', 'ihg', 'hotel_di',
  'security', 'mall_pm', 'full_bldg_pm', 'mall_fi', 'full_bi',
] as const

export interface JournalRow {
  seq:          number
  source:       JournalSource
  source_label: string
  category:     JournalCategory
  task:         string
  person:       string
  est_min:      number | null   // null = 無資料
  start_time:   string          // 'HH:MM' 或 ''
  end_time:     string          // 'HH:MM' 或 ''
  work_hours:   number | null   // null = 無資料
  remark:       string
  report:       string
}

export interface WorkJournalDaily {
  date:       string          // 'YYYY/MM/DD'
  persons:    JournalPerson[]
  total_rows: number
}

export async function fetchWorkJournalDaily(
  year: number, month: number, day: number
): Promise<WorkJournalDaily>
```

---

## 5. 前端 UI 規格（`WorkJournalTab` 元件）

### 5.1 日期選擇區（Card）

| 控制項 | 說明 |
|--------|------|
| 年 Select | 3 年選項（今年往前） |
| 月 Select | 1～12 月 |
| 日 Select | 1～該月天數（dayjs 計算） |
| 查詢 Button | 呼叫 `loadJournal()`，loading 狀態顯示 Spin |
| 結果摘要 | 查詢成功後顯示「YYYY/MM/DD ｜ 共 N 筆工作記錄」 |

### 5.2 人員分組 Collapse（預設全展開）

每個 Collapse Panel 標題：
- 人員姓名（未指定以灰色顯示）
- 工作項次 Badge（藍）
- 工時合計（geekblue Tag，僅 > 0 時顯示）
- 資料來源模組名稱（次要文字）

### 5.3 工作明細 Table

| 欄位 | 寬度 | 說明 |
|------|------|------|
| 項次 | 48px | seq，灰色小字 |
| 現場報修 | 56px | ✓（類別色，16px bold） |
| 上級交辦 | 56px | ✓ |
| 緊急事件 | 56px | ✓ |
| 例行維護 | 56px | ✓ |
| 每日巡檢 | 56px | ✓ |
| 工作事項 | 200px | task，12px 字 |
| 預估耗時(min) | 88px | est_min，null 顯示「—」 |
| 起 | 52px | start_time，空白顯示「—」 |
| 迄 | 52px | end_time，空白顯示「—」 |
| 工時(HR) | 72px | work_hours，toFixed(2)，`#1B3A5C` 粗體，null 顯示「—」 |
| 備註 | 160px | remark，灰色 |
| 回報事項 | 160px | report，橙色（`#d46b08`） |

- 5 個「類別」欄位：僅該 row 的 category 欄顯示 ✓，其餘空白
- `scroll={{ x: 'max-content' }}`，表格水平滾動

### 5.4 類別色彩對應（PROTECTED）

| 類別 | 色碼 |
|------|------|
| 現場報修 | `#4BA8E8` |
| 上級交辦 | `#52C41A` |
| 緊急事件 | `#FF4D4F` |
| 例行維護 | `#FA8C16` |
| 每日巡檢 | `#722ED1` |

---

## 6. 分類邏輯（`_classify` 函數）

工務報修案件的工項類別由 `_classify(title, repair_type)` 決定，重用自 `work_category_analysis.py`：
- `repair_type == '緊急事件'` → 緊急事件
- 否則 → 現場報修

週期保養 → 例行維護  
巡檢類 → 每日巡檢

---

## 7. 人員拆分規則

週期保養模組的 `executor_name` 欄位可能包含空格分隔的多人名稱（如 `"王大明 李小美"`），由 `_persons()` 函數拆分後分別建立 row，讓每人各自出現在自己的分組。

---

## 8. 後端檔案結構

```
backend/app/routers/work_journal.py
  ├── _classify(title, repair_type)    # 工項類別判斷
  ├── _parse_wh(val)                   # 工時字串解析（HR）
  ├── _clean_time(val)                 # HH:MM 格式化
  ├── _persons(name)                   # 多人名稱拆分
  ├── _date_str(year, month, day)      # YYYY/MM/DD
  ├── _make_row(seq, source, ...)      # 統一建立 JournalRow dict
  ├── _fetch_dazhi(db, year, month, day)
  ├── _fetch_luqun(db, year, month, day)
  ├── _fetch_hotel_pm(db, year, month, day)
  ├── _fetch_ihg(db, year, month, day)
  ├── _fetch_hotel_di(db, year, month, day)
  ├── _fetch_security(db, year, month, day)
  ├── _fetch_mall_pm(db, year, month, day)
  ├── _fetch_full_bldg_pm(db, year, month, day)
  ├── _fetch_mall_fi(db, year, month, day)
  ├── _fetch_full_bi(db, year, month, day)
  └── GET /daily                       # 主端點：整合並回傳
```

---

## 9. 明細 Drawer 設計標準（MANDATORY PATTERN）

> **強制規範**：任何模組的列表頁面，若每筆資料有對應明細欄位（原始表單欄位、附圖等），**必須**實作本節所定義的 Drawer 明細模式，無需額外提示。

### 9.1 觸發機制

- Table 的 `onRow` callback：點擊任意 row 開啟 Drawer
- Drawer 寬度：480px（無附圖）/ 640px（有附圖）
- Drawer 標題：來源模組名稱（`source_label`）+ 工作事項（`task`，12px 次要色）

### 9.2 後端規格

每個 `_fetch_*` 函數在建立 row 時，必須透過 `_make_row()` 傳入：

| 參數 | 型別 | 說明 |
|------|------|------|
| `ragic_id` | `str` | Ragic 資料列 ID（用於圖片查詢） |
| `detail` | `dict[str, str]` | 原始模組所有重要欄位的 key-value；key 為中文欄位名稱 |

#### 各模組 detail 欄位一覽

**dazhi / luqun（報修類）**

| 欄位名 | 資料來源欄位 |
|--------|------------|
| 報修編號 | `c.ragic_id` |
| 標題 | `c.title` |
| 報修人姓名 | `c.reporter_name` |
| 報修類型 | `c.repair_type` |
| 發生樓層 | `c.floor` |
| 發生時間 | `c.occurred_at` |
| 負責單位 | `c.responsible_unit` |
| 花費工時 | `c.work_hours` |
| 處理狀況 | `c.status` |
| 委外費用 | `c.outsource_cost` |
| 維修費用 | `c.repair_cost` |
| 總費用 | `c.total_cost` |
| 驗收者 | `c.inspector` |
| 驗收 | `c.inspection_result` |
| 結案人 | `c.closer` |
| 結案時間 | `c.closed_at` |
| 結案天數 | `c.close_days` |
| 扣款事項 | `c.deduction_item` |
| 扣款費用 | `c.deduction_cost` |
| 財務備註 | `c.finance_remark` |
| 管理回應 | `c.mgmt_response`（luqun 專屬） |

**hotel_pm / mall_pm / full_bldg_pm（週期保養類）**

| 欄位名 | 資料來源欄位 |
|--------|------------|
| 日誌編號 | `item.ragic_id` |
| 保養月份 | `batch.period_month` |
| 類別 | `batch.category` |
| 頻率 | `batch.frequency` |
| 區域 | `batch.area` |
| 排定日期 | `item.scheduled_date` |
| 排定人員 | `item.planned_person` |
| 執行人員 | `item.executor_name` |
| 完成狀況 | `item.status` |
| 執行結果 | `item.result` |
| 異常說明 | `item.abnormal_note` |

**ihg（IHG客房保養）**

| 欄位名 | 資料來源欄位 |
|--------|------------|
| 房號 | `r.room_number` |
| 樓層 | `r.floor` |
| 保養類型 | `r.maintenance_type` |
| 保養人員 | `r.maintainer` |
| 複核人員 | `r.reviewer` |
| 保養日期 | `r.maint_date` |
| 完成日期 | `r.completed_date` |
| 狀態 | `r.status` |
| 備註 | `r.remark` |

**hotel_di / security / mall_fi / full_bi（巡檢類）**

| 欄位名 | 資料來源欄位 |
|--------|------------|
| 巡檢表名稱 | `batch.name` |
| 巡檢人員 | `batch.inspector` |
| 巡檢日期 | `batch.inspection_date` |
| 開始時間 | `batch.start_time` |
| 結束時間 | `batch.end_time` |
| 工時 | `batch.work_hours` |

### 9.3 前端 Drawer 渲染規格

#### 基本欄位區（固定顯示）

使用 `Descriptions` 元件，`column={2}`，`size="small"`，顯示：

| 欄位 | 說明 |
|------|------|
| 來源模組 | `source_label` |
| 人員 | `person` |
| 工作事項 | `task`（`span={2}`） |
| 類別 | `category`（以對應色彩 Tag 顯示） |
| 起訖時間 | `start_time ~ end_time`（空白顯示「—」） |
| 預估耗時 | `est_min`（null 顯示「—」） |
| 工時 | `work_hours`（`#1B3A5C` 粗體，null 顯示「—」） |
| 備註 | `remark`（空白顯示「—」） |
| 回報事項 | `report`（`#d46b08`，空白顯示「—」） |

#### 明細欄位區（`detail` dict）

使用 `Descriptions` 元件，`column={1}`，`size="small"`，逐一渲染 detail dict 的每個 key-value：

| 欄位特性 | 渲染方式 |
|--------|---------|
| 狀態欄（處理狀況、完成狀況、驗收） | 依 `STATUS_COLOR` 顯示彩色 `Tag` |
| 費用欄（含「費用」字樣）| 前綴 `$` 符號，數字顯示 |
| 總費用 / 標題 | `fontWeight: bold`（加粗） |
| 空白或 None | 顯示「—」 |
| 其他 | 純文字 |

#### STATUS_COLOR 對應表（PROTECTED）

| 狀態值 | 色碼 |
|--------|------|
| 已完成 / 已修復 / 已結案 / 已辦驗 | `green` |
| 待辦驗 / 未完成 | `orange` |
| 進行中 | `blue` |
| 其他 | `default` |

#### 附圖區（僅 dazhi / luqun）

- 使用 `Image.PreviewGroup`（Ant Design），支援原地 Lightbox 預覽（禁止另開新視窗）
- 圖片來源端點：`GET /api/v1/{source}-repair/db-images/{ragic_id}`
- 前端 `fetchJournalImages(source, ragicId)` 函數封裝路由邏輯：
  - `source === 'dazhi'` → `/dazhi-repair/db-images/{ragicId}`
  - `source === 'luqun'` → `/luqun-repair/db-images/{ragicId}`
  - 其他 source → 回傳 `[]`（不發送請求）
- 圖片以 64px 縮圖呈現，點擊後全螢幕 Lightbox 預覽
- 圖片載入中顯示 `<Spin />`

### 9.4 新模組開發 Checklist

開發任何新模組列表頁時，若資料有明細欄位，必須確認：

- [ ] `_make_row()` 傳入 `ragic_id` + `detail` dict
- [ ] `detail` dict 包含原始模組所有重要欄位（中文 key）
- [ ] 前端 `JournalRow`（或對應型別）含 `ragic_id: string` + `detail: Record<string, string>`
- [ ] Table `onRow` click 觸發 Drawer 開啟
- [ ] Drawer 含「基本欄位區」+ 「明細欄位區」兩段 Descriptions
- [ ] 費用欄位加 `$` 前綴，狀態欄位加彩色 Tag
- [ ] 若模組有附圖：實作 `/db-images/{ragic_id}` 端點，前端使用 `Image.PreviewGroup`

---

## 10. Todo List（後續迭代）

| 優先 | 項目 | 說明 |
|------|------|------|
| P1 | 匯出 Excel | 當日工作日誌一鍵匯出為 xlsx，每人一個 sheet |
| P1 | 列印格式 | 輸出適合 A4 橫向列印的 PDF 工作日誌 |
| P2 | 月曆檢視 | 月視角快速點選有記錄的日期（Badge 顯示件數） |
| P2 | 人員篩選 | 日誌查詢新增人員 Select 篩選器（預設：所有人員） |
| P2 | 模組篩選 | 新增 source Checkbox 群組，可選擇只看特定模組 |
| P3 | 工時統計列 | 每人 Collapse 底部加一列合計（工時、件數、未填工時件數） |
| P3 | 空白工時提醒 | 有 start/end 但 work_hours 空白的 row 以橙色背景標示 |
| P3 | 回報事項匯總 | 額外區塊列出當日所有非空的回報事項（跨人員彙整） |
