#!/usr/bin/env python3
"""
每日數值登錄（hotel-meter-readings）診斷工具
=========================================
執行方式（在 portal/ 目錄下）：

  python diagnose_hmr.py           # 只查 DB
  python diagnose_hmr.py --fetch   # 也嘗試從 Ragic 抓第一筆看欄位名稱

輸出：
  1. DB 目前有哪些 hotel_mr_batch 記錄
  2. 若加 --fetch：直接呼叫 Ragic API，印出回傳的欄位名稱
"""

import os
import sys
import pathlib

# ── 路徑 & venv 設定（與 sync_tool.py 保持一致）────────────────────────────
_HERE    = pathlib.Path(__file__).resolve().parent
_BACKEND = _HERE / "backend"
os.chdir(_BACKEND)

for venv_name in ("venv312", "venv311", "venv", ".venv"):
    sp = _BACKEND / venv_name / "Lib" / "site-packages"
    if sp.exists():
        sys.path.insert(0, str(sp))
        break

if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# ── Import ──────────────────────────────────────────────────────────────────
try:
    from app.core.config import settings
    from app.core.database import engine
    from app.models.hotel_meter_readings import HotelMRBatch, HotelMRReading
    from sqlalchemy.orm import Session
    from sqlalchemy import text
except ImportError as e:
    print(f"[ERROR] Import 失敗：{e}")
    print("請確認在 portal/ 目錄下執行，且 venv 已安裝套件。")
    sys.exit(1)

# ============================================================================
# 1. DB 診斷
# ============================================================================

print("=" * 60)
print("▶ DB 診斷")
print(f"  DB URL  : {settings.DATABASE_URL}")
print("=" * 60)

with Session(engine) as db:
    # ── hotel_mr_batch 欄位結構 ────────────────────────────────────────────
    try:
        result = db.execute(text("PRAGMA table_info(hotel_mr_batch)"))
        cols = [(r[1], r[2]) for r in result.fetchall()]
        print(f"\n[hotel_mr_batch] 欄位清單（共{len(cols)}個）：")
        for col_name, col_type in cols:
            print(f"  {col_name:20s}  {col_type}")
    except Exception as e:
        print(f"[hotel_mr_batch] 查詢失敗：{e}")

    # ── hotel_mr_batch 資料筆數 ────────────────────────────────────────────
    print()
    for sheet_key in ("building-electric", "mall-ac-electric", "tenant-electric", "tenant-water"):
        try:
            total   = db.query(HotelMRBatch).filter(HotelMRBatch.sheet_key == sheet_key).count()
            no_date = db.query(HotelMRBatch).filter(
                HotelMRBatch.sheet_key == sheet_key,
                HotelMRBatch.record_date == "",
            ).count()
            has_date = total - no_date
            print(f"  [{sheet_key:25s}]  總計={total}  有日期={has_date}  缺日期={no_date}")
        except Exception as e:
            print(f"  [{sheet_key}] 查詢失敗：{e}")

    # ── 最近 5 筆記錄（任意 sheet_key）───────────────────────────────────
    print()
    try:
        recent = db.query(HotelMRBatch).order_by(HotelMRBatch.synced_at.desc()).limit(10).all()
        if recent:
            print(f"[最近同步的 10 筆 hotel_mr_batch]")
            for b in recent:
                print(f"  ragic_id={b.ragic_id}  date='{b.record_date}'  "
                      f"recorder='{b.recorder_name}'  start='{b.start_time}'  "
                      f"end='{b.end_time}'  hours='{b.work_hours}'  synced_at={b.synced_at}")
        else:
            print("[hotel_mr_batch] ⚠ 資料表是空的！請先執行同步。")
    except Exception as e:
        print(f"[最近記錄] 查詢失敗：{e}")

    # ── hotel_mr_reading ──────────────────────────────────────────────────
    print()
    try:
        reading_count = db.query(HotelMRReading).count()
        print(f"[hotel_mr_reading]  總筆數 = {reading_count}")
    except Exception as e:
        print(f"[hotel_mr_reading] 查詢失敗（可能資料表不存在）：{e}")


# ============================================================================
# 2. Ragic API 診斷（--fetch 時才執行）
# ============================================================================

if "--fetch" not in sys.argv:
    print()
    print("提示：加上 --fetch 參數可直接測試 Ragic API 連線並印出欄位名稱。")
    print("  例：python diagnose_hmr.py --fetch")
    sys.exit(0)

print()
print("=" * 60)
print("▶ Ragic API 診斷（--fetch 模式）")
print("=" * 60)

import asyncio
import httpx

HMR_SERVER_URL = getattr(settings, "RAGIC_HDI_SERVER_URL", "ap12.ragic.com")
HMR_ACCOUNT    = getattr(settings, "RAGIC_HDI_ACCOUNT",    "soutlet001")
API_KEY        = settings.RAGIC_API_KEY
NAMING         = getattr(settings, "RAGIC_NAMING", "")
VERSION        = getattr(settings, "RAGIC_API_VERSION", "")

print(f"  server  : {HMR_SERVER_URL}")
print(f"  account : {HMR_ACCOUNT}")
print(f"  api_key : {API_KEY[:12]}... (前12字元)")
print(f"  naming  : '{NAMING}'")
print(f"  version : '{VERSION}'")
print()

SHEET_PATHS = {
    "building-electric": "hotel-routine-inspection/11",
    "tenant-electric":   "hotel-routine-inspection/14",
}

async def fetch_first_row(sheet_key: str, sheet_path: str):
    url = f"https://{HMR_SERVER_URL}/{HMR_ACCOUNT}/{sheet_path}"
    params = {"api": "", "limit": 1, "naming": NAMING}
    if VERSION:
        params["version"] = VERSION
    headers = {
        "Authorization": f"Basic {API_KEY}",
        "Accept": "application/json",
    }
    print(f"[{sheet_key}] GET {url}")
    try:
        async with httpx.AsyncClient(timeout=20.0, verify=settings.RAGIC_VERIFY_SSL) as client:
            resp = await client.get(url, headers=headers, params=params)
        print(f"  HTTP status : {resp.status_code}")
        if resp.status_code != 200:
            print(f"  body (前500字) : {resp.text[:500]}")
            return
        data = resp.json()
        # Ragic 回傳 dict，key 為 record ID（數字）
        record_keys = [k for k in data.keys() if k.lstrip("-").isdigit()]
        print(f"  記錄筆數（本次 limit=1）: {len(record_keys)}")
        if not record_keys:
            print("  ⚠ 沒有記錄（Ragic 此 Sheet 目前是空的）")
            return
        first_id  = record_keys[0]
        first_row = data[first_id]
        all_keys      = list(first_row.keys())
        visible_keys  = [k for k in all_keys if not str(k).startswith("_") and not str(k).isdigit()]
        numeric_keys  = [k for k in all_keys if str(k).lstrip("-").isdigit()]
        print(f"  第一筆 ID   : {first_id}")
        print(f"  欄位總數     : {len(all_keys)} （文字key={len(visible_keys)} 數字key={len(numeric_keys)}）")
        print(f"  文字欄位名稱 : {visible_keys}")
        print()
        # 印出每個文字欄位的值
        for k in visible_keys[:20]:
            v = first_row.get(k, "")
            print(f"    '{k}' = '{v}'")
    except Exception as e:
        print(f"  ❌ 例外：{e}")

async def main():
    for sheet_key, sheet_path in SHEET_PATHS.items():
        await fetch_first_row(sheet_key, sheet_path)
        print()

asyncio.run(main())
