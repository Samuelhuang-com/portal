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
