"""
週期保養預排 SQLAlchemy ORM Model

資料來源（主管排定 Sheets）：
  Sheet 7  → https://ap12.ragic.com/soutlet001/periodic-maintenance/7  （飯店週期保養主管排定）
  Sheet 13 → https://ap12.ragic.com/soutlet001/periodic-maintenance/13 （商場週期保養主管排定）
  Sheet 20 → https://ap12.ragic.com/soutlet001/periodic-maintenance/20 （全棟例行維護主管排定）

資料表：
  pm_plan_item — 週期保養預排項目（三個 Sheet 共用，source_sheet 欄位區分來源）
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, func, Index
from app.core.database import Base


class PmPlanItem(Base):
    """
    週期保養預排項目
    每筆記錄代表主管為某個保養任務排定的一個執行日期（年/半年/季/月）。
    """
    __tablename__ = "pm_plan_item"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    # 格式："{source_sheet}_{ragic_record_id}"，如 "7_42"、"13_5"
    ragic_id = Column(String(80), primary_key=True, comment="格式: {sheet_no}_{ragic記錄ID}")

    # ── 來源識別 ──────────────────────────────────────────────────────────────
    source_sheet = Column(Integer, nullable=False, default=0,
                          comment="來源 Sheet 編號: 7=飯店、13=商場、20=全棟")
    source_label = Column(String(50), nullable=False, default="",
                          comment="來源中文標籤: 飯店/商場/全棟")

    # ── 保養任務資訊（Ragic 同步，不可被 Portal 編輯覆寫）────────────────────
    task_name      = Column(String(200), nullable=False, default="", comment="保養項目描述（項目欄位）")
    category       = Column(String(50),  nullable=False, default="", comment="類別：水電、空調等")
    frequency      = Column(String(20),  nullable=False, default="", comment="頻率：月/季/半年/年")
    exec_months_raw = Column(String(100), nullable=False, default="",
                             comment="執行月份原始文字，如「2月 5月 8月 11月」")
    location       = Column(String(100), nullable=False, default="", comment="位置/區域")

    # ── 排定資訊 ──────────────────────────────────────────────────────────────
    # scheduled_date 統一存為 YYYY-MM-DD（ISO 格式），便於行事曆日期篩選
    scheduled_date  = Column(String(10),  nullable=False, default="",
                             comment="排定日期 ISO 格式 YYYY-MM-DD（空=尚未排定）")
    scheduler_name  = Column(String(100), nullable=False, default="", comment="排定人員")
    note            = Column(Text,        nullable=False, default="", comment="備註")

    # ── Ragic 連結 ────────────────────────────────────────────────────────────
    ragic_url = Column(String(300), nullable=False, default="",
                       comment="Ragic 原始記錄連結，格式 https://ap12.ragic.com/soutlet001/periodic-maintenance/{sheet}/{id}")

    # ── Ragic 時間戳 ──────────────────────────────────────────────────────────
    ragic_created_at = Column(String(30), nullable=False, default="")
    ragic_updated_at = Column(String(30), nullable=False, default="")

    # ── Portal 同步時間 ────────────────────────────────────────────────────────
    synced_at = Column(DateTime, nullable=False, server_default=func.now(),
                       onupdate=func.now(), comment="最後同步時間")

    __table_args__ = (
        Index("ix_pm_plan_sched_date",  "scheduled_date"),
        Index("ix_pm_plan_source_sheet","source_sheet"),
        Index("ix_pm_plan_frequency",   "frequency"),
    )

    def __repr__(self):
        return (
            f"<PmPlanItem ragic_id={self.ragic_id} "
            f"source={self.source_label} "
            f"date={self.scheduled_date} "
            f"task={self.task_name[:30]}>"
        )
