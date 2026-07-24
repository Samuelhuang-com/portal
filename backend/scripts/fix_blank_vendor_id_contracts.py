"""
fix_blank_vendor_id_contracts.py
────────────────────────────────────────────────────────────────────────────────
把「有廠商名稱、但 vendor_id 空白／查無對應」的合約，依廠商名稱自動比對回填 vendor_id。

背景（2026-07-24）：
  check_blank_vendor_id_contracts.py 掃出 35 筆合約（COP0015-2025、COP018-2025 等，
  全部「生效中」）vendor_id 為空、只有 vendor_name，都是同一批歷史 Excel 匯入
  （import_contracts_all.py 的 silent fallback）造成。逐筆用 App 的「編輯廠商」
  功能手動修太慢，改成寫這支腳本：依 vendor_name 精確比對 vendors 表，找得到「唯一
  一筆」就直接回填 vendor_id；找不到或名稱重複（比對到多筆）的一律跳過、不猜測，
  留給人工用 App 的編輯功能處理。

安全設計（預設不寫入資料庫）：
  - 不加 --apply：只印出「比對結果」，不改任何資料，先讓你確認 mapping 對不對
  - 加 --apply：對「唯一比對成功」的合約才真的執行 UPDATE 並 commit；
    「查無此廠商」「名稱重複比對到多筆」永遠不會自動套用，只會列出來
  - vendor_name 完全不動，只補 vendor_id（vendor_name 本身已經是對的，不需要改）

比對規則：
  - 先比對「完全相同」（兩邊 strip 空白後）
  - 全形/半形括號、公司名稱裡的「(股)」「（股）」等寫法不一致時不會硬猜，會歸類到
    「查無比對」，避免猜錯把合約掛到錯的廠商上

使用方式（在 backend/ 目錄下執行）：
    python scripts/fix_blank_vendor_id_contracts.py                # 只看比對結果，不寫入
    python scripts/fix_blank_vendor_id_contracts.py --csv plan.csv # 順便輸出比對結果 CSV
    python scripts/fix_blank_vendor_id_contracts.py --apply        # 對唯一比對成功的合約實際寫入
"""
import sys, os, argparse, csv

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from collections import defaultdict
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.contract import Contract, Vendor

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--csv", dest="csv_path", default=None, help="輸出比對結果到 CSV 檔案")
parser.add_argument("--apply", action="store_true", help="實際寫入資料庫（預設只顯示比對結果、不寫入）")
args = parser.parse_args()

# ── DB（沿用其他 scripts 同一套 DATABASE_URL 解析方式）───────────────────────────
_url = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
engine = create_engine(_url, connect_args={"check_same_thread": False} if "sqlite" in _url else {})
Session = sessionmaker(bind=engine)


def main():
    with Session() as db:
        # 廠商名稱 → vendor_id 清單（同名可能不只一筆，所以先收集成 list）
        name_to_ids = defaultdict(list)
        for v in db.query(Vendor.vendor_id, Vendor.vendor_name).all():
            name_to_ids[(v.vendor_name or "").strip()].append(v.vendor_id)

        contracts = db.query(Contract).order_by(Contract.contract_id).all()

        # 待處理：vendor_id 空白，或 vendor_id 有值但查無對應廠商
        vendor_ids = {v.vendor_id for v in db.query(Vendor.vendor_id).all()}
        targets = []
        for c in contracts:
            vid = (c.vendor_id or "").strip()
            vname = (c.vendor_name or "").strip()
            if not vname:
                continue
            if not vid or vid not in vendor_ids:
                targets.append(c)

        fixable, ambiguous, not_found = [], [], []
        for c in targets:
            matches = name_to_ids.get((c.vendor_name or "").strip(), [])
            if len(matches) == 1:
                fixable.append((c, matches[0]))
            elif len(matches) > 1:
                ambiguous.append((c, matches))
            else:
                not_found.append(c)

        print(f"待處理合約共 {len(targets)} 筆（vendor_id 空白或查無對應廠商）\n")

        print(f"── 可自動比對回填（廠商名稱唯一比對成功，共 {len(fixable)} 筆）──")
        for c, vid in fixable:
            print(f"  {c.contract_id}\t{c.contract_name}\t廠商名稱={c.vendor_name}\t→ 比對到 vendor_id={vid}")

        print(f"\n── 名稱重複、比對到多筆廠商，需人工確認（共 {len(ambiguous)} 筆）──")
        for c, vids in ambiguous:
            print(f"  {c.contract_id}\t{c.contract_name}\t廠商名稱={c.vendor_name}\t候選 vendor_id={vids}")

        print(f"\n── 廠商管理中完全查無此名稱，需人工到 App 編輯選擇（共 {len(not_found)} 筆）──")
        for c in not_found:
            print(f"  {c.contract_id}\t{c.contract_name}\t廠商名稱={c.vendor_name}")

        if args.csv_path:
            with open(args.csv_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["合約編號", "合約名稱", "廠商名稱", "比對結果", "候選/回填 vendor_id"])
                for c, vid in fixable:
                    writer.writerow([c.contract_id, c.contract_name, c.vendor_name, "可自動回填", vid])
                for c, vids in ambiguous:
                    writer.writerow([c.contract_id, c.contract_name, c.vendor_name, "名稱重複需人工確認", "/".join(vids)])
                for c in not_found:
                    writer.writerow([c.contract_id, c.contract_name, c.vendor_name, "查無此廠商需人工處理", ""])
            print(f"\n已輸出比對結果 CSV：{args.csv_path}")

        if not args.apply:
            print(f"\n目前是「只顯示比對結果」模式，尚未寫入任何資料。"
                  f"\n確認上面「可自動比對回填」清單沒問題後，重新執行加上 --apply 才會真的寫入：")
            print(f"    python scripts/fix_blank_vendor_id_contracts.py --apply")
            return

        # ── 實際寫入：只處理「唯一比對成功」的合約 ─────────────────────────
        if not fixable:
            print("\n沒有可自動回填的合約，未執行任何寫入。")
            return

        now = datetime.now()
        for c, vid in fixable:
            c.vendor_id = vid
            c.updated_at = now
        db.commit()
        print(f"\n✅ 已寫入 {len(fixable)} 筆合約的 vendor_id（vendor_name 未變動）。"
              f"\n名稱重複（{len(ambiguous)} 筆）與查無廠商（{len(not_found)} 筆）未自動處理，"
              f"請到 App 合約明細「編輯」手動選擇正確廠商。")


if __name__ == "__main__":
    main()
