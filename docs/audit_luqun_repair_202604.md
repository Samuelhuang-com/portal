# 2026/04 樂群報修統計邏輯評估報告

> 稽核日期：2026-04-29　｜　資料來源：樂群報修.xlsx（129 筆）+ DB Schema `luqun_repair_case`
> 稽核性質：純資料評估，本次**不修改任何程式**

---

## 1. 現行問題摘要

| # | 問題描述 | 嚴重程度 |
|---|----------|----------|
| P1 | `未完成件數` KPI 值偏高（顯示 24，正確應為 17）| 🔴 高 |
| P2 | `待辦驗` 案件被同時計入「未完成」，造成重複計算 | 🔴 高 |
| P3 | `kpi_uncompleted_detail` 清單包含「待辦驗」案件，與卡片語義不符 | 🟠 中 |
| P4 | `kpi_close_days_detail` 若仍以 `completed_at` 篩選，應改為以 `status == "已辦驗"` 篩選 | 🟠 中 |

> **前提確認**：本系統「是否完成」的判斷依據已改為 `status`（處理狀況）欄位，**不再使用** `completed_at`（完工時間）。

---

## 2. Excel 欄位盤點

### 2.1 DB Schema → 欄位對照（`luqun_repair_case`）

| DB 欄位名稱 | 型別 | Ragic 來源欄位 | 用途說明 |
|---|---|---|---|
| `ragic_id` | VARCHAR(50) PK | 案件編號 | 唯一識別碼 |
| `case_no` | VARCHAR(100) | 案號 | 顯示用案號 |
| `title` | TEXT | 標題 | 報修摘要 |
| `reporter_name` | VARCHAR(100) | 報修人 | 報修人姓名 |
| `repair_type` | VARCHAR(50) | 維修類型 | 類型統計使用 |
| `floor` | VARCHAR(100) | 樓層 | 原始樓層文字 |
| `floor_normalized` | VARCHAR(30) | — | 標準化後樓層（前端顯示） |
| `occurred_at` | DATETIME | 報修日期 | 報修時間點 |
| `responsible_unit` | VARCHAR(100) | 負責單位 | — |
| `work_hours` | FLOAT | 花費工時 | 本月工時統計 KPI 來源 |
| **`status`** | VARCHAR(50) | **處理狀況** | **✅ 完成判斷主依據** |
| `outsource_fee` | FLOAT | 外包費用 | 費用統計 |
| `maintenance_fee` | FLOAT | 維護費用 | 費用統計 |
| `total_fee` | FLOAT | 合計費用 | 費用統計 |
| `deduction_item` | VARCHAR(200) | 扣款項目 | — |
| `deduction_fee` | FLOAT | 扣款金額 | — |
| `deduction_counter` | FLOAT | 扣款次數 | — |
| `deduction_counter_name` | TEXT | 扣款專櫃名稱 | — |
| `acceptor` | VARCHAR(100) | 驗收人 | — |
| `accept_status` | VARCHAR(200) | 驗收狀態 | — |
| `closer` | VARCHAR(100) | 結案人 | — |
| `finance_note` | TEXT | 財務備註 | — |
| `is_completed` | BOOLEAN | — | 由 Ragic 同步，與 `status` 對應 |
| `completed_at` | DATETIME | 完工/結案時間 | ⚠️ 不再作為 KPI 完成判斷依據 |
| `close_days` | FLOAT | 結案天數 | 平均結案天數 KPI 來源 |
| `year` | INTEGER | — | 統計年（服務層計算後回寫）|
| `month` | INTEGER | — | 統計月（服務層計算後回寫）|
| `occ_year` | INTEGER | — | 報修年（derived from occurred_at）|
| `occ_month` | INTEGER | — | 報修月（derived from occurred_at）|
| `is_room_case` | BOOLEAN | — | 是否為客房案件 |
| `room_no` | VARCHAR(20) | 客房號碼 | — |
| `room_category` | VARCHAR(50) | 客房類別 | — |
| `mgmt_response` | TEXT | 管理回覆 | — |
| `images_json` | TEXT | 圖片清單 | 序列化 JSON |
| `synced_at` | DATETIME | — | 最後同步時間 |

### 2.2 關鍵衍生計算欄位（服務層）

