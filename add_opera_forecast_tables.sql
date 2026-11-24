-- ============================================================================
-- OPERA 房價預測 — 索引建立腳本
-- 評估文件：docs/EVAL_opera_rate_forecasting.md §9.1
-- 建立日期：2026-08-05
--
-- 資料表本身由 SQLAlchemy Base.metadata.create_all() 建立
-- （main.py 已 import app.models.opera_forecast），本腳本只負責
-- create_all 不會產生的複合索引與唯一索引。
--
-- ⚠️ 不要單獨執行這支 SQL。若資料表還沒建立會噴 no such table。
--    請改跑：python apply_opera_forecast_migration.py
--    （那支會先依 model 定義建表，再套用本腳本）
--
-- 全部使用 IF NOT EXISTS，可重複執行。
-- ============================================================================

-- ── 事件月曆 ────────────────────────────────────────────────────────────────
-- 主要查詢型態：「某日期落在哪些啟用中的事件區間內」
CREATE INDEX IF NOT EXISTS idx_opera_event_range
  ON opera_event(property_code, is_active, start_date, end_date);

-- 學習事件係數時要把同名／同類事件的歷次紀錄抓在一起
CREATE INDEX IF NOT EXISTS idx_opera_event_name
  ON opera_event(property_code, name, start_date);

CREATE INDEX IF NOT EXISTS idx_opera_event_category
  ON opera_event(property_code, category, start_date);


-- ── 預測係數 ────────────────────────────────────────────────────────────────
-- 唯一業務鍵：同一飯店的同一種係數只能有一筆
-- （否則重新估算會不斷長出新列，且不知道該用哪一筆）
CREATE UNIQUE INDEX IF NOT EXISTS idx_opera_fc_coef_key
  ON opera_forecast_coefficient(property_code, kind, coef_key, metric);


-- ── 預測執行紀錄 ────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_opera_fc_run_property
  ON opera_forecast_run(property_code, run_at);

CREATE INDEX IF NOT EXISTS idx_opera_fc_run_horizon
  ON opera_forecast_run(property_code, horizon_start, horizon_end);


-- ── 逐日預測結果 ────────────────────────────────────────────────────────────
-- 一次執行的同一天只能有一筆
CREATE UNIQUE INDEX IF NOT EXISTS idx_opera_fc_daily_run_date
  ON opera_forecast_daily(run_id, business_date);

-- 回填實際值時要用「日期」反查所有還沒比對過的預測
CREATE INDEX IF NOT EXISTS idx_opera_fc_daily_date
  ON opera_forecast_daily(property_code, business_date);
