-- ============================================================================
-- 商場例行維護「樓層巡檢圖」：停用 13 個「全區」子項（2026-11-04 Samuel 指示；2026-11-05 改為子項停用）
-- 頁面：/mall/periodic-maintenance → TAB「樓層巡檢圖」
-- 資料庫：PostgreSQL（正式區、測試區各執行一次）
--
-- ⚠️ 2026-11-05 改版：點位已改為「母項」，停用改為針對「子項」（floor_map_disabled_sources）。
--    執行順序：先 alembic upgrade head（含 fmappm2），再執行本 script。
--    若在 fmappm2 之前已執行過舊版 script（停用子項點位），fmappm2 會自動轉成子項停用，本 script 再跑也不會重複。
--
-- 效果：這些子項仍顯示在母項的子項清單（灰色、已停用），但不計入母項當日狀態；
--       母項 8 公區壁面批土補漆、10 燈箱招牌維護含底座、11 門扇→保養 的子項全部停用 → 母項點位只在編輯模式顯示；
--       不會出現在「未對應」。恢復可在畫面上（編輯點位 → 子項清單 → 恢復）或用檔尾還原語法。
-- 預期：13 個子項
-- ============================================================================

-- ── 1. 停用（可重複執行：已停用的子項不會重複寫入）──────────────────────────
BEGIN;

INSERT INTO floor_map_disabled_sources (module, source_ref, disabled_by, disabled_at)
VALUES
    ('mall_periodic_maintenance', '五金及固定配件', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_periodic_maintenance', '安全及設施維護', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_periodic_maintenance', '各樓層後勤通道', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_periodic_maintenance', '廁所動線', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_periodic_maintenance', '公共區域', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_periodic_maintenance', '後場區域(辦公室/回收區/卸貨區/梯廳/員休室/會議室)', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_periodic_maintenance', '固定桌椅檢查保養', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_periodic_maintenance', '照明設備檢查保養', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_periodic_maintenance', '電力設備(電箱)附載檢查', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_periodic_maintenance', '停車場招牌燈箱*2戶外指引牌*4 懸掛式招牌*2(小後苑廊道)', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_periodic_maintenance', '春大直LOGO燈字招牌*2 館內燈箱指引牌*6', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_periodic_maintenance', '不鏽鋼除鏽保養', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_periodic_maintenance', '門扇→巡檢保養', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei'))
ON CONFLICT (module, source_ref) DO NOTHING;
-- 第一次執行預期：INSERT 0 13（fmappm2 已自動轉入者會少算，屬正常）

-- ── 2. 驗證（應列出 13 筆）──────────────────────────────────────
SELECT source_ref, disabled_by, disabled_at
FROM floor_map_disabled_sources
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
ORDER BY source_ref;

COMMIT;

-- ── 還原（恢復這些子項）────────────────────────────────────────────────────────
-- DELETE FROM floor_map_disabled_sources
-- WHERE module = 'mall_periodic_maintenance'
--   AND source_ref IN (
--           '五金及固定配件',
--           '安全及設施維護',
--           '各樓層後勤通道',
--           '廁所動線',
--           '公共區域',
--           '後場區域(辦公室/回收區/卸貨區/梯廳/員休室/會議室)',
--           '固定桌椅檢查保養',
--           '照明設備檢查保養',
--           '電力設備(電箱)附載檢查',
--           '停車場招牌燈箱*2戶外指引牌*4 懸掛式招牌*2(小後苑廊道)',
--           '春大直LOGO燈字招牌*2 館內燈箱指引牌*6',
--           '不鏽鋼除鏽保養',
--           '門扇→巡檢保養'
--       );
