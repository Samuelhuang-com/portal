"""週期採購 — 採購單 Pydantic Schemas"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class POItemOut(BaseModel):
    id: int
    po_id: int
    summary_id: int
    item_id: int
    item_code: str
    item_name: str
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    ordered_qty: int
    subtotal: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class POUpdate(BaseModel):
    expected_date: Optional[date] = None
    notes: Optional[str] = None


class POStatusPayload(BaseModel):
    status: str  # issued | cancelled


class POOut(BaseModel):
    id: int
    po_no: str
    cycle_id: int
    cycle_name: Optional[str] = None
    period_label: str
    company: str
    vendor_id: int
    vendor_name: Optional[str] = None
    buyer_user_id: Optional[str] = None
    buyer_name: Optional[str] = None
    expected_date: Optional[date] = None
    total_amount: Decimal
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PODetail(POOut):
    items: List[POItemOut] = []
