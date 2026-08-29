"""放寬 7 個欄位長度（PostgreSQL 遷移前置）

Revision ID: widen7
Revises: baseline_main
Create Date: 2026-08-29

背景
────────────────────────────────────────────────────────────────────────────
`VARCHAR(n)` 的長度限制**只有 PostgreSQL 會執行、SQLite 完全忽略**，
所以這些欄位在 SQLite 存得下超長的值，搬到 PG 會中途失敗
（`value too long for type character varying(n)`）。

由 `scripts/pg_migrate_pilot.py --all --dry-run` 的前置檢查抓出，
再用 `scripts/pg_show_overlong.py` 逐一看過實際內容才決定怎麼處理。

| 欄位 | 宣告 | 實測最長 | 實際內容 | 處置 |
|------|------|---------|---------|------|
| `b1f/b2f/b4f/rf_inspection_item.result_raw` | VARCHAR(50) | 239 | `檔案ID@圖檔名.jpg` 多張串接 | → Text |
| `dazhi_repair_case.accept_status` | VARCHAR(200) | 446 | 驗收人員寫的長篇說明 | → Text |
| `luqun_repair_case.deduction_counter_name` | VARCHAR(200) | 201 | 數十個櫃位名稱串接 | → Text |
| `nichiyo_claim_request_items.unit` | VARCHAR(20) | 25 | `年繳(2026/02/16-2027/02/15)` | → VARCHAR(50) |

⚠️ 前四個與 `accept_status`、`deduction_counter_name` 改 **Text 而不是更長的
   VARCHAR**：它們的長度**沒有自然上限**（附幾張圖、有幾個櫃位、寫多長的說明
   都由使用者決定），訂任何數字都只是把同一個問題往後延。
   `unit` 有自然上限（就是一段期間描述），所以維持 VARCHAR 只放寬到 50。

⚠️ **`approved_purchase_requests.applicant` 刻意不在此列。**
   它的超長值是 `data:image/png;base64,...`（Ragic 的申請人是圖檔欄位），
   屬於**資料被污染**而不是宣告太緊 —— 放寬只會讓錯誤永久合法化。
   處置見 `scripts/fix_applicant_data_uri.py` 與
   `purchase_request_sync._person_name()`，欄位維持 `VARCHAR(50)`。

⚠️⚠️ **這支 migration 在 SQLite 上是 no-op，只在 PostgreSQL 上真的執行。**
────────────────────────────────────────────────────────────────────────────
兩個理由，第二個是實測踩出來的：

**① SQLite 根本不執行 `VARCHAR(n)`。** 在 SQLite 上把宣告從 `VARCHAR(50)`
   改成 `TEXT`，行為完全不變 —— 它本來就存得下 239 個字。
   換句話說，在 SQLite 上做這件事的收益是 **0**。

**② 在 SQLite 上做這件事的代價卻很高。** SQLite 沒有 `ALTER COLUMN`，
   Alembic 的 batch 模式得「建新表 → 複製資料 → 刪原表 → 改名」。
   而 **pysqlite driver 不會在 DDL 前開交易**，所以中途失敗**不會回滾**：

     · 2026-08-29 第一次嘗試：`dazhi_repair_case.record_status` 在 DB 裡是
       `VARCHAR(50) DEFAULT ("")`（舊版 SQLite 加的，新版已不接受這種寫法），
       反射重建時直接失敗 —— 那張表現在的 DDL，用現在的 SQLite 建不出來。
     · 改用 `copy_from=`（照 model 建表、繞過反射）後，換成撞上第一次失敗
       留在資料庫裡的 `_alembic_tmp_b1f_inspection_item`。

   也就是說：為了一個收益為 0 的變更，讓 7 張有資料的表反覆 drop／recreate，
   而且失敗時沒有回滾。**風險與收益完全不成比例。**

   殘骸清理見 `scripts/check_alembic_tmp_leftover.py`。

**代價（誠實記著）**：SQLite 的實際 schema 會停在 `VARCHAR(50)`，與 model 的
`Text` 不一致。影響僅止於 `alembic revision --autogenerate` 會再偵測到同一組
差異；`check_schema_drift.py` 把 VARCHAR 與 TEXT 視為同族，不會報。
反正遷移的終點是 PostgreSQL，SQLite 的宣告不再有意義。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "widen7"
down_revision: Union[str, None] = "baseline_main"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (資料表, 欄位, 舊型別, 新型別, nullable)
CHANGES = [
    ("b1f_inspection_item", "result_raw", sa.String(50), sa.Text(), False),
    ("b2f_inspection_item", "result_raw", sa.String(50), sa.Text(), False),
    ("b4f_inspection_item", "result_raw", sa.String(50), sa.Text(), False),
    ("rf_inspection_item", "result_raw", sa.String(50), sa.Text(), False),
    ("dazhi_repair_case", "accept_status", sa.String(200), sa.Text(), False),
    ("luqun_repair_case", "deduction_counter_name", sa.String(200), sa.Text(), False),
    ("nichiyo_claim_request_items", "unit", sa.String(20), sa.String(50), True),
]


def _apply(changes) -> None:
    """只在 PostgreSQL 上執行；SQLite 直接跳過（理由見檔頭）。"""
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        print("    [widen7] SQLite 不執行 VARCHAR 長度限制，本 migration 跳過"
              "（只在 PostgreSQL 上有意義）")
        return
    for table, col, from_t, to_t, nullable in changes:
        # PostgreSQL 是原生 ALTER COLUMN TYPE，不重建表、不搬資料
        op.alter_column(table, col, existing_type=from_t, type_=to_t,
                        existing_nullable=nullable)


def upgrade() -> None:
    _apply([(t, c, old, new, n) for t, c, old, new, n in CHANGES])


def downgrade() -> None:
    # ⚠️ 回滾會讓 PostgreSQL 直接拒絕（那些列本來就超過舊長度），
    #    這是縮短欄位的必然後果 —— 真的要回滾請先把超長的值處理掉。
    _apply([(t, c, new, old, n) for t, c, old, new, n in reversed(CHANGES)])
