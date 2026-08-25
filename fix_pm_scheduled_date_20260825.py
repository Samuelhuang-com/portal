# -*- coding: utf-8 -*-
"""
週期保養排定日期殘留清理（2026-08-25）
=====================================

背景
----
2026-07-23（commit 7918a62）以前，商場例行維護的「產生排程」會在 Ragic 沒填排定
日期時，用 exec_months 公式推算一個「該月 1 號（MM/01）」寫進 mall_pm_schedule；
全棟例行維護則一直到 2026-08-25 本次修正前都還在這樣做。

三張排程表（mall_pm_schedule / pm_schedule / full_bldg_pm_schedule）是 Portal 端的
排程副本，全站沒有任何清除機制。因此：

  * Ragic 上把排定日期刪掉 → 批次項目（*_batch_item）會跟著清空
  * 但排程表仍留著舊值 → 年度計劃表顯示 Ragic 上根本不存在的日期，還可能算成逾期紅點

2026-08-25 已修正顯示層（年度計劃表改以 Ragic 為單一真實來源），但 Dashboard、月曆、
逾期清單等仍直接讀排程表，因此殘留值必須一併清乾淨。

本腳本做什麼
------------
逐筆比對排程表與對應批次項目的 scheduled_date，把不一致的排程記錄更新成 Ragic 現況
（含清空）。同時統一正規化為補零的 "MM/DD"。

保護規則（不動的資料）
----------------------
  * portal_edited_at IS NOT NULL  → Portal 端人工調整過，視為刻意覆寫，跳過
  * is_completed = 1              → 已完成的歷史記錄，跳過
  * 找不到對應批次項目的孤兒記錄  → 只計數回報，不刪除

用法
----
    python fix_pm_scheduled_date_20260825.py              # 預覽（預設，不寫入）
    python fix_pm_scheduled_date_20260825.py --apply      # 實際執行（自動備份 DB）
    python fix_pm_scheduled_date_20260825.py --db D:/portal_data/portal.db --apply

執行完請重跑一次三個模組的 Ragic 同步，或在 Portal 上按「產生排程」，確認數字正確。
"""

import argparse
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime

# (中文名稱, 排程表, 批次項目表)
MODULES = [
    ("商場例行維護", "mall_pm_schedule",      "mall_pm_batch_item"),
    ("飯店週期保養", "pm_schedule",           "pm_batch_item"),
    ("全棟例行維護", "full_bldg_pm_schedule", "full_bldg_pm_batch_item"),
]


def normalize_sched_date(raw):
    """排定日期正規化為補零的 'MM/DD'；無法解析時原樣回傳，不猜測。"""
    if not raw:
        return ""
    parts = str(raw).strip().split("/")
    try:
        if len(parts) == 3:
            return "%02d/%02d" % (int(parts[1]), int(parts[2]))
        if len(parts) == 2:
            return "%02d/%02d" % (int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return str(raw)
    return str(raw)


def resolve_db_path(explicit):
    if explicit:
        return explicit
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("#") or not line.startswith("DATABASE_URL"):
                    continue
                m = re.search(r"sqlite:/+(.+)", line)
                if m:
                    return m.group(1).strip()
    return None


def table_exists(conn, name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def process(conn, label, sched_table, item_table, apply_changes):
    if not table_exists(conn, sched_table) or not table_exists(conn, item_table):
        print("  [略過] %s：找不到資料表（%s / %s）" % (label, sched_table, item_table))
        return 0

    items = {
        r["ragic_id"]: (r["scheduled_date"] or "")
        for r in conn.execute(
            "SELECT ragic_id, scheduled_date FROM %s" % item_table
        )
    }

    rows = conn.execute(
        "SELECT id, year_month, item_ragic_id, task_name, scheduled_date, "
        "       is_completed, portal_edited_at "
        "FROM %s ORDER BY year_month, id" % sched_table
    ).fetchall()

    changed, skipped_edited, skipped_done, orphans, already_ok = [], 0, 0, 0, 0

    for r in rows:
        if r["portal_edited_at"] is not None:
            skipped_edited += 1
            continue
        if r["is_completed"]:
            skipped_done += 1
            continue
        if r["item_ragic_id"] not in items:
            orphans += 1
            continue

        current = (r["scheduled_date"] or "").strip()
        target = normalize_sched_date(items[r["item_ragic_id"]])
        if current == target:
            already_ok += 1
            continue
        changed.append((r["id"], r["year_month"], r["task_name"], current, target))

    print("  %s（%s）" % (label, sched_table))
    print("    總筆數 %d｜需更新 %d｜已正確 %d｜人工調整跳過 %d｜已完成跳過 %d｜孤兒記錄 %d"
          % (len(rows), len(changed), already_ok, skipped_edited, skipped_done, orphans))

    for sid, ym, name, cur, tgt in changed[:15]:
        print("      %s  %-28s  %-7s -> %s"
              % (ym, (name or "")[:28], cur or "(空)", tgt or "(清空)"))
    if len(changed) > 15:
        print("      ...（其餘 %d 筆未列出）" % (len(changed) - 15))

    if apply_changes and changed:
        conn.executemany(
            "UPDATE %s SET scheduled_date = ? WHERE id = ?" % sched_table,
            [(tgt, sid) for sid, _ym, _n, _c, tgt in changed],
        )
        print("    已更新 %d 筆" % len(changed))

    return len(changed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", help="portal.db 路徑（預設讀 backend/.env 的 DATABASE_URL）")
    ap.add_argument("--apply", action="store_true", help="實際寫入（不加則僅預覽）")
    args = ap.parse_args()

    db_path = resolve_db_path(args.db)
    if not db_path or not os.path.exists(db_path):
        print("找不到資料庫：%s" % (db_path or "(未指定，且 backend/.env 無法解析)"))
        print("請用 --db 明確指定，例如：--db C:/portal_data/portal.db")
        sys.exit(1)

    print("資料庫：%s" % db_path)
    print("模式：%s\n" % ("實際執行（會寫入）" if args.apply else "預覽（不寫入）"))

    if args.apply:
        backup = "%s.bak_%s" % (db_path, datetime.now().strftime("%Y%m%d_%H%M%S"))
        shutil.copy2(db_path, backup)
        print("已備份：%s\n" % backup)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    total = 0
    try:
        for label, sched_table, item_table in MODULES:
            total += process(conn, label, sched_table, item_table, args.apply)
            print("")
        if args.apply:
            conn.commit()
    finally:
        conn.close()

    print("合計需更新 %d 筆。" % total)
    if total and not args.apply:
        print("確認無誤後，加上 --apply 重跑一次即可實際寫入。")


if __name__ == "__main__":
    main()
