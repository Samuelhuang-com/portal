-- ============================================================================
--  週期採購「料號主檔＋料號對照表」匯出腳本（2026-08-09）
--
--  用途：把 /cycle-purchase/items 這一頁背後的兩張表，匯出成可以在**另一個
--        環境**直接執行的 INSERT 語句。
--
--          cycle_purchase_items          料號主檔
--          cycle_purchase_item_mappings  料號對照表（一個料號在每家公司一列）
--
--  這支腳本**只讀不寫**，不會改到來源資料庫。
--
--  用法（在 portal 資料夾開終端機）：
--      sqlite3 C:\portal_data\cycle-purchase.db < export_cycle_purchase_items.sql > cycle_purchase_items_data.sql
--
--  或直接雙擊同資料夾的 export_cycle_purchase_items.bat（會自動加日期檔名）。
--
--  產出的 cycle_purchase_items_data.sql 就是要拿到目標環境執行的檔案。
--
--  ⚠️ 最重要的一件事：**id 會原封不動帶過去**
--     對照表用 item_id / department_id / vendor_id 指向另外三張表。為了讓
--     對照表接得回料號，料號的 id 必須保持一致，所以匯出含 id。
--     連帶的風險是：
--       1. 目標環境如果**已經有料號資料**，id 會撞號 → 匯入失敗（這是好事，
--          總比靜默覆蓋好）。要先清空或改用 INSERT OR REPLACE，見產出檔的說明。
--       2. 目標環境的**部門／供應商 id 如果對不上**，對照表會指到錯的部門或
--          廠商，或因為外鍵而匯入失敗。產出檔開頭會列出這批資料依賴哪些
--          部門／供應商 id 與名稱，**匯入前務必先比對**。
-- ============================================================================

.mode list
.headers off

-- ── 防呆：先確認這個資料庫真的是 cycle-purchase.db ──────────────────────────
-- ⚠️ sqlite3 遇到**不存在的檔案會直接建一個空的**，不會報錯。所以路徑打錯時，
--    後面每一句都會噴 "no such table: cycle_purchase_items"，看起來像腳本壞了，
--    其實是開錯資料庫。這一段用 sqlite_master（任何資料庫都一定有）先檢查，
--    讓第一行就出現看得懂的訊息。
SELECT CASE WHEN (
         SELECT COUNT(*) FROM sqlite_master
          WHERE type = 'table' AND name = 'cycle_purchase_items'
       ) = 0
       THEN '!!!!!! 錯誤：這個資料庫裡沒有 cycle_purchase_items 資料表。' || char(10) ||
            '!!!!!! 你可能開錯檔案了 —— sqlite3 對不存在的路徑會「安靜地建一個空 db」。' || char(10) ||
            '!!!!!! 正確用法（路徑要用完整路徑並加引號）：' || char(10) ||
            '!!!!!!   sqlite3 "C:\portal_data\cycle-purchase.db" < export_cycle_purchase_items.sql > items_data.sql' || char(10) ||
            '!!!!!! 實際路徑請以該機器 backend\.env 的 CYCLE_PURCHASE_DATABASE_URL 為準。' || char(10) ||
            '!!!!!! （若剛才誤建了空檔案，記得把它刪掉）'
       END
 WHERE (SELECT COUNT(*) FROM sqlite_master
         WHERE type = 'table' AND name = 'cycle_purchase_items') = 0;

-- ── 產出檔的檔頭與匯入前檢查清單 ────────────────────────────────────────────
SELECT '-- ============================================================';
SELECT '--  週期採購 料號主檔＋料號對照表 資料';
SELECT '--  匯出時間：' || datetime('now', 'localtime');
SELECT '--  來源筆數：料號主檔 ' ||
       (SELECT COUNT(*) FROM cycle_purchase_items) || ' 筆、對照表 ' ||
       (SELECT COUNT(*) FROM cycle_purchase_item_mappings) || ' 筆';
SELECT '--            （其中停用料號 ' ||
       (SELECT COUNT(*) FROM cycle_purchase_items WHERE is_active = 0) || ' 筆，一併匯出）';
SELECT '-- ============================================================';
SELECT '--';
SELECT '--  ⚠️ 匯入前務必先做這兩件事：';
SELECT '--';
SELECT '--  (1) 確認目標環境的「部門」「供應商」對得上。這批資料依賴以下 id：';

SELECT '--      部門 id=' || d.id || '  ' || d.company || ' / ' || d.dept_name ||
       '   （被 ' || COUNT(m.id) || ' 筆對照列使用）'
  FROM cycle_purchase_item_mappings m
  JOIN cycle_purchase_departments d ON d.id = m.department_id
 GROUP BY d.id, d.company, d.dept_name
 ORDER BY d.id;

SELECT '--      供應商 id=' || v.id || '  ' || v.vendor_name ||
       '   （被 ' || COUNT(m.id) || ' 筆對照列使用）'
  FROM cycle_purchase_item_mappings m
  JOIN cycle_purchase_vendors v ON v.id = m.vendor_id
 GROUP BY v.id, v.vendor_name
 ORDER BY v.id;