| 衍生變數 | 計算來源欄位 | 說明 |
|---|---|---|
| `_prev_uncompleted` | `occ_year`, `occ_month`, `status` | 報修月 ≤ 上月，且 `status` ≠ 已辦驗 ≠ 取消 |
| `_this_month_new` | `occ_year`, `occ_month` | 本月新報修（`occ_year==Y AND occ_month==M`）|
| `this_month_cases` | 上兩者合集 | 本月相關案件母集合 |
| `completed`（月）| `status` == `"已辦驗"` in this_month_cases | 已完成件數 |
| `pending_verify` | `status` == `"待辦驗"` in this_month_cases | 待辦驗件數 |
| `uncompleted`（**待修正**）| 現行 = `total - completed` ← ❌ | 應改為 `total - completed - pending_verify` |

---

## 3. 正確統計邏輯

### 3.1 完成判斷依據（已更新）

| 欄位 | 說明 |
|---|---|
| `status == "已辦驗"` | ✅ 案件完成的唯一判斷條件 |
| `status == "待辦驗"` | 完工但尚未驗收，獨立計算 |
| `status == "取消"` | 排除在所有 KPI 之外 |
| `completed_at` | ⚠️ 僅保留作參考，不作為「是否完成」的判斷 |
| `is_completed` | 與 `status` 對應，保持同步，但計算時直接用 `status` |

### 3.2 本月相關案件口徑

```
本月相關案件（total）
  = ① 上期累計未結  ＋  ⑤ 本期新增報修
```

- **① 上期累計未結**：`occ_year < Y OR (occ_year == Y AND occ_month < M)`，且 `status NOT IN ("已辦驗", "取消")`
- **⑤ 本期新增報修**：`occ_year == Y AND occ_month == M`，且 `status != "取消"`

### 3.3 三類互斥分類

```
本月相關案件（total）
  = 已完成件數（completed）
  + 待辦驗件數（pending_verify）
  + 未完成件數（uncompleted）
```

| 分類 | 判斷欄位 | 條件 | 顏色 |
|---|---|---|---|
| 已完成 | `status` | `== "已辦驗"` | 綠色 ✅ |
| 待辦驗 | `status` | `== "待辦驗"` | 黃色 ⚠️ |
| 未完成 | `status` | 非已辦驗、非待辦驗、非取消 | 紅色 ❌ |

---

## 4. 狀態分類規則

### 4.1 `status`（處理狀況）值對照

| status 值 | 語義 | 歸入分類 |
|---|---|---|
| `已辦驗` | 驗收完成，案件正式結案 | 已完成 |
| `待辦驗` | 完工但尚未驗收 | 待辦驗（獨立類別）|
| `處理中` | 施工進行中 | 未完成 |
| `待排程` | 尚未安排施工 | 未完成 |
| `取消` | 取消 | **不列入任何 KPI** |
| 空白 / 其他 | 資料缺漏或新增狀態 | 未完成（保守歸類）|

### 4.2 `completed_at` 欄位說明

- 此欄位在 Ragic 中對應「完工時間」，為工班完成施工的時間點
- **與「正式結案」（`status == "已辦驗"`）並不等價**：工班完工後仍需驗收，才算結案
- 目前已不作為 KPI 完成判斷依據，僅保留供追溯查閱
- `close_days`（結案天數）若由後端計算，應確認其計算起迄點的定義是否需要同步修正

---

## 5. 2026/04 試算結果

以下數字由 Python 直接解析 Excel 原始數據驗證（`status` 欄位為判斷依據）：

| KPI | 系統現值 | 正確值 | 差異 |
|---|---|---|---|
| 本月相關案件（total） | 52 | **52** | ✅ 正確 |
| 已完成件數（`status == "已辦驗"`）| 28 | **28** | ✅ 正確 |
| 待辦驗件數（`status == "待辦驗"`）| 7 | **7** | ✅ 正確 |
| 未完成件數 | **24** ← 錯誤 | **17** | ❌ 多算 7 |

### 5.1 詳細推導

```
① 上期累計未結  =  7 筆
    條件：occ_year < 2026 OR (occ_year == 2026 AND occ_month < 4)
          AND status NOT IN ("已辦驗", "取消")

⑤ 本期新增報修  = 45 筆
    條件：occ_year == 2026 AND occ_month == 4
          AND status != "取消"
─────────────────────────────
total            = 52 筆

已完成（status == "已辦驗"）         = 28 筆
待辦驗（status == "待辦驗"）         =  7 筆  ← 本期 4 + 上期未結 3
未完成（其他 status）                = 17 筆

驗算：28 + 7 + 17 = 52 ✓
```

### 5.2 待辦驗構成

| 來源 | status | occ_month | 件數 |
|---|---|---|---|
| ⑤ 本期新增（occ_month == 4）| 待辦驗 | 4 | 4 |
| ① 上期累計未結（occ_month < 4）| 待辦驗 | ≤ 3 | 3 |
| **合計** | | | **7** |

---

## 6. 發現的問題

