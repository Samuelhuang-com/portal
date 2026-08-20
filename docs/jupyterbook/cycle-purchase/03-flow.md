# 流程與狀態機

## 六階段全貌

| 階段 | 誰做 | 產出 | 需要的權限 |
|------|------|------|-----------|
| 請購 | 各部門承辦人 | 請購單（一部門一個月一張） | `cycle_purchase_request` |
| 關閉 | 採購／管理員，**或期別過了系統自動關** | 把該月的單鎖定 | `cycle_purchase_close` |
| 彙整 | 採購 | 彙整單（公司＋料號＋部門） | `cycle_purchase_buyer` |
| 採購 | 採購 | 採購單（一供應商一張） | `cycle_purchase_buyer` |
| 驗收 | 收貨單位 | 驗收單（可分批） | `cycle_purchase_receive` |
| 請款 | 財務 | 請款單＋費用分攤明細 | `cycle_purchase_finance` |

每個階段都只能從上一階段的資料往下長：沒關閉的請購單彙整不到、沒有彙整單就開不了採購單、
沒有採購單就沒得驗收。卡住的時候，往回看一階通常就找得到原因。

## 各單據的狀態

### 請購單

2026-07-17 起**已無簽核流程**。舊的 `status` 欄位（`draft|submitted|approved|rejected`）
仍在表上但已停止使用，實際判斷改看兩組布林旗標：

```{mermaid}
stateDiagram-v2
    [*] --> 開放中
    開放中 --> 已關閉 : 人工關閉（CPCLOSE-）<br/>或系統自動關閉（CPAUTO-）
    已關閉 --> 開放中 : 重新開啟
    已關閉 --> 已彙整 : 產生彙整（is_summarized=True）
    已彙整 --> 已關閉 : 退回請購單（unsummarize）
```

| 旗標組 | 欄位 |
|--------|------|
| 關閉 | `is_closed` / `closed_by_*` / `closed_at` / `close_batch_no` / `reopened_by_*` / `reopened_at` |
| 彙整 | `is_summarized` / `summary_batch_no` / `summarized_at` / `unsummarized_by_*` / `unsummarize_reason` |

**人工關 vs 系統關**由 `close_batch_no` 的前綴分辨（`close_kind_of()`）：
`CPAUTO-` 開頭是系統關的，其他是人工關的。這是**衍生值，不落地成欄位**。

### 彙整單

`draft` → `converted`（轉成採購單後鎖定，`po_id` 指回採購單）。

### 採購單

```{mermaid}
stateDiagram-v2
    [*] --> draft
    draft --> issued : 發出
    issued --> partial_received : 部分驗收
    partial_received --> received : 全數驗收完成
    draft --> cancelled : 取消
    issued --> cancelled : 取消
    issued --> [*] : 退回彙整單（作廢，彙整列解鎖回 draft）
```

`partial_received` / `received` **不是人工設定的**，由
`cycle_purchase_receiving_service._recompute_po_status()` 依驗收累計量回算。

### 驗收單

`draft` → `completed`（數量相符）或 `discrepancy`（有差異）。狀態由系統依 `variance_qty` 判定。

### 請款單

`draft` → `submitted` → `paying` → `paid`。

## 往回退：三個退回動作

整條流程一階一階往下長，但**每一階都退得回去**。做錯不用改資料庫，也不要另開一張單沖銷。

| 現在卡在哪 | 動作 | 在哪一頁 | 結果 |
|-----------|------|---------|------|
| **採購單**開錯了 | 退回彙整單 | 採購單詳情頁 | 採購單作廢，彙整列**解鎖回 draft**，改完可再轉一張新單 |
| **彙整單**不該收這張請購單 | 退回請購單 | 彙整單頁右上角 | 該請購單回到「已關閉、未彙整」，彙整列的量**重新計算** |
| **請購單**內容要改 | 重新開啟 | 請購單清單 | 回到可編輯。改完**要再關閉一次**才彙整得到 |

要退好幾階就一階一階往回退：**採購單 → 彙整單 → 請購單**。

```{admonition} 退回的共同擋點：下一階已經動了就退不了
:class: caution

- 採購單**有驗收單**就不能退。
- 彙整列**已轉採購單**，要先退採購單才能退請購單（`_unsummarize_block_reason()`）。

這不是系統小氣，而是再往下就牽涉實際收貨與付款，硬退會讓帳對不起來。
退不了時，畫面會直接在那一列寫出原因（例如「不能退回：已轉採購單（PO-202608-0001）」）。
```

```{admonition} 「取消」不等於「退回彙整單」
:class: danger

- **取消**（`set_po_status` → `cancelled`）＝這批本期不買了，彙整列**維持鎖定**。
- **退回彙整單**（`revert_po_to_summary`）＝彙整列解鎖回 `draft`，可調整後重轉。

想重新調整再採購卻按了「取消」，會直接卡住。
```

每一種退回都**要求填原因**，並寫進異常稽核紀錄。

## 退回時金額怎麼算

退回請購單時，彙整列採用**重算**而非扣減：
把該彙整列剩餘的請購明細重新加總，而不是拿原值去減。
理由是扣減會在多次退回／重彙整後累積誤差，重算則永遠等於當下事實。

## 費用分攤

請款單掛的是**採購單**，不是驗收單。
`_compute_suggested_allocation()` 依採購單明細往回追到彙整列的 `department_id`／`cost_center_id`／
`account_code_id`，算出各部門的**建議分攤金額**（`suggested_amount`）；
財務可覆寫成**實際分攤金額**（`allocated_amount`），與建議值不同時必須填 `adjust_reason`。

```{mermaid}
flowchart LR
    PO[採購單明細] --> SUM[彙整列<br/>department_id / cost_center_id]
    SUM --> SUG[suggested_amount<br/>系統建議]
    INV[發票金額] --> SUG
    SUG --> ALLOC[allocated_amount<br/>財務實際分攤]
    ALLOC -.->|不同時必填| RSN[adjust_reason]
```

## 異常稽核紀錄

`cycle_purchase_audit_logs` 是 **append-only**（沒有 `updated_at`，紀錄本身不可修改）。

| `event_type` | 觸發點 | 狀態 |
|-------------|--------|------|
| `receiving_variance` | 驗收數量有差異 | ✅ 有觸發 |
| `payment_variance` | 請款金額有差異 | ✅ 有觸發 |
| `unsummarize` | 退回請購單 | ✅ 有觸發 |
| `revert_to_summary` | 採購單退回彙整單 | ✅ 有觸發 |
| `ragic_push` | 拋轉 Ragic | ✅ 有觸發 |
| `ragic_push_cancel` | 取消拋轉 | ✅ 有觸發 |
| `backfill` / `overdue` / `shortage` / `substitute` | — | ❌ **欄位有保留，但目前無任何觸發點**，篩選選單選了永遠是空的 |

```{admonition} document_type='summary' 的例外
:class: warning

拋轉是對「一整個週期＋期別＋公司範圍」的批次動作，沒有單一主鍵。
此時 `document_id` 放的是 `cycle_id`，**真正的識別是 `document_no`（`CPSUM-...` 批次號）**。
```
