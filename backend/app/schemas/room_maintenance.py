"""
Pydantic schemas for 客房保養 module
"""
from typing import Any, List, Optional
from pydantic import BaseModel, Field


# ── Constants ─────────────────────────────────────────────────────────────────

class WorkItemStatus:
    COMPLETED     = "已完成檢視及保養"
    NOT_SCHEDULED = "非本月排程"
    IN_PROGRESS   = "進行中"
    PENDING       = "待排程"


INSPECT_ITEM_OPTIONS = [
    "客房房門", "客房窗", "浴間", "配電盤",
    "客房設備", "客房燈/電源", "浴廁", "空調",
    "傢俱", "地板", "牆面", "天花板",
]

WORK_ITEM_OPTIONS = [
    WorkItemStatus.COMPLETED,
    WorkItemStatus.NOT_SCHEDULED,
    WorkItemStatus.IN_PROGRESS,
    WorkItemStatus.PENDING,
]


# ── Record schemas ────────────────────────────────────────────────────────────

class RoomMaintenanceRecord(BaseModel):
    """單筆客房保養記錄（讀取用）"""
    id: str
    room_no: str = Field(..., description="房號")
    inspect_items: List[str] = Field(default_factory=list, description="檢查項目（多選）")
    dept: str = Field("", description="報修部門 / 負責人")
    work_item: str = Field("", description="工作項目選擇")
    inspect_datetime: str = Field("", description="檢查日期時間")
    created_at: str = Field("", description="建立日期")
    updated_at: str = Field("", description="最後更新日期")
    close_date: str = Field("", description="結案日期")
    subtotal: int = Field(0, description="小計（檢查項目數）")
    incomplete: int = Field(0, description="未完成項目數")


class RoomMaintenanceCreate(BaseModel):
    """新增客房保養記錄"""
    room_no: str = Field(..., min_length=1, description="房號")
    inspect_items: List[str] = Field(default_factory=list)
    dept: str = Field(..., min_length=1)
    work_item: str = Field(..., description="工作項目選擇")
    inspect_datetime: str = Field(..., description="YYYY/MM/DD HH:MM")
    close_date: Optional[str] = None


class RoomMaintenanceUpdate(BaseModel):
    """更新客房保養記錄（全部可選）"""
    room_no: Optional[str] = None
    inspect_items: Optional[List[str]] = None
    dept: Optional[str] = None
    work_item: Optional[str] = None
    inspect_datetime: Optional[str] = None
    close_date: Optional[str] = None


# ── Response wrappers ─────────────────────────────────────────────────────────

class RoomMaintenanceListResponse(BaseModel):
    success: bool = True
    data: List[RoomMaintenanceRecord]
    meta: dict[str, Any] = Field(default_factory=dict)


class RoomMaintenanceSingleResponse(BaseModel):
    success: bool = True
    data: RoomMaintenanceRecord


class RoomMaintenanceStats(BaseModel):
    """統計數字（給 Dashboard KPI 卡使用）"""
    total: int
    completed: int
    not_scheduled: int
    total_incomplete: int
    completion_rate: float = Field(..., description="本月完成率（%）")


class RoomMaintenanceStatsResponse(BaseModel):
    success: bool = True
    data: RoomMaintenanceStats


class OptionsResponse(BaseModel):
    inspect_item_options: List[str]
    work_item_options: List[str]
