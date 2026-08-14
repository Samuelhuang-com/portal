-- 2026-08-14：合約模組新增「解約日」欄位 migration
-- 為 contracts 表新增 termination_date 欄位，記錄合約提前終止的實際解約日
-- （與既有 end_date「到期日」分開：end_date 是原訂合約期間，termination_date
-- 只在提前解約時才會填寫，未提前解約者維持 NULL）。
--
-- 執行對象：backend/.env 指定的執行期 DB（通常是 C:\Portal_Data\portal.db），
-- 不是 OneDrive 專案資料夾內的任何檔案。SQLAlchemy 的 create_all() 不會幫
-- 已存在的資料表補欄位，需要手動執行本檔案（或用等效的 DB 工具）。
--
-- 冪等性：SQLite 的 ALTER TABLE ADD COLUMN 若欄位已存在會報錯而非略過，
-- 重複執行前請先確認欄位是否已加過（例如用 PRAGMA table_info(contracts);）。
--
-- 欄位為 nullable，不影響既有資料列（既有合約的 termination_date 皆為 NULL，
-- 代表「非提前解約」，符合預期）。

ALTER TABLE contracts ADD COLUMN termination_date DATE;
