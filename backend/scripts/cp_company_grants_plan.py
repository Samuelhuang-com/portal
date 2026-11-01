"""週採可見公司：角色授權盤點與套用（方案 B）

背景：可見公司改由「角色權限」決定（權限鍵 cycle_purchase_company_ch／_ou／_ho）。
改版前，可見公司是依「部門歸屬」推導的。本腳本先依舊規則盤點，產生建議的角色授權，
經管理員確認後才寫入 role_permissions。

重要順序（避免權限突然消失）：
  1. 在程式切換「角色決定可見公司」之前，先執行 report（唯讀）。
  2. 管理員檢視 cp_company_grants_proposal.json，必要時修改成確認版本（同格式）。
  3. apply（預設乾跑）：確認無誤後加上 --yes 寫入。
  4. 才部署新的範圍程式。

用法：
  python scripts/cp_company_grants_plan.py report
  python scripts/cp_company_grants_plan.py apply cp_company_grants_proposal.json            （乾跑）
  python scripts/cp_company_grants_plan.py apply cp_company_grants_proposal.json --yes      （寫入）

JSON 格式：{"roles": {"角色名稱": ["CH", "OU"], ...}}
系統管理員（權限 "*"）與沒有任何角色的使用者不列入授權（系統管理員本來就是全部公司）。
"""
import json
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from app.core.database import SessionLocal  # noqa: E402
from app.core.cycle_purchase_database import CyclePurchaseSessionLocal  # noqa: E402
from app.dependencies import get_user_permissions  # noqa: E402
from app.services.cycle_purchase_company_scope import resolve_company_code, COMPANY_PERM_PREFIX  # noqa: E402
from app.models.role import Role  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.user_role import UserRole  # noqa: E402
from app.models.user_department import UserDepartment  # noqa: E402
from app.models.reference_data import Company, RefDepartment  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402
from app.models.role_permission import RolePermission  # noqa: E402

PROPOSAL_FILE = "cp_company_grants_proposal.json"


def legacy_codes_for_user(main_db, cp_db, user) -> set:
    """改版前的規則：部門所屬公司 ∪ 主要公司別。"""
    names = {n for (n,) in (
        main_db.query(Company.name)
        .join(RefDepartment, RefDepartment.company_id == Company.id)
        .join(UserDepartment, UserDepartment.department_id == RefDepartment.id)
        .filter(UserDepartment.user_id == user.id).distinct().all())}
    tenant = main_db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if tenant is not None and tenant.source_company_id:
        try:
            comp = main_db.query(Company).filter(Company.id == int(tenant.source_company_id)).first()
        except (TypeError, ValueError):
            comp = None
        if comp is not None:
            names.add(comp.name)
    codes = {resolve_company_code(cp_db, n) for n in names}
    return {c for c in codes if c}


def report() -> int:
    main_db = SessionLocal()
    cp_db = CyclePurchaseSessionLocal()
    try:
        proposal = {"roles": {}, "skipped": []}
        for role in main_db.query(Role).order_by(Role.name).all():
            members = (main_db.query(User)
                       .join(UserRole, UserRole.user_id == User.id)
                       .filter(UserRole.role_id == role.id).all())
            suggested, users = set(), []
            for u in members:
                if "*" in get_user_permissions(u.id, main_db):
                    proposal["skipped"].append({"role": role.name, "user": u.email, "reason": "系統管理員"})
                    continue
                codes = legacy_codes_for_user(main_db, cp_db, u)
                suggested |= codes
                users.append({"email": u.email, "legacy_codes": sorted(codes)})
            proposal["roles"][role.name] = {
                "role_id": role.id,
                "suggested_codes": sorted(suggested),
                "users": users,
            }
        with open(PROPOSAL_FILE, "w", encoding="utf-8") as f:
            json.dump(proposal, f, ensure_ascii=False, indent=2)
        print(f"已寫入 {PROPOSAL_FILE}")
        for name, info in proposal["roles"].items():
            print(f"- 角色「{name}」建議可見：{info['suggested_codes'] or '（無）'}，成員 {len(info['users'])} 人")
            for u in info["users"]:
                print(f"    {u['email']}  舊規則可見 {u['legacy_codes'] or '（無）'}")
        if proposal["skipped"]:
            print("略過：", proposal["skipped"])
        return 0
    finally:
        main_db.close()
        cp_db.close()


def apply(path: str, write: bool) -> int:
    with open(path, encoding="utf-8") as f:
        plan = json.load(f)["roles"]
    main_db = SessionLocal()
    cp_db = CyclePurchaseSessionLocal()
    try:
        for role_name, value in plan.items():
            # 接受兩種格式：report 產生的（{"suggested_codes": [...]}）或確認版（["CH", ...]）
            codes = value["suggested_codes"] if isinstance(value, dict) else value
            role = main_db.query(Role).filter(Role.name == role_name).first()
            if role is None:
                print(f"[跳過] 找不到角色：{role_name}")
                continue
            for c in codes:
                if resolve_company_code(cp_db, c) is None:
                    raise SystemExit(f"公司代碼無效或未啟用：{c}（角色 {role_name}）")
            want = {COMPANY_PERM_PREFIX + c.lower() for c in codes}
            have = {rp.permission_key for rp in main_db.query(RolePermission)
                    .filter(RolePermission.role_id == role.id,
                            RolePermission.permission_key.like(COMPANY_PERM_PREFIX + "%")).all()}
            to_add, to_remove = sorted(want - have), sorted(have - want)
            print(f"角色「{role_name}」：新增 {to_add or '—'}，移除 {to_remove or '—'}")
            if write:
                for key in to_remove:
                    main_db.query(RolePermission).filter(
                        RolePermission.role_id == role.id, RolePermission.permission_key == key).delete()
                for key in to_add:
                    main_db.add(RolePermission(id=str(uuid.uuid4()), role_id=role.id, permission_key=key))
        if write:
            main_db.commit()
            print("已寫入 role_permissions")
        else:
            main_db.rollback()
            print("乾跑：未寫入。確認後加上 --yes 執行。")
        return 0
    finally:
        main_db.close()
        cp_db.close()


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "report":
        sys.exit(report())
    if len(sys.argv) >= 3 and sys.argv[1] == "apply":
        sys.exit(apply(sys.argv[2], write="--yes" in sys.argv))
    print(__doc__)
    sys.exit(2)
