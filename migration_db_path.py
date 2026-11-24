"""
週期採購 migration 腳本共用的「資料庫路徑解析」。

2026-08-10 新增。起因是正式區把 migration 跑到了錯的檔案上：

  三支腳本原本都把 DB_PATH 寫死成 C:\\portal_data\\cycle-purchase.db，但正式區的
  backend/.env **沒有設 CYCLE_PURCHASE_DATABASE_URL**，後端因此吃 config.py 的預設
  相對路徑 ./cycle-purchase.db，實際用的是 D:\\portal\\backend\\cycle-purchase.db。
  兩邊講的不是同一個檔案，於是：

    - apply 腳本用裸的 sqlite3.connect() 開一個不存在的路徑 → sqlite 直接建出
      一個 0 bytes 的空檔，ALTER TABLE 全部落在空 DB 上；
    - 腳本印「成功」，後端重啟卻報一模一樣的 no such column；
    - 而且從此多一個看起來很像正牌的空 DB 檔在旁邊誤導後續每一次排查。

解析優先序（由高而低）：

  1. 命令列 --db <路徑>
  2. backend/.env 的 CYCLE_PURCHASE_DATABASE_URL
  3. 呼叫端傳入的 default（沿用各腳本原本寫死的值）

第 2 順位刻意跟後端讀同一份設定，讓「腳本改到的檔案」與「後端實際用的檔案」預設
就是同一個——這正是這次出事的地方。
"""

import os
import re
import sys

# 這支模組與三支 migration 腳本都放在 repo 根目錄，backend/.env 固定在隔壁。
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.join(_REPO_ROOT, "backend")
_ENV_PATH = os.path.join(_BACKEND_DIR, ".env")

_SQLITE_PREFIXES = ("sqlite+aiosqlite:///", "sqlite+pysqlite:///", "sqlite:///")


def _strip_sqlite_url(value):
    """把 sqlite:///C:/x/y.db 這種 URL 還原成檔案路徑；不是 sqlite URL 就回 None。

    相對路徑（sqlite:///./cycle-purchase.db）是相對於 **backend/** 解析的，因為
    後端啟動時的工作目錄就是 backend（見 app/core/cycle_purchase_database.py）。
    """
    for prefix in _SQLITE_PREFIXES:
        if value.startswith(prefix):
            raw = value[len(prefix):]
            break
    else:
        return None

    if not raw:
        return None

    # Windows 磁碟機代號（C:/...、C:\...）在非 Windows 平台上 os.path.isabs() 會回
    # False，若直接 join 會拼出 backend/C:/portal_data/... 這種鬼路徑。這支腳本平常
    # 只在正式區的 Windows 上跑，但 WSL／Linux 上做驗證時會踩到，所以自己判斷。
    is_windows_abs = bool(re.match(r"^[A-Za-z]:[\\/]", raw))

    raw = raw.replace("/", os.sep)
    if not is_windows_abs and not os.path.isabs(raw):
        raw = os.path.normpath(os.path.join(_BACKEND_DIR, raw))
    return raw


def _read_env_db_url():
    """從 backend/.env 讀 CYCLE_PURCHASE_DATABASE_URL；讀不到回 None。

    只做最小限度的解析（KEY=VALUE、跳過 # 註解、去掉引號），不引入 dotenv 相依，
    也刻意不去讀其他任何一個 key——這支腳本不需要碰到 .env 裡的機敏值。
    """
    if not os.path.exists(_ENV_PATH):
        return None

    pattern = re.compile(r"^\s*CYCLE_PURCHASE_DATABASE_URL\s*=\s*(.*?)\s*$")
    found = None
    try:
        with open(_ENV_PATH, "r", encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                if line.lstrip().startswith("#"):
                    continue
                m = pattern.match(line)
                if m:
                    # 同一個 key 出現多次時，後面的覆蓋前面的（與 dotenv 行為一致）
                    found = m.group(1)
    except OSError:
        return None

    if not found:
        return None
    return found.strip().strip('"').strip("'")


def resolve_db_path(default_path, argv=None):
    """決定要操作哪一個 cycle-purchase.db。

    回傳 (path, source)，source 是給人看的來源說明字串。
    --db 後面沒接路徑時直接 sys.exit(2)。
    """
    argv = list(sys.argv[1:] if argv is None else argv)

    if "--help" in argv or "-h" in argv:
        print("用法：python {} [--db <資料庫檔案路徑>]".format(
            os.path.basename(sys.argv[0])))
        print()
        print("不帶 --db 時的路徑決定順序：")
        print("  1. backend/.env 的 CYCLE_PURCHASE_DATABASE_URL")
        print("  2. 腳本內建預設值：{}".format(default_path))
        sys.exit(0)

    if "--db" in argv:
        idx = argv.index("--db")
        if idx + 1 >= len(argv) or argv[idx + 1].startswith("-"):
            print("[錯誤] --db 後面要接資料庫檔案路徑。")
            sys.exit(2)
        return os.path.abspath(argv[idx + 1]), "命令列 --db 參數"

    env_url = _read_env_db_url()
    if env_url:
        path = _strip_sqlite_url(env_url)
        if path:
            return path, "backend/.env 的 CYCLE_PURCHASE_DATABASE_URL"
        # 設了但不是 sqlite URL（例如改用 PostgreSQL），這時候這支腳本幫不上忙
        print("[錯誤] backend/.env 的 CYCLE_PURCHASE_DATABASE_URL 不是 SQLite 路徑：")
        print("       {}".format(env_url))
        print("       這支腳本只處理 SQLite。")
        sys.exit(2)

    return default_path, "腳本內建預設值（backend/.env 未設 CYCLE_PURCHASE_DATABASE_URL）"


def require_existing_db(path, source):
    """確認檔案真的存在，不存在就報錯退出。

    **這是這支模組存在的主要理由。** sqlite3.connect() 對不存在的路徑會靜默建出一個
    0 bytes 的空檔，接著 migration 會在空 DB 上「成功」跑完，而後端用的是另一個檔案，
    症狀完全不變——排查時最花時間的就是這種「看起來做了但其實沒做」。
    """
    print("資料庫：{}".format(path))
    print("　來源：{}".format(source))
    print()

    if not os.path.exists(path):
        print("[錯誤] 找不到資料庫檔案：{}".format(path))
        print()
        print("       這支腳本不會自動建立資料庫（建出來的空檔會讓 migration 假裝成功）。")
        print("       請確認路徑，常見的兩種情況：")
        print("         - backend/.env 有設 CYCLE_PURCHASE_DATABASE_URL → 以它為準")
        print("         - 沒設 → 後端吃預設的相對路徑，檔案在 backend/cycle-purchase.db")
        print()
        print("       也可以直接指定：python {} --db <路徑>".format(
            os.path.basename(sys.argv[0])))
        sys.exit(1)

    if os.path.getsize(path) == 0:
        print("[錯誤] 這個檔案是 0 bytes 的空檔：{}".format(path))
        print("       多半是先前某次腳本誤建出來的空殼，不是真正的資料庫。")
        print("       請確認正確路徑後用 --db 指定，並把這個空檔刪掉。")
        sys.exit(1)
