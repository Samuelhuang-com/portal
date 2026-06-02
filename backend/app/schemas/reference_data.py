"""
F1 — 基礎參考資料 Pydantic Schema
  Company / Department / PricingSpec
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


# ── Company ────────────────────────────────────────────────────────────────

class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="公司名稱")


class CompanyUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="公司名稱")


class CompanyResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CompanyOption(BaseModel):
    """供下拉使用（僅啟用中）"""
    value: str   # name（存入 DB 的值）
    label: str   # name（顯示文字）
    id: int      # 供前端過濾部門下拉使用

    class Config:
        from_attributes = True


# ── Department ─────────────────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name:       str = Field(..., min_length=1, max_length=100, description="部門名稱")
    company_id: int = Field(..., description="所屬公司 ID")


class DepartmentUpdate(BaseModel):
    name:       Optional[str] = Field(None, min_length=1, max_length=100)
    company_id: Optional[int] = None


class DepartmentResponse(BaseModel):
    id:           int
    name:         str
    company_id:   int
    company_name: str = ""
    is_active:    bool
    created_at:   datetime

    @validator("company_name", pre=True, always=True)
    @classmethod
    def _resolve_company_name(cls, v, values):
        return v or ""

    class Config:
        from_attributes = True


class DepartmentOption(BaseModel):
    """供下拉使用（僅啟用中）"""
    value: str   # name
    label: str   # name

    class Config:
        from_attributes = True


# ── PricingSpec ────────────────────────────────────────────────────────────

class PricingSpecCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="計價規格名稱")


class PricingSpecUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class PricingSpecResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PricingSpecOption(BaseModel):
    """供下拉使用"""
    value: str
    label: str

    class Config:
        from_attributes = True


# ── SlaMetricType ──────────────────────────────────────────────────────────

class SlaMetricTypeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="指標類型名稱")
    description: Optional[str] = Field(None, max_length=200)


class SlaMetricTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class SlaMetricTypeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SlaMetricTypeOption(BaseModel):
    """供 SLA Tab 下拉使用（僅啟用中）"""
    value: str   # name
    label: str   # name

    class Config:
        from_attributes = True
