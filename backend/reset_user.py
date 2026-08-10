"""
帳號救援工具 — 直接改密碼 / 改 Email / 解鎖帳號
=================================================
使用時機：管理員忘記密碼、Email 打錯登不進去、帳號被停用。

執行方式（在 backend 目錄下）：
    py -3.11 reset_user.py                    # 互動模式（列出帳號後選擇）
    py -3.11 reset_user.py --list             # 只列出所有帳號
    py -3.11 reset_user.py --email admin@portal.local --password "NewPass@2026"
    py -3.11 reset_user.py --email old@x.com --new-email new@x.com
    py -3.11 reset_user.py --email admin@portal.local --password "NewPass@2026" --hash-only
                                              # 只印出 bcrypt hash 與 SQL 語法，不寫入 DB

說明：
  - 密碼是 bcrypt 雜湊，無法用純 SQL 直接寫明文密碼。
    若一定要走 SQL，請用 --hash-only 產生 hash，再把印出來的 UPDATE 語法貼到 DB 工具執行。
  - 重設密碼會一併清除 OTP、把 must_change_password 設為 0、is_active 設為 1，
    確保重設後可以直接登入。
"""
import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from passlib.context import CryptContext
except ImportError:
    print("[錯誤] 找不到 passlib，請先在 backend 的虛擬環境執行： pip install \"passlib[bcrypt]\"")
    sys.exit(1)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def resolve_db_path() -> str:
    """從 app.core.config 讀 DATABASE_URL；讀不到就 fallback 到 .env / 預設值。"""
    url = None
    try:
        from app.core.config import settings  # noqa

        url = settings.DATABASE_URL
    except Exception:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DATABASE_URL="):
                        url = line.split("=", 1)[1].strip()
                        break
    if not url:
        url = "sqlite:///./portal.db"

    if not url.startswith("sqlite"):
        print(f"[錯誤] 本工具只支援 SQLite，目前 DATABASE_URL = {url}")
        sys.exit(1)

    path = url.split("///", 1)[1]
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    return os.path.abspath(path)


def list_users(conn) -> list:
    has_mcp = "must_change_password" in {
        r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    mcp_col = "must_change_password" if has_mcp else "0"
    rows = conn.execute(
        f"SELECT id, email, full_name, is_active, {mcp_col} FROM users ORDER BY email"
    ).fetchall()
    print(f"\n資料庫共有 {len(rows)} 個帳號：")
    print("-" * 82)
    print(f"{'#':<3} {'Email':<34} {'姓名':<14} {'啟用':<5} {'須改密碼'}")
    print("-" * 82)
    for i, r in enumerate(rows, 1):
        print(f"{i:<3} {r[1]:<34} {(r[2] or ''):<14} {'是' if r[3] else '否':<5} {'是' if r[4] else '否'}")
    print("-" * 82)
    return rows


def _columns(conn) -> set:
    return {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}


def update_password(conn, email: str, new_password: str) -> bool:
    """重設密碼；otp / must_change_password 等欄位若該 DB 尚未 migration 則自動略過。"""
    hashed = pwd_context.hash(new_password)
    cols = _columns(conn)
    sets = ["hashed_password = ?", "is_active = 1"]
    params = [hashed]
    if "must_change_password" in cols:
        sets.append("must_change_password = 0")
    if "otp_code" in cols:
        sets.append("otp_code = NULL")
    if "otp_expires_at" in cols:
        sets.append("otp_expires_at = NULL")
    params.append(email)
    cur = conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE email = ?", params)
    conn.commit()
    return cur.rowcount > 0


def update_email(conn, old_email: str, new_email: str) -> bool:
    exists = conn.execute("SELECT 1 FROM users WHERE email = ?", (new_email,)).fetchone()
    if exists:
        print(f"[錯誤] {new_email} 已經被其他帳號使用（email 有 unique 限制）")
        return False
    cur = conn.execute("UPDATE users SET email = ? WHERE email = ?", (new_email, old_email))
    conn.commit()
    return cur.rowcount > 0


def main():
    ap = argparse.ArgumentParser(description="Portal 帳號救援工具")
    ap.add_argument("--list", action="store_true", help="只列出所有帳號")
    ap.add_argument("--email", help="目標帳號 Email")
    ap.add_argument("--password", help="要設定的新密碼")
    ap.add_argument("--new-email", help="要換成的新 Email")
    ap.add_argument("--hash-only", action="store_true", help="只印 bcrypt hash 與 SQL，不寫入 DB")
    args = ap.parse_args()

    if args.hash_only:
        if not args.password or not args.email:
            print("[錯誤] --hash-only 需要同時指定 --email 與 --password")
            sys.exit(1)
        hashed = pwd_context.hash(args.password)
        print("\nbcrypt hash：")
        print(hashed)
        print("\n可直接執行的 SQL：")
        print(
            "UPDATE users SET hashed_password = '%s', is_active = 1, "
            "must_change_password = 0, otp_code = NULL, otp_expires_at = NULL "
            "WHERE email = '%s';" % (hashed, args.email)
        )
        return

    db_path = resolve_db_path()
    print("=" * 60)
    print(f"DB 路徑    : {db_path}")
    print(f"檔案存在   : {os.path.exists(db_path)}")
    print("=" * 60)
    if not os.path.exists(db_path):
        print("[錯誤] 找不到資料庫檔案，請確認 .env 的 DATABASE_URL")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    try:
        rows = list_users(conn)
        if args.list:
            return

        email = args.email
        if not email:
            choice = input("\n要處理第幾個帳號？（輸入編號，或直接貼 Email）：").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(rows):
                email = rows[int(choice) - 1][1]
            else:
                email = choice
        if not any(r[1] == email for r in rows):
            print(f"[錯誤] 找不到帳號：{email}")
            sys.exit(1)

        new_email = args.new_email
        password = args.password
        if not new_email and not password:
            new_email = input(f"新的 Email（不改就按 Enter，目前 {email}）：").strip() or None
            password = input("新的密碼（不改就按 Enter）：").strip() or None

        if not new_email and not password:
            print("沒有要變更的項目，結束。")
            return

        if new_email:
            if update_email(conn, email, new_email):
                print(f"[OK] Email 已從 {email} 改為 {new_email}")
                email = new_email
            else:
                sys.exit(1)

        if password:
            if update_password(conn, email, password):
                print(f"[OK] {email} 密碼已重設，帳號已啟用，OTP 已清除")
            else:
                print(f"[錯誤] 密碼更新失敗：{email}")
                sys.exit(1)

        print("\n目前狀態：")
        list_users(conn)
        print(f"\n請用以下資訊登入：\n  帳號：{email}\n  密碼：{password or '（未變更）'}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
