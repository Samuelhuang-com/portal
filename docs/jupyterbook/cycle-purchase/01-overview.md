# 模組總覽

## 定位

| 項目 | 內容 |
|------|------|
| 路由前綴 | 前端 `/cycle-purchase/*`、後端 `/api/v1/cycle-purchase/*` |
| 資料庫 | **獨立檔案** `cycle-purchase.db`（`CYCLE_PURCHASE_DATABASE_URL`），不與 `portal.db` 共用 |
| 資料來源 | **Portal 原生填寫**。不是 Ragic 同步唯讀模組 |
| 上線狀態 | 十大流程全部已上線（料號主檔 → 週期設定 → 請購 → 彙整 → 採購 → 驗收 → 請款 → 稽核 → 4 張支援主檔 → Dashboard） |
| 站內手冊 | `/cycle-purchase/manual`（v2.1，2026-08-09） |

## 為什麼不接 Ragic

1. 週採是**多階段交易流程**，每一階段都要寫入與檢核，Ragic 唯讀同步模式做不到。
2. 兩家公司（春大直／日曜天地）的料號明細表實測比對後發現**同代碼不同貨**，必須在 Portal 端重建一套集團料號主檔。
3. 唯一會回到 Ragic 的是彙整完成後的「匯總請購單」拋轉，目前仍是 **stub**（見〈整合與同步〉）。

## 組成清單

### 後端（`backend/app/`）

::::{tab-set}

:::{tab-item} models（11 檔）
```text
cycle_purchase_vendor.py      供應商（鏡像合約模組 vendors）
cycle_purchase_reference.py   部門 / 成本中心 / 會計科目
cycle_purchase_category.py    類別主檔（大分類-中分類-細分類）
cycle_purchase_item.py        料號主檔 + 料號對照表（mapping）
cycle_purchase_cycle.py       週期設定
cycle_purchase_request.py     請購單 + 明細
cycle_purchase_summary.py     彙整單
cycle_purchase_po.py          採購單 + 明細
cycle_purchase_receiving.py   驗收單 + 明細
cycle_purchase_payment.py     請款單 + 分攤 + 涵蓋驗收單
cycle_purchase_audit.py       異常稽核紀錄（append-only）
```
:::

:::{tab-item} routers（9 檔）
```text
cycle_purchase_masters.py     /cycle-purchase/masters/*
cycle_purchase_items.py       /cycle-purchase/items*
cycle_purchase_cycles.py      /cycle-purchase/cycles*
cycle_purchase_requests.py    /cycle-purchase/requests*
cycle_purchase_summary.py     /cycle-purchase/summary*
cycle_purchase_po.py          /cycle-purchase/pos*
cycle_purchase_receiving.py   /cycle-purchase/receiving*
cycle_purchase_payment.py     /cycle-purchase/payments*
cycle_purchase_audit.py       /cycle-purchase/audit-log
```
:::

:::{tab-item} services（11 檔）
```text
cycle_purchase_service.py             主檔 / 料號 / 週期的 CRUD
cycle_purchase_request_service.py     請購單（含期別、關閉、部門解析）
cycle_purchase_summary_service.py     彙整（含轉採購、退回、Ragic 拋轉）
cycle_purchase_po_service.py          採購單狀態機、退回彙整
cycle_purchase_receiving_service.py   分批驗收、PO 狀態回算、進貨報表
cycle_purchase_payment_service.py     請款、分攤建議值計算
cycle_purchase_audit_service.py       稽核寫入 / 查詢
cycle_purchase_vendor_sync.py         供應商鏡像同步（自合約模組）
cycle_purchase_department_sync.py     部門鏡像同步（自參考資料）
cycle_purchase_ragic_push.py          Ragic 拋轉（**stub**）
cycle_purchase_account_code_seed.py   會計科目種子資料
```
:::

::::

### 前端（`frontend/src/pages/CyclePurchase/`）

```text
Dashboard.tsx                  待辦與本月概況
Items/index.tsx                料號主檔（含料號對照表）
Cycles/index.tsx               週期設定
Requests/{index,Detail}.tsx    請購單清單 / 詳情
Summary/index.tsx              彙整單
POs/{index,Detail}.tsx         採購單
Receiving/{index,Detail}.tsx   驗收單
Receiving/Report.tsx           進貨數量報表
Payment/{index,Detail}.tsx     請款單 + 費用分攤
AuditLog/index.tsx             異常稽核紀錄
Masters/{Vendors,Categories,Departments,CostCenters,AccountCodes}.tsx
Manual/{index,content}.ts(x)   站內使用手冊
components/CloseStatusTag.tsx  關閉狀態標籤（人工／系統）
```

API 封裝統一在 `frontend/src/api/cyclePurchase.ts`。

## 單號規則一覽

盤點自各 service 的 `_next_*_no()`：

| 單據 | 格式 | 流水位數 | 重置週期 | 出處 |
|------|------|---------|---------|------|
| 請購單 | `PR-YYYY-MM-NNN` | 3 | 每月 | `cycle_purchase_request_service._next_request_no` |
| 人工關閉批次 | `CPCLOSE-YYYYMM-NNN` | 3 | 每月 | `_next_close_batch_no` |
| 系統自動關閉批次 | `CPAUTO-YYYYMM` | — | 每月共用一個 | `_auto_close_batch_no` |
| 產生彙整批次 | `CPGEN-YYYYMM-{公司}-NNN` | 3 | 每月×公司 | `cycle_purchase_summary_service._next_summary_generate_batch_no` |
| Ragic 拋轉批次 | `CPSUM-YYYYMM-{公司}-NNNN` | 4 | 每月×公司 | `_next_ragic_push_batch_no` |
| 採購單 | `PO-YYYYMM-NNNN` | 4 | 每月 | `_next_po_no` |
| 驗收單 | `RC-YYYYMM-NNNN` | 4 | 每月 | `cycle_purchase_receiving_service._next_receiving_no` |
| 請款單 | `PAY-YYYYMM-NNNN` | 4 | 每月 | `cycle_purchase_payment_service._next_payment_no` |

```{admonition} 兩個容易踩到的號碼細節
:class: warning

1. **請購單號是 `PR-YYYY-MM-NNN`（中間有連字號），其他單據是 `YYYYMM`（沒有）**。這是 2026-07-17 改版留下的不一致，兩者不可互相套用。
2. **Ragic 拋轉批次號的流水來源是稽核紀錄，不是彙整表**。因為「取消拋轉」會把 `ragic_push_batch_no` 清成 NULL，若從彙整表數，重推會拿到跟上一次一模一樣的批次號（已實測重現）。稽核紀錄是 append-only，永遠不會倒退。
```

## 期別（period_label）

`period_label` 一律由系統於**建立當下**蓋章為 `YYYY-MM`（`_current_period_label()`），
**使用者不能手動輸入**。整條流程的期別都從請購單往下傳遞（彙整 → 採購共用同一個 `period_label`）。
