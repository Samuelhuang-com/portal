"""週期採購 — 週期設定 Pydantic Schemas

2026-08-09（部門範圍 + 品類接線，見 models/cycle_purchase_cycle.py 開頭說明）：
新增 applicable_department_ids；另外加上 OrphanRequestOut / OrphanPreviewResult，
供「儲存週期設定時，先預覽會被刪掉哪幾張孤兒空白請購單」的兩段式確認流程用。
"""
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel


class CycleBase(BaseModel):
    cycle_code: str
    cycle_name: str
    frequency: str  # monthly | biweekly | bimonthly | custom
    open_rule: Optional[str] = None
    close_rule: Optional[str] = None
    applicable_categories: Optional[str] = None
    applicable_scope: Optional[str] = None
    applicable_department_ids: Optional[str] = None
    excluded_item_ids: Optional[str] = None
    auto_generate: bool = False
    reminder_rule: Optional[str] = None
    status: str = "active"
    notes: Optional[str] = None


class CycleCreate(CycleBase):
    pass


class CycleUpdate(BaseModel):
    cycle_code: Optional[str] = None
    cycle_name: Optional[str] = None
    frequency: Optional[str] = None
    open_rule: Optional[str] = None
    close_rule: Optional[str] = None
    applicable_categories: Optional[str] = None
    applicable_scope: Optional[str] = None
    applicable_department_ids: Optional[str] = None
    excluded_item_ids: Optional[str] = None
    auto_generate: Optional[bool] = None
    reminder_rule: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class CycleOut(CycleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # 2026-08-09：PUT /cycles/{id}?delete_orphans=true 時，由 router 掛上的衍生欄位，
    # 供前端提示「順便刪掉了幾張孤兒空白請購單」。不落地成資料表欄位。
    deleted_orphan_count: Optional[int] = None

    class Config:
        from_attributes = True


# ── 2026-08-09：孤兒空白請購單預覽（儲存週期設定前的確認框用）────────────────
# 判準三個條件全部成立才算「孤兒空白單」，缺一不可：
#   ① 明細 0 筆　② is_closed == False（已關閉＝已定案，不碰）
#   ③ is_summarized == False（已進彙整，不碰）

class OrphanRequestOut(BaseModel):
    """一張會因為週期範圍縮小而被刪掉的空白請購單。"""
    id: int
    request_no: str
    period_label: str
    company: str
    department_id: int
    department_name: Optional[str] = None


class OrphanPreviewResult(BaseModel):
    """POST /cycles/{id}/preview-orphan-requests 的回傳。"""
    orphans: List[OrphanRequestOut] = []
    protected_count: int = 0  # 部門雖然不再適用，但因為有明細／已關閉／已彙整而保留不刪的張數


class CycleOptionsOut(BaseModel):
    """週期設定表單的下拉選項來源（一律取自主檔 distinct 值，不讓使用者手打）。"""
    companies: List[str] = []
    categories: List[str] = []
    # 2026-08-17 新增：品類 → 部門名稱清單，供前端在「適用品類」下拉選項標籤
    # 附加部門名稱（如「空調備品-濾網（工務部）」），避免同公司底下不同部門
    # 的品類混在一起難以分辨。見 cycle_purchase_service.get_cycle_options() docstring。
    category_departments: Dict[str, List[str]] = {}


class ExcludeItemCandidateOut(BaseModel):
    """「排除料號」下拉選項：依目前表單上的適用公司＋適用品類現算，不是固定清單。"""
    item_id: int
    item_code: str
    item_name: str
    category: Optional[str] = None
    companies: List[str] = []  # 這個料號目前掛在哪幾家公司底下（對照表 distinct company）
