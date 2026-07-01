"""
第二輪診斷：鎖定「各樓層配電盤接點鎖螺絲」這個具體任務，
找出所有相關記錄（不論 year_month 是否相同、不論哪個批次），
用 repr() 印出以便看出是否有看不見的字元差異。

用法（在 backend 資料夾下執行）：
    python diagnose_full_pm_dup2.py
"""
import sqlite3

DB_PATH = r"C:\portal_data\portal.db"
KEYWORD = "配電盤接點鎖螺絲"

con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row
cur = con.cursor()

print("=" * 90)
print(f"Step A：full_bldg_pm_schedule 裡，task_name 包含「{KEYWORD}」的所有記錄")
print("=" * 90)
cur.execute("""
    SELECT id, year_month, item_ragic_id, task_name, category, location, frequency,
           scheduled_date, is_completed, portal_edited_at, schedule_source
    FROM full_bldg_pm_schedule
    WHERE task_name LIKE ?
    ORDER BY scheduled_date, year_month
""", (f"%{KEYWORD}%",))
rows = cur.fetchall()
print(f"共 {len(rows)} 筆")
for r in rows:
    print(f"  id={r['id']:<6} year_month={r['year_month']:<10} item_ragic_id={r['item_ragic_id']:<12} "
          f"sched_date={r['scheduled_date']:<8} completed={r['is_completed']} edited={r['portal_edited_at']} "
          f"source={r['schedule_source']}")
    print(f"      task_name repr = {r['task_name']!r}")
    print(f"      category={r['category']!r} location={r['location']!r} frequency={r['frequency']!r}")

print()
print("=" * 90)
print(f"Step B：full_bldg_pm_batch_item 裡，task_name 包含「{KEYWORD}」的所有記錄（跨所有批次）")
print("=" * 90)
cur.execute("""
    SELECT i.ragic_id, i.batch_ragic_id, b.period_month, i.seq_no, i.task_name, i.category,
           i.location, i.frequency, i.scheduled_date, i.exec_months_raw
    FROM full_bldg_pm_batch_item i
    LEFT JOIN full_bldg_pm_batch b ON b.ragic_id = i.batch_ragic_id
    WHERE i.task_name LIKE ?
    ORDER BY b.period_month, i.seq_no
""", (f"%{KEYWORD}%",))
rows2 = cur.fetchall()
print(f"共 {len(rows2)} 筆")
for r in rows2:
    print(f"  ragic_id={r['ragic_id']:<10} batch={r['batch_ragic_id']:<6} period_month={r['period_month']:<10} "
          f"sched_date={r['scheduled_date']!r:<12} exec_months={r['exec_months_raw']!r}")
    print(f"      task_name repr = {r['task_name']!r}")

print()
print("=" * 90)
print("Step C：所有 full_bldg_pm_batch（確認到底有幾個批次、每個批次幾筆項目）")
print("=" * 90)
cur.execute("""
    SELECT b.ragic_id, b.period_month, b.journal_no, COUNT(i.ragic_id) as item_count
    FROM full_bldg_pm_batch b
    LEFT JOIN full_bldg_pm_batch_item i ON i.batch_ragic_id = b.ragic_id
    GROUP BY b.ragic_id
    ORDER BY b.period_month DESC
""")
for r in cur.fetchall():
    print(f"  batch_ragic_id={r['ragic_id']:<6} period_month={r['period_month']:<10} "
          f"journal_no={r['journal_no']!r:<10} item_count={r['item_count']}")

con.close()
