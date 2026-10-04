"""
樓層巡檢圖（Floor Plan Inspection Map）服務

- FLOORS：樓層與底圖（backend/static/floor_plans/{key}.webp，由 Temp/build_floor_plan_images.py 產生）
- EQUIPMENT_GROUPS：點位可對應的 Ragic 設備組（＝ 2.2 每日巡檢表的 source_tab＋項目）
- 單日／整月狀態：一律經 mall_daily_inspection_sheet.build_daily_sheet 計算，
  與「每日巡檢表」Drawer 同一套判定（正常／異常、溫濕度不判異常、異常說明對應），不另寫一套。

規格：docs/SPEC_floor_plan_inspection.md
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.mall_facility_inspection import MallFIBatch, MallFIItem
from app.services.mall_daily_inspection_sheet import EXCEL_FLOOR_LABEL, build_daily_sheet

FLOOR_PLAN_DIR = Path(__file__).resolve().parents[2] / "static" / "floor_plans"

# width／height 必須與 webp 實際尺寸一致（前端用來設 Leaflet 座標範圍）
FLOORS: list[dict[str, Any]] = [
    {"key": "1f",  "label": "1F",  "width": 2928, "height": 2222, "version": "202504"},
    {"key": "2f",  "label": "2F",  "width": 2184, "height": 1777, "version": "202504"},
    {"key": "3f",  "label": "3F",  "width": 2515, "height": 1427, "version": "202504"},
    {"key": "b1f", "label": "B1F", "width": 3509, "height": 2481, "version": "202504"},
    {"key": "b2f", "label": "B2F", "width": 3509, "height": 2481, "version": "202504"},
    {"key": "b3f", "label": "B3F", "width": 3509, "height": 2481, "version": "202504"},
    {"key": "b4f", "label": "B4F", "width": 3509, "height": 2481, "version": "202504"},
]
FLOOR_KEYS = {f["key"] for f in FLOORS}

# system：上方「依系統篩選」用
EQUIPMENT_GROUPS: list[dict[str, str]] = [
    {"sheet_key": "1f-3f",   "item": "空調箱",     "system": "空調"},
    {"sheet_key": "3f",      "item": "靜電機",     "system": "油煙處理"},
    {"sheet_key": "1f",      "item": "水洗機",     "system": "油煙處理"},
    {"sheet_key": "b1f-b4f", "item": "抽排風設備", "system": "排風"},
    {"sheet_key": "b1f-b4f", "item": "電信設備",   "system": "電信"},
]
_GROUP_SET = {(g["sheet_key"], g["item"]) for g in EQUIPMENT_GROUPS}

# 一個 Ragic Sheet 涵蓋多層 → 點位結果是共用的
SHARED_LABEL: dict[str, str] = {
    "1f-3f":   "1F~3F 共用一筆",
    "b1f-b4f": "B1~B4 共用一筆",
}


def group_key(sheet_key: str, item: str) -> str:
    return f"{sheet_key}|{item}"


def is_valid_group(sheet_key: str, item: str) -> bool:
    return (sheet_key, item) in _GROUP_SET


def group_meta(sheet_key: str, item: str) -> dict[str, str]:
    for g in EQUIPMENT_GROUPS:
        if g["sheet_key"] == sheet_key and g["item"] == item:
            return {
                **g,
                "key":          group_key(sheet_key, item),
                "sheet_label":  EXCEL_FLOOR_LABEL.get(sheet_key, sheet_key),
                "shared_label": SHARED_LABEL.get(sheet_key, ""),
            }
    return {"sheet_key": sheet_key, "item": item, "system": "", "key": group_key(sheet_key, item),
            "sheet_label": EXCEL_FLOOR_LABEL.get(sheet_key, sheet_key), "shared_label": ""}


def merge_group_status(rows: list[dict[str, Any]], has_record: bool) -> str:
    """
    一個設備組（多列檢查內容）合併成一個點位顏色：
      no_record ：當日該 Sheet 沒有任何場次
      abnormal  ：任一列異常／待處理
      unchecked ：有場次但有列未填
      normal    ：其餘（含溫濕度等填數字的列）
    「Ragic 無此欄位」「另作表單」的列不列入判定。
    """
    if not has_record:
        return "no_record"
    judged = [r for r in rows if r["kind"] in ("status", "reading")]
    if any(r["abnormal"] for r in judged):
        return "abnormal"
    if any(r["status"] == "unchecked" for r in judged):
        return "unchecked"
    return "normal"


def _load(db: Session, date_filter) -> tuple[list[MallFIBatch], dict[str, list[MallFIItem]]]:
    batches = db.query(MallFIBatch).filter(date_filter).all()
    items: dict[str, list[MallFIItem]] = {b.ragic_id: [] for b in batches}
    if batches:
        for it in db.query(MallFIItem).filter(MallFIItem.batch_ragic_id.in_(list(items))).all():
            items.setdefault(it.batch_ragic_id, []).append(it)
    return batches, items


def day_groups(db: Session, insp_date: str) -> dict[str, dict[str, Any]]:
    """指定日期（YYYY/MM/DD）每個設備組的狀態、檢查列與場次資訊。"""
    batches, items = _load(db, MallFIBatch.inspection_date == insp_date)
    sheet = build_daily_sheet(batches, items)
    floors = {f["key"]: f for f in sheet["floors"]}

    out: dict[str, dict[str, Any]] = {}
    for g in EQUIPMENT_GROUPS:
        sk, item = g["sheet_key"], g["item"]
        rows = [r for r in sheet["rows"] if r["source_tab"] == sk and r["item"] == item]
        fl = floors.get(sk, {})
        out[group_key(sk, item)] = {
            **group_meta(sk, item),
            "status":         merge_group_status(rows, bool(fl.get("has_record"))),
            "rows":           rows,
            "batches":        fl.get("batches", []),
            "inspectors":     fl.get("inspectors", []),
            "actual_minutes": fl.get("actual_minutes", 0),
        }
    return out


def month_group_days(db: Session, sheet_key: str, item: str, year: int, month: int) -> list[dict[str, Any]]:
    """某設備組整月每日狀態（右側「本月每日狀況」格）。"""
    prefix = f"{year}/{month:02d}/"
    batches, items = _load(
        db,
        (MallFIBatch.sheet_key == sheet_key) & (MallFIBatch.inspection_date.like(f"{prefix}%")),
    )
    by_day: dict[str, list[MallFIBatch]] = defaultdict(list)
    for b in batches:
        by_day[b.inspection_date].append(b)

    days = []
    for d in range(1, calendar.monthrange(year, month)[1] + 1):
        date_str = f"{prefix}{d:02d}"
        bl = by_day.get(date_str, [])
        if not bl:
            days.append({"day": d, "date": date_str, "status": "no_record", "abnormal_rows": 0})
            continue
        sheet = build_daily_sheet(bl, {b.ragic_id: items.get(b.ragic_id, []) for b in bl})
        rows = [r for r in sheet["rows"] if r["source_tab"] == sheet_key and r["item"] == item]
        days.append({
            "day":           d,
            "date":          date_str,
            "status":        merge_group_status(rows, True),
            "abnormal_rows": sum(1 for r in rows if r["abnormal"]),
        })
    return days
