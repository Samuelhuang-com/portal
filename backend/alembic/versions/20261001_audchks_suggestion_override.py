"""audit_sheet_departments 加「建議」人工覆寫 suggestion_override

Revision ID: audchks
Revises: audchkd
Create Date: 2026-10-01

背景（2026-10-01 使用者要求）
────────────────────────────────────────────────────────────────────────────
稽核單（audit-check/sheets/:id）「缺失」列下面多一列「建議」。
「列入彙整」的判定拆成兩列：不算達標者（扣分）→ 缺失；算達標者（建議）→ 建議。
兩列都可人工覆寫，空值＝自動彙整。

PostgreSQL 方言（CLAUDE.md §0）。可重跑：欄位已存在就不加。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "audchks"
down_revision: Union[str, None] = "audchkd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not _has_column("audit_sheet_departments", "suggestion_override"):
        op.add_column(
            "audit_sheet_departments",
            sa.Column(
                "suggestion_override", sa.Text(), nullable=True,
                comment="「建議」人工覆寫；空值＝自動彙整（2026-10-01）",
            ),
        )


def downgrade() -> None:
    if _has_column("audit_sheet_departments", "suggestion_override"):
        op.drop_column("audit_sheet_departments", "suggestion_override")
