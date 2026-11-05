"""樓層巡檢圖：子項點位（floor_map_points.child_ref）（2026-11-05）

Revision ID: fmapcc1
Revises: hpc1
Create Date: 2026-11-05

子項可各自放點：child_ref 為子項參照，source_ref 仍為母項。母項點位 child_ref 為 NULL。
PostgreSQL 方言（CLAUDE.md §0）；IF NOT EXISTS，可重跑。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "fmapcc1"
down_revision: Union[str, None] = "hpc1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE floor_map_points ADD COLUMN IF NOT EXISTS child_ref VARCHAR(200)")


def downgrade() -> None:
    # 子項點位刪除後無法還原為母項點位，downgrade 會一併停用（is_active=false）子項點位再移除欄位
    op.execute("UPDATE floor_map_points SET is_active = false WHERE child_ref IS NOT NULL")
    op.execute("ALTER TABLE floor_map_points DROP COLUMN IF EXISTS child_ref")
