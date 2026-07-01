"""
診斷腳本：找出「室外機x5」在 full_bldg_pm_batch_item 裡的重複記錄
（附圖 Ragic 連結都指向 periodic-maintenance/21/4，代表都屬於 batch_ragic_id=4）

用法（在 backend 資料夾下執行）：
    python diagnose_full_pm_item_dup.py
"""
import sqlite3

DB_PATH = r"C:\portal_data\portal.db"
KEYWORD = "室外機x5"

con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row
cur = con.cursor()

print("=" * 90)
print(f"full_bldg_pm_batch_item 裡，task_name 包含「{KEYWORD}」的所有記錄（跨所有批次）")
print("=" * 90)
cur.execute("""
    SELECT i.ragic_id, i.batch_ragic_id, b.period_month, i.seq_no, i.task_name,
           i.category, i.location, i.frequency, i.scheduled_date, i.exec_months_raw,
           i.synced_at
    FROM full_bldg_pm_batch_item i
    LEFT JOIN full_bldg_pm_batch b ON b.ragic_id = i.batch_ragic_id
    WHERE i.task_name LIKE ?
    ORDER BY b.period_month, i.batch_ragic_id, i.seq_no
""", (f"%{KEYWORD}%",))
rows = cur.fetchall()
print(f"共 {len(rows)} 筆\n")
for r in rows:
    print(f"  ragic_id={r['ragic_id']:<10} batch_ragic_id={r['batch_ragic_id']:<6} "
          f"period_month={r['period_month']!r:<10} seq_no={r['seq_no']}")
    print(f"      task_name repr = {r['task_name']!r}")
    print(f"      category={r['category']!r} location={r['location']!r} frequency={r['frequency']!r}")
    print(f"      scheduled_date={r['scheduled_date']!r} exec_months={r['exec_months_raw']!r}")
    print(f"      synced_at={r['synced_at']!r}")
    print()

print("=" * 90)
print("full_bldg_pm_batch 全部批次（確認目前有哪些批次、各幾筆項目）")
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
          f"journal_no={r['journal_no']!r:<12} item_count={r['item_count']}")

print()
print("=" * 90)
print("batch_ragic_id=4 內，同 (task_name, scheduled_date) 分組找重複")
print("=" * 90)
cur.execute("""
    SELECT task_name, scheduled_date, COUNT(*) as cnt, GROUP_CONCAT(ragic_id) as ids
    FROM full_bldg_pm_batch_item
    WHERE batch_ragic_id = '4'
    GROUP BY task_name, scheduled_date
    HAVING cnt > 1
    ORDER BY task_name
""")
dup_rows = cur.fetchall()
print(f"共 {len(dup_rows)} 組重複\n")
for r in dup_rows:
    print(f"  task={r['task_name']!r} date={r['scheduled_date']!r} count={r['cnt']} ids={r['ids']}")

con.close()
