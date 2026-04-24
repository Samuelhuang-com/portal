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

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class UserListResponse(BaseModel):
    items: List[UserOut]
    total: int
    page: int
    per_page: int
