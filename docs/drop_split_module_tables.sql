-- ============================================================================
-- 五組已獨立模組的資料表清除（opera / realtime(OHIP) / jinxu / ota / compset）
-- 建立日期：2026-09-11
--
-- ⚠️⚠️ 本檔**刻意不自動執行**。程式碼已經拆乾淨，但資料表仍原地保留，
--      等新專案確認資料都搬完、對得起來之後，再手動跑這一支。
--
-- 執行前必做（沒做就別跑）：
--   1) 完整備份：
--        py -3.11 backend\scripts\pg_backup.py --verify-restore
--      （pg_dump 回 0 不代表還原得回來，--verify-restore 才是證明）
--   2) 確認新專案那邊這 46 張表的資料筆數與這裡一致。
--
-- 執行：
--   psql -h <host> -U <user> -d <db> -f drop_split_module_tables.sql
--
-- 表數：opera_ 11、ohip_ 12、jinxu_ 9、ota_ 7、compset_ 7 ＝ 46
-- FK 跨界只有 users.id × 2（在 compset 訂閱使用者關聯），
-- 所以 compset 那組先刪、並加 CASCADE。
-- ============================================================================

BEGIN;

-- ── 執行前的筆數快照：先看，再決定要不要 COMMIT ─────────────────────────
-- （想先只看數字的話，跑到這裡就 ROLLBACK。）
SELECT 'compset_rate_daily'        AS tbl, count(*) FROM compset_rate_daily
UNION ALL SELECT 'compset_rate_snapshots',   count(*) FROM compset_rate_snapshots
UNION ALL SELECT 'ohip_reservation',         count(*) FROM ohip_reservation
UNION ALL SELECT 'ohip_revenue_history',     count(*) FROM ohip_revenue_history
UNION ALL SELECT 'ohip_inventory_snapshot',  count(*) FROM ohip_inventory_snapshot
UNION ALL SELECT 'ohip_revenue_snapshot',    count(*) FROM ohip_revenue_snapshot
UNION ALL SELECT 'opera_departure_stay',     count(*) FROM opera_departure_stay
UNION ALL SELECT 'opera_revenue_daily',      count(*) FROM opera_revenue_daily
UNION ALL SELECT 'jinxu_ledger_entry',       count(*) FROM jinxu_ledger_entry
UNION ALL SELECT 'jinxu_reservation',        count(*) FROM jinxu_reservation
UNION ALL SELECT 'ota_reviews',              count(*) FROM ota_reviews;

-- ⚠️ ohip_inventory_snapshot / ohip_revenue_snapshot / ohip_snapshot_run
--    這三張是**每日快照**：OPERA 沒有「回到過去」的查詢參數，
--    刪掉就是永久遺失、無法重建。確認新專案已收到再往下。

-- ── 1. 競品分析 compset（7 張）──────────────────────────────────────────
DROP TABLE IF EXISTS compset_quota_grants     CASCADE;
DROP TABLE IF EXISTS compset_rate_daily       CASCADE;
DROP TABLE IF EXISTS compset_rate_snapshots   CASCADE;
DROP TABLE IF EXISTS compset_fetch_logs       CASCADE;
DROP TABLE IF EXISTS compset_hotels           CASCADE;
DROP TABLE IF EXISTS compset_subscriber_users CASCADE;   -- FK → users.id
DROP TABLE IF EXISTS compset_subscribers      CASCADE;

-- ── 2. OTA 口碑分析（7 張）──────────────────────────────────────────────
DROP TABLE IF EXISTS ota_analysis_cache   CASCADE;
DROP TABLE IF EXISTS ota_topic_candidates CASCADE;
DROP TABLE IF EXISTS ota_topic_rules      CASCADE;
DROP TABLE IF EXISTS ota_sync_logs        CASCADE;
DROP TABLE IF EXISTS ota_reviews          CASCADE;
DROP TABLE IF EXISTS ota_sources          CASCADE;
DROP TABLE IF EXISTS ota_platforms        CASCADE;

