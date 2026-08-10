-- 2026-07-14：hotel/periodic-maintenance 模組 Sheet 6+8 → Sheet 11 遷移
-- 為 pm_batch_item 補上 Sheet 11 新增欄位（images_json / repair_hours）。
-- 比照 2026-07-13 的 add_mall_pm_sheet24_columns.sql 同一模式。
--
-- 執行對象：backend/.env 指定的執行期 DB（通常是 C:\portal_data\portal.db），
-- 不是 OneDrive 專案資料夾內的任何檔案。SQLAlchemy 的 create_all() 不會幫
-- 已存在的資料表補欄位，需要手動執行本檔案（或用等效的 DB 工具）。
--
-- 冪等性：SQLite 的 ALTER TABLE ADD COLUMN 若欄位已存在會報錯而非略過，
-- 重複執行前請先確認欄位是否已加過（例如用 PRAGMA table_info(pm_batch_item);）。

ALTER TABLE pm_batch_item ADD COLUMN images_json TEXT;
ALTER TABLE pm_batch_item ADD COLUMN repair_hours REAL;
