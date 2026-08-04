"""
OPERA 營運分析 — 匯入批次與錯誤紀錄 ORM Model

資料來源：OPERA 匯出的 TXT 報表（人工上傳，非 Ragic 同步）
規格書：docs/SPEC_opera_analytics.md §5.1 / §5.2

每上傳一個 TXT 建立一筆 OperaImportBatch；同一次上傳（可同時含 Departure 與
History and Forecast 兩檔）共用同一個 session_id。
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow

# ── 常數 ──────────────────────────────────────────────────────────────────────

SOURCE_DEPARTURE = "DEPARTURE"
SOURCE_HISTORY_FORECAST = "HISTORY_FORECAST"

STATUS_PENDING = "PENDING"
STATUS_VALIDATED = "VALIDATED"
STATUS_COMMITTED = "COMMITTED"
STATUS_FAILED = "FAILED"
STATUS_ROLLED_BACK = "ROLLED_BACK"

QUALITY_PASS = "PASS"
QUALITY_PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
QUALITY_FAIL = "FAIL"

SEVERITY_ERROR = "ERROR"
SEVERITY_WARNING = "WARNING"


class OperaImportBatch(Base):
    """匯入批次（規格書 §5.1）"""

    __tablename__ = "opera_import_batch"

    id:          Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id:  Mapped[str]            = mapped_column(String(36), default="", index=True)
    source_type: Mapped[str]            = mapped_column(String(20), default="", index=True)
    property_code: Mapped[str]          = mapped_column(String(20), default="")

    source_file_name: Mapped[str]       = mapped_column(String(255), default="")
    file_sha256:      Mapped[str]       = mapped_column(String(64),  default="", index=True)
    file_size:        Mapped[int]       = mapped_column(Integer,     default=0)
    encoding:         Mapped[str]       = mapped_column(String(20),  default="")

    report_start_date: Mapped[str]      = mapped_column(String(10), default="")   # ISO YYYY-MM-DD
    report_end_date:   Mapped[str]      = mapped_column(String(10), default="")   # ISO YYYY-MM-DD

    row_count_source:   Mapped[int]     = mapped_column(Integer, default=0)
    row_count_inserted: Mapped[int]     = mapped_column(Integer, default=0)
    row_count_updated:  Mapped[int]     = mapped_column(Integer, default=0)
    row_count_skipped:  Mapped[int]     = mapped_column(Integer, default=0)
    row_count_rejected: Mapped[int]     = mapped_column(Integer, default=0)

    status:         Mapped[str]         = mapped_column(String(20), default=STATUS_PENDING, index=True)
    quality_result: Mapped[str]         = mapped_column(String(20), default="")

    footer_json:    Mapped[str | None]  = mapped_column(Text, nullable=True, default=None)
    reconcile_json: Mapped[str | None]  = mapped_column(Text, nullable=True, default=None)

    started_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=twnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    uploaded_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    uploaded_by_name:    Mapped[str]        = mapped_column(String(100), default="")
    program_version:     Mapped[str]        = mapped_column(String(20),  default="")
    error_message:       Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    # ── 輔助 ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _loads(raw: str | None) -> dict:
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def footer(self) -> dict:
        return self._loads(self.footer_json)

    def reconcile(self) -> dict:
        return self._loads(self.reconcile_json)

    def to_dict(self) -> dict:
        started = self.started_at.strftime("%Y/%m/%d %H:%M") if self.started_at else ""
        completed = self.completed_at.strftime("%Y/%m/%d %H:%M") if self.completed_at else ""
        source_label = (
            "Departure All" if self.source_type == SOURCE_DEPARTURE
            else "History and Forecast" if self.source_type == SOURCE_HISTORY_FORECAST
            else self.source_type
        )
        return {
            "id":                 self.id,
            "session_id":         self.session_id,
            "source_type":        self.source_type,
            "source_label":       source_label,
            "property_code":      self.property_code,
            "source_file_name":   self.source_file_name,
            "file_sha256":        self.file_sha256,
            "file_size":          self.file_size,
            "encoding":           self.encoding,
            "report_start_date":  self.report_start_date,
            "report_end_date":    self.report_end_date,
            "row_count_source":   self.row_count_source,
            "row_count_inserted": self.row_count_inserted,
            "row_count_updated":  self.row_count_updated,
            "row_count_skipped":  self.row_count_skipped,
            "row_count_rejected": self.row_count_rejected,
            "status":             self.status,
            "quality_result":     self.quality_result,
            "footer":             self.footer(),
            "reconcile":          self.reconcile(),
            "started_at":         started,
            "completed_at":       completed,
            "uploaded_by_name":   self.uploaded_by_name,
            "program_version":    self.program_version,
            "error_message":      self.error_message or "",
            # 明細 Drawer 用（CLAUDE.md §7）
            "detail": {
                "來源報表":     source_label,
                "檔案名稱":     self.source_file_name,
                "檔案大小":     f"{self.file_size:,} bytes" if self.file_size else "",
                "檔案指紋":     (self.file_sha256[:16] + "…") if self.file_sha256 else "",
                "編碼":         self.encoding,
                "飯店代碼":     self.property_code,
                "資料起日":     self.report_start_date,
                "資料迄日":     self.report_end_date,
                "有效列數":     f"{self.row_count_source:,}",
                "新增":         f"{self.row_count_inserted:,}",
                "更新":         f"{self.row_count_updated:,}",
                "略過":         f"{self.row_count_skipped:,}",
                "拒絕":         f"{self.row_count_rejected:,}",
                "品質結果":     self.quality_result,
                "狀態":         self.status,
                "上傳者":       self.uploaded_by_name,
                "開始時間":     started,
                "完成時間":     completed,
                "程式版本":     self.program_version,
                "錯誤訊息":     self.error_message or "",
            },
        }


class OperaImportError(Base):
    """匯入錯誤／警示明細（規格書 §5.2）

    ⚠️ raw_value 寫入前必須先經過遮罩（住客姓名／會員卡號不得落地）。
    """

    __tablename__ = "opera_import_error"

    id:            Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id:      Mapped[int]  = mapped_column(Integer, index=True, default=0)
    source_row_no: Mapped[int]  = mapped_column(Integer, default=0)
    field_name:    Mapped[str]  = mapped_column(String(50),  default="")
    raw_value:     Mapped[str]  = mapped_column(String(500), default="")
    error_code:    Mapped[str]  = mapped_column(String(30),  default="")
    error_message: Mapped[str]  = mapped_column(String(500), default="")
    severity:      Mapped[str]  = mapped_column(String(10),  default=SEVERITY_ERROR)

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "batch_id":      self.batch_id,
            "source_row_no": self.source_row_no,
            "field_name":    self.field_name,
            "raw_value":     self.raw_value,
            "error_code":    self.error_code,
            "error_message": self.error_message,
            "severity":      self.severity,
        }
