-- ============================================================================
-- OPERA 營運分析模組 — 索引建立腳本
-- 規格書：docs/SPEC_opera_analytics.md §14
-- 建立日期：2026-08-04
--
-- 資料表本身由 SQLAlchemy Base.metadata.create_all() 自動建立
-- （main.py 已 import app.models.opera_import / opera_departure / opera_revenue），
-- 本腳本只負責 create_all 不會產生的複合索引與部分唯一索引。
--
-- 執行方式（正式區／測試區各執行一次）：
--     sqlite3 C:\Portal_Data\portal.db < add_opera_tables.sql
-- 或用 Python：
--     python -c "import sqlite3;sqlite3.connect(r'C:\Portal_Data\portal.db').executescript(open('add_opera_tables.sql',encoding='utf-8').read())"
--
-- 全部使用 IF NOT EXISTS，可重複執行。
-- ============================================================================

-- ── 匯入批次 ────────────────────────────────────────────────────────────────
-- 檔案層去重（規格書 §6.1）：相同 SHA-256 不得重複匯入。
-- 註：允許同一檔案有 FAILED 批次殘留，故不設 UNIQUE，改由 service 層檢查
--     「是否存在 status='COMMITTED' 的同 sha256 批次」。
CREATE INDEX IF NOT EXISTS idx_opera_batch_sha256
  ON opera_import_batch(file_sha256, status);

CREATE INDEX IF NOT EXISTS idx_opera_batch_source_status
  ON opera_import_batch(source_type, status, id);

CREATE INDEX IF NOT EXISTS idx_opera_batch_session
  ON opera_import_batch(session_id);

CREATE INDEX IF NOT EXISTS idx_opera_error_batch
  ON opera_import_error(batch_id, severity, id);


-- ── Departure 原始層 ────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_opera_dep_raw_batch
  ON opera_departure_raw(batch_id, source_row_no);

CREATE INDEX IF NOT EXISTS idx_opera_dep_raw_hash
  ON opera_departure_raw(row_hash);


-- ── Departure 住宿事實表 ────────────────────────────────────────────────────
-- 主要查詢路徑：期間篩選
CREATE INDEX IF NOT EXISTS idx_opera_stay_current_date
  ON opera_departure_stay(property_code, is_current, departure_date);

-- 住客回訪／長住分析
CREATE INDEX IF NOT EXISTS idx_opera_stay_guest
  ON opera_departure_stay(property_code, is_current, guest_identity_hash);

-- 通路分析
CREATE INDEX IF NOT EXISTS idx_opera_stay_channel
  ON opera_departure_stay(property_code, is_current, travel_agent_name, departure_date);

-- 房型 / Rate Code 分析
CREATE INDEX IF NOT EXISTS idx_opera_stay_category
  ON opera_departure_stay(property_code, is_current, room_category_label, departure_date);

CREATE INDEX IF NOT EXISTS idx_opera_stay_rate_code
  ON opera_departure_stay(property_code, is_current, rate_code, departure_date);

-- 版本管理：同一業務鍵只能有一筆 is_current=1（規格書 §6.3）
CREATE UNIQUE INDEX IF NOT EXISTS idx_opera_stay_record_key_current
  ON opera_departure_stay(record_key)
  WHERE is_current = 1;

-- 匯入時比對舊版本用
CREATE INDEX IF NOT EXISTS idx_opera_stay_batch
  ON opera_departure_stay(batch_id);


-- ── History and Forecast 原始層 ─────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_opera_hf_raw_batch
  ON opera_history_forecast_raw(batch_id, source_row_no);

CREATE INDEX IF NOT EXISTS idx_opera_hf_raw_hash
  ON opera_history_forecast_raw(row_hash);


-- ── 每日營收事實表 ──────────────────────────────────────────────────────────
-- 版本管理：property + record_type + business_date 只能有一筆 is_current=1（§6.4）
CREATE UNIQUE INDEX IF NOT EXISTS idx_opera_revenue_business_key_current
  ON opera_revenue_daily(property_code, record_type, business_date)
  WHERE is_current = 1;

-- 主要查詢路徑：期間 + 類型
CREATE INDEX IF NOT EXISTS idx_opera_revenue_date_type
  ON opera_revenue_daily(property_code, business_date, record_type, is_current);

CREATE INDEX IF NOT EXISTS idx_opera_revenue_batch
  ON opera_revenue_daily(batch_id);


-- ── 分析門檻設定 ────────────────────────────────────────────────────────────
CREATE UNIQUE INDEX IF NOT EXISTS idx_opera_setting_key
  ON opera_analysis_setting(property_code, setting_key);
