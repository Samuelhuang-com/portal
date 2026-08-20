# API 端點

全部端點共 **83 支**，掛在 `backend/app/main.py` 的 9 個 `include_router()` 之下，
tag 統一為「週期採購」。`API_PREFIX = /api/v1`。

## 路由前綴

| Router | 前綴 |
|--------|------|
| `cycle_purchase_masters` | `/api/v1/cycle-purchase/masters` |
| 其餘 8 個 | `/api/v1/cycle-purchase` |

## 共通約定

- **Session**：`Depends(get_cycle_purchase_db)`；需要查主庫（權限、使用者姓名）時另注入 `Depends(get_db)` 為 `portal_db`
- **錯誤轉譯**：多數 router 有共用的 `_handle(fn, *args, **kwargs)`，把 service 丟出的 `ValueError` 轉成 HTTP 422
- **權限**：`Depends(require_permission("key"))` 或 `Depends(require_any_permission("a", "b"))`
- **列表查詢參數**：常見 `cycle_id` / `period_label` / `company` / `status`（alias，程式內是 `status_`）

## 端點總表

### 主檔（供應商／部門／成本中心／會計科目／類別）

`cycle_purchase_masters.py` — 前綴 `/api/v1/cycle-purchase/masters`

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| GET | `/vendors` | `cycle_purchase_view` | 供應商主檔清單 |
| POST | `/vendors` | `cycle_purchase_admin` | 新增供應商 |
| POST | `/vendors/sync` | `cycle_purchase_admin` | 自合約模組同步供應商主檔 |
| PUT | `/vendors/{vendor_id}` | `cycle_purchase_admin` | 更新供應商 |
| GET | `/departments` | `cycle_purchase_view` | 部門主檔清單 |
| POST | `/departments` | `cycle_purchase_admin` | 新增部門 |
| PUT | `/departments/{dept_id}` | `cycle_purchase_admin` | 更新部門 |
| GET | `/cost-centers` | `cycle_purchase_view` | 成本中心主檔清單 |
| POST | `/cost-centers` | `cycle_purchase_admin` | 新增成本中心 |
| PUT | `/cost-centers/{cc_id}` | `cycle_purchase_admin` | 更新成本中心 |
| GET | `/account-codes` | `cycle_purchase_view` | 會計科目主檔清單 |
| POST | `/account-codes` | `cycle_purchase_admin` | 新增會計科目 |
| PUT | `/account-codes/{ac_id}` | `cycle_purchase_admin` | 更新會計科目 |
| GET | `/categories` | `cycle_purchase_view` | 類別主檔清單 |
| POST | `/categories` | `cycle_purchase_admin` | 新增類別 |
| GET | `/categories/{category_id}/next-code` | `cycle_purchase_view` | 取這個類別下一個可用料號 |
| PUT | `/categories/{category_id}` | `cycle_purchase_admin` | 更新類別 |

### 料號主檔與料號對照表

`cycle_purchase_items.py` — 前綴 `/api/v1/cycle-purchase`

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| GET | `/items` | `cycle_purchase_view` | 週期採購料號清單 |
| GET | `/items/{item_id}` | `cycle_purchase_view` | 料號詳情（含料號對照表） |
| POST | `/items` | `cycle_purchase_admin` | 新增料號 |
| PUT | `/items/{item_id}` | `cycle_purchase_admin` | 更新料號 |
| GET | `/items/{item_id}/mappings` | `cycle_purchase_view` | 料號對照清單 |
| POST | `/items/{item_id}/mappings` | `cycle_purchase_admin` | 新增料號對照 |
| PUT | `/items/{item_id}/mappings/{mapping_id}` | `cycle_purchase_admin` | 更新料號對照 |
| DELETE | `/items/{item_id}/mappings/{mapping_id}` | `cycle_purchase_admin` | 刪除料號對照 |

### 週期設定

`cycle_purchase_cycles.py` — 前綴 `/api/v1/cycle-purchase`

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| GET | `/cycles` | `cycle_purchase_view` | 週期採購週期設定清單 |
| GET | `/cycles/options` | `cycle_purchase_view` | 週期設定表單下拉選項 |
| GET | `/cycles/exclude-item-candidates` | `cycle_purchase_view` | 「排除料號」下拉候選清單：依目前選的適用公司＋適用品類現算 |
| GET | `/cycles/{cycle_id}` | `cycle_purchase_view` | 週期設定詳情 |
| POST | `/cycles` | `cycle_purchase_admin` | 新增週期設定 |
| POST | `/cycles/{cycle_id}/preview-orphan-requests` | `cycle_purchase_admin` | 預覽：套用這份設定後，會刪掉哪幾張孤兒空白請購單 |
| PUT | `/cycles/{cycle_id}` | `cycle_purchase_admin` | 更新週期設定 |

### 請購單

