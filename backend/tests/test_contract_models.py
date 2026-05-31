"""
合約管理系統 - ORM 模型單元測試（簡化版）

測試覆蓋：
  - 4 個核心表的建立與結構驗證
  - 約束與外鍵驗證
  - 級聯刪除行為驗證
"""
import pytest
from datetime import date
from sqlalchemy import create_engine, MetaData, Table, Column, String, Float, Integer, Date, DateTime, Boolean, JSON, ForeignKey, CheckConstraint, UniqueConstraint, func, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError


@pytest.fixture(scope="function")
def test_engine():
    """為每個測試建立隔離的記憶體資料庫"""
    engine = create_engine('sqlite:///:memory:', echo=False)

    # 定義合約管理相關表
    metadata = MetaData()

    # 1. Vendors 表
    vendors = Table('vendors', metadata,
        Column('vendor_id', String(50), primary_key=True),
        Column('vendor_name', String(255), unique=True, nullable=False),
        Column('tax_id', String(20), nullable=False),
        Column('contact_person', String(100)),
        Column('phone', String(20)),
        Column('email', String(100)),
        Column('address', String(500)),
        Column('payment_terms', String(100)),
        Column('bank_name', String(100)),
        Column('bank_account', String(50)),
        Column('vendor_type', String(50)),
        Column('risk_level', String(20)),
        Column('is_critical', Boolean, default=False),
        Column('created_at', DateTime, server_default=func.now()),
        Column('updated_at', DateTime, server_default=func.now()),
    )

    # 2. Budget Categories 表
    budget_categories = Table('budget_categories', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('budget_year', Integer, nullable=False),
        Column('dept', String(100), nullable=False),
        Column('category_l1', String(100), nullable=False),
        Column('category_l2', String(100), nullable=False),
        Column('accounting_code', String(50), nullable=False),
        Column('payment_code', String(50)),
        Column('is_enabled', Boolean, default=True),
        Column('effective_date', Date, nullable=False),
        Column('disabled_date', Date),
        Column('maintain_unit', String(100), nullable=False),
        Column('created_at', DateTime, server_default=func.now()),
        Column('updated_at', DateTime, server_default=func.now()),
        UniqueConstraint('budget_year', 'category_l1', 'category_l2', 'dept', name='uq_budget_composite'),
    )

    # 3. Contracts 表
    contracts = Table('contracts', metadata,
        Column('contract_id', String(50), primary_key=True),
        Column('contract_name', String(255), nullable=False),
        Column('contract_type', String(50), nullable=False),
        Column('contract_status', String(50), default='草稿'),
        Column('responsible_dept', String(100), nullable=False),
        Column('using_depts', String(500)),
        Column('vendor_id', String(50), ForeignKey('vendors.vendor_id', ondelete='RESTRICT'), nullable=False),
        Column('vendor_name', String(255)),
        Column('start_date', Date, nullable=False),
        Column('end_date', Date, nullable=False),
        Column('notification_days', Integer, default=0),
        Column('auto_renewal', Boolean, default=False),
        Column('currency', String(10), default='TWD'),
        Column('total_amount_tax_included', Float, nullable=False),
        Column('monthly_fixed_amount', Float),
        Column('pricing_method', String(100), nullable=False),
        Column('needs_purchase_order', Boolean, default=False),
        Column('can_claim_without_po', Boolean, default=False),
        Column('needs_allocation', Boolean, default=False),
        Column('allocation_method', String(50)),
        Column('budget_year', Integer, nullable=False),
        Column('budget_category_l1', String(100), nullable=False),
        Column('budget_category_l2', String(100), nullable=False),
        Column('accounting_code', String(50), nullable=False),
        Column('budget_source', String(50), default='年度預算'),
        Column('budget_control_method', String(50), default='提醒'),
        Column('require_acceptance', Boolean, default=False),
        Column('risk_level', String(20), default='中'),
        Column('manager', String(100)),
        Column('reviewer', String(100)),
        Column('attachment_url', String(500)),
        Column('remarks', String(1000)),
        Column('detail', JSON, default=dict),
        Column('created_at', DateTime, server_default=func.now()),
        Column('updated_at', DateTime, server_default=func.now()),
        CheckConstraint('start_date <= end_date'),
        CheckConstraint("budget_source IN ('年度預算', '追加預算', '專案預算')"),
        CheckConstraint("budget_control_method IN ('提醒', '擋單', '主管覆核')"),
        CheckConstraint("risk_level IN ('低', '中', '高', '關鍵')"),
    )

    # 4. Contract Items 表
    contract_items = Table('contract_items', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('contract_id', String(50), ForeignKey('contracts.contract_id', ondelete='CASCADE'), nullable=False),
        Column('item_seq', Integer, nullable=False),
        Column('item_name', String(255), nullable=False),
        Column('item_category', String(50), nullable=False),
        Column('unit_price_tax_excluded', Float),
        Column('quantity', Float),
        Column('unit', String(20)),
        Column('tax_rate', Float, default=5),
        Column('amount_tax_excluded', Float, nullable=False),
        Column('amount_tax_included', Float, nullable=False),
        Column('is_fixed', Boolean, default=True),
        Column('is_floating', Boolean, default=False),
        Column('created_at', DateTime, server_default=func.now()),
        Column('updated_at', DateTime, server_default=func.now()),
        UniqueConstraint('contract_id', 'item_seq'),
    )

    # 建立所有表
    metadata.create_all(bind=engine)

    yield engine

    # 清理
    metadata.drop_all(bind=engine)


