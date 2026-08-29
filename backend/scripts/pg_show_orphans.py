"""
把「外鍵孤兒」的實際內容印出來（唯讀）

為什麼要先看再決定
────────────────────────────────────────────────────────────────────────────
`pg_migrate_pilot.py --dry-run` 只說「哪個外鍵有幾列對不到父資料」，
但**處理方式取決於那個欄位在業務上代表什麼**，兩條路方向完全相反：

  · 稽核性欄位（誰建的、誰授權的）→ 父資料被刪很正常，設 NULL 即可
  · 業務性欄位（這張合約屬於哪家廠商）→ 設 NULL 等於**弄丟資訊**，
    要先確認還原得回來，或決定接受這個損失

⚠️ SQLite **預設不執行外鍵約束**（要 `PRAGMA foreign_keys=ON`，本專案沒開），
   所以這些孤兒是長年累積下來的，不是遷移造成的。PostgreSQL 一律執行，
   所以搬過去之前一定要處理。

⚠️ 這支腳本唯讀，不修改任何資料。

執行：
    cd backend
    py -3.12 scripts\\pg_show_orphans.py
    py -3.12 scripts\\pg_show_orphans.py --samples 10
    py -3.12 scripts\\pg_show_orphans.py --cycle-purchase   # 改看週採那個獨立 DB
"""
from __future__ import annotations

import logging
import os
import sys

# ⚠️ 輸出強制 UTF-8（2026-08-29 踩過）
#    Windows 主控台是 UTF-8，但**把輸出導向檔案時 Python 會改用 cp950**，
#    腳本裡的 ⚠️ ✅ ❌ 一律編不進去 → UnicodeEncodeError 整支中斷。
#    `> cmp.txt` 這種存檔動作很常用，不能因此掛掉。
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

DEFAULT_SAMPLES = 5


def load_all_models(cycle_purchase: bool = False):
    """⚠️ 本專案有兩個獨立資料庫，各有自己的 Base／engine（見 pg_migrate_pilot）。"""
    import importlib
    import pkgutil
    import app.models as pkg
    for m in pkgutil.iter_modules(pkg.__path__):
        try:
            importlib.import_module(f"app.models.{m.name}")
        except Exception:
            pass
    if cycle_purchase:
        from app.core.cycle_purchase_database import CyclePurchaseBase
        return CyclePurchaseBase
    from app.core.database import Base
    return Base