### P1 — 未完成件數計算錯誤（🔴 高優先）

**現行邏輯**：
```python
uncompleted = total - completed  # 52 - 28 = 24
```

**問題**：7 筆 `status == "待辦驗"` 案件沒有從 `uncompleted` 中剔除。

**正確邏輯**：
```python
uncompleted = total - completed - pending_verify  # 52 - 28 - 7 = 17
```

---

### P2 — 待辦驗被重複計入未完成（🔴 高優先）

`待辦驗件數` KPI 卡（值 = 7）與 `未完成件數` KPI 卡（值應 = 17）目前有重疊。  
前端若顯示 `待辦驗 7` + `未完成 24`，用戶以為總未結束案件有 31 筆，實際只有 24 筆（7 + 17）。

**修正**：兩張卡片對應的案件集合必須互斥（見 §3.3）。

---

### P3 — kpi_uncompleted_detail 含待辦驗案件（🟠 中優先）

**現行**：`kpi_uncompleted_detail` = `this_month_cases` 中 `status != "已辦驗"`  
（包含了所有 `待辦驗` 案件）

**問題**：點開「未完成件數」卡片的明細清單，卻出現「待辦驗」案件，語義混亂。

**正確**：
```python
uncompleted_cases = [
    c for c in this_month_cases
    if c.status.strip() != "已辦驗"
    and c.status.strip() != "待辦驗"
]
```

---

### P4 — close_days / 平均結案天數 的樣本範圍確認（🟠 中優先）

`平均結案天數` KPI 目前計算「`close_days` 有值的案件」的平均。

若 `close_days` 由 Ragic 同步，且 Ragic 的計算起點為「報修日期」、終點為「完工時間（completed_at）」而非「正式驗收（status 轉為已辦驗）」，則其語義與 KPI 預期可能不一致。

**建議確認**：Ragic `結案天數` 欄位的計算公式，確保與 `status == "已辦驗"` 的定義對齊。

---

## 7. 建議修正方向

### 7.1 立即修正（邏輯調整，不改資料模型）

**後端 `luqun_repair_service.py`（大直 `dazhi_repair_service.py` 同步修正）**：

**① 修正 `uncompleted` 計算值**
```python
# 現行（錯）
uncompleted = total - completed

# 修正後
uncompleted = total - completed - pending_verify_count
```

**② 修正 `uncompleted_cases` 清單（供 kpi_uncompleted_detail）**
```python
# 現行（錯）
uncompleted_cases = [c for c in this_month_cases if c.status.strip() != "已辦驗"]

# 修正後：同時排除待辦驗
uncompleted_cases = [
    c for c in this_month_cases
    if c.status.strip() not in ("已辦驗", "待辦驗")
]
```

### 7.2 中期確認項目

**③ 確認 `close_days` 欄位語意**  
確認 Ragic 的「結案天數」計算終點是否為「驗收完成（status=已辦驗）」，若否，需在服務層重新計算。

**④ 確認 `_prev_uncompleted` 判斷邏輯一致性**  
目前 ① 上期未結的判斷若混用了 `completed_at`，應統一改為：
```python
# 正確：以 status 判斷是否結案
_prev_uncompleted = [
    c for c in _cases_up_to_prev
    if c.status.strip() not in ("已辦驗", "取消")
]
```

---

## 8. 後續若要改程式，需修改哪些模組或函式

| 優先 | 檔案 | 函式 / 變數 | 修改內容 |
|------|------|-------------|----------|
| P1🔴 | `backend/app/services/luqun_repair_service.py` | `compute_dashboard()` → `uncompleted` | 改為 `total - completed - pending_verify_count` |
| P1🔴 | `backend/app/services/dazhi_repair_service.py` | 同上 | 同上 |
| P2🔴 | `backend/app/services/luqun_repair_service.py` | `uncompleted_cases` 清單 | 排除 `status == "待辦驗"` |
| P2🔴 | `backend/app/services/dazhi_repair_service.py` | 同上 | 同上 |
| P3🟠 | `backend/app/services/luqun_repair_service.py` | `_prev_uncompleted` 篩選 | 確認是否混用 `completed_at`，統一改為 `status` 判斷 |
| P3🟠 | `backend/app/services/dazhi_repair_service.py` | 同上 | 同上 |
| P4🟡 | `backend/app/services/luqun_repair_service.py` | `close_days_cases` / `avg_close_days` | 確認 `close_days` 欄位語意後決定是否重算 |
| P4🟡 | `backend/app/services/dazhi_repair_service.py` | 同上 | 同上 |

---

*報告產出：Claude（資料邏輯稽核）｜ 2026-04-29*