class TestTableStructure:
    """資料表結構驗證"""

    def test_all_tables_created(self, test_engine):
        """測試所有必要表都已建立"""
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()

        expected_tables = ["vendors", "budget_categories", "contracts", "contract_items"]
        for table_name in expected_tables:
            assert table_name in tables, f"表 {table_name} 未建立"

    def test_vendors_table_structure(self, test_engine):
        """測試 Vendors 表結構"""
        inspector = inspect(test_engine)
        columns = {col['name']: col for col in inspector.get_columns('vendors')}

        # 驗證關鍵欄位
        assert 'vendor_id' in columns
        assert 'vendor_name' in columns
        assert 'tax_id' in columns
        assert 'is_critical' in columns
        assert 'created_at' in columns

        # 驗證 vendor_id 是主鍵
        pk = inspector.get_pk_constraint('vendors')
        assert 'vendor_id' in pk['constrained_columns']

    def test_contracts_table_structure(self, test_engine):
        """測試 Contracts 表結構（36 欄位）"""
        inspector = inspect(test_engine)
        columns = inspector.get_columns('contracts')

        # 驗證欄位數量
        assert len(columns) == 35, f"預期 35 欄位，實際 {len(columns)} 欄位"

        # 驗證關鍵欄位
        column_names = [col['name'] for col in columns]
        key_columns = [
            'contract_id', 'contract_name', 'contract_type', 'contract_status',
            'vendor_id', 'start_date', 'end_date',
            'total_amount_tax_included', 'pricing_method',
            'budget_year', 'budget_category_l1', 'budget_category_l2', 'accounting_code',
            'budget_source', 'budget_control_method', 'risk_level'
        ]
        for key_col in key_columns:
            assert key_col in column_names, f"必要欄位 {key_col} 缺失"

    def test_contract_items_table_structure(self, test_engine):
        """測試 ContractItems 表結構"""
        inspector = inspect(test_engine)
        columns = {col['name']: col for col in inspector.get_columns('contract_items')}

        # 驗證關鍵欄位
        assert 'contract_id' in columns
        assert 'item_seq' in columns
        assert 'item_name' in columns
        assert 'amount_tax_excluded' in columns
        assert 'amount_tax_included' in columns

    def test_budget_categories_table_structure(self, test_engine):
        """測試 BudgetCategories 表結構"""
        inspector = inspect(test_engine)
        columns = {col['name']: col for col in inspector.get_columns('budget_categories')}

        # 驗證關鍵欄位
        assert 'budget_year' in columns
        assert 'category_l1' in columns
        assert 'category_l2' in columns
        assert 'accounting_code' in columns
        assert 'is_enabled' in columns


