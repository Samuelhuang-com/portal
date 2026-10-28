"""商場週期保養：Sheet24 項目(母)／項目(子) 欄位

Revision ID: mallpc1
Revises: fbpmraw1
Create Date: 2026-10-28

新增 mall_pm_batch_item.parent_no / child_no（nullable，既有列為 NULL）。
執行後需重新同步商場週期保養，才會寫入值。
PostgreSQL 方言（CLAUDE.md §0）；IF NOT EXISTS，可重跑。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "mallpc1"
down_revision: Union[str, None] = "fbpmraw1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE mall_pm_batch_item ADD COLUMN IF NOT EXISTS parent_no VARCHAR(50)")
    op.execute("ALTER TABLE mall_pm_batch_item ADD COLUMN IF NOT EXISTS child_no VARCHAR(50)")


def downgrade() -> None:
    op.execute("ALTER TABLE mall_pm_batch_item DROP COLUMN IF EXISTS child_no")
    op.execute("ALTER TABLE mall_pm_batch_item DROP COLUMN IF EXISTS parent_no")
