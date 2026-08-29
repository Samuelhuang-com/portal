"""
偵測本機 PostgreSQL 的 host / port / 使用者（唯讀，不需要密碼）

用途：要填 `.env` 的 `POSTGRES_URL` 之前，先確認連線資訊。

⚠️ **本腳本不會問你密碼、也不會存密碼。**
   它只做兩件事：①掃常見 port 看有沒有 PostgreSQL 在聽
   ②用不帶密碼的方式試連，從錯誤訊息判斷「使用者存不存在／需不需要密碼」。
   「需要密碼」本身就是好消息 —— 代表 host／port／使用者三個都對了。

執行：
    cd backend
    python scripts\\pg_discover.py
"""
from __future__ import annotations

import socket
import subprocess
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


HOST = "127.0.0.1"
PORTS = [5432, 5433, 5434, 5435]
USERS = ["postgres", "portal"]


def scan_ports() -> list[int]:
    print("=" * 66)
    print("  ① 掃描本機常見的 PostgreSQL port")
    print("=" * 66)
    found = []
    for p in PORTS:
        s = socket.socket()
        s.settimeout(0.6)
        try:
            s.connect((HOST, p))
            print(f"  ✅ {HOST}:{p}  有服務在聽")
            found.append(p)
        except Exception:
            print(f"  ·  {HOST}:{p}  沒有回應")
        finally:
            s.close()
    if not found:
        print("\n  ❌ 找不到任何在聽的 port。可能是：")
        print("     · PostgreSQL 服務沒啟動（Win+R → services.msc → 找 postgresql-x64-XX）")
        print("     · 裝在非預設 port（見下面第 ③ 段）")
    return found


def probe_users(ports: list[int]) -> None:
    """試連並回報。

    ⚠️⚠️ **「需要密碼」不代表那個使用者或資料庫存在。**
       PostgreSQL 刻意不對未認證的連線洩漏帳號是否存在（防帳號列舉），
       所以只要設了 scram/md5 認證，不管使用者存不存在都一律先要密碼。
       2026-08-28 實際踩到：本腳本回報 `portal` 使用者「存在」，
       但在 pgAdmin 執行 ALTER USER 時得到 `role "portal" does not exist`。

       要確定有哪些使用者／資料庫，只能用**已認證**的連線查系統表 ——
       見本檔最後印出的兩行 SQL。
    """
    print()
    print("=" * 66)
    print("  ② 試連（不帶密碼）")
    print("=" * 66)
    print("  ⚠️ 這一段只能確認「連得到 / 連不到」。")
    print("     PostgreSQL 不會對未認證的連線透露使用者或資料庫是否存在，")
    print("     所以下面的「需要密碼」**不代表**那個帳號或資料庫真的有。\n")
    try:
        import psycopg
    except ImportError:
        # ⚠️ 一定要用「跑這支腳本的那個 Python」去裝。
        #    這台機器同時有 Anaconda 的 python 與 py -3.12，
        #    用 `py -3.12 -m pip install` 會裝到另一個直譯器，這裡照樣 import 不到。
        print("  ⚠️  這個 Python 尚未安裝 psycopg，跳過這段。")
        print(f"      目前的直譯器：{sys.executable}")
        print("      請用**同一個**直譯器安裝，直接複製這行：")
        print(f'        "{sys.executable}" -m pip install "psycopg[binary]"')
        return

    for port in ports:
        for user in USERS:
            for dbname in ("portal", "postgres"):
                try:
                    psycopg.connect(host=HOST, port=port, user=user,
                                    dbname=dbname, connect_timeout=3)
                    print(f"  ✅ {user}@{HOST}:{port}/{dbname} — 免密碼即可連線")
                except Exception as e:
                    msg = str(e).lower()
                    tag = f"{user}@{HOST}:{port}/{dbname}"
                    if "password" in msg:
                        # ⚠️ 只代表「伺服器要求密碼」，不代表 user/db 存在
                        print(f"  ?  {tag} — 伺服器要求密碼（無法判斷是否存在）")
                    elif "does not exist" in msg and "database" in msg:
                        print(f"  ⚠️  {tag} — **資料庫 {dbname} 不存在**")
                    elif "does not exist" in msg or "authentication" in msg:
                        print(f"  ·  {tag} — 使用者或角色不存在")
                    else:
                        print(f"  ·  {tag} — {str(e).splitlines()[0][:60]}")


def show_service_info() -> None:
    print()
    print("=" * 66)
    print("  ③ Windows 服務資訊")
    print("=" * 66)
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Service | Where-Object {$_.Name -like 'postgres*'} | "
             "Select-Object Name,Status,DisplayName | Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=20,
        )
        txt = (out.stdout or "").strip()
        print("  " + (txt.replace("\n", "\n  ") if txt else "（找不到 postgres* 服務）"))
    except Exception as e:
        print(f"  （查不到：{e}）")

    print()
    print("  手動確認的三個地方：")
    print("   · pgAdmin  → 左側 Servers 右鍵 → Properties → Connection 分頁")
    print("               （Host name/address、Port、Username 都在那）")
    print("   · services.msc → 服務名稱如 postgresql-x64-17，數字就是大版本")
    print("   · 安裝預設值 → host=localhost、port=5432、user=postgres")


def main() -> None:
    print("PostgreSQL 連線資訊偵測（唯讀，不需要也不會存密碼）")
    # ⚠️ 這台機器同時有 Anaconda 與 py -3.12，先印出到底是哪一個在跑，
    #    否則「明明裝了卻 import 不到」會查很久。
    print(f"  直譯器：{sys.executable}")
    print(f"  版本  ：{sys.version.split()[0]}\n")
    ports = scan_ports()
    if ports:
        probe_users(ports)
    show_service_info()

    print()
    print("=" * 66)
    print("  ④ 要確定有哪些使用者／資料庫，請在 pgAdmin 的 Query Tool 執行")
    print("=" * 66)
    print("""
    SELECT rolname AS 使用者, rolcanlogin AS 可登入, rolsuper AS 超級使用者
    FROM pg_roles ORDER BY 1;

    SELECT datname AS 資料庫 FROM pg_database WHERE datistemplate = false ORDER BY 1;

  （pgAdmin 已經是**已認證**的連線，才問得到這兩件事。
    本腳本的第 ② 段沒有密碼，問不到。）
""")
    print("=" * 66)
    print("  下一步：把結果填進 backend/.env")
    print("=" * 66)
    print("""
  POSTGRES_URL=postgresql+psycopg://<使用者>:<密碼>@<host>:<port>/portal

  例（預設安裝、資料庫叫 portal）：
  POSTGRES_URL=postgresql+psycopg://postgres:你的密碼@localhost:5432/portal

  ⚠️ 密碼由你自己填，不要貼給任何人。
  ⚠️ 這行是**新增**的，不要動到現有的 DATABASE_URL ——
     Phase 1 是兩個資料庫並存，SQLite 仍然是主要來源。
""")


if __name__ == "__main__":
    main()
