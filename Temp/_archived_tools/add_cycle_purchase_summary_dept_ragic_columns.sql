-- 2026-07-16：週期採購「匯總請購單」改版
-- 為 cycle_purchase_summary 補上 department_id（彙整粒度改為 公司+料號+部門）
-- 與 Ragic 拋轉追蹤欄位（ragic_push_batch_no / ragic_pushed / ragic_record_id /
-- ragic_pushed_at / ragic_push_error）。詳見 backend/app/models/cycle_purchase_summary.py
-- 開頭說明、docs/週期採購_Portal規劃評估_v1.1.md v1.2 追加章節。
--
-- 執行對象：cycle-purchase.db（獨立資料庫，與 portal.db 分開，見
-- backend/app/core/cycle_purchase_database.py），不是 portal.db。
-- SQLAlchemy 的 create_all() 不會幫已存在的資料表補欄位，需要手動執行本檔案
-- （或用等效的 DB 工具）。
--
-- 冪等性：SQLite 的 ALTER TABLE ADD COLUMN 若欄位已存在會報錯而非略過，
-- 重複執行前請先確認欄位是否已加過（例如用 PRAGMA table_info(cycle_purchase_summary);）。
--
-- ⚠️ 已知限制（不影響功能正確性，只是 DB 層還沒有物理上的新約束把關）：
-- ORM 的 UniqueConstraint 已改成 (cycle_id, period_label, company, item_id, department_id)，
-- 但 SQLite 既有資料表的實體 UNIQUE 限制不會因為只跑這支 ALTER TABLE 就自動更新
-- （SQLite 不支援 ALTER TABLE 直接改 constraint，需要整張表重建才能真正生效）。
-- 目前彙整的冪等性是靠 service 層 generate_summary() 明確查詢再插入把關，
-- 不是靠 DB constraint 擋重複，所以這個限制不影響現有功能；若未來想讓 DB
-- 層也真正套用新的 UNIQUE 約束，需要另外排一次「整張表重建」的遷移。
--
-- 既有資料：department_id 一律先是 NULL（代表「2026-07-16 之前產生的歷史彙整列，
-- 未拆分部門」），不會回填，因為已合併的 demand_qty 無法反推是哪些部門貢獻的。

ALTER TABLE cycle_purchase_summary ADD COLUMN department_id INTEGER;
ALTER TABLE cycle_purchase_summary ADD COLUMN ragic_push_batch_no VARCHAR(40);
ALTER TABLE cycle_purchase_summary ADD COLUMN ragic_pushed BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE cycle_purchase_summary ADD COLUMN ragic_record_id VARCHAR(60);
ALTER TABLE cycle_purchase_summary ADD COLUMN ragic_pushed_at DATETIME;
ALTER TABLE cycle_purchase_summary ADD COLUMN ragic_push_error TEXT;
