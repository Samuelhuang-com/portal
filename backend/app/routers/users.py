from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.dependencies import get_current_user, is_system_admin, require_roles
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.tenant import Tenant
from app.models.audit_log import AuditLog
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserOut,
    UserListResponse,
    ChangePasswordRequest,
)

router = APIRouter()


def _get_roles(user_id: str, db: Session) -> list[str]:
    return [
        r[0]
        for r in db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .all()
    ]


def _build_user_out(user: User, db: Session) -> UserOut:
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=user.tenant_id,
        tenant_name=tenant.name if tenant else "",
        is_active=user.is_active,
        roles=_get_roles(user.id, db),
        last_login=user.last_login,
        created_at=user.created_at,
    )


@router.get("", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    tenant_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_roles("system_admin", "tenant_admin")),
    db: Session = Depends(get_db),
):
    q = db.query(User)
    if "system_admin" not in _get_roles(current_user.id, db):
        q = q.filter(User.tenant_id == current_user.tenant_id)
    elif tenant_id:
        q = q.filter(User.tenant_id == tenant_id)
    if search:
        q = q.filter(
            (User.full_name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )
    total = q.count()
    users = q.offset((page - 1) * per_page).limit(per_page).all()
    return UserListResponse(
        items=[_build_user_out(u, db) for u in users],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=UserOut)
def create_user(
    data: UserCreate,
    current_user: User = Depends(require_roles("system_admin", "tenant_admin")),
    db: Session = Depends(get_db),
):
    email = data.email.lower().strip()
    if "@" not in email:
        email = f"{email}@portal.local"
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email 已存在")
    tenant = db.query(Tenant).filter(Tenant.id == data.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="據點不存在")

    user = User(
        email=email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        tenant_id=data.tenant_id,
    )
    db.add(user)
    db.flush()

    for role_name in data.role_names:
        role = db.query(Role).filter(Role.name == role_name).first()
        if role:
            db.add(
                UserRole(
                    user_id=user.id,
                    role_id=role.id,
                    tenant_id=data.tenant_id,
                    granted_by=current_user.id,
                )
            )

    db.add(
        AuditLog(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="create",
            resource_type="user",
            resource_id=user.id,
        )
    )
    db.commit()
    db.refresh(user)
    return _build_user_out(user, db)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    data: UserUpdate,
    current_user: User = Depends(require_roles("system_admin", "tenant_admin")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.role_names is not None:
        db.query(UserRole).filter(UserRole.user_id == user_id).delete()
        for role_name in data.role_names:
            role = db.query(Role).filter(Role.name == role_name).first()
            if role:
                db.add(
                    UserRole(
                        user_id=user.id,
                        role_id=role.id,
                        tenant_id=user.tenant_id,
                        granted_by=current_user.id,
                    )
                )
    db.add(
        AuditLog(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="update",
            resource_type="user",
            resource_id=user_id,
        )
    )
    db.commit()
    db.refresh(user)
    return _build_user_out(user, db)


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    current_user: User = Depends(is_system_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能刪除自己")
    db.delete(user)
    db.commit()
    return {"message": "使用者已刪除"}


@router.post("/me/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="舊密碼錯誤")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "密碼已更新"}
