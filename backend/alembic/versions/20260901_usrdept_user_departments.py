"""user_departments 使用者↔部門多對多關聯表

Revision ID: usrdept
Revises: tncomp
Create Date: 2026-09-01

背景（使用者 2026-09-01 裁示）
────────────────────────────────────────────────────────────────────────────
1. 同部門的人都能操作該部門的週採請購單（原本是一部門一位承辦人）。
2. 一個 User 可屬多公司、多部門。

因此新增 user_departments（user_id ↔ departments.id 多對多）。公司別由部門
自動推導（RefDepartment.company_id），不另建 user_companies。
`users.tenant_id` 完全不動，語意退化為「主要公司別」。

純新增一張表，不動任何既有表——這種 migration 不需要 batch_alter_table。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "usrdept"
down_revision: Union[str, None] = "tncomp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_departments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("department_id", sa.Integer(),
                  sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "department_id", name="uq_user_department"),
    )
    op.create_index("ix_user_departments_user_id", "user_departments", ["user_id"])
    op.create_index("ix_user_departments_department_id", "user_departments", ["department_id"])


def downgrade() -> None:
    op.drop_index("ix_user_departments_department_id", table_name="user_departments")
    op.drop_index("ix_user_departments_user_id", table_name="user_departments")
    op.drop_table("user_departments")
