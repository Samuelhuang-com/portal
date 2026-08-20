# 待辦與已知缺口

同步自 `docs/CYCLE_PURCHASE_TODO.md`，並依 2026-08-20 的程式碼補上幾項後續發現。

```{admonition} 現況總結
:class: important

週採**十大流程全部已上線**。正式區 DB migration 已於 2026-08-07 執行並驗證通過
（`verify_cycle_purchase_migration.py` 回報欄位齊全、舊資料轉換完成），不再是阻塞點。
```

## 🔴 A. 卡在外部條件，不是程式問題

### A-1. Ragic「匯總請購單」新表單尚未建立

| 項目 | 內容 |
|------|------|
| 現況 | `cycle_purchase_ragic_push.py` 全檔是 stub |
| 行為 | `push_summary_document()` 只寫 log、回傳 `is_stub: True`，**不呼叫 Ragic API** |
| 影響 | 「拋轉 Ragic」按鈕寫入的 5 個 `ragic_*` 欄位代表「Portal 端已標記」，不是真的寫進 Ragic |
| 解除條件 | Ragic 端建好表單，取得 `ragic_path` 與各欄位代號 |
| 屆時要改 | 只需換掉該檔的 TODO 區塊，**呼叫端介面不變** |

## 🟡 B. 功能面未開始

### B-1. 通知整合（Email／逾期催辦）

backend **零通知程式碼**。目前替代方案是 Dashboard 的「我的待辦」／「本月待關閉」卡片，
屬於被動提醒——使用者不登入就不會知道。

連帶影響：稽核紀錄的 `backfill` / `overdue` / `shortage` / `substitute` 四種事件類型
**欄位有保留但無任何觸發點**，篩選選單選了永遠是空的。

建議至少先做「本月還沒關閉的請購單」逾期催辦，因為它會卡住後面整條流程。

### B-2. Excel 匯入／匯出 API

router 內**零個端點**；只有根目錄的一次性腳本 `import_cycle_purchase_item_master.py`。

規劃文件把它列為**剛性需求**：料號主檔批次匯入、請款分攤明細匯出，
兩家公司起始資料共 466 筆需要清理。匯入對象是 Portal 資料庫，不是 Ragic 表單。

### B-3. 供應商歷史比價輔助

未導入。同一料號若有多個供應商報價紀錄，做簡易歷史比價表輔助「彙整轉採購」決策。
優先度低，非流程必要。

## 🟢 C. 資料完整性（已標示、無法還原）

### C-1. `CHANGELOG.md` 與 `README.md` 的歷史紀錄遺失

`CHANGELOG` 斷在 `[1.13.0]` 的 Phase 1 中途。v1.15.0～v1.13.0 共 9 筆已依殘存內容反推重建，
**v1.12.x 以前的紀錄仍待處理**。兩檔都不在版控中（`.gitignore` 第 42 行忽略 `*.md`），
專案內也無備份。

唯一還原途徑是 OneDrive 網頁版的「版本歷程」，需手動翻找。**若要做，越早越好**——版本歷程有保留期限。

## ⚪ D. 已提出、等裁決（非缺陷）

### D-1. `cycle_purchase_summary` 的實體 UNIQUE 約束落後 ORM

ORM 已改成含 `department_id` 的五欄 UniqueConstraint，
但 SQLite 不支援直接 ALTER constraint，實體資料表上仍是舊的四欄約束。
**功能沒壞**——彙整冪等性靠 service 層明確查詢把關。
要修需整張表重建（建新表 → 搬資料 → 換名），有停機與資料風險。
建議維持現狀，除非日後發生實際的重複列問題。

### D-2. `Receiving/Detail.tsx` 有兩個未使用的 import

`useMemo`（第 20 行）與型別 `CpReceivingItem`（第 29 行）宣告了但沒用到。
**不影響執行**（Vite 建置不會因此失敗）。依 CLAUDE.md §4「不要順手優化相鄰程式碼」，只提出未修改。
併到下次真的要動這個檔案時一起做。

### D-3. 歷史彙整列的 `department_id` 為 NULL

2026-07-16 之前產生的彙整列沒有部門別（當時粒度是「公司＋料號」）。
已確認**不回填**，NULL 即代表「未拆分部門」。

## 🔵 E. 本次盤點補充

### E-1.（已解除）`convert_to_po` 與 `po_items` UniqueConstraint

原列為未修項目，本次盤點確認**已於 2026-08-18 修正**：
`convert_to_po()` 改為依料號合併成一行後不再撞 `uq_cp_po_item`。詳見〈資料模型〉。
此處保留紀錄，是因為改動採購單轉出邏輯時仍需知道這個約束的存在。

### E-2. 請購單號格式與其他單據不一致

請購單是 `PR-YYYY-MM-NNN`（中間有連字號、3 位流水），
其餘單據是 `XX-YYYYMM-NNNN`（無連字號、4 位）。
這是 2026-07-17 改版留下的不一致，**寫共用的單號解析函式時會踩到**。

### E-3. 請購單 `status` 欄位仍在表上但已停用

`status`、`approved_by_*`、`approved_at`、`reject_reason` 四組欄位 2026-07-17 起停止寫入。
新進開發者拿 `status` 做判斷會得到錯的結果，
但依 CLAUDE.md §5「不可移除現有資料表欄位」不做清除。
