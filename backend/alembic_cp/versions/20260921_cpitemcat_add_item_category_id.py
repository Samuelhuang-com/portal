"""add category_id to cycle_purchase_items

Revision ID: cpitemcat
Revises: cpragicdept
Create Date: 2026-09-21 18:00:00.000000

2026-09-21 Samuel 發現：料號主檔（cycle-purchase/items）「類別」下拉是前端寫死的
4 個舊值（工務／清潔用品／文具印刷／營業用品），但資料實際存的是類別主檔
（cycle-purchase/masters/categories）的「類別字串」（如「客廁備品-衛生紙」）。
結果：新增料號只能選對不上主檔的舊值、編輯時一動下拉就把正確字串改壞，
改壞的料號在週期設定「適用品類」／請購單「可選料號」裡直接消失，沒有任何錯誤。

修法（Samuel 裁示）：料號改接類別主檔的**細分類 id**，前端改大／中／細三層選單。
`cycle_purchase_items.category` 字串**保留**，改為由後端依 category_id 從主檔
`category_name` 自動帶入——週期設定 applicable_categories、請購單可選料號、
類別主檔料號數都是拿這個字串比對，保留它就不用改那幾處、既有週期設定也不會失效。

NULL＝尚未對應（既有資料待回填：Temp/cp_items_category_backfill_20260921.sql）。
ondelete=RESTRICT：類別主檔目前沒有刪除端點，真要刪時必須先把料號移走，
不允許靜默變成 NULL 讓料號又從請購單消失。

方言：PostgreSQL（見 CLAUDE.md §0）。刻意不使用 op.batch_alter_table。
⚠️ 新增 revision 已同步補 scripts/alembic_stamp_current.py 的 CP_CHAIN。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cpitemcat'
down_revision: Union[str, None] = 'cpragicdept'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'cycle_purchase_items',
        sa.Column(
            'category_id',
            sa.Integer(),
            nullable=True,
            comment='類別主檔細分類（→ cycle_purchase_categories.id）；'
                    'NULL=尚未對應。category 字串由後端依此欄自動帶入',
        ),
    )
    op.create_foreign_key(
        'fk_cp_items_category_id',
        'cycle_purchase_items', 'cycle_purchase_categories',
        ['category_id'], ['id'],
        ondelete='RESTRICT',
    )
    op.create_index('ix_cp_items_category_id', 'cycle_purchase_items', ['category_id'])


def downgrade() -> None:
    op.drop_index('ix_cp_items_category_id', table_name='cycle_purchase_items')
    op.drop_constraint('fk_cp_items_category_id', 'cycle_purchase_items', type_='foreignkey')
    op.drop_column('cycle_purchase_items', 'category_id')
