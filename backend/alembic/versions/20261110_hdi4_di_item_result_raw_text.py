"""飯店每日巡檢 item.result_raw 放寬為 TEXT（2026-11-10）

Revision ID: hdi4
Revises: hdi3
Create Date: 2026-11-10

背景
────────────────────────────────────────────────────────────────────────────
同步 log（2026-11-10 18:56）大量失敗：
  value too long for type character varying(50)
來源是 hotel_di_inspection_item.result_raw。2026-11-10 起「拍照」等附件欄位
改收進 item（result_raw＝檔名清單，多張照片會串成數百字），而「異常說明」等
備註也可能很長。VARCHAR(50) 無法容納。

處置：VARCHAR(50) → TEXT。附件／備註的內容沒有自然上限，不宜再猜固定長度。
PostgreSQL 方言（CLAUDE.md §0）；擴寬型別不動既有資料，可重跑。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "hdi4"
down_revision: Union[str, None] = "hdi3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE hotel_di_inspection_item ALTER COLUMN result_raw TYPE TEXT")


def downgrade() -> None:
    # ⚠️ 縮回 VARCHAR(50) 時，超過 50 字的既有值會讓 PostgreSQL 拒絕。
    #    回滾前請先處理超長資料。
    op.execute("ALTER TABLE hotel_di_inspection_item ALTER COLUMN result_raw TYPE VARCHAR(50)")
