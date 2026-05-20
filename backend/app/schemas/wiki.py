"""
知識庫 Pydantic Schemas
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class WikiArticleBase(BaseModel):
    title: str
    body: str
    category: str = "sop"   # sop | dev
    tags: List[str] = []
    summary: str = ""
    is_published: bool = True


class WikiArticleCreate(WikiArticleBase):
    slug: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v not in ("sop", "dev"):
            raise ValueError("category 必須為 sop 或 dev")
        return v


class WikiArticleUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    summary: Optional[str] = None
    is_published: Optional[bool] = None
    slug: Optional[str] = None


class WikiArticleOut(BaseModel):
    id: str
    title: str
    slug: str
    body: str
    summary: str
    category: str
    tags: List[str]
    author: str
    author_id: str
    is_published: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v or []

    model_config = {"from_attributes": True}


class WikiListResponse(BaseModel):
    items: List[WikiArticleOut]
    total: int
    page: int
    per_page: int


# ── AI 問答 ────────────────────────────────────────────────────────────────────

class WikiAskRequest(BaseModel):
    question: str
    category: str = "all"   # all | sop | dev


class WikiAskResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    answer: str
    sources: List[WikiArticleOut]
    model_used: Optional[str] = None
