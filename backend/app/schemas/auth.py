from pydantic import BaseModel
from typing import List


class LoginRequest(BaseModel):
    identifier: str
    password: str


class UserDepartmentInfo(BaseModel):
    """登入者所屬部門（user_departments，2026-09-01 多公司多部門）"""
    id: int              # RefDepartment.id
    name: str
    company: str


class UserInfo(BaseModel):
    id: str
    email: str
    full_name: str
    tenant_id: str
    tenant_name: str
    roles: List[str]
    # 使用者所有 permission_key 清單；system_admin 為 ["*"]
    permissions: List[str] = []
    # 2026-09-01：login 即知公司別＋部門。公司由部門推導（company 欄位），
    # tenant_id/tenant_name 是「主要公司別」（顯示與稽核歸屬）。
    departments: List[UserDepartmentInfo] = []
    is_active: bool
    must_change_password: bool = False

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo
    must_change_password: bool = False


class ForgotPasswordRequest(BaseModel):
    identifier: str  # email 或 username（與登入欄位一致）
