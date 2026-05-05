# Portal 開發規範 — 標準化模式

---

## 模組開發三必要條件

每次新增模組或在現有模組新增 TAB，**必須**先確認以下三項：

| # | 項目 | 說明 |
|---|------|------|
| 1 | **中英文名稱與路徑** | 中文顯示名稱、英文模組 key、前端路由、後端 router 檔名 |
| 2 | **對應 Excel 表** | 資料結構來源，欄位定義必須依 Excel 確認 |
| 3 | **TAB 順序** | Dashboard（第1）→ 巡檢/保養表（第2）→ 統計 TABs → 批次清單（最後） |

---

## 模組命名對照表

| 中文名稱 | 英文 key | 前端路由 | 後端 router | 對應 Excel |
|----------|----------|---------|------------|-----------|
| 飯店週期保養表 | periodicMaintenance | `/hotel/periodic-maintenance` | `periodic_maintenance.py` | `#1.1每月飯店週期保養預定表.xlsx` |
| 商場週期保養表 | mallPeriodicMaintenance | `/mall/periodic-maintenance` | `mall_periodic_maintenance.py` | — |
| 全棟例行維護 | fullBuildingMaintenance | `/mall/full-building-maintenance` | `full_building_maintenance.py` | — |
| 飯店每日巡檢 | hotelDailyInspection | `/hotel/daily-inspection` | `hotel_daily_inspection.py` | `hoteldaily-inspection.xlsx` |
| 商場設施巡檢 | mallFacilityInspection | `/mall/facility-inspection` | `mall_facility_inspection.py` | `2.2商場-每日巡檢表.xlsx` |
| 整棟巡檢 | fullBuildingInspection | `/mall/full-building-inspection` | `full_building_inspection.py` | — |

> 新增模組時，在此表格補一行後再開始開發。

---

## TAB 順序規範

```
Dashboard          ← 永遠第 1
每日巡檢表 / 每月保養表  ← 永遠第 2（巡檢類用「每日巡檢表」，保養類用「每月保養表」）
每月維護           ← 統計 TABs
每季維護
每年維護
批次清單           ← 永遠最後（若有）
```

---

## 月曆格功能（MonthlyCalendarGrid）

本規範說明如何在任意模組的 Dashboard 新增「月曆格」：橫軸為日期（1–31 日），縱軸為自訂列（區域、類別、樓層等），格內顯示當日執行狀況。

---

### 架構總覽

```
後端                                   前端
────────────────────────────────────   ──────────────────────────────────────
GET /api/v1/{module}/calendar          fetchXxxCalendar(year, month)
  → { year, month, max_day, rows }  →  XxxCalendarResponse / CalendarRow
                                        ↓
                                       MonthlyCalendarGrid
                                        (components/MonthlyCalendarGrid.tsx)
```

---

### Step 1 — 後端：新增 calendar endpoint

**位置**：`backend/app/routers/{module}.py`

**回傳格式（固定不可更動）**：

```python
{
  "year":    int,
  "month":   int,
  "max_day": int,           # 該月最大日數（28–31）
  "rows": [
    {
      "key":   str,         # 唯一識別碼（snake_case）
      "label": str,         # 顯示名稱（中文）
      "daily": {
        "01": {             # 零填充日期字串 "01"–"31"
          "has_record":      bool,
          "completion_rate": int,   # 0–100
          "abnormal_count":  int,
          "pending_count":   int,
        },
        ...
      }
    },
    ...
  ]
}
```

**範例實作骨架**：

```python
import calendar as cal_mod
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db

@router.get("/calendar", summary="月曆格（列 × 日期）")
def get_calendar(
    year:  int = Query(...),
    month: int = Query(...),
    db:    Session = Depends(get_db),
):
    ROWS = ["列A", "列B", "列C"]   # 依模組替換

    max_day = cal_mod.monthrange(year, month)[1]

    # 查詢該月資料 ─────────────────────────────────────────────
    # items = db.query(MyModel).filter(...).all()

    # 依 (row_key, day_str) 分組統計 ──────────────────────────
    # grid: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(dict))
    # for item in items:
    #     day_str = f"{item.date.day:02d}"
    #     grid[item.row_key][day_str] = {計算 completed/total/...}

    rows_out = []
    for key in ROWS:
        daily = {}
        for d in range(1, max_day + 1):
            day_str = f"{d:02d}"
            bucket  = grid.get(key, {}).get(day_str, {})
            total   = bucket.get("total", 0)
            done    = bucket.get("completed", 0)
            daily[day_str] = {
                "has_record":      total > 0,
                "completion_rate": round(done / total * 100) if total else 0,
                "abnormal_count":  bucket.get("overdue", 0),
                "pending_count":   bucket.get("in_progress", 0),
            }
        rows_out.append({"key": key, "label": key, "daily": daily})

    return {"year": year, "month": month, "max_day": max_day, "rows": rows_out}
```

**注意事項**：
- 所有列（即使當日無資料）都必須出現在 `rows`；`has_record=false` 表示無資料
- `day_str` 必須是零填充字串（`"01"`、`"09"`），不可用整數 key
- endpoint 路徑使用 `/calendar`，與模組前綴組合後為 `/api/v1/{module}/calendar`

---

### Step 2 — 後端：語法驗證

```bash
python3 -c "import py_compile; py_compile.compile('backend/app/routers/{module}.py', doraise=True); print('OK')"
```

---

### Step 3 — 前端：API 型別與 fetch 函式

**位置**：`frontend/src/api/{module}.ts`

