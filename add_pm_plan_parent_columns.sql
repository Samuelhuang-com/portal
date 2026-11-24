-- 2026-11-24 飯店週期保養主管排定（pm_plan_item）：母項名稱／項目(母)／批次編號（PostgreSQL）
-- 新增欄位，預設空字串，不影響既有資料；執行後需重新同步一次主管排定（Sheet 36/35/33）以寫入值。
ALTER TABLE pm_plan_item ADD COLUMN IF NOT EXISTS batch_no VARCHAR(50) NOT NULL DEFAULT '';
ALTER TABLE pm_plan_item ADD COLUMN IF NOT EXISTS parent_no VARCHAR(50) NOT NULL DEFAULT '';
ALTER TABLE pm_plan_item ADD COLUMN IF NOT EXISTS parent_name VARCHAR(200) NOT NULL DEFAULT '';
