"""
重設 admin 密碼腳本
執行方式：py -3.11 reset_password.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User

db = SessionLocal()

try:
    users = db.query(User).all()
    if not users:
        print("資料庫裡沒有任何帳號")
    else:
        print("目前帳號列表：")
        for u in users:
            print(f"  email={u.email} | full_name={u.full_name} | is_active={u.is_active}")

    print()
    admin = db.query(User).filter(User.email == "admin@portal.local").first()
    if admin:
        admin.hashed_password = hash_password("Admin@2026")
        db.commit()
        print("✓ admin@portal.local 密碼已重設為：Admin@2026")
    else:
        print("找不到 admin@portal.local，列出所有帳號請看上方")
finally:
    db.close()
