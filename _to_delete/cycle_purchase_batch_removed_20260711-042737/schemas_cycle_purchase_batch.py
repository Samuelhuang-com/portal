"""週期採購 — 批次 Pydantic Schemas"""
from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class BatchCreate(BaseModel):
    cycle_id: int
    batch_name: str
    open_date: date
    close_date: date


class BatchUpdate(BaseModel):
    batch_name: Optional[str] = None
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    status: Optional[str] = None


class BatchOut(BaseModel):
    id: int
    batch_no: str
    cycle_id: int
    cycle_name: Optional[str] = None
    batch_name: str
    open_date: date
    close_date: date
    status: str
    requests_generated: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
