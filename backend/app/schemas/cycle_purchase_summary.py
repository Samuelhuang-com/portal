"""週期採購 — 彙整單 Pydantic Schemas"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class EligibleRequestOut(BaseModel):
    """「彙整單」畫面用：某週期＋公司＋期別（period_label）下，已關閉
    （is_closed=True）且尚未被彙整過的請購單（供使用者勾選要納入這次彙整的
    範圍，見 2026-07-16 第二次調整、2026-07-17 第三次調整說明）。"""
    id: int
    request_no: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    submitted_by_name: Optional[str] = None
    closed_by_name: Optional[str] = None
    closed_at: Optional[datetime] = None
    total_amount: Decimal


class GenerateFromRequestsPayload(BaseModel):
    """「產生彙整」：把使用者勾選的這些請購單（必須都已關閉 is_closed=True 且
    尚未被彙整過）彙整成彙整列。period_label 由系統從勾選的請購單本身的
    period_label 讀出來（不是「產生當下」的日期），不接受使用者指定。"""
    request_ids: list[int]


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
    department_id: Optional[int] = None
    department_name: Optional[str] = None
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
    ragic_push_batch_no: Optional[str] = None
    ragic_pushed: bool = False
    ragic_record_id: Optional[str] = None
    ragic_pushed_at: Optional[datetime] = None
    ragic_push_error: Optional[str] = None
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


# ═══════════════════════════════════════════════════════════════════════════
# 2026-07-16 新增：部門別＋小計 拆解畫面、拋轉 Ragic
# ═══════════════════════════════════════════════════════════════════════════

class DepartmentBreakdownRow(BaseModel):
    """匯總請購單畫面用：某料號下，某一個部門的需求／調整量與小計。"""
    summary_id: int
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    demand_qty: int
    adjusted_qty: int
    subtotal: Decimal
    status: str


class DepartmentBreakdownOut(BaseModel):
    """匯總請購單畫面用：依料號分組，展開底下各部門別＋部門小計（比照 0715 會議
    「匯總請購單」設計方向：一張單涵蓋多部門，用子表列部門別＋小計）。"""
    company: str
    item_id: int
    item_code: str
    item_name: str
    unit: Optional[str] = None
    vendor_id: Optional[int] = None
    vendor_name: Optional[str] = None
    unit_price: Optional[Decimal] = None
    departments: list[DepartmentBreakdownRow]
    total_adjusted_qty: int
    total_amount: Decimal
    has_missing_vendor: bool = False


class PushToRagicPayload(BaseModel):
    """拋轉到 Ragic：把某週期＋期別＋公司範圍內的彙整列，組成一張「匯總請購單」
    文件推送到 Ragic（Ragic 端表單目前尚未建立，現階段為 stub 串接，
    見 services/cycle_purchase_ragic_push.py）。"""
    cycle_id: int
    period_label: str
    company: str


class PushToRagicResult(BaseModel):
    """拋轉結果。"""
    batch_no: str
    pushed_count: int
    ragic_record_id: Optional[str] = None
    is_stub: bool = True
    message: str
