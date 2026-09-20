"""add ragic_dept to cycle_purchase_departments

🛑 2026-09-20：這個欄位**已停用**，ORM 上已經拿掉（models/cycle_purchase_reference.py）。
   0919 會議後 Ragic「★週期請購單」(sheet 58) 把部門下放到子表、逐列一個且改成
   自由文字，Portal 直接送部門名稱即可，七選一的對照沒有存在意義了。

   ⚠️ **這支 migration 刻意保留在鏈上、不刪檔**：若某台環境已經套用過，刪檔會讓
   alembic 找不到 revision 而整條鏈壞掉。還沒套用的環境跑了也只是多一個沒人用的
   欄位，代價遠小於弄壞版本鏈。要清掉的話另外開一支 drop_column 的 migration。


Revision ID: cpragicdept
Revises: cpragicurl
Create Date: 2026-09-18 22:30:00.000000

2026-09-18：彙整單拋轉目標由 Ragic sheet 57「週採採購單」改為
sheet 58「★週採請購單」（Samuel 裁示）。

sheet 58 主表的「部門」是**必填＋單選**，而且只吃這七個字串：
    營業／管理／行銷／資訊／執董室／財務／工務

週採部門主檔的 `dept_name` 則是自由文字（來源是 portal.db 的 RefDepartment，
常見寫法是「工務部」這種帶「部」的）。兩邊沒有保證能對上，而且：

  - 用程式猜（去掉尾字「部」再比對）今天可能剛好會通，哪天有人把部門改名成
    「工程部」就整批靜默拋不過去，而且錯誤訊息會指向 Ragic 而不是命名。
  - Ragic 那個選單沒有開 attr_userOps，送不在清單裡的值會被整筆退。

所以 2026-09-18 Samuel 裁示：**在部門主檔多一欄由使用者逐筆指定**。
NULL ＝ 尚未對照 → 該部門的彙整列不拋轉，列在回傳的 not_pushed 清單裡讓人看見。

方言：PostgreSQL（見 CLAUDE.md §0）。刻意不使用 op.batch_alter_table。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cpragicdept'
down_revision: Union[str, None] = 'cpragicurl'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'cycle_purchase_departments',
        sa.Column(
            'ragic_dept',
            sa.String(length=20),
            nullable=True,
            comment='對應 Ragic 週採請購單(sheet 58)主表「部門」的選單值，'
                    '七選一：營業/管理/行銷/資訊/執董室/財務/工務。'
                    'NULL=未對照，拋轉時該部門的彙整列會被擋下',
        ),
    )


def downgrade() -> None:
    op.drop_column('cycle_purchase_departments', 'ragic_dept')
