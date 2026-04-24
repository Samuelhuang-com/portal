"""
樂群工務報修案件 ORM Model
對應 Ragic: ap12.ragic.com/soutlet001/luqun-public-works-repair-reporting-system/6

與 DazhiRepairCase 相比多了：
  - deduction_counter（扣款專櫃）
  - occ_year / occ_month（報修月份，4.1 統計用）
"""
from datetime import datetime
from app.core.time import twnow
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base


class LuqunRepairCase(Base):
    __tablename__ = "luqun_repair_case"

    ragic_id:          Mapped[str]   = mapped_column(String(50),  primary_key=True)
    case_no:           Mapped[str]   = mapped_column(String(100), default="")
    title:             Mapped[str]   = mapped_column(Text,        default="")
    reporter_name:     Mapped[str]   = mapped_column(String(100), default="")
    repair_type:       Mapped[str]   = mapped_column(String(50),  default="")
    floor:             Mapped[str]   = mapped_column(String(100), default="")
    floor_normalized:  Mapped[str]   = mapped_column(String(30),  default="")
    occurred_at:       Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    responsible_unit:  Mapped[str]   = mapped_column(String(100), default="")
    work_hours:        Mapped[float] = mapped_column(Float,       default=0.0)
    status:            Mapped[str]   = mapped_column(String(50),  default="")
    outsource_fee:     Mapped[float] = mapped_column(Float,       default=0.0)
    maintenance_fee:   Mapped[float] = mapped_column(Float,       default=0.0)
    total_fee:         Mapped[float] = mapped_column(Float,       default=0.0)
    deduction_item:         Mapped[str]   = mapped_column(String(200), default="")
    deduction_fee:          Mapped[float] = mapped_column(Float,       default=0.0)
    deduction_counter:      Mapped[float] = mapped_column(Float,       default=0.0)  # 保持 0
    deduction_counter_name: Mapped[str]   = mapped_column(String(200), default="")   # 扣款專櫃名稱
    acceptor:               Mapped[str]   = mapped_column(String(100), default="")
    accept_status:          Mapped[str]   = mapped_column(String(200), default="")
    closer:                 Mapped[str]   = mapped_column(String(100), default="")
    finance_note:           Mapped[str]   = mapped_column(Text,        default="")
    mgmt_response:          Mapped[str]   = mapped_column(Text,        default="")   # 管理單位回應
    is_completed:      Mapped[bool]  = mapped_column(Boolean,     default=False)
    completed_at:      Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    close_days:        Mapped[float | None]    = mapped_column(Float, nullable=True)
    year:              Mapped[int | None]      = mapped_column(Integer, nullable=True)
    month:             Mapped[int | None]      = mapped_column(Integer, nullable=True)
    occ_year:          Mapped[int | None]      = mapped_column(Integer, nullable=True)   # 樂群專用
    occ_month:         Mapped[int | None]      = mapped_column(Integer, nullable=True)   # 樂群專用
    is_room_case:      Mapped[bool]  = mapped_column(Boolean,     default=False)
    room_no:           Mapped[str]   = mapped_column(String(20),  default="")
    room_category:     Mapped[str]   = mapped_column(String(50),  default="")
    synced_at:         Mapped[datetime] = mapped_column(DateTime, default=twnow)

    @property
    def is_completed_flag(self) -> bool:
        """有完工時間（completed_at）即視為已完工；亦兼顧狀態欄位判斷"""
        return (self.completed_at is not None) or self.is_completed

    def _get_counter_stores(self) -> list[str]:
        """計算扣款專櫃列表（供 compute_dashboard 使用）"""
        from app.services.luqun_repair_service import _parse_counter_stores
        return _parse_counter_stores(self.deduction_counter_name or "", self.finance_note or "")

    @property
    def counter_stores(self) -> list[str]:
        return self._get_counter_stores()

    @property
    def is_excluded_flag(self) -> bool:
        """RepairCase 相容屬性：排除「取消」等不計入統計的案件"""
        return self.status.strip() in {"取消"}

    def to_dict(self) -> dict:
        """轉換為 API 回傳用 dict（與 RepairCase.to_dict 介面相同）"""
        from datetime import datetime as _dt
        return {
            "ragic_id":               self.ragic_id,
            "case_no":                self.case_no,
            "title":                  self.title,
            "reporter_name":          self.reporter_name,
            "repair_type":            self.repair_type,
            "floor":                  self.floor,
            "floor_normalized":       self.floor_normalized,
            "occurred_at":            self.occurred_at.strftime("%Y/%m/%d %H:%M") if self.occurred_at else "",
            "responsible_unit":       self.responsible_unit,
            "work_hours":             self.work_hours,
            "status":                 self.status,
            "outsource_fee":          self.outsource_fee,
            "maintenance_fee":        self.maintenance_fee,
            "total_fee":              self.total_fee,
            "acceptor":               self.acceptor,
            "accept_status":          self.accept_status,
            "closer":                 self.closer,
            "deduction_item":         self.deduction_item,
            "deduction_fee":          self.deduction_fee,
            "deduction_counter":      self.deduction_counter,
            "deduction_counter_name": self.deduction_counter_name or "",
            "counter_stores":         self._get_counter_stores(),
            "mgmt_response":          self.mgmt_response or "",
            "finance_note":           self.finance_note,
            "is_completed":           self.is_completed_flag,
            "is_excluded":            self.is_excluded_flag,
            "completed_at":           self.completed_at.strftime("%Y/%m/%d") if self.completed_at else "",
            "close_days":             self.close_days,
            "pending_days": (
                round((_dt.now() - self.occurred_at).total_seconds() / 86400)
                if (self.completed_at is None and self.occurred_at)
                else None
            ),
            "year":               self.year,
            "month":              self.month,
            "occ_year":           self.occ_year,
            "occ_month":          self.occ_month,
            "is_room_case":       self.is_room_case,
            "room_no":            self.room_no,
            "room_category":      self.room_category,
            "images":             [],
        }
