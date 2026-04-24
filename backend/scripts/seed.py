"""
Seed script — 建立初始資料
執行方式: cd backend && python -m scripts.seed

預設帳號:
  admin@portal.com       密碼: Admin@2026!   (系統管理員)
  samuel.huang@portal.com 密碼: Samuel@2026!  (系統管理員)

注意: 所有 email 統一轉為小寫儲存
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, create_tables
from app.core.security import get_password_hash
from app.models.tenant import Tenant
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models import all_models  # ensure all models loaded

TENANTS = [
    {"code": "HQ",      "name": "總公司",  "type": "headquarters"},
    {"code": "HOTEL_A", "name": "飯店 A",  "type": "hotel"},
    {"code": "HOTEL_B", "name": "飯店 B",  "type": "hotel"},
    {"code": "MALL_A",  "name": "商場 A",  "type": "mall"},
    {"code": "MALL_B",  "name": "商場 B",  "type": "mall"},
]

ROLES = [
    {"name": "system_admin",   "scope": "global",  "description": "可操作所有據點、所有模組"},
    {"name": "tenant_admin",   "scope": "tenant",  "description": "可操作指定據點的所有模組"},
    {"name": "module_manager", "scope": "module",  "description": "可跨據點存取特定模組"},
    {"name": "viewer",         "scope": "module",  "description": "唯讀存取指定據點+模組"},
]

# email → 資料庫一律小寫
SEED_USERS = [
    {
        "email": "admin@portal.com",          # lowercase
        "full_name": "Administrator",
        "password": "Admin@2026!",
        "role": "system_admin",
        "tenant_code": "HQ",
    },
    {
        "email": "samuel.huang@portal.com",   # Samuel.Huang → lowercase
        "full_name": "Samuel Huang",
        "password": "Samuel@2026!",
        "role": "system_admin",
        "tenant_code": "HQ",
    },
]

async def seed():
    await create_tables()

    async with AsyncSessionLocal() as db:
        # ── Tenants ──────────────────────────────────────────
        tenant_map: dict[str, Tenant] = {}
        for t_data in TENANTS:
            result = await db.execute(select(Tenant).where(Tenant.code == t_data["code"]))
            tenant = result.scalar_one_or_none()
            if not tenant:
                tenant = Tenant(**t_data)
                db.add(tenant)
                await db.flush()
                print(f"  ✅ Tenant created: {t_data['code']} — {t_data['name']}")
            else:
                print(f"  ⏭  Tenant exists:  {t_data['code']}")
            tenant_map[t_data["code"]] = tenant

        await db.commit()

        # ── Roles ────────────────────────────────────────────
        role_map: dict[str, Role] = {}
        for r_data in ROLES:
            result = await db.execute(select(Role).where(Role.name == r_data["name"]))
            role = result.scalar_one_or_none()
            if not role:
                role = Role(**r_data)
                db.add(role)
                await db.flush()
                print(f"  ✅ Role created: {r_data['name']}")
            else:
                print(f"  ⏭  Role exists:  {r_data['name']}")
            role_map[r_data["name"]] = role

        await db.commit()

        # ── Users ─────────────────────────────────────────────
        hq_tenant = tenant_map["HQ"]
        for u_data in SEED_USERS:
            email = u_data["email"].lower()  # ensure lowercase
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if not user:
                user = User(
                    email=email,
                    full_name=u_data["full_name"],
                    hashed_password=get_password_hash(u_data["password"]),
                    tenant_id=hq_tenant.id,
                    is_active=True,
                )
                db.add(user)
                await db.flush()
                print(f"  ✅ User created: {email} ({u_data['full_name']})")
            else:
                print(f"  ⏭  User exists:  {email}")

            # Assign system_admin role at HQ
            role = role_map[u_data["role"]]
            existing_ur = await db.execute(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == role.id,
                    UserRole.tenant_id == hq_tenant.id,
                )
            )
            if not existing_ur.scalar_one_or_none():
                db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=hq_tenant.id))
                print(f"  ✅ Role '{u_data['role']}' assigned to {email}")
            else:
                print(f"  ⏭  Role already assigned: {email}")

        await db.commit()

    print("\n🎉 Seed completed!\n")
    print("┌─────────────────────────────────────────────────────┐")
    print("│  預設帳號 (Default Accounts)                        │")
    print("├──────────────────────────────┬──────────────────────┤")
    print("│  Email                       │  Password            │")
    print("├──────────────────────────────┼──────────────────────┤")
    print("│  admin@portal.com            │  Admin@2026!         │")
    print("│  samuel.huang@portal.com     │  Samuel@2026!        │")
    print("└──────────────────────────────┴──────────────────────┘")
    print("  ⚠️  請於首次登入後立即修改密碼！")

if __name__ == "__main__":
    asyncio.run(seed())
