"""週期採購 — 請款單 Pydantic Schemas"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class PaymentCreate(BaseModel):
    po_id: int
    receiving_ids: List[int]
    invoice_no: str
    invoice_date: date
    invoice_amount: Decimal
    notes: Optional[str] = None


class PaymentUpdate(BaseModel):
    invoice_no: Optional[str] = None
    invoice_date: Optional[date] = None
    invoice_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    # 2026-07-11（修正）：分攤總額與發票金額不符時，送出前要填的差異原因，
    # 也是透過這個 endpoint（PUT /payments/{id}）更新，跟其他表頭欄位一起走。
    amount_diff_reason: Optional[str] = None


class PaymentStatusPayload(BaseModel):
    status: str  # "paying" | "paid"


class PayableReceivingOut(BaseModel):
    """給「建立請款單」畫面用：這張採購單底下還沒被任何請款單涵蓋、且已送出
    （completed／discrepancy）的驗收單。"""
    receiving_id: int
    receiving_no: str
    received_date: date
    status: str
    estimated_amount: Decimal  # 這張驗收單的估算金額（驗收數量 × 採購單價加總），僅供參考


class AllocationUpdate(BaseModel):
    allocated_amount: Decimal
    adjust_reason: Optional[str] = None


class AllocationOut(BaseModel):
    id: int
    payment_id: int
    company: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    cost_center_id: Optional[int] = None
    cost_center_name: Optional[str] = None
    account_code_id: Optional[int] = None
    account_code_label: Optional[str] = None
    suggested_amount: Decimal
    allocated_amount: Decimal
    adjust_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentReceivingOut(BaseModel):
    id: int
    receiving_id: int
    receiving_no: Optional[str] = None
    received_date: Optional[date] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


class PaymentOut(BaseModel):
    id: int
    payment_no: str
    po_id: int
    po_no: Optional[str] = None
    company: Optional[str] = None
    vendor_name: Optional[str] = None
    invoice_no: str
    invoice_date: date
    invoice_amount: Decimal
    total_allocated: Optional[Decimal] = None  # 分攤金額加總，附加欄位供列表顯示
    status: str
    amount_diff_reason: Optional[str] = None
    processor_user_id: Optional[str] = None
    processor_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentDetail(PaymentOut):
    allocations: List[AllocationOut] = []
    receivings: List[PaymentReceivingOut] = []
