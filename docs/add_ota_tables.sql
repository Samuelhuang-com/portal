-- ============================================================================
-- OTA 口碑分析模組 — 建表 SQL
-- 對應規格書：docs/SPEC_ota_reviews.md
-- 建立日期：2026-08-21
-- 適用資料庫：portal.db（SQLite）
--
-- 【使用時機】
--   SQLAlchemy 的 create_all() 會自動建立這些表與 __table_args__ 內的索引，
--   正常情況下「不需要」執行本檔。本檔用於：
--     1. 既有 DB 需手動補建（create_all 不會 ALTER 既有表）
--     2. 正式區想先確認 schema 再上線
--     3. 索引調整（create_all 不會補建後來新增的索引）
--
-- 【執行方式】
--   sqlite3 C:\Portal_Data\portal.db < docs\add_ota_tables.sql
--   ⚠️ 執行前務必備份 portal.db
--
-- 所有語句皆為 IF NOT EXISTS，重複執行安全。
-- ============================================================================

BEGIN TRANSACTION;

-- ── 1. OTA 來源設定 ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ota_sources (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    hotel_code         VARCHAR(20)  NOT NULL DEFAULT '',
    hotel_name         VARCHAR(50)  NOT NULL DEFAULT '',
    platform           VARCHAR(20)  NOT NULL DEFAULT '',
    url                VARCHAR(500) NOT NULL,
    score_scale        INTEGER      NOT NULL DEFAULT 10,
    is_enabled         BOOLEAN      NOT NULL DEFAULT 1,
    max_pages          INTEGER      NOT NULL DEFAULT 20,
    overall_score      NUMERIC(3,1),
    overall_score_10   NUMERIC(3,1),
    review_count_site  INTEGER,
    last_sync_at       DATETIME,
    last_status        VARCHAR(20)  NOT NULL DEFAULT 'never',
    last_message       VARCHAR(500) NOT NULL DEFAULT '',
    sort_order         INTEGER      NOT NULL DEFAULT 0,
    created_at         DATETIME,
    updated_at         DATETIME,
    CONSTRAINT uq_ota_source_url UNIQUE (url)
);
CREATE INDEX IF NOT EXISTS ix_ota_source_hotel    ON ota_sources(hotel_code);
CREATE INDEX IF NOT EXISTS ix_ota_source_platform ON ota_sources(platform);

-- ── 2. 同步批次紀錄 ─────────────────────────────────────────────────────────
-- 先於 ota_reviews 建立：reviews.sync_log_id 參照本表
CREATE TABLE IF NOT EXISTS ota_sync_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id       INTEGER NOT NULL REFERENCES ota_sources(id) ON DELETE RESTRICT,
    trigger_type    VARCHAR(10)   NOT NULL DEFAULT 'schedule',
    started_at      DATETIME,
    completed_at    DATETIME,
    status          VARCHAR(20)   NOT NULL DEFAULT 'running',
    pages_fetched   INTEGER       NOT NULL DEFAULT 0,
    found_count     INTEGER       NOT NULL DEFAULT 0,
    inserted_count  INTEGER       NOT NULL DEFAULT 0,
    updated_count   INTEGER       NOT NULL DEFAULT 0,
    skipped_count   INTEGER       NOT NULL DEFAULT 0,
    warnings_json   TEXT,
    error_message   VARCHAR(1000) NOT NULL DEFAULT '',
    duration_ms     INTEGER,
    triggered_by    VARCHAR(36),
    -- 2026-08-24：誰在跑這一列。用來回收「中斷未收尾」的孤兒 running。
    -- status='running' 一寫進來就 commit，收尾卻只在 except Exception 裡 ——
    -- Ctrl-C（KeyboardInterrupt 不是 Exception）、行程被砍、後端重啟都不經過它，
    -- 剩下的孤兒會讓 POST /sync/run 永遠回 409，整個模組同步不了。
    -- 有 host+pid 才能問「那個行程還在不在」，而不是靠猜逾時。
    -- ⚠️ 既有 DB 請改用下方的 ALTER（後端啟動時也會自動補）。
    worker_host     VARCHAR(60)   NOT NULL DEFAULT '',
    worker_pid      INTEGER
);
CREATE INDEX IF NOT EXISTS ix_ota_synclog_source ON ota_sync_logs(source_id, started_at);
CREATE INDEX IF NOT EXISTS ix_ota_synclog_status ON ota_sync_logs(status);