```typescript
import type { CalendarRow } from '@/components/MonthlyCalendarGrid'

export interface XxxCalendarResponse {
  year:    number
  month:   number
  max_day: number
  rows:    CalendarRow[]
}

export async function fetchXxxCalendar(year: number, month: number): Promise<XxxCalendarResponse> {
  const res = await apiClient.get<XxxCalendarResponse>(`${BASE}/calendar`, { params: { year, month } })
  return res.data
}
```

---

### Step 4 — 前端：頁面整合

**位置**：`frontend/src/pages/{Module}/index.tsx`

**4-1 新增 imports**：

```typescript
import MonthlyCalendarGrid from '@/components/MonthlyCalendarGrid'
import type { CalendarRow } from '@/components/MonthlyCalendarGrid'
import { fetchXxxCalendar } from '@/api/{module}'
```

**4-2 新增 state**（放在其他 state 宣告區）：

```typescript
const [calRows,   setCalRows]   = useState<CalendarRow[]>([])
const [calMaxDay, setCalMaxDay] = useState(31)
```

**4-3 在 `loadDashboard`（或同等函式）中平行載入**：

```typescript
const [data, calData] = await Promise.all([
  fetchXxxStats(year, month),
  fetchXxxCalendar(parseInt(year), month).catch(() => null),
])
setData(data)
if (calData) {
  setCalMaxDay(calData.max_day)
  setCalRows(calData.rows)
}
```

**4-4 在 DashboardTab JSX 底部新增 Card**：

```tsx
<Card
  size="small"
  style={{ marginTop: 16 }}
  title={
    <Space>
      <CalendarOutlined />
      <Text strong>XXX 每日狀況</Text>
      <Text type="secondary" style={{ fontSize: 12 }}>
        （{year}/{String(month).padStart(2, '0')}）
      </Text>
    </Space>
  }
  loading={loading}
>
  {calRows.length > 0 ? (
    <MonthlyCalendarGrid
      year={parseInt(year)}
      month={month}
      maxDay={calMaxDay}
      rows={calRows}
      rowHeaderLabel="列標題"      {/* 依模組替換 */}
    />
  ) : (
    <Text type="secondary">尚無月曆資料</Text>
  )}
</Card>
```

---

### MonthlyCalendarGrid Props 參考

| Prop | 型別 | 必填 | 說明 |
|------|------|------|------|
| `year` | `number` | ✓ | 西元年 |
| `month` | `number` | ✓ | 月份（1–12） |
| `maxDay` | `number` | ✓ | 該月最大日數（後端 `max_day`） |
| `rows` | `CalendarRow[]` | ✓ | 列資料（含 `key / label / daily`） |
| `rowHeaderLabel` | `string` | — | 左上角標題（預設：`巡檢區域`） |
| `renderCell` | `(day, data?) => ReactNode` | — | 自訂格內容（不填用預設圖示） |
| `cellStyle` | `(day, data?) => CSSProperties` | — | 自訂格底色（不填用預設色彩規則） |
| `legend` | `LegendItem[]` | — | 自訂圖例（不填用預設 4 項圖例） |

**預設格內容邏輯**：

| 條件 | 顯示 | 底色 |
|------|------|------|
| `!has_record` | `—` | 白 |
| `abnormal_count > 0 \|\| pending_count > 0` | `⚠` | 淺紅 `#fff1f0` |
| `completion_rate === 100` | `✓` | 淺綠 `#f6ffed` |
| 其他（部分完成） | `{rate}%` | 淺藍 `#e6f4ff` |

---

### 現有模組清單

| 模組 | endpoint | `rowHeaderLabel` | 列定義來源 |
|------|----------|-----------------|-----------|
| `hotel/daily-inspection` | `GET /daily-calendar` | `巡檢區域` | RF / 4F~10F / 4F / 2F / 1F |
| `mall/periodic-maintenance` | `GET /mall-facility-inspection/daily-calendar` | `巡檢區域` | 商場 5 樓層 |
| `hotel/periodic-maintenance` | `GET /periodic-maintenance/calendar` | `保養類別` | 水電/空調/機修/裝修/弱電 |

---

### 開發 Checklist

- [ ] 後端 endpoint 回傳含 `max_day` + `rows`（含無資料列）
- [ ] `day_str` 零填充（`"01"` ～ `"31"`）
- [ ] `py_compile` 語法驗證通過
- [ ] 前端 API 函式使用 `CalendarRow[]` 型別（不自定義 `daily` 型別）
- [ ] Dashboard state 新增 `calRows / calMaxDay`
- [ ] `loadDashboard` 用 `Promise.all` 平行載入，calendar 失敗時 `.catch(() => null)` 不阻斷主資料
- [ ] Card 加 `loading={loading}` prop
- [ ] `calRows.length === 0` 時顯示 `尚無月曆資料`
- [ ] CHANGELOG.md 更新
- [ ] README.md 更新最後更新日期與最近變更

---

### 常見錯誤

**錯誤：`daily` 用整數 key**
```python
# ❌
daily[d] = {...}
# ✓
daily[f"{d:02d}"] = {...}
```

**錯誤：無資料的列不輸出**
```python
# ❌ 只在有資料時才 append
# ✓ 固定列清單全部輸出，無資料時 has_record=false
```

**錯誤：在元件內直接 axios，未用 @/api/ 封裝**
```typescript
// ❌ axios.get('/api/v1/...')
// ✓ import { fetchXxxCalendar } from '@/api/{module}'
```

**錯誤：calendar fetch 失敗時阻斷整個 loadDashboard**
```typescript
// ❌ const [data, cal] = await Promise.all([fetchStats(), fetchCalendar()])
// ✓ const [data, cal] = await Promise.all([fetchStats(), fetchCalendar().catch(() => null)])
```
