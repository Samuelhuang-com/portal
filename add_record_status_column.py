# -*- coding: utf-8 -*-
"""
Migration：luqun_repair_case / dazhi_repair_case 新增 record_status 欄位
（2026-08-26）

背景：
    Ragic 報修表除了「處理狀況」／「處理狀態」之外，另有一個獨立的「狀態」欄
    （結案／待辦／作廢）。「作廢」只會寫在這一欄，Portal 先前完全沒有讀取，
    導致 EXCLUDED_STATUSES 的「作廢」規則永遠不會命中，作廢案件仍被計入
    Dashboard 與各項統計。

    本次把該欄同步進 DB（record_status），排除判定改為：
        「處理狀況／處理狀態」或「狀態」任一為 取消／作廢 → 排除

用法（在 backend 目錄下執行，會自動讀 backend/.env 的 DATABASE_URL）：
    cd backend
    python ..\\add_record_status_column.py            # 預覽（不寫入）
    python ..\\add_record_status_column.py --apply    # 實際執行

執行完必須重跑一次同步，record_status 才會有值：
    python sync_tool.py       （或在 Portal 的 Ragic 連線設定頁按同步）
"""
import os
import re
import sqlite3
import sys

TABLES = ("luqun_repair_case", "dazhi_repair_case")
COLUMN = "record_status"
DDL = 'ALTER TABLE {t} ADD COLUMN {c} VARCHAR(50) DEFAULT ""'


def resolve_db_path() -> str:
    """從 backend/.env 讀 DATABASE_URL，取出 SQLite 檔案路徑。"""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "backend", ".env"),
        os.path.join(here, ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]
    url = None
    for env_path in candidates:
        if not os.path.exists(env_path):
            continue
        with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.match(r"^\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
                if m:
                    url = m.group(1)
                    break
        if url:
            print("讀取設定：%s" % env_path)
            break
    if not url:
        sys.exit("找不到 DATABASE_URL，請確認 backend/.env 存在。")
    if not url.startswith("sqlite"):
        sys.exit("此腳本只支援 SQLite，目前 DATABASE_URL = %s" % url)
    path = url.split("///", 1)[1]
    if path.startswith("./"):
        path = os.path.join(os.getcwd(), path[2:])
    return os.path.normpath(path)


def main() -> None:
    apply = "--apply" in sys.argv
    db_path = resolve_db_path()
    print("資料庫：%s" % db_path)
    if not os.path.exists(db_path):
        sys.exit("資料庫檔案不存在：%s" % db_path)

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        todo = []
        for t in TABLES:
            exists = cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)
            ).fetchone()
            if not exists:
                print("  [跳過] 資料表不存在：%s" % t)
                continue
            cols = [r[1] for r in cur.execute("PRAGMA table_info(%s)" % t).fetchall()]
            if COLUMN in cols:
                print("  [已存在] %s.%s —— 不重複新增" % (t, COLUMN))
                continue
            todo.append(t)
            print("  [待新增] %s.%s" % (t, COLUMN))

        if not todo:
            print("\n沒有需要異動的項目。")
            return
        if not apply:
            print("\n預覽模式，未寫入。加上 --apply 才會實際執行：")
            for t in todo:
                print("    " + DDL.format(t=t, c=COLUMN))
            return

        for t in todo:
            cur.execute(DDL.format(t=t, c=COLUMN))
            print("  [完成] %s" % DDL.format(t=t, c=COLUMN))
        conn.commit()
        print("\n✅ 已完成。請接著重跑一次同步，record_status 才會有值。")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