-- ── 3. 評論主表 ─────────────────────────────────────────────────────────────
-- ⚠️ 慣例：日期一律 VARCHAR(10) 存 ISO 字串；缺值一律空字串不用 NULL
--    （唯一鍵與指紋計算會用到，NULL 在 SQLite 的唯一鍵行為與空字串不同）
CREATE TABLE IF NOT EXISTS ota_reviews (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id          INTEGER NOT NULL REFERENCES ota_sources(id) ON DELETE RESTRICT,
    hotel_code         VARCHAR(20)  NOT NULL DEFAULT '',
    platform           VARCHAR(20)  NOT NULL DEFAULT '',
    external_id        VARCHAR(200) NOT NULL DEFAULT '',
    fingerprint        VARCHAR(64)  NOT NULL,
    cross_fingerprint  VARCHAR(64)  NOT NULL DEFAULT '',
    is_duplicate       BOOLEAN      NOT NULL DEFAULT 0,

    author             VARCHAR(100) NOT NULL DEFAULT '匿名旅客',
    nationality        VARCHAR(50)  NOT NULL DEFAULT '',
    traveler_type      VARCHAR(30)  NOT NULL DEFAULT '',
    room_type          VARCHAR(100) NOT NULL DEFAULT '',
    nights             INTEGER,

    score_raw          NUMERIC(3,1),
    score_scale        INTEGER      NOT NULL DEFAULT 10,
    score_10           NUMERIC(3,1),

    title              VARCHAR(300) NOT NULL DEFAULT '',
    positive_text      TEXT         NOT NULL DEFAULT '',
    negative_text      TEXT         NOT NULL DEFAULT '',
    comment            TEXT         NOT NULL DEFAULT '',

    review_date        VARCHAR(10)  NOT NULL DEFAULT '',
    review_month       VARCHAR(7)   NOT NULL DEFAULT '',
    stay_month         VARCHAR(7)   NOT NULL DEFAULT '',
    review_url         VARCHAR(500) NOT NULL DEFAULT '',

    sentiment_label    VARCHAR(10)  NOT NULL DEFAULT '',
    sentiment_score    NUMERIC(3,2),
    sentiment_engine   VARCHAR(10)  NOT NULL DEFAULT '',
    topics_json        TEXT,

    is_alert           BOOLEAN      NOT NULL DEFAULT 0,
    alert_status       VARCHAR(20)  NOT NULL DEFAULT 'open',
    alert_note         TEXT         NOT NULL DEFAULT '',
    alert_handler_id   VARCHAR(36),
    alert_handled_at   DATETIME,

    raw_json           TEXT,
    sync_log_id        INTEGER,
    fetched_at         DATETIME,
    analyzed_at        DATETIME,

    CONSTRAINT uq_ota_review_src_fp UNIQUE (source_id, fingerprint)
);
CREATE INDEX IF NOT EXISTS ix_ota_review_hotel_month    ON ota_reviews(hotel_code, review_month);
CREATE INDEX IF NOT EXISTS ix_ota_review_platform_date  ON ota_reviews(platform, review_date);
CREATE INDEX IF NOT EXISTS ix_ota_review_alert          ON ota_reviews(is_alert, alert_status);
CREATE INDEX IF NOT EXISTS ix_ota_review_pending        ON ota_reviews(analyzed_at);
CREATE INDEX IF NOT EXISTS ix_ota_review_cross_fp       ON ota_reviews(cross_fingerprint);
CREATE INDEX IF NOT EXISTS ix_ota_review_sentiment      ON ota_reviews(sentiment_label);
CREATE INDEX IF NOT EXISTS ix_ota_review_date           ON ota_reviews(review_date);
CREATE INDEX IF NOT EXISTS ix_ota_review_source         ON ota_reviews(source_id);

-- ── 4. 主題關鍵字字典 ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ota_topic_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    topic       VARCHAR(30) NOT NULL,
    keyword     VARCHAR(50) NOT NULL,
    polarity    VARCHAR(10) NOT NULL DEFAULT 'negative',
    weight      INTEGER     NOT NULL DEFAULT 1,
    is_enabled  BOOLEAN     NOT NULL DEFAULT 1,
    is_builtin  BOOLEAN     NOT NULL DEFAULT 0,
    created_by  VARCHAR(36),
    created_at  DATETIME,
    updated_at  DATETIME,
    CONSTRAINT uq_ota_topic_rule UNIQUE (topic, keyword, polarity)
);
CREATE INDEX IF NOT EXISTS ix_ota_topic_rule_topic ON ota_topic_rules(topic, is_enabled);

