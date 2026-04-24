from pydantic import BaseModel
from datetime import datetime


class TenantOut(BaseModel):
    id: str
    code: str
    name: str
    type: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TenantCreate(BaseModel):
    code: str
    name: str
    type: str
