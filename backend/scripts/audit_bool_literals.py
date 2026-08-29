"""
掃出「raw SQL 拿 0/1 跟 Boolean 欄位比較」的地方（PostgreSQL 會直接拒絕）

背景（2026-08-29，測試區試切換時炸出來的）
────────────────────────────────────────────────────────────────────────────
```
psycopg.errors.UndefinedFunction: operator does not exist: boolean = integer
LINE 1: ... WHERE menu_key = '...' AND is_visible = 1
```

⚠️⚠️ **SQLite 沒有真正的 BOOLEAN 型別** —— 它把布林存成 0/1 整數，
   所以 `WHERE is_visible = 1` 完全正常。
   **PostgreSQL 有真正的 boolean，而且不做隱式轉型** ——
   `boolean = integer` 這個運算子根本不存在。

⚠️ 為什麼 `pg_compare_reads.py` 沒抓到：那支只測**查詢函式**，
   而這個炸點在 **startup 的 seed 函式**裡 —— 服務啟動時才跑。
   這是驗證涵蓋範圍的真實破口，不是工具壞了。

判準（只報真的會炸的）
    · 只看 raw SQL 字串（`text(...)`、多行 SQL 常數）
    · 欄位必須在 model 裡宣告為 **Boolean** —— `Integer` 的 `= 1` 完全合法
      （例：`opera_revenue_daily.is_current` 是 Integer，不算）
    · ⚠️ 排除註解與 docstring —— 那些只是在講解，不會執行

⚠️ 用 SQLAlchemy 運算式（`Model.is_visible == True`）的地方**不受影響**，
   SQLAlchemy 會按方言渲染正確的字面值。只有手寫 SQL 字串有問題。

⚠️ 唯讀，只報告不修改。

執行：
    cd backend
    py -3.12 scripts\\audit_bool_literals.py
"""
from __future__ import annotations

import ast
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)


def bool_columns() -> set[str]:
    """所有在 model 裡宣告為 Boolean 的欄位名（兩個資料庫都算）。"""
    import importlib
    import logging
    import pkgutil
    logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
    import app.models as pkg
    for m in pkgutil.iter_modules(pkg.__path__):
        try:
            importlib.import_module(f"app.models.{m.name}")
        except Exception:
            pass
    from sqlalchemy import Boolean
    from app.core.database import Base
    from app.core.cycle_purchase_database import CyclePurchaseBase
    out: set[str] = set()
    for B in (Base, CyclePurchaseBase):
        for t in B.metadata.tables.values():
            for c in t.columns:
                if isinstance(c.type, Boolean):
                    out.add(c.name)
    return out


def string_literals(path: str) -> list[tuple[int, str]]:
    """回傳檔案裡所有**會執行的**字串常數（排除 docstring 與註解）。

    ⚠️ 用 AST 而不是 grep：註解與 docstring 裡經常引用 SQL 當說明，
       grep 會把那些一起報出來（實測第一版就誤報了 3 處）。
    """
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="ignore").read())
    except SyntaxError:
        return []
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            d = node.body[0] if node.body else None
            if isinstance(d, ast.Expr) and isinstance(d.value, ast.Constant) \
                    and isinstance(d.value.value, str):
                docstrings.add(id(d.value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in docstrings:
            out.append((node.lineno, node.value))
    return out


def main() -> int:
    bools = bool_columns()
    print("=" * 78)
    print("  raw SQL 拿 0/1 跟 Boolean 欄位比較（PostgreSQL 會拒絕）")
    print("=" * 78)
    print(f"  model 裡宣告為 Boolean 的欄位共 {len(bools)} 個\n")

    # `欄位 = 0/1`、`SET 欄位 = 0/1`，容許空白
    pat = re.compile(r"\b(" + "|".join(sorted(map(re.escape, bools))) + r")\s*=\s*([01])\b")
    hits: list[tuple[str, int, str, str]] = []
    for root, _, files in os.walk(os.path.join(BACKEND, "app")):
        if "__pycache__" in root:
            continue
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, BACKEND).replace("\\", "/")
            for lineno, s in string_literals(path):
                for m in pat.finditer(s):
                    frag = " ".join(s.split())
                    i = frag.find(m.group(0))
                    hits.append((rel, lineno, m.group(1),
                                 frag[max(0, i - 40):i + 40]))

    if not hits:
        print("  ✅ 沒有問題\n")
        return 0

    print(f"  ❌ 找到 {len(hits)} 處：\n")
    for rel, lineno, col, frag in hits:
        print(f"    {rel}:{lineno}  （{col} 是 Boolean）")
        print(f"        …{frag}…")
    print(f"""
  怎麼改
    · `= 1` → `IS TRUE`，`= 0` → `IS FALSE`
      ⚠️ **兩個引擎都吃 `IS TRUE` / `IS FALSE`**，所以不必寫方言判斷。
        （SQLite 從 3.23 起支援；`true`/`false` 關鍵字也支援。）
    · 更好的做法是**別寫 raw SQL** —— 改用 SQLAlchemy 運算式
      （`Model.is_visible == True`），它會按方言渲染正確的字面值。

  ⚠️ `app/routers/budget.py` 若出現在上面：那個模組用裸的 `sqlite3.connect()`，
     不經過 `DATABASE_URL`，切到 PostgreSQL 也不受影響 —— 可以先不動。
""")
    return 1


if __name__ == "__main__":
    sys.exit(main())
