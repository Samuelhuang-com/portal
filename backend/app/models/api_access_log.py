"""
API 存取日誌模型
記錄每次通過 /api/v1/ 的 HTTP 請求（排除 auth、docs、靜態資源）。
與 audit_logs（login/logout）分開，各司其職。
"""
from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import uuid
from app.core.database import Base


class ApiAccessLog(Base):
    __tablename__ = "api_access_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # ── 使用者資訊（從 JWT 解出，未登入為 NULL）──────────────────────────────
    user_id: Mapped[str | None]    = mapped_column(String(36),  nullable=True)
    user_email: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── 請求資訊 ─────────────────────────────────────────────────────────────
    module: Mapped[str]  = mapped_column(String(80),  nullable=False)  # 從 path 解析
    method: Mapped[str]  = mapped_column(String(10),  nullable=False)  # GET/POST/…
    path:   Mapped[str]  = mapped_column(String(250), nullable=False)  # 完整 endpoint

    # ── 回應資訊 ─────────────────────────────────────────────────────────────
    status_code:  Mapped[int]  = mapped_column(Integer, nullable=False)
    response_ms:  Mapped[int]  = mapped_column(Integer, nullable=False)  # 毫秒

    # ── 網路資訊 ─────────────────────────────────────────────────────────────
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max 45

    # ── 時間戳（台灣時間，由 middleware 填入）────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
