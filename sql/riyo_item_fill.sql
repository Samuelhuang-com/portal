-- 日曜（OU）料號主檔補正 — 主檔（廠商／會計科目／部門）補齊後執行。可重複執行，不會產生重複資料。
-- 執行：psql -h <主機> -U <使用者> -d <週採資料庫> -v ON_ERROR_STOP=1 -f riyo_item_fill.sql
BEGIN;

-- 1. 補寫之前因缺部門而略過的對照列（已存在者不重複寫入）
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0101001', '路燈旗(戶外帆布360dpi 60*220cm)', '駿湧有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), 450, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0101001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0101002', '1F走道旗(油性單透布 50*200cm）', '駿湧有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), 400, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0101002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0101003', '2F走道吊牌(PP霧+裁型 58*38cm）', '駿湧有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), 120, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0101003'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0201001', '1F地貼(R膠+霧PVC 299*90cm）', '萬視達廣告設計有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='萬視達廣告設計有限公司' LIMIT 1), 900, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0201001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0201002', '2F地貼(R膠+霧PVC 270*45cm）', '萬視達廣告設計有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='萬視達廣告設計有限公司' LIMIT 1), 420, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0201002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0202001', '內側電梯貼(霧PVC 100*30cm）', '萬視達廣告設計有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='萬視達廣告設計有限公司' LIMIT 1), 120, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0202001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0202002', '外側電梯貼(霧PVC 108*11cm）', '萬視達廣告設計有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='萬視達廣告設計有限公司' LIMIT 1), 60, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0202002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0203001', '6F電梯牆-貼(霧PVC 222*210cm)', '萬視達廣告設計有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='萬視達廣告設計有限公司' LIMIT 1), 2340, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0203001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0203002', '6F電梯牆-板(合成板+霧PVC 222*210cm)', '駿湧有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), 1560, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0203002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0204001', '折扣板(合成板+霧PVC 44.5*63cm）', '駿湧有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), 180, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0204001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0204002', 'HG板(合成板+霧PVC 90*15cm）', '駿湧有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), 150, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0204002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0204003', '中横眉(合成板+霧PVC 250*50cm）', '駿湧有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), 630, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0204003'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0205001', '小花車(PP 82*50cm)', '駿湧有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), 175, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0205001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0205002', '大花車(PP 98*60cm)', '駿湧有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), 245, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0205002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'D0205003', '主題牆(PP 705*140cm)', '萬視達廣告設計有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='萬視達廣告設計有限公司' LIMIT 1), 3885, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-D0205003'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0101001', '日曜-彩色信封12開西式100g道林', '藍格印刷國際企業有限公思', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='藍格印刷國際企業有限公思' LIMIT 1), 0.8133, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0101001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0101001', '日曜-彩色信封12開西式100g道林', '藍格印刷國際企業有限公思', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='藍格印刷國際企業有限公思' LIMIT 1), 0.8133, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0101001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0101001', '日曜-彩色信封12開西式100g道林', '藍格印刷國際企業有限公思', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='藍格印刷國際企業有限公思' LIMIT 1), 0.8133, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0101001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0101001', '日曜-彩色信封12開西式100g道林', '藍格印刷國際企業有限公思', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='藍格印刷國際企業有限公思' LIMIT 1), 0.8133, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0101001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0101001', '日曜-彩色信封12開西式100g道林', '藍格印刷國際企業有限公思', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='藍格印刷國際企業有限公思' LIMIT 1), 0.8133, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0101001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0101001', '日曜-彩色信封12開西式100g道林', '藍格印刷國際企業有限公思', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='藍格印刷國際企業有限公思' LIMIT 1), 0.8133, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0101001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0101001', '日曜-彩色信封12開西式100g道林', '藍格印刷國際企業有限公思', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='藍格印刷國際企業有限公思' LIMIT 1), 0.8133, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0101001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0101001', '日曜-彩色信封12開西式100g道林', '藍格印刷國際企業有限公思', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='藍格印刷國際企業有限公思' LIMIT 1), 0.8133, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0101001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102001', '日曜-專櫃人員手冊 A5', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 20.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102001', '日曜-專櫃人員手冊 A5', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 20.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102001', '日曜-專櫃人員手冊 A5', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 20.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102001', '日曜-專櫃人員手冊 A5', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 20.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102001', '日曜-專櫃人員手冊 A5', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 20.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102001', '日曜-專櫃人員手冊 A5', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 20.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102001', '日曜-專櫃人員手冊 A5', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 20.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102001', '日曜-專櫃人員手冊 A5', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 20.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102002', '日曜-會員卡申請單', '湯圓形象設計工作室', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='湯圓形象設計工作室' LIMIT 1), 0.7, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102002', '日曜-會員卡申請單', '湯圓形象設計工作室', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='湯圓形象設計工作室' LIMIT 1), 0.7, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102002', '日曜-會員卡申請單', '湯圓形象設計工作室', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='湯圓形象設計工作室' LIMIT 1), 0.7, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102002', '日曜-會員卡申請單', '湯圓形象設計工作室', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='湯圓形象設計工作室' LIMIT 1), 0.7, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102002', '日曜-會員卡申請單', '湯圓形象設計工作室', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='湯圓形象設計工作室' LIMIT 1), 0.7, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102002', '日曜-會員卡申請單', '湯圓形象設計工作室', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='湯圓形象設計工作室' LIMIT 1), 0.7, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102002', '日曜-會員卡申請單', '湯圓形象設計工作室', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='湯圓形象設計工作室' LIMIT 1), 0.7, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102002', '日曜-會員卡申請單', '湯圓形象設計工作室', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='湯圓形象設計工作室' LIMIT 1), 0.7, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102003', '日曜-專櫃代班單', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 50, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102003'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102003', '日曜-專櫃代班單', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 50, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102003'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102003', '日曜-專櫃代班單', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 50, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102003'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102003', '日曜-專櫃代班單', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 50, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102003'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102003', '日曜-專櫃代班單', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 50, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102003'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102003', '日曜-專櫃代班單', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 50, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102003'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102003', '日曜-專櫃代班單', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 50, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102003', '日曜-專櫃代班單', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 50, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102003'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102004', '日曜-進場單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 99, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102004'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102004', '日曜-進場單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 99, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102004'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102004', '日曜-進場單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 99, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102004'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102004', '日曜-進場單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 99, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102004'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102004', '日曜-進場單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 99, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102004'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102004', '日曜-進場單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 99, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102004'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102004', '日曜-進場單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 99, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102004', '日曜-進場單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 99, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102004'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102005', '日曜-營業日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 31, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102005'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102005', '日曜-營業日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 31, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102005'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102005', '日曜-營業日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 31, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102005'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102005', '日曜-營業日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 31, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102005'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102005', '日曜-營業日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 31, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102005'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102005', '日曜-營業日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 31, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102005'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102005', '日曜-營業日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 31, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102005', '日曜-營業日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 31, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102005'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102006', '日曜-銷貨日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 28, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102006'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102006', '日曜-銷貨日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 28, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102006'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102006', '日曜-銷貨日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 28, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102006'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102006', '日曜-銷貨日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 28, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102006'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102006', '日曜-銷貨日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 28, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102006'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102006', '日曜-銷貨日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 28, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102006'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102006', '日曜-銷貨日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 28, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102006'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102006', '日曜-銷貨日報表A5(專櫃用)', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 28, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102006'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102007', '日曜-退稅單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 41, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102007'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102007', '日曜-退稅單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 41, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102007'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102007', '日曜-退稅單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 41, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102007'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102007', '日曜-退稅單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 41, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102007'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102007', '日曜-退稅單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 41, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102007'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102007', '日曜-退稅單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 41, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102007'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102007', '日曜-退稅單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 41, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102007'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0102007', '日曜-退稅單', '柏辰企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), 41, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621201' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-印刷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0102007'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103001', '日曜-綠色紙袋-大(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103001', '日曜-綠色紙袋-大(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103001', '日曜-綠色紙袋-大(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103001', '日曜-綠色紙袋-大(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103001', '日曜-綠色紙袋-大(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103001', '日曜-綠色紙袋-大(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103001', '日曜-綠色紙袋-大(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103001', '日曜-綠色紙袋-大(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103002', '日曜-綠色紙袋-中(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4.6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103002', '日曜-綠色紙袋-中(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4.6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103002', '日曜-綠色紙袋-中(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4.6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103002', '日曜-綠色紙袋-中(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4.6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103002', '日曜-綠色紙袋-中(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4.6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103002', '日曜-綠色紙袋-中(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4.6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103002', '日曜-綠色紙袋-中(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4.6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103002', '日曜-綠色紙袋-中(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4.6, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103003', '日曜-綠色紙袋-小(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103003'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103003', '日曜-綠色紙袋-小(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103003'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103003', '日曜-綠色紙袋-小(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103003'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103003', '日曜-綠色紙袋-小(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103003'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103003', '日曜-綠色紙袋-小(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103003'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103003', '日曜-綠色紙袋-小(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103003'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103003', '日曜-綠色紙袋-小(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0103003', '日曜-綠色紙袋-小(專櫃用)', '大裕紙袋股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), 4, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0103003'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104001', '日曜-塑膠袋-大(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 4.2, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104001', '日曜-塑膠袋-大(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 4.2, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104001', '日曜-塑膠袋-大(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 4.2, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104001', '日曜-塑膠袋-大(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 4.2, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104001', '日曜-塑膠袋-大(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 4.2, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104001', '日曜-塑膠袋-大(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 4.2, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104001', '日曜-塑膠袋-大(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 4.2, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104001', '日曜-塑膠袋-大(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 4.2, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104002', '日曜-塑膠袋-小(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 3, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104002', '日曜-塑膠袋-小(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 3, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104002', '日曜-塑膠袋-小(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 3, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104002', '日曜-塑膠袋-小(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 3, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104002', '日曜-塑膠袋-小(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 3, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104002', '日曜-塑膠袋-小(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 3, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104002', '日曜-塑膠袋-小(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 3, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0104002', '日曜-塑膠袋-小(專櫃用)', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 3, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0104002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201001', 'smartist 70g A4影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 73, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201001', 'smartist 70g A4影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 73, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201001', 'smartist 70g A4影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 73, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201001', 'smartist 70g A4影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 73, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201001', 'smartist 70g A4影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 73, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201001', 'smartist 70g A4影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 73, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201001', 'smartist 70g A4影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 73, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201001', 'smartist 70g A4影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 73, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201002', 'smartist 70g A3影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 113, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201002', 'smartist 70g A3影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 113, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201002', 'smartist 70g A3影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 113, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201002', 'smartist 70g A3影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 113, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201002', 'smartist 70g A3影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 113, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201002', 'smartist 70g A3影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 113, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201002', 'smartist 70g A3影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 113, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0201002', 'smartist 70g A3影印紙', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 113, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0201002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0202001', 'A4丹迪紙', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 47, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0202001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0202001', 'A4丹迪紙', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 47, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0202001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0202001', 'A4丹迪紙', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 47, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0202001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0202001', 'A4丹迪紙', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 47, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0202001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0202001', 'A4丹迪紙', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 47, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0202001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0202001', 'A4丹迪紙', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 47, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0202001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0202001', 'A4丹迪紙', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 47, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0202001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0202001', 'A4丹迪紙', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 47, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0202001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0301001', '國際/2號/鹼性電池 (2入/組)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 70, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0301001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0301001', '國際/2號/鹼性電池 (2入/組)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 70, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0301001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0301001', '國際/2號/鹼性電池 (2入/組)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 70, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0301001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0301001', '國際/2號/鹼性電池 (2入/組)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 70, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0301001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0301001', '國際/2號/鹼性電池 (2入/組)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 70, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0301001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0301001', '國際/2號/鹼性電池 (2入/組)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 70, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0301001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0301001', '國際/2號/鹼性電池 (2入/組)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 70, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0301001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0301001', '國際/2號/鹼性電池 (2入/組)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 70, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0301001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401001', '人棉布雙面膠帶20*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 155, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401001', '人棉布雙面膠帶20*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 155, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401001', '人棉布雙面膠帶20*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 155, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401001', '人棉布雙面膠帶20*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 155, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401001', '人棉布雙面膠帶20*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 155, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401001', '人棉布雙面膠帶20*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 155, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401001', '人棉布雙面膠帶20*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 155, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401001', '人棉布雙面膠帶20*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 155, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401002', '人棉布雙面膠帶10*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 75, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401002', '人棉布雙面膠帶10*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 75, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401002', '人棉布雙面膠帶10*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 75, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401002', '人棉布雙面膠帶10*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 75, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401002', '人棉布雙面膠帶10*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 75, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401002', '人棉布雙面膠帶10*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 75, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401002', '人棉布雙面膠帶10*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 75, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0401002', '人棉布雙面膠帶10*25M', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 75, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0401002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402001', '透明膠帶12MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402001', '透明膠帶12MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402001', '透明膠帶12MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402001', '透明膠帶12MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402001', '透明膠帶12MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402001', '透明膠帶12MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402001', '透明膠帶12MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402001', '透明膠帶12MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402002', '透明膠帶18MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402002', '透明膠帶18MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402002', '透明膠帶18MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402002', '透明膠帶18MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402002', '透明膠帶18MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402002', '透明膠帶18MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402002', '透明膠帶18MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402002', '透明膠帶18MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402003', '透明膠帶48MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 24, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402003'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402003', '透明膠帶48MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 24, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402003'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402003', '透明膠帶48MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 24, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402003'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402003', '透明膠帶48MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 24, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402003'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402003', '透明膠帶48MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 24, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402003'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402003', '透明膠帶48MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 24, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402003'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402003', '透明膠帶48MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 24, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0402003', '透明膠帶48MM 40Y', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 24, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0402003'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0403001', '2048R 強力防水布膠帶紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 90, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0403001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0403001', '2048R 強力防水布膠帶紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 90, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0403001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0403001', '2048R 強力防水布膠帶紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 90, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0403001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0403001', '2048R 強力防水布膠帶紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 90, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0403001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0403001', '2048R 強力防水布膠帶紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 90, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0403001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0403001', '2048R 強力防水布膠帶紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 90, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0403001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0403001', '2048R 強力防水布膠帶紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 90, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0403001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0403001', '2048R 強力防水布膠帶紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 90, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0403001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501001', '開明 100事務用帶 黑 45cm (45條一束)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 68, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501001', '開明 100事務用帶 黑 45cm (45條一束)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 68, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501001', '開明 100事務用帶 黑 45cm (45條一束)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 68, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501001', '開明 100事務用帶 黑 45cm (45條一束)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 68, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501001', '開明 100事務用帶 黑 45cm (45條一束)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 68, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501001', '開明 100事務用帶 黑 45cm (45條一束)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 68, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501001', '開明 100事務用帶 黑 45cm (45條一束)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 68, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501001', '開明 100事務用帶 黑 45cm (45條一束)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 68, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501002', '開明 240 事務用帶 黑 61cm (24條一束) (扁)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 72, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501002', '開明 240 事務用帶 黑 61cm (24條一束) (扁)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 72, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501002', '開明 240 事務用帶 黑 61cm (24條一束) (扁)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 72, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501002', '開明 240 事務用帶 黑 61cm (24條一束) (扁)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 72, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501002', '開明 240 事務用帶 黑 61cm (24條一束) (扁)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 72, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501002', '開明 240 事務用帶 黑 61cm (24條一束) (扁)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 72, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501002', '開明 240 事務用帶 黑 61cm (24條一束) (扁)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 72, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0501002', '開明 240 事務用帶 黑 61cm (24條一束) (扁)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 72, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0501002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601001', '10.16*10.16CM便利貼(副總用)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 43, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601001', '10.16*10.16CM便利貼(副總用)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 43, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601001', '10.16*10.16CM便利貼(副總用)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 43, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601001', '10.16*10.16CM便利貼(副總用)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 43, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601001', '10.16*10.16CM便利貼(副總用)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 43, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601001', '10.16*10.16CM便利貼(副總用)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 43, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601001', '10.16*10.16CM便利貼(副總用)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 43, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601001', '10.16*10.16CM便利貼(副總用)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 43, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601002', '7.6*7.6CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601002', '7.6*7.6CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601002', '7.6*7.6CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601002', '7.6*7.6CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601002', '7.6*7.6CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601002', '7.6*7.6CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601002', '7.6*7.6CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601002', '7.6*7.6CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601003', '7.5*5CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601003'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601003', '7.5*5CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601003'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601003', '7.5*5CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601003'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601003', '7.5*5CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601003'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601003', '7.5*5CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601003'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601003', '7.5*5CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601003'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601003', '7.5*5CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0601003', '7.5*5CM便利貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0601003'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701001', 'WL-1007自黏性標籤貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701001', 'WL-1007自黏性標籤貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701001', 'WL-1007自黏性標籤貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701001', 'WL-1007自黏性標籤貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701001', 'WL-1007自黏性標籤貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701001', 'WL-1007自黏性標籤貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701001', 'WL-1007自黏性標籤貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701001', 'WL-1007自黏性標籤貼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701002', 'WL-1017自黏性標籤貼(紅框)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701002', 'WL-1017自黏性標籤貼(紅框)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701002', 'WL-1017自黏性標籤貼(紅框)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701002', 'WL-1017自黏性標籤貼(紅框)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701002', 'WL-1017自黏性標籤貼(紅框)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701002', 'WL-1017自黏性標籤貼(紅框)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701002', 'WL-1017自黏性標籤貼(紅框)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0701002', 'WL-1017自黏性標籤貼(紅框)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 9.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0701002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702001', 'N次貼 66514 可再貼分類索引片 28*25MM 60片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 40, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702001', 'N次貼 66514 可再貼分類索引片 28*25MM 60片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 40, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702001', 'N次貼 66514 可再貼分類索引片 28*25MM 60片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 40, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702001', 'N次貼 66514 可再貼分類索引片 28*25MM 60片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 40, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702001', 'N次貼 66514 可再貼分類索引片 28*25MM 60片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 40, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702001', 'N次貼 66514 可再貼分類索引片 28*25MM 60片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 40, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702001', 'N次貼 66514 可再貼分類索引片 28*25MM 60片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 40, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702001', 'N次貼 66514 可再貼分類索引片 28*25MM 60片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 40, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702002', 'LONGDER龍德 LD-701 五彩雙面索引片 26*34mm,30片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702002', 'LONGDER龍德 LD-701 五彩雙面索引片 26*34mm,30片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702002', 'LONGDER龍德 LD-701 五彩雙面索引片 26*34mm,30片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702002', 'LONGDER龍德 LD-701 五彩雙面索引片 26*34mm,30片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702002', 'LONGDER龍德 LD-701 五彩雙面索引片 26*34mm,30片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702002', 'LONGDER龍德 LD-701 五彩雙面索引片 26*34mm,30片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702002', 'LONGDER龍德 LD-701 五彩雙面索引片 26*34mm,30片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0702002', 'LONGDER龍德 LD-701 五彩雙面索引片 26*34mm,30片/包', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0702002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0703001', '3M Post-it 583-9非抽取式-可再貼全彩標籤9色', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0703001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0703001', '3M Post-it 583-9非抽取式-可再貼全彩標籤9色', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0703001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0703001', '3M Post-it 583-9非抽取式-可再貼全彩標籤9色', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0703001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0703001', '3M Post-it 583-9非抽取式-可再貼全彩標籤9色', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0703001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0703001', '3M Post-it 583-9非抽取式-可再貼全彩標籤9色', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0703001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0703001', '3M Post-it 583-9非抽取式-可再貼全彩標籤9色', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0703001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0703001', '3M Post-it 583-9非抽取式-可再貼全彩標籤9色', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0703001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0703001', '3M Post-it 583-9非抽取式-可再貼全彩標籤9色', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0703001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0704001', '3M Scotch 680 (Sign Here)抽取式標籤2卡入超值包 Sign Here', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0704001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0704001', '3M Scotch 680 (Sign Here)抽取式標籤2卡入超值包 Sign Here', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0704001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0704001', '3M Scotch 680 (Sign Here)抽取式標籤2卡入超值包 Sign Here', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0704001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0704001', '3M Scotch 680 (Sign Here)抽取式標籤2卡入超值包 Sign Here', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0704001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0704001', '3M Scotch 680 (Sign Here)抽取式標籤2卡入超值包 Sign Here', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0704001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0704001', '3M Scotch 680 (Sign Here)抽取式標籤2卡入超值包 Sign Here', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0704001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0704001', '3M Scotch 680 (Sign Here)抽取式標籤2卡入超值包 Sign Here', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0704001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G0704001', '3M Scotch 680 (Sign Here)抽取式標籤2卡入超值包 Sign Here', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G0704001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001001', 'Pentel飛龍 S512螢光筆3.5mm 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001001', 'Pentel飛龍 S512螢光筆3.5mm 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001001', 'Pentel飛龍 S512螢光筆3.5mm 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001001', 'Pentel飛龍 S512螢光筆3.5mm 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001001', 'Pentel飛龍 S512螢光筆3.5mm 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001001', 'Pentel飛龍 S512螢光筆3.5mm 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001001', 'Pentel飛龍 S512螢光筆3.5mm 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001001', 'Pentel飛龍 S512螢光筆3.5mm 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001002', 'Pentel飛龍 S512螢光筆3.5mm 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001002', 'Pentel飛龍 S512螢光筆3.5mm 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001002', 'Pentel飛龍 S512螢光筆3.5mm 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001002', 'Pentel飛龍 S512螢光筆3.5mm 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001002', 'Pentel飛龍 S512螢光筆3.5mm 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001002', 'Pentel飛龍 S512螢光筆3.5mm 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001002', 'Pentel飛龍 S512螢光筆3.5mm 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001002', 'Pentel飛龍 S512螢光筆3.5mm 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001003', 'Pentel飛龍 S512螢光筆3.5mm 黃', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001003'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001003', 'Pentel飛龍 S512螢光筆3.5mm 黃', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001003'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001003', 'Pentel飛龍 S512螢光筆3.5mm 黃', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001003'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001003', 'Pentel飛龍 S512螢光筆3.5mm 黃', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001003'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001003', 'Pentel飛龍 S512螢光筆3.5mm 黃', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001003'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001003', 'Pentel飛龍 S512螢光筆3.5mm 黃', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001003'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001003', 'Pentel飛龍 S512螢光筆3.5mm 黃', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001003', 'Pentel飛龍 S512螢光筆3.5mm 黃', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001003'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001004', 'Pentel飛龍 S512螢光筆3.5mm 粉', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001004'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001004', 'Pentel飛龍 S512螢光筆3.5mm 粉', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001004'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001004', 'Pentel飛龍 S512螢光筆3.5mm 粉', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001004'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001004', 'Pentel飛龍 S512螢光筆3.5mm 粉', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001004'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001004', 'Pentel飛龍 S512螢光筆3.5mm 粉', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001004'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001004', 'Pentel飛龍 S512螢光筆3.5mm 粉', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001004'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001004', 'Pentel飛龍 S512螢光筆3.5mm 粉', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001004', 'Pentel飛龍 S512螢光筆3.5mm 粉', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001004'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001005', 'Pentel飛龍 S512螢光筆3.5mm 橘', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001005'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001005', 'Pentel飛龍 S512螢光筆3.5mm 橘', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001005'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001005', 'Pentel飛龍 S512螢光筆3.5mm 橘', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001005'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001005', 'Pentel飛龍 S512螢光筆3.5mm 橘', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001005'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001005', 'Pentel飛龍 S512螢光筆3.5mm 橘', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001005'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001005', 'Pentel飛龍 S512螢光筆3.5mm 橘', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001005'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001005', 'Pentel飛龍 S512螢光筆3.5mm 橘', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1001005', 'Pentel飛龍 S512螢光筆3.5mm 橘', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1001005'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002001', 'SKB IB-100自動中油筆0.5MM藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002001', 'SKB IB-100自動中油筆0.5MM藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002001', 'SKB IB-100自動中油筆0.5MM藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002001', 'SKB IB-100自動中油筆0.5MM藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002001', 'SKB IB-100自動中油筆0.5MM藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002001', 'SKB IB-100自動中油筆0.5MM藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002001', 'SKB IB-100自動中油筆0.5MM藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002001', 'SKB IB-100自動中油筆0.5MM藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002002', 'SKB IB-100自動中油筆0.5MM紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002002', 'SKB IB-100自動中油筆0.5MM紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002002', 'SKB IB-100自動中油筆0.5MM紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002002', 'SKB IB-100自動中油筆0.5MM紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002002', 'SKB IB-100自動中油筆0.5MM紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002002', 'SKB IB-100自動中油筆0.5MM紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002002', 'SKB IB-100自動中油筆0.5MM紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002002', 'SKB IB-100自動中油筆0.5MM紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002003', 'SKB IB-100自動中油筆0.5MM黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002003'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002003', 'SKB IB-100自動中油筆0.5MM黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002003'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002003', 'SKB IB-100自動中油筆0.5MM黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002003'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002003', 'SKB IB-100自動中油筆0.5MM黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002003'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002003', 'SKB IB-100自動中油筆0.5MM黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002003'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002003', 'SKB IB-100自動中油筆0.5MM黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002003'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002003', 'SKB IB-100自動中油筆0.5MM黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002003', 'SKB IB-100自動中油筆0.5MM黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 6.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002003'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002004', '雄獅 GL-533 速乾中性筆0.7藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002004'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002004', '雄獅 GL-533 速乾中性筆0.7藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002004'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002004', '雄獅 GL-533 速乾中性筆0.7藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002004'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002004', '雄獅 GL-533 速乾中性筆0.7藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002004'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002004', '雄獅 GL-533 速乾中性筆0.7藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002004'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002004', '雄獅 GL-533 速乾中性筆0.7藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002004'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002004', '雄獅 GL-533 速乾中性筆0.7藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002004', '雄獅 GL-533 速乾中性筆0.7藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002004'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002005', '雄獅 GL-533 速乾中性筆0.7紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002005'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002005', '雄獅 GL-533 速乾中性筆0.7紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002005'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002005', '雄獅 GL-533 速乾中性筆0.7紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002005'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002005', '雄獅 GL-533 速乾中性筆0.7紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002005'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002005', '雄獅 GL-533 速乾中性筆0.7紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002005'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002005', '雄獅 GL-533 速乾中性筆0.7紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002005'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002005', '雄獅 GL-533 速乾中性筆0.7紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002005', '雄獅 GL-533 速乾中性筆0.7紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002005'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002006', '雄獅 GL-533 速乾中性筆0.7黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002006'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002006', '雄獅 GL-533 速乾中性筆0.7黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002006'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002006', '雄獅 GL-533 速乾中性筆0.7黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002006'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002006', '雄獅 GL-533 速乾中性筆0.7黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002006'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002006', '雄獅 GL-533 速乾中性筆0.7黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002006'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002006', '雄獅 GL-533 速乾中性筆0.7黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002006'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002006', '雄獅 GL-533 速乾中性筆0.7黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002006'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002006', '雄獅 GL-533 速乾中性筆0.7黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002006'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002007', 'UNI三菱 UM-151 0.38超細鋼珠筆 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002007'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002007', 'UNI三菱 UM-151 0.38超細鋼珠筆 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002007'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002007', 'UNI三菱 UM-151 0.38超細鋼珠筆 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002007'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002007', 'UNI三菱 UM-151 0.38超細鋼珠筆 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002007'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002007', 'UNI三菱 UM-151 0.38超細鋼珠筆 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002007'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002007', 'UNI三菱 UM-151 0.38超細鋼珠筆 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002007'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002007', 'UNI三菱 UM-151 0.38超細鋼珠筆 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002007'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002007', 'UNI三菱 UM-151 0.38超細鋼珠筆 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002007'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002008', 'UNI三菱 UM-151 0.38超細鋼珠筆 黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002008'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002008', 'UNI三菱 UM-151 0.38超細鋼珠筆 黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002008'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002008', 'UNI三菱 UM-151 0.38超細鋼珠筆 黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002008'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002008', 'UNI三菱 UM-151 0.38超細鋼珠筆 黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002008'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002008', 'UNI三菱 UM-151 0.38超細鋼珠筆 黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002008'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002008', 'UNI三菱 UM-151 0.38超細鋼珠筆 黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002008'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002008', 'UNI三菱 UM-151 0.38超細鋼珠筆 黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002008'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1002008', 'UNI三菱 UM-151 0.38超細鋼珠筆 黑', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1002008'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004001', 'Pentel飛龍 A105 自動鉛筆0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 23, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004001', 'Pentel飛龍 A105 自動鉛筆0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 23, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004001', 'Pentel飛龍 A105 自動鉛筆0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 23, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004001', 'Pentel飛龍 A105 自動鉛筆0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 23, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004001', 'Pentel飛龍 A105 自動鉛筆0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 23, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004001', 'Pentel飛龍 A105 自動鉛筆0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 23, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004001', 'Pentel飛龍 A105 自動鉛筆0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 23, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004001', 'Pentel飛龍 A105 自動鉛筆0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 23, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004002', 'Pentel飛龍 C205-HB 自動鉛筆芯0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 28.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004002', 'Pentel飛龍 C205-HB 自動鉛筆芯0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 28.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004002', 'Pentel飛龍 C205-HB 自動鉛筆芯0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 28.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004002', 'Pentel飛龍 C205-HB 自動鉛筆芯0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 28.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004002', 'Pentel飛龍 C205-HB 自動鉛筆芯0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 28.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004002', 'Pentel飛龍 C205-HB 自動鉛筆芯0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 28.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004002', 'Pentel飛龍 C205-HB 自動鉛筆芯0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 28.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1004002', 'Pentel飛龍 C205-HB 自動鉛筆芯0.5mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 28.5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1004002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101001', 'PLUS普樂士 WH-605 滾輪修正帶5mm*6m 白綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 35, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101001', 'PLUS普樂士 WH-605 滾輪修正帶5mm*6m 白綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 35, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101001', 'PLUS普樂士 WH-605 滾輪修正帶5mm*6m 白綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 35, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101001', 'PLUS普樂士 WH-605 滾輪修正帶5mm*6m 白綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 35, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101001', 'PLUS普樂士 WH-605 滾輪修正帶5mm*6m 白綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 35, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101001', 'PLUS普樂士 WH-605 滾輪修正帶5mm*6m 白綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 35, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101001', 'PLUS普樂士 WH-605 滾輪修正帶5mm*6m 白綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 35, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101001', 'PLUS普樂士 WH-605 滾輪修正帶5mm*6m 白綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 35, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101002', 'PLUS普樂士 WH-605 滾輪修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101002', 'PLUS普樂士 WH-605 滾輪修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101002', 'PLUS普樂士 WH-605 滾輪修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101002', 'PLUS普樂士 WH-605 滾輪修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101002', 'PLUS普樂士 WH-605 滾輪修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101002', 'PLUS普樂士 WH-605 滾輪修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101002', 'PLUS普樂士 WH-605 滾輪修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101002', 'PLUS普樂士 WH-605 滾輪修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101005', 'SDI手牌 CT-205 iPUSH輕鬆按修正帶5mm*6M 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 45, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101005'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101005', 'SDI手牌 CT-205 iPUSH輕鬆按修正帶5mm*6M 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 45, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101005'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101005', 'SDI手牌 CT-205 iPUSH輕鬆按修正帶5mm*6M 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 45, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101005'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101005', 'SDI手牌 CT-205 iPUSH輕鬆按修正帶5mm*6M 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 45, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101005'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101005', 'SDI手牌 CT-205 iPUSH輕鬆按修正帶5mm*6M 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 45, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101005'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101005', 'SDI手牌 CT-205 iPUSH輕鬆按修正帶5mm*6M 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 45, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101005'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101005', 'SDI手牌 CT-205 iPUSH輕鬆按修正帶5mm*6M 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 45, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101005', 'SDI手牌 CT-205 iPUSH輕鬆按修正帶5mm*6M 藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 45, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101005'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101006', 'SDI手牌 CT-205R iPUSH修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101006'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101006', 'SDI手牌 CT-205R iPUSH修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101006'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101006', 'SDI手牌 CT-205R iPUSH修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101006'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101006', 'SDI手牌 CT-205R iPUSH修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101006'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101006', 'SDI手牌 CT-205R iPUSH修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101006'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101006', 'SDI手牌 CT-205R iPUSH修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101006'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101006', 'SDI手牌 CT-205R iPUSH修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101006'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1101006', 'SDI手牌 CT-205R iPUSH修正帶內帶', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1101006'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201001', 'SIMBALION雄獅 50cc 合成糊', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201001', 'SIMBALION雄獅 50cc 合成糊', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201001', 'SIMBALION雄獅 50cc 合成糊', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201001', 'SIMBALION雄獅 50cc 合成糊', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201001', 'SIMBALION雄獅 50cc 合成糊', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201001', 'SIMBALION雄獅 50cc 合成糊', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201001', 'SIMBALION雄獅 50cc 合成糊', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201001', 'SIMBALION雄獅 50cc 合成糊', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201003', '妙妙 HY-503 500CC補充膠水', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 56, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201003'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201003', '妙妙 HY-503 500CC補充膠水', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 56, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201003'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201003', '妙妙 HY-503 500CC補充膠水', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 56, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201003'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201003', '妙妙 HY-503 500CC補充膠水', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 56, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201003'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201003', '妙妙 HY-503 500CC補充膠水', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 56, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201003'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201003', '妙妙 HY-503 500CC補充膠水', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 56, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201003'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201003', '妙妙 HY-503 500CC補充膠水', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 56, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1201003', '妙妙 HY-503 500CC補充膠水', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 56, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1201003'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1202001', 'SIMBALION雄獅 GS104口紅膠 8g', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1202001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1202001', 'SIMBALION雄獅 GS104口紅膠 8g', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1202001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1202001', 'SIMBALION雄獅 GS104口紅膠 8g', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1202001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1202001', 'SIMBALION雄獅 GS104口紅膠 8g', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1202001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1202001', 'SIMBALION雄獅 GS104口紅膠 8g', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1202001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1202001', 'SIMBALION雄獅 GS104口紅膠 8g', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1202001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1202001', 'SIMBALION雄獅 GS104口紅膠 8g', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1202001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1202001', 'SIMBALION雄獅 GS104口紅膠 8g', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 8, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1202001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1204001', 'SDI手牌 1102B 簡約實用型釘書機10號', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1204001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1204001', 'SDI手牌 1102B 簡約實用型釘書機10號', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1204001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1204001', 'SDI手牌 1102B 簡約實用型釘書機10號', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1204001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1204001', 'SDI手牌 1102B 簡約實用型釘書機10號', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1204001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1204001', 'SDI手牌 1102B 簡約實用型釘書機10號', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1204001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1204001', 'SDI手牌 1102B 簡約實用型釘書機10號', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1204001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1204001', 'SDI手牌 1102B 簡約實用型釘書機10號', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1204001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1204001', 'SDI手牌 1102B 簡約實用型釘書機10號', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1204001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1205001', 'PLUS普樂士 30-111 No.10 釘書針(30-925)(20小盒入)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1205001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1205001', 'PLUS普樂士 30-111 No.10 釘書針(30-925)(20小盒入)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1205001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1205001', 'PLUS普樂士 30-111 No.10 釘書針(30-925)(20小盒入)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1205001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1205001', 'PLUS普樂士 30-111 No.10 釘書針(30-925)(20小盒入)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1205001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1205001', 'PLUS普樂士 30-111 No.10 釘書針(30-925)(20小盒入)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1205001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1205001', 'PLUS普樂士 30-111 No.10 釘書針(30-925)(20小盒入)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1205001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1205001', 'PLUS普樂士 30-111 No.10 釘書針(30-925)(20小盒入)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1205001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1205001', 'PLUS普樂士 30-111 No.10 釘書針(30-925)(20小盒入)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1205001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206001', 'SDI手牌 0706B 圓型特大迴紋針(50mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206001', 'SDI手牌 0706B 圓型特大迴紋針(50mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206001', 'SDI手牌 0706B 圓型特大迴紋針(50mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206001', 'SDI手牌 0706B 圓型特大迴紋針(50mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206001', 'SDI手牌 0706B 圓型特大迴紋針(50mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206001', 'SDI手牌 0706B 圓型特大迴紋針(50mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206001', 'SDI手牌 0706B 圓型特大迴紋針(50mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206001', 'SDI手牌 0706B 圓型特大迴紋針(50mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206002', 'SDI手牌 0702B 圓型迴紋針(28mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206002', 'SDI手牌 0702B 圓型迴紋針(28mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206002', 'SDI手牌 0702B 圓型迴紋針(28mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206002', 'SDI手牌 0702B 圓型迴紋針(28mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206002', 'SDI手牌 0702B 圓型迴紋針(28mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206002', 'SDI手牌 0702B 圓型迴紋針(28mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206002', 'SDI手牌 0702B 圓型迴紋針(28mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206002', 'SDI手牌 0702B 圓型迴紋針(28mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206003', 'SDI手牌 0731B 三角迴紋針(25.4mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206003'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206003', 'SDI手牌 0731B 三角迴紋針(25.4mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206003'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206003', 'SDI手牌 0731B 三角迴紋針(25.4mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206003'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206003', 'SDI手牌 0731B 三角迴紋針(25.4mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206003'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206003', 'SDI手牌 0731B 三角迴紋針(25.4mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206003'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206003', 'SDI手牌 0731B 三角迴紋針(25.4mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206003'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206003', 'SDI手牌 0731B 三角迴紋針(25.4mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1206003', 'SDI手牌 0731B 三角迴紋針(25.4mm)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 13, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1206003'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207001', 'SDI手牌 0222B 黑色長尾夾 51mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 78, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207001', 'SDI手牌 0222B 黑色長尾夾 51mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 78, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207001', 'SDI手牌 0222B 黑色長尾夾 51mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 78, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207001', 'SDI手牌 0222B 黑色長尾夾 51mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 78, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207001', 'SDI手牌 0222B 黑色長尾夾 51mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 78, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207001', 'SDI手牌 0222B 黑色長尾夾 51mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 78, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207001', 'SDI手牌 0222B 黑色長尾夾 51mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 78, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207001', 'SDI手牌 0222B 黑色長尾夾 51mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 78, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207002', 'SDI手牌 0223B 黑色長尾夾 41mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 55, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207002', 'SDI手牌 0223B 黑色長尾夾 41mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 55, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207002', 'SDI手牌 0223B 黑色長尾夾 41mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 55, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207002', 'SDI手牌 0223B 黑色長尾夾 41mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 55, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207002', 'SDI手牌 0223B 黑色長尾夾 41mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 55, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207002', 'SDI手牌 0223B 黑色長尾夾 41mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 55, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207002', 'SDI手牌 0223B 黑色長尾夾 41mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 55, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207002', 'SDI手牌 0223B 黑色長尾夾 41mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 55, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207003', 'SDI手牌 0224B 黑色長尾夾 32mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207003'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207003', 'SDI手牌 0224B 黑色長尾夾 32mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207003'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207003', 'SDI手牌 0224B 黑色長尾夾 32mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207003'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207003', 'SDI手牌 0224B 黑色長尾夾 32mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207003'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207003', 'SDI手牌 0224B 黑色長尾夾 32mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207003'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207003', 'SDI手牌 0224B 黑色長尾夾 32mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207003'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207003', 'SDI手牌 0224B 黑色長尾夾 32mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207003', 'SDI手牌 0224B 黑色長尾夾 32mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207003'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207004', 'SDI手牌 0225B 黑色長尾夾 25mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207004'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207004', 'SDI手牌 0225B 黑色長尾夾 25mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207004'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207004', 'SDI手牌 0225B 黑色長尾夾 25mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207004'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207004', 'SDI手牌 0225B 黑色長尾夾 25mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207004'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207004', 'SDI手牌 0225B 黑色長尾夾 25mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207004'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207004', 'SDI手牌 0225B 黑色長尾夾 25mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207004'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207004', 'SDI手牌 0225B 黑色長尾夾 25mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207004', 'SDI手牌 0225B 黑色長尾夾 25mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207004'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207005', 'SDI手牌 0226B 黑色長尾夾 19mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207005'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207005', 'SDI手牌 0226B 黑色長尾夾 19mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207005'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207005', 'SDI手牌 0226B 黑色長尾夾 19mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207005'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207005', 'SDI手牌 0226B 黑色長尾夾 19mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207005'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207005', 'SDI手牌 0226B 黑色長尾夾 19mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207005'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207005', 'SDI手牌 0226B 黑色長尾夾 19mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207005'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207005', 'SDI手牌 0226B 黑色長尾夾 19mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207005', 'SDI手牌 0226B 黑色長尾夾 19mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207005'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207006', 'SDI手牌 0227B 黑色長尾夾 15mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 17, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207006'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207006', 'SDI手牌 0227B 黑色長尾夾 15mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 17, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207006'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207006', 'SDI手牌 0227B 黑色長尾夾 15mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 17, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207006'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207006', 'SDI手牌 0227B 黑色長尾夾 15mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 17, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207006'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207006', 'SDI手牌 0227B 黑色長尾夾 15mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 17, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207006'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207006', 'SDI手牌 0227B 黑色長尾夾 15mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 17, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207006'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207006', 'SDI手牌 0227B 黑色長尾夾 15mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 17, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207006'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1207006', 'SDI手牌 0227B 黑色長尾夾 15mm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 17, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1207006'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1209001', 'NO.1116 強力型拔釘器', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1209001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1209001', 'NO.1116 強力型拔釘器', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1209001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1209001', 'NO.1116 強力型拔釘器', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1209001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1209001', 'NO.1116 強力型拔釘器', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1209001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1209001', 'NO.1116 強力型拔釘器', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1209001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1209001', 'NO.1116 強力型拔釘器', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1209001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1209001', 'NO.1116 強力型拔釘器', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1209001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1209001', 'NO.1116 強力型拔釘器', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 32, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1209001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301001', 'OLFA OUTTER極致系列小型美工刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 152, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301001', 'OLFA OUTTER極致系列小型美工刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 152, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301001', 'OLFA OUTTER極致系列小型美工刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 152, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301001', 'OLFA OUTTER極致系列小型美工刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 152, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301001', 'OLFA OUTTER極致系列小型美工刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 152, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301001', 'OLFA OUTTER極致系列小型美工刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 152, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301001', 'OLFA OUTTER極致系列小型美工刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 152, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301001', 'OLFA OUTTER極致系列小型美工刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 152, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301004', 'ABEL力大 66001小美工刀片', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301004'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301004', 'ABEL力大 66001小美工刀片', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301004'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301004', 'ABEL力大 66001小美工刀片', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301004'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301004', 'ABEL力大 66001小美工刀片', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301004'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301004', 'ABEL力大 66001小美工刀片', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301004'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301004', 'ABEL力大 66001小美工刀片', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301004'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301004', 'ABEL力大 66001小美工刀片', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1301004', 'ABEL力大 66001小美工刀片', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 18, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1301004'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1302001', 'SS-40高級家庭事務剪刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1302001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1302001', 'SS-40高級家庭事務剪刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1302001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1302001', 'SS-40高級家庭事務剪刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1302001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1302001', 'SS-40高級家庭事務剪刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1302001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1302001', 'SS-40高級家庭事務剪刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1302001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1302001', 'SS-40高級家庭事務剪刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1302001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1302001', 'SS-40高級家庭事務剪刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1302001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1302001', 'SS-40高級家庭事務剪刀', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 26, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1302001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1401001', 'Penrote筆樂 TD7770 鋼尺30cm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1401001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1401001', 'Penrote筆樂 TD7770 鋼尺30cm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1401001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1401001', 'Penrote筆樂 TD7770 鋼尺30cm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1401001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1401001', 'Penrote筆樂 TD7770 鋼尺30cm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1401001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1401001', 'Penrote筆樂 TD7770 鋼尺30cm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1401001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1401001', 'Penrote筆樂 TD7770 鋼尺30cm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1401001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1401001', 'Penrote筆樂 TD7770 鋼尺30cm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1401001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1401001', 'Penrote筆樂 TD7770 鋼尺30cm', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1401001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501001', 'PE3夾鍊袋3#7*10cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 16, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501001', 'PE3夾鍊袋3#7*10cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 16, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501001', 'PE3夾鍊袋3#7*10cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 16, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501001', 'PE3夾鍊袋3#7*10cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 16, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501001', 'PE3夾鍊袋3#7*10cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 16, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501001', 'PE3夾鍊袋3#7*10cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 16, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501001', 'PE3夾鍊袋3#7*10cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 16, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501001', 'PE3夾鍊袋3#7*10cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 16, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501002', 'PE4夾鍊袋4#8.5*12cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 20, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501002', 'PE4夾鍊袋4#8.5*12cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 20, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501002', 'PE4夾鍊袋4#8.5*12cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 20, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501002', 'PE4夾鍊袋4#8.5*12cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 20, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501002', 'PE4夾鍊袋4#8.5*12cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 20, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501002', 'PE4夾鍊袋4#8.5*12cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 20, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501002', 'PE4夾鍊袋4#8.5*12cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 20, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501002', 'PE4夾鍊袋4#8.5*12cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 20, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501003', 'PE1夾鍊袋1#5*7cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501003'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501003', 'PE1夾鍊袋1#5*7cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501003'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501003', 'PE1夾鍊袋1#5*7cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501003'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501003', 'PE1夾鍊袋1#5*7cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501003'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501003', 'PE1夾鍊袋1#5*7cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501003'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501003', 'PE1夾鍊袋1#5*7cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501003'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501003', 'PE1夾鍊袋1#5*7cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1501003', 'PE1夾鍊袋1#5*7cm(100個/包)', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 11, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1501003'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1502001', 'BH-553 三層公文架 A4 (米色) ^33.5*25.8*6cm,附鐵支架,12組/箱', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 195, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1502001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1502001', 'BH-553 三層公文架 A4 (米色) ^33.5*25.8*6cm,附鐵支架,12組/箱', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 195, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1502001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1502001', 'BH-553 三層公文架 A4 (米色) ^33.5*25.8*6cm,附鐵支架,12組/箱', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 195, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1502001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1502001', 'BH-553 三層公文架 A4 (米色) ^33.5*25.8*6cm,附鐵支架,12組/箱', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 195, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1502001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1502001', 'BH-553 三層公文架 A4 (米色) ^33.5*25.8*6cm,附鐵支架,12組/箱', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 195, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1502001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1502001', 'BH-553 三層公文架 A4 (米色) ^33.5*25.8*6cm,附鐵支架,12組/箱', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 195, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1502001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1502001', 'BH-553 三層公文架 A4 (米色) ^33.5*25.8*6cm,附鐵支架,12組/箱', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 195, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1502001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1502001', 'BH-553 三層公文架 A4 (米色) ^33.5*25.8*6cm,附鐵支架,12組/箱', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 195, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1502001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601001', '自強 D15 三孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 150, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601001', '自強 D15 三孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 150, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601001', '自強 D15 三孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 150, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601001', '自強 D15 三孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 150, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601001', '自強 D15 三孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 150, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601001', '自強 D15 三孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 150, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601001', '自強 D15 三孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 150, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601001', '自強 D15 三孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 150, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601002', '自強D20三 孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601002', '自強D20三 孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601002', '自強D20三 孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601002', '自強D20三 孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601002', '自強D20三 孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601002', '自強D20三 孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601002', '自強D20三 孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1601002', '自強D20三 孔D型夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1601002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1602001', 'L型文件套12入 白', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1602001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1602001', 'L型文件套12入 白', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1602001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1602001', 'L型文件套12入 白', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1602001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1602001', 'L型文件套12入 白', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1602001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1602001', 'L型文件套12入 白', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1602001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1602001', 'L型文件套12入 白', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1602001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1602001', 'L型文件套12入 白', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1602001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1602001', 'L型文件套12入 白', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 33, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1602001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1604001', 'AS-40C 實用資料簿藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 61, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1604001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1604001', 'AS-40C 實用資料簿藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 61, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1604001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1604001', 'AS-40C 實用資料簿藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 61, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1604001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1604001', 'AS-40C 實用資料簿藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 61, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1604001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1604001', 'AS-40C 實用資料簿藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 61, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1604001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1604001', 'AS-40C 實用資料簿藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 61, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1604001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1604001', 'AS-40C 實用資料簿藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 61, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1604001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1604001', 'AS-40C 實用資料簿藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 61, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1604001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605001', '萬國 中式卷宗直式附套-藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605001', '萬國 中式卷宗直式附套-藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605001', '萬國 中式卷宗直式附套-藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605001', '萬國 中式卷宗直式附套-藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605001', '萬國 中式卷宗直式附套-藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605001', '萬國 中式卷宗直式附套-藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605001', '萬國 中式卷宗直式附套-藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605001', '萬國 中式卷宗直式附套-藍', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605002', '萬國 中式卷宗直式附套-紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605002', '萬國 中式卷宗直式附套-紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605002', '萬國 中式卷宗直式附套-紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605002', '萬國 中式卷宗直式附套-紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605002', '萬國 中式卷宗直式附套-紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605002', '萬國 中式卷宗直式附套-紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605002', '萬國 中式卷宗直式附套-紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1605002', '萬國 中式卷宗直式附套-紅', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 25, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1605002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1606001', '粉彩5入附桿文件套', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1606001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1606001', '粉彩5入附桿文件套', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1606001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1606001', '粉彩5入附桿文件套', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1606001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1606001', '粉彩5入附桿文件套', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1606001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1606001', '粉彩5入附桿文件套', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1606001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1606001', '粉彩5入附桿文件套', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1606001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1606001', '粉彩5入附桿文件套', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1606001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1606001', '粉彩5入附桿文件套', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1606001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1607001', 'A4壓克力板夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 44, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1607001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1607001', 'A4壓克力板夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 44, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1607001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1607001', 'A4壓克力板夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 44, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1607001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1607001', 'A4壓克力板夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 44, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1607001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1607001', 'A4壓克力板夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 44, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1607001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1607001', 'A4壓克力板夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 44, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1607001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1607001', 'A4壓克力板夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 44, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1607001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1607001', 'A4壓克力板夾', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 44, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1607001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701001', '萬年紅 艾絨印尼 大', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 180, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701001'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701001', '萬年紅 艾絨印尼 大', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 180, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701001'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701001', '萬年紅 艾絨印尼 大', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 180, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701001'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701001', '萬年紅 艾絨印尼 大', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 180, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701001'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701001', '萬年紅 艾絨印尼 大', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 180, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701001'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701001', '萬年紅 艾絨印尼 大', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 180, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701001'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701001', '萬年紅 艾絨印尼 大', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 180, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701001', '萬年紅 艾絨印尼 大', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 180, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701002', 'LIBERTY利百代 MS-50明色印尼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701002'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701002', 'LIBERTY利百代 MS-50明色印尼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701002'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701002', 'LIBERTY利百代 MS-50明色印尼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701002'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701002', 'LIBERTY利百代 MS-50明色印尼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701002'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701002', 'LIBERTY利百代 MS-50明色印尼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701002'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701002', 'LIBERTY利百代 MS-50明色印尼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701002'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701002', 'LIBERTY利百代 MS-50明色印尼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G1701002', 'LIBERTY利百代 MS-50明色印尼', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 77, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G1701002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901003', '66803 A3切割墊 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901003'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901003', '66803 A3切割墊 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901003'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901003', '66803 A3切割墊 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901003'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901003', '66803 A3切割墊 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901003'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901003', '66803 A3切割墊 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901003'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901003', '66803 A3切割墊 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901003'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901003', '66803 A3切割墊 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901003', '66803 A3切割墊 綠', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901003'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901004', '普通橡皮圈 18號4兩', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901004'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901004', '普通橡皮圈 18號4兩', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901004'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901004', '普通橡皮圈 18號4兩', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901004'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901004', '普通橡皮圈 18號4兩', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901004'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901004', '普通橡皮圈 18號4兩', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901004'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901004', '普通橡皮圈 18號4兩', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901004'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901004', '普通橡皮圈 18號4兩', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901004', '普通橡皮圈 18號4兩', '盛彪股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), 39, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901004'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901007', 'A3壓克力板', '昉珩壓克力企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='昉珩壓克力企業社' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901007'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901007', 'A3壓克力板', '昉珩壓克力企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='昉珩壓克力企業社' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901007'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901007', 'A3壓克力板', '昉珩壓克力企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='昉珩壓克力企業社' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901007'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901007', 'A3壓克力板', '昉珩壓克力企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='昉珩壓克力企業社' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901007'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901007', 'A3壓克力板', '昉珩壓克力企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='昉珩壓克力企業社' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901007'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901007', 'A3壓克力板', '昉珩壓克力企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='昉珩壓克力企業社' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901007'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901007', 'A3壓克力板', '昉珩壓克力企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='昉珩壓克力企業社' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901007'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901007', 'A3壓克力板', '昉珩壓克力企業社', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='昉珩壓克力企業社' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901007'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901008', '日曜-專櫃用名牌', '必凡思國際有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='必凡思國際有限公司' LIMIT 1), 219, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901008'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901008', '日曜-專櫃用名牌', '必凡思國際有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='必凡思國際有限公司' LIMIT 1), 219, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901008'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901008', '日曜-專櫃用名牌', '必凡思國際有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='必凡思國際有限公司' LIMIT 1), 219, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901008'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901008', '日曜-專櫃用名牌', '必凡思國際有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='必凡思國際有限公司' LIMIT 1), 219, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901008'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901008', '日曜-專櫃用名牌', '必凡思國際有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='必凡思國際有限公司' LIMIT 1), 219, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901008'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901008', '日曜-專櫃用名牌', '必凡思國際有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='必凡思國際有限公司' LIMIT 1), 219, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901008'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901008', '日曜-專櫃用名牌', '必凡思國際有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='必凡思國際有限公司' LIMIT 1), 219, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901008'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901008', '日曜-專櫃用名牌', '必凡思國際有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='必凡思國際有限公司' LIMIT 1), 219, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901008'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901009', '舊式pos機清機條 空白紙捲(無黑點-警告線) 41mm*48M 200捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901009'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901009', '舊式pos機清機條 空白紙捲(無黑點-警告線) 41mm*48M 200捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901009'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901009', '舊式pos機清機條 空白紙捲(無黑點-警告線) 41mm*48M 200捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901009'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901009', '舊式pos機清機條 空白紙捲(無黑點-警告線) 41mm*48M 200捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901009'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901009', '舊式pos機清機條 空白紙捲(無黑點-警告線) 41mm*48M 200捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901009'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901009', '舊式pos機清機條 空白紙捲(無黑點-警告線) 41mm*48M 200捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901009'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901009', '舊式pos機清機條 空白紙捲(無黑點-警告線) 41mm*48M 200捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901009'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901009', '舊式pos機清機條 空白紙捲(無黑點-警告線) 41mm*48M 200捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 15, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901009'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901010', '電子發票感熱紙捲 寬57mm外徑8cm 48捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901010'
  AND d.company_code='OU' AND d.dept_name='人資部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901010', '電子發票感熱紙捲 寬57mm外徑8cm 48捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901010'
  AND d.company_code='OU' AND d.dept_name='行銷部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901010', '電子發票感熱紙捲 寬57mm外徑8cm 48捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901010'
  AND d.company_code='OU' AND d.dept_name='系統輔導暨統購稽核部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901010', '電子發票感熱紙捲 寬57mm外徑8cm 48捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901010'
  AND d.company_code='OU' AND d.dept_name='客服部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901010', '電子發票感熱紙捲 寬57mm外徑8cm 48捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901010'
  AND d.company_code='OU' AND d.dept_name='財務部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901010', '電子發票感熱紙捲 寬57mm外徑8cm 48捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901010'
  AND d.company_code='OU' AND d.dept_name='設計部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901010', '電子發票感熱紙捲 寬57mm外徑8cm 48捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901010'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'G9901010', '電子發票感熱紙捲 寬57mm外徑8cm 48捲/箱', '永豐紙業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621202' LIMIT 1), false, '2026-11 日曜料號主檔匯入；文具用品-用品'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-G9901010'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'C0101001', '五月花大捲筒衛生紙 #0105054 1公斤  3捲*4袋/箱', '永豐餘消費品實業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐餘消費品實業股份有限公司' LIMIT 1), 680, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='6238' LIMIT 1), false, '2026-11 日曜料號主檔匯入；清潔費'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-C0101001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'C0103001', '五月花摺疊紙巾 200抽*20包/箱', '永豐餘消費品實業股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐餘消費品實業股份有限公司' LIMIT 1), 495, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='6238' LIMIT 1), false, '2026-11 日曜料號主檔匯入；清潔費'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-C0103001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'C0201001', '珍珠洗手乳#2211-32001  1加侖/4桶/箱', '聯合世貿有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), 140, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='6238' LIMIT 1), false, '2026-11 日曜料號主檔匯入；清潔費'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-C0201001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'C0301001', '鐵罐香罐 檸檬', '聯合世貿有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), 120, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='6238' LIMIT 1), false, '2026-11 日曜料號主檔匯入；清潔費'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-C0301001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'C0401001', '50斤垃圾袋 白50包/件 1包/6張 90*105CM', '聯合世貿有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), 21, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='6238' LIMIT 1), false, '2026-11 日曜料號主檔匯入；清潔費'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-C0401001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'C0401002', 'CR連潔垃圾袋白(特大)18張/24捲/箱 80*95CM', '聯合世貿有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), 55.83, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='6238' LIMIT 1), false, '2026-11 日曜料號主檔匯入；清潔費'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-C0401002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'C0401003', 'CR連潔垃圾袋白(大)40張/24捲/箱 65*80CM', '聯合世貿有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), 55.83, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='6238' LIMIT 1), false, '2026-11 日曜料號主檔匯入；清潔費'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-C0401003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'C0401004', 'CRPST垃圾袋白(中)73張*24捲/箱 54*57CM', '聯合世貿有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), 55.83, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='6238' LIMIT 1), false, '2026-11 日曜料號主檔匯入；清潔費'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-C0401004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'C0401005', 'CRPST垃圾袋白(小)100張*24捲/箱45*55CM', '聯合世貿有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), 55.83, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='6238' LIMIT 1), false, '2026-11 日曜料號主檔匯入；清潔費'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-C0401005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'C0401006', '客房垃圾袋白(小) 24捲/箱40*50CM', '聯合世貿有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), 55.83, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='6238' LIMIT 1), false, '2026-11 日曜料號主檔匯入；清潔費'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-C0401006'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'C0401007', '連潔清潔袋白10張/12支/箱120*140CM', '聯合世貿有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), 1340, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='6238' LIMIT 1), false, '2026-11 日曜料號主檔匯入；清潔費'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-C0401007'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'C0501013', 'Duskin小便斗藥劑', '聯合世貿有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), 140, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='6238' LIMIT 1), false, '2026-11 日曜料號主檔匯入；清潔費'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-C0501013'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'C0601001', '75%清菌用酒精#4601-32011 4000ml/6桶/箱', '聯合世貿有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), 300, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='6238' LIMIT 1), false, '2026-11 日曜料號主檔匯入；清潔費'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-C0601001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'S0301001', '白色塑膠袋-大', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 4.2, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-S0301001'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'S0301002', '白色塑膠袋-小', '廷軒有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), 3, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621702' LIMIT 1), false, '2026-11 日曜料號主檔匯入；廣告費-促銷'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-S0301002'
  AND d.company_code='OU' AND d.dept_name='營業部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0101001', '天基-濾網400風量(塑膠尼龍纖維)', '捷彬科技有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), NULL, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0101001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0101002', '天基-濾網600風量(塑膠尼龍纖維)', '捷彬科技有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), NULL, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0101002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0101003', '天基-濾網800風量(塑膠尼龍纖維)', '捷彬科技有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), NULL, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0101003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0101004', '天基-濾網1000風量(塑膠尼龍纖維)', '捷彬科技有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), NULL, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0101004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0101005', '天基-濾網1200風量(塑膠尼龍纖維)', '捷彬科技有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), NULL, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0101005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0102001', '皮帶-冷氣用三角帶SPZ950', '金利五金行', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0102001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0102002', '皮帶-散熱水塔冷氣三角帶B158', '金利五金行', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), 487, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0102002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0102003', '皮帶-空調預冷機三角帶SPZ1087', '金利五金行', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0102003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0102004', '皮帶-SPZ1287', '金利五金行', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0102004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0102005', '皮帶-SPZ1320', '金利五金行', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0102005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0102006', '皮帶-SPZ1462', '金利五金行', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0102006'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0102007', '皮帶-SPZ1112', '金利五金行', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0102007'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0102008', '皮帶-SPZ1037', '金利五金行', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0102008'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0102009', '皮帶-B56', '金利五金行', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0102009'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0102010', '皮帶-B96', '金利五金行', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0102010'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0103001', 'HS-602防塞丸', '泓昇環境工程股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='泓昇環境工程股份有限公司' LIMIT 1), 476, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0103001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0201001', '燈泡-LED飛利浦9W/E27/3000K', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 145, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0201001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0201002', '燈泡-亮博士 35W 4000K(4600 lm)', '瑞眾股份有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='瑞眾股份有限公司' LIMIT 1), 285, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0201002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0201003', '燈泡-舞光LED 25W省電球泡-日光 100-240V/30W/6500K', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 368, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0201003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0201004', '燈泡-水銀燈泡 MH-175W/U E40', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 800, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0201004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0201005', '燈泡-清光 2W', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 5, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0201005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0201006', '燈泡-LED-12W/3000K/E27', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 130, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0201006'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0201007', '燈泡-LED-6.5W/9W/E27', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 145, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0201007'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0201008', '燈泡-保溫燈泡220V/E27/250W', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 380, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0201008'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0201009', '燈泡-保溫燈泡110V/E27/250W', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 380, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0201009'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0211006', '燈泡-LED MR16 E27 7W 杯燈燈泡', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 120, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0211006'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0202001', '崁燈-LED 3W/3000K', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 300, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0202001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0202002', '崁燈-LED 7W/3000K黑杯崁燈/崁燈變壓器', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0202002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0202003', '崁燈-LED-24W-4000K 全電壓崁燈 開孔17CM', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 500, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0202003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0202004', '崁燈-LED-COB-24W-4000K 全電壓崁燈 開孔21公分', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 680, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0202004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0202005', '崁燈-LED-COB-30W-4000K 全電壓崁燈 開孔19.5公分', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 1500, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0202005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0202006', '崁燈-LED-COB-30W-4000K 全電壓崁燈 開孔22.5公分', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 1800, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0202006'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0203001', '崁燈-LEDAR-111燈組(黑) 23W-3000K25D全電壓', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 977, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0203001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0203002', '投射燈-LEDAR-111燈組 12W-4000K+DR薄型七燈', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 380, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0203002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0203003', '投射燈-LEDAR-111燈組 15W-4000K+DR(崁入)12燈', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 326, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0203003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0203004', '投射燈-LEDAR-111軌道投射燈組 12W-4000K全電壓七燈', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), '588', (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0203004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0203008', '投射燈-LED-AR111-12W/3000K', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 310, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0203008'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0204001', '軌道燈-LED 30W-4000K全電壓(白色)', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 660, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0204001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0204002', '軌道燈組-LED  30W-4000K全電壓(萊)-80mm 黑色', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 1100, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0204002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0205001', '平板燈-LED-23W雙標 全電壓 4000K', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 780, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0205001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0205003', '平板燈-LED-23W雙標 全電壓 6500K', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 780, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0205003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206001', '燈管-日光燈（飛利浦） T5/14W/865', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 55, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206002', '燈管-日光燈（飛利浦） T5/14W/830', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206003', '燈管-LED（歐司朗） T8/2尺全電壓4000K', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 100, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206004', '燈管-LED（歐司朗） T8/2尺全電壓(白光)', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 100, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206005', '燈管-日光燈《東亞太陽神》 T8/20W(晝光)FL20/18D', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 85, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206006', '燈管-日光燈《東亞太陽神》T8/20W(黃光))FL20/18D', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 55, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206006'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206008', '燈管-BB燈管 PLC-18W/830/2P', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 105, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206008'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206009', '燈管-BB燈管PLC-18W/840/2P', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 105, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206009'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206010', '燈管-BB燈管 PLC-26W/840/2P', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 105, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206010'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206011', '燈管-日光燈（飛利浦）T5/28W/830', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206011'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206012', '燈管-日光燈（飛利浦）T5/28W/827', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206012'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206013', '燈管-日光燈（飛利浦）T5/28W/840', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206013'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206014', '燈管-日光燈（飛利浦）T5/28W/865', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206014'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206015', '燈管-日光燈（飛利浦）TLD 36W/830', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 70, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206015'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206016', '燈管-日光燈（飛利浦）TLD 36W/840', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206016'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206017', '燈管-LED燈（歐司朗）T8/4尺全電壓4000K', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 132, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206017'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206018', '燈管-2/ eLED燈管（旭光）T8/3尺全電壓4000K', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 132, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206018'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206019', '燈管-雙頭複金屬燈管 HQI-TS70W/NDL(OSARAM)白', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 336, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206019'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206020', '燈管-日光燈（歐司朗）T5/35W/4000K(德製)', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206020'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206021', '燈管-日光燈（飛利浦）T5/21W/830', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206021'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206022', '燈管-日光燈（飛利浦）T5/21W/840', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206022'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206023', '燈管-日光燈（飛利浦）T5/21W/865', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206023'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206024', '燈管-日光燈（飛利浦  TLD 30W/830', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 90, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206024'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206025', '燈管-日光燈（飛利浦  TLD 30W/840', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 90, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206025'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206026', '燈管-日光燈（飛利浦  TLD 30W/865', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 90, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206026'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206027', '燈管-日光燈《東亞》 T8/40W(晝光)三波長', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 75, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206027'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206028', '燈管-LED (OSRAM) T8/4呎/6500K 全電壓', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 125, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206028'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0206029', '燈管-飛利浦有罩燈管TWG206TL5/28W830/110-220V', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 600, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0206029'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0207001', '串接式燈具 LED/T8/2尺全電壓', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 95, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0207001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0207002', '串接式燈具 LED/T8/3尺全電壓', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 116, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0207002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0207003', '串接式燈具 LED/T8/4尺全電壓', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 105, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0207003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0207004', '串接式燈具 T8/40W/220V', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 158, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0207004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0207005', '串接式燈具 T8/40W/110V', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 158, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0207005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0207006', '串接式燈具 T8/30W/220V', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 130, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0207006'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0207007', '串接式燈具 T8/30W/110V', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 130, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0207007'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0207008', '串接式燈具 T5/21W/110V', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 200, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0207008'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0207009', '串接式燈具 T5/21W/220V', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 160, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0207009'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0207010', '串接式燈具 T5/14W/110V', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 150, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0207010'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0207011', '串接式燈具 T5/28W/110V', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 200, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0207011'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0207012', '串接式燈具 T5/28W/220V', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 120, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0207012'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0208001', '支架燈 T8/4尺全電壓3000K', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 247, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0208001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0208002', '支架燈 T8/4尺全電壓6500K', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 247, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0208002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0208003', '支架燈 T5-2尺6500K全電壓', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 135, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0208003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0208004', '支架燈 T5-2尺4000K全電壓', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 148, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0208004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0208005', '支架燈 T5-3尺4000K全電壓', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 175, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0208005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0208006', '支架燈 T5-4尺4000K全電壓', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 175, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0208006'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0209001', '山型燈具組(110-220V)T5', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 600, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0209001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0210001', '反射型燈具LTS-4140XXA', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0210001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0211001', '杯燈PHILIPS-LED燈 MR16-6W-3000K全電壓', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 160, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0211001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0211002', '杯燈PHILIPS-LED燈 MR16-6W-6500K全電壓', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 160, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0211002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0211003', '杯燈樂亮-LED燈 MR16-5W-6500K全電壓', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 160, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0211003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0211004', '杯燈LED6.5w超極光(晝光色)110-240V/6.5W/6500K', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 130, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0211004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0212001', '燈座LED桶燈座 E27-CH2725W', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 410, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0212001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0213001', '燈頭G12磁燈頭 (插PIN)(軌道)', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 120, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0213001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0213002', '燈頭C G8.5進口燈頭 CDM-TC-35W燈管用', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 150, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0213002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0301001', '漏電斷路器  1P NVB-50UL-20A', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 356, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0301001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0301002', '漏電斷路器  3P  NF100- 30A', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 888, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0301002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0301003', '漏電斷路器  3P  NF100- 20A', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 714, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0301003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0302001', '無熔絲開關  1P  15A', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 63, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0302001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0302002', '無熔絲開關  3P  30A', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), '310', (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0302002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0302003', '無熔絲開關 2P  20A', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), '150', (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0302003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0302004', '無熔絲開關 1P  40A', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), '63', (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0302004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0302005', '無熔絲開關 3P  50A', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), '310', (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0302005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0302006', '無熔絲開關 3P  20A', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), '310', (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0302006'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0302007', '無熔絲開關 1P  20A', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), '63', (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0302007'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E0302008', '無熔絲開關 1P  30A', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), '63', (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E0302008'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1001001', '送風機-馬達 400型 400 CFM', '捷彬科技有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), 1200, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1001001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1001002', '送風機-馬達 600型 600 CFM', '捷彬科技有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), 1300, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1001002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1001003', '送風機-馬達 800型 800 CFM', '捷彬科技有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), 1300, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1001003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1002001', '送風機馬達(風鼓)左', '捷彬科技有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), 690, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1002001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1002002', '送風機馬達(風鼓)右', '捷彬科技有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), 690, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1002002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1101001', '偵煙器模組 M500R 控制模組', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 3700, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1101001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1101002', '偵煙器模組 M501M 監視模組', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 4000, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1101002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1101003', '偵煙器模組 M502M 監視模組', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 4000, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1101003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1102001', '差動火警探測器 停車場/商場消防', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 100, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1102001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1103001', '偵煙探測器 停車場/商場消防', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1103001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1104001', '手動排煙開關蓋板', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 80, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1104001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1104002', '手動排煙開關SH-48 DC24V 100MA', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 360, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1104002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1105001', '火警發信機DC24V 100MA', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 150, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1105001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1106001', '滅火器掛勾', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 12, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1106001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1107001', '消防壓力開關5-20Kgf/cm2', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 550, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1107001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1108001', '蜂鳴器', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1108001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1109001', '手動報警器', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 150, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1109001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1110001', '泡沫手動開關盒', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 260, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1110001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1111001', '6V-4AH電池', '羽任電池專賣店', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='羽任電池專賣店' LIMIT 1), 150, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1111001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1111002', '6-2.3AH電池', '羽任電池專賣店', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='羽任電池專賣店' LIMIT 1), 160, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1111002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1112001', 'LED60燈E燈吸壁式', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 520, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1112001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1112002', 'LED小型雙面方向燈 C級3:1 雙面', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 480, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1112002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1112003', 'LED出口指示燈 C級3:1單面滑軌耳掛兩用', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 330, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1112003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1113001', '廣播喇叭 吸頂/壁掛 3W (崁孔15公分)', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1113001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1113002', '廣播喇叭 崁入式 5W', '旭成科技製造有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), 250, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1113002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1201001', '定時器 24小時定時開關TB358NT6(220V)', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 1050, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1201001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1201002', '定時器 TB-全電壓線路型(110/220)', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 1200, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1201002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1205001', '星光三開附蓋板-5352', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 230, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1205001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1205002', '星光三開附蓋板-5252', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 140, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1205002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1205003', '歐風卡式蓋板 2孔蓋板', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 10, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1205003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1205004', '歐風卡式蓋板 1孔蓋板', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 7, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1205004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1205005', '歐風卡式蓋板 1聯封蓋無孔', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 7, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1205005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1206001', '壓條 TC-8灰', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 85, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1206001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1206002', '壓條 TC-5 乳白', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 35, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1206002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1206003', '壓條 TC-5 灰', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 35, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1206003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1206004', '壓條 RD-50 (半圓壓條)', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 90, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1206004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1206005', '壓條 RD-60(半圓壓條)', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 130, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1206005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1207001', '軌道 2M', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 300, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1207001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1207002', '軌道 3M', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 420, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1207002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1207003', '軌道 1M 深咖啡色', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 400, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1207003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1207004', '軌道 1.5M 深咖啡色', '森達利興業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), 400, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1207004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1208001', '轉向三面插', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 40, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1208001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1208002', '雙聯附接地插座 國際雙插', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 75, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1208002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1208003', '雙聯附接地插座 窗插5.5MM', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 81, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1208003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1208004', '轉向雙插', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 21, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1208004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1208005', '舒美插頭 母插', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 20, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1208005'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1208006', '插座 國際單切', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 30, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1208006'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1208007', '插座 國際單插座', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 45, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1208007'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1208008', '耐熱轉向插頭-三面 15A', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 60, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1208008'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1208009', '星光接地雙插座 WTDFP15123附益', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 90, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1208009'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1209001', '美術盒 明BOX', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 10, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1209001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1210001', '手套棉紗', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 75, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1210001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1211001', '肘動精密陶瓷自由栓 1/2" 長30CM', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 600, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1211001'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1211002', '立式冷水陶瓷自由栓 1/2"', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 650, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1211002'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1211003', '肘動精密陶瓷立栓 1/2"', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 210, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1211003'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);
INSERT INTO cycle_purchase_item_mappings
  (company_code, company, item_id, department_id, original_code, original_name, original_vendor_name, vendor_id, original_unit_price, account_code_id, is_confirmed, notes)
SELECT 'OU', '日曜天地', i.id, d.id, 'E1211004', '肘動精密陶瓷長栓 1/2"', '嘉嶽企業有限公司', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), 147, (SELECT id FROM cycle_purchase_account_codes WHERE company_code='OU' AND code='621601' LIMIT 1), false, '2026-11 日曜料號主檔匯入；修繕費-維修'
FROM cycle_purchase_items i, cycle_purchase_departments d
WHERE i.company_code='OU' AND i.item_code='OU-E1211004'
  AND d.company_code='OU' AND d.dept_name='管理部' AND d.is_active
  AND NOT EXISTS (SELECT 1 FROM cycle_purchase_item_mappings m WHERE m.item_id=i.id AND m.company_code='OU' AND m.department_id=d.id);

-- 2. 回填對照列的廠商與會計科目（主檔補齊後才會有值）
UPDATE cycle_purchase_item_mappings m SET vendor_id = v.id
FROM cycle_purchase_vendors v
WHERE m.company_code='OU' AND m.vendor_id IS NULL AND v.company_code='OU' AND v.vendor_name = m.original_vendor_name;
UPDATE cycle_purchase_item_mappings m SET account_code_id = a.id
FROM cycle_purchase_account_codes a, (VALUES ('D0101001', '621702'), ('D0101002', '621702'), ('D0101003', '621702'), ('D0201001', '621702'), ('D0201002', '621702'), ('D0202001', '621702'), ('D0202002', '621702'), ('D0203001', '621702'), ('D0203002', '621702'), ('D0204001', '621702'), ('D0204002', '621702'), ('D0204003', '621702'), ('D0205001', '621702'), ('D0205002', '621702'), ('D0205003', '621702'), ('G0101001', '621201'), ('G0102001', '621201'), ('G0102002', '621201'), ('G0102003', '621201'), ('G0102004', '621201'), ('G0102005', '621201'), ('G0102006', '621201'), ('G0102007', '621201'), ('G0103001', '621702'), ('G0103002', '621702'), ('G0103003', '621702'), ('G0104001', '621702'), ('G0104002', '621702'), ('G0201001', '621202'), ('G0201002', '621202'), ('G0202001', '621202'), ('G0301001', '621202'), ('G0401001', '621202'), ('G0401002', '621202'), ('G0402001', '621202'), ('G0402002', '621202'), ('G0402003', '621202'), ('G0403001', '621202'), ('G0501001', '621202'), ('G0501002', '621202'), ('G0601001', '621202'), ('G0601002', '621202'), ('G0601003', '621202'), ('G0701001', '621202'), ('G0701002', '621202'), ('G0702001', '621202'), ('G0702002', '621202'), ('G0703001', '621202'), ('G0704001', '621202'), ('G1001001', '621202'), ('G1001002', '621202'), ('G1001003', '621202'), ('G1001004', '621202'), ('G1001005', '621202'), ('G1002001', '621202'), ('G1002002', '621202'), ('G1002003', '621202'), ('G1002004', '621202'), ('G1002005', '621202'), ('G1002006', '621202'), ('G1002007', '621202'), ('G1002008', '621202'), ('G1004001', '621202'), ('G1004002', '621202'), ('G1101001', '621202'), ('G1101002', '621202'), ('G1101005', '621202'), ('G1101006', '621202'), ('G1201001', '621202'), ('G1201003', '621202'), ('G1202001', '621202'), ('G1204001', '621202'), ('G1205001', '621202'), ('G1206001', '621202'), ('G1206002', '621202'), ('G1206003', '621202'), ('G1207001', '621202'), ('G1207002', '621202'), ('G1207003', '621202'), ('G1207004', '621202'), ('G1207005', '621202'), ('G1207006', '621202'), ('G1209001', '621202'), ('G1301001', '621202'), ('G1301004', '621202'), ('G1302001', '621202'), ('G1401001', '621202'), ('G1501001', '621202'), ('G1501002', '621202'), ('G1501003', '621202'), ('G1502001', '621202'), ('G1601001', '621202'), ('G1601002', '621202'), ('G1602001', '621202'), ('G1604001', '621202'), ('G1605001', '621202'), ('G1605002', '621202'), ('G1606001', '621202'), ('G1607001', '621202'), ('G1701001', '621202'), ('G1701002', '621202'), ('G9901003', '621202'), ('G9901004', '621202'), ('G9901007', '621202'), ('G9901008', '621202'), ('G9901009', '621202'), ('G9901010', '621202'), ('C0101001', '6238'), ('C0103001', '6238'), ('C0201001', '6238'), ('C0301001', '6238'), ('C0401001', '6238'), ('C0401002', '6238'), ('C0401003', '6238'), ('C0401004', '6238'), ('C0401005', '6238'), ('C0401006', '6238'), ('C0401007', '6238'), ('C0501013', '6238'), ('C0601001', '6238'), ('S0301001', '621702'), ('S0301002', '621702'), ('E0101001', '621601'), ('E0101002', '621601'), ('E0101003', '621601'), ('E0101004', '621601'), ('E0101005', '621601'), ('E0102001', '621601'), ('E0102002', '621601'), ('E0102003', '621601'), ('E0102004', '621601'), ('E0102005', '621601'), ('E0102006', '621601'), ('E0102007', '621601'), ('E0102008', '621601'), ('E0102009', '621601'), ('E0102010', '621601'), ('E0103001', '621601'), ('E0201001', '621601'), ('E0201002', '621601'), ('E0201003', '621601'), ('E0201004', '621601'), ('E0201005', '621601'), ('E0201006', '621601'), ('E0201007', '621601'), ('E0201008', '621601'), ('E0201009', '621601'), ('E0211006', '621601'), ('E0202001', '621601'), ('E0202002', '621601'), ('E0202003', '621601'), ('E0202004', '621601'), ('E0202005', '621601'), ('E0202006', '621601'), ('E0203001', '621601'), ('E0203002', '621601'), ('E0203003', '621601'), ('E0203004', '621601'), ('E0203008', '621601'), ('E0204001', '621601'), ('E0204002', '621601'), ('E0205001', '621601'), ('E0205003', '621601'), ('E0206001', '621601'), ('E0206002', '621601'), ('E0206003', '621601'), ('E0206004', '621601'), ('E0206005', '621601'), ('E0206006', '621601'), ('E0206008', '621601'), ('E0206009', '621601'), ('E0206010', '621601'), ('E0206011', '621601'), ('E0206012', '621601'), ('E0206013', '621601'), ('E0206014', '621601'), ('E0206015', '621601'), ('E0206016', '621601'), ('E0206017', '621601'), ('E0206018', '621601'), ('E0206019', '621601'), ('E0206020', '621601'), ('E0206021', '621601'), ('E0206022', '621601'), ('E0206023', '621601'), ('E0206024', '621601'), ('E0206025', '621601'), ('E0206026', '621601'), ('E0206027', '621601'), ('E0206028', '621601'), ('E0206029', '621601'), ('E0207001', '621601'), ('E0207002', '621601'), ('E0207003', '621601'), ('E0207004', '621601'), ('E0207005', '621601'), ('E0207006', '621601'), ('E0207007', '621601'), ('E0207008', '621601'), ('E0207009', '621601'), ('E0207010', '621601'), ('E0207011', '621601'), ('E0207012', '621601'), ('E0208001', '621601'), ('E0208002', '621601'), ('E0208003', '621601'), ('E0208004', '621601'), ('E0208005', '621601'), ('E0208006', '621601'), ('E0209001', '621601'), ('E0210001', '621601'), ('E0211001', '621601'), ('E0211002', '621601'), ('E0211003', '621601'), ('E0211004', '621601'), ('E0212001', '621601'), ('E0213001', '621601'), ('E0213002', '621601'), ('E0301001', '621601'), ('E0301002', '621601'), ('E0301003', '621601'), ('E0302001', '621601'), ('E0302002', '621601'), ('E0302003', '621601'), ('E0302004', '621601'), ('E0302005', '621601'), ('E0302006', '621601'), ('E0302007', '621601'), ('E0302008', '621601'), ('E1001001', '621601'), ('E1001002', '621601'), ('E1001003', '621601'), ('E1002001', '621601'), ('E1002002', '621601'), ('E1101001', '621601'), ('E1101002', '621601'), ('E1101003', '621601'), ('E1102001', '621601'), ('E1103001', '621601'), ('E1104001', '621601'), ('E1104002', '621601'), ('E1105001', '621601'), ('E1106001', '621601'), ('E1107001', '621601'), ('E1108001', '621601'), ('E1109001', '621601'), ('E1110001', '621601'), ('E1111001', '621601'), ('E1111002', '621601'), ('E1112001', '621601'), ('E1112002', '621601'), ('E1112003', '621601'), ('E1113001', '621601'), ('E1113002', '621601'), ('E1201001', '621601'), ('E1201002', '621601'), ('E1205001', '621601'), ('E1205002', '621601'), ('E1205003', '621601'), ('E1205004', '621601'), ('E1205005', '621601'), ('E1206001', '621601'), ('E1206002', '621601'), ('E1206003', '621601'), ('E1206004', '621601'), ('E1206005', '621601'), ('E1207001', '621601'), ('E1207002', '621601'), ('E1207003', '621601'), ('E1207004', '621601'), ('E1208001', '621601'), ('E1208002', '621601'), ('E1208003', '621601'), ('E1208004', '621601'), ('E1208005', '621601'), ('E1208006', '621601'), ('E1208007', '621601'), ('E1208008', '621601'), ('E1208009', '621601'), ('E1209001', '621601'), ('E1210001', '621601'), ('E1211001', '621601'), ('E1211002', '621601'), ('E1211003', '621601'), ('E1211004', '621601')) x(code, acc)
WHERE m.company_code='OU' AND m.account_code_id IS NULL AND m.original_code = x.code
  AND a.company_code='OU' AND a.code = x.acc;

-- 3. 回填料號預設廠商（取其第一筆對照的廠商）
UPDATE cycle_purchase_items i SET default_vendor_id = m.vendor_id
FROM (SELECT DISTINCT ON (item_id) item_id, vendor_id FROM cycle_purchase_item_mappings WHERE company_code='OU' AND vendor_id IS NOT NULL ORDER BY item_id, id) m
WHERE i.id = m.item_id AND i.default_vendor_id IS NULL AND i.company_code='OU';

-- 4. 結果
SELECT 'mappings 已寫入' AS 項目, count(*) AS 筆數 FROM cycle_purchase_item_mappings WHERE company_code='OU'
UNION ALL SELECT 'mappings 應有', 929
UNION ALL SELECT 'mappings 仍缺廠商', count(*) FROM cycle_purchase_item_mappings WHERE company_code='OU' AND vendor_id IS NULL
UNION ALL SELECT 'mappings 仍缺科目', count(*) FROM cycle_purchase_item_mappings WHERE company_code='OU' AND account_code_id IS NULL;
COMMIT;
