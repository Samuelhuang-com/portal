"""
診斷腳本：找出「全棟維護」行事曆重複顯示的根本原因
用法：在有 C:\\portal_data\\portal.db 存取權限的機器上執行
    python diagnose_full_pm_dup.py
"""
import sqlite3

DB_PATH = r"C:\portal_data\portal.db"

con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row
cur = con.cursor()

print("=" * 80)
print("Step 1：找出 full_bldg_pm_schedule 裡，同一 year_month 內 task_name 重複的記錄")
print("=" * 80)
cur.execute("""
    SELECT year_month, task_name, category, location, frequency, COUNT(*) as cnt,
           GROUP_CONCAT(id) as ids,
           GROUP_CONCAT(item_ragic_id) as item_ragic_ids
    FROM full_bldg_pm_schedule
    GROUP BY year_month, task_name, category, frequency
    HAVING cnt > 1
    ORDER BY year_month, cnt DESC
""")
rows = cur.fetchall()
if not rows:
    print("（無重複，這個表沒有問題）")
for r in rows:
    print(f"[{r['year_month']}] {r['task_name']!r} 類別={r['category']!r} 位置={r['location']!r} "
          f"頻率={r['frequency']!r} → 重複 {r['cnt']} 筆")
    print(f"    schedule.id = {r['ids']}")
    print(f"    來源 item_ragic_id = {r['item_ragic_ids']}")

print()
print("=" * 80)
print("Step 2：找出最新批次 full_bldg_pm_batch_item 裡，內容重複的列（真正根因）")
print("=" * 80)
cur.execute("""
    SELECT ragic_id FROM full_bldg_pm_batch
    ORDER BY period_month DESC LIMIT 1
""")
latest = cur.fetchone()
if not latest:
    print("找不到 full_bldg_pm_batch 資料")
else:
    latest_batch_id = latest["ragic_id"]
    print(f"最新批次 batch_ragic_id = {latest_batch_id}")
    cur.execute("""
        SELECT ragic_id, seq_no, category, location, frequency, task_name, scheduled_date, exec_months_raw
        FROM full_bldg_pm_batch_item
        WHERE batch_ragic_id = ?
        ORDER BY task_name, seq_no
    """, (latest_batch_id,))
    items = cur.fetchall()
    print(f"此批次共 {len(items)} 列，列出所有列（依 task_name 排序，方便肉眼比對重複）：")
    for it in items:
        print(f"  ragic_id={it['ragic_id']:<10} seq_no={it['seq_no']:<4} "
              f"task={it['task_name']!r:<40} category={it['category']!r} "
              f"location={it['location']!r} frequency={it['frequency']!r} "
              f"sched_date={it['scheduled_date']!r} exec_months={it['exec_months_raw']!r}")

print()
print("=" * 80)
print("Step 3：同樣檢查 mall_pm_schedule（商場排程，架構相同，可能有同類問題）")
print("=" * 80)
cur.execute("""
    SELECT year_month, task_name, category, location, frequency, COUNT(*) as cnt,
           GROUP_CONCAT(id) as ids
    FROM mall_pm_schedule
    GROUP BY year_month, task_name, category, frequency
    HAVING cnt > 1
    ORDER BY year_month, cnt DESC
""")
mall_rows = cur.fetchall()
if not mall_rows:
    print("（無重複）")
for r in mall_rows:
    print(f"[{r['year_month']}] {r['task_name']!r} → 重複 {r['cnt']} 筆，schedule.id = {r['ids']}")

con.close()
