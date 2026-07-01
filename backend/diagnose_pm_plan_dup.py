"""
診斷腳本：找出「出風口除塵」（或指定任務）在 pm_plan_item 裡的重複記錄
用法（在 backend 資料夾下執行）：
    python diagnose_pm_plan_dup.py
"""
import sqlite3

DB_PATH = r"C:\portal_data\portal.db"
KEYWORD = "出風口除塵"

con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row
cur = con.cursor()

print("=" * 90)
print(f"pm_plan_item 裡，task_name 包含「{KEYWORD}」的所有記錄")
print("=" * 90)
cur.execute("""
    SELECT ragic_id, source_sheet, source_label, task_name, category, frequency,
           scheduled_date, scheduler_name, exec_months_raw, ragic_url,
           ragic_created_at, ragic_updated_at, synced_at
    FROM pm_plan_item
    WHERE task_name LIKE ?
    ORDER BY scheduled_date, ragic_id
""", (f"%{KEYWORD}%",))
rows = cur.fetchall()
print(f"共 {len(rows)} 筆\n")
for r in rows:
    print(f"  ragic_id={r['ragic_id']:<15} source_sheet={r['source_sheet']} "
          f"source_label={r['source_label']!r} sched_date={r['scheduled_date']!r}")
    print(f"      task_name repr = {r['task_name']!r}")
    print(f"      category={r['category']!r} frequency={r['frequency']!r} "
          f"scheduler={r['scheduler_name']!r} exec_months={r['exec_months_raw']!r}")
    print(f"      ragic_url={r['ragic_url']!r}")
    print(f"      created={r['ragic_created_at']!r} updated={r['ragic_updated_at']!r} synced_at={r['synced_at']!r}")
    print()

print("=" * 90)
print("全部 pm_plan_item 依 (source_sheet, scheduled_date, task_name) 分組，找出任何重複")
print("=" * 90)
cur.execute("""
    SELECT source_sheet, scheduled_date, task_name, COUNT(*) as cnt,
           GROUP_CONCAT(ragic_id) as ids
    FROM pm_plan_item
    WHERE scheduled_date != ''
    GROUP BY source_sheet, scheduled_date, task_name
    HAVING cnt > 1
    ORDER BY scheduled_date
""")
dup_rows = cur.fetchall()
print(f"共 {len(dup_rows)} 組重複\n")
for r in dup_rows:
    print(f"  sheet={r['source_sheet']} date={r['scheduled_date']} task={r['task_name']!r} "
          f"count={r['cnt']} ids={r['ids']}")

con.close()
