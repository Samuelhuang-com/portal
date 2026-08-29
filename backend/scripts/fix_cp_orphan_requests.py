"""
刪掉週採裡指向「已刪除週期」的孤兒請購單

背景（2026-08-29，PostgreSQL 遷移的前置檢查抓到）
────────────────────────────────────────────────────────────────────────────
`cycle_purchase_requests.cycle_id → cycle_purchase_cycles.id` 有 4 列孤兒
（全表只有 5 列），全部指向已經不存在的 `cycle_id = 6`。

⚠️⚠️ **這批孤兒不可能是從 Portal 正常操作產生的。**

   ⚠️ 注意兩個資料庫的設定**不一樣**（2026-08-29 實測確認）：

   | 資料庫 | `PRAGMA foreign_keys` | 後果 |
   |---|---|---|
   | `portal.db` | **沒開** | FK 宣告形同虛設，孤兒可以長年累積 |
   | `cycle-purchase.db` | **有開**（`cycle_purchase_database.py` 第 55 行） | FK 真的會執行 |

   所以週採這邊 `ondelete=RESTRICT` 是**有效力的** —— 透過 App 刪 cycle 6
   會被擋下來，透過 App 也建不出指向不存在週期的請購單（實測：
   `sqlite3.IntegrityError: FOREIGN KEY constraint failed`）。

   既然如此，孤兒只可能來自**繞過這個 engine 的路徑**：
     · 一次性 migration 腳本（SQLite 改結構要「建新表→搬資料→刪舊表→改名」，
       標準做法就是全程 `PRAGMA foreign_keys=OFF`）
     · DB Browser 之類的工具直接改
     · 自己開 `sqlite3.connect()` 的腳本（預設不開 FK）

   ⚠️ 這反而讓「開發期產物」的判定更確定 —— 正常使用做不出這種資料。

────────────────────────────────────────────────────────────────────────────
判定為測試資料的證據（已與使用者確認）
    · 4 張建立於 2026-08-20 **05:50:12 ～ 05:55:34，前後 5 分鐘**
    · 全部 `status='draft'`、`is_closed=0` —— 從未進入彙整／採購／驗收
    · 父週期 **5 和 6 都不存在**（現存只有 1~4）→ 一次刪掉兩個測試週期
    · 週期 1、2 是 `inactive` 而不是被刪 —— 系統有「停用」概念，
      5/6 卻是被**真的刪掉**，那是「這兩個是做錯的」的處理方式
    · 隔天 2026-08-21 的 PR-2026-08-005 用的是**存在的** cycle 4，
      而且 `is_closed=1` 走完了流程 —— 那才是真正的第一張

⚠️ `cycle_purchase_request_items.request_id` 是 **CASCADE**，
   刪請購單會**連帶刪掉明細**。本腳本會先數給你看。

⚠️ 預設唯讀。要實際刪除必須加 `--fix`。
⚠️ 動手前請先複製一份 `C:\\portal_data\\cycle-purchase.db`。

執行：
    cd backend
    py -3.12 scripts\\fix_cp_orphan_requests.py          # 只看不改
    py -3.12 scripts\\fix_cp_orphan_requests.py --fix    # 實際刪除
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

from sqlalchemy import text                                       # noqa: E402

ORPHAN = ("SELECT id FROM cycle_purchase_requests r WHERE NOT EXISTS "
          "(SELECT 1 FROM cycle_purchase_cycles c WHERE c.id = r.cycle_id)")


def main() -> int:
    do_fix = "--fix" in sys.argv
    from app.core.cycle_purchase_database import cycle_purchase_engine as engine
    engine.echo = False

    print("=" * 78)
    print("  週採：刪除指向已刪除週期的孤兒請購單")
    print("=" * 78)
    print(f"  {engine.url}\n")

    with engine.connect() as c:
        rows = c.execute(text(
            "SELECT r.id, r.request_no, r.cycle_id, r.period_label, r.company, "
            "       r.total_amount, r.status, r.is_closed, r.is_summarized, r.created_at "
            f"FROM cycle_purchase_requests r WHERE r.id IN ({ORPHAN}) ORDER BY r.id")).all()
        if not rows:
            print("  ✅ 沒有孤兒請購單，不需要處理。\n")
            return 0

        ids = [r[0] for r in rows]
        n_items = c.execute(text(
            "SELECT COUNT(*) FROM cycle_purchase_request_items "
            f"WHERE request_id IN ({','.join(str(i) for i in ids)})")).scalar_one()
        total = c.execute(text("SELECT COUNT(*) FROM cycle_purchase_requests")).scalar_one()

    print(f"  要刪除 {len(rows)} 張（全表 {total} 張）+ 連帶 {n_items} 筆明細（CASCADE）：\n")
    print(f"    {'單號':<18}{'週期':>5}{'期別':>10}{'金額':>9}  {'狀態':<8}{'已彙整':<8}建立時間")
    print("    " + "-" * 74)
    summarized = []
    for r in rows:
        mark = "是" if r[8] else "否"
        if r[8]:
            summarized.append(r[1])
        print(f"    {r[1]:<18}{r[2]:>5}{r[3]:>10}{r[5]:>9}  {r[6]:<8}{mark:<8}{r[9]}")

    if summarized:
        print(f"""
  ⚠️⚠️ **{len(summarized)} 張已經被彙整過**（{', '.join(summarized)}）——
     這跟「測試資料」的判定不符，彙整代表它進入過後續流程。
     **本腳本不會刪**，請先確認 cycle_purchase_summary 裡的對應資料。""")
        return 2

    if not do_fix:
        print("""
  （唯讀模式，未刪除任何資料）
  ⚠️ 先複製一份 C:\\portal_data\\cycle-purchase.db 當備份，再加 --fix 執行。
""")
        return 1

    id_list = ",".join(str(i) for i in ids)
    with engine.begin() as c:
        # ⚠️ 明細**先**刪、不靠 CASCADE。
        #    週採 engine 確實有開 `PRAGMA foreign_keys=ON`，CASCADE 會生效；
        #    但明確刪掉才能拿到真實的 rowcount 印給使用者看，
        #    也不必依賴「連線設定有沒有被改過」這種隱含前提。
        d_items = c.execute(text(
            f"DELETE FROM cycle_purchase_request_items WHERE request_id IN ({id_list})")).rowcount
        d_req = c.execute(text(
            f"DELETE FROM cycle_purchase_requests WHERE id IN ({id_list})")).rowcount

    with engine.connect() as c:
        left = c.execute(text(f"SELECT COUNT(*) FROM ({ORPHAN})")).scalar_one()
        remain = c.execute(text("SELECT COUNT(*) FROM cycle_purchase_requests")).scalar_one()

    print(f"\n  ✅ 已刪除 {d_req} 張請購單、{d_items} 筆明細")
    print(f"  ✅ 剩餘孤兒 {left} 張；請購單總數 {remain} 張")
    print("""
  接著：
    py -3.12 scripts\\pg_show_orphans.py --cycle-purchase      ← 應顯示「沒有外鍵孤兒」
    py -3.12 scripts\\pg_migrate_pilot.py --cycle-purchase     ← 前置檢查應全綠
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
