"""
樓層巡檢圖 Provider — 商場工務巡檢（mall_facility_inspection）

資料：mall_fi_inspection_batch／item（Ragic mall-facility-inspection/2,3,4,5,7）
判定：沿用 services/mall_daily_inspection_sheet.build_daily_sheet（與「每日巡檢表」Drawer 同一套）
source_ref：'{sheet_key}|{設備組}'，例 '1f-3f|空調箱'
業務裁示：docs/SPEC_floor_plan_inspection.md

⚠️ 編輯權限沿用 v2.10.107 已上線的 'mall_floor_map_edit'，不改成標準命名
   'mall_facility_inspection_floor_map_edit'，避免已授權的角色失效（DEV_SPEC §10 #6 唯一例外）。
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.mall_facility_inspection import MallFIBatch, MallFIItem
from app.services.floor_map.common import merge_group_status
from app.services.floor_map.providers.base import FloorMapProvider
from app.services.mall_daily_inspection_sheet import EXCEL_FLOOR_LABEL, build_daily_sheet

_GROUPS: list[tuple[str, str, str]] = [
    # sheet_key, 設備組, 系統
    ("1f-3f",   "空調箱",     "空調"),
    ("3f",      "靜電機",     "油煙處理"),
    ("1f",      "水洗機",     "油煙處理"),
    ("b1f-b4f", "抽排風設備", "排風"),
    ("b1f-b4f", "電信設備",   "電信"),
]
_SHARED = {"1f-3f": "1F~3F 共用一筆", "b1f-b4f": "B1~B4 共用一筆"}


def _ref(sheet_key: str, item: str) -> str:
    return f"{sheet_key}|{item}"


class MallFacilityInspectionProvider(FloorMapProvider):
    module          = "mall_facility_inspection"
    label           = "商場工務巡檢"
    view_permission = "mall_facility_inspection_view"
    edit_permission = "mall_floor_map_edit"
    floors          = ["3f", "2f", "1f", "b1f", "b2f", "b3f", "b4f"]
    default_floor   = "3f"
    attr_fields     = ["機房位置", "供應區域"]

    def groups(self) -> list[dict[str, Any]]:
        return [
            {
                "source_ref":   _ref(sk, item),
                "label":        f"{EXCEL_FLOOR_LABEL.get(sk, sk)}｜{item}",
                "system":       system,
                "shared_label": _SHARED.get(sk, ""),
            }
            for sk, item, system in _GROUPS
        ]

    # ── 資料讀取 ─────────────────────────────────────────────────────────────
    @staticmethod
    def _load(db: Session, cond) -> tuple[list[MallFIBatch], dict[str, list[MallFIItem]]]:
        batches = db.query(MallFIBatch).filter(cond).all()
        items: dict[str, list[MallFIItem]] = {b.ragic_id: [] for b in batches}
        if batches:
            for it in db.query(MallFIItem).filter(MallFIItem.batch_ragic_id.in_(list(items))).all():
                items.setdefault(it.batch_ragic_id, []).append(it)
        return batches, items

    @staticmethod
    def _group_rows(sheet: dict[str, Any], sk: str, item: str) -> list[dict[str, Any]]:
        return [r for r in sheet["rows"] if r["source_tab"] == sk and r["item"] == item]

    def day_status(self, db: Session, insp_date: str) -> dict[str, dict[str, Any]]:
        batches, items = self._load(db, MallFIBatch.inspection_date == insp_date)
        sheet = build_daily_sheet(batches, items)
        floors = {f["key"]: f for f in sheet["floors"]}
        out: dict[str, dict[str, Any]] = {}
        for g, (sk, item, _sys) in zip(self.groups(), _GROUPS):
            rows = self._group_rows(sheet, sk, item)
            fl = floors.get(sk, {})
            out[g["source_ref"]] = {
                **g,
                "status":         merge_group_status(rows, bool(fl.get("has_record"))),
                "rows":           rows,
                "batches":        fl.get("batches", []),
                "inspectors":     fl.get("inspectors", []),
                "actual_minutes": fl.get("actual_minutes", 0),
            }
        return out

    def month_status(self, db: Session, source_ref: str, year: int, month: int) -> list[dict[str, Any]]:
        sk, item = source_ref.split("|", 1)
        prefix = f"{year}/{month:02d}/"
        batches, items = self._load(
            db, (MallFIBatch.sheet_key == sk) & (MallFIBatch.inspection_date.like(f"{prefix}%"))
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
            rows = self._group_rows(sheet, sk, item)
            days.append({
                "day": d, "date": date_str,
                "status": merge_group_status(rows, True),
                "abnormal_rows": sum(1 for r in rows if r["abnormal"]),
            })
        return days

    def data_end(self, db: Session) -> str | None:
        return db.query(func.max(MallFIBatch.inspection_date)).filter(MallFIBatch.inspection_date != "").scalar()
