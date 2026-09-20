"""競品分析模組 7 張表（compset_*）

Revision ID: compset
Revises: usrdept
Create Date: 2026-09-09

背景
────────────────────────────────────────────────────────────────────────────
競品分析（Competitive Analysis）是獨立模組，資料來源是 SerpApi 的
`google_hotels` 引擎，與 Ragic、與 OPERA 匯入都無關。
規格書 `docs/SPEC_compset_analysis.md` v1.1、P0 報告 `docs/COMPSET_P0_REPORT.md`。

純新增 7 張表，不動任何既有表 —— 這種 migration 不需要 batch_alter_table。

⚠️ 為什麼一定要走 migration 而不是 `create_all()`
────────────────────────────────────────────────────────────────────────────
測試區與正式區都已是 PostgreSQL，而 **`create_all()` 補表不補欄位**，
之後任何一次欄位調整都會靜默失效，而且會讓 stamp 工具判斷錯亂
（見記憶 project_prod_update_pytag_broken）。

⚠️ 欄位為 NOT NULL 但沒有 server_default，是刻意的
────────────────────────────────────────────────────────────────────────────
預設值放在 model 的 Python 端（`mapped_column(default=...)`），
比照 `user_departments` 與 `ota_*` 既有慣例。
7 張表都是全新空表，沒有既有列要回填，所以不需要 server_default。
⚠️ 但這代表**任何繞過 ORM 的直接 INSERT 都必須自己補齊這些欄位**。

⚠️ 三個欄位設計不要「順手改掉」
────────────────────────────────────────────────────────────────────────────
1. `compset_rate_snapshots` 的唯一鍵**必須含 `snapshot_date`**。
   「9/9 看 12/24 的價」與「9/20 看 12/24 的價」是兩筆資料不是覆蓋；
   寫成覆蓋，「競品什麼時候降價」就永遠答不出來。
2. `is_sold_out` 是 **VARCHAR(10) 三態**（yes／no／unknown）不是 Boolean。
   地點查詢路徑拿不到滿房訊號，一律 unknown，不可退化成布林。
3. `price_gross` 與 `price_pretax` **兩個都要**。各家稅費結構不同
   （實測 +15.5%／+5%／+0%），只留一個口徑一定會誤導。

⚠️ 2026-09-20：upgrade() 改成「表／索引已存在就跳過」
────────────────────────────────────────────────────────────────────────────
症狀：`alembic upgrade head` 跑到這一支就爆 DuplicateTable
（`relation "compset_subscribers" already exists`），而且**整條 main 鏈從此卡死**
—— 後面的 `tcpurch`（台中請購／請款四張表）永遠跑不到。

根因不在這支 migration，而是那七張表**早就被 `create_all()` 建出來了**：
切 PG 時 `pg_cutover.py` 用 `create_all()` 建結構、且沒做 stamp
（見記憶 project_pg_never_stamped_alembic、project_pg_phase2_cutover）。
所以 DB 裡有表、`alembic_version` 卻停在 `usrdept`，Alembic 認為這支還沒跑。

為什麼不用 `alembic stamp compset` 帶過：stamp 是「相信 DB 已經長對了」，
但沒有人驗證過 `create_all()` 當時建的欄位與這支 migration 完全一致；
而且**七張表只要有一張不在**（例如被 drop_split_module_tables.sql 清掉一部分），
stamp 之後那張表就永遠不會被建出來，錯誤會延到執行期才爆。

改成逐一檢查「表在不在」後才建，兩種環境都對：
  · 舊環境（表已存在）→ 全部跳過，只推進版本號，效果等同 stamp，但有實際驗證。
  · 新環境（空庫）→ 照常建立七張表。
  · 半套環境（部分存在）→ 只補缺的那幾張。
跳過的表會印出來，跑完看得到到底發生了什麼。

⚠️ 這支 migration 建的是**已經從 Portal 拆走的 compset 模組**的表
（見記憶 split-revenue-suite，2026-09-11 程式碼已移除、46 張表刻意留著沒 drop）。
版本檔刻意不刪，因為刪掉會讓既有 DB 的 `alembic_version` 對不上 head。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "compset"
down_revision: Union[str, None] = "usrdept"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ⚠️ 命名與作法刻意比照 20260916_tcpurch（那一支從一開始就有這個防呆）。
def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _ensure_table(name: str, *cols, **kw) -> None:
    if _has_table(name):
        print(f"    [compset] 表 {name} 已存在，跳過建立")
        return
    op.create_table(name, *cols, **kw)


def _ensure_index(name: str, table: str, cols: list, **kw) -> None:
    if not _has_table(table):
        return
    existing = {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(table)}
    if name in existing:
        print(f"    [compset] 索引 {name} 已存在，跳過建立")
        return
    op.create_index(name, table, cols, **kw)


def upgrade() -> None:
    # ⚠️ 見檔頭「2026-09-20」那段：這七張表在既有環境是 create_all() 建的，
    #    直接 create_table 會 DuplicateTable 並卡死整條 main 鏈。
    # ── 1. 訂閱客戶 ────────────────────────────────────────────────────
    _ensure_table(
        "compset_subscribers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("plan_level", sa.String(1), nullable=False),
        sa.Column("window_a_days", sa.Integer(), nullable=False),
        sa.Column("window_b_days", sa.Integer(), nullable=False),
        sa.Column("window_c_days", sa.Integer(), nullable=False),
        sa.Column("freq_a_days", sa.Integer(), nullable=False),
        sa.Column("freq_b_days", sa.Integer(), nullable=False),
        sa.Column("freq_c_days", sa.Integer(), nullable=False),
        sa.Column("monthly_quota", sa.Integer(), nullable=False),
        sa.Column("quota_used", sa.Integer(), nullable=False),
        sa.Column("quota_anchor_day", sa.Integer(), nullable=False),
        sa.Column("quota_period_start", sa.String(10), nullable=False),
        sa.Column("location_query", sa.String(100), nullable=False),
        sa.Column("param_adults", sa.Integer(), nullable=False),
        sa.Column("param_nights", sa.Integer(), nullable=False),
        sa.Column("param_gl", sa.String(5), nullable=False),
        sa.Column("param_hl", sa.String(10), nullable=False),
        sa.Column("param_currency", sa.String(3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("contact_name", sa.String(50), nullable=False),
        sa.Column("contact_email", sa.String(120), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("code", name="uq_compset_subscriber_code"),
    )
    _ensure_index("ix_compset_subscriber_active", "compset_subscribers", ["is_active"])

    # ── 2. 訂閱客戶 ↔ 使用者（防提權 P-1 的依據，SPEC D14）───────────────
    _ensure_table(
        "compset_subscriber_users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subscriber_id", sa.Integer(),
                  sa.ForeignKey("compset_subscribers.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("user_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("subscriber_id", "user_id",
                            name="uq_compset_subscriber_user"),
    )
    _ensure_index("ix_compset_subuser_user", "compset_subscriber_users", ["user_id"])

    # ── 3. 競爭組成員 ──────────────────────────────────────────────────
    _ensure_table(
        "compset_hotels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subscriber_id", sa.Integer(),
                  sa.ForeignKey("compset_subscribers.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("hotel_code", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        # 簡稱（可留空，讀取端會退回 display_name）。2026-09-09 追加 ——
        # ⚠️ 這支 migration 當時**尚未在任何環境套用過**，所以直接改欄位定義
        #    而不是另開一支。若你的庫已經跑過 upgrade 才看到這行，
        #    請手動補：
        #      ALTER TABLE compset_hotels
        #        ADD COLUMN short_name VARCHAR(20) NOT NULL DEFAULT '';
        sa.Column("short_name", sa.String(20), nullable=False,
                  server_default=""),
        sa.Column("google_property_token", sa.String(200), nullable=False),
        sa.Column("google_query_name", sa.String(100), nullable=False),
        sa.Column("is_self", sa.Boolean(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("room_count", sa.Integer(), nullable=True),
        sa.Column("registered_address", sa.String(200), nullable=False),
        # 經緯度（2026-09-10 追加，供「從地圖挑競爭組」用）。可為 NULL。
        # ⚠️ 同 short_name：這支 migration 當時尚未在任何環境套用過，
        #    所以直接改欄位定義。若你的庫已經跑過 upgrade，手動補：
        #      ALTER TABLE compset_hotels ADD COLUMN latitude  NUMERIC(10,7);
        #      ALTER TABLE compset_hotels ADD COLUMN longitude NUMERIC(10,7);
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("subscriber_id", "display_name",
                            name="uq_compset_hotel_sub_name"),
    )
    _ensure_index("ix_compset_hotel_sub", "compset_hotels",
                    ["subscriber_id", "is_enabled", "sort_order"])
    _ensure_index("ix_compset_hotel_self", "compset_hotels",
                    ["subscriber_id", "is_self"])
    _ensure_index("ix_compset_hotel_code", "compset_hotels", ["hotel_code"])

    # ── 4. 價格快照（主表）─────────────────────────────────────────────
    _ensure_table(
        "compset_rate_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subscriber_id", sa.Integer(),
                  sa.ForeignKey("compset_subscribers.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("compset_hotel_id", sa.Integer(),
                  sa.ForeignKey("compset_hotels.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("snapshot_date", sa.String(10), nullable=False),
        sa.Column("stay_date", sa.String(10), nullable=False),
        sa.Column("tier", sa.String(1), nullable=False),
        sa.Column("fetch_path", sa.String(10), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("price_gross", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_pretax", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("tax_included", sa.String(10), nullable=False),
        sa.Column("ota_name", sa.String(50), nullable=False),
        sa.Column("is_official", sa.Boolean(), nullable=False),
        sa.Column("num_guests", sa.Integer(), nullable=True),
        sa.Column("free_cancellation", sa.Boolean(), nullable=False),
        sa.Column("room_type_raw", sa.String(200), nullable=False),
        sa.Column("is_sold_out", sa.String(10), nullable=False),
        sa.Column("typical_low", sa.Numeric(10, 2), nullable=True),
        sa.Column("typical_high", sa.Numeric(10, 2), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        # ⚠️ snapshot_date 必須留在唯一鍵裡，理由見檔頭
        sa.UniqueConstraint("subscriber_id", "snapshot_date", "stay_date",
                            "compset_hotel_id", "source",
                            name="uq_compset_snapshot"),
    )
    _ensure_index("ix_compset_snap_matrix", "compset_rate_snapshots",
                    ["subscriber_id", "snapshot_date", "stay_date"])
    _ensure_index("ix_compset_snap_trend", "compset_rate_snapshots",
                    ["subscriber_id", "stay_date", "snapshot_date"])
    _ensure_index("ix_compset_snap_hotel", "compset_rate_snapshots",
                    ["compset_hotel_id", "stay_date"])
    _ensure_index("ix_compset_snap_soldout", "compset_rate_snapshots",
                    ["subscriber_id", "stay_date", "is_sold_out"])

    # ── 5. 抓取批次紀錄 ────────────────────────────────────────────────
    _ensure_table(
        "compset_fetch_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subscriber_id", sa.Integer(),
                  sa.ForeignKey("compset_subscribers.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("tier", sa.String(1), nullable=False),
        sa.Column("fetch_path", sa.String(10), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("stay_date_from", sa.String(10), nullable=False),
        sa.Column("stay_date_to", sa.String(10), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("quota_before", sa.Integer(), nullable=True),
        sa.Column("quota_after", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("params_json", sa.Text(), nullable=True),
        sa.Column("warnings_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=False),
    )
    _ensure_index("ix_compset_fetchlog_sub", "compset_fetch_logs",
                    ["subscriber_id", "started_at"])
    _ensure_index("ix_compset_fetchlog_status", "compset_fetch_logs", ["status"])

    # ── 6. 配額手動加發紀錄 ────────────────────────────────────────────
    _ensure_table(
        "compset_quota_grants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subscriber_id", sa.Integer(),
                  sa.ForeignKey("compset_subscribers.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("granted_qty", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("granted_by_user_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=True),
        sa.Column("period_start", sa.String(10), nullable=False),
    )
    _ensure_index("ix_compset_grant_sub", "compset_quota_grants",
                    ["subscriber_id", "granted_at"])

    # ── 7. 每日彙總快取 ────────────────────────────────────────────────
    _ensure_table(
        "compset_rate_daily",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subscriber_id", sa.Integer(),
                  sa.ForeignKey("compset_subscribers.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("snapshot_date", sa.String(10), nullable=False),
        sa.Column("stay_date", sa.String(10), nullable=False),
        sa.Column("self_pretax", sa.Numeric(10, 2), nullable=True),
        sa.Column("median_pretax", sa.Numeric(10, 2), nullable=True),
        sa.Column("min_pretax", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_pretax", sa.Numeric(10, 2), nullable=True),
        sa.Column("index_pretax", sa.Numeric(6, 4), nullable=True),
        sa.Column("self_gross", sa.Numeric(10, 2), nullable=True),
        sa.Column("median_gross", sa.Numeric(10, 2), nullable=True),
        sa.Column("min_gross", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_gross", sa.Numeric(10, 2), nullable=True),
        sa.Column("index_gross", sa.Numeric(6, 4), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("sold_out_count", sa.Integer(), nullable=False),
        sa.Column("unknown_count", sa.Integer(), nullable=False),
        sa.Column("self_rank", sa.Integer(), nullable=True),
        sa.Column("rank_total", sa.Integer(), nullable=True),
        sa.Column("computed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("subscriber_id", "snapshot_date", "stay_date",
                            name="uq_compset_daily"),
    )
    _ensure_index("ix_compset_daily_stay", "compset_rate_daily",
                    ["subscriber_id", "stay_date", "snapshot_date"])


def downgrade() -> None:
    # 反序：先刪有 FK 指向別人的表
    op.drop_index("ix_compset_daily_stay", table_name="compset_rate_daily")
    op.drop_table("compset_rate_daily")

    op.drop_index("ix_compset_grant_sub", table_name="compset_quota_grants")
    op.drop_table("compset_quota_grants")

    op.drop_index("ix_compset_fetchlog_status", table_name="compset_fetch_logs")
    op.drop_index("ix_compset_fetchlog_sub", table_name="compset_fetch_logs")
    op.drop_table("compset_fetch_logs")

    op.drop_index("ix_compset_snap_soldout", table_name="compset_rate_snapshots")
    op.drop_index("ix_compset_snap_hotel", table_name="compset_rate_snapshots")
    op.drop_index("ix_compset_snap_trend", table_name="compset_rate_snapshots")
    op.drop_index("ix_compset_snap_matrix", table_name="compset_rate_snapshots")
    op.drop_table("compset_rate_snapshots")

    op.drop_index("ix_compset_hotel_code", table_name="compset_hotels")
    op.drop_index("ix_compset_hotel_self", table_name="compset_hotels")
    op.drop_index("ix_compset_hotel_sub", table_name="compset_hotels")
    op.drop_table("compset_hotels")

    op.drop_index("ix_compset_subuser_user", table_name="compset_subscriber_users")
    op.drop_table("compset_subscriber_users")

    op.drop_index("ix_compset_subscriber_active", table_name="compset_subscribers")
    op.drop_table("compset_subscribers")
