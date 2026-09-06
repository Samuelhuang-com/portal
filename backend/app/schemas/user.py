from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class UserDepartmentOut(BaseModel):
    """使用者所屬部門（來自 user_departments ↔ RefDepartment，2026-09-01）"""
    id: int              # RefDepartment.id
    name: str            # 部門名稱
    company: str         # 公司名稱（RefDepartment → Company.name）


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str = Field(min_length=8)
    tenant_id: str
    role_names: List[str] = ["viewer"]
    # 2026-09-01：使用者可屬多公司多部門（user_departments）。公司由部門推導，
    # tenant_id 退化為「主要公司別」（顯示與稽核歸屬）。
    department_ids: List[int] = []


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role_names: Optional[List[str]] = None
    email: Optional[str] = None  # 僅 system_admin / tenant_admin 可更新
    new_password: Optional[str] = Field(default=None, min_length=8)  # 管理員直接設定新密碼
    # 2026-09-01 新增：主要公司別（＝公司/部門管理的公司）原本只能在建立時指定，
    # 編輯 Modal 沒有這個欄位，調公司就只能砍帳號重建。
    tenant_id: Optional[str] = None
    # None＝不動；[]＝清空。與 role_names 的語意一致（整批取代）。
    department_ids: Optional[List[int]] = None


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    tenant_id: str
    tenant_name: str
    is_active: bool
    roles: List[str]
    departments: List[UserDepartmentOut] = []
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
