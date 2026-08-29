"""
檢查（並清掉）失敗的 batch migration 在 SQLite 留下的 `_alembic_tmp_*` 殘骸

背景（2026-08-29）
────────────────────────────────────────────────────────────────────────────
⚠️⚠️ **SQLite 上，失敗的 migration 不會回滾。**
pysqlite driver 不會在 DDL 前開交易，所以每一個 `CREATE`／`DROP`／
`ALTER ... RENAME` 都立即生效。多步驟的 migration 中途失敗時，
前面幾步**已經留在資料庫裡**了。

Alembic 的 batch 模式在 SQLite 上是這樣改欄位的：

    ① CREATE TABLE _alembic_tmp_X (新結構)
    ② INSERT INTO _alembic_tmp_X SELECT * FROM X      ← 資料搬過去
    ③ DROP TABLE X                                     ← 原表沒了
    ④ ALTER TABLE _alembic_tmp_X RENAME TO X

⚠️⚠️ **停在 ③ 和 ④ 之間的話，`_alembic_tmp_X` 是資料的唯一副本。**
   這種情況**絕對不能直接 DROP**，要 RENAME 回去。本腳本會分辨這兩種情形。

三種殘骸，處置完全不同：

| 情況 | 判斷 | 處置 |
|------|------|------|
| 停在 ①～② 之間 | 正表在、tmp 筆數 ≤ 正表 | tmp 可安全刪除 |
| 停在 ③～④ 之間 | **正表不見了** | ⚠️ **tmp 改名回去**，不可刪 |
| tmp 筆數 > 正表 | 說不通 | ⚠️ 不動，人工判斷 |

⚠️ 預設唯讀。要實際修改必須加 `--fix`。
⚠️ 動手前請先複製一份資料庫檔案。

執行：
    cd backend
    py -3.12 scripts\\check_alembic_tmp_leftover.py          # 只看不改
    py -3.12 scripts\\check_alembic_tmp_leftover.py --fix    # 實際處理
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

from sqlalchemy import inspect, text                             # noqa: E402

PREFIX = "_alembic_tmp_"


def report(engine, label: str, do_fix: bool) -> int:
    print("=" * 78)
    print(f"  {label}")
    print(f"  {engine.url}")
    print("=" * 78)

    names = set(inspect(engine).get_table_names())
    tmps = sorted(n for n in names if n.startswith(PREFIX))

    if not tmps:
        print("  ✅ 沒有 _alembic_tmp_* 殘骸\n")
        return 0

    print(f"  找到 {len(tmps)} 個殘骸：\n")
    actions: list[tuple[str, str, str]] = []      # (動作, tmp, 正表)

    with engine.connect() as c:
        for tmp in tmps:
            real = tmp[len(PREFIX):]
            tmp_n = c.execute(text(f"SELECT COUNT(*) FROM {tmp}")).scalar_one()
            if real in names:
                real_n = c.execute(text(f"SELECT COUNT(*) FROM {real}")).scalar_one()
                print(f"    {tmp}")
                print(f"        殘骸 {tmp_n:,} 列 ｜ 正表 {real} {real_n:,} 列")
                if tmp_n <= real_n:
                    print("        → 停在建表／複製階段，正表完好。**殘骸可安全刪除**")
                    actions.append(("drop", tmp, real))
                else:
                    print("        → ⚠️ 殘骸比正表多，說不通。**不處理**，請人工判斷")
                    actions.append(("skip", tmp, real))
            else:
                print(f"    {tmp}")
                print(f"        殘骸 {tmp_n:,} 列 ｜ ⚠️⚠️ **正表 {real} 不存在**")
                print("        → 停在「原表已刪、還沒改名」之間。")
                print("           **這是資料的唯一副本，絕不可刪** → 改名回去")
                actions.append(("rename", tmp, real))
            print()

    n_drop = sum(1 for a, _, _ in actions if a == "drop")
    n_ren = sum(1 for a, _, _ in actions if a == "rename")
    n_skip = sum(1 for a, _, _ in actions if a == "skip")
    print("-" * 78)
    print(f"  可刪除 {n_drop} ｜ 需改名回去 {n_ren} ｜ 需人工判斷 {n_skip}")

    if not do_fix:
        print("\n  （唯讀模式，未修改任何東西）")
        print("  ⚠️ 先把資料庫檔案複製一份備份，再加 --fix 執行。\n")
        return 1

    print("\n  --fix：開始處理…")
    with engine.begin() as c:
        for act, tmp, real in actions:
            if act == "drop":
                c.execute(text(f"DROP TABLE {tmp}"))
                print(f"    🗑  已刪除 {tmp}")
            elif act == "rename":
                c.execute(text(f"ALTER TABLE {tmp} RENAME TO {real}"))
                print(f"    ♻️  已把 {tmp} 改名回 {real}（救回資料）")
            else:
                print(f"    ⏭  略過 {tmp}（需人工判斷）")
    print()
    return 0 if n_skip == 0 else 1


def main() -> int:
    do_fix = "--fix" in sys.argv
    from app.core.database import engine
    from app.core.cycle_purchase_database import cycle_purchase_engine
    engine.echo = cycle_purchase_engine.echo = False

    rc = report(engine, "主庫 portal.db", do_fix)
    rc |= report(cycle_purchase_engine, "週期採購 cycle-purchase.db", do_fix)

    if rc and not do_fix:
        print("  接著要做的：")
        print("    ① 複製一份 C:\\portal_data\\portal.db 當備份")
        print("    ② py -3.12 scripts\\check_alembic_tmp_leftover.py --fix")
        print("    ③ py -3.12 scripts\\check_schema_drift.py    ← 確認回到乾淨狀態")
        print("    ④ py -3.12 -m alembic current                ← 確認版本沒被改動\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
