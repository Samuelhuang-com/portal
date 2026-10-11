"""KPO 稽核：期別新增 dept_order（本期部門顯示順序）

Revision ID: kpoaud2
Revises: kpoaud
Create Date: 2026-10-10

audit_kpo_periods.dept_order（TEXT, nullable）：部門 id 以逗號串接；空＝依部門主檔順序。
項目順序沿用 audit_kpo_period_items.sort_order，不需改欄位。
PostgreSQL 方言（CLAUDE.md §0）；欄位已存在則略過，可重跑。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "kpoaud2"
down_revision: Union[str, None] = "kpoaud"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("audit_kpo_periods"):
        return
    cols = {c["name"] for c in insp.get_columns("audit_kpo_periods")}
    if "dept_order" not in cols:
        op.add_column("audit_kpo_periods", sa.Column("dept_order", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("audit_kpo_periods") and "dept_order" in {c["name"] for c in insp.get_columns("audit_kpo_periods")}:
        op.drop_column("audit_kpo_periods", "dept_order")
