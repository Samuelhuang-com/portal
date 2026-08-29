"""
Phase 2：把 Portal 的資料來源從 SQLite 切到 PostgreSQL（含回退）

⚠️⚠️ 這是**唯一一支會改變 Portal 實際讀寫對象**的腳本。
   在此之前的所有工具都只是「複製 + 比對」，SQLite 全程是唯一來源。

切換本身只有一行設定：`backend/.env` 的 `DATABASE_URL`。
真正需要小心的是**順序**與**回退時的資料落差**。

四個動作
────────────────────────────────────────────────────────────────────────────
    --check      前置檢查（預設）。不改任何東西。
    --migrate    重新把 SQLite 的資料搬進 PostgreSQL（**服務必須先停**）。
    --switch     把 .env 的 DATABASE_URL 指向 PostgreSQL。
    --rollback   指回 SQLite。

⚠️⚠️ **回退會遺失切換後寫進 PostgreSQL 的所有資料。**
   切回 SQLite 之後，Portal 讀到的是**切換當下那一刻的快照** ——
   這段期間使用者建立的報修單、請購單、同步進來的 Ragic 資料，全部看不到。
   所以：
     · 切換後的觀察期越短越好，出問題就立刻回退
     · 觀察期一過（確認沒問題），SQLite 就不再是可用的回退點了
   本腳本會把切換時間寫進 `.pg_cutover_at`，回退時算給你看落差多久。

⚠️ **預算模組（`app/core/budget_database.py`）用裸的 `sqlite3.connect()`，
   不經過 SQLAlchemy，`DATABASE_URL` 對它完全無效。** 它會繼續用 SQLite。
   （使用者確認：該模組尚未上線，不影響切換。）

正常流程
────────────────────────────────────────────────────────────────────────────
    1. 停掉 Portal 服務            net stop PortalBackend
    2. py -3.12 scripts\\pg_cutover.py --check      ← 全綠才往下
    3. py -3.12 scripts\\pg_cutover.py --migrate    ← 重搬最新資料
    4. py -3.12 scripts\\pg_cutover.py --switch
    5. 啟動服務                    net start PortalBackend
    6. 開瀏覽器實際點過幾個頁面

出問題時
    1. 停服務
    2. py -3.12 scripts\\pg_cutover.py --rollback
    3. 啟動服務
"""
from __future__ import annotations

import datetime as dt
import os
import re
import shutil
import subprocess
import sys

# ⚠️ 輸出強制 UTF-8：導向檔案時 Python 會改用 cp950，emoji 編不進去會整支中斷。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRIPTS = os.path.join(BACKEND, "scripts")
ENV_PATH = os.path.join(BACKEND, ".env")
STAMP = os.path.join(BACKEND, ".pg_cutover_at")
sys.path.insert(0, BACKEND)

PAIRS = [
    # (SQLite 的 key, PostgreSQL 的 key, 顯示名)
    ("DATABASE_URL", "POSTGRES_URL", "主庫"),
    ("CYCLE_PURCHASE_DATABASE_URL", "CYCLE_PURCHASE_POSTGRES_URL", "週期採購"),
]


def mask(u: str) -> str:
    return re.sub(r"://([^:/@]+):([^@]*)@", r"://\1:****@", u or "")


def read_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if not os.path.exists(ENV_PATH):
        return out
    for line in open(ENV_PATH, encoding="utf-8", errors="ignore"):
        m = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$", line)
        if m:
            out.setdefault(m.group(1), m.group(2).strip().strip('"').strip("'"))
    return out


def set_env_keys(updates: dict[str, str]) -> str:
    """就地改寫 .env 的指定 key，回傳備份檔路徑。

    ⚠️ 逐行改寫而不是整檔重生 —— .env 有 190 多行、含註解與密碼，
       重生等於把使用者的排版與註解洗掉。
    ⚠️ 只改**第一個**符合的行（read_env 也是取第一個，兩邊要一致）。
    """
    # ⚠️ 檔名含毫秒：switch 與 rollback 在同一秒內發生時，
    #    同名會讓後者**覆蓋掉正要拿來還原的那份**。
    bak = ENV_PATH + f".bak-{dt.datetime.now():%Y%m%d_%H%M%S_%f}"
    shutil.copy2(ENV_PATH, bak)
    lines = open(ENV_PATH, encoding="utf-8", errors="ignore").read().splitlines(keepends=True)
    done: set[str] = set()
    for i, line in enumerate(lines):
        m = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=", line)
        if not m:
            continue
        k = m.group(1)
        if k in updates and k not in done:
            nl = "\r\n" if line.endswith("\r\n") else "\n"
            lines[i] = f"{k}={updates[k]}{nl}"
            done.add(k)
    missing = set(updates) - done
    if missing:
        raise RuntimeError(f".env 找不到這些 key，無法改寫：{sorted(missing)}")
    with open(ENV_PATH, "w", encoding="utf-8", newline="") as f:
        f.writelines(lines)
    return bak


