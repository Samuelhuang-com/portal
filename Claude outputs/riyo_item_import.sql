-- 日曜（OU）料號主檔匯入 — 正式區 PostgreSQL（2026-11）
-- 來源：94479f98-20261002________-___.xlsx（料號 285 筆、類別 95 筆、部門對照 929 筆）
-- 執行：psql -h <主機> -U <使用者> -d <週採資料庫> -v ON_ERROR_STOP=1 -f riyo_item_import.sql
--
-- 行為：
--   1. 只有「料號代碼 OU-* 已存在」會中止（避免覆蓋既有資料）。
--   2. 廠商、會計科目、部門缺漏：不中止。料號照常寫入，缺的廠商／科目欄位留空；
--      缺部門的對照列先略過（部門是必填欄位），結尾會列出數量。
--   3. 缺漏補齊後，執行 riyo_item_fill.sql 即可補寫對照、回填廠商與科目（可重複執行）。
BEGIN;

-- A. 料號代碼重複檢查（唯一會中止的條件）
DO $$
DECLARE dup text;
BEGIN
  SELECT string_agg(i.item_code, '、') INTO dup
  FROM cycle_purchase_items i
  WHERE i.item_code IN ('OU-D0101001', 'OU-D0101002', 'OU-D0101003', 'OU-D0201001', 'OU-D0201002', 'OU-D0202001', 'OU-D0202002', 'OU-D0203001', 'OU-D0203002', 'OU-D0204001', 'OU-D0204002', 'OU-D0204003', 'OU-D0205001', 'OU-D0205002', 'OU-D0205003', 'OU-G0101001', 'OU-G0102001', 'OU-G0102002', 'OU-G0102003', 'OU-G0102004', 'OU-G0102005', 'OU-G0102006', 'OU-G0102007', 'OU-G0103001', 'OU-G0103002', 'OU-G0103003', 'OU-G0104001', 'OU-G0104002', 'OU-G0201001', 'OU-G0201002', 'OU-G0202001', 'OU-G0301001', 'OU-G0401001', 'OU-G0401002', 'OU-G0402001', 'OU-G0402002', 'OU-G0402003', 'OU-G0403001', 'OU-G0501001', 'OU-G0501002', 'OU-G0601001', 'OU-G0601002', 'OU-G0601003', 'OU-G0701001', 'OU-G0701002', 'OU-G0702001', 'OU-G0702002', 'OU-G0703001', 'OU-G0704001', 'OU-G1001001', 'OU-G1001002', 'OU-G1001003', 'OU-G1001004', 'OU-G1001005', 'OU-G1002001', 'OU-G1002002', 'OU-G1002003', 'OU-G1002004', 'OU-G1002005', 'OU-G1002006', 'OU-G1002007', 'OU-G1002008', 'OU-G1004001', 'OU-G1004002', 'OU-G1101001', 'OU-G1101002', 'OU-G1101005', 'OU-G1101006', 'OU-G1201001', 'OU-G1201003', 'OU-G1202001', 'OU-G1204001', 'OU-G1205001', 'OU-G1206001', 'OU-G1206002', 'OU-G1206003', 'OU-G1207001', 'OU-G1207002', 'OU-G1207003', 'OU-G1207004', 'OU-G1207005', 'OU-G1207006', 'OU-G1209001', 'OU-G1301001', 'OU-G1301004', 'OU-G1302001', 'OU-G1401001', 'OU-G1501001', 'OU-G1501002', 'OU-G1501003', 'OU-G1502001', 'OU-G1601001', 'OU-G1601002', 'OU-G1602001', 'OU-G1604001', 'OU-G1605001', 'OU-G1605002', 'OU-G1606001', 'OU-G1607001', 'OU-G1701001', 'OU-G1701002', 'OU-G9901003', 'OU-G9901004', 'OU-G9901007', 'OU-G9901008', 'OU-G9901009', 'OU-G9901010', 'OU-C0101001', 'OU-C0103001', 'OU-C0201001', 'OU-C0301001', 'OU-C0401001', 'OU-C0401002', 'OU-C0401003', 'OU-C0401004', 'OU-C0401005', 'OU-C0401006', 'OU-C0401007', 'OU-C0501013', 'OU-C0601001', 'OU-S0301001', 'OU-S0301002', 'OU-E0101001', 'OU-E0101002', 'OU-E0101003', 'OU-E0101004', 'OU-E0101005', 'OU-E0102001', 'OU-E0102002', 'OU-E0102003', 'OU-E0102004', 'OU-E0102005', 'OU-E0102006', 'OU-E0102007', 'OU-E0102008', 'OU-E0102009', 'OU-E0102010', 'OU-E0103001', 'OU-E0201001', 'OU-E0201002', 'OU-E0201003', 'OU-E0201004', 'OU-E0201005', 'OU-E0201006', 'OU-E0201007', 'OU-E0201008', 'OU-E0201009', 'OU-E0211006', 'OU-E0202001', 'OU-E0202002', 'OU-E0202003', 'OU-E0202004', 'OU-E0202005', 'OU-E0202006', 'OU-E0203001', 'OU-E0203002', 'OU-E0203003', 'OU-E0203004', 'OU-E0203008', 'OU-E0204001', 'OU-E0204002', 'OU-E0205001', 'OU-E0205003', 'OU-E0206001', 'OU-E0206002', 'OU-E0206003', 'OU-E0206004', 'OU-E0206005', 'OU-E0206006', 'OU-E0206008', 'OU-E0206009', 'OU-E0206010', 'OU-E0206011', 'OU-E0206012', 'OU-E0206013', 'OU-E0206014', 'OU-E0206015', 'OU-E0206016', 'OU-E0206017', 'OU-E0206018', 'OU-E0206019', 'OU-E0206020', 'OU-E0206021', 'OU-E0206022', 'OU-E0206023', 'OU-E0206024', 'OU-E0206025', 'OU-E0206026', 'OU-E0206027', 'OU-E0206028', 'OU-E0206029', 'OU-E0207001', 'OU-E0207002', 'OU-E0207003', 'OU-E0207004', 'OU-E0207005', 'OU-E0207006', 'OU-E0207007', 'OU-E0207008', 'OU-E0207009', 'OU-E0207010', 'OU-E0207011', 'OU-E0207012', 'OU-E0208001', 'OU-E0208002', 'OU-E0208003', 'OU-E0208004', 'OU-E0208005', 'OU-E0208006', 'OU-E0209001', 'OU-E0210001', 'OU-E0211001', 'OU-E0211002', 'OU-E0211003', 'OU-E0211004', 'OU-E0212001', 'OU-E0213001', 'OU-E0213002', 'OU-E0301001', 'OU-E0301002', 'OU-E0301003', 'OU-E0302001', 'OU-E0302002', 'OU-E0302003', 'OU-E0302004', 'OU-E0302005', 'OU-E0302006', 'OU-E0302007', 'OU-E0302008', 'OU-E1001001', 'OU-E1001002', 'OU-E1001003', 'OU-E1002001', 'OU-E1002002', 'OU-E1101001', 'OU-E1101002', 'OU-E1101003', 'OU-E1102001', 'OU-E1103001', 'OU-E1104001', 'OU-E1104002', 'OU-E1105001', 'OU-E1106001', 'OU-E1107001', 'OU-E1108001', 'OU-E1109001', 'OU-E1110001', 'OU-E1111001', 'OU-E1111002', 'OU-E1112001', 'OU-E1112002', 'OU-E1112003', 'OU-E1113001', 'OU-E1113002', 'OU-E1201001', 'OU-E1201002', 'OU-E1205001', 'OU-E1205002', 'OU-E1205003', 'OU-E1205004', 'OU-E1205005', 'OU-E1206001', 'OU-E1206002', 'OU-E1206003', 'OU-E1206004', 'OU-E1206005', 'OU-E1207001', 'OU-E1207002', 'OU-E1207003', 'OU-E1207004', 'OU-E1208001', 'OU-E1208002', 'OU-E1208003', 'OU-E1208004', 'OU-E1208005', 'OU-E1208006', 'OU-E1208007', 'OU-E1208008', 'OU-E1208009', 'OU-E1209001', 'OU-E1210001', 'OU-E1211001', 'OU-E1211002', 'OU-E1211003', 'OU-E1211004');
  IF dup IS NOT NULL THEN
    RAISE EXCEPTION E'料號代碼已存在，已中止匯入（未寫入任何資料）：
%', dup;
  END IF;
END $$;

