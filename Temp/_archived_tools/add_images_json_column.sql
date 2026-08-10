-- 執行位置：C:\portal_data\portal.db
-- 用途：全棟例行維護新增「附圖」支援，需要在 full_bldg_pm_batch_item 表新增一個欄位。
--
-- ⚠️ 必須在重啟 backend 之前執行這一支，否則同步或查詢會噴
--    "no such column: images_json" 錯誤 —— SQLAlchemy 的 create_all() 只會建立
--    「不存在的資料表」，不會幫已存在的表補新欄位，這步驟一定要手動跑。
--
-- 建議先備份 C:\portal_data\portal.db（直接複製檔案即可）。

ALTER TABLE full_bldg_pm_batch_item ADD COLUMN images_json TEXT;

-- 執行後可用下面查詢確認欄位已存在（不會報錯即代表成功，新欄位預設值為 NULL）：
-- SELECT ragic_id, images_json FROM full_bldg_pm_batch_item LIMIT 1;