-- ── 5. AI 補判快取 ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ota_analysis_cache (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash     VARCHAR(64) NOT NULL,
    sentiment_label  VARCHAR(10) NOT NULL DEFAULT '',
    sentiment_score  NUMERIC(3,2),
    topics_json      TEXT,
    model            VARCHAR(50) NOT NULL DEFAULT '',
    tokens_used      INTEGER     NOT NULL DEFAULT 0,
    created_at       DATETIME,
    CONSTRAINT uq_ota_cache_hash UNIQUE (content_hash)
);

COMMIT;

-- ============================================================================
-- 內建主題字典種子資料
-- 說明：is_builtin=1 的詞在前端不可刪除，只能停用（is_enabled=0）。
--       重複執行安全（唯一鍵 topic+keyword+polarity + INSERT OR IGNORE）。
-- ============================================================================
BEGIN TRANSACTION;

INSERT OR IGNORE INTO ota_topic_rules (topic, keyword, polarity, is_builtin, created_at) VALUES
('清潔','髒','negative',1,datetime('now','localtime')),
('清潔','灰塵','negative',1,datetime('now','localtime')),
('清潔','霉','negative',1,datetime('now','localtime')),
('清潔','頭髮','negative',1,datetime('now','localtime')),
('清潔','蟑螂','negative',1,datetime('now','localtime')),
('清潔','沒打掃','negative',1,datetime('now','localtime')),
('清潔','不乾淨','negative',1,datetime('now','localtime')),
('清潔','污漬','negative',1,datetime('now','localtime')),
('清潔','乾淨','positive',1,datetime('now','localtime')),
('清潔','整潔','positive',1,datetime('now','localtime')),
('清潔','一塵不染','positive',1,datetime('now','localtime')),
('隔音','吵','negative',1,datetime('now','localtime')),
('隔音','噪音','negative',1,datetime('now','localtime')),
('隔音','隔音差','negative',1,datetime('now','localtime')),
('隔音','隔音不好','negative',1,datetime('now','localtime')),
('隔音','聽得到','negative',1,datetime('now','localtime')),
('隔音','施工','negative',1,datetime('now','localtime')),
('隔音','安靜','positive',1,datetime('now','localtime')),
('隔音','隔音好','positive',1,datetime('now','localtime')),
('隔音','很好睡','positive',1,datetime('now','localtime')),
-- ⚠️ 2026-08-24：原本是裸詞「態度」，「服務人員態度很好」也會判成負面。
-- 純名詞不帶褒貶，必須帶著評價詞一起收（同「很方便」的教訓）。
('服務','態度差','negative',1,datetime('now','localtime')),
('服務','態度不好','negative',1,datetime('now','localtime')),
('服務','態度惡劣','negative',1,datetime('now','localtime')),
('服務','態度好','positive',1,datetime('now','localtime')),
('服務','態度佳','positive',1,datetime('now','localtime')),
('服務','冷漠','negative',1,datetime('now','localtime')),
('服務','不理','negative',1,datetime('now','localtime')),
('服務','等很久','negative',1,datetime('now','localtime')),
('服務','擺臉色','negative',1,datetime('now','localtime')),
('服務','沒禮貌','negative',1,datetime('now','localtime')),
('服務','親切','positive',1,datetime('now','localtime')),
('服務','貼心','positive',1,datetime('now','localtime')),
('服務','熱情','positive',1,datetime('now','localtime')),
('服務','服務好','positive',1,datetime('now','localtime')),
('早餐','早餐難吃','negative',1,datetime('now','localtime')),
('早餐','選擇少','negative',1,datetime('now','localtime')),
('早餐','冷掉','negative',1,datetime('now','localtime')),
('早餐','種類不多','negative',1,datetime('now','localtime')),
('早餐','豐盛','positive',1,datetime('now','localtime')),
('早餐','早餐好吃','positive',1,datetime('now','localtime')),
('早餐','選擇多','positive',1,datetime('now','localtime')),
('設備','故障','negative',1,datetime('now','localtime')),
('設備','老舊','negative',1,datetime('now','localtime')),
-- ⚠️ 2026-08-24：原本是裸詞「水壓」，「水壓很強」是稱讚卻判成負面。
('設備','水壓小','negative',1,datetime('now','localtime')),
('設備','水壓不足','negative',1,datetime('now','localtime')),
('設備','水壓弱','negative',1,datetime('now','localtime')),
('設備','水壓強','positive',1,datetime('now','localtime')),
('設備','水壓足','positive',1,datetime('now','localtime')),
('設備','沒熱水','negative',1,datetime('now','localtime')),
('設備','冷氣不冷','negative',1,datetime('now','localtime')),
('設備','壞掉','negative',1,datetime('now','localtime')),
('設備','設備齊全','positive',1,datetime('now','localtime')),
('設備','很新','positive',1,datetime('now','localtime')),
('房間','房間小','negative',1,datetime('now','localtime')),
('房間','很暗','negative',1,datetime('now','localtime')),
('房間','壓迫','negative',1,datetime('now','localtime')),
('房間','床硬','negative',1,datetime('now','localtime')),
('房間','寬敞','positive',1,datetime('now','localtime')),
('房間','舒適','positive',1,datetime('now','localtime')),
('房間','採光好','positive',1,datetime('now','localtime')),
('位置','偏僻','negative',1,datetime('now','localtime')),
('位置','難找','negative',1,datetime('now','localtime')),
('位置','交通不便','negative',1,datetime('now','localtime')),
('位置','地點好','positive',1,datetime('now','localtime')),
('位置','近捷運','positive',1,datetime('now','localtime')),
('位置','很方便','positive',1,datetime('now','localtime')),
('價格','太貴','negative',1,datetime('now','localtime')),
('價格','不值','negative',1,datetime('now','localtime')),
('價格','CP值低','negative',1,datetime('now','localtime')),
('價格','划算','positive',1,datetime('now','localtime')),
('價格','超值','positive',1,datetime('now','localtime')),
('價格','CP值高','positive',1,datetime('now','localtime')),
('停車','沒車位','negative',1,datetime('now','localtime')),
('停車','停車困難','negative',1,datetime('now','localtime')),
('停車','停車方便','positive',1,datetime('now','localtime')),
('Wi-Fi','網路慢','negative',1,datetime('now','localtime')),
('Wi-Fi','連不上','negative',1,datetime('now','localtime')),
('Wi-Fi','訊號差','negative',1,datetime('now','localtime')),
('Wi-Fi','網速快','positive',1,datetime('now','localtime')),
('氣味','霉味','negative',1,datetime('now','localtime')),
('氣味','菸味','negative',1,datetime('now','localtime')),
('氣味','怪味','negative',1,datetime('now','localtime')),
('入住流程','排隊','negative',1,datetime('now','localtime')),
-- ⚠️ 2026-08-24：原本是裸詞「押金」，「押金退得很快」是稱讚。
--    收押金本身不是客訴，流程才是。
('入住流程','押金高','negative',1,datetime('now','localtime')),
('入住流程','押金太高','negative',1,datetime('now','localtime')),
('入住流程','押金沒退','negative',1,datetime('now','localtime')),
('入住流程','押金退很慢','negative',1,datetime('now','localtime')),
('入住流程','押金退得快','positive',1,datetime('now','localtime')),
('入住流程','入住快速','positive',1,datetime('now','localtime'));

