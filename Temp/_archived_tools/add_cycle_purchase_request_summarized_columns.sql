-- 2026-07-16（第二次調整）：週期採購「彙整單產生方式」改版
-- 為 cycle_purchase_requests 補上 is_summarized / summary_batch_no / summarized_at，
-- 用來標記「這張已核准的請購單是否已經被某次彙整動作納入過」，避免同一張單
-- 被重複勾選彙整、重複計入數量。詳見 backend/app/models/cycle_purchase_request.py
-- 開頭「2026-07-16（與 Samuel 確認，彙整單產生方式改版...）」段落，以及
-- backend/app/services/cycle_purchase_summary_service.py 開頭「第二次調整」說明。
--
-- 執行對象：cycle-purchase.db（獨立資料庫，與 portal.db 分開，見
-- backend/app/core/cycle_purchase_database.py），不是 portal.db。
-- SQLAlchemy 的 create_all() 不會幫已存在的資料表補欄位，需要手動執行本檔案
-- （或用等效的 DB 工具，例如隨附的 apply_cycle_purchase_summary_migration.py
-- 可以照樣改寫成跑這份 SQL）。
--
-- 冪等性：SQLite 的 ALTER TABLE ADD COLUMN 若欄位已存在會報錯而非略過，
-- 重複執行前請先確認欄位是否已加過（例如用
-- PRAGMA table_info(cycle_purchase_requests);）。
--
-- 既有資料：is_summarized 一律先是 0（false），代表「2026-07-16 之前建立的
-- 請購單，一律視為尚未被彙整過」——不會回填，因為舊版彙整是靠期別字串比對，
-- 沒有實際記錄「這張單有沒有被彙整過」這件事。如果舊資料裡有已經彙整過、
-- 甚至已經轉單的請購單，補完這個欄位後，它們理論上還是會出現在「可彙整
-- 清單」裡（因為 is_summarized 預設 0）——這是已知的過渡期限制，之後如果
-- 要清乾淨，需要另外對照舊的彙整列資料手動標記，不在這次遷移範圍內。

ALTER TABLE cycle_purchase_requests ADD COLUMN is_summarized BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE cycle_purchase_requests ADD COLUMN summary_batch_no VARCHAR(40);
ALTER TABLE cycle_purchase_requests ADD COLUMN summarized_at DATETIME;
