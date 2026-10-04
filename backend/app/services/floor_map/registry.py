"""
樓層巡檢圖 — 底圖登錄表（全站共用，DEV_SPEC §3）

底圖：backend/static/floor_plans/{key}.webp，由 Temp/build_floor_plan_images.py 產生。
⚠️ width／height 必須等於 webp 實際尺寸（前端用來設 Leaflet 座標範圍）。
⚠️ 同一層樓全站只有一張圖；新增樓層時只改這裡與產生工具，不要在模組裡另放。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

FLOOR_PLAN_DIR = Path(__file__).resolve().parents[3] / "static" / "floor_plans"

# 依實體樓層由上而下排序
FLOORS: list[dict[str, Any]] = [
    {"key": "rf",  "label": "RF",  "width": 2184, "height": 2527, "version": "建照圖",
     "source": "頂樓平面圖-建照圖.pdf"},
    {"key": "3f",  "label": "3F",  "width": 2515, "height": 1427, "version": "202504",
     "source": "202504_春大直-3F-全區平面圖 -公清.pdf"},
    {"key": "2f",  "label": "2F",  "width": 2184, "height": 1777, "version": "202504",
     "source": "202504-春大直-2F-全區平面圖 -公清.pdf"},
    {"key": "1f",  "label": "1F",  "width": 2928, "height": 2222, "version": "202504",
     "source": "202504-春大直-1F-全區平面圖 - 公清.pdf"},
    {"key": "b1f", "label": "B1F", "width": 3509, "height": 2481, "version": "202504",
     "source": "202504-春大直-B1F~B4F-全區平面圖-公清.pdf p1"},
    {"key": "b2f", "label": "B2F", "width": 3509, "height": 2481, "version": "202504",
     "source": "202504-春大直-B1F~B4F-全區平面圖-公清.pdf p2"},
    {"key": "b3f", "label": "B3F", "width": 3509, "height": 2481, "version": "202504",
     "source": "202504-春大直-B1F~B4F-全區平面圖-公清.pdf p3"},
    {"key": "b4f", "label": "B4F", "width": 3509, "height": 2481, "version": "202504",
     "source": "202504-春大直-B1F~B4F-全區平面圖-公清.pdf p4"},
]
FLOOR_MAP: dict[str, dict[str, Any]] = {f["key"]: f for f in FLOORS}


def floor_image_path(floor_key: str) -> Path:
    return FLOOR_PLAN_DIR / f"{floor_key}.webp"
