"""Ragic 簽核掃描三張表（2026-11-12）

Revision ID: rs1
Revises: hdi4
Create Date: 2026-11-12

新增 ragic_scan_fingerprint / ragic_scan_sheet / ragic_scan_hit，
對應 app/models/ragic_signoff_scan.py。PostgreSQL 方言（CLAUDE.md §0）。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "rs1"
down_revision: Union[str, None] = "hdi4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return inspect(op.get_bind()).has_table(name)


def _has_index(table: str, name: str) -> bool:
    return any(ix["name"] == name for ix in inspect(op.get_bind()).get_indexes(table))


def upgrade() -> None:
    # 冪等：sync_tool 啟動時的 _ensure_db_schema()（Base.metadata.create_all）可能已先建立這三張表，
    # 因此已存在就跳過，避免 DuplicateTable（2026-11-12 實際發生）。
    if not _has_table("ragic_scan_fingerprint"):
        op.create_table(
            "ragic_scan_fingerprint",
            sa.Column("sheet_path", sa.String(200), primary_key=True),
            sa.Column("record_id", sa.String(50), primary_key=True),
            sa.Column("fp", sa.String(64), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
    if not _has_table("ragic_scan_sheet"):
        op.create_table(
            "ragic_scan_sheet",
            sa.Column("sheet_path", sa.String(200), primary_key=True),
            sa.Column("sheet_name", sa.String(200), nullable=False, server_default=""),
            sa.Column("sheet_type", sa.String(50), nullable=False, server_default=""),
            sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("changed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_edit_at", sa.DateTime(), nullable=True),
            sa.Column("scanned_at", sa.DateTime(), nullable=False),
        )
    if not _has_table("ragic_scan_hit"):
        op.create_table(
            "ragic_scan_hit",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("sheet_path", sa.String(200), nullable=False),
            sa.Column("sheet_name", sa.String(200), nullable=False, server_default=""),
            sa.Column("record_id", sa.String(50), nullable=False),
            sa.Column("link", sa.String(400), nullable=False),
            sa.Column("status_values", sa.String(300), nullable=False, server_default=""),
            sa.Column("scanned_at", sa.DateTime(), nullable=False),
        )
    if not _has_index("ragic_scan_hit", "ix_ragic_scan_hit_sheet_path"):
        op.create_index("ix_ragic_scan_hit_sheet_path", "ragic_scan_hit", ["sheet_path"])


def downgrade() -> None:
    op.drop_index("ix_ragic_scan_hit_sheet_path", table_name="ragic_scan_hit")
    op.drop_table("ragic_scan_hit")
    op.drop_table("ragic_scan_sheet")
    op.drop_table("ragic_scan_fingerprint")
