"""
Phase 0 前置：Schema Drift 檢查（唯讀）

用途：比對「資料庫的實際結構」與「SQLAlchemy Model 宣告的結構」是否一致。

為什麼要先跑這支：
    Phase 0 的計畫是「建一個 baseline revision，把現有資料庫 stamp 上去，
    然後刪掉 main.py 那 25 個 _migrate_* 函式」。這個計畫成立的前提是
    **現有資料庫的結構已經等同於 Model 宣告的結構**（也就是 25 個 patch
    都確實跑過了）。

    這個前提有可能不成立，因為 `_run_startup_migration()` 遇到 SQLite
    鎖定重試 5 次後會**印警告然後略過**（main.py:151 的設計）。如果哪次
    重啟剛好卡在同步中、之後又沒再觸發，某個欄位就會一直缺著。

    這支腳本就是來證實或推翻這個前提的。**唯讀，不修改任何東西。**

執行：
    cd backend
    python scripts\\check_schema_drift.py

在每一個環境各跑一次（測試區 / 正式區 / 新 Server），三邊都乾淨才能進下一步。
"""
from __future__ import annotations

import logging
import os
import sys

# ⚠️ 專案的 engine 可能開著 echo，不關掉的話檢查結果會被 SQL log 淹沒
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

from sqlalchemy import inspect                                    # noqa: E402

# ── 載入所有 model，確保 metadata 完整 ────────────────────────────────────────
# ⚠️ 少 import 一個模組，它的表就不會出現在 metadata 裡，會被誤判成「多餘的表」
import app.models                                                  # noqa: E402,F401
from app.core.database import Base, engine                         # noqa: E402

try:
    from app.core.cycle_purchase_database import (                 # noqa: E402
        CyclePurchaseBase, cycle_purchase_engine,
    )
    HAS_CP = True
except Exception as e:                                             # pragma: no cover
    print(f"[warn] 載入 cycle-purchase 失敗，只檢查主庫：{e}")
    HAS_CP = False


def _load_all_models() -> None:
    """把 app/models 底下所有模組都 import 一遍。"""
    import importlib
    import pkgutil

    import app.models as pkg
    for m in pkgutil.iter_modules(pkg.__path__):
        try:
            importlib.import_module(f"app.models.{m.name}")
        except Exception as exc:
            print(f"  [warn] import app.models.{m.name} 失敗：{exc}")


def check(label: str, base, eng) -> dict:
    print()
    print("=" * 74)
    print(f"  {label}")
    print(f"  {eng.url}")
    print("=" * 74)

    insp = inspect(eng)
    db_tables = set(insp.get_table_names())
    model_tables = set(base.metadata.tables.keys())

    missing_tables = sorted(model_tables - db_tables)
    extra_tables = sorted(db_tables - model_tables - {"alembic_version", "sqlite_sequence"})

    missing_cols: list[str] = []
    type_diff: list[str] = []

    for tname in sorted(model_tables & db_tables):
        table = base.metadata.tables[tname]
        db_cols = {c["name"]: c for c in insp.get_columns(tname)}
        for col in table.columns:
            if col.name not in db_cols:
                missing_cols.append(f"{tname}.{col.name}  （Model 有、DB 沒有）")
                continue
            want = str(col.type).upper().split("(")[0]
            got = str(db_cols[col.name]["type"]).upper().split("(")[0]
            # SQLite 的型別親和性很寬鬆，只比對明顯不同的大類
            fam = {"VARCHAR": "TEXT", "STRING": "TEXT", "CHAR": "TEXT",
                   "BIGINT": "INTEGER", "SMALLINT": "INTEGER", "BOOLEAN": "INTEGER",
                   "DECIMAL": "NUMERIC", "FLOAT": "NUMERIC", "REAL": "NUMERIC",
                   "DATETIME": "TIMESTAMP", "JSON": "TEXT"}
            if fam.get(want, want) != fam.get(got, got):
                type_diff.append(f"{tname}.{col.name}  Model={want} / DB={got}")

        # DB 有、Model 沒有的欄位（多半是被淘汰但沒清掉的舊欄位）
        for cname in db_cols:
            if cname not in table.columns:
                extra_tables.append(f"（欄位）{tname}.{cname}")

    extra_cols = [x for x in extra_tables if x.startswith("（欄位）")]
    extra_tables = [x for x in extra_tables if not x.startswith("（欄位）")]

    def _show(title: str, items: list[str], critical: bool) -> None:
        mark = "❌" if (items and critical) else ("⚠️ " if items else "✅")
        print(f"\n{mark} {title}：{len(items)} 項")
        for x in items[:40]:
            print(f"     · {x}")
        if len(items) > 40:
            print(f"     … 另外 {len(items) - 40} 項")

    # ❌ 這兩項會擋住 Phase 0
    _show("Model 有、DB 缺少的資料表", missing_tables, True)
    _show("Model 有、DB 缺少的欄位", missing_cols, True)
    # ⚠️ 這幾項不擋，但要知道
    _show("DB 有、Model 沒有的資料表（可能是已淘汰的舊表）", extra_tables, False)
    _show("DB 有、Model 沒有的欄位", extra_cols, False)
    _show("型別不一致", type_diff, False)

    has_alembic = "alembic_version" in db_tables
    ver = None
    if has_alembic:
        with eng.connect() as conn:
            from sqlalchemy import text
            rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
            ver = [r[0] for r in rows]
    print(f"\n📌 alembic_version 表：{'存在，版本 ' + str(ver) if has_alembic else '不存在（從未 stamp 過）'}")
    print(f"📊 資料表數：DB {len(db_tables)} 個 / Model {len(model_tables)} 個")

    return {
        "label": label,
        "blocking": len(missing_tables) + len(missing_cols),
        "missing_tables": missing_tables,
        "missing_cols": missing_cols,
        "alembic": ver,
    }


def main() -> None:
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    engine.echo = False
    if HAS_CP:
        cycle_purchase_engine.echo = False
    print("Schema Drift 檢查（唯讀，不修改任何資料）")
    _load_all_models()

    results = [check("主庫 portal.db", Base, engine)]
    if HAS_CP:
        results.append(check("週期採購 cycle-purchase.db", CyclePurchaseBase, cycle_purchase_engine))

    print()
    print("=" * 74)
    print("  總結")
    print("=" * 74)
    blocking = sum(r["blocking"] for r in results)
    for r in results:
        state = "✅ 乾淨" if r["blocking"] == 0 else f"❌ {r['blocking']} 項阻擋"
        print(f"  {r['label']:<34} {state}")
    print()
    if blocking == 0:
        print("  ✅ 結論：DB 結構與 Model 一致。")
        print("     → 「建 baseline + stamp + 刪掉 25 個 _migrate_*」的前提成立。")
        print("     → 請在其餘環境（正式區 / 新 Server）也各跑一次，三邊都乾淨才動手。")
    else:
        print("  ❌ 結論：有欄位或資料表沒跟上 Model。")
        print("     → 代表某些 _migrate_* 沒跑成功（很可能是啟動時遇到 SQLite 鎖定被略過）。")
        print("     → **先重啟一次後端讓它們補跑**，再跑一次本腳本；")
        print("       若仍有缺，把上面的清單貼出來再決定怎麼補。")
    print()


if __name__ == "__main__":
    main()
