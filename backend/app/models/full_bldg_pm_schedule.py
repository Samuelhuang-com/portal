"""
全棟例行維護排程明細 ORM Model

資料表：full_bldg_pm_schedule
  - Portal 自有排程記錄（與 Ragic 同步無關）
  - 由「產生本月排程」功能依 full_bldg_pm_batch_item 主檔的頻率規則自動建立
  - 防重複：UNIQUE(year_month, item_ragic_id)
  - 保護機制：is_completed=True 或 portal_edited_at IS NOT NULL → 不被覆蓋
"""
from sqlalchemy import (
    Column, String, Integer, Text, DateTime, Boolean,
    func, Index, UniqueConstraint
)
from app.core.database import Base


class FullBldgPMSchedule(Base):
    """全棟例行維護排程明細（Portal 自有，不影響 Ragic 同步）"""
    __tablename__ = "full_bldg_pm_schedule"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 關聯 ──────────────────────────────────────────────────────────────────
    year_month    = Column(String(10),  nullable=False, comment="排程月份，如 2026/05")
    item_ragic_id = Column(String(50),  nullable=False, comment="來源主檔 full_bldg_pm_batch_item.ragic_id")

    # ── 快照欄位（產生時複製，歷史保護）────────────────────────────────────
    category          = Column(String(50),  nullable=False, default="",  comment="類別")
    task_name         = Column(String(200), nullable=False, default="",  comment="保養項目")
    location          = Column(String(100), nullable=False, default="",  comment="位置")
    frequency         = Column(String(20),  nullable=False, default="",  comment="頻率")
    estimated_minutes = Column(Integer,     nullable=False, default=0,   comment="預估耗時（分鐘）")

    # ── 排程資訊 ──────────────────────────────────────────────────────────────
    scheduled_date  = Column(String(10),  nullable=False, default="",    comment="排定日期，如 05/15")
    executor_name   = Column(String(100), nullable=False, default="",    comment="執行人員")
    schedule_source = Column(String(20),  nullable=False, default="auto",comment="來源：auto=自動產生, manual=人工調整")

    # ── 執行結果 ──────────────────────────────────────────────────────────────
    start_time     = Column(String(30), nullable=False, default="",    comment="保養開始時間")
    end_time       = Column(String(30), nullable=False, default="",    comment="保養結束時間")
    is_completed   = Column(Boolean,    nullable=False, default=False, comment="是否完成")
    result_note    = Column(Text,       nullable=False, default="",    comment="執行備註")
    abnormal_flag  = Column(Boolean,    nullable=False, default=False, comment="是否異常")
    abnormal_note  = Column(Text,       nullable=False, default="",    comment="異常說明")

    # ── 保護欄位 ──────────────────────────────────────────────────────────────
    portal_edited_at = Column(DateTime, nullable=True,
                               comment="人工調整時間戳，有值 → 不被 generate 覆蓋")

    # ── 時間戳 ────────────────────────────────────────────────────────────────
    created_at = Column(DateTime, nullable=False, server_default=func.now(),
                        comment="建立時間")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(),
                        onupdate=func.now(), comment="最後更新時間")

    __table_args__ = (
        UniqueConstraint("year_month", "item_ragic_id", name="uq_full_bldg_pm_schedule_month_item"),
        Index("ix_full_bldg_pm_schedule_year_month", "year_month"),
        Index("ix_full_bldg_pm_schedule_item",       "item_ragic_id"),
        Index("ix_full_bldg_pm_schedule_completed",  "is_completed"),
        Index("ix_full_bldg_pm_schedule_abnormal",   "abnormal_flag"),
    )

    def __repr__(self):
        return (
            f"<FullBldgPMSchedule id={self.id} year_month={self.year_month} "
            f"task={self.task_name[:20]!r} status={'done' if self.is_completed else 'open'}>"
        )
