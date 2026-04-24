from pydantic import BaseModel
from typing import Any, Generic, TypeVar, Optional

T = TypeVar("T")

class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None

class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T] = []
    meta: PaginationMeta

class ErrorResponse(BaseModel):
    success: bool = False
    error: dict[str, Any]
