-- 2026-07-21：合約模組「原合約複製續約 + 上下層級查詢」migration
-- 為 contracts 表新增 renewed_from_contract_id 欄位，記錄這份合約是複製自哪份原合約
-- （用於合約明細「上下層級」TAB 沿續約鏈往上溯源／往下查詢）。
--
-- 執行對象：backend/.env 指定的執行期 DB（通常是 C:\Portal_Data\portal.db），
-- 不是 OneDrive 專案資料夾內的任何檔案。SQLAlchemy 的 create_all() 不會幫
-- 已存在的資料表補欄位，需要手動執行本檔案（或用等效的 DB 工具）。
--
-- 冪等性：SQLite 的 ALTER TABLE ADD COLUMN 若欄位已存在會報錯而非略過，
-- 重複執行前請先確認欄位是否已加過（例如用 PRAGMA table_info(contracts);）。
--
-- 欄位為 nullable，不影響既有資料列（既有合約的 renewed_from_contract_id 皆為 NULL，
-- 代表「非續約複製產生」，符合預期）。

ALTER TABLE contracts ADD COLUMN renewed_from_contract_id VARCHAR(50) REFERENCES contracts(contract_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_contract_renewed_from ON contracts(renewed_from_contract_id);
