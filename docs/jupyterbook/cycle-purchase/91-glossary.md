# 名詞對照

## 畫面用詞 vs 資料庫欄位

| 畫面用詞 | 欄位／概念 | 說明 |
|---------|-----------|------|
| 期別 | `period_label` | `YYYY-MM`，建立當下由系統蓋章，使用者不能輸入 |
| 開放中 | `is_closed = False` | |
| 關閉 | `is_closed = True` | 淺粉色標籤＝系統自動關（`CPAUTO-` 前綴） |
| 已彙整 | `is_summarized = True` | |
| 需求總量 | `demand_qty` | 各已關閉請購單明細加總，系統算 |
| 調整量 | `adjusted_qty` | 採購可改，**轉採購單取的是這個** |
| 是否到此為止 | `is_final_for_item` | 驗收明細；不勾＝後面還有批次 |
| 差異數量 | `variance_qty` | 累計已收 − 訂購數量 |
| 建議分攤金額 | `suggested_amount` | 系統試算 |
| 實際分攤金額 | `allocated_amount` | 財務覆寫，與建議不同時需填原因 |
| 承辦人 | `owner_user_id` | 部門主檔；判斷登入者屬於哪個週採部門 |
| 來源／本地自建 | `source_vendor_id` / `source_department_id` | NULL ＝本地自建，同步不覆蓋也不刪除 |

## 單號前綴

| 前綴 | 意義 |
|------|------|
| `PR-` | 請購單 |
| `CPCLOSE-` | 人工關閉批次 |
| `CPAUTO-` | 系統自動關閉批次 |
| `CPGEN-` | 產生彙整批次 |
| `CPSUM-` | Ragic 拋轉批次 |
| `PO-` | 採購單 |
| `RC-` | 驗收單 |
| `PAY-` | 請款單 |
| `VND-` | 合約模組廠商代碼（供應商鏡像沿用） |
| `CPAC-` | 會計科目預設種子（001～004） |
| `DEPT-` | 部門鏡像同步的佔位代碼 |

## 縮寫

| 縮寫 | 全稱 |
|------|------|
| PR | Purchase Request，請購單 |
| PO | Purchase Order，採購單 |
| RC | Receiving，驗收單 |
| MOQ | Minimum Order Quantity，最小訂購量 |
| CP | Cycle Purchase，週期採購 |

## 相關文件

| 文件 | 內容 |
|------|------|
| `CLAUDE.md` §8 | `StandardRangePicker` 日期區間選擇器規範 |
| `CLAUDE.md` §9 | 廠商資料單一真實來源 |
| `CLAUDE.md` §11 | 權限模型與防提權 |
| `docs/CYCLE_PURCHASE_TODO.md` | 待辦清單（本書附錄同源） |
| `docs/SPEC_cycle_purchase_dept_scope.md` | 週期設定部門範圍規格 |
| `docs/MEETING_20260812_cycle_purchase_company_split.md` | 公司別拆分會議記錄 |
| `frontend/src/pages/CyclePurchase/Manual/content.ts` | 站內使用手冊原始內容 |
| `ragic-cycle-purchase/docs/欄位規格.md` | 欄位規格 v2.3 |
