-- ============================================================================
-- 週期採購 — 料號主檔：把「規格 spec」合併進「品名 item_name」
--
-- 目標資料庫：cycle-purchase.db（週期採購獨立 SQLite，非 portal.db）
--             路徑見 backend/.env 的 CYCLE_PURCHASE_DATABASE_URL
-- 目標資料表：cycle_purchase_items
-- 對應頁面：/cycle-purchase/masters/items
--
-- 決策（2026-08-20 與 Samuel 確認）：
--   1. 格式＝「品名」+ 一個半形空白 + 「規格」  例：洗手乳 5L/桶
--   2. spec 欄位「保留原值不動」（不清空、不搬到 notes）
--
-- 特性：
--   * 可重複執行（idempotent）：品名已含該規格字串者一律跳過，不會越接越長
--   * spec 為 NULL／空字串／純空白者跳過
--   * 只改 item_name，不動任何其他欄位、不動 schema
--
-- 執行方式：
--   sqlite3 "C:\Portal_Data\cycle-purchase.db" ".read merge_cycle_purchase_item_spec_into_name.sql"
--   （執行前請先停掉後端服務，避免 database is locked）
-- ============================================================================

-- ── STEP 0：先看影響範圍（可單獨執行這段確認再往下）─────────────────────────
SELECT
    '將被更新的筆數' AS metric,
    COUNT(*)         AS value
FROM cycle_purchase_items
WHERE spec IS NOT NULL
  AND TRIM(spec) <> ''
  AND INSTR(item_name, TRIM(spec)) = 0;

-- 前 30 筆變更預覽
SELECT
    id,
    item_code,
    item_name                              AS 原品名,
    spec                                   AS 規格,
    item_name || ' ' || TRIM(spec)         AS 合併後品名
FROM cycle_purchase_items
WHERE spec IS NOT NULL
  AND TRIM(spec) <> ''
  AND INSTR(item_name, TRIM(spec)) = 0
ORDER BY id
LIMIT 30;


BEGIN TRANSACTION;

-- ── STEP 1：備份（同檔案內留一份快照，可隨時回滾）───────────────────────────
DROP TABLE IF EXISTS _bak_cycle_purchase_items_20260820;

CREATE TABLE _bak_cycle_purchase_items_20260820 AS
SELECT id, item_code, item_name, spec
FROM cycle_purchase_items;

-- ── STEP 2：合併 ────────────────────────────────────────────────────────────
UPDATE cycle_purchase_items
SET item_name = item_name || ' ' || TRIM(spec),
    updated_at = CURRENT_TIMESTAMP
WHERE spec IS NOT NULL
  AND TRIM(spec) <> ''
  AND INSTR(item_name, TRIM(spec)) = 0;

COMMIT;


-- ── STEP 3：驗證 ────────────────────────────────────────────────────────────
-- 3-1 應為 0：已無「有規格但品名未含規格」的列
SELECT
    '殘留未合併筆數（應為 0）' AS metric,
    COUNT(*)                   AS value
FROM cycle_purchase_items
WHERE spec IS NOT NULL
  AND TRIM(spec) <> ''
  AND INSTR(item_name, TRIM(spec)) = 0;

-- 3-2 前後對照（前 30 筆實際有變動的）
SELECT
    b.id,
    b.item_code,
    b.item_name AS 變更前,
    i.item_name AS 變更後
FROM _bak_cycle_purchase_items_20260820 b
JOIN cycle_purchase_items i ON i.id = b.id
WHERE b.item_name <> i.item_name
ORDER BY b.id
LIMIT 30;

-- 3-3 合併後是否出現重複品名（item_name 無 unique 約束，僅供人工檢視）
SELECT item_name, COUNT(*) AS cnt
FROM cycle_purchase_items
GROUP BY item_name
HAVING cnt > 1
ORDER BY cnt DESC;


-- ============================================================================
-- 回滾（僅在確認要還原時，單獨執行以下三行）
-- ============================================================================
-- BEGIN TRANSACTION;
-- UPDATE cycle_purchase_items
--    SET item_name = (SELECT b.item_name
--                       FROM _bak_cycle_purchase_items_20260820 b
--                      WHERE b.id = cycle_purchase_items.id)
--  WHERE id IN (SELECT id FROM _bak_cycle_purchase_items_20260820);
-- COMMIT;