def port_busy(port: int = 8000) -> bool:
    """8000 埠還有人在聽 ＝ 服務還跑著。"""
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                             timeout=20).stdout
    except Exception:
        return False
    return any(f":{port}" in ln and "LISTENING" in ln for ln in out.splitlines())


def run(script: str, *args) -> int:
    print(f"\n  ── {script} {' '.join(args)}")
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args],
                       cwd=BACKEND)
    return r.returncode


def now_url_kind(env: dict) -> str:
    u = env.get("DATABASE_URL", "")
    return "postgresql" if u.startswith("postgres") else "sqlite"


# ── 動作 ────────────────────────────────────────────────────────────────────

def do_check(env: dict) -> int:
    print("=" * 78)
    print("  Phase 2 前置檢查")
    print("=" * 78)
    bad = 0

    print(f"\n  目前的資料來源：**{now_url_kind(env).upper()}**")
    for lite_k, pg_k, label in PAIRS:
        print(f"    {label:<8} 現在 → {mask(env.get(lite_k, '(未設定)'))}")
        print(f"    {label:<8} 目標 → {mask(env.get(pg_k, '(未設定)'))}")
        if not env.get(pg_k):
            print(f"    ❌ .env 缺少 {pg_k}")
            bad += 1

    print("\n  ① 服務是否已停（搬資料時 SQLite 不能有人在寫）")
    if port_busy():
        print("    ❌ 8000 埠仍有人在聽 —— **先停服務**：net stop PortalBackend")
        print("       ⚠️ 服務還跑著就搬，搬到一半寫進來的資料會遺失。")
        bad += 1
    else:
        print("    ✅ 8000 埠沒有人在聽")

    print("\n  ② schema 與 Model 一致（drift）")
    bad += 1 if run("check_schema_drift.py") else 0

    print("\n  ③ 外鍵孤兒（PostgreSQL 會擋）")
    bad += 1 if run("pg_show_orphans.py") else 0
    bad += 1 if run("pg_show_orphans.py", "--cycle-purchase") else 0

    print("\n" + "=" * 78)
    if bad:
        print(f"  ❌ 有 {bad} 項未通過，**先不要切換**。\n")
        return 2
    print("""  ✅ 前置檢查全部通過。

  下一步：
      py -3.12 scripts\\pg_cutover.py --migrate
""")
    return 0


def do_migrate(env: dict) -> int:
    print("=" * 78)
    print("  重新把 SQLite 的資料搬進 PostgreSQL")
    print("=" * 78)
    if now_url_kind(env) == "postgresql":
        print("""
  ❌ `DATABASE_URL` 已經指向 PostgreSQL，不能執行 --migrate。

     ⚠️ 那會把 **PostgreSQL 自己**當成來源重搬一次，等於清空再灌回去 ——
        中間如果出錯，正在服務的資料就沒了。
     要重搬請先 --rollback 指回 SQLite。
""")
        return 2
    if port_busy():
        print("\n  ❌ 8000 埠仍有人在聽。**先停服務**再搬。\n")
        return 2

    print("\n  ⚠️ 兩個資料庫都會**先 DROP 再重建**，PostgreSQL 現有內容會被覆蓋。")
    print("     （SQLite 全程唯讀，不受影響。）")
    rc = run("pg_migrate_pilot.py", "--all")
    if rc:
        print("\n  ❌ 主庫搬運未完全成功，**先不要切換**。\n")
        return 2
    rc = run("pg_migrate_pilot.py", "--cycle-purchase")
    if rc:
        print("\n  ❌ 週採搬運未完全成功，**先不要切換**。\n")
        return 2

    print("""
  ✅ 兩個資料庫都搬完了。

  下一步（可選但建議）：跑一次讀取比對，確認兩邊結果一致
      py -3.12 scripts\\pg_compare_reads.py --all --days 180
      py -3.12 scripts\\pg_compare_reads.py --cycle-purchase

  然後：
      py -3.12 scripts\\pg_cutover.py --switch
""")
    return 0