-- B. 缺漏主檔提示（僅提示，不中止）
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT 'vendor' AS kind, n.name AS value FROM (VALUES
      ('嘉嶽企業有限公司'),
  ('大裕紙袋股份有限公司'),
  ('廷軒有限公司'),
  ('必凡思國際有限公司'),
  ('捷彬科技有限公司'),
  ('旭成科技製造有限公司'),
  ('昉珩壓克力企業社'),
  ('柏辰企業社'),
  ('森達利興業有限公司'),
  ('永豐紙業股份有限公司'),
  ('永豐餘消費品實業股份有限公司'),
  ('泓昇環境工程股份有限公司'),
  ('湯圓形象設計工作室'),
  ('瑞眾股份有限公司'),
  ('盛彪股份有限公司'),
  ('羽任電池專賣店'),
  ('聯合世貿有限公司'),
  ('萬視達廣告設計有限公司'),
  ('藍格印刷國際企業有限公思'),
  ('金利五金行'),
  ('駿湧有限公司')) n(name)
      WHERE NOT EXISTS (SELECT 1 FROM cycle_purchase_vendors v WHERE v.company_code='OU' AND v.vendor_name=n.name)
    UNION ALL
    SELECT 'account', n.code FROM (VALUES
      ('621201'),
  ('621202'),
  ('621601'),
  ('621702'),
  ('6238')) n(code)
      WHERE NOT EXISTS (SELECT 1 FROM cycle_purchase_account_codes a WHERE a.company_code='OU' AND a.code=n.code)
    UNION ALL
    SELECT 'department', n.name FROM (VALUES
      ('人資部'),
  ('客服部'),
  ('營業部'),
  ('管理部'),
  ('系統輔導暨統購稽核部'),
  ('行銷部'),
  ('設計部'),
  ('財務部')) n(name)
      WHERE NOT EXISTS (SELECT 1 FROM cycle_purchase_departments d WHERE d.company_code='OU' AND d.dept_name=n.name AND d.is_active)
  LOOP
    RAISE NOTICE '缺少主檔（之後補正）：% → %', r.kind, r.value;
  END LOOP;
END $$;

-- C. 類別主檔
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'C', '清潔', '01', '衛生紙', '01', '捲筒', '衛生紙-捲筒', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'C', '清潔', '01', '衛生紙', '03', '衛生紙', '衛生紙', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'C', '清潔', '02', '洗手乳', '01', '洗手乳', '洗手乳', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'C', '清潔', '03', '芳香品', '01', '芳香品', '芳香品', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'C', '清潔', '04', '垃圾袋', '01', '垃圾袋', '垃圾袋', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'C', '清潔', '05', '清潔劑', '01', '清潔劑', '清潔劑-小便斗', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'C', '清潔', '06', '酒精', '01', '酒精', '清潔劑-消毒', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'D', '製作物', '01', '旗幟', '01', '旗幟', '旗幟', 3, true, '大分類 D（製作物）為 2026-11 依需求新增，規則表未定義，名稱依 Excel 類別字串')
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'D', '製作物', '02', '輪出', '01', '地貼', '輪出-地貼', 3, true, '大分類 D（製作物）為 2026-11 依需求新增，規則表未定義，名稱依 Excel 類別字串')
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'D', '製作物', '02', '輪出', '02', '電梯貼', '輪出-電梯貼', 3, true, '大分類 D（製作物）為 2026-11 依需求新增，規則表未定義，名稱依 Excel 類別字串')
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'D', '製作物', '02', '輪出', '03', '電梯牆', '輪出-電梯牆', 3, true, '大分類 D（製作物）為 2026-11 依需求新增，規則表未定義，名稱依 Excel 類別字串')
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'D', '製作物', '02', '輪出', '04', '合成板', '輪出-合成板', 3, true, '大分類 D（製作物）為 2026-11 依需求新增，規則表未定義，名稱依 Excel 類別字串')
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'D', '製作物', '02', '輪出', '05', '相紙', '輪出-相紙', 3, true, '大分類 D（製作物）為 2026-11 依需求新增，規則表未定義，名稱依 Excel 類別字串')
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '01', '空調備品', '01', '濾網', '空調備品-濾網', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '01', '空調備品', '02', '皮帶', '空調備品-皮帶', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '01', '空調備品', '03', '藥劑', '空調備品-藥劑', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '02', '照明', '01', '燈泡', '照明-燈泡', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '02', '照明', '02', '崁燈', '照明-崁燈', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '02', '照明', '03', '投射燈', '照明-投射燈', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '02', '照明', '04', '軌道燈', '照明-軌道燈', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '02', '照明', '05', '平板燈', '照明-平板燈', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '02', '照明', '06', '燈管', '照明-燈管', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '02', '照明', '07', '串接燈具', '照明-串接燈具', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '02', '照明', '08', '支架燈', '照明-支架燈', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '02', '照明', '09', '山型燈具', '照明-山型燈具', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '02', '照明', '10', '反射型燈具', '照明-反射型燈具', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '02', '照明', '11', '杯燈', '照明-杯燈', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '02', '照明', '12', '燈座', '照明-燈座', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '02', '照明', '13', '燈頭', '照明-燈頭', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '03', '斷路器', '01', '斷路器', '斷路器', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '03', '斷路器', '02', '斷路器', '斷路器', 3, true, '細分類名稱來源未定義，暫以中分類名稱代替')
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '10', '送風機', '01', '馬達', '送風機-馬達', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '10', '送風機', '02', '風鼓', '送風機-風鼓', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '11', '消防設備', '01', '偵煙器模組', '消防設備-偵煙器模組', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '11', '消防設備', '02', '差動火警探測器', '消防設備-差動火警探測器', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '11', '消防設備', '03', '偵煙探測器', '消防設備-偵煙探測器', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '11', '消防設備', '04', '手動排煙開關', '消防設備-手動排煙開關', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '11', '消防設備', '05', '火警發信機', '消防設備-火警發信機', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '11', '消防設備', '06', '滅火器掛勾', '消防設備-滅火器掛勾', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '11', '消防設備', '07', '壓力開關', '消防設備-壓力開關', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '11', '消防設備', '08', '蜂鳴器', '消防設備-蜂鳴器', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '11', '消防設備', '09', '手動報警器', '消防設備-手動報警器', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '11', '消防設備', '10', '泡沫手動開關盒', '消防設備-泡沫手動開關盒', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '11', '消防設備', '11', 'E燈電池', '消防設備-E燈電池', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '11', '消防設備', '12', 'LED燈', '消防設備-LED燈', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '11', '消防設備', '13', '消防廣播喇叭', '消防設備-廣播喇叭', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '12', '工務零件', '01', '定時器', '工務零件-定時器', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '12', '工務零件', '05', '蓋板', '工務零件-蓋板', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '12', '工務零件', '06', '壓條', '工務零件-壓條', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '12', '工務零件', '07', '軌道', '工務零件-軌道', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '12', '工務零件', '08', '插頭/插座', '工務零件-插座', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '12', '工務零件', '09', '美術盒', '工務零件-美術盒', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '12', '工務零件', '10', '手套', '工務零件-手套棉紗', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'E', '工程', '12', '工務零件', '11', '肘動精密陶瓷自由栓', '工務零件-肘動精密陶瓷自由栓', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '01', '印刷', '01', '信封/卡套', '印刷-信封/卡套', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '01', '印刷', '02', '各類表單', '印刷-各類表單', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '01', '印刷', '03', '紙袋', '印刷-紙袋', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '01', '印刷', '04', '塑膠袋', '印刷-塑膠袋', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '02', '紙', '01', '空白', '紙', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '02', '紙', '02', '美術紙', '紙', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '03', '電池', '01', '鹼性', '電池-鹼性', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '04', '膠帶', '01', '雙面', '膠帶-雙面', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '04', '膠帶', '02', '透明', '膠帶-透明', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '04', '膠帶', '03', '布膠帶', '膠帶-布膠帶', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '05', '束線帶', '01', '束線帶', '束線帶', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '06', '便利貼', '01', '便利貼', '便利貼', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '07', '標籤貼', '01', '自黏', '標籤貼-自黏', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '07', '標籤貼', '02', '索引', '標籤貼-索引', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '07', '標籤貼', '03', '非抽取', '標籤貼-非抽取', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '07', '標籤貼', '04', '抽取', '標籤貼-抽取', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '10', '筆', '01', '螢光', '筆-螢光', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '10', '筆', '02', '原子筆', '筆-原子筆', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '10', '筆', '04', '自動鉛筆', '筆-自動鉛筆', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '11', '修正', '01', '修正帶', '修正-修正帶', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '12', '整理', '01', '膠水', '整理-膠水', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '12', '整理', '02', '口紅膠', '整理-口紅膠', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '12', '整理', '04', '釘書機', '整理-釘書機', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '12', '整理', '05', '釘書針', '整理-釘書針', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '12', '整理', '06', '迴紋針', '整理-迴紋針', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '12', '整理', '07', '長尾夾', '整理-長尾夾', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '12', '整理', '09', '拔釘器', '整理-拔釘器', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '13', '刀', '01', '刀', '刀', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '13', '刀', '02', '剪刀', '刀-剪刀', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '14', '尺', '01', '尺', '尺', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '15', '收納', '01', '夾鏈袋', '收納-夾鏈袋', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '15', '收納', '02', '公文架', '收納-公文架', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '16', '資料檔案夾', '01', 'D型', '資料檔案夾-D型', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '16', '資料檔案夾', '02', 'L型', '資料檔案夾-L型', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '16', '資料檔案夾', '04', '資料簿', '資料檔案夾-資料簿', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '16', '資料檔案夾', '05', '卷宗', '資料檔案夾-卷宗', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '16', '資料檔案夾', '06', '文件套', '資料檔案夾-文件套', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '16', '資料檔案夾', '07', '板夾', '資料檔案夾-板夾', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '17', '印章', '01', '印泥', '印章-印台', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'G', '文具', '99', '文具', '01', '其他', '文具-其他', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;
INSERT INTO cycle_purchase_categories
  (company_code, company, department_id, major_code, major_name, mid_code, mid_name, sub_code, sub_name, category_name, serial_width, is_active, notes)
