"""stock_issues 補 posted_date 欄位（週採資料庫，2026-11-17）

Revision ID: cpstk4
Revises: cpstk3
Create Date: 2026-11-17

測試區 14:31 重啟後端時，啟動 create_all 依當下（開發中、尚未有 posted_date）的 model 建了 stock_issues；
之後 cpstk3 看到表已存在就跳過，欄位一直沒補上，領用單清單與 KPI 查詢失敗（「讀取單據失敗」）。
本支只在欄位不存在時補上；照正常順序部署的環境（cpstk3 建表時已含此欄）不會有任何變更。可重複執行。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "cpstk4"
down_revision: Union[str, None] = "cpstk3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, col: str) -> bool:
    insp = inspect(op.get_bind())
    return insp.has_table(table) and any(c["name"] == col for c in insp.get_columns(table))


def upgrade() -> None:
    if inspect(op.get_bind()).has_table("stock_issues") and not _has_column("stock_issues", "posted_date"):
        op.add_column("stock_issues", sa.Column("posted_date", sa.Date(), nullable=True))


def downgrade() -> None:
    # 不移除：posted_date 屬於 cpstk3 的正式欄位，本支只是補缺
    pass
