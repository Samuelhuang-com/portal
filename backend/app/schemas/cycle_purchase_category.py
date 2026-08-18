"""週期採購 — 類別主檔 Pydantic Schemas（2026-08-18 新增）"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CategoryBase(BaseModel):
    company: str
    # None ＝ 不限部門（全公司共用，如文具用品），見 models/cycle_purchase_category.py
    department_id: Optional[int] = None
    major_code: str
    major_name: str
    mid_code: str
    mid_name: str
    sub_code: str
    sub_name: Optional[str] = None
    category_name: str
    serial_width: int = 3
    is_active: bool = True
    notes: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    company: Optional[str] = None
    department_id: Optional[int] = None
    major_code: Optional[str] = None
    major_name: Optional[str] = None
    mid_code: Optional[str] = None
    mid_name: Optional[str] = None
    sub_code: Optional[str] = None
    sub_name: Optional[str] = None
    category_name: Optional[str] = None
    serial_width: Optional[int] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class CategoryOut(CategoryBase):
    id: int
    created_at: datetime
    # 以下三個是 service 層附加的顯示欄位，不落地成資料表欄位
    department_name: Optional[str] = None
    code_prefix: str = ""
    # 目前 cycle_purchase_items.category 等於這個 category_name 的啟用中料號筆數。
    # 0 筆代表這個類別在主檔裡有、但沒有任何料號在用（可能是預留、也可能是
    # 類別字串被改過而對不上），畫面上要能一眼看出來。
    item_count: int = 0

    class Config:
        from_attributes = True


class CategoryNextCodeOut(BaseModel):
    """「取下一個料號」回應（見 service.get_next_item_code 說明）"""
    category_id: int
    code_prefix: str
    next_code: str
    used_serials: list[str]
    # 中間有跳號時列出來（如春大直 E03 停車場照明缺 02／03／05），
    # 讓使用者自己決定要補跳號還是接續往下編。
    gap_serials: list[str]
