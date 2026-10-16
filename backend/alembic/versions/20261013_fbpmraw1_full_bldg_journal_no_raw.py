"""全棟保養批次：新增 journal_no_raw 保存 Ragic 原始編號

Revision ID: fbpmraw1
Revises: kpoaud4
Create Date: 2026-10-13

2026-10-13 Samuel 裁示：2026/10 起 Ragic 編號改為「2026/10棟週保-006」，同步時統一轉成
「棟週保202610-006」供配對與顯示；原始編號另存 journal_no_raw。
既有列以 journal_no 回填 journal_no_raw，下一次同步會以 Ragic 原文覆蓋。

PostgreSQL 方言（CLAUDE.md §0）；IF NOT EXISTS，可重跑。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "fbpmraw1"
down_revision: Union[str, None] = "kpoaud4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE full_bldg_pm_batch "
        "ADD COLUMN IF NOT EXISTS journal_no_raw VARCHAR(50) NOT NULL DEFAULT ''"
    )
    op.execute(
        "UPDATE full_bldg_pm_batch SET journal_no_raw = journal_no WHERE journal_no_raw = ''"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE full_bldg_pm_batch DROP COLUMN IF EXISTS journal_no_raw")
