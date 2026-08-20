# 資料模型

全部資料表位於 `cycle-purchase.db`，共 **19 張表**。以下欄位盤點自 `backend/app/models/cycle_purchase_*.py`。

## ER 概觀

```{mermaid}
erDiagram
    CyclePurchaseItem ||--o{ CyclePurchaseItemMapping : "1:N"
    CyclePurchaseDepartment ||--o{ CyclePurchaseCostCenter : "1:N"
    CyclePurchaseCycle ||--o{ CyclePurchaseRequest : "1:N"
    CyclePurchaseRequest ||--o{ CyclePurchaseRequestItem : "1:N"
    CyclePurchaseRequestItem }o--|| CyclePurchaseItem : "料號"
    CyclePurchaseSummary }o--|| CyclePurchaseItem : "料號"
    CyclePurchaseSummary }o--o| CyclePurchasePO : "converted 後回填 po_id"
    CyclePurchasePO ||--o{ CyclePurchasePOItem : "1:N"
    CyclePurchasePOItem }o--o| CyclePurchaseSummary : "summary_id"
    CyclePurchasePO ||--o{ CyclePurchaseReceiving : "1:N（分批）"
    CyclePurchaseReceiving ||--o{ CyclePurchaseReceivingItem : "1:N"
    CyclePurchaseReceivingItem }o--|| CyclePurchasePOItem : "po_item_id"
    CyclePurchasePO ||--o{ CyclePurchasePayment : "1:N"
    CyclePurchasePayment ||--o{ CyclePurchasePaymentAllocation : "1:N"
    CyclePurchasePayment ||--o{ CyclePurchasePaymentReceiving : "涵蓋的驗收單"
    CyclePurchaseVendor ||--o{ CyclePurchasePO : "供應商"
```

## 主檔層

### `cycle_purchase_vendors` — 供應商

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | Integer PK | |
| `vendor_code` | String(30) unique | 供應商代碼 |
| `vendor_name` | String(200) | 供應商名稱 |
| `tax_id` / `contact_name` / `contact_phone` | String | 來源端欄位，同步會覆蓋 |
| `payment_terms` / `notes` / `is_active` | | **模組自己的營運欄位，同步絕不碰** |
| `source_vendor_id` | String, unique, **nullable** | 跨庫對照鍵，指向 `portal.db vendors`。**NULL ＝本地自建** |
| `synced_at` | DateTime | 最後一次自合約模組同步的時間 |

### `cycle_purchase_departments` / `cycle_purchase_cost_centers` / `cycle_purchase_account_codes`

| 表 | 關鍵欄位 |
|----|---------|
| 部門 | `company`、`dept_code`、`dept_name`、**`owner_user_id`**（判斷登入者屬於哪個部門）、`source_department_id`（unique, nullable） |
| 成本中心 | `department_id` FK、`cc_code`、`cc_name` |
| 會計科目 | `code` unique、`name`。空表時啟動自動塞 `CPAC-001`～`004` |

### `cycle_purchase_categories` — 類別主檔

三層代碼：`major_code`（1 碼，E 工程／C 清潔／G 文具／S 營業）+ `mid_code`（2 碼）+ `sub_code`（2 碼），
加上 `company` 與 `department_id`。`serial_width` 控制料號流水號寬度。

### `cycle_purchase_items` — 料號主檔

`item_code`（unique）、`item_name`、`spec`、`category`、`unit`、
`default_qty`（批次預載量）、`moq`、`max_stock` / `min_stock`（**僅供參考，不做消帳**）、
`unit_price`、`default_vendor_id`、`is_active`、`is_cycle_item`。

### `cycle_purchase_item_mappings` — 料號對照表

把集團料號對到某公司的舊料號。**決定請購單看得到哪些料號**。

