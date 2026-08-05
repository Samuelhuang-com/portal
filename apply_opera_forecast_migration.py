"""
OPERA 房價預測 — 資料表 + 索引一次建立（2026-08-05）

用途：
  `add_opera_forecast_tables.sql` 只負責建索引，**資料表本身**是靠後端啟動時的
  `Base.metadata.create_all()` 產生的。所以還沒重啟後端就直接跑那支 SQL 會噴
  `no such table: main.opera_event`。

  這支腳本把兩件事一次做完，不需要先重啟服務：
    1. 從 SQLAlchemy model 定義建立 4 張預測相關資料表（只建缺的）
    2. 套用 add_opera_forecast_tables.sql 的索引（全部 IF NOT EXISTS）

安全性：
  - 只會建立「還不存在」的資料表與索引，已存在的直接跳過
  - **不會**碰到這 4 張表以外的任何資料表（明確指定 tables=）
  - 不會刪除或修改任何既有資料
  - 可以重複執行

用法（在 D:\\portal 或專案根目錄開終端機）：
    python apply_opera_forecast_migration.py

    # 指定資料庫路徑（預設讀 backend/.env 的 DATABASE_URL）
    python apply_opera_forecast_migration.py --db C:\\Portal_Data\\portal.db

或者直接雙擊同資料夾裡的 apply_opera_forecast_migration.bat
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
SQL_FILE = PROJECT_ROOT / "add_opera_forecast_tables.sql"

EXPECTED_TABLES = [
    "opera_event",
    "opera_forecast_coefficient",
    "opera_forecast_run",
    "opera_forecast_daily",
]

# 預測會讀既有的營收事實表，沒有它就沒有東西可以估係數
REQUIRED_EXISTING = ["opera_revenue_daily"]

CRITICAL_INDEXES = [
    "idx_opera_fc_coef_key",       # 係數唯一鍵
    "idx_opera_fc_daily_run_date", # 一次執行同一天只能一筆
]

_SQLITE_URL_RE = re.compile(r"^sqlite(\+\w+)?:///(?P<path>.*)$")


def die(message: str) -> None:
    print("\n[錯誤] " + message)
    sys.exit(1)


def resolve_db_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()

    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() != "DATABASE_URL":
                continue
            value = value.strip().strip('"').strip("'")
            m = _SQLITE_URL_RE.match(value)
            if not m:
                die(
                    f"backend/.env 的 DATABASE_URL 不是 SQLite（{value}）。\n"
                    "  若已遷移 PostgreSQL，請改用該資料庫的 migration 方式，或用 --db 指定 SQLite 檔案。"
                )
            p = Path(m.group("path"))
            if not p.is_absolute():
                p = (BACKEND_DIR / p).resolve()
            return p

    die(
        "找不到 backend/.env 或其中的 DATABASE_URL。\n"
        "  請改用：python apply_opera_forecast_migration.py --db C:\\Portal_Data\\portal.db"
    )


def create_tables(db_path: Path) -> list[str]:
    """回傳這次「新建立」的資料表名稱。"""
    sys.path.insert(0, str(BACKEND_DIR))
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")

    try:
        from sqlalchemy import create_engine, inspect

        from app.core.database import Base
        import app.models.opera_forecast   # noqa: F401
    except ImportError as exc:
        die(
            f"匯入後端模組失敗：{exc}\n"
            "  請確認在專案根目錄執行（旁邊要看得到 backend 資料夾），\n"
            "  且已安裝相依套件（pip install -r backend/requirements.txt）。"
        )

    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 60},
    )

    # ⚠️ 安全關鍵：`import app.models.opera_forecast` 會連帶執行 app/models/__init__.py，
    #    使 Base.metadata 裡含有全專案的資料表。因此**明確指定 tables=**，
    #    只讓 create_all 看得到這 4 張表，其他模組一律不碰。
    tables = [
        table for name, table in Base.metadata.tables.items()
        if name in EXPECTED_TABLES
    ]
    found = {t.name for t in tables}
    missing_def = [t for t in EXPECTED_TABLES if t not in found]
    if missing_def:
        die(
            f"在 model 定義中找不到這些資料表：{missing_def}\n"
            "  請確認 backend/app/models/opera_forecast.py 是最新版本。"
        )

    before = set(inspect(engine).get_table_names())
    Base.metadata.create_all(bind=engine, tables=tables)
    after = set(inspect(engine).get_table_names())
    engine.dispose()

    created = sorted(after - before)
    unexpected = [t for t in created if t not in EXPECTED_TABLES]
    if unexpected:
        die(f"異常：建立了非預期的資料表 {unexpected}，請回報。")
    return created


def apply_indexes(db_path: Path) -> tuple[int, list[str]]:
    if not SQL_FILE.exists():
        die(f"找不到 {SQL_FILE.name}，請確認在專案根目錄執行。")

    pattern = "idx_opera_event_%' OR name LIKE 'idx_opera_fc_%"
    con = sqlite3.connect(str(db_path))
    try:
        query = (
            "SELECT name FROM sqlite_master WHERE type='index' "
            f"AND (name LIKE '{pattern}')"
        )
        before = {r[0] for r in con.execute(query)}
        con.executescript(SQL_FILE.read_text(encoding="utf-8"))
        con.commit()
        after = {r[0] for r in con.execute(query)}
        return len(after), sorted(after - before)
    finally:
        con.close()


def verify(db_path: Path) -> bool:
    con = sqlite3.connect(str(db_path))
    try:
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        missing = [t for t in EXPECTED_TABLES if t not in tables]

        print("\n── 資料表 ──────────────────────────────────────────────")
        for t in EXPECTED_TABLES:
            count = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if t in tables else "-"
            mark = "OK " if t in tables else "缺 "
            print(f"  [{mark}] {t:32} 現有資料 {count} 筆")

        print("\n── 前置資料表（預測的資料來源）──────────────────────────")
        lack_source = False
        for t in REQUIRED_EXISTING:
            if t in tables:
                n = con.execute(f"SELECT COUNT(*) FROM {t} WHERE is_current = 1").fetchone()[0]
                print(f"  [OK ] {t:32} 有效資料 {n:,} 筆")
                if n == 0:
                    lack_source = True
            else:
                print(f"  [缺 ] {t:32} —— 請先跑 apply_opera_migration.py 並匯入資料")
                lack_source = True

        indexes = sorted(r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND (name LIKE 'idx_opera_event_%' OR name LIKE 'idx_opera_fc_%')"
        ))
        print(f"\n── 索引（共 {len(indexes)} 個）────────────────────────────")
        for i in indexes:
            print(f"  [OK ] {i}")
        missing_idx = [i for i in CRITICAL_INDEXES if i not in indexes]

        print("\n── integrity_check ────────────────────────────────────")
        print("  " + str(con.execute("PRAGMA integrity_check").fetchone()[0]))

        if missing:
            print(f"\n[失敗] 仍缺資料表：{missing}")
            return False
        if missing_idx:
            print(f"\n[失敗] 仍缺關鍵唯一索引：{missing_idx}")
            return False
        if lack_source:
            print("\n[注意] 資料表已建好，但還沒有營收資料可供估算係數。")
            print("       請先到 /opera/import 匯入 History and Forecast 後，")
            print("       再到 /opera/forecast 按「重新估算係數」。")
        return True
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="OPERA 房價預測 — 建表 + 建索引")
    parser.add_argument("--db", help=r"SQLite 檔案路徑，例如 C:\Portal_Data\portal.db")
    args = parser.parse_args()

    print("=" * 60)
    print("  OPERA 房價預測 — 資料表 + 索引建立")
    print("=" * 60)

    db_path = resolve_db_path(args.db)
    print(f"\n資料庫：{db_path}")
    if not db_path.exists():
        die(f"資料庫檔案不存在：{db_path}\n  請確認路徑，或用 --db 指定正確的 portal.db。")
    print(f"檔案大小：{db_path.stat().st_size / 1024 / 1024:.1f} MB")

    print("\n[1/2] 建立資料表（依 backend/app/models/opera_forecast.py 定義）…")
    created = create_tables(db_path)
    if created:
        for t in created:
            print(f"      + 新建 {t}")
    else:
        print("      所有資料表都已存在，略過")

    print("\n[2/2] 套用索引（add_opera_forecast_tables.sql）…")
    total, new_idx = apply_indexes(db_path)
    if new_idx:
        for i in new_idx:
            print(f"      + 新建 {i}")
    else:
        print("      所有索引都已存在，略過")
    print(f"      目前共 {total} 個預測相關索引")

    ok = verify(db_path)

    print("\n" + "=" * 60)
    if ok:
        print("  完成。接下來：")
        print("    1. 重啟後端服務")
        print("    2. 到「角色管理 → 權限設定 → 營運分析」勾選『房價預測』")
        print("    3. 到 /opera/forecast 按「重新估算係數」")
        print("    4. 到 /opera/events 建立事件月曆（展覽、連假等）")
    else:
        print("  未完成，請看上面的失敗訊息。")
    print("=" * 60)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
