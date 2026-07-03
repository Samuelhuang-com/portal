"""
影音教學 Pydantic Schemas（模組主檔 + 單集影片）
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# ── 教學模組主檔 ──────────────────────────────────────────────────────────────

class TutorialVideoModuleOut(BaseModel):
    id: str
    category: str
    module_name: str
    module_route: str
    sort_order: int
    video_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TutorialVideoModuleCreate(BaseModel):
    category: str
    module_name: str
    module_route: str = ""


class TutorialVideoModuleUpdate(BaseModel):
    category: Optional[str] = None
    module_name: Optional[str] = None
    module_route: Optional[str] = None


class TutorialVideoModuleReorderRequest(BaseModel):
    category: str
    ordered_ids: List[str]


# ── 單集影片 ──────────────────────────────────────────────────────────────────

class TutorialVideoOut(BaseModel):
    id: str
    module_id: str
    episode: str
    title: str
    description: str
    video_orig_name: str
    video_size_bytes: int
    script_orig_name: str
    sort_order: int
    uploaded_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TutorialVideoListResponse(BaseModel):
    items: List[TutorialVideoOut]
    total: int


class TutorialVideoUpdate(BaseModel):
    module_id: Optional[str] = None
    episode: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


class TutorialVideoReorderRequest(BaseModel):
    ordered_ids: List[str]
