"""KPO 稽核（財#1 稽核系統建構）：建立 4 張資料表並植入 9 部門稽核項目

Revision ID: kpoaud
Revises: fmap1005
Create Date: 2026-10-10

資料表：audit_kpo_departments / audit_kpo_items / audit_kpo_periods / audit_kpo_period_items
種子資料來自 Excel「財#1稽核系統建構-整合」（9 部門、共 142 項），與後端啟動步驟
services/audit_kpo_service.seed_kpo_master 共用同一個函式；僅在部門表為空時植入，可重跑。

PostgreSQL 方言（CLAUDE.md §0）。已存在的表一律略過，可重跑。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "kpoaud"
down_revision: Union[str, None] = "fmap1005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("audit_kpo_departments"):
        op.create_table(
            "audit_kpo_departments",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(50), nullable=False, unique=True),
            sa.Column("source_title", sa.String(200), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not insp.has_table("audit_kpo_items"):
        op.create_table(
            "audit_kpo_items",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("department_id", sa.Integer(),
                      sa.ForeignKey("audit_kpo_departments.id", ondelete="CASCADE"), nullable=False),
            sa.Column("item_no", sa.Integer(), nullable=True),
            sa.Column("is_key", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("score", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("method", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_audit_kpo_items_department_id", "audit_kpo_items", ["department_id"])

    if not insp.has_table("audit_kpo_periods"):
        op.create_table(
            "audit_kpo_periods",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("period", sa.String(7), nullable=False),
            sa.Column("title", sa.String(100), nullable=False, server_default="財#1稽核系統建構"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_audit_kpo_periods_period", "audit_kpo_periods", ["period"])

    if not insp.has_table("audit_kpo_period_items"):
        op.create_table(
            "audit_kpo_period_items",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("period_id", sa.Integer(),
                      sa.ForeignKey("audit_kpo_periods.id", ondelete="CASCADE"), nullable=False),
            sa.Column("department_id", sa.Integer(),
                      sa.ForeignKey("audit_kpo_departments.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("source_item_id", sa.Integer(),
                      sa.ForeignKey("audit_kpo_items.id", ondelete="SET NULL"), nullable=True),
            sa.Column("item_no", sa.Integer(), nullable=True),
            sa.Column("is_key", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("score", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("method", sa.Text(), nullable=True),
            sa.Column("result", sa.String(10), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("period_id", "source_item_id", name="uq_audit_kpo_pi_period_src"),
        )
        op.create_index("ix_audit_kpo_period_items_period_id", "audit_kpo_period_items", ["period_id"])
        op.create_index("ix_audit_kpo_period_items_department_id", "audit_kpo_period_items", ["department_id"])

    # 種子：9 部門 × 稽核項目（冪等）
    from sqlalchemy.orm import Session
    from app.services.audit_kpo_service import seed_kpo_master

    with Session(bind=bind) as s:
        seed_kpo_master(s)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for t in ("audit_kpo_period_items", "audit_kpo_periods", "audit_kpo_items", "audit_kpo_departments"):
        if insp.has_table(t):
            op.drop_table(t)
