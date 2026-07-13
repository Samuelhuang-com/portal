"""週期採購 — 請購單 + 請購明細 Pydantic Schemas"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class RequestItemCreate(BaseModel):
    item_id: int
    request_qty: int = 0
    account_code_id: Optional[int] = None
    notes: Optional[str] = None


class RequestItemUpdate(BaseModel):
    request_qty: Optional[int] = None
    account_code_id: Optional[int] = None
    notes: Optional[str] = None


class RequestItemOut(BaseModel):
    id: int
    request_id: int
    item_id: int
    item_mapping_id: Optional[int] = None
    account_code_id: Optional[int] = None
    account_code_label: Optional[str] = None
    item_code: str
    item_name: str
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    request_qty: int
    subtotal: Decimal
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RequestCreate(BaseModel):
    """
    手動新增單一部門的請購單（備用路徑；一般情況下請購單由「產生本期請購單」
    一次幫所有適用部門建好）。2026-07-11 拿掉批次後，改成掛週期 + 期別。
    """
    cycle_id: int
    department_id: int
    period_label: str
    cost_center_id: Optional[int] = None


class RequestUpdate(BaseModel):
    cost_center_id: Optional[int] = None
    notes: Optional[str] = None


class RequestRejectPayload(BaseModel):
    reason: str


class GenerateRequestsPayload(BaseModel):
    """「產生本期請購單」：依週期設定的 applicable_scope，一次幫所有適用公司的
    啟用中部門建一張空白請購單（同 cycle_id+period_label 重複觸發是冪等的）。"""
    cycle_id: int
    period_label: str


class RequestOut(BaseModel):
    id: int
    request_no: str
    cycle_id: int
    cycle_name: Optional[str] = None
    period_label: str
    department_id: int
    department_name: Optional[str] = None
    company: str
    cost_center_id: Optional[int] = None
    cost_center_name: Optional[str] = None
    total_amount: Decimal
    status: str
    submitted_by_user_id: Optional[str] = None
    submitted_by_name: Optional[str] = None
    submitted_at: Optional[datetime] = None
    approved_by_user_id: Optional[str] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RequestDetail(RequestOut):
    items: List[RequestItemOut] = []


class AvailableItemOut(BaseModel):
    """給填單頁面「選料號」用：只回傳該請購單所屬公司有對照的料號"""
    item_id: int
    item_mapping_id: int
    item_code: str
    item_name: str
    unit: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[Decimal] = None
    is_confirmed: bool


class TodoSummary(BaseModel):
    """Dashboard 待辦提醒：登入者自己部門待填、以及（若有簽核權限）全部待簽核。"""
    my_pending: List[RequestOut] = []
    pending_approval_count: int = 0
    pending_approval: List[RequestOut] = []