`cycle_purchase_requests.py` — 前綴 `/api/v1/cycle-purchase`

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| GET | `/requests` | `cycle_purchase_view` 或 `cycle_purchase_request` | 週期採購請購單清單 |
| GET | `/requests/todos` | `cycle_purchase_view` 或 `cycle_purchase_request` | Dashboard 待辦提醒 |
| GET | `/requests/open-for-close` | `cycle_purchase_close` | 列出某週期（可選：公司／月份）目前開放中的請購單，供勾選關閉 |
| GET | `/requests/generate-preview` | `cycle_purchase_buyer` | 產生前預覽：這個週期會產生哪些部門的單、哪些不會與原因 |
| GET | `/requests/copy-candidates` | `cycle_purchase_buyer` | 複製上期請購單：列出同週期＋同部門過去有填過品項的請購單供選擇 |
| GET | `/requests/{request_id}` | `cycle_purchase_view` 或 `cycle_purchase_request` | 請購單詳情（含明細） |
| POST | `/requests/generate` | `cycle_purchase_buyer` | 產生本期請購單（一次幫所有適用部門建空白單，隨時可觸發、冪等） |
| POST | `/requests` | `cycle_purchase_buyer` | 手動新增單一部門的請購單 |
| POST | `/requests/{source_request_id}/copy` | `cycle_purchase_buyer` | 複製上期請購單：以某張過去的單為範本建立新單 |
| PUT | `/requests/{request_id}` | `cycle_purchase_request` | 更新請購單 |
| DELETE | `/requests/{request_id}` | `cycle_purchase_request` | 刪除請購單（僅限明細 0 筆＋未關閉＋未彙整的空白單） |
| GET | `/requests/{request_id}/available-items` | `cycle_purchase_request` | 可選料號清單（依請購單所屬公司過濾） |
| POST | `/requests/{request_id}/items` | `cycle_purchase_request` | 新增請購明細 |
| PUT | `/requests/{request_id}/items/{item_row_id}` | `cycle_purchase_request` | 更新請購明細 |
| DELETE | `/requests/{request_id}/items/{item_row_id}` | `cycle_purchase_request` | 刪除請購明細 |
| POST | `/requests/close` | `cycle_purchase_close` | 關閉勾選的請購單 |
| POST | `/requests/close-all` | `cycle_purchase_close` | 全部關閉 |
| POST | `/requests/reopen` | `cycle_purchase_close` | 重新開啟已關閉的請購單 |

### 彙整單

`cycle_purchase_summary.py` — 前綴 `/api/v1/cycle-purchase`

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| GET | `/summary` | `cycle_purchase_view` 或 `cycle_purchase_buyer` | 週期採購彙整單清單 |
| GET | `/summary/department-breakdown` | `cycle_purchase_view` 或 `cycle_purchase_buyer` | 匯總請購單畫面用：依料號分組展開部門別＋小計 |
| GET | `/summary/vendor-groups` | `cycle_purchase_buyer` | 轉採購單畫面用：依公司＋供應商分組統計（僅草稿） |
| GET | `/summary/eligible-requests` | `cycle_purchase_buyer` | 列出某週期＋公司＋期別下，已關閉且尚未被彙整過的請購單（供勾選產生彙整） |
| POST | `/summary/generate-from-requests` | `cycle_purchase_buyer` | 把勾選的請購單彙整成彙整列（period_label 由系統從請購單本身的 period_label 讀出來） |
| GET | `/summary/summarized-requests` | `cycle_purchase_buyer` | 列出某週期＋公司＋期別下已彙整的請購單（供退回勾選；退不了的會附 block_reason） |
| POST | `/summary/unsummarize-request` | `cycle_purchase_buyer` | 退回請購單（把單一一張已彙整的請購單改回未彙整，並重算受影響的草稿彙整列） |
| PUT | `/summary/{summary_id}` | `cycle_purchase_buyer` | 調整彙整列的調整量／調整原因 |
| POST | `/summary/convert-to-po` | `cycle_purchase_buyer` | 轉採購單（同一週期＋期別＋公司＋供應商的草稿彙整列合成一張採購單） |
| POST | `/summary/push-to-ragic` | `cycle_purchase_buyer` | 拋轉到 Ragic「匯總請購單」（目前為 stub，Ragic 端表單尚未建立，見 cycle_purchase_ragic_push.py） |
| POST | `/summary/cancel-ragic-push` | `cycle_purchase_buyer` | 取消拋轉（清掉該範圍的 Ragic 拋轉標記，可重新拋轉，也解開退回請購單的限制） |

### 採購單

`cycle_purchase_po.py` — 前綴 `/api/v1/cycle-purchase`

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| GET | `/pos` | `cycle_purchase_view` 或 `cycle_purchase_buyer` | 週期採購採購單清單 |
| GET | `/pos/{po_id}` | `cycle_purchase_view` 或 `cycle_purchase_buyer` | 採購單詳情（含明細） |
| PUT | `/pos/{po_id}` | `cycle_purchase_buyer` | 更新採購單（預計到貨日／備註） |
| POST | `/pos/{po_id}/status` | `cycle_purchase_buyer` | 變更採購單狀態（issued／cancelled） |
| POST | `/pos/{po_id}/revert-to-summary` | `cycle_purchase_buyer` | 退回彙整單（採購單作廢，對應的彙整列解鎖回草稿讓買家重新調整後再轉單） |

