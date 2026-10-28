"""
create_indexes.py
一次性建立所有效能 Index（使用 IF NOT EXISTS，可重複執行不報錯）

⚠️⚠️ 2026-08-29 改為**方言中立**（PostgreSQL 遷移）
────────────────────────────────────────────────────────────────────────────
原本用裸的 `sqlite3.connect()` 並從 `DATABASE_URL` 剝掉 `sqlite:///` 取檔案路徑。
切到 PostgreSQL 之後那個 replace 什麼也沒剝掉，`Path(...).exists()` 為 False
→ `[ERROR] 找不到資料庫檔案` → `SystemExit(1)`。

⚠️ 而 `prod-update.bat` 的 [4/6] 只檢查 `errorlevel 1` 並印一行 `[WARN]`
   **然後繼續往下跑** —— 也就是說索引會**靜默地沒有建立**，
   沒有人會發現，直到某天查詢變慢。

改用 SQLAlchemy engine：
    · `CREATE INDEX IF NOT EXISTS` 兩個引擎都支援，SQL 不必改
    · 索引是否存在改用 `inspect(engine)`，不再查 `sqlite_master`
    · 欄位補丁只在 SQLite 執行（PostgreSQL 的 schema 由 Alembic 管）

執行方式：
  cd backend
  python create_indexes.py
"""
from sqlalchemy import inspect, text

from app.core.database import engine

DIALECT = engine.dialect.name
print(f"[INFO] 連線資料庫：{engine.url}（dialect={DIALECT}）")

# ── Index 定義清單 ─────────────────────────────────────────────────────────────
INDEXES = [
    # B1F 巡檢
    ("ix_b1f_batch_date",         "b1f_inspection_batch", "inspection_date"),
    ("ix_b1f_item_batch",         "b1f_inspection_item",  "batch_ragic_id"),
    ("ix_b1f_item_abnormal",      "b1f_inspection_item",  "abnormal_flag"),
    # B2F 巡檢
    ("ix_b2f_batch_date",         "b2f_inspection_batch", "inspection_date"),
    ("ix_b2f_item_batch",         "b2f_inspection_item",  "batch_ragic_id"),
    ("ix_b2f_item_abnormal",      "b2f_inspection_item",  "abnormal_flag"),
    # RF 巡檢
    ("ix_rf_batch_date",          "rf_inspection_batch",  "inspection_date"),
    ("ix_rf_item_batch",          "rf_inspection_item",   "batch_ragic_id"),
    ("ix_rf_item_abnormal",       "rf_inspection_item",   "abnormal_flag"),
    # B4F 巡檢
    ("ix_b4f_batch_date",         "b4f_inspection_batch", "inspection_date"),
    ("ix_b4f_item_batch",         "b4f_inspection_item",  "batch_ragic_id"),
    ("ix_b4f_item_abnormal",      "b4f_inspection_item",  "abnormal_flag"),
    # 飯店週期保養
    ("ix_pm_batch_month",         "pm_batch",             "period_month"),
    ("ix_pm_item_batch",          "pm_batch_item",        "batch_ragic_id"),
    ("ix_pm_item_completed",      "pm_batch_item",        "is_completed"),
    ("ix_pm_item_abnormal",       "pm_batch_item",        "abnormal_flag"),
    # 商場週期保養
    ("ix_mall_pm_batch_month",    "mall_pm_batch",        "period_month"),
    ("ix_mall_pm_item_batch",     "mall_pm_batch_item",   "batch_ragic_id"),
    ("ix_mall_pm_item_completed", "mall_pm_batch_item",   "is_completed"),
    ("ix_mall_pm_item_abnormal",  "mall_pm_batch_item",   "abnormal_flag"),
]

# ── Column Migrations（可重複執行，欄位已存在時靜默跳過）────────────────────────
COLUMN_MIGRATIONS = [
    # (table, column, type, default)
    ("ragic_connections", "module_key", "TEXT", None),
]

# ── 執行 ──────────────────────────────────────────────────────────────────────
insp = inspect(engine)
have_tables = set(insp.get_table_names())

# ⚠️ 欄位補丁只在 SQLite 跑。PostgreSQL 的 schema 一律走 Alembic
#    （`alembic upgrade head`），不該再有手寫的 ALTER TABLE。
if DIALECT == "sqlite":
    print("[Migration] 檢查欄位 migration...")
    with engine.begin() as conn:
        for table, column, col_type, default in COLUMN_MIGRATIONS:
            if table not in have_tables:
                print(f"  [SKIP] {table}.{column} — 資料表不存在")
                continue
            existing_cols = {c["name"] for c in insp.get_columns(table)}
            if column not in existing_cols:
                default_clause = f" DEFAULT {default}" if default is not None else ""
                conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}"))
                print(f"  [ADD]  {table}.{column} ({col_type})")
            else:
                print(f"  [OK]   {table}.{column} 已存在，跳過")
else:
    print(f"[Migration] dialect={DIALECT}：欄位補丁交由 Alembic 處理，跳過")
print()

ok = skip = err = 0

for idx_name, table, column in INDEXES:
    if table not in have_tables:
        print(f"  [SKIP] {idx_name}  — 資料表 {table} 不存在，跳過")
        skip += 1
        continue
    # ⚠️ `CREATE INDEX IF NOT EXISTS` 兩個引擎都支援，這行 SQL 不需要分方言
    sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({column})"
    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
        # 用 inspect 確認，不查 sqlite_master（那是 SQLite 專屬）
        names = {i["name"] for i in inspect(engine).get_indexes(table)}
        if idx_name in names:
            print(f"  [OK]   {idx_name}  ({table}.{column})")
            ok += 1
        else:
            print(f"  [WARN] {idx_name}  — 建立後仍查不到，請人工確認")
            err += 1
    except Exception as e:
        print(f"  [ERR]  {idx_name}  → {type(e).__name__}: {str(e).splitlines()[0][:90]}")
        err += 1

print(f"\n完成：建立/確認 {ok} 個 index，跳過 {skip} 個，錯誤 {err} 個")
if err:
    raise SystemExit(1)
