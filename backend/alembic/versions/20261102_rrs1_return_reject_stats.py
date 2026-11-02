"""退件統計：return_stats_source / return_stats_record / return_stats_step

Revision ID: rrs1
Revises: mallfi2
Create Date: 2026-11-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "rrs1"
down_revision: Union[str, None] = "mallfi2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("return_stats_source"):
        op.create_table(
            "return_stats_source",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("source_key", sa.String(120), nullable=False, unique=True),
            sa.Column("company", sa.String(20), nullable=False),
            sa.Column("form_type", sa.String(10), nullable=False),
            sa.Column("dept_display", sa.String(50), nullable=False, server_default=""),
            sa.Column("form_name", sa.String(100), nullable=False, server_default=""),
            sa.Column("ragic_path", sa.String(200), nullable=False),
            sa.Column("origin", sa.String(20), nullable=False, server_default="module_table"),
            sa.Column("origin_table", sa.String(60), nullable=True),
            sa.Column("parser_profile", sa.String(40), nullable=False, server_default="standard_v1"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        )
    if not _has_table("return_stats_record"):
        op.create_table(
            "return_stats_record",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("source_key", sa.String(120), nullable=False),
            sa.Column("ragic_record_id", sa.String(30), nullable=False),
            sa.Column("company", sa.String(20), nullable=False, server_default=""),
            sa.Column("form_type", sa.String(10), nullable=False, server_default=""),
            sa.Column("dept_display", sa.String(50), nullable=False, server_default=""),
            sa.Column("form_name", sa.String(100), nullable=False, server_default=""),
            sa.Column("applicant", sa.String(100), nullable=True),
            sa.Column("apply_date", sa.Date(), nullable=True),
            sa.Column("amount", sa.Integer(), nullable=True),
            sa.Column("purpose", sa.Text(), nullable=True),
            sa.Column("ragic_status", sa.String(20), nullable=True),
            sa.Column("submitter", sa.String(100), nullable=True),
            sa.Column("next_approver", sa.String(200), nullable=True),
            sa.Column("outcome", sa.String(20), nullable=False, server_default="unknown"),
            sa.Column("outcome_reason", sa.String(200), nullable=False, server_default=""),
            sa.Column("inferred_last_step", sa.Integer(), nullable=True),
            sa.Column("last_sign_date", sa.Date(), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("synced_at", sa.DateTime(), nullable=True),
            sa.Column("raw_json", sa.Text(), nullable=False, server_default="{}"),
            sa.UniqueConstraint("source_key", "ragic_record_id", name="uq_rs_record_source_rid"),
        )
        op.create_index("ix_rs_record_source_key", "return_stats_record", ["source_key"])
        op.create_index("ix_rs_record_company_dept", "return_stats_record", ["company", "dept_display"])
        op.create_index("ix_rs_record_apply_date", "return_stats_record", ["apply_date"])
        op.create_index("ix_rs_record_outcome", "return_stats_record", ["outcome"])
    if not _has_table("return_stats_step"):
        op.create_table(
            "return_stats_step",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("record_id", sa.Integer(),
                      sa.ForeignKey("return_stats_record.id", ondelete="CASCADE"), nullable=False),
            sa.Column("step_no", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("role_field", sa.String(40), nullable=False, server_default=""),
            sa.Column("approver_text", sa.String(200), nullable=False, server_default=""),
            sa.Column("sign_date", sa.Date(), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("is_inferred_last", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.create_index("ix_return_stats_step_record_id", "return_stats_step", ["record_id"])


def downgrade() -> None:
    op.drop_table("return_stats_step")
    op.drop_table("return_stats_record")
    op.drop_table("return_stats_source")
