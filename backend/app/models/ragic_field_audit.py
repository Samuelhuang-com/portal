"""
Ragic 與 Portal 欄位比對 — 資料模型

包含三張表：
  1. ragic_portal_audit_runs      — 比對任務紀錄（每次執行比對的快照）
  2. ragic_portal_field_mappings  — 欄位對應關係（Ragic ↔ Portal DB / API / 前端）
  3. ragic_portal_kpi_mappings    — KPI / Dashboard 計算來源追溯
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.core.time import twnow


class RagicPortalAuditRun(Base):
    """記錄每次欄位比對任務的執行結果摘要。"""
    __tablename__ = "ragic_portal_audit_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_time: Mapped[datetime] = mapped_column(DateTime, default=twnow)
    triggered_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 使用者 email
    scope: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)         # "all" 或 module_name
    total_modules: Mapped[int] = mapped_column(Integer, default=0)
    normal_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="completed")             # running / completed / failed
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class RagicPortalFieldMapping(Base):
    """
    記錄 Ragic 欄位與 Portal 各層欄位的對應關係。
    每筆代表一個模組的一個欄位對應紀錄。
    """
    __tablename__ = "ragic_portal_field_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── 模組識別 ──────────────────────────────────────────────────────────────
    app_directory_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)   # ragic_app_portal_annotations.item_no
    company: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)        # 公司 / 據點
    module_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)    # Portal 模組中文名稱
    portal_route: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)   # /settings/ragic-field-audit
    ragic_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ragic_form_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # ── Ragic 欄位資訊 ────────────────────────────────────────────────────────
    ragic_field_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ragic_field_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    ragic_field_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # text / number / date / select / formula / subtable
    is_ragic_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_ragic_formula: Mapped[bool] = mapped_column(Boolean, default=False)
    is_ragic_subtable: Mapped[bool] = mapped_column(Boolean, default=False)
    ragic_options: Mapped[Optional[str]] = mapped_column(Text, nullable=True)          # JSON array of select options

    # ── Portal 各層欄位 ───────────────────────────────────────────────────────
    portal_db_table: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    portal_db_field: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    portal_api_field: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    portal_frontend_field: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)   # 前端中文顯示名稱

    # ── 使用情況標記 ──────────────────────────────────────────────────────────
    is_displayed: Mapped[bool] = mapped_column(Boolean, default=False)    # 有出現在頁面
    is_filter: Mapped[bool] = mapped_column(Boolean, default=False)       # 用於篩選
    is_export: Mapped[bool] = mapped_column(Boolean, default=False)       # 用於匯出
    is_calculated: Mapped[bool] = mapped_column(Boolean, default=False)   # 用於計算

    # ── 比對結果 ──────────────────────────────────────────────────────────────
    # mapping_status 可能值：
    #   normal          — 正常對應
    #   ragic_only      — Ragic 有，Portal 沒有
    #   portal_only     — Portal 有，Ragic 沒有
    #   name_mismatch   — 欄位名稱疑似不同（fuzzy match）
    #   type_mismatch   — 型態不一致
    #   null_rate_high  — 空值率異常
    #   formula_unmarked — 公式欄位未標示
    #   subtable_unmarked — 子表格欄位未處理
    #   unmapped        — 未建立 Mapping
    mapping_status: Mapped[str] = mapped_column(String(50), default="unmapped")
    severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)        # high / medium / low
    issue_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    issue_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)         # 主管看得懂的說明
    suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)            # 建議處理方式
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=twnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=twnow, onupdate=twnow)


class RagicPortalKpiMapping(Base):
    """
    記錄 Dashboard / 統計模組的 KPI 與 Ragic 原始欄位的可追溯關係。
    """
    __tablename__ = "ragic_portal_kpi_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── 模組識別 ──────────────────────────────────────────────────────────────
    app_directory_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    module_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    portal_route: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # ── KPI 描述 ──────────────────────────────────────────────────────────────
    kpi_name: Mapped[str] = mapped_column(String(200))                               # KPI 名稱
    page_section: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 顯示位置（頁面區塊）

    # ── 資料來源 ──────────────────────────────────────────────────────────────
    api_endpoint: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    db_table: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    source_fields: Mapped[Optional[str]] = mapped_column(Text, nullable=True)        # JSON array，使用的欄位
    date_field: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)    # 日期依據欄位
    filters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)              # JSON：篩選條件
    formula: Mapped[Optional[str]] = mapped_column(Text, nullable=True)              # 計算公式說明

    # ── Ragic 可追溯性 ───────────────────────────────────────────────────────
    ragic_source_fields: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    # trace_status 可能值：traceable / partial / untraceable / unknown
    trace_status: Mapped[str] = mapped_column(String(30), default="unknown")
    issue_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=twnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=twnow, onupdate=twnow)
