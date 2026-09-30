"""add is_default to cycle_purchase_cost_centers

Revision ID: cpccdefault
Revises: cpitemcat
Create Date: 2026-09-30 12:30:00.000000

2026-09-30 Samuel 裁示：請購單（cycle-purchase/requests/{id}）的「成本中心」要把
**預設值直接呈現**，同一部門有多組時才讓使用者下拉選擇。

原本成本中心主檔只有 部門／代碼／名稱／啟用，沒有「預設」的概念，請購單一律空白、
要手動選。決策：

1. 主檔新增 `is_default`（每個部門最多一組，partial unique index 保證）。
2. 預設值判定（見 cycle_purchase_service.resolve_default_cost_center_id）：
   啟用中且 is_default → 用它；否則該部門**只有一組啟用中**的 → 視同預設；其餘 → 無。
3. 新增／複製／產生本期請購單時帶入預設值；既有「開放中（未關閉、未彙整）且成本中心
   空白」的請購單一次補上。已關閉／已彙整的不動。

本支 upgrade 也做第 3 點的一次性補填，但此時 is_default 全是 false，所以只補得到
「部門只有一組啟用中成本中心」的單。之後在主檔勾「預設」時，service 會再補一次該部門。

方言：PostgreSQL（見 CLAUDE.md §0）。刻意不使用 op.batch_alter_table。
⚠️ 新增 revision 已同步補 scripts/alembic_stamp_current.py 的 CP_CHAIN。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cpccdefault'
down_revision: Union[str, None] = 'cpitemcat'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'cycle_purchase_cost_centers',
        sa.Column(
            'is_default',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='是否為該部門的預設成本中心（每部門最多一組）',
        ),
    )
    # 每個部門最多一組預設（PostgreSQL partial unique index）
    op.create_index(
        'uq_cp_cc_dept_default',
        'cycle_purchase_cost_centers',
        ['department_id'],
        unique=True,
        postgresql_where=sa.text('is_default'),
    )

    # 一次性補填：開放中（未關閉、未彙整）且成本中心空白的請購單，
    # 部門只有一組啟用中成本中心的，直接帶入那一組。
    op.execute(
        """
        UPDATE cycle_purchase_requests r
           SET cost_center_id = cc.id
          FROM cycle_purchase_cost_centers cc
         WHERE r.cost_center_id IS NULL
           AND r.is_closed = false
           AND r.is_summarized = false
           AND cc.department_id = r.department_id
           AND cc.is_active = true
           AND (SELECT COUNT(*) FROM cycle_purchase_cost_centers c2
                 WHERE c2.department_id = r.department_id AND c2.is_active = true) = 1
        """
    )


def downgrade() -> None:
    # 補填的成本中心不回復（無法分辨哪些是本支補的、哪些是使用者之後自己選的）
    op.drop_index('uq_cp_cc_dept_default', table_name='cycle_purchase_cost_centers')
    op.drop_column('cycle_purchase_cost_centers', 'is_default')
