"""
把「超過 VARCHAR(n) 宣告長度」的實際值印出來（唯讀）

為什麼要先看再決定
────────────────────────────────────────────────────────────────────────────
`pg_migrate_pilot.py --dry-run` 只告訴你「哪個欄位有幾列超長」，
但**處理方式取決於那些值到底是什麼**，而且兩條路的方向完全相反：

  · 宣告太緊 → 放寬 model 的 String(n)，用 Alembic 產 migration
  · 資料有問題 → 修資料，**不要**放寬宣告（放寬等於把問題蓋起來）

例：`applicant`（申請人）宣告 VARCHAR(50) 卻出現 17,474 字元的值 ——
那不會是人名，比較像有別的東西被寫進去了。這種要查根因，不是放寬欄位。

⚠️ 唯讀，不修改任何資料。

執行：
    cd backend
    py -3.12 scripts\\pg_show_overlong.py
    py -3.12 scripts\\pg_show_overlong.py --chars 400    # 每個值顯示更長
"""
from __future__ import annotations

import logging
import os
import re
import sys

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

from sqlalchemy import String, Text, inspect, text                # noqa: E402

SAMPLES = 3           # 每個欄位印幾筆
DEFAULT_CHARS = 160   # 每筆值顯示幾個字


def load_all_models() -> None:
    import importlib
    import pkgutil
    import app.models as pkg
    for m in pkgutil.iter_modules(pkg.__path__):
        try:
            importlib.import_module(f"app.models.{m.name}")
        except Exception:
            pass


def main() -> int:
    chars = int(sys.argv[sys.argv.index("--chars") + 1]) if "--chars" in sys.argv else DEFAULT_CHARS
    load_all_models()
    from app.core.database import Base, engine
    engine.echo = False

    print("=" * 78)
    print("  超過 VARCHAR(n) 宣告長度的實際值（唯讀）")
    print("=" * 78)
    print(f"  {engine.url}\n")

    have = set(inspect(engine).get_table_names())
    found = 0

    with engine.connect() as c:
        for tname in sorted(Base.metadata.tables):
            if tname not in have:
                continue
            table = Base.metadata.tables[tname]
            for col in table.columns:
                length = getattr(col.type, "length", None)
                if not isinstance(col.type, (String, Text)) or not length:
                    continue
                cn = col.name
                try:
                    rows = c.execute(text(
                        f"SELECT LENGTH({cn}) AS n, {cn} FROM {tname} "
                        f"WHERE LENGTH({cn}) > {length} "
                        f"ORDER BY LENGTH({cn}) DESC LIMIT {SAMPLES}")).all()
                    total = c.execute(text(
                        f"SELECT COUNT(*) FROM {tname} WHERE LENGTH({cn}) > {length}"
                    )).scalar_one()
                except Exception:
                    continue
                if not rows:
                    continue
                found += 1
                print("-" * 78)
                print(f"  {tname}.{cn}")
                print(f"  宣告 VARCHAR({length}) ｜ {total:,} 列超長 ｜ 最長 {rows[0][0]:,} 字")
                print("-" * 78)
                for n, v in rows:
                    s = (v or "").replace("\n", "⏎").replace("\r", "")
                    cut = s[:chars] + (f" …（後面還有 {n - chars:,} 字）" if n > chars else "")
                    print(f"    [{n:>6,} 字] {cut}")
                print()

    print("=" * 78)
    if not found:
        print("  ✅ 沒有超長的值")
    else:
        print(f"  共 {found} 個欄位有超長的值。逐一判斷：\n")
        print("""    · 值看起來「就是正常內容、只是比較長」
        → 宣告太緊。放寬 model 的 String(n)，用 Alembic 產 migration：
              改 app/models/xxx.py 的欄位長度
              alembic revision --autogenerate -m "放寬 xxx 欄位長度"
              alembic upgrade head

    · 值看起來「根本不該出現在這個欄位」（超長很多、內容是別的東西）
        → 資料有問題。要查是哪條寫入路徑塞進去的，**不要放寬宣告** ——
          放寬只會讓錯誤資料合法化，之後更難發現。""")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
