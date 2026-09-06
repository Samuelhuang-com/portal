"""
Tenant — 據點主檔（人員管理「所屬據點」的來源）

⚠️ 2026-09-01 起，本表是「系統設定 → 公司/部門管理」`Company` 的**單向鏡像**。
   使用者裁示：人員管理新增使用者時的「所屬據點」下拉，必須等於公司/部門管理
   維護的公司名稱清單。

       系統設定 → 公司/部門管理（reference_data.Company）← 唯一真實來源
           └─ services/tenant_company_sync.py ──▶ 本表 tenants

   沿用 CLAUDE.md §9 的鏡像樣板（與 cycle_purchase_vendor_sync／
   cycle_purchase_department_sync 同一套規則）：
     - **不動** `id`（UUID PK）。`users.tenant_id`／`user_roles.tenant_id`／
       `ragic_connections.tenant_id` 三處外鍵都綁著它，改型別風險過高。
       只加 `source_company_id` 當跨主檔對照鍵。
     - `source_company_id` 為 NULL ＝ 本地自建的舊據點，**同步不覆蓋也不刪除**
       （一次性停用／改掛請跑 `backend/scripts/migrate_tenants_to_companies.py`）。
     - 來源端刪公司時不連帶刪／停用鏡像，只回報 orphans 計數。
"""
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.core.time import twnow
import uuid
from app.core.database import Base

def _now():
    return twnow()

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # 跨主檔對照鍵：對應 reference_data.Company.id（存成字串，比照
    # cycle_purchase 兩支鏡像同步的 source_vendor_id／source_department_id 慣例）。
    # NULL ＝ 本地自建，同步不碰。
    source_company_id: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now, nullable=False)

    users: Mapped[list["User"]] = relationship("User", back_populates="tenant")
    user_roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="tenant")
    ragic_connections: Mapped[list["RagicConnection"]] = relationship("RagicConnection", back_populates="tenant")