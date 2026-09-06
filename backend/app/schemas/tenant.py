from typing import Optional

from pydantic import BaseModel
from datetime import datetime


class TenantOut(BaseModel):
    id: str
    code: str
    name: str
    type: str
    is_active: bool
    created_at: datetime
    # None ＝ 本地自建的舊據點；有值 ＝ 鏡像自「系統設定 → 公司/部門管理」
    # 的 Company.id（見 services/tenant_company_sync.py）
    source_company_id: Optional[str] = None

    class Config:
        from_attributes = True


class TenantCreate(BaseModel):
    code: str
    name: str
    type: str