def main() -> int:
    n_s = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv \
        else DEFAULT_SAMPLES
    cp = "--cycle-purchase" in sys.argv
    Base = load_all_models(cycle_purchase=cp)
    if cp:
        from app.core.cycle_purchase_database import cycle_purchase_engine as engine
    else:
        from app.core.database import engine
    engine.echo = False

    print("=" * 78)
    print("  外鍵孤兒的實際內容（唯讀）"
          + ("　—　週期採購資料庫" if cp else ""))
    print("=" * 78)
    print(f"  {engine.url}\n")

    have = set(inspect(engine).get_table_names())
    found = 0
    # ⚠️ 查不動的外鍵要單獨記著，最後跟「有孤兒」一樣算未通過 ——
    #    這支腳本是 pg_cutover --check 的第③關，回 0 等於放行搬資料。
    failures: list[tuple[str, str]] = []

    with engine.connect() as c:
        for tname in sorted(Base.metadata.tables):
            if tname not in have:
                continue
            for fk in Base.metadata.tables[tname].foreign_keys:
                child_col = fk.parent.name
                parent_tbl = fk.column.table.name
                parent_col = fk.column.name
                if parent_tbl not in have or parent_tbl == tname:
                    continue
                miss = (f"FROM {tname} ch WHERE ch.{child_col} IS NOT NULL "
                        f"AND NOT EXISTS (SELECT 1 FROM {parent_tbl} pa "
                        f"WHERE pa.{parent_col} = ch.{child_col})")
                # ⚠️⚠️ 這裡**不可以**用 `except Exception: continue`（2026-08-29 修）。
                #    舊版把查詢失敗跟「沒有孤兒」混成同一件事：某個外鍵查爆了，
                #    腳本照樣往下走，最後印出「✅ 沒有外鍵孤兒」。
                #    **檢查工具最不該做的事，就是把「我沒查成功」講成「我查過沒問題」。**
                #    正式區當天就是被三個這種假 ✅ 帶錯方向。
                try:
                    cnt = c.execute(text(f"SELECT COUNT(*) {miss}")).scalar_one()
                except Exception as e:
                    failures.append((f"{tname}.{child_col} → {parent_tbl}.{parent_col}",
                                     f"{type(e).__name__}: "
                                     f"{str(e).splitlines()[0][:120]}"))
                    continue
                if not cnt:
                    continue
                # 這幾個只是為了把訊息講清楚，失敗不影響「有孤兒」這個結論
                try:
                    distinct = c.execute(text(
                        f"SELECT COUNT(DISTINCT ch.{child_col}) {miss}")).scalar_one()
                    total = c.execute(text(f"SELECT COUNT(*) FROM {tname}")).scalar_one()
                    vals = c.execute(text(
                        f"SELECT DISTINCT ch.{child_col} {miss} LIMIT {n_s}")).scalars().all()
                except Exception as e:
                    print(f"  ⚠️ {tname}.{child_col} 有 {cnt:,} 列孤兒，"
                          f"但取明細時失敗：{type(e).__name__}")
                    distinct, total, vals = 0, cnt, []

                found += 1
                col = fk.parent
                print("-" * 78)
                print(f"  {tname}.{child_col}  →  {parent_tbl}.{parent_col}")
                print("-" * 78)
                print(f"  孤兒 {cnt:,} 列 / 全表 {total:,} 列"
                      f"（{cnt / total * 100:.1f}%），對不到的父鍵有 {distinct} 個")
                print(f"  欄位可為 NULL：{'是 → 可設 NULL' if col.nullable else '❌ 否 → 設 NULL 會違反 NOT NULL'}")
                print(f"  對不到的值：{', '.join(repr(v) for v in vals)}"
                      + (" …" if distinct > n_s else ""))

                # 同一列還有哪些欄位可以看出這筆在講什麼
                hint_cols = [x.name for x in Base.metadata.tables[tname].columns
                             if x.name != child_col
                             and any(k in x.name for k in
                                     ("name", "no", "title", "code", "email"))][:3]
                if hint_cols:
                    try:
                        rows = c.execute(text(
                            f"SELECT {', '.join('ch.' + h for h in hint_cols)} {miss} "
                            f"LIMIT {n_s}")).all()
                        print(f"  同列的 {', '.join(hint_cols)}：")
                        for r in rows:
                            print(f"      {' ｜ '.join(str(x) for x in r)}")
                    except Exception:
                        pass
                print()

    print("=" * 78)
    if failures:
        print(f"  ❌ 有 {len(failures)} 個外鍵**查不動**（不是「沒有孤兒」，是沒查成功）：\n")
        for what, why in failures:
            print(f"    {what}")
            print(f"        {why}")
        print("""
  ⚠️⚠️ 在這些外鍵確認乾淨之前，**不可以視為通過**。
     查詢失敗最常見的原因：欄位型別兩邊對不起來（例如一邊 TEXT 一邊
     INTEGER，PostgreSQL 不做隱式轉型）、或該表根本還沒建好。
     照著搬過去，PostgreSQL 會在寫入時才擋，那時已經搬到一半。
""")
        return 1

    if not found:
        # ⚠️ 空表當然沒有孤兒 —— 要講清楚「檢查了什麼」，
        #    不然「✅ 沒有外鍵孤兒」對著一個空資料庫也會照印。
        n_fk = sum(1 for t in Base.metadata.tables
                   if t in have
                   for _ in Base.metadata.tables[t].foreign_keys)
        rows = 0
        try:
            with engine.connect() as c2:
                for t in sorted(have):
                    try:
                        rows += c2.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one()
                    except Exception:
                        pass
        except Exception:
            rows = -1
        print(f"  ✅ 沒有外鍵孤兒（檢查了 {n_fk} 個外鍵 / {len(have)} 張表 / "
              f"{rows:,} 列）")
        if rows == 0:
            print("\n  ⚠️⚠️ **但這個資料庫是空的（0 列）** —— 空表當然沒有孤兒。")
            print("     這個 ✅ 不代表你的資料乾淨，只代表這裡沒有資料可查。")
            print("     確認一下 DATABASE_URL 指的是不是你以為的那個資料庫。\n")
            return 1
        print()
        return 0

    print(f"""  共 {found} 個外鍵有孤兒。逐一判斷（不要一律設 NULL）：

    · **稽核性欄位**（granted_by、created_by、approved_by…）
        父資料被刪很正常（離職帳號被移除）。這個欄位的資訊本來就是
        「當時是誰做的」，人都不在了，設 NULL 沒有額外損失。

    · **業務性欄位**（vendor_id、contract_id、batch_id…）
        設 NULL 等於**弄丟這筆資料屬於誰**。先確認：
          ① 父資料是被誤刪的嗎 → 補回來，不要動子表
          ② 同一列還有別的欄位記著（例如廠商名稱）→ 資訊沒丟，可設 NULL
          ③ 兩者皆非 → 這是真的資料損失，要你決定接不接受

    ⚠️ **不要為了搬得過去就把外鍵約束拿掉。** 那等於把 PostgreSQL 幫你
       抓出來的問題重新蓋回去，而且以後還會繼續累積。
""")
    return 1


if __name__ == "__main__":
    sys.exit(main())
