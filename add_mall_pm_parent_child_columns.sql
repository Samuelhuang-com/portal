-- 2026-10-28 商場週期保養：Sheet24 項目(母)／項目(子) 欄位（PostgreSQL）
-- 新增 nullable 欄位，不影響既有資料；執行後需重新同步一次以寫入值。
ALTER TABLE mall_pm_batch_item ADD COLUMN IF NOT EXISTS parent_no VARCHAR(50);
ALTER TABLE mall_pm_batch_item ADD COLUMN IF NOT EXISTS child_no VARCHAR(50);