class TestConstraints:
    """約束與關聯驗證"""

    def test_vendors_unique_name(self, test_engine):
        """測試廠商名稱唯一性約束"""
        with test_engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO vendors (vendor_id, vendor_name, tax_id)
                VALUES ('VND-0001', '同名公司', '11111111')
            """))
            conn.commit()

            # 嘗試插入相同名稱 - 應該失敗
            with pytest.raises(IntegrityError):
                conn.execute(text("""
                    INSERT INTO vendors (vendor_id, vendor_name, tax_id)
                    VALUES ('VND-0002', '同名公司', '22222222')
                """))
                conn.commit()

    def test_contract_foreign_key_vendors(self, test_engine):
        """測試合約與廠商外鍵關係"""
        with test_engine.connect() as conn:
            # 建立廠商
            conn.execute(text("""
                INSERT INTO vendors (vendor_id, vendor_name, tax_id)
                VALUES ('VND-0001', '維修公司', '12345678')
            """))
            conn.commit()

            # 建立合約（應成功）
            conn.execute(text("""
                INSERT INTO contracts (
                    contract_id, contract_name, contract_type,
                    responsible_dept, vendor_id, start_date, end_date,
                    total_amount_tax_included, pricing_method,
                    budget_year, budget_category_l1, budget_category_l2, accounting_code
                )
                VALUES (
                    'CON-2026-0001', '測試合約', '維修',
                    '工務部', 'VND-0001', '2026-01-01', '2026-12-31',
                    100000, '固定',
                    2026, '維修費', '設備維修', '6000-0001'
                )
            """))
            conn.commit()

            # 驗證合約已建立
            result = conn.execute(text("SELECT COUNT(*) FROM contracts")).scalar()
            assert result == 1

            # 嘗試建立與不存在廠商的合約 - 應該失敗
            with pytest.raises(IntegrityError):
                conn.execute(text("""
                    INSERT INTO contracts (
                        contract_id, contract_name, contract_type,
                        responsible_dept, vendor_id, start_date, end_date,
                        total_amount_tax_included, pricing_method,
                        budget_year, budget_category_l1, budget_category_l2, accounting_code
                    )
                    VALUES (
                        'CON-2026-0002', '錯誤合約', '維修',
                        '工務部', 'VND-NONEXIST', '2026-01-01', '2026-12-31',
                        100000, '固定',
                        2026, '維修費', '設備維修', '6000-0001'
                    )
                """))
                conn.commit()

    def test_contract_date_check_constraint(self, test_engine):
        """測試合約起迄日期CHECK約束"""
        with test_engine.connect() as conn:
            # 建立廠商
            conn.execute(text("""
                INSERT INTO vendors (vendor_id, vendor_name, tax_id)
                VALUES ('VND-0001', '維修公司', '12345678')
            """))
            conn.commit()

            # 嘗試建立迄日早於起日的合約 - 應該失敗
            with pytest.raises(IntegrityError):
                conn.execute(text("""
                    INSERT INTO contracts (
                        contract_id, contract_name, contract_type,
                        responsible_dept, vendor_id, start_date, end_date,
                        total_amount_tax_included, pricing_method,
                        budget_year, budget_category_l1, budget_category_l2, accounting_code
                    )
                    VALUES (
                        'CON-2026-0001', '錯誤合約', '維修',
                        '工務部', 'VND-0001', '2026-12-31', '2026-01-01',
                        100000, '固定',
                        2026, '維修費', '設備維修', '6000-0001'
                    )
                """))
                conn.commit()

    def test_contract_budget_source_check(self, test_engine):
        """測試預算來源CHECK約束"""
        with test_engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO vendors (vendor_id, vendor_name, tax_id)
                VALUES ('VND-0001', '維修公司', '12345678')
            """))
            conn.commit()

            # 嘗試建立預算來源無效的合約
            with pytest.raises(IntegrityError):
                conn.execute(text("""
                    INSERT INTO contracts (
                        contract_id, contract_name, contract_type,
                        responsible_dept, vendor_id, start_date, end_date,
                        total_amount_tax_included, pricing_method,
                        budget_year, budget_category_l1, budget_category_l2, accounting_code,
                        budget_source
                    )
                    VALUES (
                        'CON-2026-0001', '合約', '維修',
                        '工務部', 'VND-0001', '2026-01-01', '2026-12-31',
                        100000, '固定',
                        2026, '維修費', '設備維修', '6000-0001',
                        '無效來源'
                    )
                """))
                conn.commit()

    def test_contract_risk_level_check(self, test_engine):
        """測試風險等級CHECK約束"""
        with test_engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO vendors (vendor_id, vendor_name, tax_id)
                VALUES ('VND-0001', '維修公司', '12345678')
            """))
            conn.commit()

            # 嘗試建立風險等級無效的合約
            with pytest.raises(IntegrityError):
                conn.execute(text("""
                    INSERT INTO contracts (
                        contract_id, contract_name, contract_type,
                        responsible_dept, vendor_id, start_date, end_date,
                        total_amount_tax_included, pricing_method,
                        budget_year, budget_category_l1, budget_category_l2, accounting_code,
                        risk_level
                    )
                    VALUES (
                        'CON-2026-0001', '合約', '維修',
                        '工務部', 'VND-0001', '2026-01-01', '2026-12-31',
                        100000, '固定',
                        2026, '維修費', '設備維修', '6000-0001',
                        '超高風險'
                    )
                """))
                conn.commit()

    def test_budget_category_composite_unique(self, test_engine):
        """測試預算科目複合唯一鍵"""
        with test_engine.connect() as conn:
            # 插入第一筆
            conn.execute(text("""
                INSERT INTO budget_categories (
                    budget_year, dept, category_l1, category_l2,
                    accounting_code, is_enabled, effective_date, maintain_unit
                )
                VALUES (2026, '工務部', '維修費', '設備維修', '6000-0001', 1, '2026-01-01', '工務課')
            """))
            conn.commit()

            # 嘗試插入相同組合 - 應該失敗
            with pytest.raises(IntegrityError):
                conn.execute(text("""
                    INSERT INTO budget_categories (
                        budget_year, dept, category_l1, category_l2,
                        accounting_code, is_enabled, effective_date, maintain_unit
                    )
                    VALUES (2026, '工務部', '維修費', '設備維修', '6000-0001', 1, '2026-01-01', '工務課')
                """))
                conn.commit()

    def test_contract_item_unique_seq(self, test_engine):
        """測試合約明細item_seq唯一性"""
        with test_engine.connect() as conn:
            # 建立廠商和合約
            conn.execute(text("""
                INSERT INTO vendors (vendor_id, vendor_name, tax_id)
                VALUES ('VND-0001', '維修公司', '12345678')
            """))
            conn.execute(text("""
                INSERT INTO contracts (
                    contract_id, contract_name, contract_type,
                    responsible_dept, vendor_id, start_date, end_date,
                    total_amount_tax_included, pricing_method,
                    budget_year, budget_category_l1, budget_category_l2, accounting_code
                )
                VALUES (
                    'CON-2026-0001', '合約', '維修',
                    '工務部', 'VND-0001', '2026-01-01', '2026-12-31',
                    100000, '固定',
                    2026, '維修費', '設備維修', '6000-0001'
                )
            """))
            conn.commit()

            # 插入第一個明細項目
            conn.execute(text("""
                INSERT INTO contract_items (
                    contract_id, item_seq, item_name, item_category,
                    amount_tax_excluded, amount_tax_included
                )
                VALUES ('CON-2026-0001', 1, '項目1', '服務', 100, 105)
            """))
            conn.commit()

            # 嘗試插入相同seq - 應該失敗
            with pytest.raises(IntegrityError):
                conn.execute(text("""
                    INSERT INTO contract_items (
                        contract_id, item_seq, item_name, item_category,
                        amount_tax_excluded, amount_tax_included
                    )
                    VALUES ('CON-2026-0001', 1, '項目2', '服務', 200, 210)
                """))
                conn.commit()


class TestCascadeDelete:
    """級聯刪除行為驗證"""

    def test_contract_cascade_delete(self, test_engine):
        """測試刪除合約時明細被級聯刪除"""
        with test_engine.connect() as conn:
            # 建立廠商、合約、明細
            conn.execute(text("""
                INSERT INTO vendors (vendor_id, vendor_name, tax_id)
                VALUES ('VND-0001', '維修公司', '12345678')
            """))
            conn.execute(text("""
                INSERT INTO contracts (
                    contract_id, contract_name, contract_type,
                    responsible_dept, vendor_id, start_date, end_date,
                    total_amount_tax_included, pricing_method,
                    budget_year, budget_category_l1, budget_category_l2, accounting_code
                )
                VALUES (
                    'CON-2026-0001', '合約', '維修',
                    '工務部', 'VND-0001', '2026-01-01', '2026-12-31',
                    100000, '固定',
                    2026, '維修費', '設備維修', '6000-0001'
                )
            """))
            conn.execute(text("""
                INSERT INTO contract_items (
                    contract_id, item_seq, item_name, item_category,
                    amount_tax_excluded, amount_tax_included
                )
                VALUES ('CON-2026-0001', 1, '項目1', '服務', 100, 105)
            """))
            conn.commit()

            # 驗證明細已建立
            items_before = conn.execute(text("SELECT COUNT(*) FROM contract_items")).scalar()
            assert items_before == 1

            # 刪除合約
            conn.execute(text("DELETE FROM contracts WHERE contract_id = 'CON-2026-0001'"))
            conn.commit()

            # 驗證明細也被刪除
            items_after = conn.execute(text("SELECT COUNT(*) FROM contract_items")).scalar()
            assert items_after == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
