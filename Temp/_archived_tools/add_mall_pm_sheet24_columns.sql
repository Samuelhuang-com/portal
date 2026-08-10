-- mall/periodic-maintenance（商場週期保養）改用 Sheet24 為主要來源
-- 2026-07-13 新增，比照 full_bldg_pm（全棟例行維護）Sheet28 同日改版
--
-- 執行對象：C:\portal_data\portal.db（backend/.env 指定的「執行期」DB，
-- 不是 OneDrive 同步的 portal 專案資料夾！）
--
-- ⚠️ SQLAlchemy Base.metadata.create_all() 只會建立「缺少的資料表」，
-- 不會替既有資料表補欄位 / 建立缺少的資料表以外的東西時仍需注意：
--   1) mall_pm_batch_item 是既有資料表 → 新增 images_json 欄位「必須」手動 ALTER TABLE
--   2) mall_pm_item_worklog 是全新資料表 → 可以讓 create_all() 自動建立，
--      但這裡仍提供對應 CREATE TABLE 語句供你想在 SQL migration 一次到位時使用
--      （若已用 create_all() 建立過，重複執行本檔的 CREATE TABLE IF NOT EXISTS 是安全的）
--
-- 執行後「不需要」重啟後端（純 SQLite schema 變更即可生效於下一次查詢）；
-- 但若後端已經在執行中，建議仍重啟一次，確保 ORM session 快取的 schema 資訊更新。

-- 1) mall_pm_batch_item 新增 images_json 欄位（附圖，來源 Sheet24「圖片上傳」）
ALTER TABLE mall_pm_batch_item ADD COLUMN images_json TEXT;

-- 2) 新增 mall_pm_item_worklog 資料表（維修記錄明細，來源 Sheet24 巢狀子表格）
--    欄位與 full_bldg_pm_item_worklog 完全對應
CREATE TABLE IF NOT EXISTS mall_pm_item_worklog (
    ragic_id      VARCHAR(50)  NOT NULL PRIMARY KEY,
    item_ragic_id VARCHAR(50)  NOT NULL DEFAULT '',
    seq_no        INTEGER      NOT NULL DEFAULT 0,
    repair_note   TEXT         NOT NULL DEFAULT '',
    start_time    VARCHAR(30)  NOT NULL DEFAULT '',
    end_time      VARCHAR(30)  NOT NULL DEFAULT '',
    staff_name    VARCHAR(100) NOT NULL DEFAULT '',
    synced_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 驗證（執行完以上兩步後可用這兩句確認欄位/資料表都已建立）：
-- PRAGMA table_info(mall_pm_batch_item);
-- PRAGMA table_info(mall_pm_item_worklog);
