"""
公告系統 Pydantic Schemas
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class MemoFileOut(BaseModel):
    id: str
    orig_name: str
    content_type: str
    size_bytes: int
    uploaded_by: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class MemoListItem(BaseModel):
    id: str
    title: str
    preview: str          # body 前 160 字（純文字）
    visibility: str
    author: str
    doc_no: str
    recipient: str
    source: str
    source_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class MemoListResponse(BaseModel):
    items: List[MemoListItem]
    total: int
    page: int
    per_page: int


class MemoDetail(BaseModel):
    id: str
    title: str
    body: str
    visibility: str
    author: str
    author_id: str
    doc_no: str
    recipient: str
    source: str
    source_id: str
    created_at: datetime
    updated_at: datetime
    attachments: List[MemoFileOut] = []

    class Config:
        from_attributes = True


class MemoCreate(BaseModel):
    title: str
    body: str = ""
    visibility: str = "org"      # org | restricted
    doc_no: str = ""
    recipient: str = ""


class MemoUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    visibility: Optional[str] = None
    doc_no: Optional[str] = None
    recipient: Optional[str] = None
