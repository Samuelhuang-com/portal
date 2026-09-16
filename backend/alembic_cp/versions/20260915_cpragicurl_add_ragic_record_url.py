"""add ragic_record_url to cycle_purchase_summary

Revision ID: cpragicurl
Revises: baseline_cp
Create Date: 2026-09-15 23:10:00.000000

2026-09-15 新增：彙整單頁「依供應商分組」要能點單號直接開到 Ragic 那一張單。

為什麼需要新欄位——`ragic_record_id` 不夠用：
  - 它存的是**給人看的採購編號**（樂管週採00003），而 Ragic 的單筆網址要的是
    **內部 _ragicId**（樂管週採00003 的內部 id 是 2，網址是 .../57/2）。
  - 兩者沒有任何可推導的關係。目前這張表剛好「編號 - 1 = 內部 id」純粹是因為
    還沒刪過任何一筆，刪一筆就永遠對不起來，絕對不能靠這個推算。
  - `ragic_record_id` 已經有正式資料在用（且顯示在清單上），不適合改語意。

所以改成在拋轉當下就把**完整網址**存起來：前端直接 <a href> 就好，不用在前端
再拼一次網址（表單位置的唯一真實來源是 config.py 的 RAGIC_CP_SUMMARY_*）。

⚠️ 既有已拋轉的列（樂管週採00003／00004／00005）這個欄位會是 NULL，畫面上
   單號照常顯示、只是不可點。要補的話就「取消拋轉 → 重推」，會拿到新的一張單。

方言：PostgreSQL（見 CLAUDE.md §0）。刻意不使用 op.batch_alter_table——
那是 SQLite 改欄位的 workaround，PG 直接 ALTER 即可。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cpragicurl'
down_revision: Union[str, None] = 'baseline_cp'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'cycle_purchase_summary',
        sa.Column(
            'ragic_record_url',
            sa.String(length=300),
            nullable=True,
            comment='Ragic 該筆記錄的完整網址（拋轉當下由後端依 config 組出並存檔，'
                    '前端「依供應商分組」的單號連結直接用這個值）',
        ),
    )


def downgrade() -> None:
    op.drop_column('cycle_purchase_summary', 'ragic_record_url')
