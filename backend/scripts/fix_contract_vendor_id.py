"""
把 `contracts.vendor_id` 的空字串轉成 NULL

背景（2026-08-29，PostgreSQL 遷移的前置檢查抓到）
────────────────────────────────────────────────────────────────────────────
`contracts.vendor_id → vendors.vendor_id` 有一批孤兒，值**全部是 `''`**。

一開始誤判為「廠商被刪掉」，追查後才確認**不是**：
    · `ondelete=RESTRICT` 本來就擋得住刪除
    · 這些合約是**早期用 Excel 匯入的**，當時只有廠商名稱文字，
      根本沒有對應的廠商編號 —— 使用者確認「本來就沒連結」

⚠️⚠️ **所以問題不在資料，在 model 說謊。**
   原本宣告 `nullable=False, default=""`，於是「沒填」被存成空字串。
   那等於宣稱「連到一個 `vendor_id = ''` 的廠商」，而那個廠商不存在：

   | | SQLite | PostgreSQL |
   |---|---|---|
   | `vendor_id = ''` | 照收（沒開 `PRAGMA foreign_keys`） | **拒收**（`violates foreign key constraint`）|
   | `vendor_id IS NULL` | 照收 | **照收** —— NULL 不參與外鍵檢查 |

   **外鍵欄位的「沒有值」就該是 NULL。** model 已改為 `nullable=True`
   （見 `app/models/contract.py`），本腳本把既有的 `''` 轉成 NULL。

改完之後
    · 這張表的外鍵孤兒歸零
    · **外鍵約束可以保留** —— 不必再用 `pg_migrate_pilot.py --allow-orphans`
    · 語意正確：NULL ＝ 未連結廠商主檔

⚠️ 只轉 `''`，**不碰任何有值的 `vendor_id`**。
⚠️ 預設唯讀。要實際修改必須加 `--fix`。
⚠️ 動手前請先複製一份資料庫檔案。

執行：
    cd backend
    py -3.12 scripts\\fix_contract_vendor_id.py          # 只看不改
    py -3.12 scripts\\fix_contract_vendor_id.py --fix    # 實際轉換
"""
from __future__ import annotations

import logging
import os
import sys

# ⚠️ 輸出強制 UTF-8：導向檔案時 Python 會改用 cp950，emoji 編不進去會整支中斷。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

from sqlalchemy import inspect, text                              # noqa: E402


def main() -> int:
    do_fix = "--fix" in sys.argv
    from app.core.database import engine
    engine.echo = False

    print("=" * 78)
    print("  contracts.vendor_id：空字串 → NULL")
    print("=" * 78)
    print(f"  {engine.url}\n")

    # ⚠️ 先確認 DB 的欄位真的已經可為 NULL（model 改了但 migration 沒跑的話會失敗）
    cols = {c["name"]: c for c in inspect(engine).get_columns("contracts")}
    if cols["vendor_id"]["nullable"] is False:
        print("""  ❌ 資料庫的 `contracts.vendor_id` 還是 NOT NULL，不能轉。

     model 已經改成 nullable，但**資料庫還沒跟上**。先跑：
         py -3.12 -m alembic upgrade head

     ⚠️ 這是刻意的順序 —— 先放寬欄位，才能寫 NULL 進去。
""")
        return 2

    with engine.connect() as c:
        total = c.execute(text("SELECT COUNT(*) FROM contracts")).scalar_one()
        n = c.execute(text("SELECT COUNT(*) FROM contracts WHERE vendor_id = ''")).scalar_one()
        linked = c.execute(text(
            "SELECT COUNT(*) FROM contracts WHERE vendor_id IS NOT NULL AND vendor_id <> ''"
        )).scalar_one()
        already = c.execute(text(
            "SELECT COUNT(*) FROM contracts WHERE vendor_id IS NULL")).scalar_one()

        if not n:
            print(f"  ✅ 沒有空字串的 vendor_id（全表 {total} 張，"
                  f"已連結 {linked}、未連結 {already}）\n")
            return 0

        print(f"  全表 {total} 張合約：")
        print(f"    已連結廠商主檔      {linked:>4} 張")
        print(f"    vendor_id = ''      {n:>4} 張  ← 要轉成 NULL")
        print(f"    已經是 NULL         {already:>4} 張\n")
        rows = c.execute(text(
            "SELECT contract_name, vendor_name FROM contracts "
            "WHERE vendor_id = '' ORDER BY vendor_name LIMIT 12")).all()
        print("  要轉換的（廠商名稱**保留不動**，只有編號欄位變 NULL）：")
        for name, vendor in rows:
            print(f"    {(vendor or '（空白）')[:24]:<26} {name}")
        if n > 12:
            print(f"    …（另外 {n - 12} 張）")

    if not do_fix:
        print("""
  （唯讀模式，未修改任何資料）
  ⚠️ 先複製一份資料庫檔案當備份，再加 --fix 執行。
""")
        return 1

    with engine.connect() as c:
        done = c.execute(text(
            "UPDATE contracts SET vendor_id = NULL WHERE vendor_id = ''")).rowcount
        c.commit()
        left = c.execute(text("SELECT COUNT(*) FROM contracts WHERE vendor_id = ''")).scalar_one()
        after = c.execute(text("SELECT COUNT(*) FROM contracts")).scalar_one()

    print(f"\n  ✅ 已轉換 {done} 張；剩餘空字串 {left} 張")
    print(f"  ✅ 合約總數 {after} 張（應與轉換前相同）")
    print("""
  接著：
    py -3.12 scripts\\pg_show_orphans.py                ← 應顯示「沒有外鍵孤兒」
    py -3.12 scripts\\pg_migrate_pilot.py --all         ← ⚠️ **不必再加
                                                          --allow-orphans**
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
