-- ============================================================================
-- 商場例行維護「樓層巡檢圖」：停用 13 個「全區」保養項目的點位（2026-11-04 Samuel 指示）
-- 頁面：/mall/periodic-maintenance → TAB「樓層巡檢圖」
-- 資料庫：PostgreSQL（正式區、測試區各執行一次）
--
-- 停用＝is_active = false（與畫面上「停用點位」相同，不硬刪，資料列保留）
-- 13 項 × 8 層（4F～B4F）＝預期 104 點；停用後商場例行維護剩 26 個啟用點位
-- 可重複執行：已停用的點不會再被計入
-- ============================================================================

-- ── 1. 先確認（應為 13 項、104 點；尚未停用前 active_points 皆為 8）──────────
SELECT source_ref,
       COUNT(*)                                AS points,
       COUNT(*) FILTER (WHERE is_active)       AS active_points,
       STRING_AGG(floor_key, ',' ORDER BY floor_key) AS floors
FROM floor_map_points
WHERE module = 'mall_periodic_maintenance'
  AND source_ref IN (
        '五金及固定配件',
        '安全及設施維護',
        '各樓層後勤通道',
        '廁所動線',
        '公共區域',
        '後場區域(辦公室/回收區/卸貨區/梯廳/員休室/會議室)',
        '固定桌椅檢查保養',
        '照明設備檢查保養',
        '電力設備(電箱)附載檢查',
        '停車場招牌燈箱*2戶外指引牌*4 懸掛式招牌*2(小後苑廊道)',
        '春大直LOGO燈字招牌*2 館內燈箱指引牌*6',
        '不鏽鋼除鏽保養',
        '門扇→巡檢保養'
      )
GROUP BY source_ref
ORDER BY source_ref;

-- ── 2. 停用 ───────────────────────────────────────────────────────────────────
BEGIN;

UPDATE floor_map_points
SET is_active  = false,
    updated_by = 'sql:20261104-停用全區點位',
    updated_at = (now() AT TIME ZONE 'Asia/Taipei')
WHERE module = 'mall_periodic_maintenance'
  AND is_active = true
  AND source_ref IN (
        '五金及固定配件',
        '安全及設施維護',
        '各樓層後勤通道',
        '廁所動線',
        '公共區域',
        '後場區域(辦公室/回收區/卸貨區/梯廳/員休室/會議室)',
        '固定桌椅檢查保養',
        '照明設備檢查保養',
        '電力設備(電箱)附載檢查',
        '停車場招牌燈箱*2戶外指引牌*4 懸掛式招牌*2(小後苑廊道)',
        '春大直LOGO燈字招牌*2 館內燈箱指引牌*6',
        '不鏽鋼除鏽保養',
        '門扇→巡檢保養'
      );
-- 第一次執行預期顯示：UPDATE 104
-- 數字不對就執行 ROLLBACK; 不要 COMMIT

-- ── 3. 驗證（停用後：啟用點位應剩 26）──────────────────────────────────────────
SELECT COUNT(*) FILTER (WHERE is_active)     AS active_points,
       COUNT(*) FILTER (WHERE NOT is_active) AS disabled_points
FROM floor_map_points
WHERE module = 'mall_periodic_maintenance';

COMMIT;

-- ── 還原（如需恢復這 104 點，只還原本 script 停用的）────────────────────────────
-- UPDATE floor_map_points
-- SET is_active = true, updated_by = 'sql:20261104-還原全區點位', updated_at = (now() AT TIME ZONE 'Asia/Taipei')
-- WHERE module = 'mall_periodic_maintenance' AND updated_by = 'sql:20261104-停用全區點位';
