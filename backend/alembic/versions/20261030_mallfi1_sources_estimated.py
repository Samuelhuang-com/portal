"""商場工務巡檢：多來源（現行＋封存）、預估分鐘、場次 ID 加來源前綴

Revision ID: mallfi1
Revises: fmapins2
Create Date: 2026-10-30

2026-10-30 Samuel 裁示：商場工務巡檢頁籤依新 Ragic Sheet 調整（1-4F／4F／3F／1F~3F／1F／B1F~B4F）。
- 新增 mall_fi_inspection_batch.estimated_minutes（Ragic「預估時間」）。
- 既有場次 ID 由 "{頁籤}_{Row ID}" 改為 "{來源}_{Row ID}"，來源為舊 Sheet 的封存來源：
    4f → 4f_2、3f → 3f_3、1f-3f → 1f-3f_4、1f → 1f_5、b1f-b4f → b1f-b4f_7
  例：4f 舊場次 '4f_10' → '4f_2_10'；其設備項目 '4f_10_1' → '4f_2_10_1'。
- 既有非設備欄位（建立日期／建立年份／月份）去除異常旗標（同整棟巡檢的修正）。

PG 方言；只改寫符合舊格式的列（^頁籤_數字$），可重跑。
⚠️ downgrade 只移除 estimated_minutes；場次 ID 不還原（不影響資料完整性）。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "mallfi1"
down_revision: Union[str, None] = "fmapins2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (頁籤, 舊 Sheet 編號)：舊 Sheet 已封存為 archive-old-data，來源 key = {頁籤}_{舊編號}
_LEGACY = [
    ("4f", "2"),
    ("3f", "3"),
    ("1f-3f", "4"),
    ("1f", "5"),
    ("b1f-b4f", "7"),
]

T_BATCH = "mall_fi_inspection_batch"
T_ITEM = "mall_fi_inspection_item"


def upgrade() -> None:
    op.execute(f"ALTER TABLE {T_BATCH} ADD COLUMN IF NOT EXISTS estimated_minutes INTEGER")

    for tab, old in _LEGACY:
        new_prefix = f"{tab}_{old}_"
        pat = f"^{tab}_[0-9]+$"
        # 場次：'{tab}_{row}' → '{tab}_{old}_{row}'
        op.execute(
            f"UPDATE {T_BATCH} SET ragic_id = '{new_prefix}' || substring(ragic_id from length('{tab}') + 2) "
            f"WHERE sheet_key = '{tab}' AND ragic_id ~ '{pat}'"
        )
        # 設備項目：batch_ragic_id 與 ragic_id 同步改寫（以舊的 batch_ragic_id 判斷，同一句 UPDATE 取舊值）
        op.execute(
            f"UPDATE {T_ITEM} "
            f"SET batch_ragic_id = '{new_prefix}' || substring(batch_ragic_id from length('{tab}') + 2), "
            f"    ragic_id = '{new_prefix}' || substring(ragic_id from length('{tab}') + 2) "
            f"WHERE sheet_key = '{tab}' AND batch_ragic_id ~ '{pat}'"
        )

    # 非設備欄位（建立日期／建立年份／月份）改為 note（與 item_status 一致），不算異常
    op.execute(
        f"UPDATE {T_ITEM} SET result_status = 'note', abnormal_flag = FALSE "
        f"WHERE is_note = FALSE "
        f"  AND (item_name ~ '^(建立日期|建立年份|建立時間|年份|月份)\\s*[0-9]*$')"
    )


def downgrade() -> None:
    op.execute(f"ALTER TABLE {T_BATCH} DROP COLUMN IF EXISTS estimated_minutes")
