"""
全棟例行維護 SQLAlchemy ORM Models

資料表：
  full_bldg_pm_batch       — 保養批次主表（對應 Ragic Sheet 21）
  full_bldg_pm_batch_item  — 保養項目明細（對應 Ragic Sheet 21 sub-table）
"""
import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, func
from app.core.database import Base


class FullBldgPMBatch(Base):
    """全棟例行維護批次主表（每月/每期一筆）"""
    __tablename__ = "full_bldg_pm_batch"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    ragic_id = Column(String(50), primary_key=True, comment="Ragic Sheet 21 記錄 ID")

    # ── 業務欄位 ──────────────────────────────────────────────────────────────
    journal_no    = Column(String(50),  nullable=False, default="", comment="保養日誌編號，如 全棟保202604-001")
    period_month  = Column(String(10),  nullable=False, default="", comment="保養月份，如 2026/04")

    # ── Ragic 時間戳 ──────────────────────────────────────────────────────────
    ragic_created_at = Column(String(30), nullable=False, default="", comment="Ragic 建立時間")
    ragic_updated_at = Column(String(30), nullable=False, default="", comment="Ragic 更新時間")

    # ── Portal 同步時間 ────────────────────────────────────────────────────────
    synced_at = Column(DateTime, nullable=False, server_default=func.now(),
                       onupdate=func.now(), comment="最後同步時間")

    def __repr__(self):
        return f"<FullBldgPMBatch ragic_id={self.ragic_id} journal_no={self.journal_no} period_month={self.period_month}>"


class FullBldgPMItem(Base):
    """全棟例行維護項目明細（每個保養任務一筆）"""
    __tablename__ = "full_bldg_pm_batch_item"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    ragic_id = Column(String(50), primary_key=True, comment="Ragic 記錄 ID，格式 {batch_id}_{row_key}")

    # ── 外鍵關聯 ──────────────────────────────────────────────────────────────
    batch_ragic_id = Column(String(50), nullable=False, default="", comment="關聯 full_bldg_pm_batch.ragic_id")

    # ── 保養項目基本資料（Ragic 同步，不可被 Portal 編輯覆寫）──────────────────
    seq_no            = Column(Integer,     nullable=False, default=0,  comment="項次")
    category          = Column(String(50),  nullable=False, default="", comment="類別：水電、空調等")
    frequency         = Column(String(20),  nullable=False, default="", comment="頻率：月/季/半年/年")
    exec_months_raw   = Column(String(100), nullable=False, default="", comment="執行月份原始文字，如「2月 5月 8月 11月」")
    exec_months_json  = Column(Text,        nullable=False, default="[]", comment="解析後整數陣列 JSON，如 [2,5,8,11]")
    task_name         = Column(String(200), nullable=False, default="", comment="保養項目描述")
    location          = Column(String(100), nullable=False, default="", comment="區域/位置")
    estimated_minutes = Column(Integer,     nullable=False, default=0,  comment="預估耗時（分鐘）")

    # ── 排定與執行欄位（Ragic 同步來源）─────────────────────────────────────
    scheduled_date  = Column(String(10),  nullable=False, default="", comment="排定日期，如 04/23")
    scheduler_name  = Column(String(100), nullable=False, default="", comment="排定人員")
    executor_name   = Column(String(100), nullable=False, default="", comment="執行人員（多人以空格分隔）")
    start_time      = Column(String(30),  nullable=False, default="", comment="保養開始時間")
    end_time        = Column(String(30),  nullable=False, default="", comment="保養結束時間（空白=尚未完成）")

    # ── 完成標記（start_time + end_time 均有值 → True）──
    is_completed   = Column(Boolean, nullable=False, default=False, comment="保養是否完成")

    # ── Portal 回填欄位 ──────────────────────────────────────────────────────
    result_note    = Column(Text,    nullable=False, default="",    comment="執行結果備註")
    abnormal_flag  = Column(Boolean, nullable=False, default=False, comment="是否有異常")
    abnormal_note  = Column(Text,    nullable=False, default="",    comment="異常說明")

    # ── Portal 編輯時間戳 ──────────────────────────────────────────────────────
    portal_edited_at = Column(DateTime, nullable=True, comment="Portal 最後編輯時間（保護機制）")

    # ── 同步時間 ───────────────────────────────────────────────────────────────
    synced_at = Column(DateTime, nullable=False, server_default=func.now(),
                       onupdate=func.now(), comment="最後同步時間")

    # ── Helper ────────────────────────────────────────────────────────────────
    def get_exec_months(self) -> list[int]:
        try:
            return json.loads(self.exec_months_json or "[]")
        except Exception:
            return []

    def __repr__(self):
        return f"<FullBldgPMItem ragic_id={self.ragic_id} seq_no={self.seq_no} task_name={self.task_name[:20]}>"
