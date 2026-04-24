"""
Pydantic schemas for 倉庫庫存 module
"""
from typing import Any, List, Optional
from pydantic import BaseModel, Field


# ── Record schemas ────────────────────────────────────────────────────────────

class InventoryRecord(BaseModel):
    """單筆倉庫庫存記錄（讀取用）"""
    id: str
    inventory_no: str   = Field("", description="庫存編號")
    warehouse_code: str = Field("", description="倉庫代碼")
    warehouse_name: str = Field("", description="倉庫名稱")
    product_no: str     = Field("", description="商品編號")
    product_name: str   = Field("", description="商品名稱")
    quantity: int       = Field(0,  description="數量")
    category: str       = Field("", description="種類")
    spec: str           = Field("", description="規格")
    created_at: str     = Field("", description="建立日期")
    updated_at: str     = Field("", description="最後更新日期")


# ── Response wrappers ─────────────────────────────────────────────────────────

class InventoryListResponse(BaseModel):
    success: bool = True
    data: List[InventoryRecord]
    meta: dict[str, Any] = Field(default_factory=dict)


class InventorySingleResponse(BaseModel):
    success: bool = True
    data: InventoryRecord


class InventoryStats(BaseModel):
    """統計數字"""
    total_skus: int           = Field(0,   description="總 SKU 數")
    total_quantity: int       = Field(0,   description="總庫存量")
    zero_stock_count: int     = Field(0,   description="零庫存 SKU 數")
    warehouse_count: int      = Field(0,   description="倉庫數")


class InventoryStatsResponse(BaseModel):
    success: bool = True
    data: InventoryStats


class InventoryFilters(BaseModel):
    """查詢篩選條件"""
    warehouse_code: Optional[str] = None
    product_no: Optional[str]     = None
    product_name: Optional[str]   = None
    page: int     = Field(1,   ge=1)
    per_page: int = Field(50,  ge=1, le=200)
