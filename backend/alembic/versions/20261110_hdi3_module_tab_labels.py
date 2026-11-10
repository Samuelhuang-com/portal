"""模組頁籤自訂名稱表 module_tab_labels（飯店每日巡檢頁籤名稱可在畫面上修改）

Revision ID: hdi3
Revises: hdi2
Create Date: 2026-11-10

2026-11-10 Samuel 裁示：飯店每日巡檢 7 個頁籤名稱開放在 Portal 頁面上直接修改。
(module, tab_key) 為主鍵；custom_label NULL＝使用預設名稱。可重跑（表已存在就略過）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "hdi3"
down_revision: Union[str, None] = "hdi2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("module_tab_labels"):
        return
    op.create_table(
        "module_tab_labels",
        sa.Column("module", sa.String(50), primary_key=True),
        sa.Column("tab_key", sa.String(50), primary_key=True),
        sa.Column("custom_label", sa.String(100), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("module_tab_labels")