### 驗收單與進貨報表

`cycle_purchase_receiving.py` — 前綴 `/api/v1/cycle-purchase`

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| GET | `/receiving` | `cycle_purchase_view` 或 `cycle_purchase_receive` | 週期採購驗收單清單 |
| GET | `/receiving/report` | `cycle_purchase_report` | 進貨數量報表（依月份＋公司＋供應商＋料號彙總，僅計已送出驗收單） |
| GET | `/receiving/{receiving_id}` | `cycle_purchase_view` 或 `cycle_purchase_receive` | 驗收單詳情（含明細） |
| POST | `/receiving` | `cycle_purchase_receive` | 新增驗收單（草稿） |
| GET | `/receiving/{receiving_id}/receivable-items` | `cycle_purchase_receive` | 這張驗收單所屬採購單的可驗收明細（含累計已驗收量／剩餘量） |
| POST | `/receiving/{receiving_id}/items` | `cycle_purchase_receive` | 新增／更新一筆驗收明細（upsert，僅草稿可編輯） |
| DELETE | `/receiving/{receiving_id}/items/{receiving_item_id}` | `cycle_purchase_receive` | 刪除一筆驗收明細 |
| POST | `/receiving/{receiving_id}/submit` | `cycle_purchase_receive` | 送出驗收單（自動判定 completed／discrepancy，並重算採購單狀態） |

### 請款單與費用分攤

`cycle_purchase_payment.py` — 前綴 `/api/v1/cycle-purchase`

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| GET | `/payments` | `cycle_purchase_view` 或 `cycle_purchase_finance` | 週期採購請款單清單 |
| GET | `/payments/payable-receivings` | `cycle_purchase_finance` | 建立請款單畫面用：這張採購單底下還沒被涵蓋的已送出驗收單 |
| GET | `/payments/{payment_id}` | `cycle_purchase_view` 或 `cycle_purchase_finance` | 請款單詳情（含分攤明細／涵蓋的驗收單） |
| POST | `/payments` | `cycle_purchase_finance` | 新增請款單（草稿，自動試算費用分攤明細） |
| PUT | `/payments/{payment_id}` | `cycle_purchase_finance` | 更新發票資訊／備註（僅草稿可編輯） |
| PUT | `/payments/{payment_id}/allocations/{allocation_id}` | `cycle_purchase_finance` | 調整一筆分攤明細（僅草稿可編輯，金額與試算值不同時需填原因） |
| POST | `/payments/{payment_id}/submit` | `cycle_purchase_finance` | 送出請款單（檢查分攤總額 vs 發票金額，不符需已填差異原因） |
| POST | `/payments/{payment_id}/status` | `cycle_purchase_finance` | 變更請款單狀態（submitted -> paying -> paid，只能依序推進） |

### 異常稽核紀錄

`cycle_purchase_audit.py` — 前綴 `/api/v1/cycle-purchase`

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| GET | `/audit-log` | `cycle_purchase_admin` | 週期採購異常稽核紀錄清單 |

## 幾支要特別留意的端點

```{admonition} GET /requests 的可見範圍是動態的
:class: important

`_can_see_closed()` 會查登入者的權限：持有 `*`、`cycle_purchase_close` 或 `cycle_purchase_view`
才看得到**已關閉**（含系統自動關閉）的請購單。
只勾 `cycle_purchase_request` 的填單人，清單裡只有「開放中」的單。

這是刻意的：能關閉／重新開啟的人才看得到關閉後的結果，語意最一致。
```

```{admonition} POST /requests/generate 是冪等的
:class: note

「同一個週期＋期別＋部門只能有一張請購單」由唯一鍵保證，重複觸發不會產生第二張。
搭配 `GET /requests/generate-preview` 可先看會產生哪些部門、哪些不會與**原因**。
```

```{admonition} POST /summary/push-to-ragic 目前是 stub
:class: warning

`cycle_purchase_ragic_push.push_summary_document()` 全檔是 stub，只寫 log 並回傳
`is_stub: True` 的模擬成功結果，**不會真的呼叫 Ragic API**。
端點會把 Portal 端的 5 個 `ragic_*` 欄位寫進去，那代表「Portal 端已標記為拋轉」，不是真的寫進 Ragic。
```

```{admonition} POST /pos/{po_id}/status 與 revert-to-summary 語意不同
:class: danger

- `status` → `cancelled`：本期不買了，彙整列**維持鎖定**
- `revert-to-summary`：採購單作廢，彙整列**解鎖回 draft**

用錯會卡住流程，且事後只能再開一次。
```

## 尚未提供的端點

| 需求 | 現況 |
|------|------|
| Excel 匯入／匯出 | router 內**零個端點**。只有根目錄的一次性腳本 `import_cycle_purchase_item_master.py` |
| 通知／催辦 | backend 零通知程式碼 |
| 供應商歷史比價 | 未導入 |
