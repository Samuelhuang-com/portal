import uuid
from datetime import datetime
from app.core.time import twnow
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.core.database import Base

class RagicConnection(Base):
    __tablename__ = "ragic_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    server: Mapped[str] = mapped_column(String(20), nullable=False)  # www | ap8 | na3 | eu2 | ap5
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    sheet_path: Mapped[str] = mapped_column(String(200), nullable=False)
    field_mappings: Mapped[dict] = mapped_column(JSON, default=dict)
    sync_interval: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=twnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=twnow, onupdate=twnow)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="ragic_connections")
    sync_logs: Mapped[list["SyncLog"]] = relationship("SyncLog", back_populates="connection")
    snapshots: Mapped[list["DataSnapshot"]] = relationship("DataSnapshot", back_populates="connection")
