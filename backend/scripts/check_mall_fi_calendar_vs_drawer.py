"""
商場工務每日巡檢：月曆格 vs 每日巡檢表（抽屜）數字核對 —— 唯讀，不寫任何資料（2026-11-19）

目的：確認「月曆格完成率」與「每日巡檢表抽屜」是否用同一套判定。
  - 月曆格：routers/mall_facility_inspection._build_daily_calendar（用資料庫 result_status，_calc_kpi）
  - 抽屜：  services/mall_daily_inspection_sheet.item_kpi／item_status（依項目內容重新判定）

輸出（--out 目錄，預設 ./mall_fi_calendar_check_<日期>/）：
  day_compare.csv   每個頁籤 × 每一天：月曆格數字 vs 抽屜數字，標出不一致
  item_compare.csv  逐項：資料庫狀態 vs 抽屜判定不同的項目（例：數值讀數被存成 abnormal）
  終端機印出摘要

用法（在 backend 目錄執行）：
  python scripts/check_mall_fi_calendar_vs_drawer.py --year 2026 --month 11
"""
import argparse
import csv
import os
import sys
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal  # noqa: E402
from app.models.mall_facility_inspection import MallFIBatch, MallFIItem  # noqa: E402
from app.routers.mall_facility_inspection import _build_daily_calendar, _calc_kpi  # noqa: E402
from app.services.mall_daily_inspection_sheet import item_kpi, item_status  # noqa: E402


def load_month(db, year: int, month: int):
    prefix = f"{year}/{month:02d}/"
    batches = (
        db.query(MallFIBatch)
        .filter(MallFIBatch.inspection_date.like(f"{prefix}%"))
        .all()
    )
    ids = [b.ragic_id for b in batches]
    items_by_batch: dict[str, list] = {i: [] for i in ids}
    for s in range(0, len(ids), 500):
        for it in db.query(MallFIItem).filter(MallFIItem.batch_ragic_id.in_(ids[s:s + 500])).all():
            items_by_batch.setdefault(it.batch_ragic_id, []).append(it)
    return batches, items_by_batch


def pct(checked: int, total: int) -> int:
    return round(checked / total * 100) if total > 0 else 0


