"""整棟工務每日巡檢 B1~B4（新樓層）：建立獨立的場次與設備項目表

Revision ID: b1b4t1
Revises: inskey1
Create Date: 2026-10-30

2026-10-30 Samuel 裁示：B1~B4 為獨立樓層，不併入既有樓層 TAB。
結構與 b1f_inspection_* 相同，並含 sheet_key 與 estimated_minutes。
來源 Sheet：Ragic full-building-inspection/8（抽排風設備）。

PG 方言（CLAUDE.md §0）；IF NOT EXISTS，可重跑。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b1b4t1"
down_revision: Union[str, None] = "inskey1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS b1b4_inspection_batch (
            ragic_id          VARCHAR(50)  PRIMARY KEY,
            sheet_key         VARCHAR(40)  NOT NULL DEFAULT '',
            inspection_date   VARCHAR(20)  NOT NULL DEFAULT '',
            inspector_name    VARCHAR(100) NOT NULL DEFAULT '',
            start_time        VARCHAR(30)  NOT NULL DEFAULT '',
            end_time          VARCHAR(30)  NOT NULL DEFAULT '',
            work_hours        VARCHAR(20)  NOT NULL DEFAULT '',
            estimated_minutes INTEGER,
            synced_at         TIMESTAMP    NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS b1b4_inspection_item (
            ragic_id       VARCHAR(80)  PRIMARY KEY,
            sheet_key      VARCHAR(40)  NOT NULL DEFAULT '',
            batch_ragic_id VARCHAR(50)  NOT NULL DEFAULT '',
            seq_no         INTEGER      NOT NULL DEFAULT 0,
            item_name      VARCHAR(200) NOT NULL DEFAULT '',
            result_raw     TEXT         NOT NULL DEFAULT '',
            result_status  VARCHAR(20)  NOT NULL DEFAULT 'unchecked',
            abnormal_flag  BOOLEAN      NOT NULL DEFAULT FALSE,
            synced_at      TIMESTAMP    NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_b1b4_batch_date ON b1b4_inspection_batch (inspection_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_b1b4_batch_sheet_key ON b1b4_inspection_batch (sheet_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_b1b4_item_batch ON b1b4_inspection_item (batch_ragic_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_b1b4_item_abnormal ON b1b4_inspection_item (abnormal_flag)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_b1b4_item_sheet_key ON b1b4_inspection_item (sheet_key)")


def downgrade() -> None:
    # 新表：downgrade 會連同資料一起刪除（僅限尚未正式使用前執行）
    op.execute("DROP TABLE IF EXISTS b1b4_inspection_item")
    op.execute("DROP TABLE IF EXISTS b1b4_inspection_batch")
