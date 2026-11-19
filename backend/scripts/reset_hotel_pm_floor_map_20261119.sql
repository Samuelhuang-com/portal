-- 飯店例行維護樓層巡檢圖：清除舊點位，讓啟動時依 v2 Excel 重新種入（2026-11-19）
-- ⚠️ 執行前請確認：此模組尚無人工定位或新增的點位（會一併刪除）。
-- 執行後重啟後端即會種入母項點位與子項點位（待定位）。
BEGIN;
DELETE FROM floor_map_points WHERE module = 'hotel_periodic_maintenance';
DELETE FROM floor_map_disabled_sources WHERE module = 'hotel_periodic_maintenance';
-- 檢查：應為 0
SELECT COUNT(*) AS remaining FROM floor_map_points WHERE module = 'hotel_periodic_maintenance';
COMMIT;
