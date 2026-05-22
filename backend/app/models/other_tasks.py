"""
主管交辦／緊急事件 ORM Model
對應 Ragic: ap12.ragic.com/soutlet001/other-tasks/1

屬性欄位決定分類：
  "上級交辦" → 主管交辦 TAB
  "緊急事件" → 緊急事件 TAB
"""
import json
from datetime import datetime
from app.core.time import twnow
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base


class OtherTask(Base):
    __tablename__ = "other_task"

    ragic_id:    Mapped[str]           = mapped_column(String(50),   primary_key=True)
    task_type:   Mapped[str]           = mapped_column(String(50),   default="")   # 屬性: 上級交辦 / 緊急事件
    supervisor:  Mapped[str]           = mapped_column(String(100),  default="")   # 交辦主管
    engineer:    Mapped[str]           = mapped_column(String(100),  default="")   # 工程人員
    created_at:  Mapped[datetime|None] = mapped_column(DateTime,     nullable=True)  # 建立日期
    description: Mapped[str]           = mapped_column(Text,         default="")   # 問題說明
    notes:       Mapped[str]           = mapped_column(Text,         default="")   # 備註
    updated_at:  Mapped[datetime|None] = mapped_column(DateTime,     nullable=True)  # 最後更新日期
    status:      Mapped[str]           = mapped_column(String(50),   default="")   # 狀態
    work_hours:  Mapped[float|None]    = mapped_column(Float,        nullable=True)  # 維修工時
    year:        Mapped[int|None]      = mapped_column(Integer,      nullable=True)
    month:       Mapped[int|None]      = mapped_column(Integer,      nullable=True)
    venue:       Mapped[str]           = mapped_column(String(50),   default="")   # 歸屬: 飯店 / 商場
    images_json: Mapped[str|None]      = mapped_column(Text,         nullable=True, default=None)  # 附圖 JSON
    synced_at:   Mapped[datetime]      = mapped_column(DateTime,     default=twnow)

    def _parse_images(self) -> list:
        if not self.images_json:
            return []
        try:
            return json.loads(self.images_json)
        except Exception:
            return []

    def to_dict(self) -> dict:
        ragic_url = (
            f"https://ap12.ragic.com/soutlet001/other-tasks/1/{self.ragic_id}"
            if self.ragic_id else ""
        )
        created_str = self.created_at.strftime("%Y/%m/%d %H:%M") if self.created_at else ""
        updated_str = self.updated_at.strftime("%Y/%m/%d %H:%M") if self.updated_at else ""
        return {
            "ragic_id":    self.ragic_id,
            "ragic_url":   ragic_url,
            "task_type":   self.task_type,
            "supervisor":  self.supervisor,
            "engineer":    self.engineer,
            "created_at":  created_str,
            "description": self.description,
            "notes":       self.notes,
            "updated_at":  updated_str,
            "status":      self.status,
            "work_hours":  self.work_hours,
            "year":        self.year,
            "month":       self.month,
            "venue":       self.venue,
            "images":      self._parse_images(),
            "detail": {
                "歸屬":         self.venue,
                "屬性":         self.task_type,
                "交辦主管":     self.supervisor,
                "工程人員":     self.engineer,
                "建立日期":     created_str,
                "問題說明":     self.description,
                "備註":         self.notes,
                "最後更新日期": updated_str,
                "狀態":         self.status,
                "維修工時":     f"{self.work_hours:.2f}" if self.work_hours is not None else "",
            },
        }
