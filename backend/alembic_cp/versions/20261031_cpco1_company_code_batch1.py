"""多公司隔離 第一批：週採庫公司主檔＋各分公司表加 company_code（nullable）

Revision ID: cpco1
Revises: cpccdefault
Create Date: 2026-10-31

背景（規格 docs/SPEC_cycle_purchase_multi_company.md）
────────────────────────────────────────────────────────────────────────────
週採表位於獨立的 cycle-purchase 資料庫，無法對主庫的 companies 建立外鍵，
因此在本庫建立 cycle_purchase_companies（公司主檔），以公司代碼為隔離鍵：
    CH 春大直　OU 日曜天地　HO 台中（智選）

本支（第一批）只做三件事，全部 nullable，不影響既有功能：
  1. 建 cycle_purchase_companies 並寫入三筆種子資料。
  2. 15 張分公司表加 company_code 欄位＋外鍵＋索引。
  3. 回填：
     - 既有 company 字串表：依字串對照代碼（無法對照者留 NULL，第三批會擋）。
     - 料號／成本中心／收驗／付款／廠商：依關聯推導。
     - 料號、廠商、會計科目、稽核紀錄 無法推導者：預設歸春大直（CH）。

第二批（改唯一鍵）與第三批（NOT NULL）另案。
方言：PostgreSQL（CLAUDE.md §0）。刻意不使用 op.batch_alter_table。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "cpco1"
down_revision: Union[str, None] = "cpccdefault"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEEDS = [
    ("CH", "春大直"),
    ("OU", "日曜天地"),
    ("HO", "台中"),
]

# 既有字串 → 代碼（含歷史別名；樂群=春大直、自由/日曜/日耀=日曜天地、智選=台中）
ALIAS_TO_CODE = {
    "春大直": "CH", "樂群": "CH",
    "日曜天地": "OU", "日曜": "OU", "日耀": "OU", "自由": "OU",
    "台中": "HO", "智選": "HO",
}

# 含 company 字串欄位的表（直接依字串回填）
STRING_TABLES = [
    "cycle_purchase_categories",
    "cycle_purchase_item_mappings",
    "cycle_purchase_payment_allocations",
    "cycle_purchase_pos",
    "cycle_purchase_departments",
    "cycle_purchase_requests",
    "cycle_purchase_summary",
]

# 無 company 字串欄位的表（依關聯推導或預設）
OTHER_TABLES = [
    "cycle_purchase_items",
    "cycle_purchase_cost_centers",
    "cycle_purchase_account_codes",
    "cycle_purchase_vendors",
    "cycle_purchase_receiving",
    "cycle_purchase_payments",
    "cycle_purchase_audit_logs",
]

# 推導不出來時預設歸春大直
DEFAULT_CH_TABLES = [
    "cycle_purchase_items",
    "cycle_purchase_vendors",
    "cycle_purchase_account_codes",
    "cycle_purchase_audit_logs",
]

ALL_TABLES = STRING_TABLES + OTHER_TABLES


def upgrade() -> None:
    conn = op.get_bind()
    # 2026-10-31 修正：後端啟動時 create_all 會依模型先建出 cycle_purchase_companies，
    # 此時表已存在，不能再 CREATE（會 DuplicateTable）。存在就沿用，不存在才建立。
    if not sa.inspect(conn).has_table("cycle_purchase_companies"):
        op.create_table(
            "cycle_purchase_companies",
            sa.Column("code", sa.String(10), primary_key=True, comment="公司代碼（CH／OU／HO）"),
            sa.Column("name", sa.String(100), nullable=False, unique=True, comment="公司名稱（週採慣用字串）"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        )

    for code, name in SEEDS:
        conn.execute(
            text("INSERT INTO cycle_purchase_companies (code, name, is_active, created_at) "
                 "VALUES (:c, :n, true, now()) ON CONFLICT (code) DO NOTHING"),
            {"c": code, "n": name},
        )

    for t in ALL_TABLES:
        op.add_column(t, sa.Column("company_code", sa.String(10), nullable=True))
        op.create_foreign_key(
            f"fk_{t}_company_code", t, "cycle_purchase_companies",
            ["company_code"], ["code"], ondelete="RESTRICT",
        )
        op.create_index(f"ix_{t}_company_code", t, ["company_code"])

    name_to_code = {name: code for code, name in SEEDS}

    # ── 1. 依既有 company 字串回填 ───────────────────────────────
    for t in STRING_TABLES:
        rows = conn.execute(text(f"SELECT DISTINCT company FROM {t} WHERE company IS NOT NULL")).fetchall()
        for (s,) in rows:
            code = name_to_code.get(s) or ALIAS_TO_CODE.get(s)
            if code is None:
                print(f"[cpco1] 無法對照的 company 字串：{t}.company = {s!r}（留 NULL）")
                continue
            conn.execute(
                text(f"UPDATE {t} SET company_code = :c WHERE company = :s AND company_code IS NULL"),
                {"c": code, "s": s},
            )

    # ── 2. 依關聯推導 ─────────────────────────────────────────
    conn.execute(text("""
        UPDATE cycle_purchase_items i SET company_code = m.company_code
        FROM (SELECT DISTINCT ON (item_id) item_id, company_code
              FROM cycle_purchase_item_mappings
              WHERE company_code IS NOT NULL
              ORDER BY item_id, id) m
        WHERE m.item_id = i.id AND i.company_code IS NULL
    """))
    conn.execute(text("""
        UPDATE cycle_purchase_cost_centers c SET company_code = d.company_code
        FROM cycle_purchase_departments d
        WHERE d.id = c.department_id AND c.company_code IS NULL
    """))
    conn.execute(text("""
        UPDATE cycle_purchase_vendors v SET company_code = p.company_code
        FROM (SELECT DISTINCT ON (vendor_id) vendor_id, company_code
              FROM cycle_purchase_pos
              WHERE company_code IS NOT NULL
              ORDER BY vendor_id, id DESC) p
        WHERE p.vendor_id = v.id AND v.company_code IS NULL
    """))
    conn.execute(text("""
        UPDATE cycle_purchase_receiving r SET company_code = p.company_code
        FROM cycle_purchase_pos p
        WHERE p.id = r.po_id AND r.company_code IS NULL
    """))
    conn.execute(text("""
        UPDATE cycle_purchase_payments y SET company_code = p.company_code
        FROM cycle_purchase_pos p
        WHERE p.id = y.po_id AND y.company_code IS NULL
    """))

    # ── 3. 無法推導者預設歸春大直 ───────────────────────────────
    for t in DEFAULT_CH_TABLES:
        conn.execute(
            text(f"UPDATE {t} SET company_code = 'CH' WHERE company_code IS NULL"),
        )

    # ── 4. 回報剩餘 NULL（第三批 NOT NULL 前必須為 0）──────────
    for t in ALL_TABLES:
        n = conn.execute(text(f"SELECT COUNT(*) FROM {t} WHERE company_code IS NULL")).scalar()
        print(f"[cpco1] {t}: company_code NULL = {n}")


def downgrade() -> None:
    for t in reversed(ALL_TABLES):
        op.drop_index(f"ix_{t}_company_code", table_name=t)
        op.drop_constraint(f"fk_{t}_company_code", t, type_="foreignkey")
        op.drop_column(t, "company_code")
    op.drop_table("cycle_purchase_companies")
