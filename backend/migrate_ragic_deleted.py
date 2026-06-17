"""
Migration：為 luqun_repair_case 和 dazhi_repair_case 加入
  - is_ragic_deleted (BOOLEAN, DEFAULT 0)
  - ragic_deleted_at (DATETIME, NULL)

用法：
  cd backend
  python migrate_ragic_deleted.py

DB 路徑：自動從 .env 讀取 DATABASE_URL（優先），fallback 到 C:/portal_data/portal.db
"""
import sqlite3
import os
import re

def _resolve_db_path() -> str:
    """從 .env 讀取 DATABASE_URL，取出 SQLite 檔案路徑"""
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"DATABASE_URL\s*=\s*sqlite:///(.*)", line.strip())
                if m:
                    return m.group(1)
    # fallback
    return r"C:/portal_data/portal.db"

DB_PATH = _resolve_db_path()

MIGRATIONS = [
    (
        "luqun_repair_case",
        [
            "ALTER TABLE luqun_repair_case ADD COLUMN is_ragic_deleted BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE luqun_repair_case ADD COLUMN ragic_deleted_at DATETIME",
        ],
    ),
    (
        "dazhi_repair_case",
        [
            "ALTER TABLE dazhi_repair_case ADD COLUMN is_ragic_deleted BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE dazhi_repair_case ADD COLUMN ragic_deleted_at DATETIME",
        ],
    ),
]


def column_exists(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def main():
    print(f"DB: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for table, stmts in MIGRATIONS:
        for stmt in stmts:
            # 從 ALTER TABLE ... ADD COLUMN <col_name> ... 取出欄位名稱
            col_name = stmt.split("ADD COLUMN")[1].strip().split()[0]
            if column_exists(cur, table, col_name):
                print(f"  [SKIP] {table}.{col_name} 已存在")
                continue
            print(f"  [RUN]  {stmt}")
            cur.execute(stmt)

    conn.commit()
    conn.close()
    print("Migration 完成。")


if __name__ == "__main__":
    main()
