"""
整棟工務每日巡檢 - B1F  ORM 模型【寬表格 Pivot 架構】

資料庫表格：
  b1f_inspection_batch  — 每次巡檢場次（對應一筆 Ragic Row）
  b1f_inspection_item   — 巡檢設備項目（每個欄位 pivot 成一列）
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.core.database import Base


class B1FInspectionBatch(Base):
    """一次完整巡檢場次，對應 Ragic Sheet 4 的一個 Row。"""
    __tablename__ = "b1f_inspection_batch"

    ragic_id = Column(String(50), primary_key=True, comment="Ragic Sheet 4 記錄 ID")

    inspection_date = Column(String(20),  nullable=False, default="", comment="巡檢日期，從開始時間萃取 YYYY/MM/DD")
    inspector_name  = Column(String(100), nullable=False, default="", comment="巡檢人員")
    start_time      = Column(String(30),  nullable=False, default="", comment="開始巡檢時間（原始值）")
    end_time        = Column(String(30),  nullable=False, default="", comment="巡檢結束時間（原始值）")
    work_hours      = Column(String(20),  nullable=False, default="", comment="工時計算")

    synced_at = Column(DateTime, nullable=False, server_default=func.now(),
                       onupdate=func.now(), comment="最近同步時間")

    def __repr__(self):
        return f"<B1FInspectionBatch {self.ragic_id} {self.inspection_date}>"


class B1FInspectionItem(Base):
    """巡檢設備項目（一筆 = 一個設備欄位值）。"""
    __tablename__ = "b1f_inspection_item"

    ragic_id = Column(String(80), primary_key=True, comment="複合鍵：{batch_ragic_id}_{seq_no}")

    batch_ragic_id = Column(String(50), nullable=False, default="",
                            comment="所屬場次 ragic_id")

    seq_no    = Column(Integer,     nullable=False, default=0,   comment="項次（依欄位順序）")
    item_name = Column(String(200), nullable=False, default="",  comment="設備/項目名稱（Ragic 欄位名）")

    result_raw    = Column(String(50), nullable=False, default="",          comment="原始值（正常/異常/待處理/空白）")
    result_status = Column(String(20), nullable=False, default="unchecked", comment="正規化：normal/abnormal/pending/unchecked")
    abnormal_flag = Column(Boolean,    nullable=False, default=False,        comment="是否有異常旗標")

    synced_at = Column(DateTime, nullable=False, server_default=func.now(),
                       onupdate=func.now(), comment="最近同步時間")

    def __repr__(self):
        return f"<B1FInspectionItem {self.ragic_id} {self.item_name}={self.result_status}>"
