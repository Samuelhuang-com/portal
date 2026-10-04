"""
樓層巡檢圖（共用）服務套件 —— 規格 docs/DEV_SPEC_floor_plan_map.md

  registry.py   底圖登錄表（全站共用）
  common.py     共用小工具（時間解析、狀態合併、Ragic 連結）
  service.py    點位 CRUD、單日狀態、整月狀態（所有模組共用）
  providers/    各模組的資料提供者（Provider）；新模組只需新增一支並註冊
"""
