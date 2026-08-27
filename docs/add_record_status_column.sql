-- 2026-08-26  報修模組新增 record_status 欄位（Ragic「狀態」欄：結案／待辦／作廢）
-- 對應程式碼：LuqunRepairCase.record_status / DazhiRepairCase.record_status
-- 執行後必須重跑一次 Ragic 同步，欄位才會有值。
-- 建議改用 add_record_status_column.py（有預覽模式、可重複執行不報錯）。

ALTER TABLE luqun_repair_case ADD COLUMN record_status VARCHAR(50) DEFAULT "";
ALTER TABLE dazhi_repair_case ADD COLUMN record_status VARCHAR(50) DEFAULT "";
