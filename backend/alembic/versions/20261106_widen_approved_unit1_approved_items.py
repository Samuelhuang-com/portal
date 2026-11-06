"""放寬採購／請款已核准品項的 unit 欄位長度（2026-11-06）

Revision ID: widen_approved_unit1
Revises: fmapcc1
Create Date: 2026-11-06

背景
────────────────────────────────────────────────────────────────────────────
正式區同步 log（2026-11-06）出現反覆失敗：
  value too long for type character varying(20)
來源是 Ragic 採購／請款表單的品項欄位，實際寫入的值為規格字串，例如
`Surface Pro 7/i5-1035G4/8G/256GB/W11`（36 字），超過 VARCHAR(20)。

影響的兩張表（同步寫入失敗，整筆單據無法入庫）：
  · approved_purchase_request_items.unit
  · approved_claim_request_items.unit

處置：VARCHAR(20) → VARCHAR(100)。
  - 這是止血，不是根治：`unit` 內容是否應該是規格字串，需另外確認 Ragic 欄位對應。
  - 不改成 TEXT：與 widen7 的判斷一致，`unit` 有自然上限，仍維持 VARCHAR。
  - 100 字為保守上限，留足 Ragic 規格字串的成長空間。

PostgreSQL 方言（CLAUDE.md §0）；擴寬型別不會動到既有資料，可重跑。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "widen_approved_unit1"
down_revision: Union[str, None] = "fmapcc1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE approved_purchase_request_items ALTER COLUMN unit TYPE VARCHAR(100)")
    op.execute("ALTER TABLE approved_claim_request_items ALTER COLUMN unit TYPE VARCHAR(100)")


def downgrade() -> None:
    # ⚠️ 縮回 VARCHAR(20) 時，PostgreSQL 會拒絕超過 20 字的既有值。
    #    回滾前請先確認／處理超長的 unit 資料，否則會直接失敗。
    op.execute("ALTER TABLE approved_purchase_request_items ALTER COLUMN unit TYPE VARCHAR(20)")
    op.execute("ALTER TABLE approved_claim_request_items ALTER COLUMN unit TYPE VARCHAR(20)")