| 欄位 | 說明 |
|------|------|
| `item_id` FK | 集團料號 |
| `company` + `department_id` | 篩選鍵 |
| `original_code` / `original_name` / `original_vendor_name` / `original_unit_price` | 公司原始資料，追溯用 |
| `vendor_id` | 對到週採供應商主檔 |
| `is_confirmed` | 是否已人工確認 |

唯一鍵於 2026-08-18 由啟動時 migration `_migrate_cycle_purchase_item_mapping_unique()` 重建。

### `cycle_purchase_cycles` — 週期設定

| 欄位 | 說明 |
|------|------|
| `cycle_code` unique / `cycle_name` / `frequency` | |
| `applicable_categories` | CSV，適用品類 |
| `applicable_scope` | CSV 公司別，`all` 或空＝全部 |
| `applicable_department_ids` | CSV 部門 id。**空＝適用公司下全部啟用中部門**（舊資料相容） |
| `excluded_item_ids` | CSV，手動排除的料號 |
| `auto_generate` / `reminder_rule` / `status` | |

```{admonition} 部門解析是 B ∩ D
:class: note

`resolve_applicable_departments()` 回傳 `(included, excluded)`：

- **B 層**：勾選的部門（或適用公司下全部啟用中部門），排除已停用／不屬適用公司／主檔已刪的
- **D 層**：該公司＋部門在此品類下（扣掉 `excluded_item_ids`）**有沒有啟用中料號**

`excluded` 只收「使用者可能覺得意外」的排除並附上原因；
單純因為不在適用公司範圍而落選的不列入（那是設定本來就想要的結果，列出來只會變成雜訊）。
```

## 交易層

### `cycle_purchase_requests` — 請購單

唯一鍵：週期 + 期別 + 部門（一部門一期一張，冪等）。

| 群組 | 欄位 |
|------|------|
| 識別 | `request_no`（`PR-YYYY-MM-NNN`）、`cycle_id`、`period_label`、`department_id`、`company`、`cost_center_id` |
| 金額 | `total_amount`（明細加總，系統維護） |
| 關閉 | `is_closed`、`closed_by_user_id/name`、`closed_at`、`close_batch_no`、`reopened_by_*`、`reopened_at` |
| 彙整 | `is_summarized`、`summary_batch_no`、`summarized_at`、`unsummarized_by_*`、`unsummarized_at`、`unsummarize_reason` |
| 填寫 | `submitted_by_user_id/name`、`submitted_at`（＝建立時間快照，**沿用舊欄位名**） |
| 歷史殘留 | `status`、`approved_by_*`、`approved_at`、`reject_reason` — **2026-07-17 起停止寫入** |

```{admonition} status 欄位還在，但別用它
:class: danger

`status`（`draft|submitted|approved|rejected`）是改版前的狀態機殘留。
現在請購單的狀態一律看 `is_closed` / `is_summarized`。拿 `status` 做判斷會得到錯的結果。
```

### `cycle_purchase_request_items` — 請購明細

`item_id`、`item_mapping_id`、**`account_code_id`（逐行手選）**、
料號／品名／單位／單價**快照**、`request_qty`、`subtotal`（系統維護）。

### `cycle_purchase_summary` — 彙整單

粒度：`cycle_id` + `period_label` + `company` + `item_id` + `department_id`。

| 欄位 | 說明 |
|------|------|
| `demand_qty` | 需求總量，各已關閉請購單明細加總，系統計算 |
| `adjusted_qty` | 調整量，預設＝需求總量 |
| `adjust_reason` | 調整量 ≠ 需求總量時必填 |
| `status` | `draft` \| `converted` |
| `po_id` | converted 後回填 |
| `vendor_id` | 指定供應商 |
| `ragic_push_batch_no` / `ragic_pushed` / `ragic_record_id` / `ragic_pushed_at` / `ragic_push_error` | Ragic 拋轉 5 欄 |

