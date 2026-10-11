"""現場營運稽核：新增「公司別稽核單」與「受稽部門」，選定項目改掛稽核單

Revision ID: kpoaud4
Revises: kpoaud3
Create Date: 2026-10-11

2026-10-11 Samuel 裁示：現場營運稽核（audit-check/kpo）建立方式比照 audit-check：
  建立期別 → 新增公司別稽核單 → 選受稽部門（來源＝現場營運稽核項目的部門，不依公司過濾）
  → periods/:id 依「公司 → 部門 → 稽核項目」呈現。

  + audit_kpo_sheets        （period_id × company_id 唯一）
  + audit_kpo_sheet_depts   （sheet_id × department_id 唯一，sort_order＝顯示順序）
  + audit_kpo_period_items.sheet_id（NOT NULL，FK sheets CASCADE）
  - uq_audit_kpo_pi_period_src → uq_audit_kpo_pi_sheet_src（sheet_id, source_item_id）
  舊測試期別／選定項目沒有公司別 → 依裁示「清空重建」：刪除 audit_kpo_period_items 與 audit_kpo_periods
  （不動部門與項目主檔）。audit_kpo_periods.dept_order 欄位保留但不再使用。

PostgreSQL 方言（CLAUDE.md §0）；已存在則略過，可重跑。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "kpoaud4"
down_revision: Union[str, None] = "kpoaud3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PI = "audit_kpo_period_items"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(PI):
        return

    if not insp.has_table("audit_kpo_sheets"):
        op.create_table(
            "audit_kpo_sheets",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("period_id", sa.Integer(), sa.ForeignKey("audit_kpo_periods.id", ondelete="CASCADE"), nullable=False),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("period_id", "company_id", name="uq_audit_kpo_sheet_period_company"),
        )
        op.create_index("ix_audit_kpo_sheets_period_id", "audit_kpo_sheets", ["period_id"])
        op.create_index("ix_audit_kpo_sheets_company_id", "audit_kpo_sheets", ["company_id"])

    if not insp.has_table("audit_kpo_sheet_depts"):
        op.create_table(
            "audit_kpo_sheet_depts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("sheet_id", sa.Integer(), sa.ForeignKey("audit_kpo_sheets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("department_id", sa.Integer(), sa.ForeignKey("audit_kpo_departments.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.UniqueConstraint("sheet_id", "department_id", name="uq_audit_kpo_sheet_dept"),
        )
        op.create_index("ix_audit_kpo_sheet_depts_sheet_id", "audit_kpo_sheet_depts", ["sheet_id"])
        op.create_index("ix_audit_kpo_sheet_depts_department_id", "audit_kpo_sheet_depts", ["department_id"])

    cols = {c["name"] for c in insp.get_columns(PI)}
    if "sheet_id" not in cols:
        # 裁示：舊測試資料（無公司別）清空重建。先清再加 NOT NULL 欄位。
        op.execute(f"DELETE FROM {PI}")
        op.execute("DELETE FROM audit_kpo_periods")
        op.add_column(PI, sa.Column("sheet_id", sa.Integer(),
                                    sa.ForeignKey("audit_kpo_sheets.id", ondelete="CASCADE"), nullable=False))
        op.create_index("ix_audit_kpo_period_items_sheet_id", PI, ["sheet_id"])

    insp = sa.inspect(bind)
    ucs = {u["name"] for u in insp.get_unique_constraints(PI)}
    if "uq_audit_kpo_pi_period_src" in ucs:
        op.drop_constraint("uq_audit_kpo_pi_period_src", PI, type_="unique")
    if "uq_audit_kpo_pi_sheet_src" not in ucs:
        op.create_unique_constraint("uq_audit_kpo_pi_sheet_src", PI, ["sheet_id", "source_item_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(PI):
        return
    op.execute(f"DELETE FROM {PI}")
    ucs = {u["name"] for u in insp.get_unique_constraints(PI)}
    if "uq_audit_kpo_pi_sheet_src" in ucs:
        op.drop_constraint("uq_audit_kpo_pi_sheet_src", PI, type_="unique")
    cols = {c["name"] for c in insp.get_columns(PI)}
    if "sheet_id" in cols:
        op.drop_column(PI, "sheet_id")
    if "uq_audit_kpo_pi_period_src" not in ucs:
        op.create_unique_constraint("uq_audit_kpo_pi_period_src", PI, ["period_id", "source_item_id"])
    for t in ("audit_kpo_sheet_depts", "audit_kpo_sheets"):
        if insp.has_table(t):
            op.drop_table(t)
