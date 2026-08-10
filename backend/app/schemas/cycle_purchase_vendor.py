"""週期採購 — 供應商主檔 Pydantic Schemas"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class VendorBase(BaseModel):
    vendor_code: str
    vendor_name: str
    tax_id: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    vendor_code: Optional[str] = None
    vendor_name: Optional[str] = None
    tax_id: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class VendorOut(VendorBase):
    id: int
    # 2026-08-10：鏡像自合約模組 vendors 的來源鍵（VND-NNNN）。
    # 非空 = 受同步管控，前端須把 vendor_code/vendor_name/tax_id/contact_* 設唯讀；
    # 為 None = 週採本地自建，全部欄位可編。
    source_vendor_id: Optional[str] = None
    synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
