# 整合與同步

週採是 Portal 原生模組，但仍有三條對外連線：**供應商鏡像**、**部門鏡像**、**Ragic 拋轉（stub）**。

## 供應商鏡像：合約模組 → 週採

```{mermaid}
flowchart LR
    R[Ragic Sheet 15<br/>廠商資料表] -->|vendor_sync.py| P[(portal.db<br/>vendors 唯一主檔)]
    P -->|cycle_purchase_vendor_sync.py<br/>sync_from_contract| C[(cycle-purchase.db<br/>cycle_purchase_vendors)]
```

依 CLAUDE.md §9：**廠商資料的唯一真實來源是合約模組的 `vendors`**，
週採的 `cycle_purchase_vendors` 退化成鏡像副本。

### 比對優先序（固定三層）

| 層 | 條件 | 作用 |
|----|------|------|
| 1 | `source_vendor_id` 已連結 | 直接比對到該筆 |
| 2 | `tax_id` 非空且完全相同 | 視為同一筆，回填 `source_vendor_id` |
| 3 | `vendor_name` 完全相同 | 視為同一筆，回填 `source_vendor_id` |
| 4 | 都比對不到 | 新增，`vendor_code` 沿用合約端的 `VND-NNNN` |

第 3 層負責把週採原本手動建的資料**一次性合併**進來，不需另寫 backfill 腳本。

### 欄位權責

| 類別 | 欄位 | 規則 |
|------|------|------|
| 同步覆蓋 | `vendor_name` | 必填，無條件覆蓋 |
| 同步覆蓋 | `tax_id`、`contact_name`、`contact_phone` | **來源端有值才覆蓋** |
| 絕不碰 | `payment_terms`、`notes`、`is_active` | 週採自維護，前端仍可編輯 |

```{admonition} 為什麼「來源端有值才覆蓋」不能省
:class: danger

若無條件覆蓋，合約端沒填統編的廠商會把週採端本來手動維護的統編**洗成空**。
統編一旦被清空，下次同步的第 2 層比對也跟著失效，**錯誤會擴散**。
```

### 刻意不做的事

合約端刪除廠商時，**不會**刪除或停用週採端對應資料：
`cycle_purchase_pos.vendor_id` 是 RESTRICT，硬刪會直接失敗；
`is_active` 屬於週採自維護欄位，同步不該代為關掉。
孤兒資料只在回傳的 `orphans` 計數中呈現。

```{admonition} 順序相依
:class: warning

本模組的來源是 `portal.db vendors` 而非 Ragic，因此在
`sync_tool.py MODULES`、`main.py _auto_sync`、`RagicConnections.tsx ALL_MODULES`
三處都**必須排在「廠商資料」之後**，否則同步到的會是上一輪的舊資料。
```

## 部門鏡像：系統設定 → 週採

2026-08-17 加入，做法完全比照供應商。來源是 `reference_data.py` 的
`Company` / `RefDepartment`（「系統設定 → 公司/部門管理」頁面維護）。

| 層 | 條件 |
|----|------|
| 1 | `source_department_id` 已連結 |
| 2 | 公司 ＋ 部門名稱完全相同 → 回填 `source_department_id` |
| 3 | 都比對不到 → 新增 |

| 類別 | 欄位 |
|------|------|
| 同步覆蓋（無條件，來源 NOT NULL） | `company`（← `Company.name`）、`dept_name`（← `RefDepartment.name`） |
| 絕不碰 | `dept_code`、**`owner_user_id`**、`is_active` |

`dept_code` 沒有天然來源（`RefDepartment` 沒有代碼欄位），新增時自動帶
`DEPT-{來源RefDepartment.id}` 佔位，同步之後不再動它，使用者可自行改成有意義的代碼。

```{admonition} owner_user_id 同步不會幫你設
:class: caution

部門承辦人是週採自維護欄位。鏡像同步新增的部門，`owner_user_id` 一律是空的，
必須到「週期採購 → 部門主檔」手動指定，否則該部門的填單人動不了自己的單。
```

## 同步註冊位置

兩支鏡像同步在 `main.py` 的 `_auto_sync` 模組表中：

```python
"週期採購供應商": ("app.services.cycle_purchase_vendor_sync",    "sync_from_contract"),
"週期採購部門":   ("app.services.cycle_purchase_department_sync", "sync_from_reference"),
```

也可由前端 `/cycle-purchase/masters/vendors` 頁的「自合約模組同步」按鈕手動觸發
（`POST /api/v1/cycle-purchase/masters/vendors/sync`）。

```{admonition} 比對不到要記 warnings，不是 errors
:class: note

`main.py` 只要 `errors` 非空就把同步標成 partial（黃燈）。
來源端只要有重複統編就會**永遠黃燈**，久了沒人看。
「比對不到／略過」一律記進 `warnings`。
```

## Ragic 拋轉：目前是 stub

`cycle_purchase_ragic_push.py` 全檔是 stub。
`push_summary_document()` 只寫 log、回傳 `is_stub: True` 的模擬成功結果，**不呼叫 Ragic API**。

### 現況影響

彙整單頁的「拋轉 Ragic」按鈕會把 Portal 端的 5 個 `ragic_*` 欄位寫進去，
但那代表「**Portal 端已標記為拋轉**」，不是真的寫進 Ragic。

### 解除條件

Ragic 端建好「匯總請購單」表單，並提供：

- 新表單的 `ragic_path`
- 各欄位的 **Ragic 欄位 ID／內部代號**（API 寫入用 ID 而非顯示名稱）
- 子表（部門別＋料號明細）的巢狀資料格式
- 認證沿用現有 `RAGIC_API_KEY`

屆時只需換掉該檔的 TODO 區塊，**呼叫端介面不需變動**
（`cycle_purchase_summary_service.push_summary_to_ragic()` 不用動）。

```{admonition} 新表單為什麼要重建而不是沿用舊的請購單
:class: note

Ragic 既有的請購單是**比價式**的：有廠商(一)/(二)/(三) 三組比價欄位＋擬定廠商勾選。
週採的供應商已在料號對照表指定好、不比價，所以新表單要拿掉這三組欄位，
改成單一廠商欄位由 Portal 直接帶入。0715 會議確認。
```

### 取消拋轉

`POST /summary/cancel-ragic-push` 會清掉該範圍的拋轉標記，可重新拋轉，
也解開「退回請購單」的限制。取消與重推都會寫進稽核紀錄
（`ragic_push_cancel` / `ragic_push`），批次號從稽核紀錄取號因此不會倒退。
