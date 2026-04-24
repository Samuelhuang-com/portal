"""
初始化資料庫：建立資料表 + 種子資料
執行：cd backend && python init_db.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import engine, SessionLocal
from app.models import Base, Tenant, Role, User, UserRole
from app.core.security import hash_password

TENANTS = [
    {"code": "HQ",      "name": "總公司",  "type": "headquarters"},
    {"code": "HOTEL_A", "name": "飯店A",   "type": "hotel"},
    {"code": "HOTEL_B", "name": "飯店B",   "type": "hotel"},
    {"code": "MALL_A",  "name": "商場A",   "type": "mall"},
    {"code": "MALL_B",  "name": "商場B",   "type": "mall"},
]

ROLES = [
    {"name": "system_admin",   "scope": "global",  "description": "可操作所有據點、所有模組"},
    {"name": "tenant_admin",   "scope": "tenant",  "description": "可操作指定據點的所有模組"},
    {"name": "module_manager", "scope": "module",  "description": "可跨據點存取特定模組"},
    {"name": "viewer",         "scope": "module",  "description": "唯讀存取指定據點+模組"},
]

# 初始最高權限使用者（帳號不分大小寫，DB 統一小寫存放）
INITIAL_USERS = [
    {
        "email":     "admin@portal.local",
        "full_name": "Administrator",
        "password":  "Admin@2026",
        "role":      "system_admin",
    },
    {
        "email":     "samuel.huang@portal.local",
        "full_name": "Samuel Huang",
        "password":  "Samuel@2026",
        "role":      "system_admin",
    },
]

def main():
    print("\n🚀 初始化資料庫...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        tenant_map: dict[str, str] = {}
        print("\n📍 建立據點...")
        for t in TENANTS:
            obj = db.query(Tenant).filter(Tenant.code == t["code"]).first()
            if not obj:
                obj = Tenant(**t)
                db.add(obj)
                db.flush()
                print(f"   + {t['code']}  {t['name']}")
            tenant_map[t["code"]] = obj.id

        role_map: dict[str, str] = {}
        print("\n🎭 建立角色...")
        for r in ROLES:
            obj = db.query(Role).filter(Role.name == r["name"]).first()
            if not obj:
                obj = Role(**r)
                db.add(obj)
                db.flush()
                print(f"   + {r['name']}")
            role_map[r["name"]] = obj.id

        hq_id = tenant_map["HQ"]
        print("\n👤 建立初始使用者...")
        for u in INITIAL_USERS:
            email = u["email"].lower()
            obj = db.query(User).filter(User.email == email).first()
            if not obj:
                obj = User(
                    email=email,
                    full_name=u["full_name"],
                    hashed_password=hash_password(u["password"]),
                    tenant_id=hq_id,
                )
                db.add(obj)
                db.flush()
                db.add(UserRole(
                    user_id=obj.id,
                    role_id=role_map[u["role"]],
                    tenant_id=hq_id,
                ))
                print(f"   + {email}")
            else:
                print(f"   ~ {email}（已存在）")

        db.commit()
        print("\n✅ 初始化完成！")
        print("\n登入帳號：")
        print("  ┌──────────────────────────────────┬──────────────┐")
        print("  │ 帳號                             │ 密碼         │")
        print("  ├──────────────────────────────────┼──────────────┤")
        for u in INITIAL_USERS:
            uname = u['email'].split('@')[0]
            print(f"  │ {uname:<32} │ {u['password']:<12} │")
        print("  └──────────────────────────────────┴──────────────┘")
        print("\n  （帳號不分大小寫；也可用完整 email 登入）\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ 錯誤：{e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
