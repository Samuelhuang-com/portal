"""
Phase 0 步驟 3：把既有資料庫 stamp 到 baseline

做什麼
────────────────────────────────────────────────────────────────────────────
在 `portal.db` 與 `cycle-purchase.db` 各建一張 `alembic_version` 表，
寫入 baseline 版本號，告訴 Alembic「這個庫的結構已經是 baseline 了，
不用再跑 baseline 那支 migration」。

**不會建立、修改或刪除任何資料表與資料。** 只寫一列版本號。

為什麼安全
    baseline revision 是從 Model autogenerate 出來的，已驗證
    `alembic upgrade head` 建出的結構與 `create_all()` **完全一致**
    （459 個物件逐一比對，忽略引號／DEFAULT 括號／約束排列順序）。
    而你的資料庫結構也已經由 check_schema_drift.py 確認等同 Model。
    三者相等，所以 stamp 是在陳述事實，不是在改變什麼。

執行前提
    ⚠️ **必須先跑 check_schema_drift.py 且兩個庫都全綠。**
       本腳本會自己再檢查一次，有 drift 就拒絕執行。

執行：
    cd backend
    python scripts\\alembic_stamp_baseline.py

每個環境各跑一次（測試區 / 正式區 / 新 Server）。
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

from sqlalchemy import inspect, text                              # noqa: E402

BASELINE_MAIN = "baseline_main"
BASELINE_CP = "baseline_cp"


def _load_all_models() -> None:
    import importlib
    import pkgutil

    import app.models as pkg
    bad = []
    for m in pkgutil.iter_modules(pkg.__path__):
        try:
            importlib.import_module(f"app.models.{m.name}")
        except Exception as exc:
            bad.append(f"{m.name}: {exc}")
    if bad:
        raise SystemExit("model import 失敗，中止：\n  " + "\n  ".join(bad))


def _drift(base, eng) -> list[str]:
    """回傳阻擋項目（Model 有、DB 沒有的表或欄位）。"""
    insp = inspect(eng)
    db_tables = set(insp.get_table_names())
    problems: list[str] = []
    for tname, table in base.metadata.tables.items():
        if tname not in db_tables:
            problems.append(f"缺少資料表 {tname}")
            continue
        db_cols = {c["name"] for c in insp.get_columns(tname)}
        for col in table.columns:
            if col.name not in db_cols:
                problems.append(f"缺少欄位 {tname}.{col.name}")
    return problems


def _check_ini_ascii(ini: str) -> list[str]:
    """檢查 .ini 是否為純 ASCII。

    ⚠️ Alembic 用 `encoding="locale"` 讀 .ini。在 Windows 繁中環境那是 **cp950**，
       檔案裡只要有一個 UTF-8 位元組（中文註解、破折號 —、emoji），
       就會在 Alembic 真正啟動之前拋 `UnicodeDecodeError`。
       2026-08-28 實際踩過這個坑。中文說明一律寫在 `env.py`（Python 讀 UTF-8）。
    """
    path = os.path.join(BACKEND, ini)
    if not os.path.exists(path):
        return [f"{ini} 不存在"]
    with open(path, "rb") as f:
        raw = f.read()
    bad = []
    for lineno, line in enumerate(raw.split(b"\n"), start=1):
        try:
            line.decode("ascii")
        except UnicodeDecodeError:
            bad.append(f"{ini} 第 {lineno} 行含非 ASCII 字元")
    return bad


def _current_version(eng) -> str | None:
    insp = inspect(eng)
    if "alembic_version" not in insp.get_table_names():
        return None
    with eng.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    return row[0] if row else None


def stamp(label: str, ini: str, revision: str, base, eng) -> bool:
    print()
    print("=" * 72)
    print(f"  {label}")
    print(f"  {eng.url}")
    print("=" * 72)

    enc = _check_ini_ascii(ini)
    if enc:
        print(f"❌ {ini} 編碼問題，Alembic 會在啟動前就失敗：")
        for e in enc:
            print(f"     · {e}")
        print("   → Alembic 用 encoding=\"locale\" 讀 .ini，Windows 繁中是 cp950，")
        print("     檔案裡不能有任何中文／破折號／emoji。中文說明請寫在 env.py。")
        return False

    problems = _drift(base, eng)
    if problems:
        print(f"❌ 偵測到 {len(problems)} 項 schema drift，拒絕 stamp：")
        for p in problems[:20]:
            print(f"     · {p}")
        print("   → 請先修好 drift（見 check_schema_drift.py 的建議）再回來。")
        return False
    print("✅ schema 與 Model 一致")

    cur = _current_version(eng)
    if cur == revision:
        print(f"✅ 已經 stamp 過（version_num = {cur}），不需要重複執行。")
        return True
    if cur is not None:
        print(f"⚠️  alembic_version 已存在且版本是 {cur}（預期 {revision}）。")
        print("   → 這個環境的狀態跟預期不同，先不要動，把這行訊息貼出來。")
        return False

    print(f"執行：alembic -c {ini} stamp {revision}")
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", ini, "stamp", revision],
        cwd=BACKEND, capture_output=True, text=True,
    )
    if r.returncode != 0:
        print("❌ 失敗：")
        print((r.stdout + r.stderr)[-1500:])
        return False

    after = _current_version(eng)
    if after == revision:
        print(f"✅ 完成，alembic_version = {after}")
        return True
    print(f"❌ 執行後版本是 {after!r}，與預期不符")
    return False


def main() -> None:
    _load_all_models()
    from app.core.database import Base, engine
    from app.core.cycle_purchase_database import CyclePurchaseBase, cycle_purchase_engine
    engine.echo = False
    cycle_purchase_engine.echo = False

    print("Alembic baseline stamp（只寫版本號，不建表、不改資料）")

    ok1 = stamp("主庫 portal.db", "alembic.ini", BASELINE_MAIN, Base, engine)
    ok2 = stamp("週期採購 cycle-purchase.db", "alembic_cp.ini", BASELINE_CP,
                CyclePurchaseBase, cycle_purchase_engine)

    print()
    print("=" * 72)
    if ok1 and ok2:
        print("  ✅ 兩個庫都已 stamp 到 baseline。")
        print()
        print("  之後改 schema 的流程變成：")
        print("    1. 改 app/models/*.py")
        print("    2. cd backend && alembic revision --autogenerate -m \"說明\"")
        print("       （週採庫加 -c alembic_cp.ini）")
        print("    3. 檢查產出的版本檔內容")
        print("    4. alembic upgrade head")
        print()
        print("  ⚠️ 不要再往 main.py 加 _migrate_* 函式。")
    else:
        print("  ❌ 尚未完成，請看上面的訊息。")
    print()


if __name__ == "__main__":
    main()
