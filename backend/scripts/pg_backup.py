"""
PostgreSQL 每日備份：pg_dump ＋ **驗證** ＋ 保留期清理

背景（2026-08-29，正式區切到 PostgreSQL 當天）
────────────────────────────────────────────────────────────────────────────
⚠️⚠️ **切換之後，原本的備份方式就失效了，而且不會有任何警訊。**
   切換前備份 ＝ 複製 `C:\\portal_data` 的 `.db` 檔。切換之後那兩個檔案
   **凍結在切換那一刻**，再怎麼複製都只是備份一份停在過去的資料 ——
   檔案還在、複製還會成功、排程還是綠燈，但內容永遠不再更新。

   `TECH_SPEC.md` 早就寫著「備份｜pg_dump 每日｜至少保留 7 天」，
   但從來沒有實作過。這支腳本就是那一行。

⚠️⚠️ **任何一步失敗都 exit 非 0，而且不吞例外。**
   `prod-update.bat` 那種「印個 `[WARN]` 就繼續」的作法用在備份上
   等於沒有備份 —— 你會一直以為有，直到需要還原的那天才發現。

⚠️⚠️ **沒有還原過的備份不算備份。**
   `pg_dump` 回 0 只代表「寫出了一個檔案」，不代表那個檔案還原得回來。
   所以本腳本每次都會用 `pg_restore --list` 讀一次剛產生的檔（能列出物件
   才算數），另外提供 `--verify-restore` 真的還原到一個暫存資料庫、
   逐表比對筆數。**建議每月至少跑一次 --verify-restore。**

⚠️ 備份放在同一台機器上**不是真備份** —— 硬碟壞掉會一起帶走。
   本腳本只負責產生與驗證，「複製到另一台／雲端」請另外排程。

設定（都在 backend/.env，沒設就用預設）
    PG_BACKUP_DIR              預設 D:\\portal_backup\\pg（跟資料庫不同磁碟）
    PG_BACKUP_RETENTION_DAYS   預設 14
    PG_BIN                     pg_dump/pg_restore 所在目錄，預設自動尋找

執行：
    cd backend
    py -3.11 scripts\\pg_backup.py                  # 備份 + 驗證 + 清理
    py -3.11 scripts\\pg_backup.py --dry-run        # 只看會做什麼
    py -3.11 scripts\\pg_backup.py --status         # 上次成功是什麼時候
    py -3.11 scripts\\pg_backup.py --verify-restore # ⭐ 真的還原一次來驗證

排程（正式區，系統管理員身分）：
    schtasks /Create /TN "Portal PG Backup" /SC DAILY /ST 03:30 /RU SYSTEM /RL HIGHEST ^
      /TR "cmd /c cd /d D:\\portal\\backend && py -3.11 scripts\\pg_backup.py >> D:\\portal\\logs\\pg_backup.log 2>&1"
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys

# ⚠️ 輸出強制 UTF-8：Windows 主控台是 UTF-8，但**導向檔案時 Python 改用 cp950**，
#    ⚠️ ✅ ❌ 一律編不進去 → UnicodeEncodeError。排程一定是導向檔案的。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ENV_PATH = os.path.join(BACKEND, ".env")

DEFAULT_DIR = r"D:\portal_backup\pg" if os.name == "nt" else "/var/backups/portal-pg"
DEFAULT_RETENTION = 14
STATUS_NAME = "_status.json"

# (.env 的 key, 備份檔名前綴, 顯示名)
TARGETS = [
    ("DATABASE_URL", "portal", "主庫"),
    ("CYCLE_PURCHASE_DATABASE_URL", "cycle_purchase", "週期採購"),
]

# pg_dump 在 Windows 上的常見位置（新版排前面 —— 見 find_bin 的說明）
WIN_HINTS = [rf"C:\Program Files\PostgreSQL\{v}\bin" for v in (18, 17, 16, 15, 14, 13)]


def read_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if not os.path.exists(ENV_PATH):
        return out
    for line in open(ENV_PATH, encoding="utf-8", errors="ignore"):
        m = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$", line)
        if m:
            out.setdefault(m.group(1), m.group(2).strip().strip('"').strip("'"))
    return out


def mask(u: str) -> str:
    return re.sub(r"://([^:/@]+):([^@]*)@", r"://\1:****@", u or "")


def find_bin(name: str, env: dict) -> str:
    """找 pg_dump / pg_restore。

    ⚠️ **pg_dump 的版本必須 >= 伺服器版本。** 用舊版去 dump 新版伺服器，
       pg_dump 會直接拒絕（`server version mismatch`）。Windows 上如果裝過
       多個版本，PATH 上排到的常常是舊的那個 —— 所以這裡**優先找新版目錄**，
       PATH 反而放最後。
    """
    exe = name + (".exe" if os.name == "nt" else "")
    hint = env.get("PG_BIN") or os.environ.get("PG_BIN")
    cands = ([os.path.join(hint, exe)] if hint else []) + \
            [os.path.join(d, exe) for d in WIN_HINTS]
    for c in cands:
        if os.path.isfile(c):
            return c
    found = shutil.which(name)
    if found:
        return found
    raise SystemExit(
        f"❌ 找不到 {name}。請在 .env 設 PG_BIN 指向 PostgreSQL 的 bin 目錄，例如：\n"
        f"       PG_BIN=C:\\Program Files\\PostgreSQL\\18\\bin")


def split_url(url: str):
    """從 SQLAlchemy URL 取出 pg_dump 需要的連線參數與密碼。

    ⚠️ 密碼**不會**出現在命令列 —— 走 PGPASSWORD 環境變數傳給子行程。
       命令列參數在 Windows 的工作管理員／`wmic process` 裡看得到，
       密碼寫進去等於印在螢幕上。
    """
    from sqlalchemy.engine import make_url
    u = make_url(url)
    return {
        "host": u.host or "localhost",
        "port": str(u.port or 5432),
        "user": u.username or "postgres",
        "password": u.password or "",
        "dbname": u.database or "",
    }


def run(cmd: list[str], password: str, timeout: int = 3600):
    e = dict(os.environ)
    if password:
        e["PGPASSWORD"] = password
    return subprocess.run(cmd, env=e, capture_output=True, text=True,
                          errors="replace", timeout=timeout)


def dump_one(pg_dump: str, url: str, out_path: str, label: str, dry: bool) -> tuple[bool, str]:
    c = split_url(url)
    cmd = [pg_dump, "-h", c["host"], "-p", c["port"], "-U", c["user"],
           "-d", c["dbname"], "-Fc", "--no-owner", "--no-privileges",
           "-f", out_path]
    if dry:
        print(f"    [dry-run] {' '.join(cmd)}")
        return True, "dry-run"
    r = run(cmd, c["password"])
    if r.returncode != 0:
        return False, (r.stderr or r.stdout or "").strip().splitlines()[-1][:200] \
            if (r.stderr or r.stdout) else f"returncode={r.returncode}"
    if not os.path.exists(out_path):
        return False, "pg_dump 回 0 但檔案不存在"
    size = os.path.getsize(out_path)
    if size < 1024:
        return False, f"檔案只有 {size} bytes，明顯不對"
    return True, f"{size / 1024 / 1024:.1f} MB"


def verify_dump(pg_restore: str, path: str) -> tuple[bool, str]:
    """讀一次剛產生的檔 —— `pg_dump` 回 0 只代表寫出了檔案，不代表讀得回來。"""
    r = subprocess.run([pg_restore, "--list", path], capture_output=True,
                       text=True, errors="replace", timeout=600)
    if r.returncode != 0:
        return False, (r.stderr or "").strip().splitlines()[-1][:200]
    # ⚠️ 只數 `TABLE DATA` —— 那才是「有資料被備進去」的項目。
    #    數 " TABLE " 會把建表語句與資料各算一次，報出來的張數是兩倍
    #    （實測 2 張表報成 4）。驗證訊息裡的數字不準，比沒有數字更糟。
    tables = sum(1 for ln in r.stdout.splitlines() if "TABLE DATA " in ln)
    if tables == 0:
        return False, "檔案讀得開，但裡面沒有任何資料表的資料"
    return True, f"{tables} 張表的資料"


def prune(root: str, days: int, dry: bool) -> int:
    cutoff = dt.datetime.now() - dt.timedelta(days=days)
    n = 0
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not os.path.isdir(d) or not re.fullmatch(r"\d{8}_\d{6}", name):
            continue
        try:
            when = dt.datetime.strptime(name, "%Y%m%d_%H%M%S")
        except ValueError:
            continue
        if when < cutoff:
            print(f"    🗑  {name}（{(dt.datetime.now() - when).days} 天前）"
                  + ("  [dry-run]" if dry else ""))
            if not dry:
                shutil.rmtree(d, ignore_errors=True)
            n += 1
    return n


def show_status(root: str) -> int:
    p = os.path.join(root, STATUS_NAME)
    if not os.path.exists(p):
        print(f"  ❌ 沒有 {p} —— **從來沒有成功備份過**。")
        return 1
    s = json.load(open(p, encoding="utf-8"))
    last = dt.datetime.fromisoformat(s["last_success"])
    age = dt.datetime.now() - last
    print(f"  上次成功：{last:%Y-%m-%d %H:%M:%S}（{age.days} 天 "
          f"{age.seconds // 3600} 小時前）")
    for k, v in s.get("targets", {}).items():
        print(f"      {k:<16}{v}")
    if age > dt.timedelta(days=2):
        print(f"\n  ⚠️⚠️ 已經 {age.days} 天沒有成功備份了。排程可能壞了 —— "
              "去看 D:\\portal\\logs\\pg_backup.log")
        return 1
    print("\n  ✅ 備份是新的")
    return 0


def verify_restore(env: dict) -> int:
    """⭐ 真的把最新的備份還原到一個暫存資料庫，逐表比對筆數。

    ⚠️ `pg_restore --list` 只證明「檔案結構讀得開」，不證明**資料還原得回來**。
       這一段才是真的證明。它會建一個 `<db>_restoretest` 資料庫，
       驗完就砍掉，**完全不碰正式資料庫**。
    """
    from sqlalchemy import create_engine, text
    pg_restore = find_bin("pg_restore", env)
    psql_ok = True
    root = env.get("PG_BACKUP_DIR") or DEFAULT_DIR
    runs = sorted((d for d in os.listdir(root)
                   if re.fullmatch(r"\d{8}_\d{6}", d)), reverse=True)
    if not runs:
        print("  ❌ 沒有任何備份可以驗證")
        return 1
    newest = os.path.join(root, runs[0])
    print(f"  用最新的備份：{runs[0]}\n")

    bad = 0
    for key, prefix, label in TARGETS:
        url = env.get(key, "")
        path = os.path.join(newest, prefix + ".dump")
        if not url.startswith("postgres") or not os.path.exists(path):
            continue
        c = split_url(url)
        scratch = f"{c['dbname']}_restoretest"
        admin = (f"postgresql+psycopg://{c['user']}:{c['password']}"
                 f"@{c['host']}:{c['port']}/postgres")
        eng = create_engine(admin, isolation_level="AUTOCOMMIT")
        print(f"  ── {label}：還原到暫存資料庫 {scratch}")
        try:
            with eng.connect() as cn:
                cn.execute(text(f'DROP DATABASE IF EXISTS "{scratch}"'))
                # ⚠️ 跟正式庫一樣用 template0 + C collation，否則比對條件不同
                cn.execute(text(f'CREATE DATABASE "{scratch}" TEMPLATE template0 '
                                f"LC_COLLATE 'C' LC_CTYPE 'C' ENCODING 'UTF8'"))
            r = run([pg_restore, "-h", c["host"], "-p", c["port"], "-U", c["user"],
                     "-d", scratch, "--no-owner", "--no-privileges", path],
                    c["password"])
            # pg_restore 對 owner/權限之類的差異會回非 0 但資料其實進去了，
            # 所以不看 returncode，直接比對筆數 —— 那才是我們在乎的事。
            src = create_engine(url.replace("+psycopg", "+psycopg"))
            dst = create_engine(admin.rsplit("/", 1)[0] + "/" + scratch)
            with src.connect() as s, dst.connect() as d:
                tabs = [t for (t,) in s.execute(text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "ORDER BY tablename"))]
                diff = []
                for t in tabs:
                    a = s.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar_one()
                    try:
                        b = d.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar_one()
                    except Exception:
                        b = None
                    if a != b:
                        diff.append((t, a, b))
                print(f"      比對 {len(tabs)} 張表")
                if diff:
                    bad += 1
                    print(f"      ❌ {len(diff)} 張對不上：")
                    for t, a, b in diff[:10]:
                        print(f"          {t:<40} 正式 {a:>10,} / 還原 "
                              f"{'讀不到' if b is None else format(b, ',')}")
                else:
                    print("      ✅ 每一張表的筆數都一致 —— **這份備份真的還原得回來**")
            src.dispose()
            dst.dispose()
        except Exception as e:
            bad += 1
            psql_ok = False
            print(f"      ❌ {type(e).__name__}: {str(e).splitlines()[0][:160]}")
        finally:
            try:
                with eng.connect() as cn:
                    cn.execute(text(f'DROP DATABASE IF EXISTS "{scratch}"'))
                print(f"      🧹 已清掉 {scratch}")
            except Exception:
                print(f"      ⚠️ 清不掉 {scratch}，請手動 DROP DATABASE")
            eng.dispose()
        print()
    return 1 if (bad or not psql_ok) else 0


def main() -> int:
    dry = "--dry-run" in sys.argv
    env = read_env()
    root = env.get("PG_BACKUP_DIR") or DEFAULT_DIR
    days = int(env.get("PG_BACKUP_RETENTION_DAYS") or DEFAULT_RETENTION)

    print("=" * 78)
    print("  PostgreSQL 備份" + ("（dry-run）" if dry else ""))
    print("=" * 78)
    print(f"  備份目錄：{root}")
    print(f"  保留天數：{days}\n")

    if "--status" in sys.argv:
        return show_status(root)
    if "--verify-restore" in sys.argv:
        return verify_restore(env)

    # ⚠️ 先確認現在真的在跑 PostgreSQL。還在 SQLite 的話 pg_dump 無事可做，
    #    而「跑完沒報錯」會讓人以為備份好了 —— 這正是今天踩過的那種假 ✅。
    live = [(k, p, lb) for k, p, lb in TARGETS
            if env.get(k, "").startswith("postgres")]
    if not live:
        print("  ❌ .env 裡沒有任何 PostgreSQL 連線（都還是 SQLite）。")
        print("     這支腳本只備份 PostgreSQL。SQLite 請直接複製 .db 檔。\n")
        return 2
    for k, _, lb in TARGETS:
        u = env.get(k, "")
        flag = "✅" if u.startswith("postgres") else "⚠️ 仍是 SQLite，跳過"
        print(f"  {lb:<8}{flag}  {mask(u)}")
    print()

    pg_dump = find_bin("pg_dump", env)
    pg_restore = find_bin("pg_restore", env)
    print(f"  pg_dump   : {pg_dump}")
    print(f"  pg_restore: {pg_restore}\n")

    stamp = f"{dt.datetime.now():%Y%m%d_%H%M%S}"
    outdir = os.path.join(root, stamp)
    if not dry:
        os.makedirs(outdir, exist_ok=True)

    results: dict[str, str] = {}
    failed = 0
    for key, prefix, label in live:
        path = os.path.join(outdir, prefix + ".dump")
        print(f"  ── {label} → {prefix}.dump")
        ok, info = dump_one(pg_dump, env[key], path, label, dry)
        if not ok:
            failed += 1
            print(f"      ❌ 備份失敗：{info}\n")
            continue
        print(f"      ✅ 已產生（{info}）")
        if dry:
            results[prefix] = "dry-run"
            print()
            continue
        vok, vinfo = verify_dump(pg_restore, path)
        if not vok:
            failed += 1
            print(f"      ❌ **驗證失敗**：{vinfo}")
            print("         檔案寫出來了但讀不回去 —— 這種備份等於沒有。\n")
            continue
        print(f"      ✅ 驗證通過（{vinfo}）\n")
        results[prefix] = f"{info}，{vinfo}"

    print(f"  ── 清理超過 {days} 天的備份")
    if os.path.isdir(root):
        n = prune(root, days, dry)
        print(f"      刪除 {n} 份舊備份\n" if n else "      沒有需要清理的\n")
    else:
        print("      （備份目錄還不存在）\n")

    print("=" * 78)
    if failed:
        print(f"  ❌ 有 {failed} 個資料庫備份失敗。**排程請視為紅燈。**\n")
        return 1
    if not dry:
        json.dump({"last_success": dt.datetime.now().isoformat(timespec="seconds"),
                   "dir": outdir, "targets": results},
                  open(os.path.join(root, STATUS_NAME), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    print(f"  ✅ 備份完成：{outdir}")
    print("""
  ⚠️ 兩件事這支腳本**不會**幫你做：

    ① **複製到另一台機器。** 備份跟資料庫在同一顆硬碟上，硬碟壞掉會一起沒。
       請另外排程同步到 NAS／雲端。

    ② **證明還原得回來。** 上面的驗證只讀了檔案結構。真的證明要跑：
           py -3.11 scripts\\pg_backup.py --verify-restore
       它會還原到一個暫存資料庫、逐表比對筆數，完全不碰正式庫。
       **建議每月至少一次。**
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
