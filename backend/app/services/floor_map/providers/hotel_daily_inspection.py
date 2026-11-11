"""
樓層巡檢圖 Provider — 飯店每日巡檢（hotel_daily_inspection）

2026-11-10 新增（Samuel 裁示：樓層巡檢圖這次要做；照商場做法先放草稿點位，再在畫面上拖到正確位置）。
資料：hotel_di_inspection_batch／item（Ragic main-project-inspection/17、28～33）
判定：沿用 services/hotel_daily_inspection_sheet.build_daily_sheet（與每日巡檢表 Drawer 同一套），
      只看現行（新）表的場次；舊表場次不上圖（舊表欄位與新版型不同）。
source_ref：'{sheet_key}|{設備組}' 或 '{sheet_key}|{設備組}|{檢查內容}'（5-10F 每層一台空調箱各自一點）

Ragic 粒度（DEV_SPEC §5.3）：
  RF 冷卻水塔／上水塔／熱水系統／鍋爐設備／RF瓦斯：各一組欄位、各一點
  5-10F：每層一個欄位（5樓～10樓客房走道空調箱）→ 各層各一點（不共用）
  4F BAR-D公區、B1F 高壓機房、B1F 辦公室公區、B1F 廚房瓦斯設備、B4F 下水塔、B4F 空調機房：各一點
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.hotel_daily_inspection import HotelDIBatch, HotelDIItem
from app.services.floor_map.common import merge_group_status
from app.services.floor_map.providers.base import FloorMapProvider
from app.services.hotel_daily_inspection_sheet import EXCEL_FLOOR_LABEL, build_daily_sheet, norm_name
from app.services.hotel_daily_inspection_sources import is_live_batch

# sheet_key, 設備組, 檢查內容（None＝整組）, 系統, 顯示名稱
_GROUPS: list[tuple[str, str, str | None, str, str]] = [
    ("rf",         "冷卻水塔",     None, "空調",   "RF｜冷卻水塔"),
    ("rf",         "上水塔",       None, "給排水", "RF｜上水塔"),
    ("rf",         "熱水系統",     None, "熱水",   "RF｜熱水系統"),
    ("rf",         "鍋爐設備",     None, "熱水",   "RF｜鍋爐設備"),
    ("rf",         "RF瓦斯",       None, "瓦斯",   "RF｜RF瓦斯"),
    *[("5f-10f", "客房公共區域", f"{n}樓客房走道空調箱", "空調", f"{n}F｜客房走道空調箱") for n in range(5, 11)],
    ("4f",         "BAR-D公區",    None, "公區",   "4F｜BAR-D公區"),
    ("b1f-hv",     "高壓機房",     None, "電力",   "B1F｜高壓機房"),
    ("b1f-office", "辦公室公區",   None, "公區",   "B1F｜辦公室公區"),
    ("b1f-office", "廚房瓦斯設備", None, "瓦斯",   "B1F｜廚房瓦斯設備"),
    ("b4f-water",  "下水塔",       None, "給排水", "B4F｜下水塔"),
    ("b4f-ac",     "空調機房",     None, "空調",   "B4F｜空調機房"),
]


def _ref(sk: str, item: str, content: str | None) -> str:
    return f"{sk}|{item}" + (f"|{content}" if content else "")


def _parse_ref(source_ref: str) -> tuple[str, str, str | None]:
    parts = source_ref.split("|")
    return parts[0], parts[1], (parts[2] if len(parts) > 2 else None)


def _present_rows(rows: list[dict[str, Any]], items: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """缺欄位規則（同商場）：場次沒有此檢查的欄位 → 該場次不列；所有場次都沒有 → 整列不呈現。"""
    out: list[dict[str, Any]] = []
    for r in rows:
        fields = {norm_name(f) for f in (r.get("ragic_fields") or [])}
        kept = []
        for res in r.get("results", []):
            names = {norm_name(it.item_name) for it in items.get(res["batch_ragic_id"], [])}
            if fields & names:
                kept.append(res)
        if not kept:
            continue
        sts = [x["status"] for x in kept]
        merged = next((p for p in ("abnormal", "pending", "unchecked", "reading", "normal") if p in sts),
                      "unchecked")
        out.append({**r, "results": kept, "status": merged, "abnormal": merged in ("abnormal", "pending")})
    return out


class HotelDailyInspectionProvider(FloorMapProvider):
    module          = "hotel_daily_inspection"
    label           = "飯店每日巡檢"
    view_permission = "hotel_daily_inspection_view"
    edit_permission = "hotel_daily_inspection_floor_map_edit"
    floors          = ["rf", "10f", "9f", "8f", "7f", "6f", "5f", "4f", "b1f", "b4f"]
    default_floor   = "rf"
    attr_fields     = ["機房位置", "供應區域"]

    def groups(self) -> list[dict[str, Any]]:
        return [
            {"source_ref": _ref(sk, item, c), "label": label, "system": system, "shared_label": ""}
            for sk, item, c, system, label in _GROUPS
        ]

    @staticmethod
    def _load(db: Session, cond) -> tuple[list[HotelDIBatch], dict[str, list[HotelDIItem]]]:
        batches = [b for b in db.query(HotelDIBatch).filter(cond).all() if is_live_batch(b.ragic_id)]
        items: dict[str, list[HotelDIItem]] = {b.ragic_id: [] for b in batches}
        if batches:
            ids = list(items)
            for i in range(0, len(ids), 500):
                for it in db.query(HotelDIItem).filter(HotelDIItem.batch_ragic_id.in_(ids[i:i + 500])).all():
                    items.setdefault(it.batch_ragic_id, []).append(it)
        return batches, items

    @staticmethod
    def _group_rows(sheet: dict[str, Any], sk: str, item: str, content: str | None) -> list[dict[str, Any]]:
        return [r for r in sheet["rows"]
                if r["source_tab"] == sk and r["item"] == item and (content is None or r["check_content"] == content)]

    def day_status(self, db: Session, insp_date: str) -> dict[str, dict[str, Any]]:
        batches, items = self._load(db, HotelDIBatch.inspection_date == insp_date)
        sheet = build_daily_sheet(batches, items)
        floors = {f["key"]: f for f in sheet["floors"]}
        out: dict[str, dict[str, Any]] = {}
        for g, (sk, item, content, _sys, _lab) in zip(self.groups(), _GROUPS):
            rows = _present_rows(self._group_rows(sheet, sk, item, content), items)
            fl = floors.get(sk, {})
            out[g["source_ref"]] = {
                **g,
                "status":         merge_group_status(rows, bool(fl.get("has_record")) and bool(rows)),
                "rows":           rows,
                "batches":        fl.get("batches", []),
                "inspectors":     fl.get("inspectors", []),
                "actual_minutes": fl.get("actual_minutes", 0),
                "abnormal_notes": fl.get("abnormal_notes", []),
            }
        return out

    def month_status(self, db: Session, source_ref: str, year: int, month: int) -> list[dict[str, Any]]:
        sk, item, content = _parse_ref(source_ref)
        prefix = f"{year}/{month:02d}/"
        batches, items = self._load(
            db, (HotelDIBatch.sheet_key == sk) & (HotelDIBatch.inspection_date.like(f"{prefix}%"))
        )
        by_day: dict[str, list[HotelDIBatch]] = defaultdict(list)
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
            rows = _present_rows(self._group_rows(sheet, sk, item, content), items)
            days.append({"day": d, "date": date_str, "status": merge_group_status(rows, bool(rows)),
                         "abnormal_rows": sum(1 for r in rows if r["abnormal"])})
        return days

    def data_end(self, db: Session) -> str | None:
        # 只看現行表（舊表場次不上圖）；舊表 ID 前綴：rf_legacy、*_a3x／a4x
        rows = (
            db.query(HotelDIBatch.ragic_id, HotelDIBatch.inspection_date)
            .filter(HotelDIBatch.inspection_date != "")
            .order_by(HotelDIBatch.inspection_date.desc())
            .limit(500)
            .all()
        )
        for rid, d in rows:
            if is_live_batch(rid):
                return d
        return db.query(func.max(HotelDIBatch.inspection_date)).filter(HotelDIBatch.inspection_date != "").scalar()


__all__ = ["HotelDailyInspectionProvider", "EXCEL_FLOOR_LABEL"]
