"""
班表拆分 — 資料庫 schema 遷移腳本（2026-08-14）

本腳本只處理「飯店班表既有資料表」的異動。
商場班表的 6 張新表由 SQLAlchemy `create_all` 在後端啟動時自動建立，不需本腳本處理。

異動內容
────────
1. schedule_staff_members 新增 venue_flag 欄位（VARCHAR(4) NOT NULL DEFAULT '飯'）
2. schedules 建立部分唯一索引 uq_schedules_year_month_active
   （只約束 is_deleted = 0 的列 —— 既有流程是「先軟刪除舊班表再重新匯入同年月」，
     一般唯一約束會讓重新匯入直接失敗）
3. schedule_details 建立三個索引（work_date / schedule_id / staff_id）
   原本完全沒有索引，/shifts-range 的區間查詢是全表掃描

⚠️ 為什麼不能只靠 create_all
──────────────────────────
`Base.metadata.create_all(checkfirst=True)` 對「已存在的表」會整張跳過，
連帶新加的 Index 也不會建立，新欄位也不會補。所以既有表必須用本腳本處理。

⚠️ 第 2 項可能失敗
────────────────
若資料庫裡已經有「同年月且都未刪除」的重複班表，唯一索引會建不起來。
腳本會先檢查並列出重複資料，請先人工處理（保留一筆、其餘軟刪除）後再重跑。

用法
────
    # 預覽（預設，不寫入任何資料）
    cd backend
    python ..\\docs\\migrate_schedule_venue_split.py

    # 正式執行（會先自動備份資料庫）
    python ..\\docs\\migrate_schedule_venue_split.py --apply

    # 指定資料庫路徑
    python ..\\docs\\migrate_schedule_venue_split.py --apply --db C:\\Portal_Data\\portal.db

本腳本可重複執行（每個步驟都會先檢查是否已完成）。
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime

HOTEL_VENUE_FLAG = "飯"


def _resolve_db_path(explicit: str | None) -> str:
    if explicit:
        return explicit
    try:
        sys.path.insert(0, os.getcwd())
        from app.core.config import settings  # type: ignore

        url = str(settings.DATABASE_URL)
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "", 1)
        raise SystemExit(f"[中止] 本腳本只支援 SQLite，但設定的是：{url}")
    except ImportError:
        raise SystemExit(
            "[中止] 找不到 app.core.config。\n"
            "       請在 backend/ 目錄下執行，或用 --db 明確指定資料庫路徑。"
        )


def _backup(db_path: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{db_path}.bak_schedule_split_{stamp}"
    shutil.copy2(db_path, dst)
    return dst


def _has_column(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1] == column for r in cur.fetchall())


def _has_index(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (name,))
    return cur.fetchone() is not None


def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def main() -> int:
    ap = argparse.ArgumentParser(description="班表拆分 schema 遷移")
    ap.add_argument("--apply", action="store_true", help="實際寫入。未加此參數時只做預覽。")
    ap.add_argument("--db", default=None, help="SQLite 資料庫路徑（預設讀 app.core.config）")
    args = ap.parse_args()

    db_path = _resolve_db_path(args.db)
    if not os.path.exists(db_path):
        print(f"[中止] 找不到資料庫：{db_path}")
        return 1

    print(f"資料庫：{db_path}")
    print(f"模式　：{'正式執行（會寫入）' if args.apply else '預覽（不寫入）'}")
    print("─" * 64)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    for t in ("schedule_staff_members", "schedules", "schedule_details"):
        if not _table_exists(cur, t):
            print(f"[中止] 找不到資料表 {t}，請確認連到正確的資料庫。")
            conn.close()
            return 1

    steps: list[tuple[str, str]] = []   # (說明, SQL)

    # ── 1. venue_flag 欄位 ───────────────────────────────────────
    if _has_column(cur, "schedule_staff_members", "venue_flag"):
        print("[跳過] schedule_staff_members.venue_flag 已存在")
    else:
        steps.append((
            "schedule_staff_members 新增 venue_flag 欄位",
            f"ALTER TABLE schedule_staff_members "
            f"ADD COLUMN venue_flag VARCHAR(4) NOT NULL DEFAULT '{HOTEL_VENUE_FLAG}'",
        ))

    # ── 2. schedules 部分唯一索引 ────────────────────────────────
    if _has_index(cur, "uq_schedules_year_month_active"):
        print("[跳過] uq_schedules_year_month_active 已存在")
    else:
        cur.execute("""
            SELECT schedule_year, schedule_month, COUNT(*) AS c
            FROM schedules
            WHERE is_deleted = 0
            GROUP BY schedule_year, schedule_month
            HAVING c > 1
        """)
        dups = cur.fetchall()
        if dups:
            print("[中止] 有重複的未刪除班表，唯一索引無法建立。請先人工處理：")
            for y, m, c in dups:
                print(f"        {y} 年 {m} 月：{c} 筆")
                cur.execute(
                    "SELECT id, title, source_file_name, created_at FROM schedules "
                    "WHERE schedule_year=? AND schedule_month=? AND is_deleted=0 "
                    "ORDER BY created_at",
                    (y, m),
                )
                for row in cur.fetchall():
                    print(f"          - id={row[0]} title={row[1]!r} file={row[2]!r} created={row[3]}")
            print("\n        處理方式：保留正確的一筆，其餘在「班表總覽」頁面刪除（軟刪除）後重跑本腳本。")
            conn.close()
            return 1
        steps.append((
            "schedules 建立部分唯一索引（只約束未刪除的列）",
            "CREATE UNIQUE INDEX uq_schedules_year_month_active "
            "ON schedules (schedule_year, schedule_month) WHERE is_deleted = 0",
        ))

    # ── 3. schedule_details 索引 ─────────────────────────────────
    for idx_name, cols in [
        ("ix_schedule_details_work_date",   "work_date"),
        ("ix_schedule_details_schedule_id", "schedule_id"),
        ("ix_schedule_details_staff_id",    "staff_id"),
    ]:
        if _has_index(cur, idx_name):
            print(f"[跳過] {idx_name} 已存在")
        else:
            steps.append((
                f"schedule_details 建立索引 {idx_name}",
                f"CREATE INDEX {idx_name} ON schedule_details ({cols})",
            ))

    if not steps:
        print("\n所有異動都已套用，不需要再執行。")
        conn.close()
        return 0

    print(f"\n待執行 {len(steps)} 個步驟：")
    for i, (desc, sql) in enumerate(steps, 1):
        print(f"  {i}. {desc}")
        print(f"     {sql}")

    if not args.apply:
        print("\n" + "─" * 64)
        print("以上為預覽，未寫入任何資料。")
        print("確認無誤後，加上 --apply 重跑即可實際執行。")
        conn.close()
        return 0

    backup_path = _backup(db_path)
    print(f"\n已備份：{backup_path}")

    try:
        for desc, sql in steps:
            cur.execute(sql)
            print(f"  ✓ {desc}")
        conn.commit()
    except Exception as exc:
        conn.rollback()
        conn.close()
        print(f"\n[失敗] 已回滾，資料庫未變更：{exc}")
        print(f"       備份檔仍保留在：{backup_path}")
        return 1

    # ── 驗證 ─────────────────────────────────────────────────────
    ok = True
    if not _has_column(cur, "schedule_staff_members", "venue_flag"):
        print("[警告] venue_flag 欄位未建立成功"); ok = False
    for idx in ("uq_schedules_year_month_active", "ix_schedule_details_work_date",
                "ix_schedule_details_schedule_id", "ix_schedule_details_staff_id"):
        if not _has_index(cur, idx):
            print(f"[警告] 索引 {idx} 未建立成功"); ok = False

    cur.execute("SELECT COUNT(*) FROM schedule_staff_members WHERE venue_flag = ?", (HOTEL_VENUE_FLAG,))
    flagged = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM schedule_staff_members")
    total = cur.fetchone()[0]
    conn.close()

    print("\n" + "─" * 64)
    print(f"完成。飯店人員共 {total} 筆，其中 venue_flag='{HOTEL_VENUE_FLAG}' 有 {flagged} 筆。")
    if not ok:
        return 1
    print("\n商場班表的 6 張新表會在後端啟動時由 create_all 自動建立，不需另外處理。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
