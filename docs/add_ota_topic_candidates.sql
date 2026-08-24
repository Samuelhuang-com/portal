-- ═══════════════════════════════════════════════════════════════════════
-- OTA 口碑分析 — AI 發現的字典外主題候選
-- 建立日期：2026-08-23   版本：v1.91.0
-- ═══════════════════════════════════════════════════════════════════════
-- ⚠️ 這支**其實可以不執行** —— `create_all()` 會自動建立新表。
--    但正式區習慣先在 DB 端確認 schema，所以照樣提供，且寫成冪等的
--    （IF NOT EXISTS），重複執行不會出錯。
--
-- 這張表是「AI 發現 → 人工確認 → 進字典」閉環的中繼站。
-- 為什麼不直接寫進 ota_topic_rules：見 app/models/ota_review.py 的類別註解，
-- 簡言之是 ①AI 會產生同義詞爆炸 ②主題是統計的維度，悄悄多一個會讓
-- 月度趨勢圖憑空多一條沒人知道來源的線。
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS ota_topic_candidates (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               VARCHAR(30)  NOT NULL,
    description        VARCHAR(200) NOT NULL DEFAULT '',
    keywords_json      TEXT,
    hit_count          INTEGER      NOT NULL DEFAULT 0,
    neg_count          INTEGER      NOT NULL DEFAULT 0,
    -- ⚠️ 只存 review id 不存文字：評論的著作權不屬於我們，
    --    而且文字若被重新擷取覆寫，兩邊會不一致。
    sample_review_ids  TEXT,
    -- pending（待確認）/ accepted（已收進字典）/ rejected（否決，不再提示）
    status             VARCHAR(10)  NOT NULL DEFAULT 'pending',
    reviewed_by        VARCHAR(36),
    reviewed_at        DATETIME,
    first_seen_at      DATETIME,
    last_seen_at       DATETIME
);

-- 主題名唯一 —— 同一個議題重複出現要累加次數，不是各建一列
CREATE UNIQUE INDEX IF NOT EXISTS uq_ota_topic_candidate_name
    ON ota_topic_candidates (name);

-- 清單預設查 pending 並依出現次數排序，這個索引直接對應那個查詢
CREATE INDEX IF NOT EXISTS ix_ota_topic_candidate_status
    ON ota_topic_candidates (status, hit_count);
