"""
整棟巡檢每日巡檢表（Excel 版型）—— Dashboard「整棟巡檢月曆格」的下一層

版型：#2.3整棟-每日巡檢表.xlsx（services/full_building_inspection_template.py，實際 82 列）
回傳格式與商場工務巡檢 /mall-facility-inspection/daily-sheet 相同，前端共用
pages/MallFacilityInspection/MallFIDailySheetDrawer.tsx。

判定與欄位對應**沿用樓層巡檢圖的整棟巡檢 Provider**
（services/floor_map/providers/full_building_inspection.py：Ragic 無此欄位、異常說明對應、
 沿用 sync 的 result_status 含 measure），兩個畫面同一套邏輯，不會各說各話。

2026-10-05（v2.10.113）：月曆格 ⚠ 也改用這裡的判定（build_full_building_month_issues），
與 Drawer 一致；並比照商場，把「Ragic 有、Excel 版型沒有」的欄位中明確寫出異常字樣的值
列為 extra_issues，不因版型沒有就藏起來。
"""
from __future__ import annotations

import calendar
import re
from typing import Any

from sqlalchemy.orm import Session

from app.services.floor_map.common import batch_out, hhmm
from app.services.floor_map.providers.full_building_inspection import (
    NOTE_FIELD, SHEETS, FullBuildingInspectionProvider,
)
from app.services.full_building_inspection_template import (
    FULL_BUILDING_DAILY_INSPECTION_TEMPLATE as TEMPLATE,
    STANDARD_MINUTES_MORNING, STANDARD_MINUTES_TOTAL,
)
from app.services.inspection_field_rules import is_equipment_field

_TABS = list(dict.fromkeys(t["source_tab"] for t in TEMPLATE))          # rf, b1f, b2f, b4f（Excel 順序）
_FLOOR_LABEL = {t["source_tab"]: t["floor"] for t in TEMPLATE}

# 版型內欄位（檢查內容與 Ragic 欄名同名）＋各組異常說明欄
_REFERENCED: dict[str, set[str]] = {tab: set() for tab in _TABS}
for _t in TEMPLATE:
    _REFERENCED[_t["source_tab"]].add(_t["check_content"])
for (_tab, _item), _f in NOTE_FIELD.items():
    _REFERENCED.setdefault(_tab, set()).add(_f)

# 版型外欄位只在值明確寫出異常字樣時才算（與商場 mall_daily_inspection_sheet 相同規則）
_EXPLICIT_ISSUE_RE = re.compile(r"異常|待處理|待修|故障|損壞|不良|^[Xx]$")


def _extra_issues(tab: str, batches: list[Any], values: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    multi = len(batches) > 1
    refs = _REFERENCED.get(tab, set())
    out: list[dict[str, Any]] = []
    for b in batches:
        for name, it in values.get(b.ragic_id, {}).items():
            raw = (it.result_raw or "").strip()
            if not raw or name in refs or not is_equipment_field(name, raw):
                continue
            if any(w in name for w in ("說明", "備註")):
                continue
            if it.result_status in ("abnormal", "pending") and _EXPLICIT_ISSUE_RE.search(raw):
                out.append({
                    "source_tab": tab,
                    "floor":      _FLOOR_LABEL[tab],
                    "field":      name,
                    "status":     it.result_status,
                    "text":       raw,
                    "time_label": hhmm(b.start_time or "") if multi else "",
                })
    return out


def _build(insp_date: str, loaded: dict[str, tuple[list[Any], dict[str, dict[str, Any]]]]) -> dict[str, Any]:
    prov = FullBuildingInspectionProvider()

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

    extra: list[dict[str, Any]] = []
    for tab in _TABS:
        extra += _extra_issues(tab, *loaded[tab])

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
            "extra_issues":        len(extra),
        },
        "extra_issues": extra,
    }


def build_full_building_daily_sheet(db: Session, insp_date: str) -> dict[str, Any]:
    loaded = {
        tab: FullBuildingInspectionProvider._load(db, tab, lambda B: B.inspection_date == insp_date)
        for tab in _TABS
    }
    return _build(insp_date, loaded)


def day_issues(sheet: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """每日巡檢表結果 → {樓層 tab: [異常／待處理項目]}（月曆格 ⚠ 與 Tooltip 用；欄位與商場相同）。"""
    out: dict[str, list[dict[str, Any]]] = {tab: [] for tab in _TABS}
    for r in sheet["rows"]:
        if r["abnormal"]:
            out[r["source_tab"]].append({
                "source_tab":    r["source_tab"],
                "floor":         r["floor"],
                "item":          r["item"],
                "check_content": r["check_content"],
                "status":        r["status"],
                "note":          r["abnormal_note"],
                "in_template":   True,
            })
    for x in sheet.get("extra_issues", []):
        out[x["source_tab"]].append({
            "source_tab":    x["source_tab"],
            "floor":         x["floor"],
            "item":          "版型外欄位",
            "check_content": x["field"],
            "status":        x["status"],
            "note":          (f"[{x['time_label']}] " if x["time_label"] else "") + x["text"],
            "in_template":   False,
        })
    return out


def build_full_building_month_issues(db: Session, year: int, month: int) -> dict[int, dict[str, list[dict[str, Any]]]]:
    """{日: {樓層 tab: [異常／待處理項目]}}，一個樓層整月只查一次。"""
    prefix = f"{year}/{month:02d}/"
    month_loaded = {
        tab: FullBuildingInspectionProvider._load(db, tab, lambda B: B.inspection_date.like(f"{prefix}%"))
        for tab in _TABS
    }
    out: dict[int, dict[str, list[dict[str, Any]]]] = {}
    for d in range(1, calendar.monthrange(year, month)[1] + 1):
        date_str = f"{prefix}{d:02d}"
        loaded = {}
        for tab, (batches, values) in month_loaded.items():
            bl = [b for b in batches if b.inspection_date == date_str]
            loaded[tab] = (bl, {b.ragic_id: values.get(b.ragic_id, {}) for b in bl})
        if any(bl for bl, _v in loaded.values()):
            out[d] = day_issues(_build(date_str, loaded))
    return out
