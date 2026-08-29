"""
確認 Portal **實際**連到哪個資料庫（不是看設定檔，是問程式本身）

為什麼不能只看 .env
────────────────────────────────────────────────────────────────────────────
⚠️ `.env` 只是**輸入**。實際生效的還取決於：
     · 環境變數會蓋過 .env（`app/core/config.py` 用 pydantic-settings）
     · 服務可能還跑著切換**之前**啟動的舊行程（舊連線不會自己換）
     · 兩個資料庫各有各的 URL，有可能只切了一個

所以這支腳本做三件事，全部問「真正在用的那個 engine」：
    ① 兩個 engine 的 dialect 與連線目標
    ② 直接跟資料庫要它的版本字串（真的連得上才回得出來）
    ③ 抽幾張表比對筆數 —— 確認讀到的是**有資料的那一份**，不是空殼

⚠️ 還會檢查**執行中的服務**（8000 埠）是不是也連到同一個地方 ——
   腳本自己連 PG 不代表跑著的後端也是。

⚠️ 唯讀。

執行：
    cd backend
    py -3.12 scripts\\pg_verify_live.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import logging                                                    # noqa: E402
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

from sqlalchemy import text                                       # noqa: E402

# (表名, 是哪個庫) —— 挑有資料、跨模組的幾張
SAMPLES_MAIN = ["users", "contracts", "vendors", "dazhi_repair_case",
                "ohip_revenue_history", "menu_configs"]
SAMPLES_CP = ["cycle_purchase_items", "cycle_purchase_vendors", "cycle_purchase_cycles"]


def probe(engine, label: str, samples: list[str]) -> bool:
    print("-" * 78)
    print(f"  {label}")
    print("-" * 78)
    dialect = engine.dialect.name
    print(f"  dialect     : {dialect}")
    print(f"  連線目標    : {engine.url}")      # SQLAlchemy 的 repr 本來就會遮密碼

    ok = dialect == "postgresql"
    try:
        with engine.connect() as c:
            if dialect == "postgresql":
                ver = c.execute(text("SELECT version()")).scalar_one()
                db = c.execute(text("SELECT current_database()")).scalar_one()
                coll = c.execute(text(
                    "SELECT datcollate FROM pg_database WHERE datname = current_database()"
                )).scalar_one()
                print(f"  伺服器回報  : {ver.split(',')[0]}")
                print(f"  current_db  : {db}   collation: {coll}")
                if not coll.upper().startswith(("C", "POSIX")):
                    print("  ⚠️ collation 不是 C —— 中文 ORDER BY 會與 SQLite 不同")
            else:
                ver = c.execute(text("SELECT sqlite_version()")).scalar_one()
                print(f"  伺服器回報  : SQLite {ver}")
            print("\n  抽樣筆數（確認讀到的是有資料的那一份，不是空殼）：")
            for t in samples:
                try:
                    n = c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one()
                    flag = "⚠️ 空的" if n == 0 else ""
                    print(f"      {t:<26}{n:>10,} 列  {flag}")
                except Exception as e:
                    print(f"      {t:<26}{'查不到':>10}  ← {type(e).__name__}")
    except Exception as e:
        print(f"  ❌ 連不上：{type(e).__name__}: {str(e).splitlines()[0][:80]}")
        return False
    print()
    return ok


def probe_service() -> None:
    """⚠️ 腳本自己連得上 PG，不代表**跑著的後端**也是。

    後端是另一個行程，它的連線是啟動當下建立的 —— 切換 .env 之後沒重啟的話，
    它還連在舊的資料庫上，而且完全看不出來。這裡用 API 反問它。
    """
    print("-" * 78)
    print("  執行中的服務（8000 埠）")
    print("-" * 78)
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/version", timeout=5) as r:
            body = json.loads(r.read().decode("utf-8", "replace"))
        print(f"  ✅ 服務有回應：{body}")
    except urllib.error.HTTPError as e:
        print(f"  服務有回應但該端點回 {e.code}（沒有 /version 端點也正常）")
    except Exception as e:
        print(f"  ⚠️ 連不上 8000 埠：{type(e).__name__} —— 服務沒跑，或跑在別的埠")
    print("""
  ⚠️⚠️ **這支腳本查的是「現在重新連線會連到哪」。**
     跑著的後端行程是在它**啟動當下**建立連線的 —— 如果 .env 是在服務
     啟動之後才改的，它仍連著舊資料庫，從這裡看不出來。
     唯一可靠的判斷：看後端啟動 log 有沒有那一行
         [Portal] Dialect = postgresql（非 SQLite，跳過 WAL 設定）
     沒看到就是還沒重啟。
""")


def main() -> int:
    print("=" * 78)
    print("  Portal 實際連到哪個資料庫")
    print("=" * 78)
    print(f"  ⚠️ 環境變數會蓋過 .env：")
    for k in ("DATABASE_URL", "CYCLE_PURCHASE_DATABASE_URL"):
        v = os.environ.get(k)
        print(f"      os.environ[{k}] = {'（未設定，會用 .env）' if not v else v[:60]}")
    print()

    from app.core.database import engine
    from app.core.cycle_purchase_database import cycle_purchase_engine
    engine.echo = cycle_purchase_engine.echo = False

    a = probe(engine, "主庫（app.core.database.engine）", SAMPLES_MAIN)
    b = probe(cycle_purchase_engine, "週期採購（cycle_purchase_engine）", SAMPLES_CP)
    probe_service()

    print("=" * 78)
    if a and b:
        print("  ✅ 兩個資料庫都已連到 PostgreSQL。\n")
        return 0
    print("  ⚠️ 尚未全部切換：")
    if not a:
        print("      主庫還在 SQLite")
    if not b:
        print("      週期採購還在 SQLite")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
