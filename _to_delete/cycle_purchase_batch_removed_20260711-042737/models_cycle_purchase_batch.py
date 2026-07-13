"""
週期採購 — 批次（獨立資料庫 cycle-purchase.db）

第二層：依「週期採購週期設定」的規則，產生實際要開放給各單位填寫的批次
（例如「2026年7月文具統購」）。批次是否已產生請購單由 requests_generated
標記，避免同一批次被重複產生請購單。
"""
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.cycle_purchase_database import CyclePurchaseBase


class CyclePurchaseBatch(CyclePurchaseBase):
    """週期採購批次（第二層：實際作業批次）"""
    __tablename__ = "cycle_purchase_batches"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    batch_no            = Column(String(30), nullable=False, unique=True,
                                  comment="批次號（系統產生，如 CP-202607-0001）")
    cycle_id            = Column(
        Integer,
        ForeignKey("cycle_purchase_cycles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    batch_name          = Column(String(100), nullable=False, comment="批次名稱（如 2026年7月文具統購）")
    open_date           = Column(Date, nullable=False, comment="開放日期")
    close_date          = Column(Date, nullable=False, comment="截止日期")
    status              = Column(String(20), nullable=False, default="draft",
                                  comment="狀態：draft | open | closed | done")
    requests_generated  = Column(Boolean, nullable=False, default=False,
                                  comment="是否已產生請購單（防止重複產生，對應 RFP REQ 需求）")

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    cycle = relationship("CyclePurchaseCycle", back_populates="batches")

    def __repr__(self):
        return f"<CyclePurchaseBatch id={self.id} no={self.batch_no} status={self.status}>"
