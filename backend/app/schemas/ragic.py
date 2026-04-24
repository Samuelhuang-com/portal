from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class RagicConnectionCreate(BaseModel):
    tenant_id: str
    display_name: str
    server: str  # www | ap8 | ap12 | ap16 | na3 | eu2 | ap5
    account_name: str
    api_key: str  # 明文，存入前加密
    sheet_path: str
    field_mappings: Dict[str, Any] = {}
    sync_interval: int = 60  # 單位：分鐘


class RagicConnectionUpdate(BaseModel):
    """更新連線設定（api_key 選填；不傳則沿用現有加密值）"""
    display_name: str
    server: str
    account_name: str
    api_key: Optional[str] = None  # 選填：不傳則不更新
    sheet_path: str
    field_mappings: Dict[str, Any] = {}
    sync_interval: int = 60


class RagicConnectionOut(BaseModel):
    id: str
    tenant_id: str
    display_name: str
    server: str
    account_name: str
    sheet_path: str
    field_mappings: Dict[str, Any]
    sync_interval: int
    is_active: bool
    last_synced_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SyncLogOut(BaseModel):
    id: str
    connection_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    records_fetched: Optional[int] = None
    status: str
    error_msg: Optional[str] = None
    triggered_by: str

    class Config:
        from_attributes = True
