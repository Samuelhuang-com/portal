"""
客房保養明細 SQLAlchemy ORM Model
對應資料庫表：room_maintenance_detail_records

欄位來源：https://ap12.ragic.com/soutlet001/report2/2
  保養日期、保養人員、房號、工時計算、建立日期
  檢查項目（X/V）：房門、消防、設備、傢俱、客房燈/電源、客房窗、
                   面盆/台面、浴厠、浴間、天地壁、客房空調、陽台
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, func
from app.core.database import Base


class RoomMaintenanceDetailRecord(Base):
    __tablename__ = "room_maintenance_detail_records"

    # ── 主鍵：使用 Ragic record ID（字串）作為自然主鍵 ─────────────────────────
    ragic_id = Column(String(50), primary_key=True, comment="Ragic 記錄 ID")

    # ── 基本資訊 ──────────────────────────────────────────────────────────────
    maintain_date  = Column(String(20),  nullable=False, default="", comment="保養日期")
    staff_name     = Column(String(100), nullable=False, default="", comment="保養人員")
    room_no        = Column(String(20),  nullable=False, default="", comment="房號")
    work_hours     = Column(String(50),  nullable=False, default="", comment="工時計算")
    created_date   = Column(String(30),  nullable=False, default="", comment="建立日期")

    # ── 檢查項目（V = 正常, X = 異常, 空 = 未填）─────────────────────────────
    chk_door       = Column(String(5), nullable=False, default="", comment="房門")
    chk_fire       = Column(String(5), nullable=False, default="", comment="消防")
    chk_equipment  = Column(String(5), nullable=False, default="", comment="設備")
    chk_furniture  = Column(String(5), nullable=False, default="", comment="傢俱")
    chk_light      = Column(String(5), nullable=False, default="", comment="客房燈/電源")
    chk_window     = Column(String(5), nullable=False, default="", comment="客房窗")
    chk_sink       = Column(String(5), nullable=False, default="", comment="面盆/台面")
    chk_toilet     = Column(String(5), nullable=False, default="", comment="浴厠")
    chk_bath       = Column(String(5), nullable=False, default="", comment="浴間")
    chk_surface    = Column(String(5), nullable=False, default="", comment="天地壁")
    chk_ac         = Column(String(5), nullable=False, default="", comment="客房空調")
    chk_balcony    = Column(String(5), nullable=False, default="", comment="陽台")

    # ── Portal 同步時間 ────────────────────────────────────────────────────────
    synced_at = Column(
        DateTime, nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="最後同步時間",
    )

    def __repr__(self) -> str:
        return (
            f"<RoomMaintenanceDetailRecord ragic_id={self.ragic_id} "
            f"room_no={self.room_no} date={self.maintain_date}>"
        )