VALUES ('OU', '日曜天地', NULL, 'S', '營業用品', '03', '塑膠袋', '01', '塑膠袋', '塑膠袋', 3, true, NULL)
ON CONFLICT ON CONSTRAINT uq_cp_category_company_codes DO NOTHING;

-- D. 料號
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0101001', '路燈旗(戶外帆布360dpi', '60*220cm)', '旗幟', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='01' AND sub_code='01'), '張', 0, 0, NULL, NULL, 450, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；位置：商場廁所用；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0101002', '1F走道旗(油性單透布', '50*200cm）', '旗幟', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='01' AND sub_code='01'), '張', 0, 0, NULL, NULL, 400, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；位置：公區廁所用；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0101003', '2F走道吊牌(PP霧+裁型', '58*38cm）', '旗幟', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='01' AND sub_code='01'), '張', 0, 0, NULL, NULL, 120, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；位置：客房用；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0201001', '1F地貼(R膠+霧PVC', '299*90cm）', '輪出-地貼', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='02' AND sub_code='01'), '張', 0, 0, NULL, NULL, 900, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='萬視達廣告設計有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；位置：商場廁所用；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0201002', '2F地貼(R膠+霧PVC', '270*45cm）', '輪出-地貼', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='02' AND sub_code='01'), '張', 0, 0, NULL, NULL, 420, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='萬視達廣告設計有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；位置：商場廁所用；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0202001', '內側電梯貼(霧PVC', '100*30cm）', '輪出-電梯貼', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='02' AND sub_code='02'), '張', 0, 0, NULL, NULL, 120, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='萬視達廣告設計有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0202002', '外側電梯貼(霧PVC', '108*11cm）', '輪出-電梯貼', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='02' AND sub_code='02'), '張', 0, 0, NULL, NULL, 60, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='萬視達廣告設計有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0203001', '6F電梯牆-貼(霧PVC', '222*210cm)', '輪出-電梯牆', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='02' AND sub_code='03'), '張', 0, 0, NULL, NULL, 2340, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='萬視達廣告設計有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0203002', '6F電梯牆-板(合成板+霧PVC', '222*210cm)', '輪出-電梯牆', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='02' AND sub_code='03'), '張', 0, 0, NULL, NULL, 1560, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0204001', '折扣板(合成板+霧PVC', '44.5*63cm）', '輪出-合成板', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='02' AND sub_code='04'), '張', 0, 0, NULL, NULL, 180, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0204002', 'HG板(合成板+霧PVC', '90*15cm）', '輪出-合成板', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='02' AND sub_code='04'), '張', 0, 0, NULL, NULL, 150, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0204003', '中横眉(合成板+霧PVC', '250*50cm）', '輪出-合成板', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='02' AND sub_code='04'), '張', 0, 0, NULL, NULL, 630, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0205001', '小花車(PP', '82*50cm)', '輪出-相紙', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='02' AND sub_code='05'), '張', 0, 0, NULL, NULL, 175, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0205002', '大花車(PP', '98*60cm)', '輪出-相紙', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='02' AND sub_code='05'), '張', 0, 0, NULL, NULL, 245, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='駿湧有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-D0205003', '主題牆(PP', '705*140cm)', '輪出-相紙', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='D' AND mid_code='02' AND sub_code='05'), '張', 0, 0, NULL, NULL, 3885, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='萬視達廣告設計有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（製作物）；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0101001', '日曜-彩色信封12開西式100g道林', NULL, '印刷-信封/卡套', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='01' AND sub_code='01'), '個', 0, 3000, 3100, 100, 0.8133, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='藍格印刷國際企業有限公思' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；備註：2024單價；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0102001', '日曜-專櫃人員手冊', 'A5', '印刷-各類表單', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='01' AND sub_code='02'), '本', 0, 500, 560, 60, 20.5, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0102002', '日曜-會員卡申請單', NULL, '印刷-各類表單', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='01' AND sub_code='02'), '張', 0, 3000, 3100, 100, 0.7, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='湯圓形象設計工作室' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0102003', '日曜-專櫃代班單', NULL, '印刷-各類表單', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='01' AND sub_code='02'), '本', 0, 50, 52, 2, 50, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0102004', '日曜-進場單', NULL, '印刷-各類表單', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='01' AND sub_code='02'), '本', 0, 20, 22, 2, 99, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0102005', '日曜-營業日報表A5(專櫃用)', NULL, '印刷-各類表單', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='01' AND sub_code='02'), '本', 0, 0, NULL, NULL, 31, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0102006', '日曜-銷貨日報表A5(專櫃用)', NULL, '印刷-各類表單', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='01' AND sub_code='02'), '本', 0, 0, NULL, NULL, 28, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0102007', '日曜-退稅單', NULL, '印刷-各類表單', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='01' AND sub_code='02'), '本', 0, 0, NULL, NULL, 41, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='柏辰企業社' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0103001', '日曜-綠色紙袋-大(專櫃用)', NULL, '印刷-紙袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='01' AND sub_code='03'), '個', 0, 0, NULL, NULL, 6, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0103002', '日曜-綠色紙袋-中(專櫃用)', NULL, '印刷-紙袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='01' AND sub_code='03'), '個', 0, 0, NULL, NULL, 4.6, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0103003', '日曜-綠色紙袋-小(專櫃用)', NULL, '印刷-紙袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='01' AND sub_code='03'), '個', 0, 0, NULL, NULL, 4, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='大裕紙袋股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0104001', '日曜-塑膠袋-大(專櫃用)', NULL, '印刷-塑膠袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='01' AND sub_code='04'), '個', 0, 40000, 45000, 5000, 4.2, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0104002', '日曜-塑膠袋-小(專櫃用)', NULL, '印刷-塑膠袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='01' AND sub_code='04'), '個', 0, 40000, 45000, 5000, 3, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0201001', 'smartist', '70g A4影印紙', '紙', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='02' AND sub_code='01'), '包', 0, 0, NULL, NULL, 73, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0201002', 'smartist', '70g A3影印紙', '紙', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='02' AND sub_code='01'), '包', 0, 0, NULL, NULL, 113, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0202001', 'A4丹迪紙', NULL, '紙', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='02' AND sub_code='02'), '包', 0, 1, 2, 1, 47, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0301001', '國際/2號/鹼性電池', '(2入/組)', '電池-鹼性', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='03' AND sub_code='01'), '封', 0, 1, 3, 2, 70, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0401001', '人棉布雙面膠帶20*25M', NULL, '膠帶-雙面', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='04' AND sub_code='01'), '個', 0, 1, 3, 2, 155, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0401002', '人棉布雙面膠帶10*25M', NULL, '膠帶-雙面', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='04' AND sub_code='01'), '個', 0, 1, 3, 2, 75, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0402001', '透明膠帶12MM', '40Y', '膠帶-透明', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='04' AND sub_code='02'), '個', 0, 12, 15, 3, 8, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0402002', '透明膠帶18MM', '40Y', '膠帶-透明', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='04' AND sub_code='02'), '個', 0, 8, 11, 3, 11, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0402003', '透明膠帶48MM', '40Y', '膠帶-透明', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='04' AND sub_code='02'), '個', 0, 6, 9, 3, 24, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0403001', '2048R', '強力防水布膠帶紅', '膠帶-布膠帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='04' AND sub_code='03'), '個', 0, 1, 2, 1, 90, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0501001', '開明', '100事務用帶 黑 45cm (45條一束)', '束線帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='05' AND sub_code='01'), '束', 0, 1, 2, 1, 68, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0501002', '開明', '240 事務用帶 黑 61cm (24條一束) (扁)', '束線帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='05' AND sub_code='01'), '束', 0, 1, 2, 1, 72, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0601001', '10.16*10.16CM便利貼(副總用)', NULL, '便利貼', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='06' AND sub_code='01'), '包', 0, 3, 4, 1, 43, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0601002', '7.6*7.6CM便利貼', NULL, '便利貼', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='06' AND sub_code='01'), '包', 0, 3, 5, 2, 26, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0601003', '7.5*5CM便利貼', NULL, '便利貼', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='06' AND sub_code='01'), '包', 0, 3, 5, 2, 26, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0701001', 'WL-1007自黏性標籤貼', NULL, '標籤貼-自黏', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='07' AND sub_code='01'), '包', 0, 1, 2, 1, 9.5, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0701002', 'WL-1017自黏性標籤貼(紅框)', NULL, '標籤貼-自黏', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='07' AND sub_code='01'), '包', 0, 1, 2, 1, 9.5, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0702001', 'N次貼', '66514 可再貼分類索引片 28*25MM 60片/包', '標籤貼-索引', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='07' AND sub_code='02'), '包', 0, 1, 2, 1, 40, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0702002', 'LONGDER龍德', 'LD-701 五彩雙面索引片 26*34mm,30片/包', '標籤貼-索引', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='07' AND sub_code='02'), '包', 0, 1, 2, 1, 15, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0703001', '3M', 'Post-it 583-9非抽取式-可再貼全彩標籤9色', '標籤貼-非抽取', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='07' AND sub_code='03'), '包', 0, 0, NULL, NULL, 33, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G0704001', '3M', 'Scotch 680 (Sign Here)抽取式標籤2卡入超值包 Sign Here', '標籤貼-抽取', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='07' AND sub_code='04'), '包', 0, 0, NULL, NULL, 77, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1001001', 'Pentel飛龍', 'S512螢光筆3.5mm 藍', '筆-螢光', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='01'), '支', 0, 1, 3, 2, 11, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1001002', 'Pentel飛龍', 'S512螢光筆3.5mm 綠', '筆-螢光', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='01'), '支', 0, 1, 3, 2, 11, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1001003', 'Pentel飛龍', 'S512螢光筆3.5mm 黃', '筆-螢光', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='01'), '支', 0, 1, 3, 2, 11, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1001004', 'Pentel飛龍', 'S512螢光筆3.5mm 粉', '筆-螢光', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='01'), '支', 0, 1, 3, 2, 11, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1001005', 'Pentel飛龍', 'S512螢光筆3.5mm 橘', '筆-螢光', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='01'), '支', 0, 1, 3, 2, 11, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1002001', 'SKB', 'IB-100自動中油筆0.5MM藍', '筆-原子筆', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='02'), '支', 0, 1, 3, 2, 6.5, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1002002', 'SKB', 'IB-100自動中油筆0.5MM紅', '筆-原子筆', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='02'), '支', 0, 1, 3, 2, 6.5, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1002003', 'SKB', 'IB-100自動中油筆0.5MM黑', '筆-原子筆', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='02'), '支', 0, 1, 3, 2, 6.5, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1002004', '雄獅', 'GL-533 速乾中性筆0.7藍', '筆-原子筆', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='02'), '支', 0, 1, 3, 2, 11, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1002005', '雄獅', 'GL-533 速乾中性筆0.7紅', '筆-原子筆', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='02'), '支', 0, 1, 3, 2, 11, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1002006', '雄獅', 'GL-533 速乾中性筆0.7黑', '筆-原子筆', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='02'), '支', 0, 1, 3, 2, 11, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1002007', 'UNI三菱', 'UM-151 0.38超細鋼珠筆 藍', '筆-原子筆', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='02'), '支', 0, 1, 2, 1, 32, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1002008', 'UNI三菱', 'UM-151 0.38超細鋼珠筆 黑', '筆-原子筆', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='02'), '支', 0, 1, 2, 1, 32, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1004001', 'Pentel飛龍', 'A105 自動鉛筆0.5mm', '筆-自動鉛筆', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='04'), '支', 0, 1, 2, 1, 23, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1004002', 'Pentel飛龍', 'C205-HB 自動鉛筆芯0.5mm', '筆-自動鉛筆', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='10' AND sub_code='04'), '支', 0, 1, 2, 1, 28.5, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1101001', 'PLUS普樂士', 'WH-605 滾輪修正帶5mm*6m 白綠', '修正-修正帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='11' AND sub_code='01'), '組', 0, 1, 3, 2, 35, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1101002', 'PLUS普樂士', 'WH-605 滾輪修正帶內帶', '修正-修正帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='11' AND sub_code='01'), '個', 0, 1, 3, 2, 25, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1101005', 'SDI手牌', 'CT-205 iPUSH輕鬆按修正帶5mm*6M 藍', '修正-修正帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='11' AND sub_code='01'), '組', 0, 1, 3, 2, 45, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1101006', 'SDI手牌', 'CT-205R iPUSH修正帶內帶', '修正-修正帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='11' AND sub_code='01'), '個', 0, 1, 3, 2, 26, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1201001', 'SIMBALION雄獅', '50cc 合成糊', '整理-膠水', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='01'), '瓶', 0, 1, 2, 1, 8, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1201003', '妙妙', 'HY-503 500CC補充膠水', '整理-膠水', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='01'), '瓶', 0, 1, 2, 1, 56, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1202001', 'SIMBALION雄獅', 'GS104口紅膠 8g', '整理-口紅膠', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='02'), '支', 0, 1, 3, 2, 8, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1204001', 'SDI手牌', '1102B 簡約實用型釘書機10號', '整理-釘書機', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='04'), '個', 0, 1, 2, 1, 39, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1205001', 'PLUS普樂士', '30-111 No.10 釘書針(30-925)(20小盒入)', '整理-釘書針', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='05'), '盒', 0, 20, 25, 5, 95, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1206001', 'SDI手牌', '0706B 圓型特大迴紋針(50mm)', '整理-迴紋針', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='06'), '盒', 0, 1, 4, 3, 33, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1206002', 'SDI手牌', '0702B 圓型迴紋針(28mm)', '整理-迴紋針', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='06'), '盒', 0, 1, 2, 1, 13, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1206003', 'SDI手牌', '0731B 三角迴紋針(25.4mm)', '整理-迴紋針', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='06'), '盒', 0, 1, 2, 1, 13, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1207001', 'SDI手牌', '0222B 黑色長尾夾 51mm', '整理-長尾夾', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='07'), '盒', 0, 1, 3, 2, 78, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1207002', 'SDI手牌', '0223B 黑色長尾夾 41mm', '整理-長尾夾', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='07'), '盒', 0, 1, 3, 2, 55, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1207003', 'SDI手牌', '0224B 黑色長尾夾 32mm', '整理-長尾夾', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='07'), '盒', 0, 1, 3, 2, 30, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1207004', 'SDI手牌', '0225B 黑色長尾夾 25mm', '整理-長尾夾', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='07'), '盒', 0, 1, 3, 2, 25, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1207005', 'SDI手牌', '0226B 黑色長尾夾 19mm', '整理-長尾夾', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='07'), '盒', 0, 1, 3, 2, 18, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1207006', 'SDI手牌', '0227B 黑色長尾夾 15mm', '整理-長尾夾', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='07'), '盒', 0, 1, 3, 2, 17, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1209001', 'NO.1116', '強力型拔釘器', '整理-拔釘器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='12' AND sub_code='09'), '個', 0, 1, 3, 2, 32, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1301001', 'OLFA', 'OUTTER極致系列小型美工刀', '刀', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='13' AND sub_code='01'), '支', 0, 1, 1, 0, 152, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1301004', 'ABEL力大', '66001小美工刀片', '刀', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='13' AND sub_code='01'), '盒', 0, 1, 1, 0, 18, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1302001', 'SS-40高級家庭事務剪刀', NULL, '刀-剪刀', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='13' AND sub_code='02'), '支', 0, 1, 2, 1, 26, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1401001', 'Penrote筆樂', 'TD7770 鋼尺30cm', '尺', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='14' AND sub_code='01'), '支', 0, 1, 1, 0, 30, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1501001', 'PE3夾鍊袋3#7*10cm(100個/包)', NULL, '收納-夾鏈袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='15' AND sub_code='01'), '包', 0, 1, 2, 1, 16, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1501002', 'PE4夾鍊袋4#8.5*12cm(100個/包)', NULL, '收納-夾鏈袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='15' AND sub_code='01'), '包', 0, 1, 2, 1, 20, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1501003', 'PE1夾鍊袋1#5*7cm(100個/包)', NULL, '收納-夾鏈袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='15' AND sub_code='01'), '包', 0, 1, 2, 1, 11, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1502001', 'BH-553', '三層公文架 A4 (米色) ^33.5*25.8*6cm,附鐵支架,12組/箱', '收納-公文架', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='15' AND sub_code='02'), '組', 0, 1, 1, 0, 195, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1601001', '自強', 'D15 三孔D型夾', '資料檔案夾-D型', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='16' AND sub_code='01'), '個', 0, 1, 2, 1, 150, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1601002', '自強D20三', '孔D型夾', '資料檔案夾-D型', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='16' AND sub_code='01'), '個', 0, 1, 1, 0, 210, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1602001', 'L型文件套12入', '白', '資料檔案夾-L型', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='16' AND sub_code='02'), '包', 0, 1, 3, 2, 33, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1604001', 'AS-40C', '實用資料簿藍', '資料檔案夾-資料簿', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='16' AND sub_code='04'), '個', 0, 1, 1, 0, 61, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1605001', '萬國', '中式卷宗直式附套-藍', '資料檔案夾-卷宗', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='16' AND sub_code='05'), '個', 0, 1, 3, 2, 25, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1605002', '萬國', '中式卷宗直式附套-紅', '資料檔案夾-卷宗', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='16' AND sub_code='05'), '個', 0, 1, 3, 2, 25, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1606001', '粉彩5入附桿文件套', NULL, '資料檔案夾-文件套', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='16' AND sub_code='06'), '組', 0, 2, 3, 1, 39, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1607001', 'A4壓克力板夾', NULL, '資料檔案夾-板夾', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='16' AND sub_code='07'), '個', 0, 1, 1, 0, 44, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1701001', '萬年紅', '艾絨印尼 大', '印章-印台', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='17' AND sub_code='01'), '個', 0, 1, 1, 0, 180, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G1701002', 'LIBERTY利百代', 'MS-50明色印尼', '印章-印台', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='17' AND sub_code='01'), '個', 0, 1, 1, 0, 77, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G9901003', '66803', 'A3切割墊 綠', '文具-其他', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='99' AND sub_code='01'), '片', 0, 1, 1, 0, 95, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G9901004', '普通橡皮圈', '18號4兩', '文具-其他', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='99' AND sub_code='01'), '包', 0, 1, 2, 1, 39, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='盛彪股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G9901007', 'A3壓克力板', NULL, '文具-其他', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='99' AND sub_code='01'), '個', 0, 0, NULL, NULL, 210, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='昉珩壓克力企業社' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G9901008', '日曜-專櫃用名牌', NULL, '文具-其他', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='99' AND sub_code='01'), '個', 0, 0, NULL, NULL, 219, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='必凡思國際有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G9901009', '舊式pos機清機條', '空白紙捲(無黑點-警告線) 41mm*48M 200捲/箱', '文具-其他', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='99' AND sub_code='01'), '箱', 0, 200, 220, 20, 15, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-G9901010', '電子發票感熱紙捲', '寬57mm外徑8cm 48捲/箱', '文具-其他', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='G' AND mid_code='99' AND sub_code='01'), '箱', 0, 1536, 1586, 50, 30, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐紙業股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（文具&印刷）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-C0101001', '五月花大捲筒衛生紙', '#0105054 1公斤  3捲*4袋/箱', '衛生紙-捲筒', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='C' AND mid_code='01' AND sub_code='01'), '箱', 0, 15, 18, 3, 680, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐餘消費品實業股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（清潔用品）；位置：商場廁所用；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-C0103001', '五月花摺疊紙巾', '200抽*20包/箱', '衛生紙', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='C' AND mid_code='01' AND sub_code='03'), '箱', 0, 15, 18, 3, 495, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='永豐餘消費品實業股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（清潔用品）；位置：商場廁所用；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-C0201001', '珍珠洗手乳#2211-32001', '1加侖/4桶/箱', '洗手乳', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='C' AND mid_code='02' AND sub_code='01'), '桶', 0, 4, 5, 1, 140, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（清潔用品）；位置：商場廁所用；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-C0301001', '鐵罐香罐', '檸檬', '芳香品', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='C' AND mid_code='03' AND sub_code='01'), '罐', 0, 6, 6, 0, 120, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（清潔用品）；位置：商場廁所用；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-C0401001', '50斤垃圾袋', '白50包/件 1包/6張 90*105CM', '垃圾袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='C' AND mid_code='04' AND sub_code='01'), '包', 0, 30, 40, 10, 21, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（清潔用品）；位置：商場用；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-C0401002', 'CR連潔垃圾袋白(特大)18張/24捲/箱', '80*95CM', '垃圾袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='C' AND mid_code='04' AND sub_code='01'), '捲', 0, 4, 5, 1, 55.83, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（清潔用品）；位置：商場用；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-C0401003', 'CR連潔垃圾袋白(大)40張/24捲/箱', '65*80CM', '垃圾袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='C' AND mid_code='04' AND sub_code='01'), '捲', 0, 6, 8, 2, 55.83, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（清潔用品）；位置：商場用；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-C0401004', 'CRPST垃圾袋白(中)73張*24捲/箱', '54*57CM', '垃圾袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='C' AND mid_code='04' AND sub_code='01'), '捲', 0, 1, 2, 1, 55.83, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（清潔用品）；位置：商場用；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-C0401005', 'CRPST垃圾袋白(小)100張*24捲/箱45*55CM', NULL, '垃圾袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='C' AND mid_code='04' AND sub_code='01'), '捲', 0, 1, 2, 1, 55.83, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（清潔用品）；位置：商場用；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-C0401006', '客房垃圾袋白(小)', '24捲/箱40*50CM', '垃圾袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='C' AND mid_code='04' AND sub_code='01'), '捲', 0, 0, NULL, NULL, 55.83, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（清潔用品）；位置：飯店；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-C0401007', '連潔清潔袋白10張/12支/箱120*140CM', NULL, '垃圾袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='C' AND mid_code='04' AND sub_code='01'), '支', 0, 12, 15, 3, 1340, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（清潔用品）；位置：9F回收區用；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-C0501013', 'Duskin小便斗藥劑', NULL, '清潔劑-小便斗', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='C' AND mid_code='05' AND sub_code='01'), '顆', 0, 5, 5, 0, 140, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（清潔用品）；位置：商場廁所用；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-C0601001', '75%清菌用酒精#4601-32011', '4000ml/6桶/箱', '清潔劑-消毒', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='C' AND mid_code='06' AND sub_code='01'), '桶', 0, 4, 5, 1, 300, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='聯合世貿有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（清潔用品）；位置：商場廁所/服務台用；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-S0301001', '白色塑膠袋-大', NULL, '塑膠袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='S' AND mid_code='03' AND sub_code='01'), '個', 0, 40000, 45000, 5000, 4.2, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（營業用品）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-S0301002', '白色塑膠袋-小', NULL, '塑膠袋', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='S' AND mid_code='03' AND sub_code='01'), '個', 0, 40000, 45000, 5000, 3, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='廷軒有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（營業用品）；月結：30天');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0101001', '天基-濾網400風量(塑膠尼龍纖維)', NULL, '空調備品-濾網', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='01'), '片', 0, 0, NULL, NULL, NULL, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：商場全區∕飯店全區；月結：30天；來源未提供單價；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0101002', '天基-濾網600風量(塑膠尼龍纖維)', NULL, '空調備品-濾網', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='01'), '片', 0, 0, NULL, NULL, NULL, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：商場全區∕飯店全區；月結：30天；來源未提供單價；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0101003', '天基-濾網800風量(塑膠尼龍纖維)', NULL, '空調備品-濾網', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='01'), '片', 0, 0, NULL, NULL, NULL, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：商場全區∕飯店全區；月結：30天；來源未提供單價；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0101004', '天基-濾網1000風量(塑膠尼龍纖維)', NULL, '空調備品-濾網', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='01'), '片', 0, 0, NULL, NULL, NULL, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：商場全區∕飯店全區；月結：30天；來源未提供單價；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0101005', '天基-濾網1200風量(塑膠尼龍纖維)', NULL, '空調備品-濾網', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='01'), '片', 0, 0, NULL, NULL, NULL, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：商場全區∕飯店全區；月結：30天；來源未提供單價；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0102001', '皮帶-冷氣用三角帶SPZ950', NULL, '空調備品-皮帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='02'), '條', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0102002', '皮帶-散熱水塔冷氣三角帶B158', NULL, '空調備品-皮帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='02'), '條', 0, 0, NULL, NULL, 487, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0102003', '皮帶-空調預冷機三角帶SPZ1087', NULL, '空調備品-皮帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='02'), '條', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0102004', '皮帶-SPZ1287', NULL, '空調備品-皮帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='02'), '條', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：RF客房排氣機；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0102005', '皮帶-SPZ1320', NULL, '空調備品-皮帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='02'), '條', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：2F排氣機；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0102006', '皮帶-SPZ1462', NULL, '空調備品-皮帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='02'), '條', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：6F停車場8F排氣機；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0102007', '皮帶-SPZ1112', NULL, '空調備品-皮帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='02'), '條', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：2F預冷機；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0102008', '皮帶-SPZ1037', NULL, '空調備品-皮帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='02'), '條', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：飯店各樓層愈冷空調箱；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0102009', '皮帶-B56', NULL, '空調備品-皮帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='02'), '條', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：1F排氣機；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0102010', '皮帶-B96', NULL, '空調備品-皮帶', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='02'), '條', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='金利五金行' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：B1F排氣機；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0103001', 'HS-602防塞丸', NULL, '空調備品-藥劑', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='01' AND sub_code='03'), '包', 0, 0, NULL, NULL, 476, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='泓昇環境工程股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：賣場冷氣/飯店空調；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0201001', '燈泡-LED飛利浦9W/E27/3000K', NULL, '照明-燈泡', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='01'), '個', 0, 0, NULL, NULL, 145, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0201002', '燈泡-亮博士', '35W 4000K(4600 lm)', '照明-燈泡', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='01'), '個', 0, 0, NULL, NULL, 285, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='瑞眾股份有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：賣場桶燈用；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0201003', '燈泡-舞光LED', '25W省電球泡-日光 100-240V/30W/6500K', '照明-燈泡', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='01'), '個', 0, 0, NULL, NULL, 368, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0201004', '燈泡-水銀燈泡', 'MH-175W/U E40', '照明-燈泡', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='01'), '個', 0, 0, NULL, NULL, 800, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0201005', '燈泡-清光', '2W', '照明-燈泡', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='01'), '個', 0, 0, NULL, NULL, 5, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0201006', '燈泡-LED-12W/3000K/E27', NULL, '照明-燈泡', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='01'), '個', 0, 0, NULL, NULL, 130, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：客房門內燈；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0201007', '燈泡-LED-6.5W/9W/E27', NULL, '照明-燈泡', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='01'), '個', 0, 0, NULL, NULL, 145, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：客房檯燈；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0201008', '燈泡-保溫燈泡220V/E27/250W', NULL, '照明-燈泡', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='01'), '個', 0, 0, NULL, NULL, 380, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：G/R；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0201009', '燈泡-保溫燈泡110V/E27/250W', NULL, '照明-燈泡', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='01'), '個', 0, 0, NULL, NULL, 380, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：3F餐廳；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0211006', '燈泡-LED', 'MR16 E27 7W 杯燈燈泡', '照明-杯燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='11'), '個', 0, 0, NULL, NULL, 120, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：客房床頭燈；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0202001', '崁燈-LED', '3W/3000K', '照明-崁燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='02'), '個', 0, 0, NULL, NULL, 300, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：B2公區用；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0202002', '崁燈-LED', '7W/3000K黑杯崁燈/崁燈變壓器', '照明-崁燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='02'), '組', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：B2公區用；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0202003', '崁燈-LED-24W-4000K', '全電壓崁燈 開孔17CM', '照明-崁燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='02'), '組', 0, 0, NULL, NULL, 500, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：B2公區用；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0202004', '崁燈-LED-COB-24W-4000K', '全電壓崁燈 開孔21公分', '照明-崁燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='02'), '組', 0, 0, NULL, NULL, 680, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：1F及B1公區天花板用；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0202005', '崁燈-LED-COB-30W-4000K', '全電壓崁燈 開孔19.5公分', '照明-崁燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='02'), '組', 0, 0, NULL, NULL, 1500, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：1F戶外廣場用(小)；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0202006', '崁燈-LED-COB-30W-4000K', '全電壓崁燈 開孔22.5公分', '照明-崁燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='02'), '組', 0, 0, NULL, NULL, 1800, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：1F戶外廣場用(大)；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0203001', '崁燈-LEDAR-111燈組(黑)', '23W-3000K25D全電壓', '照明-投射燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='03'), '組', 0, 0, NULL, NULL, 977, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0203002', '投射燈-LEDAR-111燈組', '12W-4000K+DR薄型七燈', '照明-投射燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='03'), '組', 0, 0, NULL, NULL, 380, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0203003', '投射燈-LEDAR-111燈組', '15W-4000K+DR(崁入)12燈', '照明-投射燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='03'), '組', 0, 0, NULL, NULL, 326, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0203004', '投射燈-LEDAR-111軌道投射燈組', '12W-4000K全電壓七燈', '照明-投射燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='03'), '組', 0, 0, NULL, NULL, '588', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0203008', '投射燈-LED-AR111-12W/3000K', NULL, '照明-投射燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='03'), '組', 0, 0, NULL, NULL, 310, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：飯店大廳；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0204001', '軌道燈-LED', '30W-4000K全電壓(白色)', '照明-軌道燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='04'), '組', 0, 0, NULL, NULL, 660, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0204002', '軌道燈組-LED', '30W-4000K全電壓(萊)-80mm 黑色', '照明-軌道燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='04'), '組', 0, 0, NULL, NULL, 1100, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0205001', '平板燈-LED-23W雙標', '全電壓 4000K', '照明-平板燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='05'), '組', 0, 0, NULL, NULL, 780, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0205003', '平板燈-LED-23W雙標', '全電壓 6500K', '照明-平板燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='05'), '組', 0, 0, NULL, NULL, 780, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：LED平板燈(白光)；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206001', '燈管-日光燈（飛利浦）', 'T5/14W/865', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 55, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：B2廚房；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206002', '燈管-日光燈（飛利浦）', 'T5/14W/830', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 95, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206003', '燈管-LED（歐司朗）', 'T8/2尺全電壓4000K', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 100, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206004', '燈管-LED（歐司朗）', 'T8/2尺全電壓(白光)', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 100, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206005', '燈管-日光燈《東亞太陽神》', 'T8/20W(晝光)FL20/18D', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 85, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206006', '燈管-日光燈《東亞太陽神》T8/20W(黃光))FL20/18D', NULL, '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 55, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206008', '燈管-BB燈管', 'PLC-18W/830/2P', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '顆', 0, 0, NULL, NULL, 105, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206009', '燈管-BB燈管PLC-18W/840/2P', NULL, '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '顆', 0, 0, NULL, NULL, 105, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206010', '燈管-BB燈管', 'PLC-26W/840/2P', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '顆', 0, 0, NULL, NULL, 105, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206011', '燈管-日光燈（飛利浦）T5/28W/830', NULL, '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 95, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206012', '燈管-日光燈（飛利浦）T5/28W/827', NULL, '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 95, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206013', '燈管-日光燈（飛利浦）T5/28W/840', NULL, '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 95, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206014', '燈管-日光燈（飛利浦）T5/28W/865', NULL, '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 95, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206015', '燈管-日光燈（飛利浦）TLD', '36W/830', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 70, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206016', '燈管-日光燈（飛利浦）TLD', '36W/840', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 95, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206017', '燈管-LED燈（歐司朗）T8/4尺全電壓4000K', NULL, '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 132, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：飯店梯間、B2、B3公區、電氣室等…；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206018', '燈管-2/', 'eLED燈管（旭光）T8/3尺全電壓4000K', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 132, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206019', '燈管-雙頭複金屬燈管', 'HQI-TS70W/NDL(OSARAM)白', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 336, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206020', '燈管-日光燈（歐司朗）T5/35W/4000K(德製)', NULL, '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：員工出入口斜坡上方；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206021', '燈管-日光燈（飛利浦）T5/21W/830', NULL, '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 95, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206022', '燈管-日光燈（飛利浦）T5/21W/840', NULL, '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 95, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206023', '燈管-日光燈（飛利浦）T5/21W/865', NULL, '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 95, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206024', '燈管-日光燈（飛利浦', 'TLD 30W/830', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 90, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206025', '燈管-日光燈（飛利浦', 'TLD 30W/840', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 90, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206026', '燈管-日光燈（飛利浦', 'TLD 30W/865', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 90, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206027', '燈管-日光燈《東亞》', 'T8/40W(晝光)三波長', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 75, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206028', '燈管-LED', '(OSRAM) T8/4呎/6500K 全電壓', '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 125, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0206029', '燈管-飛利浦有罩燈管TWG206TL5/28W830/110-220V', NULL, '照明-燈管', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='06'), '支', 0, 0, NULL, NULL, 600, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0207001', '串接式燈具', 'LED/T8/2尺全電壓', '照明-串接燈具', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='07'), '支', 0, 0, NULL, NULL, 95, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0207002', '串接式燈具', 'LED/T8/3尺全電壓', '照明-串接燈具', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='07'), '支', 0, 0, NULL, NULL, 116, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0207003', '串接式燈具', 'LED/T8/4尺全電壓', '照明-串接燈具', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='07'), '支', 0, 0, NULL, NULL, 105, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0207004', '串接式燈具', 'T8/40W/220V', '照明-串接燈具', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='07'), '支', 0, 0, NULL, NULL, 158, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0207005', '串接式燈具', 'T8/40W/110V', '照明-串接燈具', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='07'), '支', 0, 0, NULL, NULL, 158, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0207006', '串接式燈具', 'T8/30W/220V', '照明-串接燈具', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='07'), '支', 0, 0, NULL, NULL, 130, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0207007', '串接式燈具', 'T8/30W/110V', '照明-串接燈具', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='07'), '支', 0, 0, NULL, NULL, 130, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0207008', '串接式燈具', 'T5/21W/110V', '照明-串接燈具', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='07'), '支', 0, 0, NULL, NULL, 200, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：馬桶上方；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0207009', '串接式燈具', 'T5/21W/220V', '照明-串接燈具', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='07'), '支', 0, 0, NULL, NULL, 160, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：公區層板照明；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0207010', '串接式燈具', 'T5/14W/110V', '照明-串接燈具', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='07'), '支', 0, 0, NULL, NULL, 150, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：浴室壁燈；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0207011', '串接式燈具', 'T5/28W/110V', '照明-串接燈具', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='07'), '支', 0, 0, NULL, NULL, 200, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：B2廚房；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0207012', '串接式燈具', 'T5/28W/220V', '照明-串接燈具', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='07'), '支', 0, 0, NULL, NULL, 120, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：公區層板照明；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0208001', '支架燈', 'T8/4尺全電壓3000K', '照明-支架燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='08'), '支', 0, 0, NULL, NULL, 247, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0208002', '支架燈', 'T8/4尺全電壓6500K', '照明-支架燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='08'), '支', 0, 0, NULL, NULL, 247, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0208003', '支架燈', 'T5-2尺6500K全電壓', '照明-支架燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='08'), '支', 0, 0, NULL, NULL, 135, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0208004', '支架燈', 'T5-2尺4000K全電壓', '照明-支架燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='08'), '支', 0, 0, NULL, NULL, 148, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0208005', '支架燈', 'T5-3尺4000K全電壓', '照明-支架燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='08'), '支', 0, 0, NULL, NULL, 175, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0208006', '支架燈', 'T5-4尺4000K全電壓', '照明-支架燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='08'), '支', 0, 0, NULL, NULL, 175, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0209001', '山型燈具組(110-220V)T5', NULL, '照明-山型燈具', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='09'), '組', 0, 0, NULL, NULL, 600, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0210001', '反射型燈具LTS-4140XXA', NULL, '照明-反射型燈具', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='10'), '組', 0, 0, NULL, NULL, 210, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0211001', '杯燈PHILIPS-LED燈', 'MR16-6W-3000K全電壓', '照明-杯燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='11'), '組', 0, 0, NULL, NULL, 160, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0211002', '杯燈PHILIPS-LED燈', 'MR16-6W-6500K全電壓', '照明-杯燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='11'), '組', 0, 0, NULL, NULL, 160, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0211003', '杯燈樂亮-LED燈', 'MR16-5W-6500K全電壓', '照明-杯燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='11'), '組', 0, 0, NULL, NULL, 160, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0211004', '杯燈LED6.5w超極光(晝光色)110-240V/6.5W/6500K', NULL, '照明-杯燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='11'), '組', 0, 0, NULL, NULL, 130, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0212001', '燈座LED桶燈座', 'E27-CH2725W', '照明-燈座', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='12'), '組', 0, 0, NULL, NULL, 410, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0213001', '燈頭G12磁燈頭', '(插PIN)(軌道)', '照明-燈頭', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='13'), '組', 0, 0, NULL, NULL, 120, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0213002', '燈頭C', 'G8.5進口燈頭 CDM-TC-35W燈管用', '照明-燈頭', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='02' AND sub_code='13'), '組', 0, 0, NULL, NULL, 150, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0301001', '漏電斷路器', '1P NVB-50UL-20A', '斷路器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='03' AND sub_code='01'), '個', 0, 0, NULL, NULL, 356, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0301002', '漏電斷路器', '3P  NF100- 30A', '斷路器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='03' AND sub_code='01'), '個', 0, 0, NULL, NULL, 888, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0301003', '漏電斷路器', '3P  NF100- 20A', '斷路器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='03' AND sub_code='01'), '個', 0, 0, NULL, NULL, 714, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0302001', '無熔絲開關', '1P  15A', '斷路器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='03' AND sub_code='02'), '個', 0, 0, NULL, NULL, 63, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0302002', '無熔絲開關', '3P  30A', '斷路器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='03' AND sub_code='02'), '個', 0, 0, NULL, NULL, '310', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0302003', '無熔絲開關', '2P  20A', '斷路器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='03' AND sub_code='02'), '個', 0, 0, NULL, NULL, '150', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0302004', '無熔絲開關', '1P  40A', '斷路器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='03' AND sub_code='02'), '個', 0, 0, NULL, NULL, '63', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0302005', '無熔絲開關', '3P  50A', '斷路器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='03' AND sub_code='02'), '個', 0, 0, NULL, NULL, '310', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0302006', '無熔絲開關', '3P  20A', '斷路器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='03' AND sub_code='02'), '個', 0, 0, NULL, NULL, '310', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0302007', '無熔絲開關', '1P  20A', '斷路器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='03' AND sub_code='02'), '個', 0, 0, NULL, NULL, '63', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E0302008', '無熔絲開關', '1P  30A', '斷路器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='03' AND sub_code='02'), '個', 0, 0, NULL, NULL, '63', (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1001001', '送風機-馬達', '400型 400 CFM', '送風機-馬達', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='10' AND sub_code='01'), '只', 0, 0, NULL, NULL, 1200, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1001002', '送風機-馬達', '600型 600 CFM', '送風機-馬達', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='10' AND sub_code='01'), '只', 0, 0, NULL, NULL, 1300, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1001003', '送風機-馬達', '800型 800 CFM', '送風機-馬達', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='10' AND sub_code='01'), '只', 0, 0, NULL, NULL, 1300, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1002001', '送風機馬達(風鼓)左', NULL, '送風機-風鼓', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='10' AND sub_code='02'), '只', 0, 0, NULL, NULL, 690, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；位置：客房送風機風鼓；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1002002', '送風機馬達(風鼓)右', NULL, '送風機-風鼓', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='10' AND sub_code='02'), '只', 0, 0, NULL, NULL, 690, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='捷彬科技有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1101001', '偵煙器模組', 'M500R 控制模組', '消防設備-偵煙器模組', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='01'), '個', 0, 0, NULL, NULL, 3700, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1101002', '偵煙器模組', 'M501M 監視模組', '消防設備-偵煙器模組', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='01'), '個', 0, 0, NULL, NULL, 4000, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1101003', '偵煙器模組', 'M502M 監視模組', '消防設備-偵煙器模組', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='01'), '個', 0, 0, NULL, NULL, 4000, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1102001', '差動火警探測器', '停車場/商場消防', '消防設備-差動火警探測器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='02'), '個', 0, 0, NULL, NULL, 100, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1103001', '偵煙探測器', '停車場/商場消防', '消防設備-偵煙探測器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='03'), '個', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1104001', '手動排煙開關蓋板', NULL, '消防設備-手動排煙開關', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='04'), '個', 0, 0, NULL, NULL, 80, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1104002', '手動排煙開關SH-48', 'DC24V 100MA', '消防設備-手動排煙開關', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='04'), '個', 0, 0, NULL, NULL, 360, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1105001', '火警發信機DC24V', '100MA', '消防設備-火警發信機', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='05'), '個', 0, 0, NULL, NULL, 150, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1106001', '滅火器掛勾', NULL, '消防設備-滅火器掛勾', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='06'), '個', 0, 0, NULL, NULL, 12, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1107001', '消防壓力開關5-20Kgf/cm2', NULL, '消防設備-壓力開關', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='07'), '只', 0, 0, NULL, NULL, 550, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1108001', '蜂鳴器', NULL, '消防設備-蜂鳴器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='08'), '只', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1109001', '手動報警器', NULL, '消防設備-手動報警器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='09'), '只', 0, 0, NULL, NULL, 150, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1110001', '泡沫手動開關盒', NULL, '消防設備-泡沫手動開關盒', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='10'), '只', 0, 0, NULL, NULL, 260, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1111001', '6V-4AH電池', NULL, '消防設備-E燈電池', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='11'), '顆', 0, 0, NULL, NULL, 150, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='羽任電池專賣店' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：當日付現金；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1111002', '6-2.3AH電池', NULL, '消防設備-E燈電池', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='11'), '顆', 0, 0, NULL, NULL, 160, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='羽任電池專賣店' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：當日付現金；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1112001', 'LED60燈E燈吸壁式', NULL, '消防設備-LED燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='12'), '個', 0, 0, NULL, NULL, 520, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1112002', 'LED小型雙面方向燈', 'C級3:1 雙面', '消防設備-LED燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='12'), '個', 0, 0, NULL, NULL, 480, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1112003', 'LED出口指示燈', 'C級3:1單面滑軌耳掛兩用', '消防設備-LED燈', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='12'), '個', 0, 0, NULL, NULL, 330, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1113001', '廣播喇叭', '吸頂/壁掛 3W (崁孔15公分)', '消防設備-廣播喇叭', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='13'), '個', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1113002', '廣播喇叭', '崁入式 5W', '消防設備-廣播喇叭', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='11' AND sub_code='13'), '個', 0, 0, NULL, NULL, 250, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='旭成科技製造有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1201001', '定時器', '24小時定時開關TB358NT6(220V)', '工務零件-定時器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='01'), '只', 0, 0, NULL, NULL, 1050, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1201002', '定時器', 'TB-全電壓線路型(110/220)', '工務零件-定時器', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='01'), '只', 0, 0, NULL, NULL, 1200, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1205001', '星光三開附蓋板-5352', NULL, '工務零件-蓋板', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='05'), '只', 0, 0, NULL, NULL, 230, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1205002', '星光三開附蓋板-5252', NULL, '工務零件-蓋板', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='05'), '只', 0, 0, NULL, NULL, 140, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1205003', '歐風卡式蓋板', '2孔蓋板', '工務零件-蓋板', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='05'), '只', 0, 0, NULL, NULL, 10, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1205004', '歐風卡式蓋板', '1孔蓋板', '工務零件-蓋板', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='05'), '只', 0, 0, NULL, NULL, 7, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1205005', '歐風卡式蓋板', '1聯封蓋無孔', '工務零件-蓋板', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='05'), '只', 0, 0, NULL, NULL, 7, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1206001', '壓條', 'TC-8灰', '工務零件-壓條', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='06'), '支', 0, 0, NULL, NULL, 85, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1206002', '壓條', 'TC-5 乳白', '工務零件-壓條', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='06'), '支', 0, 0, NULL, NULL, 35, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1206003', '壓條', 'TC-5 灰', '工務零件-壓條', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='06'), '支', 0, 0, NULL, NULL, 35, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1206004', '壓條', 'RD-50 (半圓壓條)', '工務零件-壓條', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='06'), '支', 0, 0, NULL, NULL, 90, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1206005', '壓條', 'RD-60(半圓壓條)', '工務零件-壓條', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='06'), '支', 0, 0, NULL, NULL, 130, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1207001', '軌道', '2M', '工務零件-軌道', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='07'), '支', 0, 0, NULL, NULL, 300, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1207002', '軌道', '3M', '工務零件-軌道', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='07'), '支', 0, 0, NULL, NULL, 420, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1207003', '軌道', '1M 深咖啡色', '工務零件-軌道', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='07'), '支', 0, 0, NULL, NULL, 400, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1207004', '軌道', '1.5M 深咖啡色', '工務零件-軌道', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='07'), '支', 0, 0, NULL, NULL, 400, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='森達利興業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1208001', '轉向三面插', NULL, '工務零件-插座', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='08'), '只', 0, 0, NULL, NULL, 40, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1208002', '雙聯附接地插座', '國際雙插', '工務零件-插座', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='08'), '只', 0, 0, NULL, NULL, 75, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1208003', '雙聯附接地插座', '窗插5.5MM', '工務零件-插座', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='08'), '只', 0, 0, NULL, NULL, 81, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1208004', '轉向雙插', NULL, '工務零件-插座', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='08'), '只', 0, 0, NULL, NULL, 21, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1208005', '舒美插頭', '母插', '工務零件-插座', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='08'), '只', 0, 0, NULL, NULL, 20, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1208006', '插座', '國際單切', '工務零件-插座', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='08'), '只', 0, 0, NULL, NULL, 30, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1208007', '插座', '國際單插座', '工務零件-插座', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='08'), '只', 0, 0, NULL, NULL, 45, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1208008', '耐熱轉向插頭-三面', '15A', '工務零件-插座', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='08'), '只', 0, 0, NULL, NULL, 60, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1208009', '星光接地雙插座', 'WTDFP15123附益', '工務零件-插座', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='08'), '只', 0, 0, NULL, NULL, 90, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1209001', '美術盒', '明BOX', '工務零件-美術盒', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='09'), '只', 0, 0, NULL, NULL, 10, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1210001', '手套棉紗', NULL, '工務零件-手套棉紗', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='10'), '打', 0, 0, NULL, NULL, 75, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1211001', '肘動精密陶瓷自由栓', '1/2" 長30CM', '工務零件-肘動精密陶瓷自由栓', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='11'), '支', 0, 0, NULL, NULL, 600, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1211002', '立式冷水陶瓷自由栓', '1/2"', '工務零件-肘動精密陶瓷自由栓', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='11'), '只', 0, 0, NULL, NULL, 650, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1211003', '肘動精密陶瓷立栓', '1/2"', '工務零件-肘動精密陶瓷自由栓', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='11'), '只', 0, 0, NULL, NULL, 210, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');
INSERT INTO cycle_purchase_items
  (company_code, item_code, item_name, spec, category, category_id, unit, default_qty, moq, max_stock, min_stock, unit_price, default_vendor_id, is_active, is_cycle_item, notes)
