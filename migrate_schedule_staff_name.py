"""
一次性 migration：將 schedule_details.staff_name 從 Excel 原始字串
（如「吳友仁(福群)」「劉子良(PT)」）更新為純姓名（如「吳友仁」「劉子良」）。

來源：透過 staff_id JOIN schedule_staff_members.name 取得純姓名。
執行後可安全刪除此腳本。

用法：
  python migrate_schedule_staff_name.py --db C:/portal_data/portal.db [--dry-run]
"""
import argparse
import sqlite3
import sys


def run(db_path: str, dry_run: bool):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 取出所有 details，JOIN staff_members 取純姓名
    rows = conn.execute("""
        SELECT
            sd.id,
            sd.staff_name   AS old_name,
            sm.name         AS new_name
        FROM schedule_details sd
        JOIN schedule_staff_members sm ON sd.staff_id = sm.id
        WHERE sd.staff_name != sm.name
    """).fetchall()

    if not rows:
        print("✓ 無需更新，所有 staff_name 已與 schedule_staff_members.name 一致。")
        conn.close()
        return

    print(f"共 {len(rows)} 筆需要更新：")
    for r in rows[:20]:
        print(f"  id={r['id']}  「{r['old_name']}」→「{r['new_name']}」")
    if len(rows) > 20:
        print(f"  ... 另有 {len(rows) - 20} 筆（略）")

    if dry_run:
        print("\n[dry-run 模式] 未實際修改，加上 --apply 參數執行更新。")
        conn.close()
        return

    conn.executemany(
        "UPDATE schedule_details SET staff_name = ? WHERE id = ?",
        [(r["new_name"], r["id"]) for r in rows],
    )
    conn.commit()
    print(f"\n✓ 已更新 {len(rows)} 筆。")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="schedule_details.staff_name migration")
    parser.add_argument("--db", required=True, help="portal.db 路徑")
    parser.add_argument("--apply", action="store_true", help="實際寫入（預設 dry-run）")
    args = parser.parse_args()

    dry = not args.apply
    if dry:
        print("[dry-run 模式] 只預覽，不修改。加 --apply 才實際執行。\n")

    try:
        run(args.db, dry)
    except Exception as e:
        print(f"[錯誤] {e}", file=sys.stderr)
        sys.exit(1)
