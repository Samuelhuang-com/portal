"""週期採購 — 供應商主檔 Pydantic Schemas"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class VendorBase(BaseModel):
    vendor_code: str
    vendor_name: str
    tax_id: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    vendor_code: Optional[str] = None
    vendor_name: Optional[str] = None
    tax_id: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class VendorLinkPayload(BaseModel):
    """把一筆週採供應商「對照」到合約模組的廠商主檔（2026-09-20 新增）。

    ⚠️ 刻意跟 VendorUpdate 分開：`update_vendor()` 明文規定
    「source_vendor_id / synced_at 只由同步服務維護，任何情況都不吃前端傳入值」，
    那條規則要保留（避免一般編輯不小心動到同步鍵）。對照是一個獨立、明確的
    動作，所以給它自己的端點與 payload。

    source_vendor_id = None 代表「解除對照」，解除後這筆就回到本地自建、
    欄位重新可編。
    """
    source_vendor_id: Optional[str] = None


class VendorMergePayload(BaseModel):
    """把這一筆供應商併入另一筆（2026-09-20 新增）。

    `dry_run=True` 只試算會搬動什麼、不寫入，給畫面在按下合併前先確認用。
    """
    target_vendor_id: int
    dry_run: bool = False


class VendorMergeResult(BaseModel):
    source_id: int
    source_name: str
    target_id: int
    target_name: str
    moved: dict[str, int]      # {"料號對照": 90, "彙整列": 3, …}
    total_moved: int
    applied: bool              # False ＝ 只是試算


class VendorOut(VendorBase):
    id: int
    # 2026-08-10：鏡像自合約模組 vendors 的來源鍵（VND-NNNN）。
    # 非空 = 受同步管控，前端須把 vendor_code/vendor_name/tax_id/contact_* 設唯讀；
    # 為 None = 週採本地自建，全部欄位可編。
    source_vendor_id: Optional[str] = None
    # 2026-09-20 新增（衍生欄位，非資料表欄位）：對照到的合約廠商名稱。
    # 合約主檔在 portal.db、這張表在 cycle-purchase.db，跨庫查不到，
    # 由 router 用 portal_db 補上（比照 _attach_owner_names 的做法）。
    source_vendor_name: Optional[str] = None
    synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
