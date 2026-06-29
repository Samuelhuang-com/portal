"""
export_contract_sql.py
────────────────────────────────────────────────────────────────────────────────
從測試 DB 讀取合約相關資料，產生可直接在正式 DB 執行的 SQL INSERT script。

使用方式（在 backend/ 目錄下執行）：
    python scripts/export_contract_sql.py [--src SOURCE_DB] [--out OUTPUT_SQL]

    --src   來源 DB 路徑（預設：C:/portal_data/portal.db）
    --out   輸出 SQL 檔案路徑（預設：scripts/insert_contracts_prod.sql）

範例：
    cd backend
    python scripts/export_contract_sql.py
    python scripts/export_contract_sql.py --src C:/portal_data/portal.db --out scripts/insert_contracts_prod.sql
"""

import sys, os, sqlite3, argparse
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--src", default="C:/portal_data/portal.db")
parser.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "insert_contracts_prod.sql"))
args = parser.parse_args()

if not os.path.exists(args.src):
    print(f"❌  找不到來源 DB：{args.src}")
    sys.exit(1)

conn = sqlite3.connect(args.src)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def esc(v) -> str:
    """轉義 SQL 字串值"""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    # 字串：單引號轉義
    return "'" + str(v).replace("'", "''") + "'"

def gen_inserts(table: str, rows, cols: list[str]) -> list[str]:
    sqls = []
    for row in rows:
        vals = ", ".join(esc(row[c]) for c in cols)
        col_list = ", ".join(cols)
        sqls.append(
            f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({vals});"
        )
    return sqls

lines = []
lines.append(f"-- Portal 合約資料匯入腳本")
lines.append(f"-- 產生時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append(f"-- 來源：{args.src}")
lines.append(f"-- 使用 INSERT OR IGNORE（已存在的 PK 自動跳過）")
lines.append("")
lines.append("PRAGMA foreign_keys = OFF;")
lines.append("BEGIN TRANSACTION;")
lines.append("")

# ── vendors ──────────────────────────────────────────────────────────────────
cur.execute("SELECT * FROM vendors")
vendor_rows = cur.fetchall()
if vendor_rows:
    cols = [d[0] for d in cur.description]
    lines.append(f"-- ── vendors（{len(vendor_rows)} 筆）────────────────────────────────────")
    lines.extend(gen_inserts("vendors", vendor_rows, cols))
    lines.append("")
print(f"✓  vendors：{len(vendor_rows)} 筆")

# ── contracts ─────────────────────────────────────────────────────────────────
cur.execute("SELECT * FROM contracts")
contract_rows = cur.fetchall()
if contract_rows:
    cols = [d[0] for d in cur.description]
    lines.append(f"-- ── contracts（{len(contract_rows)} 筆）──────────────────────────────────")
    lines.extend(gen_inserts("contracts", contract_rows, cols))
    lines.append("")
print(f"✓  contracts：{len(contract_rows)} 筆")

# ── contract_items ────────────────────────────────────────────────────────────
cur.execute("SELECT * FROM contract_items")
item_rows = cur.fetchall()
if item_rows:
    cols = [d[0] for d in cur.description]
    lines.append(f"-- ── contract_items（{len(item_rows)} 筆）──────────────────────────────────")
    lines.extend(gen_inserts("contract_items", item_rows, cols))
    lines.append("")
print(f"✓  contract_items：{len(item_rows)} 筆")

lines.append("COMMIT;")
lines.append("PRAGMA foreign_keys = ON;")
lines.append("")

conn.close()

# 寫出 SQL 檔案
sql_text = "\n".join(lines)
with open(args.out, "w", encoding="utf-8") as f:
    f.write(sql_text)

print(f"\n✅  SQL 已產生：{args.out}")
print(f"   共 {len(vendor_rows)+len(contract_rows)+len(item_rows)} 筆 INSERT")
print(f"\n正式區執行方式：")
print(f"   sqlite3 <正式DB路徑> < {os.path.basename(args.out)}")
print(f"   或用 DB Browser for SQLite 開啟後執行")