def main() -> None:
    ap = argparse.ArgumentParser(description="商場工務月曆格 vs 抽屜數字核對（唯讀）")
    ap.add_argument("--year", type=int, default=date.today().year)
    ap.add_argument("--month", type=int, default=date.today().month)
    ap.add_argument("--out", default=None, help="輸出目錄（預設 ./mall_fi_calendar_check_<日期>）")
    args = ap.parse_args()
    out = args.out or os.path.join(os.getcwd(), f"mall_fi_calendar_check_{date.today():%Y%m%d}")
    os.makedirs(out, exist_ok=True)

    db = SessionLocal()
    try:
        batches, items_by_batch = load_month(db, args.year, args.month)
        cal = _build_daily_calendar(args.year, args.month, db)  # 正式月曆格（唯讀查詢）

        # ── 資料庫判定（與月曆格相同）與抽屜判定，依 (頁籤, 日) 彙整 ──
        db_agg = defaultdict(lambda: {"total": 0, "checked": 0})
        dr_agg = defaultdict(lambda: {"total": 0, "checked": 0, "abnormal": 0, "pending": 0})
        for b in batches:
            day = int(b.inspection_date.split("/")[2])
            items = items_by_batch.get(b.ragic_id, [])
            k_db = _calc_kpi(items)
            db_agg[(b.sheet_key, day)]["total"] += k_db["total"]
            db_agg[(b.sheet_key, day)]["checked"] += k_db["checked"]
            k_dr = item_kpi(b.sheet_key, items)
            d = dr_agg[(b.sheet_key, day)]
            d["total"] += k_dr["total"]
            d["checked"] += k_dr["checked"]
            d["abnormal"] += k_dr["abnormal"]
            d["pending"] += k_dr["pending"]

        # ── 1) 逐日比對 ──────────────────────────────────────────────
        day_rows = []
        cat = Counter()
        for sheet in cal["sheets"]:
            key = sheet["key"]
            for day in range(1, cal["max_day"] + 1):
                cell = sheet["daily"].get(str(day), {})
                has_cal = bool(cell.get("has_record"))
                dbk = db_agg.get((key, day))
                drk = dr_agg.get((key, day))
                if not has_cal and drk is None:
                    continue
                cal_rate = int(cell.get("completion_rate", 0))
                db_rate = pct(dbk["checked"], dbk["total"]) if dbk else 0
                dr_rate = pct(drk["checked"], drk["total"]) if drk else 0
                mismatch = (not has_cal) != (drk is None) or cal_rate != dr_rate
                if cal_rate != db_rate:
                    cat["月曆格數字與重算不同（應為 0，若非 0 代表月曆格程式與本腳本不一致）"] += 1
                if mismatch:
                    if cal_rate == 100 and dr_rate < 100:
                        cat["月曆 100%／抽屜未滿"] += 1
                    elif cal_rate < 100 and dr_rate == 100:
                        cat["月曆未滿／抽屜 100%"] += 1
                    else:
                        cat["其他差異"] += 1
                day_rows.append({
                    "month": f"{args.year}-{args.month:02d}",
                    "頁籤": key,
                    "日": day,
                    "月曆格有紀錄": "Y" if has_cal else "N",
                    "抽屜有紀錄": "Y" if drk is not None else "N",
                    "月曆格完成率": cal_rate,
                    "資料庫重算完成率": db_rate,
                    "抽屜完成率": dr_rate,
                    "差異": "Y" if mismatch else "",
                    "資料庫應檢項": dbk["total"] if dbk else 0,
                    "抽屜應檢項": drk["total"] if drk else 0,
                    "資料庫已檢": dbk["checked"] if dbk else 0,
                    "抽屜已檢": drk["checked"] if drk else 0,
                    "抽屜異常": drk["abnormal"] if drk else 0,
                    "抽屜待處理": drk["pending"] if drk else 0,
                    "月曆格異常": cell.get("abnormal_count", 0),
                    "月曆格待處理": cell.get("pending_count", 0),
                })

        # ── 2) 逐項比對：資料庫 result_status vs 抽屜 item_status ──────
        item_rows = []
        pair_count = Counter()
        for b in batches:
            day = int(b.inspection_date.split("/")[2])
            for it in items_by_batch.get(b.ragic_id, []):
                db_st = it.result_status
                dr_st = item_status(b.sheet_key, it.item_name, it.result_raw, bool(it.is_note))
                if db_st != dr_st:
                    pair_count[(it.item_name, db_st, dr_st)] += 1
                    item_rows.append({
                        "month": f"{args.year}-{args.month:02d}",
                        "頁籤": b.sheet_key,
                        "日": day,
                        "場次ID": b.ragic_id,
                        "項目": it.item_name,
                        "原始值": it.result_raw,
                        "資料庫狀態": db_st,
                        "抽屜判定": dr_st,
                    })

        # ── 輸出 CSV（utf-8-sig，方便 Excel 開啟）──────────────────────
        def write_csv(name, rows):
            path = os.path.join(out, name)
            if not rows:
                open(path, "w", encoding="utf-8-sig").close()
                return path
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
            return path

        p1 = write_csv("day_compare.csv", day_rows)
        p2 = write_csv("item_compare.csv", item_rows)

        # ── 摘要 ─────────────────────────────────────────────────────
        n_mis = sum(1 for r in day_rows if r["差異"] == "Y")
        print(f"核對月份：{args.year}-{args.month:02d}　場次數：{len(batches)}　比對的（頁籤×日）：{len(day_rows)}")
        print(f"完成率不一致（月曆格 vs 抽屜）：{n_mis} 筆")
        for k, v in cat.items():
            print(f"  - {k}：{v}")
        print(f"逐項判定不同（資料庫 vs 抽屜）：{len(item_rows)} 項")
        for (name, a, b2), n in pair_count.most_common(15):
            print(f"  - {name}：資料庫={a}　抽屜={b2}　（{n} 次）")
        print(f"輸出：{p1}")
        print(f"　　　{p2}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
