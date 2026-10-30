"""整棟巡檢：多 Sheet 來源（sheet_key）＋預估分鐘

Revision ID: inskey1
Revises: fbmpc1
Create Date: 2026-10-30

2026-10-30 Samuel 裁示：整棟巡檢 RF／B1F／B2F／B4F 各樓層改為多 Sheet 來源。
- 每個場次 ragic_id 改為 "{sheet_key}_{Ragic Row ID}"（與 sync_tool 既有複合鍵慣例一致）。
- 新增 sheet_key 欄位（batch、item 皆有，item 為冗餘欄位）。
- 新增 batch.estimated_minutes（Ragic「預估時間」＝預排分鐘數，不是設備項目）。
- 既有資料回填為舊 Sheet 的封存來源：
    rf   → rf_1  （archive-old-data/19）
    b1f  → b1f_4 （archive-old-data/22）
    b2f  → b2f_3 （archive-old-data/21）
    b4f  → b4f_2 （archive-old-data/20）
  例：b4f 舊場次 ragic_id '8' → 'b4f_2_8'；其設備項目 '8_1' → 'b4f_2_8_1'。
- 主鍵結構不變（仍為單欄 ragic_id），因此既有外鍵式關聯（item.batch_ragic_id）同步改寫。

PG 方言（CLAUDE.md §0）；IF NOT EXISTS、回填條件 sheet_key = ''，可重跑。

⚠️ downgrade 只在「尚未新增任何非封存來源」時安全；否則會把不同 Sheet 的相同 Row ID 還原成衝突值。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "inskey1"
down_revision: Union[str, None] = "fbmpc1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (floor 表名前綴, 舊 Sheet 的 sheet_key)
_FLOORS = [
    ("rf",  "rf_1"),
    ("b1f", "b1f_4"),
    ("b2f", "b2f_3"),
    ("b4f", "b4f_2"),
]


def upgrade() -> None:
    for prefix, legacy in _FLOORS:
        bt = f"{prefix}_inspection_batch"
        it = f"{prefix}_inspection_item"

        op.execute(f"ALTER TABLE {bt} ADD COLUMN IF NOT EXISTS sheet_key VARCHAR(40) NOT NULL DEFAULT ''")
        op.execute(f"ALTER TABLE {bt} ADD COLUMN IF NOT EXISTS estimated_minutes INTEGER")
        op.execute(f"ALTER TABLE {it} ADD COLUMN IF NOT EXISTS sheet_key VARCHAR(40) NOT NULL DEFAULT ''")

        # 先改場次（batch），再改設備項目（item）；item 的 batch_ragic_id 仍是舊值，所以順序不能反
        op.execute(
            f"UPDATE {bt} SET ragic_id = '{legacy}_' || ragic_id, sheet_key = '{legacy}' "
            f"WHERE sheet_key = ''"
        )
        op.execute(
            f"UPDATE {it} SET batch_ragic_id = '{legacy}_' || batch_ragic_id, "
            f"ragic_id = '{legacy}_' || ragic_id, sheet_key = '{legacy}' "
            f"WHERE sheet_key = ''"
        )
        # 既有非設備項目（附件／附註／系統欄位）去除異常旗標：與 inspection_field_rules 的名稱規則一致。
        # 先前同步把「拍照」檔名、「異常說明」文字等當成異常，會讓儀表板異常數虛增。
        op.execute(
            f"UPDATE {it} SET result_status = 'meta', abnormal_flag = FALSE "
            f"WHERE item_name ~ '^(拍照|照片|相片|圖片|圖檔|附件|附圖|上傳圖片)\\s*[0-9]*$' "
            f"   OR item_name ~ '^(異常說明|備註|說明|建立日期|建立年份|建立時間|年份|月份)\\s*[0-9]*$' "
            f"   OR result_raw ~* '\\.(jpe?g|png|gif|bmp|webp|heic|heif|pdf)\\s*$'"
        )
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{prefix}_batch_sheet_key ON {bt} (sheet_key)")
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{prefix}_item_sheet_key ON {it} (sheet_key)")


def downgrade() -> None:
    for prefix, _legacy in _FLOORS:
        bt = f"{prefix}_inspection_batch"
        it = f"{prefix}_inspection_item"

        # 還原 Ragic 原始 ID：去掉 "{sheet_key}_" 前綴
        op.execute(
            f"UPDATE {it} SET batch_ragic_id = SUBSTRING(batch_ragic_id FROM LENGTH(sheet_key) + 2), "
            f"ragic_id = SUBSTRING(ragic_id FROM LENGTH(sheet_key) + 2) "
            f"WHERE sheet_key <> ''"
        )
        op.execute(
            f"UPDATE {bt} SET ragic_id = SUBSTRING(ragic_id FROM LENGTH(sheet_key) + 2) "
            f"WHERE sheet_key <> ''"
        )
        op.execute(f"DROP INDEX IF EXISTS ix_{prefix}_item_sheet_key")
        op.execute(f"DROP INDEX IF EXISTS ix_{prefix}_batch_sheet_key")
        op.execute(f"ALTER TABLE {it} DROP COLUMN IF EXISTS sheet_key")
        op.execute(f"ALTER TABLE {bt} DROP COLUMN IF EXISTS estimated_minutes")
        op.execute(f"ALTER TABLE {bt} DROP COLUMN IF EXISTS sheet_key")
