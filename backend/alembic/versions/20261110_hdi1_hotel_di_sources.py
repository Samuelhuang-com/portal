"""飯店每日巡檢：新 Ragic 表（17、28～33）＋封存來源、預估分鐘、場次 ID 加來源前綴

Revision ID: hdi1
Revises: widen_approved_unit1
Create Date: 2026-11-10

2026-11-10 Samuel 裁示：飯店每日巡檢改接新 Ragic 表，新舊連結同時存在，舊資料掛在最接近的新頁籤。
- 新增 hotel_di_inspection_batch.estimated_minutes（Ragic「預估時間」）。
- 既有場次 ID "{舊頁籤}_{Row ID}" 改為 "{來源}_{Row ID}"，並改到新頁籤：
    rf      → rf_legacy     （頁籤 rf；Ragic 封存區找不到舊 RF，Portal 是唯一一份，不同步）
    4f-10f  → 5f-10f_a31    （頁籤 5f-10f；archive-old-data/31）
    4f      → 4f_a32        （頁籤 4f；archive-old-data/32）
    2f      → 4f_a33        （頁籤 4f；archive-old-data/33）
    1f      → 4f_a34        （頁籤 4f；archive-old-data/34）
  ⚠️ 必須在新 RF 表（main-project-inspection/17，Row ID 從 0 起算）第一次同步前執行，
     否則新紀錄 rf_17_N 雖不會撞號，但舊 rf_N 會無法歸屬來源；同步程式偵測到舊格式會拒絕同步。

PG 方言；只改寫符合舊格式的列（^舊頁籤_數字$），可重跑。
⚠️ downgrade 只移除 estimated_minutes；場次 ID 不還原。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "hdi1"
down_revision: Union[str, None] = "widen_approved_unit1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (舊頁籤, 新頁籤, 新來源 key, 新頁籤顯示名稱)
_LEGACY = [
    ("rf",     "rf",     "rf_legacy",  "飯店每日巡檢 - RF 樓層 早班巡檢"),
    ("4f-10f", "5f-10f", "5f-10f_a31", "飯店每日巡檢 - 5-10F 客房公共區域"),
    ("4f",     "4f",     "4f_a32",     "飯店每日巡檢 - 4F BAR-D公區"),
    ("2f",     "4f",     "4f_a33",     "飯店每日巡檢 - 4F BAR-D公區"),
    ("1f",     "4f",     "4f_a34",     "飯店每日巡檢 - 4F BAR-D公區"),
]

T_BATCH = "hotel_di_inspection_batch"
T_ITEM = "hotel_di_inspection_item"


def upgrade() -> None:
    op.execute(f"ALTER TABLE {T_BATCH} ADD COLUMN IF NOT EXISTS estimated_minutes INTEGER")

    for old_tab, new_tab, src_key, sheet_name in _LEGACY:
        pat = f"^{old_tab}_[0-9]+$"
        cut = len(old_tab) + 2          # substring 起點：跳過 '{old_tab}_'
        # 場次：'{old_tab}_{row}' → '{src_key}_{row}'，頁籤與名稱一併改
        op.execute(
            f"UPDATE {T_BATCH} SET ragic_id = '{src_key}_' || substring(ragic_id from {cut}), "
            f"    sheet_key = '{new_tab}', sheet_name = '{sheet_name}' "
            f"WHERE sheet_key = '{old_tab}' AND ragic_id ~ '{pat}'"
        )
        # 項目：batch_ragic_id 與 ragic_id 同步改寫（同一句 UPDATE 取舊值判斷）
        op.execute(
            f"UPDATE {T_ITEM} "
            f"SET batch_ragic_id = '{src_key}_' || substring(batch_ragic_id from {cut}), "
            f"    ragic_id = '{src_key}_' || substring(ragic_id from {cut}), "
            f"    sheet_key = '{new_tab}' "
            f"WHERE sheet_key = '{old_tab}' AND batch_ragic_id ~ '{pat}'"
        )

    # 非設備欄位（建立日期／建立年份／月份）改為 note，不算異常（同商場 mallfi1）
    op.execute(
        f"UPDATE {T_ITEM} SET result_status = 'note', abnormal_flag = FALSE "
        f"WHERE is_note = FALSE "
        f"  AND (item_name ~ '^(建立日期|建立年份|建立時間|年份|月份)\\s*[0-9]*$')"
    )


def downgrade() -> None:
    op.execute(f"ALTER TABLE {T_BATCH} DROP COLUMN IF EXISTS estimated_minutes")
