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
    # 商場 4F：底圖尚未提供，地圖暫時空白；尺寸為佔位值（2026-10-30）
    {"key": "4f", "label": "4F", "width": 2515, "height": 1427, "version": "未提供",
     "source": "（底圖未提供）"},
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
    # B1~B4（抽排風設備）：底圖尚未提供，地圖暫時空白；尺寸為佔位值
    {"key": "b1b4", "label": "B1~B4", "width": 3509, "height": 2481, "version": "未提供",
     "source": "（底圖未提供）"},
]
FLOOR_MAP: dict[str, dict[str, Any]] = {f["key"]: f for f in FLOORS}

# 底圖置換後的尺寸／版本覆寫（由 floor_image_store 寫入；啟動時讀回）
OVERRIDE_FILE = FLOOR_PLAN_DIR / "floor_image_meta.json"


def _apply_image_overrides() -> None:
    import json
    try:
        data = json.loads(OVERRIDE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    for key, ov in data.items():
        if key in FLOOR_MAP:
            for k in ("width", "height", "version"):
                if k in ov:
                    FLOOR_MAP[key][k] = ov[k]


_apply_image_overrides()


def floor_image_path(floor_key: str) -> Path:
    return FLOOR_PLAN_DIR / f"{floor_key}.webp"
