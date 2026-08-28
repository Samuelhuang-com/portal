"""
部署用：檢查並套用 Alembic migration（`prod-update.bat` 的 [3/6] 會呼叫）

設計原則
────────────────────────────────────────────────────────────────────────────
⚠️ **不做靜默自動升級。** schema 變更套用在正式區沒有攔截點是很危險的事，
   所以流程是「先看清楚要做什麼 → 人按 Enter → 才執行」。

⚠️ **沒 stamp 過的資料庫一律停下來，不要硬跑 `upgrade`。**
   那台若沒有 `alembic_version` 表，`upgrade head` 會從 baseline 開始跑，
   試圖建立 163 張**已經存在**的表然後失敗，錯誤訊息還很難懂。
   正確做法是先跑 `scripts/alembic_stamp_baseline.py`。

回傳碼
    0 = 一切就緒（沒有待套用，或已成功套用）
    2 = 需要人工處理（尚未 stamp／版本對不上／使用者取消）
    1 = 執行失敗

用法
    cd backend
    python scripts\\alembic_deploy.py            # 互動，會停下來確認
    python scripts\\alembic_deploy.py --yes      # 不詢問直接套用
    python scripts\\alembic_deploy.py --check    # 只檢查不套用（給 CI／巡檢用）
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

# (顯示名稱, ini 檔, 這個庫的 engine 屬性取法)
TARGETS = [
    ("main database (portal.db)", "alembic.ini", "main"),
    ("cycle-purchase database", "alembic_cp.ini", "cp"),
]


def _engine(kind: str):
    if kind == "main":
        from app.core.database import engine
        return engine
    from app.core.cycle_purchase_database import cycle_purchase_engine
    return cycle_purchase_engine


def _alembic(ini: str, *args: str) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", ini, *args],
        cwd=BACKEND, capture_output=True, text=True,
    )
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _db_version(eng) -> str | None:
    insp = inspect(eng)
    if "alembic_version" not in insp.get_table_names():
        return None
    with eng.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    return row[0] if row else None


def _heads(ini: str) -> list[str]:
    code, out = _alembic(ini, "heads")
    if code != 0:
        return []
    # 每行像 "baseline_main (head)"
    return [ln.split()[0] for ln in out.splitlines() if ln.strip()]


def inspect_target(label: str, ini: str, kind: str) -> tuple[str, str]:
    """回傳 (狀態, 訊息)。狀態 = ok / pending / not_stamped / error"""
    print()
    print("-" * 70)
    print(f"  {label}")
    try:
        eng = _engine(kind)
        eng.echo = False
    except Exception as exc:
        return "error", f"無法建立 engine：{exc}"

    print(f"  {eng.url}")
    print("-" * 70)

    cur = _db_version(eng)
    if cur is None:
        return "not_stamped", (
            "這個資料庫沒有 alembic_version 表（從未 stamp 過）。\n"
            "     不要直接跑 upgrade —— 它會從 baseline 開始建已存在的表然後失敗。\n"
            "     請先執行：  python scripts\\alembic_stamp_baseline.py")

    heads = _heads(ini)
    if not heads:
        return "error", "無法取得 head 版本（alembic heads 失敗）"

    print(f"  目前版本：{cur}")
    print(f"  最新版本：{', '.join(heads)}")

    if cur in heads:
        print("  ✅ 已是最新，沒有待套用的 migration")
        return "ok", ""

    # ⚠️ 範圍要用 `-r cur:heads`，寫成位置參數 `history cur:heads` 會被
    #    argparse 當成未知參數而報錯（且錯誤訊息不會出現在畫面上）。
    code, out = _alembic(ini, "history", "-r", f"{cur}:heads")
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()] if code == 0 else []
    # 只留「本次會往前跑」的那幾筆；`<base> -> 目前版本` 那行是已套用的，濾掉
    lines = [ln for ln in lines if not ln.startswith("<base>")]
    print("  ⬇ 待套用：")
    if lines:
        for ln in lines:
            print(f"     {ln}")
    else:
        print(f"     （取不到明細，請自行確認 {cur} → {', '.join(heads)}）")
    return "pending", ""


def main() -> int:
    args = set(sys.argv[1:])
    auto_yes = "--yes" in args or "-y" in args
    check_only = "--check" in args

    print("=" * 70)
    print("  Alembic 部署檢查")
    print("=" * 70)

    results = []
    for label, ini, kind in TARGETS:
        state, msg = inspect_target(label, ini, kind)
        if msg:
            print(f"  ⚠️  {msg}")
        results.append((label, ini, state))

    blocked = [r for r in results if r[2] in ("not_stamped", "error")]
    pending = [r for r in results if r[2] == "pending"]

    print()
    print("=" * 70)
    if blocked:
        print("  ❌ 需要人工處理，本次不套用任何 migration：")
        for label, _, state in blocked:
            print(f"     · {label} → {state}")
        print()
        return 2

    if not pending:
        print("  ✅ 兩個資料庫都已是最新，沒有需要套用的 migration。")
        print()
        return 0

    print(f"  有 {len(pending)} 個資料庫需要套用 migration：")
    for label, _, _ in pending:
        print(f"     · {label}")
    print()

    if check_only:
        print("  （--check 模式，不執行套用）")
        return 2

    if not auto_yes:
        print("  ⚠️ 這會變更正式資料庫的結構。確認上面的清單無誤再繼續。")
        try:
            ans = input("  要套用嗎？輸入 y 執行，其他任意鍵取消： ").strip().lower()
        except EOFError:
            ans = ""
        if ans not in ("y", "yes"):
            print("  已取消，沒有套用任何變更。")
            return 2

    print()
    for label, ini, _ in pending:
        print(f"  → {label}：alembic -c {ini} upgrade head")
        code, out = _alembic(ini, "upgrade", "head")
        tail = "\n".join(out.strip().splitlines()[-12:])
        print("    " + tail.replace("\n", "\n    "))
        if code != 0:
            print(f"  ❌ {label} 套用失敗")
            return 1
        print(f"  ✅ {label} 完成")

    print()
    print("  ✅ 全部套用完成。")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
