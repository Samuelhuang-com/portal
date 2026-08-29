"""
補建「Model 有、資料庫沒有」的資料表（只建表，不碰任何資料）

什麼時候會用到
────────────────────────────────────────────────────────────────────────────
某台機器的後端**自從新模組上線後就沒重啟過**時，那個模組的資料表不會存在
—— 因為建表是 `create_all()` 做的，而 `create_all()` 只在啟動時跑一次。
2026-08-28 正式區就是這個狀況：缺 `ai_query_cache` 與 `ai_conversation_log`。

⚠️ **這支只呼叫 `Base.metadata.create_all()`，與後端啟動時做的完全同一件事。**
   `create_all()` **只建不存在的表**，不會變更既有表、不會動任何一列資料。

⚠️ **不要用 `init_db.py` 代替。** 那支除了建表還會塞據點／角色／
   用寫死的密碼建初始使用者，並把密碼印在畫面上 —— 不適合在正式區執行。

⚠️ **補不了「缺欄位」。** `create_all()` 對既有表束手無策。
   缺欄位是另一回事，要走 Alembic：
       alembic revision --autogenerate -m "說明"
       alembic upgrade head

執行：
    cd backend
    py -3.12 scripts\\create_missing_tables.py           # 會先列出再問你
    py -3.12 scripts\\create_missing_tables.py --yes     # 不問直接建
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

from sqlalchemy import inspect                                    # noqa: E402


def load_all_models() -> None:
    import importlib
    import pkgutil

    import app.models as pkg
    bad: list[str] = []
    for m in pkgutil.iter_modules(pkg.__path__):
        try:
            importlib.import_module(f"app.models.{m.name}")
        except Exception as exc:
            bad.append(f"{m.name}: {type(exc).__name__}: {exc}")
    if bad:
        # ⚠️ 少 import 一個模組，它的表就會被誤判成「不需要建」
        raise SystemExit("model import 失敗，中止：\n  " + "\n  ".join(bad))


def handle(label: str, base, eng, auto_yes: bool) -> bool:
    print()
    print("=" * 72)
    print(f"  {label}")
    print(f"  {eng.url}")
    print("=" * 72)

    insp = inspect(eng)
    have = set(insp.get_table_names())
    want = set(base.metadata.tables)
    missing = sorted(want - have)

    # 缺欄位是另一回事，這支補不了 —— 先講清楚免得誤以為跑完就沒事
    lack_cols: list[str] = []
    for tname in sorted(want & have):
        db_cols = {c["name"] for c in insp.get_columns(tname)}
        for col in base.metadata.tables[tname].columns:
            if col.name not in db_cols:
                lack_cols.append(f"{tname}.{col.name}")

    if not missing:
        print("  ✅ 沒有缺少的資料表")
    else:
        print(f"  缺少 {len(missing)} 張資料表：")
        for t in missing:
            print(f"     · {t}")
        if not auto_yes:
            try:
                ans = input("\n  要建立這些表嗎？（只建表、不動任何資料）輸入 y 執行： ").strip().lower()
            except EOFError:
                ans = ""
            if ans not in ("y", "yes"):
                print("  已取消。")
                return False
        base.metadata.create_all(bind=eng)
        after = set(inspect(eng).get_table_names())
        created = sorted(set(missing) & after)
        failed = sorted(set(missing) - after)
        print(f"\n  ✅ 已建立 {len(created)} 張：{', '.join(created)}")
        if failed:
            print(f"  ❌ 仍缺少：{', '.join(failed)}")
            return False

    if lack_cols:
        print(f"\n  ⚠️  另有 {len(lack_cols)} 個**缺少的欄位**，本腳本補不了：")
        for c in lack_cols[:20]:
            print(f"     · {c}")
        print("     → 缺欄位要走 Alembic：alembic revision --autogenerate → upgrade head")
        return False
    return True


def main() -> int:
    auto_yes = "--yes" in sys.argv or "-y" in sys.argv
    load_all_models()

    from app.core.database import Base, engine
    from app.core.cycle_purchase_database import CyclePurchaseBase, cycle_purchase_engine
    engine.echo = False
    cycle_purchase_engine.echo = False

    print("補建缺少的資料表（只建表，不動任何資料）")
    ok1 = handle("主庫 portal.db", Base, engine, auto_yes)
    ok2 = handle("週期採購 cycle-purchase.db", CyclePurchaseBase, cycle_purchase_engine, auto_yes)

    print()
    print("=" * 72)
    if ok1 and ok2:
        print("  ✅ 完成。接著跑：")
        print("       py -3.12 scripts\\check_schema_drift.py      （應該全綠）")
        print("       py -3.12 scripts\\alembic_stamp_baseline.py")
    else:
        print("  ❌ 尚未完成，請看上面的訊息。")
    print()
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    sys.exit(main())
