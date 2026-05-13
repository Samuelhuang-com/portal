"""
create_indexes.py
一次性建立所有效能 Index（使用 IF NOT EXISTS，可重複執行不報錯）

執行方式：
  cd backend
  python create_indexes.py
"""
import sqlite3
from pathlib import Path
from app.core.config import settings

# ── 解析 DB 路徑 ──────────────────────────────────────────────────────────────
db_url = settings.DATABASE_URL  # e.g. sqlite:///C:/portal_data/portal.db
db_path = db_url.replace("sqlite:///", "")
print(f"[INFO] 連線資料庫：{db_path}")

if not Path(db_path).exists():
    print(f"[ERROR] 找不到資料庫檔案：{db_path}")
    raise SystemExit(1)

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
conn = sqlite3.connect(db_path)
cur  = conn.cursor()

print("[Migration] 檢查欄位 migration...")
for table, column, col_type, default in COLUMN_MIGRATIONS:
    cur.execute(f"PRAGMA table_info({table})")
    existing_cols = [row[1] for row in cur.fetchall()]
    if column not in existing_cols:
        default_clause = f" DEFAULT {default}" if default is not None else ""
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}")
        print(f"  [ADD]  {table}.{column} ({col_type})")
    else:
        print(f"  [OK]   {table}.{column} 已存在，跳過")
conn.commit()
print()

ok = skip = err = 0

for idx_name, table, column in INDEXES:
    sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({column});"
    try:
        cur.execute(sql)
        # 確認是否已存在
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (idx_name,))
        existed = cur.fetchone()
        if existed:
            print(f"  [OK]   {idx_name}  ({table}.{column})")
            ok += 1
        else:
            print(f"  [SKIP] {idx_name}  — 資料表不存在，跳過")
            skip += 1
    except sqlite3.OperationalError as e:
        print(f"  [ERR]  {idx_name}  → {e}")
        err += 1

conn.commit()
conn.close()

print(f"\n完成：建立 {ok} 個 index，跳過 {skip} 個，錯誤 {err} 個")