def do_switch(env: dict) -> int:
    print("=" * 78)
    print("  切換：DATABASE_URL → PostgreSQL")
    print("=" * 78)
    if now_url_kind(env) == "postgresql":
        print("\n  ✅ 已經指向 PostgreSQL，不需要重複切換。\n")
        return 0
    if port_busy():
        print("\n  ⚠️ 8000 埠仍有人在聽。建議**先停服務**再切，"
              "否則舊行程還連著 SQLite、新連線連 PostgreSQL，兩邊各寫各的。\n")
        return 2

    updates = {}
    for lite_k, pg_k, _ in PAIRS:
        if env.get(pg_k):
            updates[lite_k] = env[pg_k]
    if not updates:
        print("\n  ❌ .env 沒有可用的 *_POSTGRES_URL。\n")
        return 2

    bak = set_env_keys(updates)
    with open(STAMP, "w", encoding="utf-8") as f:
        f.write(dt.datetime.now().isoformat(timespec="seconds"))

    print(f"\n  ✅ 已改寫 .env（備份：{os.path.basename(bak)}）")
    for k, v in updates.items():
        print(f"      {k} = {mask(v)}")
    print(f"  ✅ 切換時間已記錄：{os.path.basename(STAMP)}")
    print("""
  ⚠️⚠️ **從現在起，SQLite 的內容就凝固在切換前那一刻。**
     切換後寫進 PostgreSQL 的資料，回退時**一筆都拿不回來**。
     觀察期越短越好，出問題立刻 --rollback。

  下一步：
      net start PortalBackend
      開瀏覽器實際點過：合約管理、請購單、任一個清單頁、任一個統計頁
""")
    return 0


def do_rollback(env: dict) -> int:
    print("=" * 78)
    print("  回退：DATABASE_URL → SQLite")
    print("=" * 78)
    if now_url_kind(env) == "sqlite":
        print("\n  ✅ 已經指向 SQLite，不需要回退。\n")
        return 0

    since = ""
    if os.path.exists(STAMP):
        try:
            t = dt.datetime.fromisoformat(open(STAMP, encoding="utf-8").read().strip())
            d = dt.datetime.now() - t
            since = (f"{t:%Y-%m-%d %H:%M:%S}（{int(d.total_seconds() // 3600)} 小時 "
                     f"{int(d.total_seconds() % 3600 // 60)} 分鐘前）")
        except Exception:
            pass

    print(f"""
  ⚠️⚠️ **這會遺失切換之後寫進 PostgreSQL 的所有資料。**
     切換時間：{since or '（沒有紀錄）'}
     這段期間的報修單、請購單、Ragic 同步結果 —— 回到 SQLite 後全部看不到。
     ⚠️ PostgreSQL 的資料**不會被刪除**，只是 Portal 不再讀它；
        真的需要的話還可以事後撈出來，但那是另一件工程。
""")
    if port_busy():
        print("  ❌ 8000 埠仍有人在聽。**先停服務**再回退。\n")
        return 2
    try:
        ans = input("  確定要回退嗎？輸入 rollback 執行： ").strip()
    except EOFError:
        ans = ""
    if ans != "rollback":
        print("  已取消，未修改任何設定。\n")
        return 1

    # ⚠️⚠️ 從備份找回原本的 SQLite URL —— 不用猜、不用組字串。
    #    但**不能直接取最新的備份**（2026-08-29 實測抓到的 bug）：
    #    每次 set_env_keys 都會產生一份備份，包含 --rollback 自己。
    #    第二次回退時「最新的備份」會是第一次回退產生的那份，
    #    而它裡面的 DATABASE_URL 是**切換後的 PostgreSQL** ——
    #    照著還原等於什麼都沒做，而且看起來像成功了。
    #    正確做法：由新到舊找出**第一份 DATABASE_URL 真的是 sqlite** 的備份。
    def _sqlite_urls(path: str) -> dict[str, str]:
        got: dict[str, str] = {}
        for line in open(path, encoding="utf-8", errors="ignore"):
            m = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$", line)
            if m and m.group(1) in {p[0] for p in PAIRS} and m.group(1) not in got:
                got[m.group(1)] = m.group(2).strip().strip('"').strip("'")
        return got

    old, src = {}, None
    for name in sorted((f for f in os.listdir(BACKEND) if f.startswith(".env.bak-")),
                       reverse=True):
        cand = _sqlite_urls(os.path.join(BACKEND, name))
        if cand.get("DATABASE_URL", "").startswith("sqlite"):
            old, src = cand, name
            break
    if not old:
        print("""
  ❌ 所有 `.env.bak-*` 裡的 DATABASE_URL 都不是 sqlite，找不到可還原的來源。
     請手動把 .env 的 DATABASE_URL / CYCLE_PURCHASE_DATABASE_URL
     改回 sqlite:///C:/portal_data/... 的形式。
""")
        return 2

    bak = set_env_keys(old)
    print(f"\n  ✅ 已從 {src} 還原（本次備份：{os.path.basename(bak)}）")
    for k, v in old.items():
        print(f"      {k} = {mask(v)}")
    print("\n  下一步：net start PortalBackend\n")
    return 0


def main() -> int:
    args = sys.argv[1:]
    env = read_env()
    if "--migrate" in args:
        return do_migrate(env)
    if "--switch" in args:
        return do_switch(env)
    if "--rollback" in args:
        return do_rollback(env)
    return do_check(env)


if __name__ == "__main__":
    sys.exit(main())
