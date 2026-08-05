-- ============================================================================
--  金旭 PMS 分析模組 — 索引 migration
--  規格書：docs/SPEC_jinxu_analytics.md §16
--
--  新環境由 create_all 自動建表，本腳本供**既有 DB** 補索引使用。
--  全部 IF NOT EXISTS，可重複執行。
--
--  ⚠️ 兩個 UNIQUE 索引是覆蓋規則（§8.2）的效能關鍵：每一列匯入都要先查一次
--     事實表。少了它們，40,706 次全表掃描會讓匯入從 30 秒變成數十分鐘。
-- ============================================================================

-- ── 分錄事實表 ──────────────────────────────────────────────────────────────
CREATE UNIQUE INDEX IF NOT EXISTS ix_jinxu_ledger_create_seq
    ON jinxu_ledger_entry (create_seq);
CREATE INDEX IF NOT EXISTS ix_jinxu_ledger_date_subject
    ON jinxu_ledger_entry (business_date, subject_code);
CREATE INDEX IF NOT EXISTS ix_jinxu_ledger_date_side
    ON jinxu_ledger_entry (business_date, subject_side);
CREATE INDEX IF NOT EXISTS ix_jinxu_ledger_booking
    ON jinxu_ledger_entry (booking_no);
CREATE INDEX IF NOT EXISTS ix_jinxu_ledger_batch
    ON jinxu_ledger_entry (batch_id);
CREATE INDEX IF NOT EXISTS ix_jinxu_ledger_room
    ON jinxu_ledger_entry (room_no, business_date);
CREATE INDEX IF NOT EXISTS ix_jinxu_ledger_operator
    ON jinxu_ledger_entry (operator_id, business_date);
-- 收入統計固定排除純記錄性分錄（J20）與非客房（J24）
CREATE INDEX IF NOT EXISTS ix_jinxu_ledger_memo_kind
    ON jinxu_ledger_entry (is_memo_only, room_kind, business_date);

-- ── 訂房事實表 ──────────────────────────────────────────────────────────────
CREATE UNIQUE INDEX IF NOT EXISTS ix_jinxu_resv_booking_no
    ON jinxu_reservation (booking_no);
-- 母體條件（is_cancelled=0 AND is_dummy=0）幾乎每個查詢都會帶，放最前面
CREATE INDEX IF NOT EXISTS ix_jinxu_resv_active_arrival
    ON jinxu_reservation (is_cancelled, is_dummy, arrival_date);
CREATE INDEX IF NOT EXISTS ix_jinxu_resv_arrival
    ON jinxu_reservation (arrival_date);
CREATE INDEX IF NOT EXISTS ix_jinxu_resv_departure
    ON jinxu_reservation (departure_date);
CREATE INDEX IF NOT EXISTS ix_jinxu_resv_company
    ON jinxu_reservation (company_name, arrival_date);
CREATE INDEX IF NOT EXISTS ix_jinxu_resv_status
    ON jinxu_reservation (status_code);
CREATE INDEX IF NOT EXISTS ix_jinxu_resv_batch
    ON jinxu_reservation (batch_id);
-- 回訪分析（J12/J13）：排除佔位符後依識別鍵分群
CREATE INDEX IF NOT EXISTS ix_jinxu_resv_identity
    ON jinxu_reservation (guest_is_placeholder, guest_identity_hash);

-- ── 住宿明細段 ──────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS ix_jinxu_stay_resv
    ON jinxu_reservation_stay (reservation_id);
CREATE INDEX IF NOT EXISTS ix_jinxu_stay_booking
    ON jinxu_reservation_stay (booking_no);
CREATE INDEX IF NOT EXISTS ix_jinxu_stay_roomtype
    ON jinxu_reservation_stay (room_type_code);

-- ── 原始層 ──────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS ix_jinxu_fcr02raw_batch  ON jinxu_fcr02_raw (batch_id);
CREATE INDEX IF NOT EXISTS ix_jinxu_fcr02raw_seq    ON jinxu_fcr02_raw (create_seq);
CREATE INDEX IF NOT EXISTS ix_jinxu_resvraw_batch   ON jinxu_resv_raw (batch_id);
CREATE INDEX IF NOT EXISTS ix_jinxu_resvraw_booking ON jinxu_resv_raw (booking_no);

-- ── 批次與錯誤 ──────────────────────────────────────────────────────────────
CREATE UNIQUE INDEX IF NOT EXISTS ix_jinxu_batch_sha256
    ON jinxu_import_batch (file_sha256);
CREATE INDEX IF NOT EXISTS ix_jinxu_batch_source_status
    ON jinxu_import_batch (source_type, status);
CREATE INDEX IF NOT EXISTS ix_jinxu_error_batch
    ON jinxu_import_error (batch_id, severity);

-- ── 科目對照 ────────────────────────────────────────────────────────────────
CREATE UNIQUE INDEX IF NOT EXISTS ix_jinxu_subject_code
    ON jinxu_subject_map (subject_code);

-- ── 分析設定 ────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS ix_jinxu_setting_key
    ON jinxu_analysis_setting (property_code, setting_key);
