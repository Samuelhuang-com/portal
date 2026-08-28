"""
Phase 0 前置修正：補上 `ohip_snapshot_run.lookback_days` 欄位

背景（2026-08-28 由 check_schema_drift.py 找出）
────────────────────────────────────────────────────────────────────────────
`OhipSnapshotRun` model 有 `lookback_days` 欄位，但資料庫沒有。

原因不是「某個 _migrate_* 被略過」—— 是**從來沒有人為它寫過 migration**。
`ohip_snapshot_run` 表在 2026-08-07 由 `create_all()` 建立，之後
`lookback_days` 被加進 model，而 `create_all()` 只建缺少的**表**、
不會為既有表加**欄位**。

為什麼沒人發現：
    `ohip_snapshot_service._save_run()` 是
        try: db.add(run); db.commit()
        except Exception: db.rollback()
    刻意吞掉例外（理由是「執行紀錄寫入失敗不該讓主流程失敗」）。
    於是每天 06:00 的快照都：快照資料寫入成功、**執行紀錄靜默寫入失敗**。

實際後果（兩個）
    ① `ohip_snapshot_run` 永遠 0 筆。而這張表 model docstring 寫著
       「一定要有這張表……沒有執行紀錄的話，『這三個月的資料為什麼有缺口』
       永遠查不出來」—— 它正是那個查不出來的狀態。
    ② `sync_snapshot()` 用這張表判斷「今天是否已完成」（service 第 474 行）。
       表永遠是空的 → 判斷永遠不成立 → **每次觸發都重跑整批快照**，
       重打 OHIP API（會計費）。

本腳本只做一件事：ALTER TABLE 加上該欄位。冪等，可重複執行。
`ohip_snapshot_run` 目前 0 筆，**沒有資料風險**。

執行（每個環境各跑一次）：
    cd backend
    python scripts\\fix_snapshot_run_lookback_days.py

跑完再跑一次 check_schema_drift.py 確認全綠。
"""
from __future__ import annotations

import logging
import os
import sys

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

from sqlalchemy import inspect, text                              # noqa: E402

from app.core.database import engine                              # noqa: E402

TABLE = "ohip_snapshot_run"
COLUMN = "lookback_days"
DDL = f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} INTEGER NOT NULL DEFAULT 0"


def main() -> None:
    engine.echo = False
    print(f"DB: {engine.url}\n")

    insp = inspect(engine)
    if TABLE not in insp.get_table_names():
        print(f"⚠️  找不到資料表 {TABLE} —— 這個環境可能還沒建過快照表，"
              f"下次 create_all() 會直接建成正確版本，不需要本腳本。")
        return

    cols = {c["name"] for c in insp.get_columns(TABLE)}
    if COLUMN in cols:
        print(f"✅ {TABLE}.{COLUMN} 已存在，不需要處理。")
        return

    with engine.connect() as conn:
        n = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar_one()
        print(f"{TABLE} 目前 {n} 筆資料")
        print(f"執行：{DDL}")
        conn.execute(text(DDL))
        conn.commit()

    cols_after = {c["name"] for c in inspect(engine).get_columns(TABLE)}
    if COLUMN in cols_after:
        print(f"\n✅ 完成。{TABLE}.{COLUMN} 已新增（預設值 0）。")
        print("   → 請再跑一次 check_schema_drift.py 確認全綠。")
    else:
        print(f"\n❌ 執行完仍找不到 {COLUMN}，請把畫面訊息貼出來。")


if __name__ == "__main__":
    main()
