"""
check_blank_vendor_id_contracts.py
────────────────────────────────────────────────────────────────────────────────
唯讀健檢腳本：找出「有廠商名稱、但 vendor_id 對不到廠商管理中任何一筆廠商」的合約。

背景（2026-07-24）：
  複製續約功能新增「原合約廠商已不在廠商管理中」提醒後，Samuel 實測發現
  COP018-2025（廠商「普迪國際有限公司」）觸發警示。追查根因：合約/廠商目前不在
  Ragic 自動同步清單內，是透過一次性批次匯入腳本 import_contracts_all.py 寫入，
  該腳本依廠商名稱字串比對回填 vendor_id，比對不到時靜默 fallback 成空字串、
  vendor_name 卻正常寫入，且完全不記錄警告 —— 導致資料庫裡可能還有其他合約
  有一樣的問題，但目前沒有清單可查。

這支腳本涵蓋兩種「廠商查無對應」的情況：
  1. vendor_id 為空字串 / NULL，但 vendor_name 有值（import_contracts_all.py 的
     silent fallback 症狀）
  2. vendor_id 有值，但這個值不存在於目前的 vendors 表（廠商後來被刪除、或
     vendor_id 寫錯/格式不符等孤兒參照）

本腳本只做查詢，不修改任何資料。

使用方式（在 backend/ 目錄下執行）：
    python scripts/check_blank_vendor_id_contracts.py
    python scripts/check_blank_vendor_id_contracts.py --csv out.csv   # 另外輸出 CSV
"""
import sys, os, argparse, csv

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.contract import Contract, Vendor

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--csv", dest="csv_path", default=None, help="另外輸出結果到 CSV 檔案")
args = parser.parse_args()

# ── DB（沿用 import_contracts_all.py 同一套 DATABASE_URL 解析方式）───────────────
_url = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
engine = create_engine(_url, connect_args={"check_same_thread": False} if "sqlite" in _url else {})
Session = sessionmaker(bind=engine)


def main():
    with Session() as db:
        vendor_ids = {v.vendor_id for v in db.query(Vendor.vendor_id).all()}
        contracts = db.query(Contract).order_by(Contract.contract_id).all()

        blank_id_rows = []      # vendor_id 為空 / NULL
        orphan_id_rows = []     # vendor_id 有值但查無對應廠商

        for c in contracts:
            vid = (c.vendor_id or "").strip()
            vname = (c.vendor_name or "").strip()
            if not vname:
                continue  # 連廠商名稱都沒有的合約不在本次排查範圍內
            if not vid:
                blank_id_rows.append(c)
            elif vid not in vendor_ids:
                orphan_id_rows.append(c)

        print(f"廠商總數：{len(vendor_ids)}　合約總數：{len(contracts)}\n")

        print(f"── vendor_id 為空、但 vendor_name 有值（共 {len(blank_id_rows)} 筆）──")
        for c in blank_id_rows:
            print(f"  {c.contract_id}\t{c.contract_name}\t廠商名稱={c.vendor_name}\t狀態={c.contract_status}")

        print(f"\n── vendor_id 有值但查無對應廠商（孤兒參照，共 {len(orphan_id_rows)} 筆）──")
        for c in orphan_id_rows:
            print(f"  {c.contract_id}\t{c.contract_name}\t廠商名稱={c.vendor_name}\tvendor_id={c.vendor_id}\t狀態={c.contract_status}")

        total = len(blank_id_rows) + len(orphan_id_rows)
        print(f"\n合計 {total} 筆合約的廠商在「廠商管理」中查無對應，複製續約時都會觸發警示。")

        if args.csv_path:
            with open(args.csv_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["合約編號", "合約名稱", "廠商名稱", "vendor_id", "問題類型", "合約狀態"])
                for c in blank_id_rows:
                    writer.writerow([c.contract_id, c.contract_name, c.vendor_name, c.vendor_id or "", "vendor_id 為空", c.contract_status])
                for c in orphan_id_rows:
                    writer.writerow([c.contract_id, c.contract_name, c.vendor_name, c.vendor_id, "vendor_id 查無對應廠商", c.contract_status])
            print(f"已輸出 CSV：{args.csv_path}")


if __name__ == "__main__":
    main()
