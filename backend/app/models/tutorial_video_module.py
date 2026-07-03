"""
教學模組主檔 SQLAlchemy ORM Model
資料表：tutorial_video_modules

每一列代表「影音教學」頁面中的一個模組分組（如「IHG客房保養」），
獨立於個別影片（TutorialVideo）之外管理，避免模組名稱/路由打字不一致，
並讓模組順序可被拖曳排序。

欄位說明：
  category      分類：hotel=飯店管理 | mall=商場管理 | group=集團決策
  module_name   中文模組名稱（建議對應 Portal Menu 顯示名稱，如「IHG客房保養」）
  module_route  對應 Portal 路由（如 /hotel/ihg-room-maintenance），選填、僅供參考
  sort_order    同分類內的顯示順序（拖曳排序寫入此欄位）
"""
import uuid
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from app.core.time import twnow
from app.core.database import Base


def _now():
    return twnow()


def _new_uuid():
    return str(uuid.uuid4())


class TutorialVideoModule(Base):
    __tablename__ = "tutorial_video_modules"

    id            = Column(String(36),  primary_key=True, default=_new_uuid)
    category      = Column(String(20),  nullable=False, default="hotel")   # hotel | mall | group
    module_name   = Column(String(100), nullable=False, default="")
    module_route  = Column(String(200), nullable=False, default="")
    sort_order    = Column(Integer,     nullable=False, default=0)

    created_at    = Column(DateTime,    nullable=False, default=_now)
    updated_at    = Column(DateTime,    nullable=False, default=_now, onupdate=_now)

    videos = relationship(
        "TutorialVideo",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="TutorialVideo.sort_order",
    )
