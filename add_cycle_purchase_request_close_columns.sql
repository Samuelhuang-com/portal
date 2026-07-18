-- 2026-07-17（第三次調整）：週期採購「請購單流程」大改版
-- 拿掉送出／核准／退回，改成「關閉／重新開啟」。為 cycle_purchase_requests
-- 補上 is_closed / closed_by_user_id / closed_by_name / closed_at /
-- close_batch_no / reopened_by_user_id / reopened_by_name / reopened_at，
-- 並把舊資料裡 status='approved' 的請購單一次性轉換成 is_closed=True
-- （closed_* 欄位從既有的 approved_* 欄位回填）。
--
-- 詳見 backend/app/models/cycle_purchase_request.py 開頭「2026-07-17（第三次
-- 調整...）」段落，以及 backend/app/services/cycle_purchase_request_service.py、
-- cycle_purchase_summary_service.py 開頭的對應說明。
--
-- 執行對象：cycle-purchase.db（獨立資料庫，與 portal.db 分開，見
-- backend/app/core/cycle_purchase_database.py），不是 portal.db。
--
-- ⚠️ 建議優先使用同資料夾的 apply_cycle_purchase_summary_migration.py
-- （雙擊 apply_cycle_purchase_summary_migration.bat 即可）：那支腳本會先用
-- PRAGMA table_info 檢查每個欄位是否已存在、只補「還沒加過」的，而且已經
-- 把這次的欄位與一次性資料轉換都納入了，不需要再手動跑這份 SQL。這份 SQL
-- 檔案只是同一份變更的另一種呈現方式（供想直接看 DDL／自己執行 SQL 的情況
-- 參考），冪等性沒有 .py 版本完整——SQLite 的 ALTER TABLE ADD COLUMN 若欄位
-- 已存在會直接報錯而不是略過，執行前請先用
-- PRAGMA table_info(cycle_purchase_requests); 確認欄位是否已加過；最後的
-- UPDATE 語句本身有用 close_batch_no IS NULL 防呆，可以放心重複執行。

ALTER TABLE cycle_purchase_requests ADD COLUMN is_closed BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE cycle_purchase_requests ADD COLUMN closed_by_user_id VARCHAR(36);
ALTER TABLE cycle_purchase_requests ADD COLUMN closed_by_name VARCHAR(100);
ALTER TABLE cycle_purchase_requests ADD COLUMN closed_at DATETIME;
ALTER TABLE cycle_purchase_requests ADD COLUMN close_batch_no VARCHAR(40);
ALTER TABLE cycle_purchase_requests ADD COLUMN reopened_by_user_id VARCHAR(36);
ALTER TABLE cycle_purchase_requests ADD COLUMN reopened_by_name VARCHAR(100);
ALTER TABLE cycle_purchase_requests ADD COLUMN reopened_at DATETIME;

-- 一次性資料轉換：舊資料 status='approved' -> is_closed=True，closed_* 從
-- approved_* 回填。用 close_batch_no IS NULL 判斷「還沒轉換過」，重複執行
-- 這段 UPDATE 不會覆蓋掉之後使用者手動關閉／重新開啟的結果。
UPDATE cycle_purchase_requests
SET is_closed = 1,
    closed_by_user_id = approved_by_user_id,
    closed_by_name = approved_by_name,
    closed_at = approved_at,
    close_batch_no = 'LEGACY-CONVERT-20260717'
WHERE status = 'approved' AND close_batch_no IS NULL;
