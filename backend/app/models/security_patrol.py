"""
保全巡檢 SQLAlchemy ORM Models【統一模型 + 寬表格 Pivot 架構】

支援 7 張 Ragic Sheet（同一組 DB 表格，以 sheet_key 區分）：
  b1f-b4f  → security-patrol/1  保全每日巡檢 - B1F~B4F夜間巡檢
  1f-3f    → security-patrol/2  保全巡檢 - 1F ~ 3F (夜間巡檢)
  5f-10f   → security-patrol/3  保全巡檢 - 5F ~ 10F (夜間巡檢)
  4f       → security-patrol/4  保全巡檢 - 4F (夜間巡檢)
  1f-hotel → security-patrol/5  保全巡檢 - 1F夜間巡檢 (飯店大廳)
  1f-close → security-patrol/6  保全巡檢 - 1F 閉店巡檢
  1f-open  → security-patrol/9  保全巡檢 - 1F 開店準備

DB 架構：
  security_patrol_batch  — 一筆 = 一次巡檢場次（對應 Ragic 一個 Row）
  security_patrol_item   — 一筆 = 一個巡檢點結果（Sync 時 pivot 產生）

巡檢結果狀態（item.result_status）：
  normal    — 正常（OK）
  abnormal  — 異常
  pending   — 待處理 / 待修
  unchecked — 空白 / 未填
  note      — 文字備註（異常說明類欄位，is_note=True，不計入統計）
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, func, Index
from app.core.database import Base


class SecurityPatrolBatch(Base):
    """保全巡檢場次（每筆 Ragic 記錄 = 一次完整巡檢）"""
    __tablename__ = "security_patrol_batch"

    # ── 主鍵（"{sheet_key}_{ragic_row_id}"，避免不同 sheet 衝突）───────────────
    ragic_id = Column(String(80), primary_key=True,
                      comment="複合主鍵：{sheet_key}_{Ragic Row ID}")

    # ── Sheet 識別 ───────────────────────────────────────────────────────────
    sheet_key  = Column(String(20), nullable=False, default="",
                        comment="Sheet 識別符，如 b1f-b4f / 1f-3f / 5f-10f ...")
    sheet_id   = Column(Integer,    nullable=False, default=0,
                        comment="Ragic Sheet 編號，如 1 / 2 / 3 ...")
    sheet_name = Column(String(100), nullable=False, default="",
                        comment="Sheet 顯示名稱，如 保全巡檢 - 5F~10F (夜間巡檢)")

    # ── 場次欄位 ─────────────────────────────────────────────────────────────
    inspection_date = Column(String(20),  nullable=False, default="",
                             comment="巡檢日期，從開始時間萃取 YYYY/MM/DD")
    inspector_name  = Column(String(100), nullable=False, default="",
                             comment="巡檢人員")
    start_time      = Column(String(30),  nullable=False, default="",
                             comment="開始巡檢時間（原始值）")
    end_time        = Column(String(30),  nullable=False, default="",
                             comment="巡檢結束時間（原始值）")
    work_hours      = Column(String(20),  nullable=False, default="",
                             comment="工時計算")

    # ── 同步時間 ──────────────────────────────────────────────────────────────
    synced_at = Column(DateTime, nullable=False, server_default=func.now(),
                       onupdate=func.now(), comment="最後同步時間")

    __table_args__ = (
        Index("ix_sp_batch_sheet_date", "sheet_key", "inspection_date"),
    )

    def __repr__(self):
        return (
            f"<SecurityPatrolBatch {self.ragic_id} "
            f"sheet={self.sheet_key} date={self.inspection_date}>"
        )


class SecurityPatrolItem(Base):
    """保全巡檢項目（每個巡檢點一筆，由 Sync 時 pivot 產生）"""
    __tablename__ = "security_patrol_item"

    # ── 主鍵（"{batch_ragic_id}_{seq_no}"）───────────────────────────────────
    ragic_id = Column(String(100), primary_key=True,
                      comment="複合主鍵：{batch_ragic_id}_{seq_no}")

    # ── 外鍵 ─────────────────────────────────────────────────────────────────
    batch_ragic_id = Column(String(80), nullable=False, default="",
                            comment="所屬場次 ragic_id（security_patrol_batch.ragic_id）")
    sheet_key      = Column(String(20), nullable=False, default="",
                            comment="冗餘欄位，方便跨 sheet 查詢")

    # ── 項目資訊 ──────────────────────────────────────────────────────────────
    seq_no    = Column(Integer,     nullable=False, default=0,   comment="項次順序")
    item_name = Column(String(200), nullable=False, default="",  comment="巡檢點名稱（Ragic 欄位名）")

    # ── 巡檢結果 ──────────────────────────────────────────────────────────────
    result_raw    = Column(String(50),  nullable=False, default="",          comment="原始值")
    result_status = Column(String(20),  nullable=False, default="unchecked", comment="正規化：normal/abnormal/pending/unchecked/note")
    abnormal_flag = Column(Boolean,     nullable=False, default=False,        comment="是否異常旗標")
    is_note       = Column(Boolean,     nullable=False, default=False,        comment="文字備註項（異常說明類），呈現但不計入統計")

    # ── 同步時間 ──────────────────────────────────────────────────────────────
    synced_at = Column(DateTime, nullable=False, server_default=func.now(),
                       onupdate=func.now(), comment="最後同步時間")

    __table_args__ = (
        Index("ix_sp_item_batch",      "batch_ragic_id"),
        Index("ix_sp_item_sheet_name", "sheet_key", "item_name"),
    )

    def __repr__(self):
        return (
            f"<SecurityPatrolItem {self.ragic_id} "
            f"item={self.item_name[:20]} status={self.result_status}>"
        )
