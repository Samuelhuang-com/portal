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


class RevertPoPayload(BaseModel):
    """「退回彙整單」：把這張採購單作廢，並把對應的彙整列解鎖回 draft。
    退回原因必填（會寫進採購單備註與稽核紀錄）。

    ⚠️ 與「取消」（POST /pos/{id}/status，status=cancelled）是**兩個不同動作**：
    取消只把單標成 cancelled、彙整列**維持鎖定**（語意是「這批本期不買了」）；
    退回則會把彙整列放回可編輯狀態，讓買家重新調整後再轉一張新單。"""
    reason: str


class RevertPoResult(BaseModel):
    """退回結果。deleted_item_count 是被刪掉的採購明細筆數——明細不保留是因為
    `po_items.summary_id` 是 RESTRICT 外鍵，留著會擋住之後彙整列的刪除；
    明細內容已完整寫進稽核紀錄的 old_value（見
    services/cycle_purchase_po_service.py 開頭說明）。"""
    po_id: int
    po_no: str
    period_label: str
    company: str
    vendor_id: int
    unlocked_summary_count: int
    deleted_item_count: int
    message: str
    next_step: Optional[str] = None
