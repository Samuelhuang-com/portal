"""
金旭 PMS 分析 — 匯入批次與錯誤紀錄 ORM Model

資料來源：金旭 PMS 匯出的 xlsx 報表（人工上傳，非 Ragic 同步）
規格書：docs/SPEC_jinxu_analytics.md §7.1 / §7.2

每上傳一個 xlsx 建立一筆 JinxuImportBatch；同一次上傳（可同時含 FCR02 與
訂房狀況表兩檔）共用同一個 session_id。
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow

# ── 來源類型（規格書 §2.2）────────────────────────────────────────────────────

SOURCE_FCR02_LEDGER = "FCR02_LEDGER"      # 客帳帳目明細表（交易分錄層）
SOURCE_RESV_DETAIL = "RESV_DETAIL"        # 訂房狀況表（訂房層）

SOURCE_TYPES = (SOURCE_FCR02_LEDGER, SOURCE_RESV_DETAIL)

SOURCE_LABELS = {
    SOURCE_FCR02_LEDGER: "客帳帳目明細表",
    SOURCE_RESV_DETAIL: "訂房狀況表",
}

# ── 批次狀態 ──────────────────────────────────────────────────────────────────

STATUS_PENDING = "PENDING"
STATUS_VALIDATED = "VALIDATED"
STATUS_COMMITTED = "COMMITTED"
STATUS_FAILED = "FAILED"
STATUS_ROLLED_BACK = "ROLLED_BACK"

# ── 品質結果 ──────────────────────────────────────────────────────────────────

QUALITY_PASS = "PASS"
QUALITY_PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
QUALITY_FAIL = "FAIL"

# ── 錯誤層級 ──────────────────────────────────────────────────────────────────

SEVERITY_ERROR = "ERROR"
SEVERITY_WARNING = "WARNING"
SEVERITY_INFO = "INFO"

PROGRAM_VERSION = "1.0.0"


class JinxuImportBatch(Base):
    """匯入批次（規格書 §7.1）"""

    __tablename__ = "jinxu_import_batch"

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id:    Mapped[str] = mapped_column(String(36), default="", index=True)
    source_type:   Mapped[str] = mapped_column(String(20), default="", index=True)
    property_code: Mapped[str] = mapped_column(String(20), default="")
    property_name: Mapped[str] = mapped_column(String(50), default="")

    source_file_name: Mapped[str] = mapped_column(String(255), default="")
    file_sha256:      Mapped[str] = mapped_column(String(64), default="", index=True)
    file_size:        Mapped[int] = mapped_column(Integer, default=0)
    sheet_name:       Mapped[str] = mapped_column(String(100), default="")

    report_start_date: Mapped[str] = mapped_column(String(10), default="")   # ISO YYYY-MM-DD
    report_end_date:   Mapped[str] = mapped_column(String(10), default="")   # ISO YYYY-MM-DD
    printed_at:        Mapped[str] = mapped_column(String(30), default="")

    row_count_source:   Mapped[int] = mapped_column(Integer, default=0)  # 檔案總列數
    row_count_data:     Mapped[int] = mapped_column(Integer, default=0)  # 有效資料列數
    row_count_inserted: Mapped[int] = mapped_column(Integer, default=0)
    row_count_updated:  Mapped[int] = mapped_column(Integer, default=0)
    row_count_skipped:  Mapped[int] = mapped_column(Integer, default=0)
    row_count_rejected: Mapped[int] = mapped_column(Integer, default=0)
    row_count_child:    Mapped[int] = mapped_column(Integer, default=0)  # 住宿明細段數

    status:         Mapped[str] = mapped_column(String(20), default=STATUS_PENDING, index=True)
    quality_result: Mapped[str] = mapped_column(String(20), default="")

    totals_json:    Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    reconcile_json: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    started_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=twnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    uploaded_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    uploaded_by_name:    Mapped[str] = mapped_column(String(100), default="")
    program_version:     Mapped[str] = mapped_column(String(20), default=PROGRAM_VERSION)
    error_message:       Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    # ── 輔助 ──────────────────────────────────────────────────────────────────

    @property
    def source_label(self) -> str:
        return SOURCE_LABELS.get(self.source_type, self.source_type or "")

    def set_totals(self, data: dict) -> None:
        self.totals_json = json.dumps(data, ensure_ascii=False)

    def get_totals(self) -> dict:
        return json.loads(self.totals_json) if self.totals_json else {}

    def set_reconcile(self, data: dict) -> None:
        self.reconcile_json = json.dumps(data, ensure_ascii=False)

    def get_reconcile(self) -> dict:
        return json.loads(self.reconcile_json) if self.reconcile_json else {}


class JinxuImportError(Base):
    """匯入錯誤／警告明細（規格書 §7.2）

    ⚠️ raw_value 若來自 RV_detail 的「登記名稱」欄，寫入前必須先遮罩
       （規格書 §15.2；由 jinxu_parser 負責，本層不再處理）。
    """

    __tablename__ = "jinxu_import_error"

    id:       Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(Integer, default=0, index=True)

    source_row_no: Mapped[int] = mapped_column(Integer, default=0)
    field_name:    Mapped[str] = mapped_column(String(50), default="")
    raw_value:     Mapped[str] = mapped_column(String(500), default="")
    error_code:    Mapped[str] = mapped_column(String(30), default="", index=True)
    error_message: Mapped[str] = mapped_column(String(500), default="")
    severity:      Mapped[str] = mapped_column(String(10), default=SEVERITY_ERROR, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=twnow)