SELECT '--';
SELECT '--      在目標環境跑這段對照，確認名稱一樣（有差異就先處理再匯入）：';
SELECT '--        SELECT id, company, dept_name FROM cycle_purchase_departments ORDER BY id;';
SELECT '--        SELECT id, vendor_name        FROM cycle_purchase_vendors      ORDER BY id;';
SELECT '--';
SELECT '--  (2) 確認目標環境的這兩張表是空的：';
SELECT '--        SELECT COUNT(*) FROM cycle_purchase_items;';
SELECT '--        SELECT COUNT(*) FROM cycle_purchase_item_mappings;';
SELECT '--      不是空的就會撞 id。要覆蓋的話把下面那兩行 DELETE 的註解拿掉，';
SELECT '--      ⚠️ 但那會刪掉目標環境現有的料號資料，刪之前請先備份 db 檔。';
SELECT '--';
SELECT '-- ============================================================';
SELECT '';
SELECT 'PRAGMA foreign_keys = ON;   -- 刻意開著：對不上就讓它失敗，不要靜默寫入孤兒資料';
SELECT 'BEGIN TRANSACTION;';
SELECT '';
SELECT '-- DELETE FROM cycle_purchase_item_mappings;   -- ⚠️ 要覆蓋才解除註解（先刪子表）';
SELECT '-- DELETE FROM cycle_purchase_items;           -- ⚠️ 要覆蓋才解除註解';
SELECT '';

-- ── 料號主檔 ────────────────────────────────────────────────────────────────
SELECT '-- ── 料號主檔 cycle_purchase_items（' ||
       (SELECT COUNT(*) FROM cycle_purchase_items) || ' 筆）──';

SELECT 'INSERT INTO cycle_purchase_items ' ||
       '(id, item_code, item_name, spec, category, unit, default_qty, moq, ' ||
       'max_stock, min_stock, unit_price, default_vendor_id, is_active, ' ||
       'is_cycle_item, notes, created_at, updated_at) VALUES (' ||
       quote(id)                || ', ' ||
       quote(item_code)         || ', ' ||
       quote(item_name)         || ', ' ||
       quote(spec)              || ', ' ||
       quote(category)          || ', ' ||
       quote(unit)              || ', ' ||
       quote(default_qty)       || ', ' ||
       quote(moq)               || ', ' ||
       quote(max_stock)         || ', ' ||
       quote(min_stock)         || ', ' ||
       quote(unit_price)        || ', ' ||
       quote(default_vendor_id) || ', ' ||
       quote(is_active)         || ', ' ||
       quote(is_cycle_item)     || ', ' ||
       quote(notes)             || ', ' ||
       quote(created_at)        || ', ' ||
       quote(updated_at)        || ');'
  FROM cycle_purchase_items
 ORDER BY id;

SELECT '';

-- ── 料號對照表 ──────────────────────────────────────────────────────────────
SELECT '-- ── 料號對照表 cycle_purchase_item_mappings（' ||
       (SELECT COUNT(*) FROM cycle_purchase_item_mappings) || ' 筆）──';
SELECT '-- 一列 = 一個「公司 × 料號」。department_id / vendor_id 指向目標環境的';
SELECT '-- 部門／供應商主檔，對不上就會被外鍵擋下（見檔頭說明）。';

SELECT 'INSERT INTO cycle_purchase_item_mappings ' ||
       '(id, item_id, company, department_id, original_code, original_name, ' ||
       'original_vendor_name, vendor_id, original_unit_price, is_confirmed, ' ||
       'notes, created_at, updated_at) VALUES (' ||
       quote(id)                    || ', ' ||
       quote(item_id)               || ', ' ||
       quote(company)               || ', ' ||
       quote(department_id)         || ', ' ||
       quote(original_code)         || ', ' ||
       quote(original_name)         || ', ' ||
       quote(original_vendor_name)  || ', ' ||
       quote(vendor_id)             || ', ' ||
       quote(original_unit_price)   || ', ' ||
       quote(is_confirmed)          || ', ' ||
       quote(notes)                 || ', ' ||
       quote(created_at)            || ', ' ||
       quote(updated_at)            || ');'
  FROM cycle_purchase_item_mappings
 ORDER BY id;

SELECT '';
SELECT 'COMMIT;';
SELECT '';

-- ── 匯入後的驗證查詢（附在產出檔末尾，方便直接複製執行）────────────────────
SELECT '-- ── 匯入後請跑這幾句確認 ──';
SELECT '-- 1) 筆數要對得上（應為 ' ||
       (SELECT COUNT(*) FROM cycle_purchase_items) || ' / ' ||
       (SELECT COUNT(*) FROM cycle_purchase_item_mappings) || '）';
SELECT '--    SELECT (SELECT COUNT(*) FROM cycle_purchase_items) AS items,';
SELECT '--           (SELECT COUNT(*) FROM cycle_purchase_item_mappings) AS mappings;';
SELECT '-- 2) 外鍵沒有斷掉（應回傳 0 列）';
SELECT '--    PRAGMA foreign_key_check;';
SELECT '-- 3) 對照表的部門／供應商都指得到（應回傳 0 列）';
SELECT '--    SELECT m.id, m.company, m.department_id, m.vendor_id';
SELECT '--      FROM cycle_purchase_item_mappings m';
SELECT '--      LEFT JOIN cycle_purchase_departments d ON d.id = m.department_id';
SELECT '--      LEFT JOIN cycle_purchase_vendors     v ON v.id = m.vendor_id';
SELECT '--     WHERE d.id IS NULL OR (m.vendor_id IS NOT NULL AND v.id IS NULL);';
