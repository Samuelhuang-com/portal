"""KPO 稽核：部門改為可連結 settings/company-departments（公司別＋部門別）

Revision ID: kpoaud3
Revises: kpoaud2
Create Date: 2026-10-10

audit_kpo_departments：
  + company_id          （FK companies.id，SET NULL，nullable）
  + ref_department_id   （FK departments.id，SET NULL，nullable）
  - name 的單欄唯一限制（各公司都有「營業部」）→ 改為 (company_id, name) 唯一；name 改普通索引、長度 100
Excel 植入的 9 個部門 company_id／ref_department_id 維持 NULL（尚未連結），可在主檔頁編輯時補選。

PostgreSQL 方言（CLAUDE.md §0）。欄位／限制已存在則略過，可重跑。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "kpoaud3"
down_revision: Union[str, None] = "kpoaud2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

T = "audit_kpo_departments"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(T):
        return
    cols = {c["name"] for c in insp.get_columns(T)}
    if "company_id" not in cols:
        op.add_column(T, sa.Column("company_id", sa.Integer(),
                                   sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True))
    if "ref_department_id" not in cols:
        op.add_column(T, sa.Column("ref_department_id", sa.Integer(),
                                   sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True))

    # 拿掉 name 單欄唯一（名稱由 inspector 查，不寫死自動產生的名稱）
    for uc in insp.get_unique_constraints(T):
        if uc["column_names"] == ["name"]:
            op.drop_constraint(uc["name"], T, type_="unique")
    op.alter_column(T, "name", existing_type=sa.String(50), type_=sa.String(100), existing_nullable=False)

    insp = sa.inspect(bind)
    if not any(i["column_names"] == ["name"] for i in insp.get_indexes(T)):
        op.create_index("ix_audit_kpo_departments_name", T, ["name"])
    if "uq_audit_kpo_dept_company_name" not in {u["name"] for u in insp.get_unique_constraints(T)}:
        op.create_unique_constraint("uq_audit_kpo_dept_company_name", T, ["company_id", "name"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(T):
        return
    if "uq_audit_kpo_dept_company_name" in {u["name"] for u in insp.get_unique_constraints(T)}:
        op.drop_constraint("uq_audit_kpo_dept_company_name", T, type_="unique")
    cols = {c["name"] for c in insp.get_columns(T)}
    for c in ("ref_department_id", "company_id"):
        if c in cols:
            op.drop_column(T, c)
