from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str = Field(min_length=8)
    tenant_id: str
    role_names: List[str] = ["viewer"]


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role_names: Optional[List[str]] = None
    email: Optional[str] = None  # 僅 system_admin / tenant_admin 可更新
    new_password: Optional[str] = Field(default=None, min_length=8)  # 管理員直接設定新密碼


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    tenant_id: str
    tenant_name: str
    is_active: bool
    roles: List[str]
    last_login: Optional[datetime] = None
    created_at: datetime
    must_change_password: bool = False

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    old_password: Optional[str] = None   # must_change_password=True 時免填
    new_password: str = Field(min_length=8)


class AdminResetPasswordResponse(BaseModel):
    """管理員重設密碼後回傳的 OTP（明文，只出現一次）"""
    otp: str
    expires_minutes: int = 15
    message: str


class UserListResponse(BaseModel):
    items: List[UserOut]
    total: int
    page: int
    per_page: int
