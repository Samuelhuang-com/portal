"""
diagnose_hotel_di_dates.py
═══════════════════════════════════════════════════════════════════════
診斷飯店每日巡檢 inspection_date 解析失敗的記錄

執行（在 backend/ 目錄）：
    python scripts/diagnose_hotel_di_dates.py

輸出：
  1. 所有 hotel_di_inspection_batch 原始欄位（逐筆列印）
  2. 標記哪些筆 inspection_date 無法解析為日期
  3. 2026/05 月份命中 / 遺漏各幾筆
"""
from __future__ import annotations
import re, sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TARGET_YEAR  = 2026
TARGET_MONTH = 5


def _parse_date(s: str):
    """回傳 (year, month, day) 或 None"""
    s = (s or "").strip()
    if not s:
        return None
    try:
        from datetime import datetime
        d = datetime.strptime(s[:10].replace("-", "/"), "%Y/%m/%d")
        return (d.year, d.month, d.day)
    except Exception:
        return None


with engine.connect() as conn:
    rows = conn.execute(text(
        "SELECT ragic_id, sheet_key, sheet_name, inspection_date, "
        "start_time, end_time, work_hours, inspector_name "
        "FROM hotel_di_inspection_batch ORDER BY sheet_key, inspection_date"
    )).fetchall()

print(f"\n{'='*110}")
print(f" 共 {len(rows)} 筆  hotel_di_inspection_batch  原始資料")
print(f"{'='*110}\n")

COL = "{:<28} {:<8} {:<16} {:<22} {:<12} {:<8} {}"
print(COL.format("ragic_id", "sheet", "inspection_date", "start_time", "end_time", "工時", "inspector"))
print("-" * 110)

hit = []     # 可解析且符合 2026/05
miss = []    # 無法解析
wrong = []   # 可解析但非 2026/05

for r in rows:
    rid, sk, sn, insp_d, st, et, wh, inspector = (
        r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]
    )

    yd = _parse_date(insp_d)
    if yd is None:
        # double fallback: try start_time
        yd = _parse_date(st)

    if yd is None:
        tag = "❌ 無法解析"
        miss.append(r)
    elif (yd[0], yd[1]) == (TARGET_YEAR, TARGET_MONTH):
        tag = "✅ 2026/05"
        hit.append(r)
    else:
        tag = f"   {yd[0]}/{yd[1]:02d}"
        wrong.append(r)

    print(f"{rid:<28} {sk:<8} {insp_d or '(空)':<16} {st or '(空)':<22} "
          f"{et or '(空)':<12} {wh:<8} {inspector:<12}  {tag}")

print()
print("="*110)
print(f"  2026/05 命中：{len(hit)} 筆")
print(f"  其他月份：   {len(wrong)} 筆")
print(f"  ❌ 無法解析（遺漏）：{len(miss)} 筆")
print()

if miss:
    print("──── 遺漏明細 ────")
    for r in miss:
        print(f"  ragic_id={r[0]}")
        print(f"    sheet_key       = {r[1]!r}")
        print(f"    inspection_date = {r[3]!r}")
        print(f"    start_time      = {r[4]!r}")
        print(f"    end_time        = {r[5]!r}")
        print(f"    work_hours      = {r[6]!r}")
        print(f"    inspector_name  = {r[7]!r}")
        print()
