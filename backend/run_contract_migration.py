#!/usr/bin/env python3
"""
合約管理系統初始化 - 透過 SQLAlchemy ORM 建立資料表

用法:
  python run_contract_migration.py upgrade
  python run_contract_migration.py downgrade
"""
import sys
import os
from pathlib import Path

# 確保可以 import app module
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine


def upgrade():
    """建立合約管理相關的所有資料表"""
    print("🔧 建立合約管理資料表...")
    print(f"   資料庫: {engine.url}")

    try:
        from sqlalchemy import MetaData, Table, Column, String, Float, Integer, Date, DateTime, Boolean, JSON, ForeignKey, CheckConstraint, UniqueConstraint, func

        # 只為合約相關表建立 metadata，避免與現有表衝突
        contract_metadata = MetaData()

        # 1. Vendors 表
        vendors = Table(
            'vendors',
            contract_metadata,
            Column('vendor_id', String(50), primary_key=True),
            Column('vendor_name', String(255), nullable=False, unique=True),
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
        budget_categories = Table(
            'budget_categories',
            contract_metadata,
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
            UniqueConstraint('budget_year', 'category_l1', 'category_l2', 'dept', name='uq_budget_category_composite'),
        )

        # 3. Contracts 表
        contracts = Table(
            'contracts',
            contract_metadata,
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
            CheckConstraint('start_date <= end_date', name='ck_contract_date_order'),
            CheckConstraint("budget_source IN ('年度預算', '追加預算', '專案預算')", name='ck_budget_source'),
            CheckConstraint("budget_control_method IN ('提醒', '擋單', '主管覆核')", name='ck_budget_control_method'),
            CheckConstraint("risk_level IN ('低', '中', '高', '關鍵')", name='ck_risk_level'),
        )

        # 4. Contract Items 表
        contract_items = Table(
            'contract_items',
            contract_metadata,
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
            UniqueConstraint('contract_id', 'item_seq', name='uq_contract_item_seq'),
        )

        # 建立表
        contract_metadata.create_all(bind=engine, checkfirst=True)
        print("✅ 成功建立所有合約管理資料表")

        # 驗證表是否成立
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(engine)
        inspector_tables = inspector.get_table_names()
        expected_tables = ["vendors", "budget_categories", "contracts", "contract_items"]

        print("\n📋 已建立的資料表:")
        for table in expected_tables:
            if table in inspector_tables:
                print(f"   ✓ {table}")
            else:
                print(f"   ✗ {table} (未建立)")

        return 0
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1


def downgrade():
    """刪除合約管理相關的所有資料表"""
    print("⚠️  刪除合約管理資料表...")
    print(f"   資料庫: {engine.url}")

    response = input("確認刪除? (yes/no): ")
    if response.lower() != "yes":
        print("已取消")
        return 0

    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS contract_items"))
            conn.execute(text("DROP TABLE IF EXISTS contracts"))
            conn.execute(text("DROP TABLE IF EXISTS budget_categories"))
            conn.execute(text("DROP TABLE IF EXISTS vendors"))
            conn.commit()

        print("✅ 成功刪除所有資料表")
        return 0
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"

    if command == "upgrade":
        sys.exit(upgrade())
    elif command == "downgrade":
        sys.exit(downgrade())
    else:
        print(f"未知命令: {command}")
        print("用法: python run_contract_migration.py [upgrade|downgrade]")
        sys.exit(1)
