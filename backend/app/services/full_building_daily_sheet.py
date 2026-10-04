"""
整棟巡檢每日巡檢表（Excel 版型）—— Dashboard「整棟巡檢月曆格」的下一層

版型：#2.3整棟-每日巡檢表.xlsx（services/full_building_inspection_template.py，65 列）
回傳格式與商場工務巡檢 /mall-facility-inspection/daily-sheet 相同，前端共用
pages/MallFacilityInspection/MallFIDailySheetDrawer.tsx。

判定與欄位對應**沿用樓層巡檢圖的整棟巡檢 Provider**
（services/floor_map/providers/full_building_inspection.py：Ragic 無此欄位、異常說明對應、
 沿用 sync 的 result_status 含 measure），兩個畫面同一套邏輯，不會各說各話。
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.floor_map.common import batch_out
from app.services.floor_map.providers.full_building_inspection import (
    SHEETS, FullBuildingInspectionProvider,
)
from app.services.full_building_inspection_template import (
    FULL_BUILDING_DAILY_INSPECTION_TEMPLATE as TEMPLATE,
    STANDARD_MINUTES_MORNING, STANDARD_MINUTES_TOTAL,
)

_TABS = list(dict.fromkeys(t["source_tab"] for t in TEMPLATE))          # rf, b1f, b2f, b4f（Excel 順序）
_FLOOR_LABEL = {t["source_tab"]: t["floor"] for t in TEMPLATE}


def build_full_building_daily_sheet(db: Session, insp_date: str) -> dict[str, Any]:
    prov = FullBuildingInspectionProvider()
    loaded = {tab: prov._load(db, tab, lambda B: B.inspection_date == insp_date) for tab in _TABS}

    floors = []
    for tab in _TABS:
        batches, _values = loaded[tab]
        path = SHEETS[tab][2]
        bo = [batch_out(path, b.ragic_id, b) for b in batches]
        floors.append({
            "key":            tab,
            "floor":          _FLOOR_LABEL[tab],
            "sheet_url":      f"https://ap12.ragic.com/soutlet001/{path}",
            "has_record":     bool(batches),
            "inspectors":     list(dict.fromkeys(x["inspector"] for x in bo if x["inspector"])),
            "batches":        bo,
            "actual_minutes": sum(x["actual_minutes"] for x in bo),
        })

    rows: list[dict[str, Any]] = []
    cnt = {"normal": 0, "abnormal": 0, "pending": 0, "unchecked": 0, "reading": 0}
    for tab, item in dict.fromkeys((t["source_tab"], t["item"]) for t in TEMPLATE):
        tmpl = [t for t in TEMPLATE if t["source_tab"] == tab and t["item"] == item]
        grows = prov._rows(tab, item, *loaded[tab])
        for t, g in zip(tmpl, grows):
            st = g["status"]
            key = "reading" if st == "measure" else st
            if key in cnt:
                cnt[key] += 1
            rows.append({**t, **g, "remark": ""})

    return {
        "date":   insp_date,
        "floors": floors,
        "rows":   rows,
        "summary": {
            "floors_total":        len(floors),
            "floors_logged":       sum(1 for f in floors if f["has_record"]),
            **cnt,
            "std_minutes_routine": STANDARD_MINUTES_MORNING,
            "std_minutes_total":   STANDARD_MINUTES_TOTAL,
            "actual_minutes":      sum(f["actual_minutes"] for f in floors),
            "shift_times":         [],
            # Excel #2.3 底部的時間列（模板常數，照 Excel 原文）
            "footer": [
                {"text": "早班巡檢時間", "minutes": STANDARD_MINUTES_MORNING, "note": "早班"},
                {"text": "整體巡檢時間（1H20分）", "minutes": STANDARD_MINUTES_TOTAL, "note": "早班＋晚班"},
            ],
        },
    }
