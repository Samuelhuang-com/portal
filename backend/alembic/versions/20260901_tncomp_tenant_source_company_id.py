"""tenants 新增 source_company_id（公司主檔鏡像對照鍵）

Revision ID: tncomp
Revises: ctvnull
Create Date: 2026-09-01

背景
────────────────────────────────────────────────────────────────────────────
使用者裁示（2026-09-01）：人員管理「新增使用者 → 所屬據點」的下拉選項，
必須等於「系統設定 → 公司/部門管理」維護的公司名稱。

作法採 CLAUDE.md §9 的鏡像樣板，**不動** `tenants.id`（UUID PK）——
`users.tenant_id`／`user_roles.tenant_id`／`ragic_connections.tenant_id`
三處外鍵都綁著它，改成對接 `companies.id`（Integer）風險過高。
只加一個 `source_company_id` 當跨主檔對照鍵。

欄位設計
────────────────────────────────────────────────────────────────────────────
  String(20)  存 `Company.id` 的字串形式，比照 cycle_purchase 兩支鏡像同步
              既有的 source_vendor_id／source_department_id 慣例。
  nullable    **必須可為 NULL** —— NULL 代表「本地自建的舊據點」，
              `tenant_company_sync.py` 對這些列不覆蓋也不刪除。
  unique      一個 Company 只能鏡像成一個 Tenant。NULL 不參與唯一性檢查
              （PG 與 SQLite 皆然），所以多筆本地自建據點不會互相衝突。

⚠️ 刻意**不建**外鍵到 `companies.id`：型別不同（String vs Integer），
   且來源端刪公司時本專案的規則是「只回報 orphans、不連帶刪」，
   有 FK 反而會擋下正常的刪除操作。

⚠️ SQLite 沿用 `batch_alter_table` + `copy_from`（理由同 20260829_widen7／
   20260829_ctvnull：SQLite 沒有 ALTER COLUMN，batch 會重建表，`copy_from`
   讓它照 model 建，避開反射舊表時可能撞上的非法 default）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "tncomp"
down_revision: Union[str, None] = "ctvnull"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _kwargs() -> dict:
    if op.get_bind().dialect.name != "sqlite":
        return {}
    from app.core.database import Base      # env.py 已把所有 model import 進來
    return {"copy_from": Base.metadata.tables["tenants"]}


def upgrade() -> None:
    with op.batch_alter_table("tenants", **_kwargs()) as batch:
        batch.add_column(sa.Column("source_company_id", sa.String(20), nullable=True))
        batch.create_unique_constraint("uq_tenants_source_company_id", ["source_company_id"])


def downgrade() -> None:
    with op.batch_alter_table("tenants", **_kwargs()) as batch:
        batch.drop_constraint("uq_tenants_source_company_id", type_="unique")
        batch.drop_column("source_company_id")
