"""
模組自動同步日誌 ORM Model

記錄 _auto_sync() 每次執行時各模組的同步結果，供前端「同步紀錄」頁面查詢。

Loop Engineering 欄位（2026-06-17 新增）：
- retry_count   : 第幾次嘗試（0=首次、1=第一次重試、2=第二次重試）
- parent_log_id : 重試記錄指向原始首次嘗試的 id（首次為 NULL）
- is_anomaly    : 驗證階段偵測到異常（fetched=0 但歷史上持續有資料）
"""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base


class ModuleSyncLog(Base):
    __tablename__ = "module_sync_log"

    id:            Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_name:   Mapped[str]            = mapped_column(String(50),  nullable=False)
    started_at:    Mapped[datetime]       = mapped_column(DateTime,    nullable=False)
    finished_at:   Mapped[datetime | None] = mapped_column(DateTime,  nullable=True)
    duration_sec:  Mapped[float | None]   = mapped_column(Float,       nullable=True)
    status:        Mapped[str]            = mapped_column(String(20),  default="running")  # success|error|partial
    fetched:       Mapped[int]            = mapped_column(Integer,     default=0)
    upserted:      Mapped[int]            = mapped_column(Integer,     default=0)
    errors_count:  Mapped[int]            = mapped_column(Integer,     default=0)
    error_msg:     Mapped[str | None]     = mapped_column(Text,        nullable=True)
    triggered_by:  Mapped[str]            = mapped_column(String(20),  default="scheduler")  # scheduler|manual
    # ── Loop Engineering 欄位 ──────────────────────────────────────────────────
    retry_count:   Mapped[int]            = mapped_column(Integer,     default=0)        # 0=首次
    parent_log_id: Mapped[int | None]     = mapped_column(Integer,     nullable=True)    # 重試指向原始 id
    is_anomaly:    Mapped[bool]           = mapped_column(Boolean,     default=False)    # 驗證異常旗標