```{admonition} 已知：實體 UNIQUE 約束落後 ORM
:class: warning

ORM 的 `__table_args__` 已改成含 `department_id` 的五欄 UniqueConstraint，
但 SQLite 不支援直接 ALTER constraint，**實體資料表上仍是舊的四欄約束**。
功能沒壞——彙整冪等性目前靠 service 層明確查詢把關。要修需整張表重建，已決定維持現狀。
```

### `cycle_purchase_pos` / `cycle_purchase_po_items` — 採購單

`po_no`（`PO-YYYYMM-NNNN`）、`cycle_id`、`period_label`、`company`、`vendor_id`、
`buyer_user_id/name`、`expected_date`、`total_amount`、`status`。

明細帶 `summary_id`（回指彙整列）、料號快照、`ordered_qty`（＝彙整列的**調整量**）、`subtotal`。

```{admonition} po_items 的 UNIQUE(po_id, item_id) 與同料號跨部門
:class: warning

彙整列的粒度含 `department_id`，同一支料號可以同時被四個部門請購、產生四列彙整列，
但 `cycle_purchase_po_items` 上是 `UniqueConstraint("po_id", "item_id", name="uq_cp_po_item")`。
2026-08-18 之前逐列插入會撞唯一鍵 → `IntegrityError` → 500，症狀是「文具的採購單永遠轉不出來」。

現行 `convert_to_po()` 已改為**依料號合併成一行**（`ordered_qty` 加總），衝突已解除。
兩個連帶設計：

- **單價不一致直接擋下報錯**，不自行挑一個。四筆對照的單價都來自同一列 Excel，正常必然相同；
  會不同只有人工改過其中一個部門的對照單價，這時「系統默默挑一個」會產生一張金額對不起來的採購單。
- `summary_id` 是 NOT NULL 單一外鍵，合併後**只記其中一筆當代表列**。
  反向追溯完整清單靠 `summary.po_id`（退回採購單走的就是這條）。
```

### `cycle_purchase_receiving` / `_items` — 驗收單

`receiving_no`（`RC-YYYYMM-NNNN`）、`po_id`、`receiver_user_id/name`、`received_date`、`status`。

明細關鍵欄位：

| 欄位 | 說明 |
|------|------|
| `ordered_qty` | 採購明細訂購數量快照 |
| `previously_received_qty` | 前幾張驗收單已收的量 |
| `received_qty` | 本次驗收數量 |
| `is_final_for_item` | **這個料號**是否驗收完結（預設 True）。只有 True 的列在送出時才計算 `variance_qty`；分批到貨中途的列維持 NULL，不算差異 |
| `variance_qty` | 累計已收 − 訂購數量 |
| `variance_reason` | `variance_qty ≠ 0` 時必填 |

### `cycle_purchase_payments` + 兩張附表 — 請款單

| 表 | 內容 |
|----|------|
| `cycle_purchase_payments` | `payment_no`（`PAY-YYYYMM-NNNN`）、`po_id`、`invoice_no`、`invoice_date`、`invoice_amount`、`status`、`amount_diff_reason`、`processor_user_id/name` |
| `cycle_purchase_payment_receivings` | 這張請款單涵蓋哪些驗收單（多對多） |
| `cycle_purchase_payment_allocations` | 費用分攤：`company` + `department_id` + `cost_center_id` + `account_code_id`，`suggested_amount`（系統建議）／`allocated_amount`（實際）／`adjust_reason` |

### `cycle_purchase_audit_logs` — 異常稽核紀錄

**append-only，沒有 `updated_at`**。`document_type` ∈ `request|po|receiving|payment|summary`；
`event_type` 見〈流程與狀態機〉。

## 金額欄位的型別慣例

| 用途 | 型別 |
|------|------|
| 單價 | `Numeric(12, 4)` — 4 位小數 |
| 小計／分攤 | `Numeric(12, 2)` 或 `Numeric(14, 2)` |
| 單據總額 | `Numeric(14, 2)` |

所有 `total_amount` / `subtotal` 都是**系統維護**（`_recompute_total()`），不接受前端直接寫入。
