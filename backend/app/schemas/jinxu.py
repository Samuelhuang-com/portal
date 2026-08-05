"""
金旭 PMS 分析 — Pydantic Schemas

規格書：docs/SPEC_jinxu_analytics.md §12

⚠️ J17：FCR02 的「備註」欄儲存於 DB 但**全站不顯示**。
   本檔案的任何 response schema 都**不得**出現 remark 欄位。
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class BatchSummary(BaseModel):
    """匯入紀錄清單用。"""

    id: int
    source_type: str
    source_label: str
    source_file_name: str
    file_size: int
    report_start_date: str
    report_end_date: str
    row_count_data: int
    row_count_inserted: int
    row_count_updated: int
    row_count_skipped: int
    row_count_rejected: int
    row_count_child: int
    status: str
    quality_result: str
    started_at: str = ""
    completed_at: str = ""
    uploaded_by_name: str = ""
    error_message: str = ""


class BatchListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[BatchSummary]


class BatchDetail(BatchSummary):
    session_id: str = ""
    property_code: str = ""
    property_name: str = ""
    file_sha256: str = ""
    sheet_name: str = ""
    printed_at: str = ""
    row_count_source: int = 0
    program_version: str = ""
    totals: dict = Field(default_factory=dict)
    reconcile: dict = Field(default_factory=dict)
    issue_summary: list[dict] = Field(default_factory=list)


class ImportIssue(BaseModel):
    id: int
    source_row_no: int
    field_name: str
    raw_value: str
    error_code: str
    error_message: str
    severity: str


class IssueListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ImportIssue]


class ValidateResponse(BaseModel):
    """驗證報告（不寫入 DB）。"""

    ok: bool
    error: str = ""
    detected_source_type: str | None = None

    source_type: str = ""
    source_label: str = ""
    file_name: str = ""
    file_sha256: str = ""
    file_size: int = 0
    sheet_name: str = ""
    total_source_rows: int = 0

    row_counts: dict = Field(default_factory=dict)
    data_rows: int = 0
    child_rows: int = 0
    report_start_date: str = ""
    report_end_date: str = ""
    printed_at: str = ""
    property_name: str = ""
    unknown_subjects: list[str] = Field(default_factory=list)

    duplicate_batch: dict | None = None
    quality_result: str = ""
    can_commit: bool = False
    reconcile: dict = Field(default_factory=dict)
    issue_summary: list[dict] = Field(default_factory=list)
    issue_samples: list[dict] = Field(default_factory=list)
    delta: dict = Field(default_factory=dict)


class CommitResponse(BaseModel):
    ok: bool
    message: str = ""
    batch_id: int | None = None
    source_type: str = ""
    source_label: str = ""
    quality_result: str = ""
    row_count_data: int = 0
    row_count_inserted: int = 0
    row_count_updated: int = 0
    row_count_skipped: int = 0
    row_count_rejected: int = 0
    row_count_child: int = 0
    reconcile: dict = Field(default_factory=dict)


class RollbackResponse(BaseModel):
    ok: bool
    batch_id: int
    deleted_raw_rows: int
    updated_keys_count: int
    updated_keys: list[str] = Field(default_factory=list)
    warning: str = ""


class SourceStatus(BaseModel):
    label: str
    row_count: int
    child_count: int = 0
    date_start: str = ""
    date_end: str = ""
    has_data: bool = False


class ImportStatusResponse(BaseModel):
    sources: dict[str, SourceStatus]
    cross_analysis_available: bool
    years_covered: list[str]
    yoy_available: bool
    last_batch: dict | None = None
