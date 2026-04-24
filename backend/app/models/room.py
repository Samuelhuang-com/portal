"""
客房主檔 SQLAlchemy ORM Model
對應資料庫表：rooms

資料為靜態主檔，記錄飯店所有樓層 × 房號，
供「客房保養明細總表」顯示完整房間清單（含未保養灰底）。
"""
from sqlalchemy import Column, Integer, String
from app.core.database import Base


class Room(Base):
    __tablename__ = "rooms"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    floor    = Column(String(10), nullable=False, default="", comment="樓層標籤 e.g. '9F'")
    floor_no = Column(Integer,    nullable=False, default=0,  comment="樓層數字 e.g. 9，供排序")
    room_no  = Column(String(10), nullable=False, unique=True, default="", comment="房號 e.g. '923'")

    def __repr__(self) -> str:
        return f"<Room {self.floor}-{self.room_no}>"
