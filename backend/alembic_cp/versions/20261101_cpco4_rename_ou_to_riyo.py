"""週採多公司隔離：日曜公司顯示名稱改為「日曜」

Revision ID: cpco4
Revises: cpco3
Create Date: 2026-11-01

只改週採庫公司主檔的名稱（OU）。既有單據上的公司字串「日曜天地」仍保留，
由 ALIAS_TO_CODE 對應到 OU，不影響既有資料與隔離結果。
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "cpco4"
down_revision: Union[str, None] = "cpco3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text(
        "UPDATE cycle_purchase_companies SET name = '日曜' "
        "WHERE code = 'OU' AND name = '日曜天地'"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text(
        "UPDATE cycle_purchase_companies SET name = '日曜天地' "
        "WHERE code = 'OU' AND name = '日曜'"
    ))
