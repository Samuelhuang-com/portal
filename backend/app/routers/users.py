from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import random
import string
from datetime import timedelta
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.core.time import twnow
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
    AdminResetPasswordResponse,
)

OTP_EXPIRES_MINUTES = 15

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
        must_change_password=user.must_change_password or False,
    )


def _generate_otp() -> str:
    """產生 6 位數字 OTP。"""
    return "".join(random.choices(string.digits, k=6))


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
    # email 更新（system_admin + tenant_admin 皆可；需唯一性檢查）
    if data.email is not None:
        new_email = data.email.lower().strip()
        if "@" not in new_email:
            new_email = f"{new_email}@portal.local"
        if new_email != user.email:
            conflict = db.query(User).filter(User.email == new_email, User.id != user_id).first()
            if conflict:
                raise HTTPException(status_code=400, detail="此 Email 已被其他帳號使用")
            user.email = new_email
    # 管理員直接設定新密碼（不走 OTP 流程）
    if data.new_password is not None:
        user.hashed_password = hash_password(data.new_password)
        user.otp_code = None
        user.must_change_password = False
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
    # 若帳號標記為「必須更改密碼」（OTP 登入後），免驗舊密碼
    if not current_user.must_change_password:
        if not data.old_password:
            raise HTTPException(status_code=400, detail="請輸入舊密碼")
        if not verify_password(data.old_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="舊密碼錯誤")

    current_user.hashed_password = hash_password(data.new_password)
    # 清除 OTP 狀態與強制更改旗標
    current_user.must_change_password = False
    current_user.otp_code = None
    current_user.otp_expires_at = None
    db.add(
        AuditLog(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="change_password",
            resource_type="user",
            resource_id=current_user.id,
        )
    )
    db.commit()
    return {"message": "密碼已更新"}


@router.post("/{user_id}/reset-password", response_model=AdminResetPasswordResponse)
def admin_reset_password(
    user_id: str,
    current_user: User = Depends(require_roles("system_admin", "tenant_admin")),
    db: Session = Depends(get_db),
):
    """
    管理員替指定使用者產生 OTP。
    OTP 明文僅回傳一次，管理員需口頭告知使用者。
    使用者以 OTP 登入後，系統強制要求設定新密碼。
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能重設自己的密碼（請使用「修改密碼」功能）")

    otp = _generate_otp()
    user.otp_code = hash_password(otp)
    user.otp_expires_at = twnow() + timedelta(minutes=OTP_EXPIRES_MINUTES)
    user.must_change_password = True

    db.add(
        AuditLog(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="admin_reset_password",
            resource_type="user",
            resource_id=user_id,
        )
    )
    db.commit()

    return AdminResetPasswordResponse(
        otp=otp,
        expires_minutes=OTP_EXPIRES_MINUTES,
        message=f"已為 {user.full_name} 產生一次性密碼，請口頭告知使用者，密碼 {OTP_EXPIRES_MINUTES_MINUTES} 分鐘後失效。",
    )


# ── 人員選單（供合約等模組的 manager/reviewer 下拉使用）────────────────
class UserOptionItem(BaseModel):
    value: str   # full_name
    label: str   # full_name
    user_id: str


@router.get("/options", response_model=list[UserOptionItem])
def list_user_options(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取得啟用中使用者名稱清單，供 manager/reviewer 下拉使用（任何登入者可呼叫）"""
    users = (
        db.query(User)
        .filter(User.is_active == True)
        .order_by(User.full_name)
        .all()
    )
    return [
        UserOptionItem(value=u.full_name, label=u.full_name, user_id=u.id)
        for u in users
    ]
