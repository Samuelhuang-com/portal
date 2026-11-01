"""多公司隔離 第三批：分公司表 company_code 改 NOT NULL

Revision ID: cpco3
Revises: cpco2
Create Date: 2026-10-31

⚠️ 上線前置條件（缺一不可，否則請勿套用）：
  1. 寫入路徑已改為一律填入 company_code（建立請購單、採購單、驗收、付款分攤、
     彙整、部門、料號、廠商、成本中心、會計科目、分類、對照表、稽核紀錄）。
     否則 NOT NULL 上線後，既有建立功能會直接寫入失敗。
  2. 測試區執行第一批後，各表 company_code IS NULL 的筆數皆為 0（見第一批 log）。

本支開頭會先檢查所有表的 NULL 筆數，有任何 NULL 即拋出錯誤並列出表名與筆數，
不會嘗試猜測公司代碼。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "cpco3"
down_revision: Union[str, None] = "cpco2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ALL_TABLES = [
    "cycle_purchase_categories",
    "cycle_purchase_item_mappings",
    "cycle_purchase_payment_allocations",
    "cycle_purchase_pos",
    "cycle_purchase_departments",
    "cycle_purchase_requests",
    "cycle_purchase_summary",
    "cycle_purchase_items",
    "cycle_purchase_cost_centers",
    "cycle_purchase_account_codes",
    "cycle_purchase_vendors",
    "cycle_purchase_receiving",
    "cycle_purchase_payments",
    "cycle_purchase_audit_logs",
]


def upgrade() -> None:
    conn = op.get_bind()
    nulls = {}
    for t in ALL_TABLES:
        n = conn.execute(text(f"SELECT COUNT(*) FROM {t} WHERE company_code IS NULL")).scalar()
        if n:
            nulls[t] = n
    if nulls:
        detail = "、".join(f"{t}={n}" for t, n in nulls.items())
        raise RuntimeError(
            f"[cpco3] 以下表仍有 company_code 為 NULL，已中止：{detail}。"
            "請先人工確認歸屬公司並補值（或修正對照），再重新執行 upgrade。"
        )

    for t in ALL_TABLES:
        op.alter_column(t, "company_code", existing_type=sa.String(10), nullable=False)


def downgrade() -> None:
    for t in ALL_TABLES:
        op.alter_column(t, "company_code", existing_type=sa.String(10), nullable=True)
