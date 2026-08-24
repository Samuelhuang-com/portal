-- ═══════════════════════════════════════════════════════════════════════
-- OTA 口碑分析 — 平台清單改為資料驅動
-- 建立日期：2026-08-23   版本：v1.92.0
-- ═══════════════════════════════════════════════════════════════════════
-- ⚠️ 這支**其實可以不執行** —— `create_all()` 會自動建表，
--    而且 `ensure_builtin_platforms()` 會自我播種內建的五個平台。
--    照樣提供是因為正式區習慣先在 DB 端確認 schema。冪等，重跑無害。
--
-- 為什麼要這張表：使用者要加 Hotels.com、Trip.com、KKday……
-- 原本每加一個都要改程式重新部署。但新增平台不需要寫任何邏輯 ——
-- 有代碼／名稱／分制／網域就能建來源、匯入 CSV、跑分析、進統計。
-- 需要寫程式的只有「自動擷取器」，而那件事本來就未必做得到
-- （Tripadvisor、Expedia 都被站方擋）。
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS ota_platforms (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    -- ⚠️ 會寫進每一筆評論的 platform 欄位，而且是統計的分組鍵。
    --    建立後不可修改（service 層強制），改了歷史資料會變孤兒。
    code         VARCHAR(30)  NOT NULL,
    label        VARCHAR(50)  NOT NULL,
    score_scale  INTEGER      NOT NULL DEFAULT 10,
    -- 逗號分隔。填了才會擋「網址與平台對不上」，留空則不比對。
    domains      VARCHAR(300) NOT NULL DEFAULT '',
    note         VARCHAR(200) NOT NULL DEFAULT '',
    is_enabled   BOOLEAN      NOT NULL DEFAULT 1,
    is_builtin   BOOLEAN      NOT NULL DEFAULT 0,
    sort_order   INTEGER      NOT NULL DEFAULT 0,
    created_by   VARCHAR(36),
    created_at   DATETIME,
    updated_at   DATETIME
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ota_platform_code
    ON ota_platforms (code);

CREATE INDEX IF NOT EXISTS ix_ota_platform_enabled
    ON ota_platforms (is_enabled, sort_order);

-- 內建五個平台。⚠️ 用 INSERT OR IGNORE：已經被 ensure_builtin_platforms()
-- 播種過、或使用者改過顯示名稱的，都不覆蓋。
INSERT OR IGNORE INTO ota_platforms
    (code, label, score_scale, domains, is_builtin, sort_order)
VALUES
    ('booking',     'Booking.com', 10, 'booking.com', 1, 0),
    ('agoda',       'Agoda',       10, 'agoda.com',   1, 1),
    ('expedia',     'Expedia',     10, 'expedia.com,expedia.com.tw,expedia.co.jp', 1, 2),
    ('tripadvisor', 'Tripadvisor',  5, 'tripadvisor.com,tripadvisor.com.tw,tripadvisor.cn', 1, 3),
    ('google',      'Google',       5, 'google.com',  1, 4);
