import uuid
from datetime import datetime
from app.core.time import twnow
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.core.database import Base

class DataSnapshot(Base):
    __tablename__ = "data_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    connection_id: Mapped[str] = mapped_column(String(36), ForeignKey("ragic_connections.id"), nullable=False)
    sync_log_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sync_logs.id"), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=twnow)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)

    connection: Mapped["RagicConnection"] = relationship("RagicConnection", back_populates="snapshots")
