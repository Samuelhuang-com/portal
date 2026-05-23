"""
報修未完成報表 — ORM Models

資料表：
  repair_report_recipients       收件人管理
  repair_report_schedule_settings 排程設定
  repair_report_mail_logs        每日寄送紀錄（每位收件人一筆）
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text

from app.core.database import Base


class RepairReportRecipient(Base):
    """收件人管理"""
    __tablename__ = "repair_report_recipients"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(100), nullable=False)
    email       = Column(String(200), nullable=False, unique=True)
    department  = Column(String(100), default="")
    role        = Column(String(100), default="")
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, nullable=True)
    created_by  = Column(String(100), default="")
    updated_by  = Column(String(100), default="")


class RepairReportScheduleSettings(Base):
    """排程設定（只維護一筆，id=1）"""
    __tablename__ = "repair_report_schedule_settings"

    id                      = Column(Integer, primary_key=True, autoincrement=True)
    schedule_name           = Column(String(200), nullable=False, default="每日報修未完成報表")
    is_enabled              = Column(Boolean, default=False)          # 預設關閉，避免上線即寄信
    send_time               = Column(String(10), default="08:30")    # HH:MM
    report_year_month_mode  = Column(String(50), default="current_month")  # current_month / previous_month
    include_hotel           = Column(Boolean, default=True)
    include_mall            = Column(Boolean, default=True)
    include_excel_attachment = Column(Boolean, default=True)
    email_subject_template  = Column(
        String(500),
        default="【報修未完成報表】{year}年{month}月｜未完成 {total} 件｜飯店 {hotel_count} 件｜商場 {mall_count} 件",
    )
    email_body_template     = Column(Text, default="")
    created_at              = Column(DateTime, default=datetime.utcnow)
    updated_at              = Column(DateTime, nullable=True)
    updated_by              = Column(String(100), default="")


class RepairReportMailLog(Base):
    """每日寄送紀錄（每位收件人各一筆）"""
    __tablename__ = "repair_report_mail_logs"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    send_date             = Column(Date, nullable=False)
    send_time             = Column(String(10), nullable=False)   # HH:MM
    report_year           = Column(Integer, nullable=False)
    report_month          = Column(Integer, nullable=False)
    recipient_email       = Column(String(200), nullable=False)
    recipient_name        = Column(String(100), default="")
    subject               = Column(String(500), default="")
    status                = Column(String(20), nullable=False)   # success / failed / skipped
    error_message         = Column(Text, nullable=True)
    hotel_unfinished_count   = Column(Integer, nullable=True)
    mall_unfinished_count    = Column(Integer, nullable=True)
    total_unfinished_count   = Column(Integer, nullable=True)
    attachment_filename   = Column(String(200), nullable=True)
    send_source           = Column(String(20), nullable=True, default="scheduled")  # 'scheduled' | 'manual'
    created_at            = Column(DateTime, default=datetime.utcnow)