VALUES ('OU', 'OU-E1211004', '肘動精密陶瓷長栓', '1/2"', '工務零件-肘動精密陶瓷自由栓', (SELECT id FROM cycle_purchase_categories WHERE company_code='OU' AND major_code='E' AND mid_code='12' AND sub_code='11'), '只', 0, 0, NULL, NULL, 147, (SELECT id FROM cycle_purchase_vendors WHERE company_code='OU' AND vendor_name='嘉嶽企業有限公司' LIMIT 1), true, true, '來源：日曜料號主檔（工務用）；月結：30天；來源未提供 mini order');

-- E. 部門對照（部門不存在者略過，見結尾統計）
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

-- F. 結果統計（應與來源相符；對照未寫入數 = 缺部門所致，補部門後執行 riyo_item_fill.sql）
SELECT 'categories' AS 項目, count(*) AS 筆數 FROM cycle_purchase_categories WHERE company_code='OU'
UNION ALL SELECT 'items（OU-）', count(*) FROM cycle_purchase_items WHERE company_code='OU' AND item_code LIKE 'OU-%'
UNION ALL SELECT 'mappings 已寫入', count(*) FROM cycle_purchase_item_mappings WHERE company_code='OU'
UNION ALL SELECT 'mappings 應有（來源）', 929
UNION ALL SELECT 'items 缺廠商', count(*) FROM cycle_purchase_items WHERE company_code='OU' AND item_code LIKE 'OU-%' AND default_vendor_id IS NULL
UNION ALL SELECT 'mappings 缺廠商', count(*) FROM cycle_purchase_item_mappings WHERE company_code='OU' AND vendor_id IS NULL;
COMMIT;
