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
    # 2026-08-21 新增：這個料號在這家公司這個部門要記到哪個會計科目。
    # 掛在 mapping 而不是 item，因為《設料號明細表》的會科本來就是按部門欄位填的，
    # 且確實有跨部門不同科目的案例（E0204002 軌道燈：工程部 621601／營業部 1142）。
    account_code_id: Optional[int] = None
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
    account_code_id: Optional[int] = None
    is_confirmed: Optional[bool] = None
    notes: Optional[str] = None


class ItemMappingOut(ItemMappingBase):
    id: int
    item_id: int
    department_name: Optional[str] = None
    vendor_name: Optional[str] = None
    # 2026-08-21 新增：「代碼 名稱」組合字串，供列表直接顯示（與請購明細
    # account_code_label 的格式一致）。
    account_code_label: Optional[str] = None
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
    # 2026-08-17 新增：這個料號目前掛在哪幾組「公司／部門」（衍生自
    # cycle_purchase_item_mappings，不落地成資料表欄位）。絕大多數料號只有
    # 一組；僅少數幾筆兩公司統購共用料號（如永豐餘衛生紙）會有兩組。
    # 目的：料號主檔列表原本要點進「料號對照」才看得到公司/部門，容易讓人
    # 誤以為同名品類可以跨公司套用（已連續發生兩次週期設定選錯品類的事故）。
    company_departments: List[str] = []
    # 2026-08-21 新增：這個料號目前設了哪些會計科目（衍生自
    # cycle_purchase_item_mappings.account_code_id，格式如 "621601 修繕費-維修"）。
    # 科目是逐筆對照設定的，列表看得到才知道哪些料號還沒設——請購明細的科目
    # 是從對照表自動帶入的，漏設等於該筆請購沒有科目可分攤。
    account_code_labels: List[str] = []

    class Config:
        from_attributes = True


class ItemDetail(ItemOut):
    mappings: List[ItemMappingOut] = []


class ItemListResponse(BaseModel):
    items: List[ItemOut]
    total: int
    page: int
    per_page: int
