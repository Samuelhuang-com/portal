"""Add contract management tables (vendors, budget_categories, contracts, contract_items)

Revision ID: 001_add_contract_tables
Revises:
Create Date: 2026-05-27 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001_add_contract_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    建立合約管理系統的 4 個核心表：
    1. vendors - 廠商主檔
    2. budget_categories - 預算科目字典
    3. contracts - 合約主檔
    4. contract_items - 合約明細
    """

    # ──────────────────────────────────────────────────────────────
    # 1. Vendors 表 - 廠商主檔
    # ──────────────────────────────────────────────────────────────
    op.create_table(
        "vendors",
        sa.Column("vendor_id", sa.String(50), primary_key=True, nullable=False, comment="廠商編號 (VND-NNNN)"),
        sa.Column("vendor_name", sa.String(255), nullable=False, unique=True, comment="廠商名稱"),
        sa.Column("tax_id", sa.String(20), nullable=False, comment="統一編號"),
        sa.Column("contact_person", sa.String(100), nullable=True, comment="聯絡人"),
        sa.Column("phone", sa.String(20), nullable=True, comment="電話"),
        sa.Column("email", sa.String(100), nullable=True, comment="電子郵件"),
        sa.Column("address", sa.String(500), nullable=True, comment="地址"),
        sa.Column("payment_terms", sa.String(100), nullable=True, comment="付款條件"),
        sa.Column("bank_name", sa.String(100), nullable=True, comment="銀行名稱"),
        sa.Column("bank_account", sa.String(50), nullable=True, comment="銀行帳號（敏感資訊）"),
        sa.Column("vendor_type", sa.String(50), nullable=True, comment="廠商類型"),
        sa.Column("risk_level", sa.String(20), nullable=True, comment="風險等級"),
        sa.Column("is_critical", sa.Boolean, default=False, nullable=False, comment="是否為關鍵廠商"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        comment="合約廠商主檔"
    )
    op.create_index("idx_vendors_name", "vendors", ["vendor_name"])
    op.create_index("idx_vendors_tax_id", "vendors", ["tax_id"])

    # ──────────────────────────────────────────────────────────────
    # 2. BudgetCategories 表 - 預算科目字典
    # ──────────────────────────────────────────────────────────────
    op.create_table(
        "budget_categories",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("budget_year", sa.Integer, nullable=False, comment="預算年度"),
        sa.Column("dept", sa.String(100), nullable=False, comment="部門"),
        sa.Column("category_l1", sa.String(100), nullable=False, comment="預算大項"),
        sa.Column("category_l2", sa.String(100), nullable=False, comment="預算細項"),
        sa.Column("accounting_code", sa.String(50), nullable=False, comment="會計科目"),
        sa.Column("payment_code", sa.String(50), nullable=True, comment="付款科目"),
        sa.Column("is_enabled", sa.Boolean, default=True, nullable=False, comment="是否啟用"),
        sa.Column("effective_date", sa.Date, nullable=False, comment="生效日期"),
        sa.Column("disabled_date", sa.Date, nullable=True, comment="停用日期"),
        sa.Column("maintain_unit", sa.String(100), nullable=False, comment="維護單位"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("budget_year", "category_l1", "category_l2", "dept", name="uq_budget_category_composite"),
        comment="預算科目字典"
    )
    op.create_index("idx_budget_cat_year", "budget_categories", ["budget_year"])
    op.create_index("idx_budget_cat_dept", "budget_categories", ["dept"])
    op.create_index("idx_budget_cat_l1", "budget_categories", ["category_l1"])

    # ──────────────────────────────────────────────────────────────
    # 3. Contracts 表 - 合約主檔
    # ──────────────────────────────────────────────────────────────
    op.create_table(
        "contracts",
        # 基本資訊
        sa.Column("contract_id", sa.String(50), primary_key=True, nullable=False, comment="合約編號 (CON-YYYY-NNNN)"),
        sa.Column("contract_name", sa.String(255), nullable=False, comment="合約名稱"),
        sa.Column("contract_type", sa.String(50), nullable=False, comment="合約類型"),
        sa.Column("contract_status", sa.String(50), default="草稿", nullable=False, comment="合約狀態"),
        sa.Column("responsible_dept", sa.String(100), nullable=False, comment="權責部門"),
        sa.Column("using_depts", sa.String(500), nullable=True, comment="使用部門（多個時以;分隔）"),

        # 廠商資訊
        sa.Column("vendor_id", sa.String(50), nullable=False, comment="廠商編號"),
        sa.Column("vendor_name", sa.String(255), nullable=True, comment="廠商名稱（唯讀，冗餘欄位）"),

        # 合約期間
        sa.Column("start_date", sa.Date, nullable=False, comment="合約起日"),
        sa.Column("end_date", sa.Date, nullable=False, comment="合約迄日"),
        sa.Column("notification_days", sa.Integer, default=0, nullable=False, comment="到期前通知天數"),
        sa.Column("auto_renewal", sa.Boolean, default=False, nullable=False, comment="是否自動續約"),

        # 金額與計價
        sa.Column("currency", sa.String(10), default="TWD", nullable=False, comment="幣別"),
        sa.Column("total_amount_tax_included", sa.Float, nullable=False, comment="合約總金額含稅"),
        sa.Column("monthly_fixed_amount", sa.Float, nullable=True, comment="每月固定金額"),
        sa.Column("pricing_method", sa.String(100), nullable=False, comment="計價方式"),

        # 購買單與請款
        sa.Column("needs_purchase_order", sa.Boolean, default=False, nullable=False, comment="是否需請購單"),
        sa.Column("can_claim_without_po", sa.Boolean, default=False, nullable=False, comment="是否可無請購請款"),

        # 分攤
        sa.Column("needs_allocation", sa.Boolean, default=False, nullable=False, comment="是否需分攤"),
        sa.Column("allocation_method", sa.String(50), nullable=True, comment="分攤方式"),

        # 預算與會計
        sa.Column("budget_year", sa.Integer, nullable=False, comment="預算年度"),
        sa.Column("budget_category_l1", sa.String(100), nullable=False, comment="預算大項"),
        sa.Column("budget_category_l2", sa.String(100), nullable=False, comment="預算細項"),
        sa.Column("accounting_code", sa.String(50), nullable=False, comment="會計科目"),
        sa.Column("budget_source", sa.String(50), default="年度預算", nullable=False, comment="預算來源（年度/追加/專案）"),
        sa.Column("budget_control_method", sa.String(50), default="提醒", nullable=False, comment="預算控管方式（提醒/擋單/主管覆核）"),
        sa.Column("require_acceptance", sa.Boolean, default=False, nullable=False, comment="是否需驗收"),

        # 風險與管理
        sa.Column("risk_level", sa.String(20), default="中", nullable=False, comment="風險等級（低/中/高/關鍵）"),
        sa.Column("manager", sa.String(100), nullable=True, comment="管理人"),
        sa.Column("reviewer", sa.String(100), nullable=True, comment="覆核人"),

        # 附件與備註
        sa.Column("attachment_url", sa.String(500), nullable=True, comment="附件連結"),
        sa.Column("remarks", sa.String(1000), nullable=True, comment="備註"),

        # Drawer 明細用 JSON
        sa.Column("detail", sa.JSON, default=dict, nullable=False, comment="Drawer 用詳細資訊 dict"),

        # 系統欄位
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # 外鍵
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.vendor_id"], ondelete="RESTRICT"),

        # 約束條件
        sa.CheckConstraint("start_date <= end_date", name="ck_contract_date_order"),
        sa.CheckConstraint("budget_source IN ('年度預算', '追加預算', '專案預算')", name="ck_budget_source"),
        sa.CheckConstraint("budget_control_method IN ('提醒', '擋單', '主管覆核')", name="ck_budget_control_method"),
        sa.CheckConstraint("risk_level IN ('低', '中', '高', '關鍵')", name="ck_risk_level"),

        comment="合約主檔"
    )

    # 索引
    op.create_index("idx_contracts_status", "contracts", ["contract_status"])
    op.create_index("idx_contracts_vendor", "contracts", ["vendor_id"])
    op.create_index("idx_contracts_dept", "contracts", ["responsible_dept"])
    op.create_index("idx_contracts_budget_year", "contracts", ["budget_year"])
    op.create_index("idx_contracts_dates", "contracts", ["start_date", "end_date"])
    op.create_index("idx_contracts_risk", "contracts", ["risk_level"])

    # ──────────────────────────────────────────────────────────────
    # 4. ContractItems 表 - 合約明細
    # ──────────────────────────────────────────────────────────────
    op.create_table(
        "contract_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("contract_id", sa.String(50), nullable=False, comment="合約編號（FK）"),
        sa.Column("item_seq", sa.Integer, nullable=False, comment="項目序號"),
        sa.Column("item_name", sa.String(255), nullable=False, comment="項目名稱"),
        sa.Column("item_category", sa.String(50), nullable=False, comment="項目類別"),
        sa.Column("unit_price_tax_excluded", sa.Float, nullable=True, comment="單價（未稅）"),
        sa.Column("quantity", sa.Float, nullable=True, comment="數量"),
        sa.Column("unit", sa.String(20), nullable=True, comment="單位"),
        sa.Column("tax_rate", sa.Float, default=5, nullable=False, comment="稅率（%）"),
        sa.Column("amount_tax_excluded", sa.Float, nullable=False, comment="金額（未稅）"),
        sa.Column("amount_tax_included", sa.Float, nullable=False, comment="金額（含稅）"),
        sa.Column("is_fixed", sa.Boolean, default=True, nullable=False, comment="是否為固定項目"),
        sa.Column("is_floating", sa.Boolean, default=False, nullable=False, comment="是否為浮動項目"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # 外鍵
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.contract_id"], ondelete="CASCADE"),

        # 複合主鍵
        sa.UniqueConstraint("contract_id", "item_seq", name="uq_contract_item_seq"),

        comment="合約明細"
    )

    # 索引
    op.create_index("idx_contract_items_contract", "contract_items", ["contract_id"])
    op.create_index("idx_contract_items_seq", "contract_items", ["contract_id", "item_seq"])


def downgrade() -> None:
    """降級：刪除所有新增的表"""
    # 刪除順序很重要 - 先刪有 FK 依賴的表，再刪被參考的表
    op.drop_table("contract_items")
    op.drop_table("contracts")
    op.drop_table("budget_categories")
    op.drop_table("vendors")
