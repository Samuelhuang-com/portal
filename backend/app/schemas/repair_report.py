"""
報修未完成報表 — Pydantic Schemas
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, field_validator


# ── 統一案件格式（前端顯示用）────────────────────────────────────────────────

class UnifiedCase(BaseModel):
    source:           str           # hotel / mall
    source_label:     str           # 飯店 / 商場
    ragic_id:         str
    case_no:          str
    occurred_at:      Optional[str]
    floor:            str
    repair_type:      str
    title:            str
    status:           str
    responsible_unit: str           # 工務處理人員（responsible_unit 欄位）
    pending_days:     Optional[int]
    is_overdue:       bool
    synced_at:        Optional[str]
    finance_note:     str
    ragic_url:        str


class KpiData(BaseModel):
    total_unfinished:   int
    hotel_unfinished:   int
    mall_unfinished:    int
    overdue_count:      int
    avg_pending_days:   float
    max_pending_days:   int
    new_this_month:     int
    new_today:          int


class FilterOptions(BaseModel):
    statuses:     list[str]
    repair_types: list[str]


class UnfinishedCasesResponse(BaseModel):
    items:          list[UnifiedCase]
    total:          int
    kpi:            KpiData
    filter_options: FilterOptions


# ── 收件人 ────────────────────────────────────────────────────────────────────

class RecipientBase(BaseModel):
    name:       str
    email:      EmailStr
    department: str = ""
    role:       str = ""
    is_active:  bool = True


class RecipientCreate(RecipientBase):
    pass


class RecipientUpdate(BaseModel):
    name:       Optional[str]  = None
    email:      Optional[EmailStr] = None
    department: Optional[str]  = None
    role:       Optional[str]  = None
    is_active:  Optional[bool] = None


class RecipientOut(RecipientBase):
    id:         int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_by: str
    updated_by: str

    class Config:
        from_attributes = True


# ── 排程設定 ──────────────────────────────────────────────────────────────────

class ScheduleSettingsBase(BaseModel):
    schedule_name:            str  = "每日報修未完成報表"
    is_enabled:               bool = False
    send_time:                str  = "08:30"   # HH:MM
    report_year_month_mode:   str  = "current_month"
    include_hotel:            bool = True
    include_mall:             bool = True
    include_excel_attachment: bool = True
    email_subject_template:   str  = "【報修未完成報表】{year}年{month}月｜未完成 {total} 件｜飯店 {hotel_count} 件｜商場 {mall_count} 件"
    email_body_template:      str  = ""

    @field_validator("send_time")
    @classmethod
    def validate_send_time(cls, v: str) -> str:
        try:
            hour, minute = v.split(":")
            assert 0 <= int(hour) <= 23
            assert 0 <= int(minute) <= 59
        except Exception:
            raise ValueError("send_time 格式必須為 HH:MM（例如 08:30）")
        return v


class ScheduleSettingsUpdate(ScheduleSettingsBase):
    pass


class ScheduleSettingsOut(ScheduleSettingsBase):
    id:         int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    updated_by: str

    class Config:
        from_attributes = True


# ── 手動寄送請求 ──────────────────────────────────────────────────────────────

class ManualSendRequest(BaseModel):
    year:                    int
    month:                   int
    include_hotel:           bool = True
    include_mall:            bool = True
    include_excel_attachment: bool = True
    recipient_ids:           list[int] = []   # 空 = 全部 active 收件人


class SendResult(BaseModel):
    recipient_email: str
    recipient_name:  str
    success:         bool
    error_message:   Optional[str]


class ManualSendResponse(BaseModel):
    sent_count:   int
    failed_count: int
    results:      list[SendResult]


# ── 寄送紀錄 ──────────────────────────────────────────────────────────────────

class MailLogOut(BaseModel):
    id:                    int
    send_date:             date
    send_time:             str
    report_year:           int
    report_month:          int
    recipient_email:       str
    recipient_name:        str
    subject:               str
    status:                str
    error_message:         Optional[str]
    hotel_unfinished_count:  Optional[int]
    mall_unfinished_count:   Optional[int]
    total_unfinished_count:  Optional[int]
    attachment_filename:   Optional[str]
    created_at:            Optional[datetime]

    class Config:
        from_attributes = True


class MailLogListResponse(BaseModel):
    items: list[MailLogOut]
    total: int


# ── 測試寄送 ──────────────────────────────────────────────────────────────────

class TestSendResponse(BaseModel):
    success:       bool
    message:       str
