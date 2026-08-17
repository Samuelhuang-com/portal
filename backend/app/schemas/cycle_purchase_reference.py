"""週期採購 — 部門／成本中心／會計科目主檔 Pydantic Schemas"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DepartmentBase(BaseModel):
    company: str
    dept_code: str
    dept_name: str
    owner_user_id: Optional[str] = None
    is_active: bool = True


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    company: Optional[str] = None
    dept_code: Optional[str] = None
    dept_name: Optional[str] = None
    owner_user_id: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentOut(DepartmentBase):
    id: int
    owner_name: Optional[str] = None
    created_at: datetime
    # 2026-08-17 新增：非 None 代表這筆是從 portal.db Company/RefDepartment
    # 鏡像同步過來的（見 cycle_purchase_department_sync.py），前端用來顯示
    # 「同步」Tag，並把 company／dept_name 欄位設成唯讀（後端 update_department
    # 也會剔除這兩欄，前端唯讀只是提示，不是唯一防線）。
    source_department_id: Optional[str] = None

    class Config:
        from_attributes = True


class CostCenterBase(BaseModel):
    department_id: int
    cc_code: str
    cc_name: str
    is_active: bool = True


class CostCenterCreate(CostCenterBase):
    pass


class CostCenterUpdate(BaseModel):
    department_id: Optional[int] = None
    cc_code: Optional[str] = None
    cc_name: Optional[str] = None
    is_active: Optional[bool] = None


class CostCenterOut(CostCenterBase):
    id: int
    created_at: datetime
    department_name: Optional[str] = None

    class Config:
        from_attributes = True


class AccountCodeBase(BaseModel):
    code: str
    name: str
    is_active: bool = True


class AccountCodeCreate(AccountCodeBase):
    pass


class AccountCodeUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None


class AccountCodeOut(AccountCodeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
