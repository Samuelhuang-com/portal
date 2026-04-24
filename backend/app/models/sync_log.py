import uuid
from datetime import datetime
from app.core.time import twnow
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.core.database import Base

class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    connection_id: Mapped[str] = mapped_column(String(36), ForeignKey("ragic_connections.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=twnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    records_fetched: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running | success | error | partial
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(20), default="scheduler")  # scheduler | manual | api

    connection: Mapped["RagicConnection"] = relationship("RagicConnection", back_populates="sync_logs")
