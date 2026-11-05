"""飯店週期保養：Sheet 11 項目(母)／項目(子) 欄位（2026-11-05）

Revision ID: hpc1
Revises: fmappm2
Create Date: 2026-11-05

新增 pm_batch_item.parent_no / child_no（nullable，既有列為 NULL）。
執行後需重新同步飯店週期保養（sync_from_sheet11），才會寫入值。
PostgreSQL 方言（CLAUDE.md §0）；IF NOT EXISTS，可重跑。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "hpc1"
down_revision: Union[str, None] = "fmappm2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE pm_batch_item ADD COLUMN IF NOT EXISTS parent_no VARCHAR(50)")
    op.execute("ALTER TABLE pm_batch_item ADD COLUMN IF NOT EXISTS child_no VARCHAR(50)")


def downgrade() -> None:
    op.execute("ALTER TABLE pm_batch_item DROP COLUMN IF EXISTS child_no")
    op.execute("ALTER TABLE pm_batch_item DROP COLUMN IF EXISTS parent_no")
