"""週期採購 — 異常稽核紀錄 Pydantic Schemas"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    document_type: str
    document_id: int
    document_no: str
    event_type: str
    description: str
    operator_user_id: Optional[str] = None
    operator_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
