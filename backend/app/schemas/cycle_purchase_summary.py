"""週期採購 — 彙整單 Pydantic Schemas"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class GenerateSummaryPayload(BaseModel):
    """「產生彙整」：把某週期＋期別下所有已核准請購明細，按公司＋料號彙總。冪等。"""
    cycle_id: int
    period_label: str


class SummaryUpdate(BaseModel):
    """調整量／調整原因（僅 draft 狀態的彙整列可編輯）"""
    adjusted_qty: Optional[int] = None
    adjust_reason: Optional[str] = None


class SummaryOut(BaseModel):
    id: int
    cycle_id: int
    cycle_name: Optional[str] = None
    period_label: str
    company: str
    item_id: int
    item_mapping_id: Optional[int] = None
    vendor_id: Optional[int] = None
    vendor_name: Optional[str] = None
    item_code: str
    item_name: str
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    demand_qty: int
    adjusted_qty: int
    adjust_reason: Optional[str] = None
    status: str
    po_id: Optional[int] = None
    po_no: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConvertToPoPayload(BaseModel):
    """轉採購單：指定週期＋期別＋公司＋供應商，把符合條件、狀態仍是 draft 的彙整列
    合成一張採購單（調整量為 0 的列會一併鎖定但不會出現在採購明細裡）。"""
    cycle_id: int
    period_label: str
    company: str
    vendor_id: int


class VendorGroupOut(BaseModel):
    """給「轉採購單」畫面用：某週期＋期別＋公司下，還沒轉單的彙整列依供應商分組統計。"""
    company: str
    vendor_id: Optional[int] = None
    vendor_name: Optional[str] = None
    item_count: int
    total_amount: Decimal
    has_missing_vendor: bool = False
