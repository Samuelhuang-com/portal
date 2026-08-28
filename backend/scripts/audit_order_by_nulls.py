"""
盤點 `order_by()` 的 NULL 排序風險（唯讀，只做靜態分析）

為什麼要盤這個
────────────────────────────────────────────────────────────────────────────
**SQLite 與 PostgreSQL 的 ORDER BY 遇到 NULL，位置是相反的：**

    SQLite      ASC : [None, 'a', 'b']      DESC: ['b', 'a', None]
    PostgreSQL  ASC : ['a', 'b', None]      DESC: [None, 'b', 'a']

SQLite 的 NULL 永遠排最前；PostgreSQL 是 ASC 排最後（NULLS LAST）、
DESC 排最前（NULLS FIRST）。**ASC 時完全相反。**

⚠️ 這件事**不會報錯**，只是那幾列跑到別的位置去。使用者只會說
   「這張表怎麼跟以前不一樣」，很難聯想到資料庫換了。

本腳本做什麼
    ① 從 SQLAlchemy metadata 讀出每個「表.欄位」是否 nullable
    ② 用 AST 掃過所有 router／service，找出 `order_by(...)` 的參數
    ③ 解析得出 `Model.column` 的，比對 nullable，分成三類報告

⚠️ **靜態分析有極限。** 它看不出「那個欄位實際上有沒有 NULL 值」，
   也解析不了 `order_by(sort_col)` 這種先組變數再傳進去的寫法
   （會歸到「無法解析」，需要人工看）。這支是**縮小人工檢查範圍**用的，
   不是保證清單。

執行：
    cd backend
    python scripts\\audit_order_by_nulls.py
    python scripts\\audit_order_by_nulls.py --all      # 連不受影響的也列出
"""
from __future__ import annotations

import ast
import logging
import os
import sys
from collections import defaultdict

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

SCAN_DIRS = ["app/routers", "app/services"]


def build_column_map() -> dict[str, dict[str, bool]]:
    """{ Model 類別名: { 欄位屬性名: nullable } }"""
    import importlib
    import pkgutil

    import app.models as pkg
    for m in pkgutil.iter_modules(pkg.__path__):
        try:
            importlib.import_module(f"app.models.{m.name}")
        except Exception:
            pass

    out: dict[str, dict[str, bool]] = {}
    for base_mod, base_name in (("app.core.database", "Base"),
                                ("app.core.cycle_purchase_database", "CyclePurchaseBase")):
        try:
            base = getattr(importlib.import_module(base_mod), base_name)
        except Exception:
            continue
        for mapper in base.registry.mappers:
            cls = mapper.class_
            cols: dict[str, bool] = {}
            for prop in mapper.column_attrs:
                col = prop.columns[0]
                cols[prop.key] = bool(col.nullable)
            out[cls.__name__] = cols
    return out


def describe(node: ast.AST) -> tuple[str | None, str | None, str]:
    """把 order_by 的一個參數拆成 (Model, column, 方向)。解析不了就回 (None, None, ...)。"""
    direction = "asc"
    # Model.col.desc() / .asc() / .nullsfirst() / .nullslast()
    while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        name = node.func.attr
        if name in ("desc", "asc"):
            direction = name
        elif name in ("nullsfirst", "nullslast"):
            return None, None, "explicit"      # 已明確指定，不受影響
        node = node.func.value
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id, node.attr, direction
    return None, None, direction


def main() -> None:
    show_all = "--all" in sys.argv
    colmap = build_column_map()

    risky: list[tuple] = []
    safe = 0
    explicit = 0
    unresolved: list[tuple] = []

    for d in SCAN_DIRS:
        root = os.path.join(BACKEND, d)
        for dirpath, _, files in os.walk(root):
            if "__pycache__" in dirpath:
                continue
            for fn in sorted(files):
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(dirpath, fn)
                rel = os.path.relpath(path, BACKEND).replace("\\", "/")
                try:
                    tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if not (isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Attribute)
                            and node.func.attr == "order_by"):
                        continue
                    for arg in node.args:
                        model, col, direction = describe(arg)
                        if direction == "explicit":
                            explicit += 1
                        elif model and col:
                            nullable = colmap.get(model, {}).get(col)
                            if nullable is None:
                                unresolved.append((rel, node.lineno, f"{model}.{col}", "找不到此欄位"))
                            elif nullable:
                                risky.append((rel, node.lineno, f"{model}.{col}", direction))
                            else:
                                safe += 1
                        else:
                            unresolved.append((rel, node.lineno, ast.unparse(arg)[:44], "非 Model.欄位"))

    total = len(risky) + safe + explicit + len(unresolved)
    print("=" * 78)
    print("  ORDER BY 的 NULL 排序風險盤點")
    print("=" * 78)
    print(f"  掃到 order_by 參數共 {total} 個\n")
    print(f"  ❗ 可為 NULL、未指定 NULLS 位置 : {len(risky):>4}  ← 遷移後順序會變")
    print(f"  ✅ NOT NULL 欄位                : {safe:>4}  ← 不受影響")
    print(f"  ✅ 已明確寫 nullsfirst/nullslast: {explicit:>4}  ← 不受影響")
    print(f"  ?  無法靜態解析                 : {len(unresolved):>4}  ← 需人工看")

    if risky:
        print()
        print("-" * 78)
        print("  ❗ 需要決定的（依檔案分組）")
        print("-" * 78)
        by_file: dict[str, list] = defaultdict(list)
        for rel, line, what, direction in risky:
            by_file[rel].append((line, what, direction))
        for rel in sorted(by_file):
            print(f"\n  {rel}")
            for line, what, direction in sorted(by_file[rel]):
                # ⚠️ SQLite 的 NULL 永遠最前；PG 是 ASC 最後、DESC 最前
                moves = "NULL 由最前 → 最後" if direction == "asc" else "NULL 位置不變（都在最前）"
                mark = "❗" if direction == "asc" else "·"
                print(f"    {mark} L{line:<5} {what:<44} {direction:<5} {moves}")

    if unresolved and show_all:
        print()
        print("-" * 78)
        print("  ? 無法靜態解析（多半是先組變數再傳進 order_by）")
        print("-" * 78)
        for rel, line, what, why in unresolved[:60]:
            print(f"    {rel}:{line}  {what}  （{why}）")
        if len(unresolved) > 60:
            print(f"    … 另外 {len(unresolved) - 60} 處")

    print()
    print("=" * 78)
    print("""  怎麼判讀
    · DESC 的其實不用動 —— SQLite 與 PostgreSQL 的 DESC 都把 NULL 排最前，行為一致
    · **ASC 才是真的會變**：NULL 從最前面跑到最後面
    · 要固定行為就在後面接 `.nullsfirst()`（維持 SQLite 的舊行為）
      或 `.nullslast()`（採用 PostgreSQL 的預設）
    · 也可以什麼都不做 —— 前提是那一欄實際上沒有 NULL 值，
      或那幾列排在哪裡對使用者無所謂""")
    print()


if __name__ == "__main__":
    main()
