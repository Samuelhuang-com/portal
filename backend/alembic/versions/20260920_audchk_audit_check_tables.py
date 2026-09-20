"""audit_check 稽核檢查模組九張表

Revision ID: audchk
Revises: tcpurch
Create Date: 2026-09-20

背景
────────────────────────────────────────────────────────────────────────────
新增「稽核檢查」模組（財#3 系統建置稽核）。純新增，不動任何既有表。
公司別／部門沿用 reference_data 的 companies / departments，直接建 FK。

PostgreSQL 方言（CLAUDE.md §0）。所有識別名稱皆已控制在 63 bytes 內。

⚠️ 可重跑：main.py 啟動時的 Base.metadata.create_all() 可能已先把表建出來，
   因此每張表／索引都先檢查存在與否，不存在才建，避免 DuplicateTable。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "audchk"
down_revision: Union[str, None] = "tcpurch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _ensure_index(name: str, table: str, cols: list) -> None:
    existing = {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, cols, unique=False)


def upgrade() -> None:
    # ── 判定類型主檔（使用者自訂字色語意）────────────────────────────────
    if not _has_table("audit_result_types"):
        op.create_table(
            "audit_result_types",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("code", sa.String(length=20), nullable=False, comment="程式用代碼"),
            sa.Column("label", sa.String(length=50), nullable=False, comment="顯示名稱"),
            sa.Column("color", sa.String(length=20), nullable=False, server_default="#000000", comment="文字色碼"),
            sa.Column("counts_as_pass", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="是否算達標"),
            sa.Column("include_in_summary", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否列入缺失彙整"),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code", name="uq_audit_result_types_code"),
        )

    # ── 檢查項主檔（兩階自我參照）────────────────────────────────────────
    if not _has_table("audit_items"):
        op.create_table(
            "audit_items",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=200), nullable=False, comment="項目名稱（純名稱）"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["parent_id"], ["audit_items.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("parent_id", "name", name="uq_audit_items_parent_name"),
        )

    # ── 期別 ──────────────────────────────────────────────────────────────
    if not _has_table("audit_periods"):
        op.create_table(
            "audit_periods",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("period", sa.String(length=7), nullable=False, comment="YYYY-MM"),
            sa.Column("title", sa.String(length=100), nullable=False),
            sa.Column("goal_major", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("goal_minor", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("review_counts_in_score", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="覆核區是否計為一個稽核子項"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
            sa.Column("created_by", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("period", name="uq_audit_periods_period"),
        )

    # ── 稽核單（期別 × 公司）──────────────────────────────────────────────
    if not _has_table("audit_sheets"):
        op.create_table(
            "audit_sheets",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("period_id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("audited_on", sa.Date(), nullable=True),
            sa.Column("audited_session", sa.String(length=10), nullable=True),
            sa.Column("executor_label", sa.String(length=50), nullable=True),
            sa.Column("completion_adjust", sa.Integer(), nullable=False, server_default="0", comment="完成率已完成數的人工調整"),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("created_by", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["period_id"], ["audit_periods.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("period_id", "company_id", name="uq_audit_sheets_period_company"),
        )
    _ensure_index("ix_audit_sheets_period_id", "audit_sheets", ["period_id"])
    _ensure_index("ix_audit_sheets_company_id", "audit_sheets", ["company_id"])

    # ── 稽核單部門欄 ──────────────────────────────────────────────────────
    if not _has_table("audit_sheet_departments"):
        op.create_table(
            "audit_sheet_departments",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("sheet_id", sa.Integer(), nullable=False),
            sa.Column("department_id", sa.Integer(), nullable=False),
            sa.Column("column_label", sa.String(length=50), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("deficiency_override", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["sheet_id"], ["audit_sheets.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("sheet_id", "department_id", name="uq_audit_sheet_dept"),
        )
    _ensure_index("ix_audit_sheet_depts_sheet_id", "audit_sheet_departments", ["sheet_id"])

    # ── 稽核單檢查項列 ────────────────────────────────────────────────────
    if not _has_table("audit_sheet_items"):
        op.create_table(
            "audit_sheet_items",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("sheet_id", sa.Integer(), nullable=False),
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("parent_sheet_item_id", sa.Integer(), nullable=True),
            sa.Column("display_no", sa.String(length=10), nullable=True),
            sa.Column("scope_note", sa.String(length=200), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["sheet_id"], ["audit_sheets.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["item_id"], ["audit_items.id"]),
            sa.ForeignKeyConstraint(["parent_sheet_item_id"], ["audit_sheet_items.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("sheet_id", "item_id", name="uq_audit_sheet_item"),
        )
    _ensure_index("ix_audit_sheet_items_sheet_id", "audit_sheet_items", ["sheet_id"])

    # ── 該期該項的建議查核部門 ────────────────────────────────────────────
    if not _has_table("audit_item_targets"):
        op.create_table(
            "audit_item_targets",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("sheet_item_id", sa.Integer(), nullable=False),
            sa.Column("department_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["sheet_item_id"], ["audit_sheet_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("sheet_item_id", "department_id", name="uq_audit_item_target"),
        )
    _ensure_index("ix_audit_item_targets_item_id", "audit_item_targets", ["sheet_item_id"])

    # ── 交叉格 ────────────────────────────────────────────────────────────
    if not _has_table("audit_cells"):
        op.create_table(
            "audit_cells",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("sheet_id", sa.Integer(), nullable=False),
            sa.Column("sheet_item_id", sa.Integer(), nullable=False),
            sa.Column("sheet_department_id", sa.Integer(), nullable=False),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("result_code", sa.String(length=20), nullable=False, server_default="ok"),
            sa.Column("updated_by", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["sheet_id"], ["audit_sheets.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sheet_item_id"], ["audit_sheet_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sheet_department_id"], ["audit_sheet_departments.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("sheet_item_id", "sheet_department_id", name="uq_audit_cells_item_dept"),
        )
    _ensure_index("ix_audit_cells_sheet_id", "audit_cells", ["sheet_id"])
    _ensure_index("ix_audit_cells_item_id", "audit_cells", ["sheet_item_id"])
    _ensure_index("ix_audit_cells_dept_id", "audit_cells", ["sheet_department_id"])

    # ── 覆核區 ────────────────────────────────────────────────────────────
    if not _has_table("audit_reviews"):
        op.create_table(
            "audit_reviews",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("sheet_id", sa.Integer(), nullable=False),
            sa.Column("sheet_department_id", sa.Integer(), nullable=False),
            sa.Column("source_period", sa.String(length=7), nullable=True),
            sa.Column("pending_text", sa.Text(), nullable=True),
            sa.Column("pending_result", sa.String(length=20), nullable=False, server_default="ok"),
            sa.Column("result_text", sa.Text(), nullable=True),
            sa.Column("result_status", sa.String(length=20), nullable=False, server_default="ok"),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["sheet_id"], ["audit_sheets.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sheet_department_id"], ["audit_sheet_departments.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("sheet_id", "sheet_department_id", name="uq_audit_reviews_sheet_dept"),
        )
    _ensure_index("ix_audit_reviews_sheet_id", "audit_reviews", ["sheet_id"])


def downgrade() -> None:
    for tbl in (
        "audit_reviews",
        "audit_cells",
        "audit_item_targets",
        "audit_sheet_items",
        "audit_sheet_departments",
        "audit_sheets",
        "audit_periods",
        "audit_items",
        "audit_result_types",
    ):
        if _has_table(tbl):
            op.drop_table(tbl)
