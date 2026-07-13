"""週期採購 — 料號主檔 + 料號對照表 Pydantic Schemas"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class ItemMappingBase(BaseModel):
    company: str
    # 2026-07-11 新增：這個料號在這家公司屬於哪個部門（工務／清潔／文具印刷／
    # 營業用品），供請購單「可選料號」查詢按公司＋部門篩選用。
    department_id: int
    original_code: Optional[str] = None
    original_name: Optional[str] = None
    original_vendor_name: Optional[str] = None
    # 2026-07-11 新增：這個料號在這家公司實際跟哪個供應商叫貨，供彙整單/採購單
    # 按供應商分單用；可為 None（原始資料廠商欄位本來就空的情況）。
    vendor_id: Optional[int] = None
    original_unit_price: Optional[Decimal] = None
    is_confirmed: bool = False
    notes: Optional[str] = None


class ItemMappingCreate(ItemMappingBase):
    pass


class ItemMappingUpdate(BaseModel):
    company: Optional[str] = None
    department_id: Optional[int] = None
    original_code: Optional[str] = None
    original_name: Optional[str] = None
    original_vendor_name: Optional[str] = None
    vendor_id: Optional[int] = None
    original_unit_price: Optional[Decimal] = None
    is_confirmed: Optional[bool] = None
    notes: Optional[str] = None


class ItemMappingOut(ItemMappingBase):
    id: int
    item_id: int
    department_name: Optional[str] = None
    vendor_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ItemBase(BaseModel):
    item_code: str
    item_name: str
    spec: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    default_qty: int = 0
    moq: int = 0
    max_stock: Optional[int] = None
    min_stock: Optional[int] = None
    unit_price: Optional[Decimal] = None
    default_vendor_id: Optional[int] = None
    is_active: bool = True
    is_cycle_item: bool = True
    notes: Optional[str] = None


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    item_code: Optional[str] = None
    item_name: Optional[str] = None
    spec: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    default_qty: Optional[int] = None
    moq: Optional[int] = None
    max_stock: Optional[int] = None
    min_stock: Optional[int] = None
    unit_price: Optional[Decimal] = None
    default_vendor_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_cycle_item: Optional[bool] = None
    notes: Optional[str] = None


class ItemOut(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime
    default_vendor_name: Optional[str] = None

    class Config:
        from_attributes = True


class ItemDetail(ItemOut):
    mappings: List[ItemMappingOut] = []


class ItemListResponse(BaseModel):
    items: List[ItemOut]
    total: int
    page: int
    per_page: int
