"""
backfill_contract_renewed_status.py
────────────────────────────────────────────────────────────────────────────────
一次性回補：把「已經有續約新合約生效」的原合約，狀態從「生效中／即將到期」改為「已續約」。

背景（2026-09-30，CHANGELOG [2.10.80]）：
  Samuel 裁示複製續約的新合約「生效」時，原合約自動改為「已續約」。
  但這個連動只對上線之後的核准／狀態變更有效，上線前就已經生效的續約新合約，
  它的原合約還停在「生效中／即將到期」，會繼續出現在到期預警、行事曆，
  也會跟新合約重複計入廠商金額統計與預算分析。這支腳本補這一段舊資料。

判定規則（與 ContractService.mark_source_renewed 同一套口徑）：
  - 新合約：renewed_from_contract_id 有值，且狀態為「生效中／即將到期／已續約」
    （已續約＝它自己也生效過、之後又被下一版取代，同樣代表它曾經生效）
  - 原合約：目前狀態為「生效中／即將到期」→ 改成「已續約」
  - 同一份原合約被複製多次（分支）時，只要有任一份新合約生效就改
  - 其他情況一律不動，只列出來：
      · 新合約還在草稿／審核中 → 之後核准時系統會自動處理，不需回補
      · 新合約已終止 → 續約沒成立或已結束，原合約怎麼處理需人工判斷
      · 原合約是草稿／審核中／已終止 → 狀態不在可轉換範圍，不動

安全設計（預設不寫入資料庫）：
  - 不加 --apply：只印出清單，不改任何資料
  - 加 --apply：只對「將改為已續約」清單執行 UPDATE（contract_status、updated_at），一次 commit
  - 可重複執行：已經是「已續約」的原合約不會再被列入

使用方式（在 backend/ 目錄下執行）：
    # 測試區
    python scripts\\backfill_contract_renewed_status.py                 # 只看清單
    python scripts\\backfill_contract_renewed_status.py --csv plan.csv  # 順便輸出 CSV
    python scripts\\backfill_contract_renewed_status.py --apply         # 實際寫入

    # 正式區（直譯器不同，見 pg_fix_sequences.py 的說明）
    py -3.11 scripts\\backfill_contract_renewed_status.py
    py -3.11 scripts\\backfill_contract_renewed_status.py --apply
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
from app.models.contract import Contract

CHILD_EFFECTIVE = ("生效中", "即將到期", "已續約")
SOURCE_CONVERTIBLE = ("生效中", "即將到期")
RENEWED = "已續約"

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--csv", dest="csv_path", default=None, help="輸出清單到 CSV 檔案")
parser.add_argument("--apply", action="store_true", help="實際寫入資料庫（預設只顯示清單、不寫入）")
args = parser.parse_args()

# ── DB（沿用其他 scripts 同一套 DATABASE_URL 解析方式）───────────────────────────
_url = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
engine = create_engine(_url, connect_args={"check_same_thread": False} if "sqlite" in _url else {})
Session = sessionmaker(bind=engine)


def _fmt(c):
    return f"{c.contract_id}「{c.contract_name}」[{c.contract_status}] {c.start_date}～{c.end_date}"


def main():
    with Session() as db:
        children = (
            db.query(Contract)
            .filter(Contract.renewed_from_contract_id.isnot(None),
                    Contract.renewed_from_contract_id != "")
            .order_by(Contract.contract_id)
            .all()
        )
        by_source = defaultdict(list)
        for ch in children:
            by_source[ch.renewed_from_contract_id].append(ch)

        sources = {
            c.contract_id: c
            for c in db.query(Contract).filter(Contract.contract_id.in_(list(by_source.keys()))).all()
        } if by_source else {}

        to_update, pending, child_ended, src_other, src_missing = [], [], [], [], []
        for src_id, chs in sorted(by_source.items()):
            src = sources.get(src_id)
            if not src:
                src_missing.append((src_id, chs))
                continue
            effective = [ch for ch in chs if ch.contract_status in CHILD_EFFECTIVE]
            if src.contract_status == RENEWED:
                continue  # 已處理過
            if effective:
                if src.contract_status in SOURCE_CONVERTIBLE:
                    to_update.append((src, effective))
                else:
                    src_other.append((src, effective))
            elif any(ch.contract_status in ("草稿", "審核中") for ch in chs):
                pending.append((src, chs))
            else:
                child_ended.append((src, chs))

        print(f"有續約來源的新合約共 {len(children)} 筆，對應原合約 {len(by_source)} 份\n")

        print(f"── 將改為「已續約」（共 {len(to_update)} 份）──")
        for src, effs in to_update:
            print(f"  原合約 {_fmt(src)}")
            for ch in effs:
                print(f"      └ 已生效的新合約 {_fmt(ch)}")

        print(f"\n── 新合約尚在草稿／審核中，之後核准時會自動處理，不需回補（共 {len(pending)} 份）──")
        for src, chs in pending:
            print(f"  原合約 {_fmt(src)} ← " + "、".join(f"{c.contract_id}[{c.contract_status}]" for c in chs))

        print(f"\n── 新合約都已終止，原合約需人工判斷（共 {len(child_ended)} 份）──")
        for src, chs in child_ended:
            print(f"  原合約 {_fmt(src)} ← " + "、".join(f"{c.contract_id}[{c.contract_status}]" for c in chs))

        print(f"\n── 新合約已生效，但原合約狀態不是生效中／即將到期，不動（共 {len(src_other)} 份）──")
        for src, effs in src_other:
            print(f"  原合約 {_fmt(src)} ← " + "、".join(f"{c.contract_id}[{c.contract_status}]" for c in effs))

        if src_missing:
            print(f"\n── 續約來源編號查無合約（共 {len(src_missing)} 筆，資料異常，請人工確認）──")
            for src_id, chs in src_missing:
                print(f"  來源 {src_id} ← " + "、".join(c.contract_id for c in chs))

        if args.csv_path:
            with open(args.csv_path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["分類", "原合約編號", "原合約名稱", "原合約狀態", "新合約（狀態）"])
                for label, rows in (("將改為已續約", to_update), ("新合約待核准", pending),
                                    ("新合約已終止", child_ended), ("原合約狀態不符", src_other)):
                    for src, chs in rows:
                        w.writerow([label, src.contract_id, src.contract_name, src.contract_status,
                                    "、".join(f"{c.contract_id}({c.contract_status})" for c in chs)])
                for src_id, chs in src_missing:
                    w.writerow(["來源查無合約", src_id, "", "", "、".join(c.contract_id for c in chs)])
            print(f"\n已輸出 CSV：{args.csv_path}")

        if not args.apply:
            print("\n目前是「只顯示清單」模式，尚未寫入任何資料。"
                  "\n確認「將改為已續約」清單沒問題後，加上 --apply 重新執行才會寫入。")
            return

        if not to_update:
            print("\n沒有需要回補的原合約，未執行任何寫入。")
            return

        now = datetime.now()
        for src, _ in to_update:
            src.contract_status = RENEWED
            src.updated_at = now
        db.commit()
        print(f"\n✅ 已將 {len(to_update)} 份原合約改為「已續約」。其他分類未變動。")


if __name__ == "__main__":
    main()
