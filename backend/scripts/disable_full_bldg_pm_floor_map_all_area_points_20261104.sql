-- ============================================================================
-- 全棟例行維護「樓層巡檢圖」：停用 4 個「全區」子項（2026-11-04 Samuel 指示；2026-11-05 改為子項停用）
-- 頁面：/mall/full-building-maintenance → TAB「樓層巡檢圖」
-- 資料庫：PostgreSQL（正式區、測試區各執行一次）
--
-- ⚠️ 2026-11-05 改版：點位已改為「母項」，停用改為針對「子項」（floor_map_disabled_sources）。
--    執行順序：先 alembic upgrade head（含 fmappm2），再執行本 script。
--    若在 fmappm2 之前已執行過舊版 script（停用子項點位），fmappm2 會自動轉成子項停用，本 script 再跑也不會重複。
--
-- 效果：這些子項仍顯示在母項的子項清單（灰色、已停用），但不計入母項當日狀態；
--       母項 19 客貨梯/扶梯保養、20 倉庫整理、盤點（含工具）、21 工務耗材庫存管理每月盤點出單 的子項全部停用 → 母項點位只在編輯模式顯示；
--       不會出現在「未對應」。恢復可在畫面上（編輯點位 → 子項清單 → 恢復）或用檔尾還原語法。
-- 預期：4 個子項
-- ============================================================================

-- ── 1. 停用（可重複執行：已停用的子項不會重複寫入）──────────────────────────
BEGIN;

INSERT INTO floor_map_disabled_sources (module, source_ref, disabled_by, disabled_at)
VALUES
    ('mall_full_building_maintenance', '商場扶梯x4', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_full_building_maintenance', '商場客.貨x4', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_full_building_maintenance', '倉庫整理、盤點（含工具）', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei')),
    ('mall_full_building_maintenance', '工務耗材庫存管理每月盤點出單', 'sql:20261105-停用子項', (now() AT TIME ZONE 'Asia/Taipei'))
ON CONFLICT (module, source_ref) DO NOTHING;
-- 第一次執行預期：INSERT 0 4（fmappm2 已自動轉入者會少算，屬正常）

-- ── 2. 驗證（應列出 4 筆）──────────────────────────────────────
SELECT source_ref, disabled_by, disabled_at
FROM floor_map_disabled_sources
WHERE module = 'mall_full_building_maintenance'
  AND source_ref IN (
        '商場扶梯x4',
        '商場客.貨x4',
        '倉庫整理、盤點（含工具）',
        '工務耗材庫存管理每月盤點出單'
      )
ORDER BY source_ref;

COMMIT;

-- ── 還原（恢復這些子項）────────────────────────────────────────────────────────
-- DELETE FROM floor_map_disabled_sources
-- WHERE module = 'mall_full_building_maintenance'
--   AND source_ref IN (
--           '商場扶梯x4',
--           '商場客.貨x4',
--           '倉庫整理、盤點（含工具）',
--           '工務耗材庫存管理每月盤點出單'
--       );
