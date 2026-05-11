"""
IHG 客房保養 SQLAlchemy ORM Models

資料表：
  ihg_rm_master   — 保養主表（對應 Ragic Sheet periodic-maintenance/4 每筆記錄）
  ihg_rm_detail   — 保養明細（每筆主表內的子表格列）
  ihg_rm_section  — 保養區段摘要（V/▲/X，每月×每房×每類別一列，供統計分析）

設計原則：
  - raw_json 保留完整 Ragic 原始 JSON，欄位 mapping 可隨時補正
  - 同步後由 Portal 讀本地 DB，不重複打 Ragic
  - floor 由 room_no 前 1~2 位自動推導（如 501 → 5F, 1001 → 10F）
  - section 資料於 Ragic 同步時由 raw_json 自動拆出，供月報矩陣查詢
"""
import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, Index, func
from app.core.database import Base


class IHGRoomMaintenanceMaster(Base):
    """IHG 客房保養主表（Ragic Sheet 4 每筆記錄一列）"""
    __tablename__ = "ihg_rm_master"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    ragic_id = Column(String(50), primary_key=True, comment="Ragic Sheet 4 記錄 ID")

    # ── 房號資訊 ──────────────────────────────────────────────────────────────
    room_no  = Column(String(20),  nullable=False, default="", comment="房號，如 501")
    floor    = Column(String(10),  nullable=False, default="", comment="樓層，如 5F（由 room_no 推導）")

    # ── 時間軸 ────────────────────────────────────────────────────────────────
    maint_year   = Column(String(4),  nullable=False, default="", comment="保養年度，如 2026")
    maint_month  = Column(String(2),  nullable=False, default="", comment="保養月份，如 04")
    maint_date   = Column(String(20), nullable=False, default="", comment="實際保養日期，如 2026/04/15")

    # ── 保養狀態 ──────────────────────────────────────────────────────────────
    # 狀態值：pending / completed / overdue / scheduled
    status       = Column(String(20), nullable=False, default="pending", comment="保養狀態")
    is_completed = Column(Boolean,    nullable=False, default=False,      comment="是否完成")

    # ── 人員 ──────────────────────────────────────────────────────────────────
    assignee_name   = Column(String(100), nullable=False, default="", comment="保養人員")
    checker_name    = Column(String(100), nullable=False, default="", comment="複核人員")

    # ── 其他資訊 ──────────────────────────────────────────────────────────────
    maint_type      = Column(String(50),  nullable=False, default="", comment="保養類型")
    notes           = Column(Text,        nullable=False, default="", comment="備註")
    completion_date = Column(String(20),  nullable=False, default="", comment="完成日期")

    # ── Ragic 原始資料（保留完整 JSON，供欄位補正）───────────────────────────
    raw_json         = Column(Text, nullable=False, default="{}", comment="Ragic 原始 JSON")

    # ── Ragic 時間戳 ──────────────────────────────────────────────────────────
    ragic_created_at = Column(String(30), nullable=False, default="", comment="Ragic 建立時間")
    ragic_updated_at = Column(String(30), nullable=False, default="", comment="Ragic 更新時間")

    # ── Portal 同步時間 ────────────────────────────────────────────────────────
    synced_at = Column(DateTime, nullable=False, server_default=func.now(),
                       onupdate=func.now(), comment="最後同步時間")

    def get_raw(self) -> dict:
        try:
            return json.loads(self.raw_json or "{}")
        except Exception:
            return {}

    def __repr__(self):
        return (
            f"<IHGRMMaster ragic_id={self.ragic_id} "
            f"room_no={self.room_no} {self.maint_year}/{self.maint_month}>"
        )


class IHGRoomMaintenanceDetail(Base):
    """IHG 客房保養明細（Ragic Sheet 4 子表格列，若無子表格則不使用）"""
    __tablename__ = "ihg_rm_detail"

    # ── 主鍵："{master_ragic_id}_{row_key}" ────────────────────────────────
    ragic_id         = Column(String(80), primary_key=True,
                               comment="複合 ID：{master_ragic_id}_{row_key}")
    master_ragic_id  = Column(String(50), nullable=False, default="",
                               comment="關聯 ihg_rm_master.ragic_id")

    # ── 明細欄位 ──────────────────────────────────────────────────────────────
    seq_no      = Column(Integer,     nullable=False, default=0,  comment="項次")
    task_name   = Column(String(200), nullable=False, default="", comment="保養項目")
    result      = Column(String(20),  nullable=False, default="", comment="執行結果（OK/NG/N/A）")
    notes       = Column(Text,        nullable=False, default="", comment="備註")
    is_ok       = Column(Boolean,     nullable=False, default=False, comment="是否正常")

    # ── Ragic 原始資料 ────────────────────────────────────────────────────────
    raw_json    = Column(Text, nullable=False, default="{}", comment="子列原始 JSON")

    # ── 同步時間 ──────────────────────────────────────────────────────────────
    synced_at   = Column(DateTime, nullable=False, server_default=func.now(),
                         onupdate=func.now(), comment="最後同步時間")

    def __repr__(self):
        return (
            f"<IHGRMDetail ragic_id={self.ragic_id} "
            f"seq_no={self.seq_no} task={self.task_name[:30]}>"
        )


class IHGRoomMaintenanceSection(Base):
    """
    IHG 客房保養區段摘要（每月 x 每房 x 每類別 一列）

    區段欄位來自 raw_json 的 section header 欄位（值為 V/三角/X），
    於 Ragic 同步時自動拆出寫入此表，供月報矩陣使用。

    值域意義：
      V  — 已完成
      X  — 待料中（等待維護）
    """
    __tablename__ = "ihg_rm_section"

    id              = Column(Integer,    primary_key=True, autoincrement=True)
    master_ragic_id = Column(String(50), nullable=False, default="",
                             comment="關聯 ihg_rm_master.ragic_id")
    room_no         = Column(String(20), nullable=False, default="",
                             comment="房號（冗餘，方便查詢）")
    maint_year      = Column(String(4),  nullable=False, default="", comment="年度")
    maint_month     = Column(String(2),  nullable=False, default="", comment="月份（零填）")
    category        = Column(String(50), nullable=False, default="",
                             comment="類別名稱，如 客房房門、浴厠")
    value           = Column(String(10), nullable=False, default="",
                             comment="值域：V / X")
    synced_at       = Column(DateTime, nullable=False, server_default=func.now(),
                             onupdate=func.now(), comment="最後同步時間")

    __table_args__ = (
        Index("ix_ihg_rm_section_ym_room",
              "maint_year", "maint_month", "room_no"),
        Index("ix_ihg_rm_section_master",
              "master_ragic_id"),
    )

    def __repr__(self):
        return (
            f"<IHGRMSection master={self.master_ragic_id} "
            f"{self.room_no} {self.maint_year}/{self.maint_month} "
            f"{self.category}={self.value}>"
        )
