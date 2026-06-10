"""
班表資料遷移工具
用法：
  python migrate_schedule.py --src C:/portal_data/portal.db --dst C:/portal_data/portal_dev.db

若開發區 DB 路徑不確定，先執行查詢模式（不加 --dst）只印出來源資料筆數：
  python migrate_schedule.py --src C:/portal_data/portal.db
"""
import argparse
import sqlite3
import sys

TABLES = [
    "schedule_departments",
    "schedule_staff_members",
    "schedule_shift_types",
    "schedules",
    "schedule_details",
    "schedule_import_logs",
]


def migrate(src_path: str, dst_path: str | None):
    src = sqlite3.connect(src_path)
    src.row_factory = sqlite3.Row

    if dst_path is None:
        print("[查詢模式] 來源資料筆數：")
        for t in TABLES:
            cnt = src.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {cnt} 筆")
        src.close()
        return

    dst = sqlite3.connect(dst_path)

    for table in TABLES:
        # 從來源複製 CREATE TABLE schema（若目的地尚無此 table）
        ddl_row = src.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not ddl_row:
            print(f"  {table}: 來源找不到此 table，跳過")
            continue
        dst.execute(f"DROP TABLE IF EXISTS {table}")
        dst.execute(ddl_row[0])
        dst.commit()

        # 取來源資料
        rows = src.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"  {table}: 0 筆（table 已建立）")
            continue

        cols = rows[0].keys()
        col_list = ", ".join(cols)
        placeholders = ", ".join(["?"] * len(cols))

        data = [tuple(r) for r in rows]
        dst.executemany(
            f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})",
            data,
        )
        dst.commit()
        print(f"  {table}: 匯入 {len(data)} 筆 ✓")

    src.close()
    dst.close()
    print("\n完成！")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="班表 DB 遷移工具")
    parser.add_argument("--src", required=True, help="來源 DB 路徑（正式區）")
    parser.add_argument("--dst", default=None, help="目的 DB 路徑（開發區）")
    args = parser.parse_args()

    print(f"來源：{args.src}")
    if args.dst:
        print(f"目的：{args.dst}")
    print()

    try:
        migrate(args.src, args.dst)
    except Exception as e:
        print(f"[錯誤] {e}", file=sys.stderr)
        sys.exit(1)
