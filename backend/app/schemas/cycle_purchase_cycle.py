"""週期採購 — 週期設定 Pydantic Schemas"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CycleBase(BaseModel):
    cycle_code: str
    cycle_name: str
    frequency: str  # monthly | biweekly | bimonthly | custom
    open_rule: Optional[str] = None
    close_rule: Optional[str] = None
    applicable_categories: Optional[str] = None
    applicable_scope: Optional[str] = None
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
    auto_generate: Optional[bool] = None
    reminder_rule: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class CycleOut(CycleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
