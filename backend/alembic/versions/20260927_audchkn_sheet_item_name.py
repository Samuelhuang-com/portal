"""audit_sheet_items 加「本期名稱快照」item_name

Revision ID: audchkn
Revises: audchk
Create Date: 2026-09-27

背景（2026-09-27 使用者裁示）
────────────────────────────────────────────────────────────────────────────
1. 已存在的歷史稽核單留在資料庫中，不動。
2. 可以在稽核單上直接修改某一列的檢查項名稱，只影響那一張單（該月 × 該公司）。
3. 檢查項主檔解鎖改名；改名只影響之後新加入稽核單的列。

作法：audit_sheet_items 新增 item_name，並把現有每一列補上「目前主檔名稱」，
之後畫面／匯出／統計一律讀快照，主檔怎麼改都不會回頭改到歷史。

PostgreSQL 方言（CLAUDE.md §0）。可重跑：欄位已存在就不加；backfill 只補 NULL。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "audchkn"
down_revision: Union[str, None] = "audchk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not _has_column("audit_sheet_items", "item_name"):
        op.add_column(
            "audit_sheet_items",
            sa.Column(
                "item_name", sa.String(length=200), nullable=True,
                comment="本期名稱快照（加入時取主檔名稱；可在稽核單上單獨修改，只影響本張）",
            ),
        )

    # 既有列補上目前主檔名稱 → 從此凍結，主檔改名不再影響這些歷史列
    op.execute(
        """
        UPDATE audit_sheet_items AS si
           SET item_name = ai.name
          FROM audit_items AS ai
         WHERE ai.id = si.item_id
           AND si.item_name IS NULL
        """
    )


def downgrade() -> None:
    if _has_column("audit_sheet_items", "item_name"):
        op.drop_column("audit_sheet_items", "item_name")
