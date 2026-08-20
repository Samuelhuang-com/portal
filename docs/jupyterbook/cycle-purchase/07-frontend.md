# 前端

## 路由與選單

選單定義在 `frontend/src/components/Layout/MainLayout.tsx`（2026-07-10 新增的獨立區塊），
顯示名稱來自 `navLabels.ts` 的 `NAV_PAGE.*`。

| 路徑 | 頁面 | 選單權限 |
|------|------|---------|
| `/cycle-purchase/dashboard` | Dashboard | `cycle_purchase_view` |
| `/cycle-purchase/items` | 料號主檔 | `cycle_purchase_view` |
| `/cycle-purchase/cycles` | 週期設定 | `cycle_purchase_admin` |
| `/cycle-purchase/requests` | 請購單 | `cycle_purchase_view` **或** `cycle_purchase_request` |
| `/cycle-purchase/summary` | 彙整單 | `cycle_purchase_view` **或** `cycle_purchase_buyer` |
| `/cycle-purchase/pos` | 採購單 | `cycle_purchase_view` **或** `cycle_purchase_buyer` |
| `/cycle-purchase/receiving` | 驗收單 | `cycle_purchase_view` **或** `cycle_purchase_receive` |
| `/cycle-purchase/receiving-report` | 進貨數量報表 | `cycle_purchase_report` |
| `/cycle-purchase/payments` | 請款單 | `cycle_purchase_view` **或** `cycle_purchase_finance` |
| `/cycle-purchase/audit-log` | 異常稽核紀錄 | `cycle_purchase_admin` |
| `/cycle-purchase/masters/vendors` | 供應商主檔 | `cycle_purchase_admin` |
| `/cycle-purchase/masters/categories` | 類別主檔 | `cycle_purchase_admin` |
| `/cycle-purchase/masters/departments` | 部門主檔 | `cycle_purchase_admin` |
| `/cycle-purchase/masters/cost-centers` | 成本中心主檔 | `cycle_purchase_admin` |
| `/cycle-purchase/masters/account-codes` | 會計科目主檔 | `cycle_purchase_admin` |
| `/cycle-purchase/manual` | 使用手冊 | 8 個週採 key 任一 |

```{admonition} permissionKey vs permissionKeys
:class: important

`MainLayout` 支援兩種寫法：單一 `permissionKey`，或 OR 語意的 `permissionKeys: [...]`。

2026-08-07 修正過一個實際踩到的坑：驗收單原本寫死 `cycle_purchase_view`，
但驗收人員實際持有的是 `cycle_purchase_receive`——**權限開了卻進不去**。
新增路由時務必確認選單條件與後端 `require_any_permission` 一致。
```

週採父選單本身的展開條件是 8 個 key 的 OR，
這樣只勾 `cycle_purchase_request` 的一般填單人也能展開，不必額外開放範圍更大的 `cycle_purchase_view`。

## API 封裝

統一在 `frontend/src/api/cyclePurchase.ts`，元件內**不直接用 axios**（CLAUDE.md §6）。

## 頁面實作要點

### 請購單詳情 `Requests/Detail.tsx`

**改一格存一格的即時儲存**，沒有「儲存」按鈕。每改一次數量或會計科目立刻打 API。
標題旁顯示「儲存中…／已自動儲存 HH:mm」。

三組明細工具可疊加：

| 工具 | 行為 |
|------|------|
| 全部／只看已填 | 切到「只看已填」會自動全部展開 |
| 全部展開／全部收合 | — |
| 搜尋框 | 搜尋時自動展開有結果的類別 |

副作用：在「只看已填」下把數量改成 0，該列會**立刻消失**（不再符合篩選條件）。

### 彙整單 `Summary/index.tsx`

「產生彙整」Modal 會同時列出**未關閉**的請購單（勾不動，附「關閉並納入」按鈕，
需 `cycle_purchase_close`，沒有時顯示「需關閉權限」）。刻意不藏資料，避免使用者誤以為系統漏抓。

「退回請購單」清單會把退不了的單一併列出並附 `block_reason`（例如「已轉採購單（PO-202608-0001）」）。

### 進貨數量報表 `Receiving/Report.tsx`

使用共用元件 `StandardRangePicker`（CLAUDE.md §8），
`anchor` 傳入**最後一張驗收單的驗收日期**，不是 `dayjs()`。
下拉選單底部會標明基準日。

### 關閉狀態標籤 `components/CloseStatusTag.tsx`

依 `close_batch_no` 前綴區分人工關閉與系統自動關閉（淺粉色）。

## 明細 Drawer 規範

週採的採購單／驗收單／請款單採**獨立詳情頁**（`Detail.tsx`）而非 Drawer，
因為它們是可編輯的多階段單據，不是唯讀明細。
CLAUDE.md §7 的 Drawer 強制規範適用於「Ragic 同步模組的唯讀列表」，週採不在其列。

## 元件庫

Ant Design 5（全站固定）。圖表用 recharts。