-- ── 3. 金旭 PMS 分析 jinxu（9 張）───────────────────────────────────────
DROP TABLE IF EXISTS jinxu_reservation_stay  CASCADE;
DROP TABLE IF EXISTS jinxu_reservation       CASCADE;
DROP TABLE IF EXISTS jinxu_resv_raw          CASCADE;
DROP TABLE IF EXISTS jinxu_ledger_entry      CASCADE;
DROP TABLE IF EXISTS jinxu_fcr02_raw         CASCADE;
DROP TABLE IF EXISTS jinxu_import_error      CASCADE;
DROP TABLE IF EXISTS jinxu_import_batch      CASCADE;
DROP TABLE IF EXISTS jinxu_subject_map       CASCADE;
DROP TABLE IF EXISTS jinxu_analysis_setting  CASCADE;

-- ── 4. 即時營運 / OHIP（12 張）──────────────────────────────────────────
DROP TABLE IF EXISTS ohip_block_allocation      CASCADE;
DROP TABLE IF EXISTS ohip_block                 CASCADE;
DROP TABLE IF EXISTS ohip_reservation_night     CASCADE;
DROP TABLE IF EXISTS ohip_reservation           CASCADE;
DROP TABLE IF EXISTS ohip_reservation_sync      CASCADE;
DROP TABLE IF EXISTS ohip_revenue_history       CASCADE;
DROP TABLE IF EXISTS ohip_revenue_history_sync  CASCADE;
DROP TABLE IF EXISTS ohip_revenue_snapshot      CASCADE;
DROP TABLE IF EXISTS ohip_inventory_snapshot    CASCADE;
DROP TABLE IF EXISTS ohip_snapshot_run          CASCADE;
DROP TABLE IF EXISTS ohip_async_cache           CASCADE;
DROP TABLE IF EXISTS ohip_call_log              CASCADE;

-- ── 5. 營運分析 OPERA（11 張）───────────────────────────────────────────
DROP TABLE IF EXISTS opera_forecast_daily        CASCADE;
DROP TABLE IF EXISTS opera_forecast_run          CASCADE;
DROP TABLE IF EXISTS opera_forecast_coefficient  CASCADE;
DROP TABLE IF EXISTS opera_event                 CASCADE;
DROP TABLE IF EXISTS opera_revenue_daily         CASCADE;
DROP TABLE IF EXISTS opera_history_forecast_raw  CASCADE;
DROP TABLE IF EXISTS opera_departure_stay        CASCADE;
DROP TABLE IF EXISTS opera_departure_raw         CASCADE;
DROP TABLE IF EXISTS opera_import_error          CASCADE;
DROP TABLE IF EXISTS opera_import_batch          CASCADE;
DROP TABLE IF EXISTS opera_analysis_setting      CASCADE;

-- ── 6. 權限資料列：PERMISSION_DEFINITIONS 已移除這 35 個 key，─────────────
--      role_permissions 裡的既有授權列會變成孤兒，一併清掉。
DELETE FROM role_permissions WHERE permission_key IN (
  -- 營運分析 10
  'opera_view','opera_revenue_view','opera_guest_view','opera_import','opera_admin',
  'opera_forecast_view','opera_segment_view','opera_reservation_view',
  'opera_pace_view','opera_event_admin',
  -- 即時營運 3
  'realtime_view','realtime_revenue','realtime_compare',
  -- 金旭分析 8
  'jinxu_view','jinxu_resv_view','jinxu_revenue_view','jinxu_payment_view',
  'jinxu_deposit_view','jinxu_import','jinxu_admin','jinxu_cancel_view',
  -- 口碑分析 7
  'ota_view','ota_reviews_view','ota_alerts_view','ota_trend_view',
  'ota_sources_admin','ota_topic_admin','ota_sync_run',
  -- 競品分析 7
  'compset_view','compset_matrix_view','compset_trend_view','compset_hotels_admin',
  'compset_settings_admin','compset_fetch_run','compset_subscriber_admin'
);

-- ── 7. 同步紀錄：sync_tool.py MODULES 已移除這 8 項 ─────────────────────
--      （歷史紀錄想留就把這段註解掉。）
DELETE FROM module_sync_log WHERE module_name IN (
  '市場區隔歷史回補','市場區隔增量同步','訂房歷史回補','訂房增量同步',
  'OHIP 每日快照','OTA 評論擷取','OTA 情緒分析','競品價格抓取'
);

-- 確認上面的數字與影響列數都合理後才 COMMIT；有疑慮就 ROLLBACK。
COMMIT;
-- ROLLBACK;
