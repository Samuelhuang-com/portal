"""
開發統計（2026-11-02）：CHANGELOG 條目 → 資料庫。開始／結束時間可於頁面編輯。
"""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Index, UniqueConstraint

from app.core.database import Base


class DevLogEntry(Base):
    __tablename__ = "dev_log_entries"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    source_key   = Column(String(300), nullable=False, unique=True, comment="日期|類型|標題|同名序號，匯入去重用")
    entry_date   = Column(Date,        nullable=False, comment="CHANGELOG 版本日期")
    category     = Column(String(30),  nullable=False, default="", comment="Added／Changed／Fixed／Known")
    title        = Column(String(300), nullable=False, default="")
    module       = Column(String(120), nullable=False, default="", comment="由標題推得的模組名稱")
    route        = Column(String(200), nullable=True, comment="模組路由（CHANGELOG「> 路由：」）；空＝未知")
    start_at     = Column(DateTime,    nullable=True, comment="開始時間（可手動編輯）")
    end_at       = Column(DateTime,    nullable=True, comment="結束時間（可手動編輯）")
    time_note    = Column(Text,        nullable=True, comment="時間來源／未知原因")
    updated_by   = Column(String(120), nullable=True)
    updated_at   = Column(DateTime,    nullable=True)

    __table_args__ = (
        Index("ix_dev_log_entry_date", "entry_date"),
        Index("ix_dev_log_module", "module"),
    )
