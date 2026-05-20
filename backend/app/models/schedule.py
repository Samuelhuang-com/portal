"""
班表模組 SQLAlchemy ORM Models
包含：departments（部門表）、staff_members（人員表）、shift_types（班別表）、
      schedules（班表主檔）、schedule_details（班表明細）、schedule_import_logs（匯入紀錄）

本模組為純本地 SQLite 資料庫模組，不對接 Ragic。
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date,
    ForeignKey, Text, JSON, func
)
from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────
# 1. 部門表
# ─────────────────────────────────────────────────────────────
class Department(Base):
    __tablename__ = "schedule_departments"

    id          = Column(String(36), primary_key=True, default=_uuid, comment="主鍵 UUID")
    name        = Column(String(100), nullable=False, unique=True, default="", comment="部門名稱")
    remark      = Column(String(200), nullable=False, default="", comment="備註")
    sort_order  = Column(Integer, nullable=False, default=0, comment="排序")
    is_active   = Column(Boolean, nullable=False, default=True, comment="是否啟用")
    is_deleted  = Column(Boolean, nullable=False, default=False, comment="軟刪除")
    created_at  = Column(DateTime, nullable=False, server_default=func.now(), comment="建立時間")
    updated_at  = Column(DateTime, nullable=False, server_default=func.now(),
                         onupdate=func.now(), comment="更新時間")

    def __repr__(self) -> str:
        return f"<Department name={self.name}>"


# ─────────────────────────────────────────────────────────────
# 2. 人員表
# ─────────────────────────────────────────────────────────────
class StaffMember(Base):
    __tablename__ = "schedule_staff_members"

    id              = Column(String(36), primary_key=True, default=_uuid, comment="主鍵 UUID")
    staff_code      = Column(String(50),  nullable=False, default="", comment="人員代碼（可空）")
    name            = Column(String(100), nullable=False, default="", comment="姓名（解析後）")
    source_name     = Column(String(150), nullable=False, default="", comment="Excel 原始姓名")
    department_id   = Column(String(36),  ForeignKey("schedule_departments.id"), nullable=True,
                             comment="部門 FK")
    department_name = Column(String(100), nullable=False, default="", comment="部門名稱快照")
    employment_type = Column(String(20),  nullable=False, default="正職",
                             comment="正職 / PT / 支援人員")
    remark          = Column(String(200), nullable=False, default="", comment="備註（如福群）")
    is_active       = Column(Boolean,     nullable=False, default=True,  comment="是否啟用")
    is_deleted      = Column(Boolean,     nullable=False, default=False, comment="軟刪除")
    created_at      = Column(DateTime,    nullable=False, server_default=func.now(), comment="建立時間")
    updated_at      = Column(DateTime,    nullable=False, server_default=func.now(),
                             onupdate=func.now(), comment="更新時間")

    def __repr__(self) -> str:
        return f"<StaffMember name={self.name} type={self.employment_type}>"


# ─────────────────────────────────────────────────────────────
# 3. 班別表
# ─────────────────────────────────────────────────────────────
class ShiftType(Base):
    __tablename__ = "schedule_shift_types"

    id           = Column(String(36), primary_key=True, default=_uuid, comment="主鍵 UUID")
    code         = Column(String(20),  nullable=False, unique=True, default="", comment="班別代碼，如 Y、N1")
    name         = Column(String(100), nullable=False, default="", comment="班別名稱")
    start_time   = Column(String(5),   nullable=False, default="",  comment="上班時間 HH:MM")
    end_time     = Column(String(5),   nullable=False, default="",  comment="下班時間 HH:MM")
    work_minutes = Column(Integer,     nullable=False, default=480, comment="預設工時分鐘（預設 8hr）")
    is_overnight = Column(Boolean,     nullable=False, default=False, comment="是否跨日")
    color        = Column(String(20),  nullable=False, default="#6b7280", comment="前端顯示顏色 hex")
    is_active    = Column(Boolean,     nullable=False, default=True,  comment="是否啟用")
    is_deleted   = Column(Boolean,     nullable=False, default=False, comment="軟刪除")
    created_at   = Column(DateTime,    nullable=False, server_default=func.now(), comment="建立時間")
    updated_at   = Column(DateTime,    nullable=False, server_default=func.now(),
                          onupdate=func.now(), comment="更新時間")

    def __repr__(self) -> str:
        return f"<ShiftType code={self.code} {self.start_time}-{self.end_time}>"


# ─────────────────────────────────────────────────────────────
# 4. 班表主檔
# ─────────────────────────────────────────────────────────────
class Schedule(Base):
    __tablename__ = "schedules"

    id               = Column(String(36), primary_key=True, default=_uuid, comment="主鍵 UUID")
    schedule_year    = Column(Integer,     nullable=False, default=0,  comment="年（西元）")
    schedule_month   = Column(Integer,     nullable=False, default=0,  comment="月")
    title            = Column(String(200), nullable=False, default="", comment="班表標題")
    source_file_name = Column(String(300), nullable=False, default="", comment="來源檔名")
    import_batch_id  = Column(String(36),  nullable=False, default=_uuid, comment="匯入批次 UUID")
    # raw_summary：保留 Excel 統計欄位（應出勤/實出勤/加班/請假）
    # 格式：{"陳志明": {"應出勤": 22, "實出勤": 21, "超時加班": 2, "請假天數": 1}}
    raw_summary      = Column(JSON,        nullable=True,  comment="Excel 原始統計欄位 JSON")
    # status: draft / imported / confirmed
    status           = Column(String(20),  nullable=False, default="imported", comment="班表狀態")
    is_deleted       = Column(Boolean,     nullable=False, default=False, comment="軟刪除")
    created_at       = Column(DateTime,    nullable=False, server_default=func.now(), comment="建立時間")
    updated_at       = Column(DateTime,    nullable=False, server_default=func.now(),
                              onupdate=func.now(), comment="更新時間")

    def __repr__(self) -> str:
        return f"<Schedule {self.schedule_year}/{self.schedule_month:02d} status={self.status}>"


# ─────────────────────────────────────────────────────────────
# 5. 班表明細
# ─────────────────────────────────────────────────────────────
class ScheduleDetail(Base):
    __tablename__ = "schedule_details"

    id            = Column(String(36), primary_key=True, default=_uuid, comment="主鍵 UUID")
    schedule_id   = Column(String(36), ForeignKey("schedules.id"), nullable=False,
                           comment="班表主檔 FK")
    work_date     = Column(Date,       nullable=False, comment="日期")
    staff_id      = Column(String(36), ForeignKey("schedule_staff_members.id"), nullable=True,
                           comment="人員 FK（nullable，允許先以 staff_name 快照保存）")
    staff_name    = Column(String(150), nullable=False, default="", comment="人員姓名快照")
    shift_code    = Column(String(20),  nullable=False, default="", comment="班別代碼")
    shift_type_id = Column(String(36),  ForeignKey("schedule_shift_types.id"), nullable=True,
                           comment="班別 FK（nullable，未知班別時為 null）")
    start_time    = Column(String(5),   nullable=False, default="", comment="實際上班時間 HH:MM")
    end_time      = Column(String(5),   nullable=False, default="", comment="實際下班時間 HH:MM")
    work_minutes  = Column(Integer,     nullable=False, default=0,  comment="工時分鐘")
    raw_value     = Column(String(50),  nullable=False, default="", comment="Excel 原始值")
    remark        = Column(String(300), nullable=False, default="", comment="備註")
    is_deleted    = Column(Boolean,     nullable=False, default=False, comment="軟刪除")
    created_at    = Column(DateTime,    nullable=False, server_default=func.now(), comment="建立時間")
    updated_at    = Column(DateTime,    nullable=False, server_default=func.now(),
                           onupdate=func.now(), comment="更新時間")

    def __repr__(self) -> str:
        return (
            f"<ScheduleDetail {self.work_date} staff={self.staff_name} "
            f"shift={self.shift_code}>"
        )


# ─────────────────────────────────────────────────────────────
# 6. 匯入紀錄
# ─────────────────────────────────────────────────────────────
class ScheduleImportLog(Base):
    __tablename__ = "schedule_import_logs"

    id                  = Column(String(36), primary_key=True, default=_uuid, comment="主鍵 UUID")
    import_batch_id     = Column(String(36), nullable=False, default="", comment="匯入批次 UUID")
    file_name           = Column(String(300), nullable=False, default="", comment="檔名")
    sheet_name          = Column(String(100), nullable=False, default="", comment="Sheet 名稱")
    schedule_year       = Column(Integer,     nullable=False, default=0,  comment="班表年")
    schedule_month      = Column(Integer,     nullable=False, default=0,  comment="班表月")
    total_rows          = Column(Integer,     nullable=False, default=0,  comment="掃描列數")
    total_details       = Column(Integer,     nullable=False, default=0,  comment="明細總筆數")
    success_count       = Column(Integer,     nullable=False, default=0,  comment="成功筆數")
    warning_count       = Column(Integer,     nullable=False, default=0,  comment="警告筆數")
    error_count         = Column(Integer,     nullable=False, default=0,  comment="錯誤筆數")
    # unknown_shift_codes: ["X1", "Z"]
    unknown_shift_codes = Column(JSON,        nullable=True,  comment="未辨識班別代碼清單")
    # new_staff_names: ["陳志明", "李宗銘"]
    new_staff_names     = Column(JSON,        nullable=True,  comment="新增人員清單")
    message             = Column(Text,        nullable=False, default="", comment="匯入訊息")
    created_at          = Column(DateTime,    nullable=False, server_default=func.now(),
                                 comment="建立時間")

    def __repr__(self) -> str:
        return (
            f"<ScheduleImportLog {self.schedule_year}/{self.schedule_month:02d} "
            f"batch={self.import_batch_id[:8]}>"
        )
