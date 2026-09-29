"""audit_periods.period 拿掉 UNIQUE —— 期別不設限，同月可多期

Revision ID: audchkp
Revises: audchkn
Create Date: 2026-09-29

背景（2026-09-29 使用者裁示）
────────────────────────────────────────────────────────────────────────────
稽核檢查不限制「期別」，期別可以無限新增，不再檢查期別。
→ 同一個月份（YYYY-MM）可以建立多期；API 的「該期別已存在」檢查一併移除。

表可能由 audchk 建立（約束名 uq_audit_periods_period），也可能由 create_all
建立（PG 自動命名 audit_periods_period_key），所以用 inspector 找出「只含 period
一欄」的 UNIQUE 約束／唯一索引逐一拿掉，不寫死名稱。可重跑。

downgrade 會把 UNIQUE 加回去；若屆時已有同月多期資料會失敗，需先人工合併。
PostgreSQL 方言（CLAUDE.md §0）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "audchkp"
down_revision: Union[str, None] = "audchkn"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "audit_periods"
_IDX = "ix_audit_periods_period"


def _insp():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    insp = _insp()
    for uc in insp.get_unique_constraints(_TABLE):
        if list(uc.get("column_names") or []) == ["period"] and uc.get("name"):
            op.drop_constraint(uc["name"], _TABLE, type_="unique")
    insp = _insp()
    for ix in insp.get_indexes(_TABLE):
        if ix.get("unique") and list(ix.get("column_names") or []) == ["period"]:
            op.drop_index(ix["name"], table_name=_TABLE)
    # 改成一般索引（年度統計用 LIKE 'YYYY-%' 篩選）
    insp = _insp()
    if _IDX not in {ix["name"] for ix in insp.get_indexes(_TABLE)}:
        op.create_index(_IDX, _TABLE, ["period"], unique=False)


def downgrade() -> None:
    insp = _insp()
    if _IDX in {ix["name"] for ix in insp.get_indexes(_TABLE)}:
        op.drop_index(_IDX, table_name=_TABLE)
    names = {uc.get("name") for uc in _insp().get_unique_constraints(_TABLE)}
    if "uq_audit_periods_period" not in names:
        op.create_unique_constraint("uq_audit_periods_period", _TABLE, ["period"])
