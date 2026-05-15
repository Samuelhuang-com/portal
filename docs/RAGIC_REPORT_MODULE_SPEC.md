# Ragic Report Module — 標準開發規格 (SPEC)

> **版本：** v1.0（基於 purchase-report + claim-report 完整開發經驗）  
> **適用：** 任何「Ragic → SQLite → FastAPI → React 月報表」模組  
> **使用方式：** 新開發時在 Claude Code 下達 Section 9 的標準提示詞

---

## 目錄

1. [模組架構總覽](#1-模組架構總覽)
2. [後端：ORM Model](#2-後端orm-model)
3. [後端：Sync Service](#3-後端sync-service)
4. [後端：FastAPI Router](#4-後端fastapi-router)
5. [後端：main.py 整合](#5-後端mainpy-整合)
6. [前端：API 封裝層](#6-前端api-封裝層)
7. [前端：頁面元件](#7-前端頁面元件)
8. [關聯模組整合](#8-關聯模組整合)
9. [標準開發提示詞（Claude Code 用）](#9-標準開發提示詞claude-code-用)
10. [已知坑位清單（Bug Graveyard）](#10-已知坑位清單bug-graveyard)
11. [多分公司部署差異點](#11-多分公司部署差異點)

---

## 1. 模組架構總覽

```
Ragic API（各部門 Sheet × N）
    ↓ sync_list_only()（每 15/30 分）
approved_xxx_requests（主單表）       raw_data_json ← 保留完整原始欄位
    ↓ sync_detail_batch()（每 45 分）
approved_xxx_request_items（品項表）   detail_synced=True

FastAPI Routers
  /api/v1/xxx-report/approved/orders    ← 主清單（分頁）
  /api/v1/xxx-report/approved/monthly   ← 月報明細（品項級）
  /api/v1/xxx-report/approved/summary   ← KPI
  /api/v1/xxx-report/approved/departments ← 部門統計
  /api/v1/xxx-report/approved/export    ← Excel
  /api/v1/xxx-report/approved/available-months
  /api/v1/xxx-report/config/*           ← 篩選用下拉清單
  /api/v1/xxx-report/sync               ← 手動觸發同步
  /api/v1/xxx-report/sync/status
  /api/v1/xxx-report/admin/reparse-*   ← 就地修正 DB（不重抓 Ragic）

React 頁面（src/pages/XxxReport/index.tsx）
  TAB-1：主單清單（可點列開 Drawer）
  TAB-2：月報明細（品項級）
  TAB-3：部門統計（跨部門並排）
  TAB-4：資料異常稽核
```

---

## 2. 後端：ORM Model

**檔案：** `backend/app/models/xxx_request.py`

### 2.1 必備欄位

```python
class ApprovedXxxRequest(Base):
    __tablename__ = "approved_xxx_requests"
    id                  = Column(Integer, primary_key=True, autoincrement=True)
    company             = Column(String(20), nullable=False, default="樂群")
    department_raw      = Column(String(50))          # Ragic 原始部門值
    department_display  = Column(String(50))          # 對照 DISPLAY_MAP 後的顯示名
    ragic_sheet_path    = Column(String(200))         # 用於 Ragic URL 組合
    ragic_record_id     = Column(String(50))
    request_no          = Column(String(100))         # ⚠️ 允許 NULL，各部門欄位名不同
    apply_date          = Column(Date)
    approved_date       = Column(Date)                # ⚠️ 需三層 fallback 取值
    raw_data_json       = Column(Text)                # ⚠️ 必須保留，供 reparse 使用
    detail_synced       = Column(Boolean, default=False, nullable=False)
    synced_at           = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("ragic_sheet_path", "ragic_record_id",
                         name="uq_xxx_ragic_record"),
    )
```

### 2.2 ⛔ 禁止事項

| 禁止 | 原因 |
|------|------|
| `nullable=False` 且無 `default` 的新欄位 | SQLite ALTER TABLE 無法加 NOT NULL 無預設欄位 |
| 不存 `raw_data_json` | 欄位名稱錯誤只能重抓 Ragic，不能就地修復 |
| `async` SQLAlchemy | 專案統一使用 sync，混用會導致 session 衝突 |

### 2.3 部門對照表

```python
XXX_DEPT_DISPLAY_MAP: dict[str, str] = {
    "執董室": "執董室",
    "營業":   "營業部",
    "客服":   "客服部",
    # ...
}

XXX_DEPT_SHEETS: list[dict] = [
    {
        "display_name": "執董室",
        "ragic_dept":   "執董室",    # Ragic API 過濾值（可能與 display_name 不同）
        "list_path":    "free-executive-office/9",
        "detail_path":  "free-executive-office/9",
        "flow_type":    "零用金型",
    },
    # ... 各部門
]
```

### 2.4 ⛔ Ragic Sheet 不可跨模組共用（強制規則）

> **規則：每個模組必須在自己的 `models/xxx_request.py` 內維護獨立的 `XXX_DEPT_SHEETS` 與 `XXX_DEPT_DISPLAY_MAP`。任何情況下不得跨模組 import 或共用這些常數。**

| 禁止行為 | 原因 |
|----------|------|
| `from app.models.claim_request import CLAIM_DEPT_SHEETS` 用在 nichiyo sync | 兩個模組同步目標不同（請購 vs 請款），邏輯耦合後任一方改動會靜默破壞另一方 |
| `from app.models.nichiyo_purchase_request import NICHIYO_DEPT_SHEETS` 用在 claim sync | 同上；即使當下 URL 相同，未來 Sheet 會分開演化 |
| 把兩個模組共用的 Sheet 設定提取到 `shared_config.py` | 看似 DRY，實為 wrong abstraction——部門清單、欄位映射、flow_type 定義都是各模組私有知識 |

**正確做法：**
```
backend/app/models/
  purchase_request.py       → DEPT_SHEETS（樂群請購，lequn-*）
  claim_request.py          → CLAIM_DEPT_SHEETS（樂群請款，free-*）
  nichiyo_purchase_request.py → NICHIYO_DEPT_SHEETS（日曜請購，free-*）
  # 每個模組完全獨立，互不 import
```

即使兩個模組的 Sheet URL 在某個時間點完全相同，常數也必須各自維護。Ragic Sheet 結構會隨業務獨立演化，保持隔離是防止靜默錯誤的唯一方式。

---

## 3. 後端：Sync Service

**檔案：** `backend/app/services/xxx_request_sync.py`

### 3.1 欄位候選清單模式

```python
LIST_FIELD_CANDIDATES: dict[str, list[str]] = {
    # 按優先序排列，_pick() 取第一個有值的
    "request_no": [
        "編號", "請款單號", "單號",
        "管請編號", "財請編號",        # 各部門前綴短標籤
        "樂行購編號",                   # 帶「樂」前綴的命名
        "職請編號",                     # 執董室實際欄位名
        # ... 加入所有已知變體
    ],
}
```

### 3.2 ⚠️ `request_no` 專用取值函式（含 Regex Fallback）

```python
_REQUEST_NO_RE = re.compile(r"^樂.+請\d{8,}")

def _pick_request_no(data: dict, candidates: list[str]) -> str:
    """候選清單 → Regex Fallback（樂X請YYYYMMXXX 格式）"""
    for key in candidates:
        val = data.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    # Fallback：掃全部欄位值，找符合單號格式的
    for key, val in data.items():
        if isinstance(val, str) and _REQUEST_NO_RE.match(val.strip()):
            logger.debug("request_no regex fallback: key=%r val=%r", key, val)
            return val.strip()
    return ""
```

> **為何必要：** 9 個部門各自命名欄位（職請編號 / 樂資請編號 / 樂行購編號...），  
> 無法事先枚舉所有變體。Regex 掃值是根本解決方案。

### 3.3 `approved_date` 三層 Fallback

```python
def _parse_approved_date(data: dict) -> date | None:
    """
    各部門核准日期欄位名不同，且工作流程可能無「日期N」欄位。
    三層 fallback 確保不 fallback 到同步日期（last_updated_dt）。
    """
    # 層 1：工作流日期欄位（Ragic 核准流程）
    for key in ["日期1", "日期2", "日期3", "日期4", "日期5"]:
        if val := _to_date(data.get(key)):
            return val
    # 層 2：語意明確的日期欄位
    for key in ["核准日期", "付款日期", "簽核完成日期"]:
        if val := _to_date(data.get(key)):
            return val
    # 層 3：申請日期（最後手段）
    return _to_date(data.get("申請日期") or data.get("填單日期"))
    # ⛔ 絕對不用 last_updated_dt 作為 approved_date
```

### 3.4 sorted() 的 None 陷阱

```python
# ❌ 錯誤：當 department_display=None 時 sorted() 拋 TypeError
sorted(departments)

# ✅ 正確：加 key=lambda x: x or ""
sorted(departments, key=lambda x: x or "")
```

### 3.5 func.sum() 的 None 陷阱

```python
# SQLAlchemy func.sum() 在全為 NULL 時回傳 None，不是 0
# ❌ 錯誤：None 會被 coalesce(item_sum, 0) 轉為 0，與 amount=500 比較 → 誤報異常
.filter(func.abs(coalesce(amount, 0) - item_sum_sq.c.item_sum) > 1)

# ✅ 正確：先排除 NULL（代表「尚未同步」，非「金額=0」）
.filter(
    item_sum_sq.c.item_sum.isnot(None),
    func.abs(coalesce(amount, 0) - item_sum_sq.c.item_sum) > 1,
)
```

### 3.6 Sync 函式命名規範

```python
async def sync_list_only() -> dict:
    """清單同步（每 15/30 分）— main.py APScheduler 呼叫"""

async def sync_detail_batch() -> dict:
    """Detail 品項同步（每 45 分）— main.py APScheduler 呼叫"""

async def sync_all() -> dict:
    """清單 + Detail 完整同步（手動觸發）"""
```

### 3.7 RAGIC_SERVER / ACCOUNT 設定

```python
# ⚠️ 目前硬碼，不從 settings 讀取（purchase/claim sync service 現況）
RAGIC_SERVER  = "ap12.ragic.com"
RAGIC_ACCOUNT = "soutlet001"
# 若分公司 Ragic 帳號不同，必須在此修改（或改為從 settings 讀取）
```

---

## 4. 後端：FastAPI Router

**檔案：** `backend/app/routers/xxx_report.py`

### 4.1 標準端點清單

```
GET  /approved/orders             主單清單（分頁 + 篩選）
GET  /approved/orders/{id}        單筆詳情（含品項）
GET  /approved/monthly            月報明細（品項級，分頁）
GET  /approved/summary            KPI 統計
GET  /approved/departments        部門彙總
GET  /approved/export             Excel 匯出（StreamingResponse）
GET  /approved/available-months   有資料的年月清單（DatePicker 限制用）
GET  /config/departments          部門下拉
GET  /config/account-categories   會科下拉
POST /sync                        手動觸發同步（BackgroundTasks）
GET  /sync/status                 同步狀態 + pending count
POST /admin/reparse-{field}       就地修正 DB 欄位（不重抓 Ragic）
```

### 4.2 日期篩選三模式

```python
# 所有端點統一使用 year_month_from + year_month_to
# 前端傳值規則：
#   單月模式：from = to = "2026-05"
#   全年度：  from = "2026-01", to = "2026-12"
#   自訂區間：from / to 由使用者選擇

@router.get("/approved/orders")
def get_approved_orders(
    year_month_from: str = Query("", description="YYYY-MM"),
    year_month_to:   str = Query("", description="YYYY-MM"),
    department:      Optional[str] = Query(None),
    q:               Optional[str] = Query(None),  # 全文搜尋
    page:            int = Query(1, ge=1),
    per_page:        int = Query(20, ge=1, le=200),
    # ...
):
```

### 4.3 Excel 匯出中文檔名

```python
# ⚠️ Content-Disposition 必須用 RFC 5987 編碼，否則 Starlette Latin-1 報錯
from urllib.parse import quote
encoded_name = quote(filename, encoding='utf-8')
headers = {
    "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"
}
return StreamingResponse(io.BytesIO(excel_bytes), headers=headers,
                         media_type="application/vnd.openxmlformats...")
```

### 4.4 Reparse 端點模式

```python
@router.post("/admin/reparse-{field}")
def reparse_field(db: Session = Depends(get_db), _=Depends(require_permission(_PERM))):
    """
    從 raw_data_json 就地修復欄位值。
    回傳 still_null 清單（含欄位 key 清單）供診斷。
    """
    from app.services.xxx_sync import _pick_request_no, LIST_FIELD_CANDIDATES
    total, updated, still_null, errors = 0, 0, [], []
    for rec in db.query(XxxRequest).filter(XxxRequest.raw_data_json.isnot(None)).all():
        total += 1
        raw = json.loads(rec.raw_data_json)
        new_val = _pick_request_no(raw, LIST_FIELD_CANDIDATES["request_no"]) or None
        if new_val != rec.request_no:
            rec.request_no = new_val
            updated += 1
        if not new_val:
            still_null.append({
                "id": rec.id, "ragic_id": rec.ragic_record_id,
                "department": rec.department_display,
                "no_related_keys": [k for k in raw if "號" in k],
                "all_keys_sample": list(raw.keys())[:30],
            })
    db.commit()
    return {"total": total, "updated": updated, "still_null": still_null, "errors": errors[:20]}
```

---

## 5. 後端：main.py 整合

### 5.1 ⛔ 最易遺漏的步驟：include_router

```python
# backend/app/main.py

# Step A — Import（通常記得）
from app.routers import xxx_report, yyy_report

# Step B — include_router（⚠️ 最常忘記！少了這行 = 全部端點 404）
app.include_router(
    xxx_report.router,
    prefix=f"{API_PREFIX}/xxx-report",
    tags=["XXX月報表"],
)
```

> **真實案例：** `combined_report` 在 `main.py` 有 import 但缺 `include_router()`，  
> 導致所有 `/api/v1/combined-report/*` 請求 404，前端靜默顯示空資料，  
> 耗時數小時除錯才發現根本原因。

### 5.2 APScheduler 排程（新增至 `_auto_sync`）

```python
async def _auto_sync():
    # ... 現有同步 ...
    from app.services.xxx_request_sync import sync_list_only as sync_xxx_list
    await _run_and_log("XXX清單", sync_xxx_list())
```

**Detail 批次同步（額外排程）**，在 `lifespan` 中加：

```python
# 每 45 分同步一次 Detail
_scheduler.add_job(
    lambda: asyncio.create_task(sync_xxx_detail()),
    CronTrigger(minute="*/45"),
    id="sync_xxx_detail",
    replace_existing=True,
)
```

### 5.3 前端靜默 404 問題

```python
# 後端 404 → 前端 axios 無 .catch() → 空 state 靜默顯示
# 防禦：後端端點未就緒前加佔位回應，不要讓 404 傳出去
```

---

## 6. 前端：API 封裝層

**檔案：** `frontend/src/api/xxxReport.ts`

```typescript
import axios from "axios";

const API = "/api/v1/xxx-report";

export interface XxxOrderRow {
  id: number;
  ragic_id: string;
  department_display: string;
  request_no: string | null;      // nullable！
  approved_date: string;
  amount: number | null;
  detail: Record<string, string>; // Drawer 明細用
  // ...
}

// 統一參數介面（三模式日期篩選）
interface DateParams {
  year_month_from?: string;
  year_month_to?: string;
}

export const getXxxOrders = (params: DateParams & {
  department?: string;
  q?: string;
  page?: number;
  per_page?: number;
}) =>
  axios.get<{ items: XxxOrderRow[]; total: number }>(`${API}/approved/orders`, { params })
    .then(r => r.data);

// ⚠️ 注意：per_page 不是 page_size（常見命名錯誤）
```

---

## 7. 前端：頁面元件

**檔案：** `frontend/src/pages/XxxReport/index.tsx`

### 7.1 TAB 結構（固定順序）

```
TAB-1：主單清單     key="orders"
TAB-2：月報明細     key="monthly"
TAB-3：部門統計     key="dept"      ← 不設 key="combined"（已移除）
TAB-4：資料異常     key="audit"
```

### 7.2 Tab 群組判斷

```typescript
const isOrdersTab   = activeTab === "orders" || activeTab === "orders-detail"
const isMonthlyTab  = activeTab === "monthly"
const isCombinedTab = activeTab === "dept"    // ⚠️ 只對應 "dept"，不含 "combined"
const isAuditTab    = activeTab === "audit"
```

### 7.3 頁面標題邏輯

```typescript
// 依 Tab 群組切換標題
const pageTitle = isOrdersTab   ? "核准XXX單月報表"
                : isMonthlyTab  ? "核准XXX單月報表"
                : isCombinedTab ? "部門統計"
                : "資料異常稽核"
```

### 7.4 主單清單（TAB-1）欄位標準順序

以 `purchase-report` 為基準，所有同類模組必須對齊：

| 欄位 | width | 說明 |
|------|-------|------|
| 編號（purchase_no） | 190 | `fixed: 'left'`, monospace, ellipsis |
| 部門（department_display） | 80 | `blue` Tag（⚠️ 非 geekblue） |
| 會科（account_category） | 110 | ellipsis |
| 申請人（applicant） | 80 | — |
| 說明（description） | flex | ellipsis |
| 擬定廠商（selected_vendors） | 160 | 子表品項廠商聚合，ellipsis |
| 全案小計（amount） | 110 | right-align, bold, `#1B3A5C` |
| 狀態（status） | 80 | statusTag() |
| 核准日期（approved_date） | 100 | 12px gray |
| ''（action） | 48 | `fixed: 'right'`, `<EyeOutlined />` 觸發 Drawer |

`scroll={{ x: 1000 }}`，`onRow` click 也觸發 Drawer（與 EyeOutlined 雙觸發）。

### 7.5 Drawer 強制規範（以 purchase-report 為基準）

| 條件 | 規格 |
|------|------|
| 寬度 | **680px**（⚠️ 非 480px；工作日誌模組才用 480px） |
| 有附圖 | 寬度 640px，用 `Image.PreviewGroup` Lightbox |
| 點擊列觸發 | `Table onRow` click + 右側固定欄 `EyeOutlined` 按鈕 |
| Descriptions | `column={2}`，**結構化明確欄位**，非 detail dict |
| 欄位順序 | 編號(span=2) → 申請日期/核准日期 → 部門/申請人 → 會科(span=2) → 說明(span=2) → 廠商(一)/(二) → 廠商(三 if exists) → 廠商資訊(if !detail_synced) → 全案小計/營業稅 → 簽核狀態/最後更新 → 備註(if exists) |
| 品項區 | `Typography.Title level={5}` + `Table` 直接顯示（**不用 Collapse**）；無品項時 `Alert` |
| 狀態欄 | 彩色 Tag |
| 費用欄 | fmt() 格式化，粗體 + `#1B3A5C` 主色 |
| 空值 | `'-'` 或 `'—'` |
| Ragic 連結 | `<Button type="link">在 Ragic 中開啟 ↗</Button>`，`textAlign: right` |

**⚠️ SPEC 誤差說明（2026-05-14 修正）：**  
原始 SPEC 寫的「480px + detail dict 兩段 Descriptions」是 WORK_JOURNAL_SPEC 的規格，**不適用於報表模組**。  
報表模組 Drawer 規格應以 `purchase-report/PurchaseReport/index.tsx` 的實作為準。

**`handleOpenDrawer` 必須接受 `orderId: number`（不接受整個 row 物件）：**

```typescript
// ✅ 正確：接受純 ID，TAB-1 / TAB-2 共用
const handleOpenDrawer = async (orderId: number) => {
  setDrawerOpen(true)
  setDrawerLoading(true)
  setSelectedOrder(null)
  const r = await getXxxOrderDetail(orderId)
  setSelectedOrder(r.data)  // r.data = { order: {...}, items: [...] }
}

// ❌ 錯誤：接受整個 row 物件，TAB-2 只有 order_id 無法傳完整物件
const handleOpenDrawer = async (order: XxxOrder) => { ... }
```

後端 `GET /approved/orders/{id}` 回傳結構**必須**是：
```json
{ "order": { ...所有主單欄位... }, "items": [ ...品項... ] }
```
⚠️ 不可回傳 flat dict（`{ id, purchase_no, ..., items: [] }`）— 前端 `selectedOrder.order` 會永遠是 `undefined`，Drawer 完全空白。

### 7.6 月報明細（TAB-2）onRow Drawer

TAB-2 月報明細（品項級）的 Table **必須**加 `onRow` 觸發 Drawer：

```typescript
// ✅ 必做：TAB-2 品項 Table 也要有 Drawer
<Table
  dataSource={items}
  rowKey={(r) => `${r.order_id}-${r.item_id ?? r.seq}`}
  onRow={(r) => ({ onClick: () => handleOpenDrawer(r.order_id), style: { cursor: 'pointer' } })}
  ...
/>
```

品項 row 只有 `order_id`（沒有完整 order 物件），因此 `handleOpenDrawer` 接受 number 是前提。

### 7.7 日期模式 Segmented

```typescript
// Header 共用（三模式）
<Segmented value={dateMode} onChange={handleDateModeChange}
  options={[
    { label: "單月", value: "month" },
    { label: "全年度", value: "year" },
    { label: "自訂區間", value: "range" },
  ]} />

// 依模式顯示對應選擇器
{dateMode === "month"  && <DatePicker picker="month" ... />}
{dateMode === "year"   && <DatePicker picker="year" ... />}
{dateMode === "range"  && <DatePicker.RangePicker picker="month" ... />}
```

### 7.8 部門統計（TAB-3）欄位命名規範

部門統計 Table 依「業務組合」分為兩種型態，**規格不同，不可混用**：

#### 型態 A：單一業務模組（如 NichiyoPurchaseReport）

只顯示單一業務（純請購或純請款），變數命名 `deptColumns`：

| 欄位 | dataIndex | width | 說明 |
|------|-----------|-------|------|
| 部門 | department_display | 100 | `blue` Tag（⚠️ 非 `geekblue`） |
| 請購單數 | order_count | 90 | right-align, bold `#1B3A5C` |
| 請購未稅合計 | total_amount | — | right-align, bold `#1B3A5C` |
| 請購稅額 | total_tax | 100 | right-align |
| 請購占比 | — | 160 | `<Progress>` strokeColor `#4BA8E8` |

#### 型態 B：請購 + 請款合併統計（PurchaseReport / ClaimReport）

同時顯示請購（藍 `#1B3A5C`）+ 請款（橙 `#d46b08`）雙色欄位，變數命名 `combinedDeptColumns`：

| 欄位 | dataIndex | 顏色 | 說明 |
|------|-----------|------|------|
| 部門 | department_display | `geekblue` Tag | 合併視圖用 `geekblue`（區別於單色 `blue`） |
| 請購單數 | purchase_count | `#1B3A5C` | — |
| 請購未稅合計 | purchase_amount | `#1B3A5C` bold | — |
| 請購稅額 | purchase_tax | `#1B3A5C` | — |
| 請款筆數 | claim_count | `#d46b08` | — |
| 請款應付合計 | claim_payable | `#d46b08` bold | — |
| 請款稅額 | claim_tax | `#d46b08` | — |
| 請購占比 | — | `#4BA8E8` Progress | 以請購金額為基準 |

**命名原則（共通）：** 欄位標題 = `{業務前綴}{語意}`，**禁止**用無前綴的通用名稱：

| ❌ 禁止 | ✅ 正確（請購）| ✅ 正確（請款）|
|---------|--------------|--------------|
| 單據筆數 | 請購單數 | 請款筆數 |
| 未稅合計 | 請購未稅合計 | 請款應付合計 |
| 稅額 | 請購稅額 | 請款稅額 |
| 占比 | 請購占比 | — |

**現況驗證（2026-05-14）：**
- `NichiyoPurchaseReport`：型態 A，欄位已對齊 ✅，Tag `blue` ✅
- `PurchaseReport`：型態 B，欄位已對齊 ✅，Tag `geekblue` ✅
- `ClaimReport`：型態 B（與 PurchaseReport 共用相同 combinedDeptColumns 結構），欄位已對齊 ✅，Tag `geekblue` ✅

**Summary Row 合計行**（必須與欄位欄數對齊）：
```typescript
<Table.Summary.Row style={{ background: '#f0f4f8', fontWeight: 600 }}>
  <Table.Summary.Cell index={0}>合計</Table.Summary.Cell>
  <Table.Summary.Cell index={1} align="right">{totalCnt}</Table.Summary.Cell>
  <Table.Summary.Cell index={2} align="right">{fmt(totalAmt)}</Table.Summary.Cell>
  <Table.Summary.Cell index={3} align="right">{fmt(totalTax)}</Table.Summary.Cell>
  <Table.Summary.Cell index={4} />   {/* 占比欄空白 */}
</Table.Summary.Row>
```

### 7.9 部門統計 Admin 折疊面板規範

部門統計 TAB 底部的管理員同步控制面板，**必須**使用以下完整結構：

```typescript
{isAdmin && (
  <Collapse style={{ marginTop: 24 }}
    items={[{   // ⚠️ AntD5 items API，不用 <Collapse.Panel>
      key: 'sync',
      label: (
        <Space>
          <SyncOutlined />同步狀態管理
          {(syncStatus?.pending_detail_count ?? 0) > 0 && (
            <Badge count={syncStatus!.pending_detail_count} size="small" />
          )}
        </Space>
      ),
      children: (
        <Card size="small" title={...}>
          {/* 按鈕列：增量 / 全量 / 刷新 */}
          <Space style={{ marginBottom: 12 }}>
            <Button type="primary" size="small" icon={<SyncOutlined spin={syncing} />}
              loading={syncing} onClick={() => handleSync(false)}>增量同步</Button>
            <Button danger size="small" loading={syncing}
              onClick={() => Modal.confirm({
                title: '確認全量重新同步？',
                content: '將重設所有品項 detail_synced 旗標，重新抓取所有部門的請購品項明細。',
                okText: '確認執行', cancelText: '取消',
                onOk: () => handleSync(true),
              })}>全量同步</Button>
            <Button size="small" icon={<SyncOutlined />}
              onClick={loadSyncStatus} loading={syncLoading}>刷新</Button>
          </Space>

          {/* 待同步 Alert */}
          {(syncStatus?.pending_detail_count ?? 0) > 0 && (
            <Alert type="warning" showIcon style={{ marginBottom: 12 }}
              message={`尚有 ${syncStatus!.pending_detail_count} 筆未完成品項同步`} />
          )}

          <Spin spinning={syncLoading}>
            {/* 部門同步率 Table（含 Progress） */}
            {(syncStatus?.dept_stats?.length ?? 0) > 0 && (
              <Table dataSource={syncStatus!.dept_stats} ... columns={[
                { title: '部門', render: (v) => <Tag color="geekblue">{v}</Tag> },
                { title: '主單', dataIndex: 'total' },
                { title: '已同步', dataIndex: 'detail_synced', render: (v) => <span style={{color:'#52c41a'}}>{v}</span> },
                { title: '待同步', dataIndex: 'pending', render: (v) => <span style={{color: v > 0 ? '#fa8c16' : '#aaa'}}>{v}</span> },
                { title: '同步率', render: (_, r) => {
                    const pct = r.total > 0 ? Math.round(r.detail_synced / r.total * 100) : 100
                    return <Progress percent={pct} size="small"
                      strokeColor={pct === 100 ? '#52c41a' : '#fa8c16'} />
                  } },
              ]} />
            )}

            {/* 最近同步 Log Table */}
            <Table dataSource={syncStatus?.recent_logs ?? []} ... columns={[
              { title: '時間', dataIndex: 'created_at', render: (v) => v?.slice(0,19).replace('T',' ') },
              { title: '觸發', dataIndex: 'trigger' },
              { title: '狀態', dataIndex: 'status', render: (v) => <Tag color={...}>{v}</Tag> },
              { title: '訊息', dataIndex: 'message', ellipsis: true },
            ]} />
          </Spin>
        </Card>
      ),
    }]}
  />
)}
```

**必備欄位（`sync/status` 端點 Response）：**
```json
{
  "pending_detail_count": 12,
  "dept_stats": [
    { "department_display": "執董室", "total": 5, "detail_synced": 3, "pending": 2 }
  ],
  "recent_logs": [
    { "id": 1, "created_at": "2026-05-14T10:00:00", "trigger": "manual",
      "status": "success", "message": "同步完成 3 筆" }
  ]
}
```

### 7.10 KPI 卡片（固定格式）

```typescript
// 6 欄，Card size="small"，每欄一個 Statistic
// 顏色：主色 #1B3A5C、輔色 #4BA8E8、金額橙 #d46b08、稅綠 #52c41a
```

---

## 8. 關聯模組整合

### 8.1 settings/ragic-connections

在 Ragic Connections 設定頁面為每個部門 Sheet 新增一筆連線記錄。  
`sync_tool.py` 掃描此表自動同步，不在此表的 Sheet 不會被自動同步。

```
display_name: "核准請XXX單 — 執董室"
sheet_path:   "lequn-executive-office/9"
sync_interval: 900    (15 分 = 900 秒)
is_active:    true
module_tag:   "xxx_request"
```

### 8.2 settings/roles — Permission Key 命名規範

```python
# 格式：{模組}.{動作}
"purchase_report.view"    # 查看請購月報
"claim_report.view"       # 查看請款月報
"xxx_report.view"         # 新模組遵循同格式
"xxx_report.export"       # 匯出權限
"xxx_report.admin"        # 管理員（reparse、sync）
```

Router 中使用：
```python
_PERM = "xxx_report.view"
_     = Depends(require_permission(_PERM))
```

### 8.3 settings/menu-config — Menu Key 命名規範

```
menu_key 格式：/{前端路由路徑}
例：/purchase-report → menu_key = "/purchase-report"
    /claim-report    → menu_key = "/claim-report"
    /xxx-report      → menu_key = "/xxx-report"

parent_key：報表類模組建議掛在 "finance" 或 "report" 群組下
```

前端 `navLabels` 同步更新：
```typescript
// frontend/src/components/Layout/MainLayout.tsx（或 navLabels.ts）
"/xxx-report": "XXX月報表",
```

### 8.4 前端路由（React Router）

```typescript
// frontend/src/router/index.tsx
{
  path: "xxx-report",
  element: <XxxReport />,
}
```

---

## 9. 標準開發提示詞（Claude Code 用）

### 9.1 新模組開發（完整版）

將以下提示詞貼給 Claude Code，它會依照本 SPEC 完整開發：

```
請參照 docs/RAGIC_REPORT_MODULE_SPEC.md 開發新的 Ragic Report Module。

【模組資訊】
- 模組名稱（中文）：XXX月報表
- 模組名稱（英文/路由）：xxx-report
- API 前綴：/api/v1/xxx-report
- 前端路由：/xxx-report
- Permission Key：xxx_report.view / xxx_report.export / xxx_report.admin
- Menu Key：/xxx-report
- Menu 父節點：finance（或其他已有的父群組）

【Ragic Sheet 設定】（依部門逐一填入）
- 執董室：lequn-executive-office/X
- 財務部：lequn-finance-department/X
- ...（全部 9 個部門）

【主單欄位映射】（Ragic 欄位 → DB 欄位）
- 單號欄位候選：["編號", "XXX單號", ...]
- 申請日期：["申請日期", "填單日期"]
- 金額：["金額", "未稅金額"]
- ...

【開發 Checklist（按序執行，每步完成後標記）】
□ 1.  建立 backend/app/models/xxx_request.py（含 DISPLAY_MAP + DEPT_SHEETS）
□ 2.  建立 backend/app/services/xxx_request_sync.py
      - LIST_FIELD_CANDIDATES + _pick_request_no（含 regex fallback）
      - _parse_approved_date 三層 fallback
      - sync_list_only / sync_detail_batch / sync_all
□ 3.  建立 backend/app/routers/xxx_report.py（11 個標準端點）
□ 4.  更新 backend/app/main.py
      - import xxx_report（在 from app.routers import ... 中加入）
      - app.include_router(xxx_report.router, ...)  ← ⚠️ 千萬不能漏
      - _auto_sync 加入 sync_xxx_list
      - APScheduler 加 detail 批次排程
□ 5.  建立 frontend/src/api/xxxReport.ts
□ 6.  建立 frontend/src/pages/XxxReport/index.tsx
      - 4 TAB：主清單 / 月報明細 / 部門統計 / 資料異常
      - Drawer 680px（column={2} 結構化 Descriptions，非 detail dict）
        ⚠️ handleOpenDrawer(orderId: number)——接受純 ID，TAB-1 & TAB-2 共用
        ⚠️ TAB-2 月報明細 Table 必須加 onRow → handleOpenDrawer(r.order_id)
      - 部門統計欄位命名帶業務前綴（請購單數 / 請購未稅合計 / 請購稅額 / 請購占比）
        部門 Tag 統一用 blue（⚠️ 非 geekblue）
      - 部門統計 Admin Collapse：items API、Badge、增量/全量 Modal.confirm、Alert、dept_stats Progress、recent_logs Table
      - 日期 Segmented 三模式
      - 部門 + 篩選器 + 全文搜尋
      - Excel 匯出按鈕
□ 7.  更新 frontend/src/router/index.tsx（加路由）
□ 8.  更新前端 navLabels / MainLayout sidebar（加選單項目）
□ 9.  更新 settings/ragic-connections：為每個部門 Sheet 各加一筆記錄
□ 10. 更新 settings/roles：加 xxx_report.view / export / admin 三個 permission
□ 11. 更新 settings/menu-config：加 /xxx-report 選單項目
□ 12. 執行 DB migration（Alembic 或 Base.metadata.create_all）
□ 13. 驗證後端：curl /api/v1/xxx-report/approved/orders 確認有回傳
□ 14. 驗證前端：開啟 /xxx-report，確認 TAB 切換 / Drawer / 篩選器正常
□ 15. 執行 reparse 確認無 null request_no（POST /admin/reparse-request-no）
□ 16. 加入稽核規則（在 audit_service.py 加 _check_xxx）
□ 17. 更新 docs/CHANGELOG.md
□ 18. 更新 README.md 最後更新日期 + 最近變更

完成每個步驟後請先確認沒有 TypeScript 型別錯誤、沒有 Python import 錯誤，
再進行下一步。
```

### 9.2 快速驗證提示詞（現有模組健康檢查）

```
請參照 docs/RAGIC_REPORT_MODULE_SPEC.md 中 Section 10「Bug Graveyard」，
逐一驗證 [purchase-report / claim-report / xxx-report] 是否存在以下已知問題：

1. main.py 有 include_router 嗎？（不是只有 import）
2. sorted() 有 key=lambda x: x or "" 嗎？
3. func.sum() 比較前有 isnot(None) 過濾嗎？
4. request_no 用 _pick_request_no（含 regex fallback）嗎？
5. approved_date 有三層 fallback 且不用 last_updated_dt 嗎？
6. Excel 匯出用 RFC 5987 filename* 編碼嗎？
7. reparse 端點回傳 still_null 陣列嗎？
8. raw_data_json 有被存入 DB 嗎？

發現問題請直接修正。
```

### 9.3 多分公司複製提示詞

```
要將 [xxx-report] 模組複製給「[分公司名稱]」使用。

新分公司的 Ragic 設定：
- Server：ap16.ragic.com
- Account：new-company-account
- 各部門 Sheet 路徑：（逐一填入）

請執行：
1. 在 DEPT_SHEETS 中加入新分公司的部門設定（或建立新的設定檔）
2. 確認 DISPLAY_MAP 映射是否需要調整（部門名稱可能不同）
3. 更新 RAGIC_SERVER / RAGIC_ACCOUNT 設定（或改為從 settings 讀取）
4. 驗證 LIST_FIELD_CANDIDATES 是否適用（欄位名稱可能不同）
5. 執行 scripts/scan_claim_fields.py 確認各部門欄位名稱
```

---

## 10. 已知坑位清單（Bug Graveyard）

> 這些 bug 在 purchase-report / claim-report 開發中實際發生過，記錄於此以防重演。

| # | 症狀 | 根因 | 修正方式 |
|---|------|------|---------|
| B01 | `combined_report` / `部門統計` TAB 完全空白，無錯誤訊息 | `main.py` 只有 import `combined_report`，缺 `app.include_router(combined_report.router, ...)` | 補入 `include_router()` 呼叫 |
| B02 | 部門統計 API 500，前端靜默顯示空表 | `sorted(departments)` 遇 `None` 值拋 `TypeError: '<' not supported between NoneType and str` | 改 `sorted(departments, key=lambda x: x or "")` |
| B03 | R03 稽核誤報（請款單有品項但被標為「金額異常」） | `payable_amount=None` 被誤判，但品項有 `selected_amount` | 豁免邏輯：`detail_synced=True AND item_sum > 0` 則跳過 R03 |
| B04 | R04 稽核誤報（品項加總不符） | `func.sum()` 全 NULL → `None`，`coalesce(None,0)=0` 與 `amount=500` 比較 → 誤觸發 | `.filter(item_sum.isnot(None), ...)` 先排除未同步記錄 |
| B05 | 執董室請款單 `request_no=null` | 欄位名為「職請編號」，不在候選清單（只有「執董請編號」） | 加入「職請編號」；長期改用 `_pick_request_no` regex fallback |
| B06 | 資訊部 `request_no=null`（樂資請...） | 欄位名為未知的部門特定標籤 | `_pick_request_no` regex fallback 掃全欄位值 |
| B07 | 請款單 `approved_date` 全部等於同步日期 | 請款 Ragic 表單無工作流「日期N」欄位，舊邏輯 fallback 到 `last_updated_dt` | 三層 fallback：日期N → 核准日期/付款日期 → 申請日期（絕不用 last_updated_dt） |
| B08 | Excel 匯出 500 `UnicodeEncodeError` | `Content-Disposition` 直接拼中文，Starlette 用 Latin-1 編碼失敗 | RFC 5987 編碼：`filename*=UTF-8''{{quote(filename)}}` |
| B09 | 全文搜尋 Input 打字lag / 無法輸入 | 使用 `value` 綁定但 `onChange` 直接觸發 API call | 拆成 `searchInput`（顯示值）+ `searchKeyword`（API 觸發），Enter 才送查詢 |
| B10 | `per_page` 參數無效，後端收到舊值 | 前端 API 封裝用了 `page_size` 參數名，後端 Query 是 `per_page` | 前後端參數名必須一致，統一用 `per_page` |
| B11 | `approved_date` Ragic 連結路徑錯誤 | `_ragic_url()` 誤用 `detail_path`（API sheet）而非 `list_path`（記錄所在 sheet） | 改用 `list_path` 組合 Ragic 前台連結 |
| B12 | 頁面標題顯示「請購 + 請款整合總表」 | ClaimReport 複製自 PurchaseReport，標題邏輯未更新 | 各頁面獨立維護標題邏輯，複製後立即更新 |
| B13 | 總表 TAB 功能重複 | 總表同時在 PurchaseReport + ClaimReport 頁出現，功能重疊 | 移除兩個頁面的「總表」TAB，保留「部門統計」 |

---

## 11. 多分公司部署差異點

### 11.1 必須調整的設定

| 設定位置 | 現有值（樂群） | 新分公司調整 |
|---------|--------------|------------|
| `RAGIC_SERVER` | `ap12.ragic.com` | 新帳號的 server |
| `RAGIC_ACCOUNT` | `soutlet001` | 新帳號名稱 |
| `DEPT_SHEETS[*].list_path` | `lequn-executive-office/9` | 新分公司的 sheet 路徑 |
| `DEPT_DISPLAY_MAP` | `{"客服": "停管部"}` | 新分公司的部門映射 |
| `LIST_FIELD_CANDIDATES` | 以「樂X請」開頭的單號格式 | 若單號格式不同需調整 regex |

### 11.2 建議改進（長期）

```python
# 現況：RAGIC_SERVER / RAGIC_ACCOUNT 硬碼在 sync service
RAGIC_SERVER  = "ap12.ragic.com"   # ← 硬碼

# 建議：改從 settings 讀取，支援多分公司設定
from app.core.config import settings
RAGIC_SERVER  = settings.RAGIC_SERVER_URL
RAGIC_ACCOUNT = settings.RAGIC_ACCOUNT

# 或由 DEPT_SHEETS 逐筆帶入 server/account，實現同一 Portal 多帳號
```

### 11.3 scripts/scan_claim_fields.py

每次新增分公司或新部門，執行此腳本掃描實際欄位名稱，確認候選清單完整：

```bash
cd portal/backend
python scripts/scan_claim_fields.py          # 掃描各部門欄位
python scripts/scan_claim_fields.py --reparse  # 同時修正現有 null 記錄
```

---

*最後更新：2026-05-14（v1.61.38）*  
*維護者：依照 CHANGELOG 版號同步更新本文件*
