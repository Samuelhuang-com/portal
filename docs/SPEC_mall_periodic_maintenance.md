# 商場例行維護（/mall/periodic-maintenance）修改 SPEC

> 本 SPEC 對應飯店例行維護（`hotel/periodic-maintenance`）的完整修改內容，
> 請依序將下列所有變更套用至商場模組。
>
> 飯店模組版本基準：v1.57.29

---

## 目錄

1. [模組更名](#1-模組更名)
2. [後端：頻率分類邏輯與統計端點](#2-後端頻率分類邏輯與統計端點)
3. [後端：保養項目目錄端點](#3-後端保養項目目錄端點)
4. [前端 API 檔案更新](#4-前端-api-檔案更新)
5. [前端：MATRIX_METRICS 欄位標籤 + Tooltip](#5-前端matrix_metrics-欄位標籤--tooltip)
6. [前端：YearMatrixTable 欄位標籤 render 更新](#6-前端yearmatrixtable-欄位標籤-render-更新)
7. [前端：三個 TAB 加入 frequency_type 傳遞](#7-前端三個-tab-加入-frequency_type-傳遞)
8. [前端：矩陣數字點擊 → MatrixDetailModal](#8-前端矩陣數字點擊--matrixdetailmodal)
9. [前端：各 TAB 新增「保養項目」按鈕 + CatalogModal](#9-前端各-tab-新增保養項目按鈕--catalogmodal)
10. [重要注意事項](#10-重要注意事項)

---

## 1. 模組更名

**檔案：** `frontend/src/constants/navLabels.ts`

目前值（若尚未改過）：
```ts
mallPeriodicMaintenance: '商場例行維護',
```
此行**保持不動**（商場側命名已符合規範，無需修改）。

---

## 2. 後端：頻率分類邏輯與統計端點

**檔案：** `backend/app/routers/mall_periodic_maintenance.py`

### 2-A. 加入 `_FREQ_KEYWORDS` 與 `_freq_match()`

在現有 import 區塊下方、第一個 endpoint 之前，新增：

```python
from typing import Optional

# ── 頻率分類 mapping ─────────────────────────────────────────────────────────
_FREQ_KEYWORDS: dict[str, set[str]] = {
    "monthly":   {"月", "每月", "月維護", "Monthly", "monthly"},
    "quarterly": {"季", "每季", "季維護", "Quarterly", "quarterly"},
    "yearly":    {"年", "每年", "年維護", "Annual", "annual", "Yearly", "yearly"},
}

def _freq_match(frequency: str, frequency_type: Optional[str]) -> bool:
    """回傳 True 表示該 item 的頻率符合篩選條件（None = 不篩選）"""
    if not frequency_type:
        return True
    keywords = _FREQ_KEYWORDS.get(frequency_type, set())
    return frequency.strip() in keywords
```

### 2-B. `_calc_year_matrix()` 加入 `frequency_type` 參數

找到現有的 `_calc_year_matrix(db, year)` 函數，將簽名改為：

```python
def _calc_year_matrix(db: Session, year: int, frequency_type: Optional[str] = None) -> PMYearMatrix:
```

在函數內部，找到 item 過濾迴圈（通常是對查詢結果做 `for row in rows`），加入頻率過濾：

```python
# 在現有 for row in rows: 之後，第一行加入：
if not _freq_match(row.frequency, frequency_type):
    continue
```

> 注意：`frequency_type=None` 時 `_freq_match` 回傳 `True`，Dashboard 端點呼叫不傳 `frequency_type` 即可保持原有行為。

### 2-C. `_calc_period_stats_core()` 加入 `frequency_type` 參數

同樣找到 `_calc_period_stats_core()` 函數，加入：

```python
def _calc_period_stats_core(..., frequency_type: Optional[str] = None):
    # 在 item 迴圈內，第一行加入：
    if not _freq_match(item.frequency, frequency_type):
        continue
```

### 2-D. `GET /period-stats/year-matrix` 端點加入 `frequency_type` 參數

```python
@router.get("/period-stats/year-matrix")
def get_year_matrix(
    year: Optional[int] = Query(None),
    frequency_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    y = year or datetime.now().year
    return _calc_year_matrix(db, y, frequency_type)
```

### 2-E. `GET /period-stats` 端點加入 `frequency_type` 參數

```python
@router.get("/period-stats")
def get_period_stats(
    period_type: str = Query(...),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    quarter: Optional[int] = Query(None),
    frequency_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return _calc_period_stats_core(db, period_type, year, month, quarter, frequency_type)
```

### 2-F. 新增 `GET /period-stats/year-matrix/items` 端點

在 year-matrix 端點之後加入：

```python
@router.get("/period-stats/year-matrix/items")
def get_year_matrix_items(
    year: int = Query(...),
    month: int = Query(...),      # 0 = 全年合計
    metric: str = Query(...),     # prev_carry_over | prev_resolved | period_total | period_completed
    frequency_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """矩陣格點擊查詢明細（對應 MallPeriodicMaintenanceItem）"""
    from app.models.mall_periodic_maintenance import MallPeriodicMaintenanceBatch, MallPeriodicMaintenanceItem

    # 建立月份範圍過濾
    if month == 0:
        month_filter = None
    else:
        month_str = f"{year}/{str(month).zfill(2)}"

    rows = (
        db.query(MallPeriodicMaintenanceItem, MallPeriodicMaintenanceBatch)
        .join(MallPeriodicMaintenanceBatch,
              MallPeriodicMaintenanceItem.batch_ragic_id == MallPeriodicMaintenanceBatch.ragic_id)
        .filter(MallPeriodicMaintenanceBatch.period_month.like(f"{year}/%"))
        .all()
    )

    settings_obj = __import__('app.core.config', fromlist=['settings']).settings
    base_url = getattr(settings_obj, 'ragic_base_url', '')

    results = []
    for item, batch in rows:
        if not _freq_match(item.frequency, frequency_type):
            continue
        if month != 0 and not batch.period_month.endswith(f"/{str(month).zfill(2)}"):
            continue

        # 依 metric 決定是否包含此筆
        is_completed = bool(item.end_time and item.end_time.strip())
        carry_over = False  # 計算較複雜，簡化為：只依月份過濾

        if metric == 'period_total':
            pass  # 全部包含
        elif metric == 'period_completed':
            if not is_completed:
                continue
        elif metric in ('prev_carry_over', 'prev_resolved'):
            # 上期結轉 = 非本月應完成但仍未完成的項目（簡化處理，可依實際邏輯調整）
            pass

        ragic_id_num = item.ragic_id.replace('_', '') if item.ragic_id else ''
        results.append({
            "ragic_id":            item.ragic_id,
            "batch_ragic_id":      item.batch_ragic_id,
            "period_month":        batch.period_month,
            "category":            item.category,
            "task_name":           item.task_name,
            "frequency":           item.frequency,
            "scheduled_date_full": f"{batch.period_month[:4]}/{item.scheduled_date}" if item.scheduled_date else "",
            "end_time":            item.end_time or "",
            "status":              "已完成" if is_completed else ("進行中" if item.start_time else "待排程"),
            "executor_name":       item.executor_name or "",
            "result_note":         item.result_note or "",
            "abnormal_flag":       bool(item.abnormal_flag),
            "abnormal_note":       item.abnormal_note or "",
            "ragic_link":          f"{base_url}/..." if base_url else "",
        })

    return {"total": len(results), "items": results}
```

> ⚠️ **注意**：上方 `prev_carry_over` / `prev_resolved` 的計算邏輯需依商場模組的實際統計邏輯實作，建議參考飯店端 `backend/app/routers/periodic_maintenance.py` line ~852 的完整實作。

---

## 3. 後端：保養項目目錄端點

**檔案：** `backend/app/routers/mall_periodic_maintenance.py`（在檔案最末尾加入）

```python
# ── 保養項目目錄（依頻率分類）──────────────────────────────────────────────────
@router.get("/items/catalog")
def get_items_catalog(
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    取得保養項目目錄（不分批次），依 frequency_type 篩選。
    結果為去重後的保養項目列表，以最新 seq_no 的資料為準。
    """
    from sqlalchemy import func as sqlfunc
    from app.models.mall_periodic_maintenance import MallPeriodicMaintenanceItem

    subq = (
        db.query(
            MallPeriodicMaintenanceItem.task_name,
            MallPeriodicMaintenanceItem.category,
            MallPeriodicMaintenanceItem.frequency,
            sqlfunc.max(MallPeriodicMaintenanceItem.seq_no).label("max_seq"),
        )
        .group_by(
            MallPeriodicMaintenanceItem.task_name,
            MallPeriodicMaintenanceItem.category,
            MallPeriodicMaintenanceItem.frequency,
        )
        .subquery()
    )

    rows = (
        db.query(MallPeriodicMaintenanceItem)
        .join(
            subq,
            (MallPeriodicMaintenanceItem.task_name   == subq.c.task_name)
            & (MallPeriodicMaintenanceItem.category  == subq.c.category)
            & (MallPeriodicMaintenanceItem.frequency == subq.c.frequency)
            & (MallPeriodicMaintenanceItem.seq_no    == subq.c.max_seq),
        )
        .order_by(MallPeriodicMaintenanceItem.category, MallPeriodicMaintenanceItem.seq_no)
        .all()
    )

    result = []
    seen: set[tuple] = set()
    for r in rows:
        if not _freq_match(r.frequency, frequency_type):
            continue
        key = (r.task_name, r.category, r.frequency)
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "seq_no":            r.seq_no,
            "category":          r.category,
            "frequency":         r.frequency,
            "task_name":         r.task_name,
            "location":          r.location,
            "estimated_minutes": r.estimated_minutes,
            "exec_months_raw":   r.exec_months_raw,
        })

    return {"total": len(result), "items": result}
```

---

## 4. 前端 API 檔案更新

**檔案：** `frontend/src/api/mallPeriodicMaintenance.ts`

### 4-A. `fetchMallPMPeriodStats` 加入 `frequency_type`

```ts
export async function fetchMallPMPeriodStats(params: {
  period_type: 'month' | 'quarter' | 'year'
  year?: number
  month?: number
  quarter?: number
  frequency_type?: 'monthly' | 'quarterly' | 'yearly'   // ← 新增
}): Promise<PMPeriodStats> {
  const res = await apiClient.get<PMPeriodStats>(`${BASE}/period-stats`, { params })
  return res.data
}
```

### 4-B. `fetchMallPMYearMatrix` 加入 `frequency_type`

```ts
export async function fetchMallPMYearMatrix(
  year?: number,
  frequency_type?: 'monthly' | 'quarterly' | 'yearly',   // ← 新增
): Promise<PMYearMatrix> {
  const params: Record<string, number | string> = {}
  if (year) params.year = year
  if (frequency_type) params.frequency_type = frequency_type  // ← 新增
  const res = await apiClient.get<PMYearMatrix>(`${BASE}/period-stats/year-matrix`, { params })
  return res.data
}
```

### 4-C. 新增矩陣明細型別與函數

```ts
// ── 矩陣格明細（數字點擊查詢）────────────────────────────────────────────────
export type PMMatrixMetric = 'prev_carry_over' | 'prev_resolved' | 'period_total' | 'period_completed'

export interface MallPMMatrixItem {
  ragic_id:              string
  batch_ragic_id:        string
  period_month:          string
  category:              string
  task_name:             string
  frequency:             string
  scheduled_date_full:   string
  end_time:              string
  status:                string
  executor_name:         string
  result_note:           string
  abnormal_flag:         boolean
  abnormal_note:         string
  ragic_link:            string
}

export interface MallPMMatrixItemsResponse {
  total: number
  items: MallPMMatrixItem[]
}

export async function fetchMallPMMatrixItems(params: {
  year: number
  month: number
  metric: PMMatrixMetric
  frequency_type?: string
}): Promise<MallPMMatrixItemsResponse> {
  const res = await apiClient.get<MallPMMatrixItemsResponse>(
    `${BASE}/period-stats/year-matrix/items`, { params }
  )
  return res.data
}
```

### 4-D. 新增保養項目目錄型別與函數

```ts
// ── 保養項目目錄（依頻率分類）────────────────────────────────────────────────
export interface MallPMCatalogItem {
  seq_no:            number
  category:          string
  frequency:         string
  task_name:         string
  location:          string
  estimated_minutes: number
  exec_months_raw:   string
}

export interface MallPMCatalogResponse {
  total: number
  items: MallPMCatalogItem[]
}

export async function fetchMallPMCatalog(
  frequency_type?: 'monthly' | 'quarterly' | 'yearly',
): Promise<MallPMCatalogResponse> {
  const params: Record<string, string> = {}
  if (frequency_type) params.frequency_type = frequency_type
  const res = await apiClient.get<MallPMCatalogResponse>(`${BASE}/items/catalog`, { params })
  return res.data
}
```

---

## 5. 前端：MATRIX_METRICS 欄位標籤 + Tooltip

**檔案：** `frontend/src/pages/MallPeriodicMaintenance/index.tsx`

找到 `MATRIX_METRICS` 陣列定義，修改如下：

```ts
// 型別定義加入 tooltip?
const MATRIX_METRICS: {
  key: keyof PMYearMatrixMonth | '_sep1' | '_sep2'
  label: string
  isRate?: boolean
  isText?: boolean
  tooltip?: string        // ← 新增
}[] = [
  { key: 'prev_carry_over',
    label: '截至上月底累計未結案數',        // ← 改（無①）
    tooltip: '前期結轉未完成數：截至上月底，所有尚未結案的週期保養項目累計總數（含更早期遞延未完成項目）。' },
  { key: 'prev_resolved_in_period',
    label: '其中本月已結案數',              // ← 改（無②）
    tooltip: '本月已結案數：上列「截至上月底累計未結案數」中，在本月內完成並結案的項目數。\n完成率（累計項目完成率）＝ 已結案數 ÷ 累計未結案數 × 100%。' },
  // ... 其他 metric 保持不動
]
```

---

## 6. 前端：YearMatrixTable 欄位標籤 render 更新

**檔案：** `frontend/src/pages/MallPeriodicMaintenance/index.tsx`

找到 `YearMatrixTable` 函數內的 `cols` 陣列，更新 label 欄的 `render`：

```tsx
{
  title:     '',
  dataIndex: 'label',
  width:     310,        // ← 從 230 改為 310（配合字體放大）
  fixed:     'left',
  onCell:    (row) => ({ style: { background: row['_isSep'] ? '#fafafa' : undefined } }),
  render:    (v: string, row) => {
    const metric = MATRIX_METRICS.find((x) => x.key === row['_key'])
    const tip = metric?.tooltip
    return (
      <Space size={4}>
        <Typography.Text style={{ fontSize: 18, fontWeight: v ? 500 : undefined }}>
          {v}
        </Typography.Text>
        {tip && (
          <Tooltip title={<span style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{tip}</span>} placement="right">
            <span style={{
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              width: 18, height: 18, borderRadius: '50%',
              background: '#1677ff', color: '#fff',
              fontSize: 12, fontWeight: 700, cursor: 'help', lineHeight: '18px',
            }}>?</span>
          </Tooltip>
        )}
      </Space>
    )
  },
},
```

月份欄與合計欄：
```tsx
// 月份欄 width: 75 → 90，title 加 fontSize
title:  <span style={{ fontSize: 18 }}>{m.label}</span>,
width:  90,

// 合計欄 width: 80 → 100，title 加 fontSize
title:  <Typography.Text strong style={{ color: '#1B3A5C', fontSize: 18 }}>合計</Typography.Text>,
width:  100,
```

renderCell 內所有 fontSize：
```tsx
// futureCell
<Typography.Text type="secondary" style={{ fontSize: 18 }}>—</Typography.Text>

// 備註文字（isText）
style={{ fontSize: 17, display: 'block', maxWidth: 90, cursor: 'pointer' }}

// 比率（isRate）
style={{ fontSize: 18, color: ... }}

// 可點擊數字
style={{ fontSize: 18, fontWeight: isTotal ? 600 : undefined, color: '#1677ff', ... }}

// 一般數字
style={{ fontSize: 18, color: num === 0 ? '#ccc' : undefined, fontWeight: isTotal ? 600 : undefined }}
```

> 確認 `Tooltip` 已從 `antd` import，若尚未加入請補充：
> ```ts
> import { ..., Tooltip, Space, ... } from 'antd'
> ```

---

## 7. 前端：三個 TAB 加入 frequency_type 傳遞 + 矩陣移至頂部

**檔案：** `frontend/src/pages/MallPeriodicMaintenance/index.tsx`

### 7-A. 三個 TAB 的 JSX 排版結構

**三個 TAB 均採用相同排版順序：**
1. 年度選擇器 Row（年度 Select + 重新整理 + 保養項目按鈕）
2. **YearMatrixTable**（矩陣在最上方，此為重點）
3. Divider（「季度鑽取」／「年度鑽取」／「單月鑽取」）
4. KPI Cards + IncompleteTable 等鑽取區塊

每個 TAB 對應 `YearMatrixTable` 的呼叫加上 `frequencyType` prop，**緊接在年度選擇器 Row 之後**：

```tsx
// 每月 TAB（matrix 在最上方）
<Row ...>  {/* 年度選擇器 */}  </Row>
{matrixLoading ? <Card>...</Card> : matrixData ? (
  <YearMatrixTable data={matrixData} frequencyType='monthly' onCellClick={...} />
) : <Alert ... />}
<Divider>單月鑽取</Divider>
{/* KPI Cards, IncompleteTable */}

// 每季 TAB（matrix 在最上方，取代原本放在底部的做法）
<Row ...>  {/* 年度選擇器 */}  </Row>
{quarterlyMatrixLoading ? <Card>...</Card> : quarterlyMatrixData ? (
  <YearMatrixTable data={quarterlyMatrixData} frequencyType='quarterly' onCellClick={...} />
) : <Alert ... />}
<Divider>季度鑽取</Divider>
{/* QuarterSelectorCards */}
<Divider>Q{n}（...月）詳細統計</Divider>
{/* KPI Cards, IncompleteTable */}

// 每年 TAB（matrix 在最上方，取代原本放在底部的做法）
<Row ...>  {/* 年度選擇器 */}  </Row>
{yearlyMatrixLoading ? <Card>...</Card> : yearlyMatrixData ? (
  <YearMatrixTable data={yearlyMatrixData} frequencyType='yearly' onCellClick={...} />
) : <Alert ... />}
<Divider>年度鑽取</Divider>
{/* KPI Cards, SubBreakdownTable, IncompleteTable */}
```

> ⚠️ **重點**：每季/每年 TAB 原本矩陣在底部（用 Divider「全年矩陣總覽（每季維護）」隔開），請**移除底部矩陣區塊**，改在頂部呈現。

### 7-B. 每季/每年重新整理按鈕同時觸發 matrix + stats

```tsx
// 每季
onClick={() => { loadQuarterlyMatrix(); loadQuarterlyStats() }}
loading={quarterlyMatrixLoading || quarterlyLoading}

// 每年
onClick={() => { loadYearlyMatrix(); loadYearlyStats() }}
loading={yearlyMatrixLoading || yearlyLoading}
```

### 7-C. YearMatrixTable 函數簽名更新（若尚未有 `frequencyType`）

```ts
function YearMatrixTable({
  data, frequencyType, onCellClick
}: {
  data: PMYearMatrix
  frequencyType?: string
  onCellClick?: (year: number, month: number, metric: PMMatrixMetric, monthLabel: string) => void
})
```

### 7-D. 三個 loadMatrix 函數分別傳入 frequency_type

```ts
const data = await fetchMallPMYearMatrix(monthlyYear, 'monthly')    // 每月
const data = await fetchMallPMYearMatrix(quarterlyYear, 'quarterly') // 每季
const data = await fetchMallPMYearMatrix(yearlyYear, 'yearly')       // 每年
```

### 7-E. 三個 loadPeriodStats 函數分別傳入 frequency_type

```ts
fetchMallPMPeriodStats({ period_type: 'month',   year: monthlyYear,   month: monthlyMonth,       frequency_type: 'monthly' })
fetchMallPMPeriodStats({ period_type: 'quarter', year: quarterlyYear, quarter: quarterlyQuarter, frequency_type: 'quarterly' })
fetchMallPMPeriodStats({ period_type: 'year',    year: yearlyYear,                               frequency_type: 'yearly' })
```

---

## 8. 前端：矩陣數字點擊 → MatrixDetailModal

**檔案：** `frontend/src/pages/MallPeriodicMaintenance/index.tsx`

### 8-A. 在 MATRIX_METRICS 之後加入可點擊 metric 對照表

```ts
const CLICKABLE_METRIC_MAP: Record<string, PMMatrixMetric> = {
  prev_carry_over:         'prev_carry_over',
  prev_resolved_in_period: 'prev_resolved',
  period_total:            'period_total',
  period_completed:        'period_completed',
}
```

### 8-B. 在 `renderCell` 中加入點擊邏輯

```tsx
const matricMetric = CLICKABLE_METRIC_MAP[row['_key'] as string]
const isClickable = !isTotal && num > 0 && !!matricMetric && !!onCellClick
if (isClickable) {
  return (
    <Typography.Text
      style={{ fontSize: 18, fontWeight: isTotal ? 600 : undefined, color: '#1677ff', textDecoration: 'underline', cursor: 'pointer' }}
      onClick={() => onCellClick!(data.year, monthNum, matricMetric, monthLabel)}
    >
      {num}
    </Typography.Text>
  )
}
```

### 8-C. 主元件加入 Modal state 與 openDetailModal

```ts
const [modalOpen,       setModalOpen]       = useState(false)
const [modalYear,       setModalYear]       = useState(0)
const [modalMonth,      setModalMonth]      = useState(0)
const [modalMetric,     setModalMetric]     = useState<PMMatrixMetric>('period_total')
const [modalFreqType,   setModalFreqType]   = useState<string>('')
const [modalMonthLabel, setModalMonthLabel] = useState('')

const openDetailModal = (freqType: string, year: number, month: number, metric: PMMatrixMetric, monthLabel: string) => {
  setModalFreqType(freqType)
  setModalYear(year)
  setModalMonth(month)
  setModalMetric(metric)
  setModalMonthLabel(monthLabel)
  setModalOpen(true)
}
```

### 8-D. MatrixDetailModal 元件

在主元件 return 的 `</>` 之前加入：

```tsx
<MatrixDetailModal
  open={modalOpen}
  year={modalYear}
  month={modalMonth}
  metric={modalMetric}
  frequencyType={modalFreqType}
  monthLabel={modalMonthLabel}
  onClose={() => setModalOpen(false)}
/>
```

在主元件外新增 `MatrixDetailModal` 函數元件（複製自 `hotel/periodic-maintenance` 的相同元件，將 `fetchPMMatrixItems` 替換為 `fetchMallPMMatrixItems`，`PMMatrixItem` 替換為 `MallPMMatrixItem`）。

```tsx
// METRIC_LABELS（放在 MatrixDetailModal 函數之前）
const METRIC_LABELS: Record<string, string> = {
  prev_carry_over:   '截至上月底累計未結案數',
  prev_resolved:     '其中本月已結案數',
  period_total:      '本期應完成總數',
  period_completed:  '本期已完成',
}
```

---

## 9. 前端：各 TAB 新增「保養項目」按鈕 + CatalogModal

**檔案：** `frontend/src/pages/MallPeriodicMaintenance/index.tsx`

### 9-A. import 更新

```ts
import { fetchMallPMCatalog } from '@/api/mallPeriodicMaintenance'
import type { MallPMCatalogItem } from '@/api/mallPeriodicMaintenance'
```

確認 `ToolOutlined` 已 import：
```ts
import { ..., ToolOutlined, ... } from '@ant-design/icons'
```

### 9-B. 主元件加入 Catalog Modal state + openCatalogModal

```ts
const [catalogOpen,     setCatalogOpen]     = useState(false)
const [catalogFreqType, setCatalogFreqType] = useState<'monthly' | 'quarterly' | 'yearly'>('monthly')
const [catalogItems,    setCatalogItems]    = useState<MallPMCatalogItem[]>([])
const [catalogLoading,  setCatalogLoading]  = useState(false)

const openCatalogModal = useCallback(async (freqType: 'monthly' | 'quarterly' | 'yearly') => {
  setCatalogFreqType(freqType)
  setCatalogOpen(true)
  setCatalogLoading(true)
  try {
    const res = await fetchMallPMCatalog(freqType)
    setCatalogItems(res.items)
  } catch {
    setCatalogItems([])
  } finally {
    setCatalogLoading(false)
  }
}, [])
```

### 9-C. 三個 TAB 的年度選擇器 Row 中，在「重新整理」按鈕之後新增

```tsx
<Col>
  <Button
    icon={<ToolOutlined />}
    type="primary"
    style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)', border: 'none' }}
    onClick={() => openCatalogModal('monthly')}   // quarterly / yearly 依各 TAB 修改
  >
    保養項目
  </Button>
</Col>
```

### 9-D. 主元件 return `</>` 前加入 CatalogModal

```tsx
<CatalogModal
  open={catalogOpen}
  frequencyType={catalogFreqType}
  items={catalogItems}
  loading={catalogLoading}
  onClose={() => setCatalogOpen(false)}
/>
```

### 9-E. CatalogModal 元件（加在 MatrixDetailModal 之後）

```tsx
const FREQ_TYPE_LABELS: Record<string, string> = {
  monthly:   '每月',
  quarterly: '每季',
  yearly:    '每年',
}

function CatalogModal({
  open, frequencyType, items, loading, onClose,
}: {
  open: boolean
  frequencyType: 'monthly' | 'quarterly' | 'yearly'
  items: MallPMCatalogItem[]
  loading: boolean
  onClose: () => void
}) {
  const columns: ColumnsType<MallPMCatalogItem> = [
    { title: '項次', dataIndex: 'seq_no', width: 60, align: 'center',
      render: (v: number) => <Typography.Text style={{ fontSize: 12 }}>{v}</Typography.Text> },
    { title: '類別', dataIndex: 'category', width: 90,
      render: (v: string) => <Tag color="blue" style={{ fontSize: 11 }}>{v}</Tag> },
    { title: '頻率', dataIndex: 'frequency', width: 80, align: 'center',
      render: (v: string) => <Tag color="purple" style={{ fontSize: 11 }}>{v}</Tag> },
    { title: '保養項目', dataIndex: 'task_name',
      render: (v: string) => <Typography.Text style={{ fontSize: 12 }}>{v}</Typography.Text> },
    { title: '區域/位置', dataIndex: 'location', width: 120,
      render: (v: string) => <Typography.Text style={{ fontSize: 12 }}>{v || '—'}</Typography.Text> },
    { title: '執行月份', dataIndex: 'exec_months_raw', width: 130,
      render: (v: string) => <Typography.Text style={{ fontSize: 11, color: '#666' }}>{v || '—'}</Typography.Text> },
    { title: '預估工時', dataIndex: 'estimated_minutes', width: 90, align: 'center',
      render: (v: number) => <Typography.Text style={{ fontSize: 12 }}>{v > 0 ? `${v} 分` : '—'}</Typography.Text> },
  ]

  const freqLabel = FREQ_TYPE_LABELS[frequencyType] || frequencyType

  return (
    <Modal open={open} onCancel={onClose} footer={null} width={900}
      title={
        <Space>
          <ToolOutlined style={{ color: '#764ba2' }} />
          <span style={{ fontWeight: 600 }}>{freqLabel}保養項目清單</span>
          {!loading && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>共 {items.length} 項</Typography.Text>
          )}
        </Space>
      }
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><Spin tip="載入保養項目中…" /></div>
      ) : (
        <Table
          dataSource={items}
          columns={columns}
          rowKey={(r) => `${r.category}-${r.seq_no}-${r.task_name}`}
          size="small"
          scroll={{ x: 800 }}
          pagination={{ pageSize: 15, showTotal: (t) => `共 ${t} 項`, showSizeChanger: false }}
        />
      )}
    </Modal>
  )
}
```

---

## 10. 重要注意事項

1. **ORM Model 確認**：商場端 Model 類別名稱可能是 `MallPeriodicMaintenanceBatch` / `MallPeriodicMaintenanceItem`，確認與 `mall_periodic_maintenance.py` 中的實際類別名相符後再套用代碼。

2. **main return 包 Fragment**：若主元件 `return` 尚未用 `<>...</>` 包住，在新增多個 Modal 後須改為：
   ```tsx
   return (
     <>
       <div style={{ padding: '0 4px' }}>
         ...
       </div>
       <MatrixDetailModal ... />
       <CatalogModal ... />
     </>
   )
   ```

3. **TypeScript 編譯驗證**：套用後執行：
   ```bash
   cd frontend && npx tsc --noEmit
   ```
   確認零錯誤後才部署。

4. **Dashboard 端點不受影響**：`GET /stats` 不傳 `frequency_type`，`_freq_match(freq, None)` 永遠回傳 `True`，全量資料不篩選。

5. **CHANGELOG 更新**：
   ```
   - vX.X.X：商場例行維護同步飯店例行維護 v1.57.26 規格 — 頻率分類統計（monthly/quarterly/yearly）、矩陣欄位標籤更新（①②+Tooltip）、保養項目按鈕+Modal、矩陣數字點擊明細
   ```
