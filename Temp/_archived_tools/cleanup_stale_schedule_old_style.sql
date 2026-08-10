-- ============================================================================
-- 清除 mall_pm_schedule / full_bldg_pm_schedule 殘留舊格式排程記錄
-- 2026-07-13，Sheet24（商場）/ Sheet28（全棟）改版後發現：
--
-- 排程表以 (year_month, item_ragic_id) 判斷該排程是否已存在。改版把
-- item_ragic_id 格式由 "{batch_id}_{row_key}"（如 "4_56"，含底線）
-- 改為 Ragic 項目自身的原始 ragic_id（如 "56"，不含底線）後，「產生本月
-- 排程」比對不到舊記錄，另外新增一筆新格式記錄，卻沒有清掉舊記錄，
-- 導致同一保養項目在行事曆／本月排程列表上重複出現兩筆，且日期可能
-- 不一致（舊記錄是改版前的舊資料，不會再更新）。
--
-- 已用瀏覽器直連 API 逐月核對（2026/01～2026/12）：
--   mall_pm_schedule       ：2026/05（12 筆全舊格式）、2026/06（14 筆全舊格式）、
--                            2026/07（8 舊 + 8 新，重複）共 34 筆殘留舊格式記錄
--   full_bldg_pm_schedule  ：目前無殘留（0 筆舊格式）
-- 且確認這 34 筆殘留記錄均為 is_completed=0、abnormal_flag=0、
-- portal_edited_at IS NULL、start_time/end_time 皆空 —— 刪除不會遺失
-- 任何人工已完成／已標記異常／人工調整過的資料。
--
-- 對應程式碼修正：backend/app/services/mall_periodic_maintenance_sync.py 與
-- full_building_maintenance_sync.py 的 sync_items_from_sheet24()／
-- sync_items_from_sheet28() 已加上相同清除邏輯，往後每次 Ragic 同步都會
-- 自動清除新產生的舊格式殘留（若發現有人工資料的舊格式記錄則保留並記錄
-- warning，不自動刪除）。本次 SQL 僅處理「本次執行前」已存在的殘留資料。
--
-- 安全性：WHERE 條件與程式碼清除邏輯完全一致，只刪除「無人工資料」的舊格式
-- 記錄；執行前後筆數可用下方 SELECT 對照確認。
-- ============================================================================

-- 執行前檢查（先跑這段確認筆數，再執行下方 DELETE）：
-- SELECT 'mall_pm_schedule'      AS tbl, COUNT(*) AS old_style_safe_to_delete
--   FROM mall_pm_schedule
--  WHERE INSTR(item_ragic_id, '_') > 0
--    AND is_completed = 0 AND abnormal_flag = 0 AND portal_edited_at IS NULL
--    AND (start_time = '' OR start_time IS NULL) AND (end_time = '' OR end_time IS NULL)
-- UNION ALL
-- SELECT 'full_bldg_pm_schedule', COUNT(*)
--   FROM full_bldg_pm_schedule
--  WHERE INSTR(item_ragic_id, '_') > 0
--    AND is_completed = 0 AND abnormal_flag = 0 AND portal_edited_at IS NULL
--    AND (start_time = '' OR start_time IS NULL) AND (end_time = '' OR end_time IS NULL);

DELETE FROM mall_pm_schedule
 WHERE INSTR(item_ragic_id, '_') > 0
   AND is_completed = 0
   AND abnormal_flag = 0
   AND portal_edited_at IS NULL
   AND (start_time = '' OR start_time IS NULL)
   AND (end_time = '' OR end_time IS NULL);

DELETE FROM full_bldg_pm_schedule
 WHERE INSTR(item_ragic_id, '_') > 0
   AND is_completed = 0
   AND abnormal_flag = 0
   AND portal_edited_at IS NULL
   AND (start_time = '' OR start_time IS NULL)
   AND (end_time = '' OR end_time IS NULL);
