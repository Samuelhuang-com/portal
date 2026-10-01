"""收斂 audchks：資料庫若曾跑過第一版 audchks（部門層級 suggestion_override），
這支會補上 audit_cells.suggestion 並拿掉 suggestion_override。已是最終狀態則什麼都不做。

Revision ID: audchkt
Revises: audchks
Create Date: 2026-10-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "audchkt"
down_revision: Union[str, None] = "audchks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
    return column in cols


def _converge() -> None:
    """冪等：最終狀態＝audit_cells.suggestion 存在、audit_sheet_departments.suggestion_override 不存在。"""
    if not _has_column("audit_cells", "suggestion"):
        op.add_column(
            "audit_cells",
            sa.Column(
                "suggestion", sa.Text(), nullable=True,
                comment="建議（2026-10-01）：固定藍字、與判定無關，不計分；評語空白但有建議時仍保留此列",
            ),
        )
    if _has_column("audit_sheet_departments", "suggestion_override"):
        op.drop_column("audit_sheet_departments", "suggestion_override")


def upgrade() -> None:
    _converge()


def downgrade() -> None:
    pass   # 收斂用，退版交給 audchks
