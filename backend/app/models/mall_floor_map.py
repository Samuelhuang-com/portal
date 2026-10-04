"""
樓層巡檢圖（Floor Plan Inspection Map）— SQLAlchemy ORM 模型

中文名稱：樓層巡檢圖
英文名稱：Floor Plan Inspection Map
前端路由：/mall-facility-inspection/dashboard?tab=floor-map（商場工務巡檢的 TAB）
後端 router：app/routers/mall_floor_map.py   （prefix /api/v1/mall-floor-map）
對應 Excel：2.2商場-每日巡檢表.xlsx（檢查項目）
            20261003飯店及商場空調設備位置及供應區域.xlsx（設備機房位置，初始草稿點位）
規格文件：docs/SPEC_floor_plan_inspection.md

設計重點（2026-10-04 使用者裁示）
────────────────────────────────────────────────────────────────────────────
1. 底圖不進資料庫：底圖是 backend/static/floor_plans/{floor_key}.webp（進版控），
   樓層清單寫在 services/mall_floor_map_service.FLOORS。只有「點位」存 DB。
2. 座標存比例（0～1，左上角為原點），換新版底圖只要外框不變，點位不會跑掉。
3. 點位 = 「實體設備」，資料來源 = Ragic 的「設備組」（sheet_key + item，
   即 2.2 每日巡檢表的 source_tab + 項目）。同一設備組可以有多個點位
   （例如 1F~3F 的 11 台空調箱都對到 Ragic 1F~3F 表的同一組欄位），
   畫面上會標「共用」——這是 Ragic 粒度限制，不是 bug。
4. 刪除＝停用（is_active=False），不硬刪，保留誰在何時動過。

⚠️ PostgreSQL、Alembic migration：alembic/versions/20261004_mflmap_mall_floor_map_points.py
⚠️ 時間一律用 app.core.time.twnow()。
"""
from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String

from app.core.database import Base
from app.core.time import twnow


class MallFloorMapPoint(Base):
    __tablename__ = "mall_floor_map_points"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    floor_key      = Column(String(20),  nullable=False, comment="樓層 key：1f / 2f / 3f / b1f / b2f / b3f / b4f")
    x              = Column(Float,       nullable=False, comment="水平位置比例 0～1（左→右）")
    y              = Column(Float,       nullable=False, comment="垂直位置比例 0～1（上→下）")
    label          = Column(String(100), nullable=False, comment="顯示名稱，例：AH-R33 空調箱")
    equipment_code = Column(String(50),  nullable=True,  comment="設備編號，例：AH-R33")
    sheet_key      = Column(String(20),  nullable=False, comment="Ragic 來源 Sheet（mall_fi_inspection_batch.sheet_key）")
    item           = Column(String(50),  nullable=False, comment="設備組（2.2 每日巡檢表的「項目」），例：空調箱")
    location_desc  = Column(String(100), nullable=True,  comment="機房位置（空調設備位置表）")
    supply_area    = Column(String(200), nullable=True,  comment="供應區域（空調設備位置表）")
    note           = Column(String(300), nullable=True,  comment="備註")
    sort_order     = Column(Integer,     nullable=False, default=0)
    is_active      = Column(Boolean,     nullable=False, default=True)
    created_by     = Column(String(100), nullable=True)
    updated_by     = Column(String(100), nullable=True)
    created_at     = Column(DateTime,    nullable=False, default=twnow)
    updated_at     = Column(DateTime,    nullable=False, default=twnow, onupdate=twnow)

    __table_args__ = (
        Index("ix_mall_floor_map_points_floor", "floor_key", "is_active"),
    )
