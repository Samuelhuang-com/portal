"""
影音教學（單集影片）SQLAlchemy ORM Model
資料表：tutorial_videos

本模組為 Portal 本地內容（不對接 Ragic、不經 sync 模組）。
影片檔案直接存於後端伺服器本機檔案系統（backend/uploads/tutorial_videos/），
資料庫僅保存中繼資料與檔名。

每一支影片隸屬於一個 TutorialVideoModule（教學模組主檔），
分類（category）／模組名稱／模組路由都改由該主檔管理，
此表只保留「集」這個層級的資訊。

欄位說明：
  module_id     所屬模組（tutorial_video_modules.id）
  episode       集數標籤（如 EP01），字串以保留前導 0
  title         集標題
  description   說明文字（選填）
  video_stored_name / video_orig_name / video_size_bytes / video_content_type
                影片檔案（mp4）
  script_stored_name / script_orig_name
                TTS 逐字稿（txt），選填
  sort_order    同模組內的集數顯示順序（拖曳排序寫入此欄位）
  uploaded_by   上傳者 full_name
  created_at / updated_at
"""
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.core.time import twnow
from app.core.database import Base


def _now():
    return twnow()


def _new_uuid():
    return str(uuid.uuid4())


class TutorialVideo(Base):
    __tablename__ = "tutorial_videos"

    id                  = Column(String(36),  primary_key=True, default=_new_uuid)
    module_id           = Column(String(36),  ForeignKey("tutorial_video_modules.id", ondelete="CASCADE"), nullable=False)
    episode             = Column(String(20),  nullable=False, default="")
    title               = Column(String(255), nullable=False, default="")
    description         = Column(Text,        nullable=False, default="")

    video_stored_name   = Column(String(255), nullable=False, default="")
    video_orig_name     = Column(String(255), nullable=False, default="")
    video_size_bytes    = Column(Integer,     nullable=False, default=0)
    video_content_type  = Column(String(100), nullable=False, default="video/mp4")

    script_stored_name  = Column(String(255), nullable=False, default="")
    script_orig_name    = Column(String(255), nullable=False, default="")

    sort_order          = Column(Integer,     nullable=False, default=0)
    uploaded_by         = Column(String(100), nullable=False, default="")

    created_at          = Column(DateTime,    nullable=False, default=_now)
    updated_at          = Column(DateTime,    nullable=False, default=_now, onupdate=_now)

    module = relationship("TutorialVideoModule", back_populates="videos")
