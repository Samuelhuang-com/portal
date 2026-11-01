"""多公司隔離 第二批：唯一鍵改用 company_code

Revision ID: cpco2
Revises: cpco1
Create Date: 2026-10-31

改動（皆為 PostgreSQL）：
  1. uq_cp_category_company_codes         (company, major, mid, sub) → (company_code, major, mid, sub)
  2. uq_cp_item_mapping_item_company_dept (item_id, company, dept)   → (item_id, company_code, dept)
  3. uq_cp_summary_cycle_period_company_item_dept → company_code
  4. uq_cp_po_active_cycle_period_company_vendor → company_code，並補上 WHERE status <> 'cancelled'
     （baseline_cp 只給 SQLite 加了條件；PG 上一直是無條件唯一索引，已取消的採購單會擋住重開）
  5. cycle_purchase_account_codes.code 全域唯一 → (company_code, code)（會計科目分公司）

注意：第二批執行時 company_code 仍可能為 NULL（第三批才 NOT NULL）。PG 的 UNIQUE 允許
多筆 NULL，所以 NULL 列不參與唯一性檢查；上線前須先確認第一批 log 的 NULL 筆數。
若兩筆不同字串對應到同一代碼而撞鍵，本支會失敗並回滾（預期行為，需人工處理）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cpco2"
down_revision: Union[str, None] = "cpco1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PO_INDEX = "uq_cp_po_active_cycle_period_company_vendor"


def upgrade() -> None:
    op.drop_constraint("uq_cp_category_company_codes", "cycle_purchase_categories", type_="unique")
    op.create_unique_constraint(
        "uq_cp_category_company_codes", "cycle_purchase_categories",
        ["company_code", "major_code", "mid_code", "sub_code"],
    )

    op.drop_constraint("uq_cp_item_mapping_item_company_dept", "cycle_purchase_item_mappings", type_="unique")
    op.create_unique_constraint(
        "uq_cp_item_mapping_item_company_dept", "cycle_purchase_item_mappings",
        ["item_id", "company_code", "department_id"],
    )

    op.drop_constraint("uq_cp_summary_cycle_period_company_item_dept", "cycle_purchase_summary", type_="unique")
    op.create_unique_constraint(
        "uq_cp_summary_cycle_period_company_item_dept", "cycle_purchase_summary",
        ["cycle_id", "period_label", "company_code", "item_id", "department_id"],
    )

    op.drop_index(PO_INDEX, table_name="cycle_purchase_pos")
    op.create_index(
        PO_INDEX, "cycle_purchase_pos",
        ["cycle_id", "period_label", "company_code", "vendor_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'cancelled'"),
    )

    op.drop_constraint("cycle_purchase_account_codes_code_key", "cycle_purchase_account_codes", type_="unique")
    op.create_unique_constraint(
        "uq_cp_account_code_company_code", "cycle_purchase_account_codes",
        ["company_code", "code"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_cp_account_code_company_code", "cycle_purchase_account_codes", type_="unique")
    op.create_unique_constraint(
        "cycle_purchase_account_codes_code_key", "cycle_purchase_account_codes", ["code"],
    )

    op.drop_index(PO_INDEX, table_name="cycle_purchase_pos")
    op.create_index(
        PO_INDEX, "cycle_purchase_pos",
        ["cycle_id", "period_label", "company", "vendor_id"],
        unique=True,
    )

    op.drop_constraint("uq_cp_summary_cycle_period_company_item_dept", "cycle_purchase_summary", type_="unique")
    op.create_unique_constraint(
        "uq_cp_summary_cycle_period_company_item_dept", "cycle_purchase_summary",
        ["cycle_id", "period_label", "company", "item_id", "department_id"],
    )

    op.drop_constraint("uq_cp_item_mapping_item_company_dept", "cycle_purchase_item_mappings", type_="unique")
    op.create_unique_constraint(
        "uq_cp_item_mapping_item_company_dept", "cycle_purchase_item_mappings",
        ["item_id", "company", "department_id"],
    )

    op.drop_constraint("uq_cp_category_company_codes", "cycle_purchase_categories", type_="unique")
    op.create_unique_constraint(
        "uq_cp_category_company_codes", "cycle_purchase_categories",
        ["company", "major_code", "mid_code", "sub_code"],
    )
