"""
［相容層］樓層巡檢圖 v2.10.107 的商場專用模型名稱。

⚠️ 2026-10-04 共用化：mall_floor_map_points 已改名為 floor_map_points（Alembic fmapgen），
   模型移到 app/models/floor_map.py。這裡**不可**再宣告 __tablename__='mall_floor_map_points'
   的模型 —— main.py 啟動時的 create_all 會把舊表重新建出來，變成兩張表各有資料。
"""
from app.models.floor_map import FloorMapPoint as MallFloorMapPoint  # noqa: F401
