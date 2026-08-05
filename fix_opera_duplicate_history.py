"""
修復 OPERA History and Forecast 重複計算問題（2026-08-04）

問題
────
`opera_revenue_daily` 的版本管理業務鍵是 `(property_code, record_type, business_date)`。
History and Forecast 檔案**本身沒有飯店代碼欄位**，只能從 Departure（RESORT1）或
資料庫既有批次繼承。若第一次匯入 History 時還沒匯入過 Departure，飯店代碼就會存成
**空字串**；日後用正確代碼（例如 SUMMER）重新匯入重疊期間時，兩組資料的業務鍵不同，
**都會保持 is_current=1**，於是同一個營業日出現兩筆有效資料。

後果：**營收與房晚被重複計算**。而 ADR 與住房率因為分子分母同時放大，
看起來完全正常 —— 這也是為什麼這個問題很難從畫面上發現。

實例（Samuel 的資料，2026-08-04）：
    批次 #1  property_code=""       2024-01-01 ~ 2026-08-04
    批次 #3  property_code="SUMMER" 2023-01-01 ~ 2026-08-05
    → 946 個日期重複，總營收 232,550,101 → 實際應為 116,506,069

這支腳本做什麼
──────────────
把**飯店代碼為空白**的 `opera_revenue_daily` 資料列，在「同一個 record_type + business_date
已經有另一筆有正確代碼的有效資料」時，標記為 `is_current = 0`（不刪除，保留可追溯）。

若某個日期**只有**空白代碼那一筆（沒有正確代碼的版本），則不是重複，
腳本會改為把它的 `property_code` 補成指定的代碼，而不是把資料弄不見。

安全性
──────
  - 預設為 **dry-run**，只報告不修改；要實際執行請加 `--apply`
  - 不刪除任何資料列，只改 `is_current` 或補 `property_code`
  - 只動 `opera_revenue_daily`，不碰其他資料表
  - 執行前後都會印出總營收，方便你確認修正幅度
  - 可重複執行

用法
────
    # 先看報告（不會改任何東西）
    python fix_opera_duplicate_history.py

    # 確認無誤後實際執行
    python fix_opera_duplicate_history.py --apply

    # 指定資料庫或飯店代碼
    python fix_opera_duplicate_history.py --db C:\\Portal_Data\\portal.db --property SUMMER --apply
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"

_SQLITE_URL_RE = re.compile(r"^sqlite(\+\w+)?:///(?P<path>.*)$")


def die(msg: str) -> None:
    print("\n[錯誤] " + msg)
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
            m = _SQLITE_URL_RE.match(value.strip().strip('"').strip("'"))
            if not m:
                die("backend/.env 的 DATABASE_URL 不是 SQLite，請用 --db 指定檔案。")
            p = Path(m.group("path"))
            if not p.is_absolute():
                p = (BACKEND_DIR / p).resolve()
            return p
    die("找不到 backend/.env 的 DATABASE_URL，請用 --db 指定資料庫檔案。")


def totals(con: sqlite3.Connection) -> tuple[int, float, int]:
    row = con.execute(
        "SELECT COUNT(*), COALESCE(SUM(revenue), 0), COALESCE(SUM(sold_rooms), 0) "
        "FROM opera_revenue_daily WHERE is_current = 1 AND record_type = 'History'"
    ).fetchone()
    return int(row[0]), float(row[1]), int(row[2])


def main() -> None:
    ap = argparse.ArgumentParser(description="修復 OPERA History 重複計算")
    ap.add_argument("--db", help=r"SQLite 路徑，例如 C:\Portal_Data\portal.db")
    ap.add_argument("--property", default="", help="正確的飯店代碼；留空則自動取用最常見的非空白代碼")
    ap.add_argument("--apply", action="store_true", help="實際執行（不加就只報告）")
    args = ap.parse_args()

    db_path = resolve_db_path(args.db)
    print("=" * 64)
    print("  OPERA History 重複計算修復")
    print("=" * 64)
    print(f"\n資料庫：{db_path}")
    if not db_path.exists():
        die(f"資料庫不存在：{db_path}")

    con = sqlite3.connect(str(db_path))
    try:
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "opera_revenue_daily" not in tables:
            die("找不到 opera_revenue_daily，請先執行 apply_opera_migration.py。")

        # ── 現況 ──────────────────────────────────────────────────────────
        print("\n── 目前各飯店代碼的有效資料列 ──")
        codes = con.execute(
            "SELECT property_code, COUNT(*) FROM opera_revenue_daily "
            "WHERE is_current = 1 GROUP BY property_code ORDER BY 2 DESC"
        ).fetchall()
        for pc, n in codes:
            print(f"  {'（空白）' if not pc else pc:12} {n:>6,} 列")

        target = args.property or next((pc for pc, _ in codes if pc), "")
        if not target:
            die("資料庫裡沒有任何非空白的飯店代碼，無法判斷正確代碼。請用 --property 指定。")
        print(f"\n正確代碼判定為：{target}")

        blank = con.execute(
            "SELECT COUNT(*) FROM opera_revenue_daily WHERE is_current = 1 AND property_code = ''"
        ).fetchone()[0]
        if not blank:
            print("\n[OK] 沒有飯店代碼空白的有效資料，不需要修復。")
            return

        dup = con.execute(
            "SELECT COUNT(*) FROM opera_revenue_daily a "
            "WHERE a.is_current = 1 AND a.property_code = '' AND EXISTS ("
            "  SELECT 1 FROM opera_revenue_daily b WHERE b.is_current = 1"
            "    AND b.property_code = ? AND b.record_type = a.record_type"
            "    AND b.business_date = a.business_date)",
            (target,),
        ).fetchone()[0]
        orphan = blank - dup

        rows_before, rev_before, sold_before = totals(con)
        print(f"\n空白代碼的有效資料：{blank:,} 列")
        print(f"  其中與 {target} 重複（要下架）：{dup:,} 列")
        print(f"  其中沒有對應版本（要補代碼）：{orphan:,} 列")
        print(f"\n修復前 History：{rows_before:,} 列　營收 {rev_before:,.0f}　已售房晚 {sold_before:,}")

        if not args.apply:
            print("\n" + "=" * 64)
            print("  這是 dry-run，尚未修改任何資料。")
            print("  確認以上數字無誤後，加上 --apply 重新執行：")
            print("      python fix_opera_duplicate_history.py --apply")
            print("=" * 64)
            return

        # ── 實際修復 ──────────────────────────────────────────────────────
        con.execute(
            "UPDATE opera_revenue_daily SET is_current = 0 "
            "WHERE is_current = 1 AND property_code = '' AND EXISTS ("
            "  SELECT 1 FROM opera_revenue_daily b WHERE b.is_current = 1"
            "    AND b.property_code = ? AND b.record_type = opera_revenue_daily.record_type"
            "    AND b.business_date = opera_revenue_daily.business_date)",
            (target,),
        )
        con.execute(
            "UPDATE opera_revenue_daily SET property_code = ? "
            "WHERE is_current = 1 AND property_code = ''",
            (target,),
        )
        con.commit()

        rows_after, rev_after, sold_after = totals(con)
        print(f"\n修復後 History：{rows_after:,} 列　營收 {rev_after:,.0f}　已售房晚 {sold_after:,}")
        print(f"  減少 {rows_before - rows_after:,} 列　營收 −{rev_before - rev_after:,.0f}"
              f"　房晚 −{sold_before - sold_after:,}")

        still = con.execute(
            "SELECT COUNT(*) FROM (SELECT 1 FROM opera_revenue_daily WHERE is_current = 1 "
            "GROUP BY record_type, business_date HAVING COUNT(*) > 1)"
        ).fetchone()[0]
        print(f"\n仍有重複的營業日：{still}", "✅" if still == 0 else "❌ 請回報")

        print("\n" + "=" * 64)
        print("  完成。舊資料只被標記為非目前有效，並未刪除，隨時可追溯。")
        print("  請重新整理營運分析頁面確認數字。")
        print("=" * 64)
    finally:
        con.close()


if __name__ == "__main__":
    main()
