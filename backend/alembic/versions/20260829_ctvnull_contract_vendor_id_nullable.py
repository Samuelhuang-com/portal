"""contracts.vendor_id 改為可為 NULL

Revision ID: ctvnull
Revises: widen7
Create Date: 2026-08-29

背景
────────────────────────────────────────────────────────────────────────────
「這張合約沒有連到廠商主檔」**是合法的業務狀態** —— 早期用 Excel 匯入的合約
只有 `vendor_name` 文字，沒有對應的廠商編號（使用者確認：本來就沒連結）。

原本宣告 `nullable=False, default=""`，於是「沒填」被存成**空字串**：

| | SQLite | PostgreSQL |
|---|---|---|
| `vendor_id = ''` | 照收（沒開 `PRAGMA foreign_keys`） | **拒收** `violates foreign key constraint` |
| `vendor_id IS NULL` | 照收 | **照收** —— NULL 不參與外鍵檢查 |

⚠️ `''` 等於宣稱「連到一個 `vendor_id = ''` 的廠商」，而那個廠商不存在。
   **外鍵欄位的「沒有值」就該是 NULL。**

改完之後這張表的外鍵孤兒歸零，**外鍵約束可以保留** ——
不必再用 `pg_migrate_pilot.py --allow-orphans`。

⚠️ **順序**：先跑這支 migration 放寬欄位，**才能**跑
   `scripts/fix_contract_vendor_id.py` 把 `''` 寫成 NULL。
   反過來會因為 NOT NULL 而失敗（那支腳本有檢查並會擋下來）。

⚠️ SQLite 上仍用 `batch_alter_table` + `copy_from`：SQLite 沒有 ALTER COLUMN，
   batch 會重建表；`copy_from` 讓它照 model 建，避開反射舊表時可能撞上的
   非法 default（見 `20260829_widen7` 的說明）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ctvnull"
down_revision: Union[str, None] = "widen7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _kwargs() -> dict:
    if op.get_bind().dialect.name != "sqlite":
        return {}
    from app.core.database import Base      # env.py 已把所有 model import 進來
    return {"copy_from": Base.metadata.tables["contracts"]}


def upgrade() -> None:
    with op.batch_alter_table("contracts", **_kwargs()) as batch:
        batch.alter_column("vendor_id", existing_type=sa.String(50), nullable=True)


def downgrade() -> None:
    # ⚠️ 回滾前必須先把 NULL 補回成 ''，否則 NOT NULL 會失敗。
    #    這裡刻意**不自動代填** —— 那些 NULL 是「真的沒有廠商」，
    #    自動填 '' 等於把剛修好的錯誤再放回去。要回滾請自行決定怎麼處理。
    with op.batch_alter_table("contracts", **_kwargs()) as batch:
        batch.alter_column("vendor_id", existing_type=sa.String(50), nullable=False)
