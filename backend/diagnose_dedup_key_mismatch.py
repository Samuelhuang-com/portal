"""
診斷腳本：檢查「室外機x5」在 full_bldg_pm_batch_item (ragic_id=1_128 / 4_278)
與 pm_plan_item (sheet 20, ragic_id=20_1_128 / 20_4_278) 的去重 key 是否真的相同。

行事曆去重邏輯用 key = (task_name, item_date, zone) 或
(source_sheet, scheduled_date, task_name)，理論上同一任務跨批次應該
completely 相同才對。如果 API 還是回傳 2 筆，代表這些 key 欄位有肉眼看
不出來的差異（例如全形/半形空白、不可見字元、日期格式差異）。

用法（在 backend 資料夾下執行）：
    python diagnose_dedup_key_mismatch.py
"""
import sqlite3

DB_PATH = r"C:\portal_data\portal.db"

con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row
cur = con.cursor()

print("=" * 100)
print("full_bldg_pm_batch_item — ragic_id 128 與 278 逐欄位 repr 比對")
print("=" * 100)
cur.execute("""
    SELECT i.ragic_id, i.batch_ragic_id, b.period_month, i.task_name, i.scheduled_date,
           i.category, i.location
    FROM full_bldg_pm_batch_item i
    LEFT JOIN full_bldg_pm_batch b ON b.ragic_id = i.batch_ragic_id
    WHERE i.ragic_id IN ('128', '278')
""")
rows = {r["ragic_id"]: r for r in cur.fetchall()}
for rid in ("128", "278"):
    r = rows.get(rid)
    if not r:
        print(f"  ragic_id={rid} 找不到記錄")
        continue
    print(f"  ragic_id={rid}")
    print(f"    batch_ragic_id = {r['batch_ragic_id']!r}")
    print(f"    period_month   = {r['period_month']!r}")
    print(f"    task_name      = {r['task_name']!r}  (len={len(r['task_name'] or '')}, bytes={ (r['task_name'] or '').encode('utf-8')!r})")
    print(f"    scheduled_date = {r['scheduled_date']!r}")
    print(f"    category       = {r['category']!r}")
    print(f"    location       = {r['location']!r}")
    print()

if "128" in rows and "278" in rows:
    a, b_ = rows["128"], rows["278"]
    print(f"  task_name 是否相等（==）      : {a['task_name'] == b_['task_name']}")
    print(f"  scheduled_date 是否相等（==）  : {a['scheduled_date'] == b_['scheduled_date']}")

print()
print("=" * 100)
print("pm_plan_item — sheet=20, ragic_id 含 128 / 278 逐欄位 repr 比對")
print("=" * 100)
cur.execute("""
    SELECT ragic_id, source_sheet, task_name, scheduled_date
    FROM pm_plan_item
    WHERE source_sheet = '20' AND (ragic_id LIKE '%_128' OR ragic_id LIKE '%_278')
""")
rows2 = {r["ragic_id"]: r for r in cur.fetchall()}
for rid, r in rows2.items():
    print(f"  ragic_id={rid}")
    print(f"    source_sheet   = {r['source_sheet']!r}")
    print(f"    task_name      = {r['task_name']!r}  (len={len(r['task_name'] or '')}, bytes={ (r['task_name'] or '').encode('utf-8')!r})")
    print(f"    scheduled_date = {r['scheduled_date']!r}")
    print()

ids2 = list(rows2.values())
if len(ids2) == 2:
    a, b_ = ids2[0], ids2[1]
    print(f"  task_name 是否相等（==）      : {a['task_name'] == b_['task_name']}")
    print(f"  scheduled_date 是否相等（==）  : {a['scheduled_date'] == b_['scheduled_date']}")
    print(f"  source_sheet 是否相等（==）    : {a['source_sheet'] == b_['source_sheet']}")

con.close()
