"""週期採購 — 驗收單 Pydantic Schemas"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class ReceivingCreate(BaseModel):
    po_id: int
    received_date: date
    notes: Optional[str] = None


class ReceivableItemOut(BaseModel):
    """給「新增驗收單明細」畫面用：這張驗收單所屬採購單的每個明細行，
    附累計已驗收量／剩餘量，以及這張（草稿）驗收單目前已經填的值（若有）。"""
    po_item_id: int
    item_id: int
    item_code: str
    item_name: str
    unit: Optional[str] = None
    ordered_qty: int
    previously_received_qty: int  # 不含這張驗收單本身已填的量
    remaining_qty: int            # ordered_qty - previously_received_qty，僅供參考，不強制擋輸入
    receiving_item_id: Optional[int] = None
    received_qty: Optional[int] = None
    is_final_for_item: Optional[bool] = None
    variance_reason: Optional[str] = None


class ReceivingItemUpsert(BaseModel):
    po_item_id: int
    received_qty: int
    is_final_for_item: bool = True
    variance_reason: Optional[str] = None


class ReceivingItemOut(BaseModel):
    id: int
    receiving_id: int
    po_item_id: int
    item_id: int
    item_code: str
    item_name: str
    unit: Optional[str] = None
    ordered_qty: int
    previously_received_qty: int
    received_qty: int
    is_final_for_item: bool
    variance_qty: Optional[int] = None
    variance_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReceivingOut(BaseModel):
    id: int
    receiving_no: str
    po_id: int
    po_no: Optional[str] = None
    company: Optional[str] = None
    vendor_name: Optional[str] = None
    receiver_user_id: Optional[str] = None
    receiver_name: Optional[str] = None
    received_date: date
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReceivingDetail(ReceivingOut):
    items: List[ReceivingItemOut] = []


class ReceivingReportRow(BaseModel):
    """進貨數量報表：依月份＋公司＋供應商＋料號彙總（前端再依需要篩選／樞紐）。
    只統計已送出（completed/discrepancy）的驗收單，草稿不算。"""
    period: str
    company: str
    vendor_id: Optional[int] = None
    vendor_name: Optional[str] = None
    item_id: int
    item_code: str
    item_name: str
    unit: Optional[str] = None
    total_received_qty: int
    total_amount: Decimal
    receiving_count: int
