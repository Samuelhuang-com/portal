from pydantic import BaseModel
from typing import List


class LoginRequest(BaseModel):
    identifier: str
    password: str


class UserInfo(BaseModel):
    id: str
    email: str
    full_name: str
    tenant_id: str
    tenant_name: str
    roles: List[str]
    # 使用者所有 permission_key 清單；system_admin 為 ["*"]
    permissions: List[str] = []
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo
