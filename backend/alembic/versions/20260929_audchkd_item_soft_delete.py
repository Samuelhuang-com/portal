"""audit_items 加 deleted_at（軟刪除）＋ 同層名稱唯一改為只看未刪除

Revision ID: audchkd
Revises: audchkp
Create Date: 2026-09-29

背景（2026-09-29 使用者裁示）
────────────────────────────────────────────────────────────────────────────
檢查項主檔「項目名稱」開放刪除，但刪除不可影響歷史稽核單與進行中的稽核單。

audit_sheet_items.item_id 是 NOT NULL 外鍵，被引用過的主檔列不能真的刪。
→ 被引用者刪除時只標 deleted_at（連同子項），主檔畫面與勾選清單不再出現；
  稽核單各列有 item_name 快照（audchkn），評語／分數都掛在稽核單列上，完全不受影響。
→ 沒被引用者照舊真的刪除。

同層名稱唯一原本是 UNIQUE(parent_id, name)，軟刪除後會擋住「再建一個同名項目」，
改為 partial unique index：WHERE deleted_at IS NULL。
表可能由 audchk 建立（約束名 uq_audit_items_parent_name），也可能由 create_all 建立，
所以用 inspector 找出欄位恰為 (parent_id, name) 的 UNIQUE 約束／唯一索引逐一拿掉。
PostgreSQL 方言（CLAUDE.md §0）。可重跑。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "audchkd"
down_revision: Union[str, None] = "audchkp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "audit_items"
_NEW_IDX = "uq_audit_items_parent_name_live"


def _insp():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    cols = {c["name"] for c in _insp().get_columns(_TABLE)}
    if "deleted_at" not in cols:
        op.add_column(
            _TABLE,
            sa.Column("deleted_at", sa.DateTime(), nullable=True,
                      comment="軟刪除時間；被稽核單引用的項目刪除時只標記"),
        )

    target = ["parent_id", "name"]
    for uc in _insp().get_unique_constraints(_TABLE):
        if sorted(uc.get("column_names") or []) == sorted(target) and uc.get("name"):
            op.drop_constraint(uc["name"], _TABLE, type_="unique")
    for ix in _insp().get_indexes(_TABLE):
        if (ix.get("unique") and ix["name"] != _NEW_IDX
                and sorted(ix.get("column_names") or []) == sorted(target)):
            op.drop_index(ix["name"], table_name=_TABLE)

    if _NEW_IDX not in {ix["name"] for ix in _insp().get_indexes(_TABLE)}:
        op.create_index(
            _NEW_IDX, _TABLE, target, unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )


def downgrade() -> None:
    if _NEW_IDX in {ix["name"] for ix in _insp().get_indexes(_TABLE)}:
        op.drop_index(_NEW_IDX, table_name=_TABLE)
    # 若已有「軟刪除＋同名重建」的資料，加回 UNIQUE 會失敗，需先人工處理
    op.create_unique_constraint("uq_audit_items_parent_name", _TABLE, ["parent_id", "name"])
    cols = {c["name"] for c in _insp().get_columns(_TABLE)}
    if "deleted_at" in cols:
        op.drop_column(_TABLE, "deleted_at")
