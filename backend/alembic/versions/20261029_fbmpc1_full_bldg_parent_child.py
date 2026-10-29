"""全棟週期保養：Sheet28 項目(母)／項目(子)／項目母項名稱 欄位

Revision ID: fbmpc1
Revises: mallpc1
Create Date: 2026-10-29

新增 full_bldg_pm_batch_item.parent_no / child_no / parent_name（nullable，既有列為 NULL）。
執行後需重新同步全棟週期保養，才會寫入值。
PostgreSQL 方言（CLAUDE.md §0）；IF NOT EXISTS，可重跑。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "fbmpc1"
down_revision: Union[str, None] = "mallpc1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE full_bldg_pm_batch_item ADD COLUMN IF NOT EXISTS parent_no VARCHAR(50)")
    op.execute("ALTER TABLE full_bldg_pm_batch_item ADD COLUMN IF NOT EXISTS child_no VARCHAR(50)")
    op.execute("ALTER TABLE full_bldg_pm_batch_item ADD COLUMN IF NOT EXISTS parent_name VARCHAR(200)")


def downgrade() -> None:
    op.execute("ALTER TABLE full_bldg_pm_batch_item DROP COLUMN IF EXISTS parent_name")
    op.execute("ALTER TABLE full_bldg_pm_batch_item DROP COLUMN IF EXISTS child_no")
    op.execute("ALTER TABLE full_bldg_pm_batch_item DROP COLUMN IF EXISTS parent_no")
