"""
登入診斷 + 強制重設密碼
執行：py -3.11 fix_login.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# ── 1. 確認讀到哪個 DB ───────────────────────────────────────
from app.core.config import settings
print("=" * 55)
print(f"DATABASE_URL : {settings.DATABASE_URL}")

db_path = settings.DATABASE_URL.replace("sqlite:///", "").replace("./", "")
if not os.path.isabs(db_path):
    db_path = os.path.join(os.path.dirname(__file__), db_path)
db_path = os.path.abspath(db_path)
print(f"DB 實際路徑  : {db_path}")
print(f"DB 檔案存在  : {os.path.exists(db_path)}")
print("=" * 55)

# ── 2. 列出所有使用者 ────────────────────────────────────────
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password, verify_password

db = SessionLocal()
try:
    users = db.query(User).all()
    print(f"\n資料庫共有 {len(users)} 個帳號：")
    for u in users:
        print(f"  email={u.email} | is_active={u.is_active} | hashed_password={u.hashed_password[:20]}...")

    # ── 3. 強制重設 admin 密碼 ─────────────────────────────────
    NEW_PASSWORD = "Admin@2026"
    TARGET_EMAIL = "admin@portal.local"

    print(f"\n目標帳號：{TARGET_EMAIL}")
    admin = db.query(User).filter(User.email == TARGET_EMAIL).first()

    if admin:
        new_hash = hash_password(NEW_PASSWORD)
        admin.hashed_password = new_hash
        db.commit()
        db.refresh(admin)

        # 驗證是否成功
        ok = verify_password(NEW_PASSWORD, admin.hashed_password)
        print(f"密碼重設完成：{'✓ 驗證成功' if ok else '✗ 驗證失敗（異常）'}")
        print(f"新 hash 前20碼：{admin.hashed_password[:20]}...")
        print(f"\n請用以下帳密登入：")
        print(f"  帳號：admin  （或 {TARGET_EMAIL}）")
        print(f"  密碼：{NEW_PASSWORD}")
    else:
        print(f"找不到 {TARGET_EMAIL}，嘗試重設第一個帳號...")
        if users:
            u = users[0]
            u.hashed_password = hash_password(NEW_PASSWORD)
            db.commit()
            ok = verify_password(NEW_PASSWORD, u.hashed_password)
            print(f"帳號 {u.email} 密碼重設：{'✓ 成功' if ok else '✗ 失敗'}")
            print(f"\n請用以下帳密登入：")
            print(f"  帳號：{u.email}")
            print(f"  密碼：{NEW_PASSWORD}")
        else:
            print("資料庫完全沒有帳號！請執行：py -3.11 init_db.py")
finally:
    db.close()

print("\n完成。")
