from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.time import twnow
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, decode_token
from app.dependencies import get_current_user
from app.models.user import User
from app.models.user_role import UserRole
from app.models.role import Role
from app.models.tenant import Tenant
from app.models.audit_log import AuditLog
from app.schemas.auth import LoginRequest, TokenResponse, UserInfo

router = APIRouter()


def _get_user_roles(user_id: str, db: Session) -> list[str]:
    rows = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .all()
    )
    return [r[0] for r in rows]


def _build_user_info(user: User, db: Session) -> UserInfo:
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    return UserInfo(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=user.tenant_id,
        tenant_name=tenant.name if tenant else "",
        roles=_get_user_roles(user.id, db),
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    identifier = data.identifier.lower().strip()
    if "@" not in identifier:
        identifier = f"{identifier}@portal.local"

    user = (
        db.query(User).filter(User.email == identifier, User.is_active == True).first()
    )
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="帳號或密碼錯誤"
        )

    roles = _get_user_roles(user.id, db)
    token = create_access_token(
        subject=user.id,
        extra_claims={"email": user.email, "roles": roles},
    )

    user.last_login = twnow()
    db.add(
        AuditLog(
            user_id=user.id,
            tenant_id=user.tenant_id,
            action="login",
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()

    return TokenResponse(access_token=token, user=_build_user_info(user, db))


@router.get("/me", response_model=UserInfo)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _build_user_info(current_user, db)


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    db.add(
        AuditLog(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="logout",
        )
    )
    db.commit()
    return {"message": "已登出"}