COMMIT;

-- ============================================================================
-- 既有 DB 的字典清理（2026-08-24）
-- ============================================================================
-- ⚠️ 上面的 INSERT 是 OR IGNORE，**不會**刪掉既有的壞規則。
--    「態度」「水壓」「押金」三個裸詞留著就會繼續把稱讚判成負評。
--    後端啟動時 _retire_obsolete_builtin_rules() 會自動刪，
--    想手動執行的話跑這三行：
--
-- DELETE FROM ota_topic_rules WHERE is_builtin=1 AND topic='服務'     AND keyword='態度' AND polarity='negative';
-- DELETE FROM ota_topic_rules WHERE is_builtin=1 AND topic='設備'     AND keyword='水壓' AND polarity='negative';
-- DELETE FROM ota_topic_rules WHERE is_builtin=1 AND topic='入住流程' AND keyword='押金' AND polarity='negative';
--
-- ⚠️ 刪完要到 Portal 按「重新分析全部」，既有評論的 topics_json 才會更新。

-- ============================================================================
-- 既有 DB 的欄位補丁（2026-08-24）
-- ============================================================================
-- 上面的 CREATE TABLE 只對「還沒有這張表」的 DB 生效（IF NOT EXISTS）。
-- 已經有 ota_sync_logs 的 DB 請跑這兩行；SQLite 沒有 ADD COLUMN IF NOT EXISTS，
-- 已經有欄位時會報 "duplicate column name"，那個錯誤可以直接忽略。
--
-- ⚠️ 後端啟動時 _migrate_ota_synclog_worker() 會自動補，正常情況不需要手動執行。
--
-- ALTER TABLE ota_sync_logs ADD COLUMN worker_host VARCHAR(60) DEFAULT '';
-- ALTER TABLE ota_sync_logs ADD COLUMN worker_pid  INTEGER;

-- ============================================================================
-- 驗證：執行後應看到 5 張表與 77 筆內建字典
-- ============================================================================
-- SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ota_%';
-- SELECT topic, polarity, COUNT(*) FROM ota_topic_rules GROUP BY topic, polarity;
