"""
一次性清理腳本：刪除 memos 表中 source='contract_expiry' 的重複公告，
同一 (source_id, 建立日期) 只保留最早建立的一筆。

用法（在 backend 資料夾下執行）：
    python cleanup_dup_contract_memo.py            # 先看會刪哪些（dry-run）
    python cleanup_dup_contract_memo.py --apply     # 實際刪除
"""
import sys
import sqlite3

DB_PATH = r"C:\portal_data\portal.db"
APPLY = "--apply" in sys.argv

con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row
cur = con.cursor()

cur.execute("""
    SELECT id, source_id, title, created_at
    FROM memos
    WHERE source = 'contract_expiry'
    ORDER BY source_id, date(created_at), created_at
""")
rows = cur.fetchall()

groups: dict = {}
for r in rows:
    day = (r["created_at"] or "")[:10]
    key = (r["source_id"], day)
    groups.setdefault(key, []).append(r)

to_delete = []
for key, items in groups.items():
    if len(items) <= 1:
        continue
    # items 已依 created_at 排序，保留第一筆（最早），其餘刪除
    keep = items[0]
    remove = items[1:]
    print(f"合約 {key[0]}（{key[1]}）：共 {len(items)} 筆，保留 id={keep['id']}（{keep['created_at']}），"
          f"將刪除 {len(remove)} 筆：{[r['id'] for r in remove]}")
    to_delete.extend(r["id"] for r in remove)

print()
if not to_delete:
    print("沒有發現重複，無需清理。")
else:
    print(f"共 {len(to_delete)} 筆將被刪除。")
    if APPLY:
        cur.executemany("DELETE FROM memos WHERE id = ?", [(i,) for i in to_delete])
        con.commit()
        print("已刪除。")
    else:
        print("目前是 dry-run，未實際刪除。確認無誤後請加 --apply 參數重跑一次。")

con.close()
