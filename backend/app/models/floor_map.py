"""
樓層巡檢圖（共用）— 點位 ORM 模型

規格：docs/DEV_SPEC_floor_plan_map.md（§4）
所有模組的點位都在這張表，以 module 欄位區分；底圖不在 DB（backend/static/floor_plans/）。

⚠️ 2026-10-04 由 mall_floor_map_points 改名而來（Alembic fmapgen）。
   sheet_key／item／location_desc／supply_area 是商場第一版的舊欄位，
   CLAUDE.md §5 不可移除欄位 → 保留但不再寫入；新資料一律用 source_ref／attrs。
"""
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Index, Integer, String

from app.core.database import Base
from app.core.time import twnow

PLACEMENTS = ("confirmed", "draft", "pending")   # 已校正／草稿概估／待定位


class FloorMapPoint(Base):
    __tablename__ = "floor_map_points"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    module         = Column(String(50),  nullable=False, comment="模組代碼＝Provider.module")
    floor_key      = Column(String(20),  nullable=False, comment="底圖 key：b4f～b1f、1f～10f、rf")
    x              = Column(Float,       nullable=False, comment="比例座標 0～1（左→右）")
    y              = Column(Float,       nullable=False, comment="比例座標 0～1（上→下）")
    label          = Column(String(100), nullable=False, comment="顯示名稱")
    equipment_code = Column(String(50),  nullable=True,  comment="設備編號")
    source_ref     = Column(String(200), nullable=False, comment="資料來源參照，格式由 Provider 定義")
    placement      = Column(String(20),  nullable=False, default="confirmed", comment="confirmed／draft／pending")
    attrs          = Column(JSON(none_as_null=True), nullable=True,  comment="模組自訂屬性（如機房位置、供應區域）")
    note           = Column(String(300), nullable=True,  comment="備註")
    sort_order     = Column(Integer,     nullable=False, default=0)
    is_active      = Column(Boolean,     nullable=False, default=True)
    created_by     = Column(String(100), nullable=True)
    updated_by     = Column(String(100), nullable=True)
    created_at     = Column(DateTime,    nullable=False, default=twnow)
    updated_at     = Column(DateTime,    nullable=False, default=twnow, onupdate=twnow)

    # ── 商場第一版舊欄位（保留、不再寫入）──────────────────────────────────
    sheet_key      = Column(String(20),  nullable=True, comment="[舊] 商場 Sheet key，已併入 source_ref")
    item           = Column(String(50),  nullable=True, comment="[舊] 商場設備組，已併入 source_ref")
    location_desc  = Column(String(100), nullable=True, comment="[舊] 機房位置，已併入 attrs")
    supply_area    = Column(String(200), nullable=True, comment="[舊] 供應區域，已併入 attrs")

    __table_args__ = (
        Index("ix_floor_map_points_module_floor", "module", "floor_key", "is_active"),
    )
