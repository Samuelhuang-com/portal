-- ============================================================================
-- 全棟例行維護「樓層巡檢圖」：停用 4 個「全區」保養項目的點位（2026-11-04 Samuel 指示）
-- 頁面：/mall/full-building-maintenance → TAB「樓層巡檢圖」
-- 資料庫：PostgreSQL（正式區、測試區各執行一次；需先 alembic upgrade head 寫入點位）
--
-- 停用＝is_active = false（與畫面上「停用點位」相同，不硬刪，資料列保留）
-- 4 項 × 9 層（RF、4F～B4F）＝預期 36 點；停用後全棟例行維護剩 68 個啟用點位
-- 停用的項目不會列入「未對應」（有點位紀錄含已停用＝刻意不放在圖上）
-- 可重複執行：已停用的點不會再被計入
-- ============================================================================

-- ── 1. 先確認（應為 4 項、36 點；尚未停用前 active_points 皆為 9）────────────
SELECT source_ref,
       COUNT(*)                                AS points,
       COUNT(*) FILTER (WHERE is_active)       AS active_points,
       STRING_AGG(floor_key, ',' ORDER BY floor_key) AS floors
FROM floor_map_points
WHERE module = 'mall_full_building_maintenance'
  AND source_ref IN (
        '商場扶梯x4',
        '商場客.貨x4',
        '倉庫整理、盤點（含工具）',
        '工務耗材庫存管理每月盤點出單'
      )
GROUP BY source_ref
ORDER BY source_ref;

-- ── 2. 停用 ───────────────────────────────────────────────────────────────────
BEGIN;

UPDATE floor_map_points
SET is_active  = false,
    updated_by = 'sql:20261104-停用全棟全區點位',
    updated_at = (now() AT TIME ZONE 'Asia/Taipei')
WHERE module = 'mall_full_building_maintenance'
  AND is_active = true
  AND source_ref IN (
        '商場扶梯x4',
        '商場客.貨x4',
        '倉庫整理、盤點（含工具）',
        '工務耗材庫存管理每月盤點出單'
      );
-- 第一次執行預期顯示：UPDATE 36
-- 數字不對就執行 ROLLBACK; 不要 COMMIT

-- ── 3. 驗證（停用後：啟用點位應剩 68）──────────────────────────────────────────
SELECT COUNT(*) FILTER (WHERE is_active)     AS active_points,
       COUNT(*) FILTER (WHERE NOT is_active) AS disabled_points
FROM floor_map_points
WHERE module = 'mall_full_building_maintenance';

COMMIT;

-- ── 還原（如需恢復這 36 點，只還原本 script 停用的）─────────────────────────────
-- UPDATE floor_map_points
-- SET is_active = true, updated_by = 'sql:20261104-還原全棟全區點位', updated_at = (now() AT TIME ZONE 'Asia/Taipei')
-- WHERE module = 'mall_full_building_maintenance' AND updated_by = 'sql:20261104-停用全棟全區點位';
