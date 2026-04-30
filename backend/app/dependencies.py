from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

bearer = HTTPBearer()


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 無效或已過期"
        )

    user = (
        db.query(User)
        .filter(
            User.id == payload.get("sub"),
            User.is_active == True,
        )
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="使用者不存在或已停用"
        )
    return user


def _get_roles(user_id: str, db: Session) -> set[str]:
    from app.models.user_role import UserRole
    from app.models.role import Role

    rows = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .all()
    )
    return {r[0] for r in rows}


def get_user_permissions(user_id: str, db: Session) -> list[str]:
    """
    取得使用者所有 permission_key 清單。
    - system_admin 角色：回傳 ["*"]（萬用符，代表擁有所有權限）
    - 其他角色：聯集所有 role_permissions 中的 permission_key
    新模組開發期間預設只有 system_admin 可存取（前端 permissionKey 設為
    'system_admin_only' 或直接不加入 role_permissions 即可）。
    """
    from app.models.user_role import UserRole
    from app.models.role import Role
    from app.models.role_permission import RolePermission

    # 取得使用者的所有 role
    role_rows = (
        db.query(Role.id, Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .all()
    )

    # system_admin 擁有所有權限
    if any(r[1] == "system_admin" for r in role_rows):
        return ["*"]

    if not role_rows:
        return []

    role_ids = [r[0] for r in role_rows]
    perm_rows = (
        db.query(RolePermission.permission_key)
        .filter(RolePermission.role_id.in_(role_ids))
        .all()
    )
    return list({r[0] for r in perm_rows})


def require_roles(*roles: str):
    def checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        user_roles = _get_roles(current_user.id, db)
        if "system_admin" in user_roles:
            return current_user
        if not any(r in user_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="權限不足"
            )
        return current_user

    return checker


def require_permission(permission_key: str):
    """
    FastAPI Dependency 工廠：要求使用者具備指定的 permission_key。
    system_admin 無條件通過（permissions=["*"]）。
    用法：Depends(require_permission("settings_users_manage"))

    【新模組開發規則】
    開發期間使用 permission_key="system_admin_only"（不會被賦予給任何一般角色），
    完成並測試後，再透過角色管理介面將對應 permission_key 加入適當角色。
    """
    def checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        permissions = get_user_permissions(current_user.id, db)
        # "*" = system_admin 萬用符
        if "*" in permissions:
            return current_user
        if permission_key not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"權限不足（需要 {permission_key}）",
            )
        return current_user

    return checker


def is_system_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_roles = _get_roles(current_user.id, db)
    if "system_admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要系統管理員權限"
        )
    return current_user
