"""
［已停用］樓層巡檢圖 v2.10.107 的商場專用服務。

⚠️ 2026-10-04 共用化後已無任何程式 import 這支（CLAUDE.md §12、docs/DEV_SPEC_floor_plan_map.md）：
   - 樓層登錄表 → app/services/floor_map/registry.py
   - 商場判定   → app/services/floor_map/providers/mall_facility_inspection.py
   - 點位 CRUD  → app/services/floor_map/service.py
   保留檔名只為避免外部腳本 import 失敗；請勿再新增程式碼到這裡。
"""
from app.services.floor_map.registry import FLOOR_MAP, FLOOR_PLAN_DIR, FLOORS  # noqa: F401
