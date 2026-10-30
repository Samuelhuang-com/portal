"""
樓層底圖置換：格式轉換後寫入（2026-10-30）

- 支援 WebP／PNG／JPG／PDF（PDF 可指定頁碼與 DPI），一律轉成 WebP 存放。
- 寫入流程：tmp → 舊圖改名為 {key}.webp.prev → tmp 改名為 {key}.webp，避免寫到一半的檔案被讀取。
- 尺寸與版本寫入 static/floor_plans/floor_image_meta.json，registry 啟動時讀回。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from app.services.floor_map.floor_image_convert import convert_to_webp
from app.services.floor_map.registry import FLOOR_MAP, FLOOR_PLAN_DIR, OVERRIDE_FILE, floor_image_path

MAX_BYTES = 40 * 1024 * 1024


def _load_overrides() -> dict[str, Any]:
    try:
        return json.loads(OVERRIDE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def replace_floor_image(
    floor_key: str,
    data: bytes,
    uploaded_by: str,
    page: int = 1,
    dpi: int = 150,
) -> dict[str, Any]:
    result = convert_to_webp(data, page=page, dpi=dpi)   # 可能丟 UnsupportedFormat／ConverterUnavailable

    FLOOR_PLAN_DIR.mkdir(parents=True, exist_ok=True)
    path = floor_image_path(floor_key)
    tmp = path.with_suffix(".webp.tmp")
    prev = path.with_suffix(".webp.prev")
    tmp.write_bytes(result.webp)
    if path.exists():
        os.replace(path, prev)
    os.replace(tmp, path)

    now = datetime.now()
    version = f"上傳 {now.strftime('%Y%m%d')}"
    overrides = _load_overrides()
    overrides[floor_key] = {
        "width": result.width, "height": result.height, "version": version,
        "uploaded_at": now.isoformat(timespec="seconds"), "uploaded_by": uploaded_by,
        "source_format": result.source_format,
        "page": result.page, "page_count": result.page_count,
    }
    OVERRIDE_FILE.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")
    FLOOR_MAP[floor_key].update(width=result.width, height=result.height, version=version)
    return {
        "key": floor_key, "width": result.width, "height": result.height, "version": version,
        "source_format": result.source_format, "page": result.page, "page_count": result.page_count,
    }
