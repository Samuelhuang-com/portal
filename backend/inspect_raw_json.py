"""
檢查 approved_purchase_requests.raw_data_json 欄位內容
用途：確認 Ragic 清單 API 是否已含品項子表格資料（可否省略 Detail API）

執行方式：
  cd portal/backend
  python inspect_raw_json.py
"""
import json
import sqlite3
import sys
from pathlib import Path

# 讀取 DB 路徑
env_path = Path(__file__).parent / ".env"
db_path = "C:/portal_data/portal.db"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("DATABASE_URL"):
            url = line.split("=", 1)[1].strip().strip('"').strip("'")
            # sqlite:///C:/portal_data/portal.db → C:/portal_data/portal.db
            db_path = url.replace("sqlite:///", "")
            break

print(f"DB: {db_path}")
conn = sqlite3.connect(db_path)
cur  = conn.cursor()

# ── 找目標記錄 ────────────────────────────────────────────────────────────────
purchase_no = sys.argv[1] if len(sys.argv) > 1 else "樂專購20260500001"
cur.execute(
    "SELECT id, purchase_no, department_display, detail_synced, raw_data_json "
    "FROM approved_purchase_requests WHERE purchase_no = ? LIMIT 1",
    (purchase_no,)
)
row = cur.fetchone()
if not row:
    print(f"⚠️  找不到 purchase_no = {purchase_no}")
    # 列出所有專案部門的 purchase_no
    cur.execute(
        "SELECT id, purchase_no, detail_synced FROM approved_purchase_requests "
        "WHERE department_display='專案' ORDER BY id DESC LIMIT 10"
    )
    rows = cur.fetchall()
    print(f"\n專案部門最近 10 筆：")
    for r in rows:
        print(f"  id={r[0]}  no={r[1]}  detail_synced={r[2]}")
    conn.close()
    sys.exit(1)

rid, no, dept, detail_synced, raw_json = row
print(f"\n=== {no} (id={rid}, dept={dept}, detail_synced={detail_synced}) ===\n")

raw = {}
if raw_json:
    try:
        raw = json.loads(raw_json)
    except Exception as e:
        print(f"raw_data_json 解析失敗：{e}")
        sys.exit(1)

# ── 分類列印 ──────────────────────────────────────────────────────────────────
main_fields = {}
subtable_rows = {}
meta_fields = {}

for k, v in raw.items():
    if k.startswith("_"):
        meta_fields[k] = v
    elif k.lstrip("-").isdigit() and isinstance(v, dict):
        subtable_rows[k] = v
    else:
        main_fields[k] = v

print("【主表欄位】")
for k, v in main_fields.items():
    print(f"  {k!r:30s} = {str(v)[:80]!r}")

print(f"\n【子表格行數（頂層數字 key）】= {len(subtable_rows)}")
if subtable_rows:
    print("  ← 清單 API 已包含品項！可直接從 raw_data_json 解析")
    for row_key, row_data in sorted(subtable_rows.items(), key=lambda x: int(x[0])):
        print(f"\n  --- 子列 {row_key} ---")
        for fk, fv in row_data.items():
            if not fk.startswith("_"):
                print(f"    {fk!r:30s} = {str(fv)[:80]!r}")
else:
    print("  ← 頂層無數字 key 品項")

print(f"\n【meta 欄位（_開頭）—完整顯示 _subtable_* 內容】")
for k, v in meta_fields.items():
    if k.startswith("_subtable_"):
        print(f"\n  {k!r} 的內容：")
        # v 可能是 dict 字串或 dict
        if isinstance(v, str):
            try:
                import ast
                v = ast.literal_eval(v)
            except Exception:
                print(f"    (解析失敗) {v[:200]}")
                continue
        if isinstance(v, dict):
            for row_key, row_data in sorted(v.items(), key=lambda x: str(x[0])):
                print(f"    --- 子列 {row_key} ---")
                if isinstance(row_data, dict):
                    for fk, fv in row_data.items():
                        print(f"      {fk!r:35s} = {str(fv)[:80]!r}")
                else:
                    print(f"      {row_data}")
        else:
            print(f"    {v}")
    else:
        print(f"  {k!r:30s} = {str(v)[:80]!r}")

conn.close()
