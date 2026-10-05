"""
樓層巡檢圖 Provider — 整棟巡檢（full_building_inspection）

資料：rf／b4f／b2f／b1f_inspection_batch／item（Ragic full-building-inspection/1,2,3,4，每層一張 Sheet）
版型：#2.3整棟-每日巡檢表.xlsx（services/full_building_inspection_template.py，65 列）
source_ref：'{樓層 tab}|{設備組}'，例 'b4f|下水塔'

Ragic 粒度檢查（DEV_SPEC §5.3，2026-10-04；欄位依 2026-10 同步 log「偵測到 N 個設備欄位」）
──────────────────────────────────────────────────────────────────────────────
- 檢查內容與 Ragic 欄位名一一同名，對應表只需列出例外。
- Excel 有、Ragic 沒有（→ unmapped，畫面標「Ragic 無此欄位」）：
    B1F 電力機房「廠商年度保養」（Ragic 只有一個「廠商年度保養」，位在發電機那一段）
    B2F 油脂截流槽「廠商年度保養」
    B4F 冰水主機/冰水泵/冷卻水泵「廠商年度保養」、B4F 汙廢水「廠商年度保養」
- 異常說明：每個設備組各一欄，依 Ragic 欄位順序為 異常說明、異常說明2、3、4。
- 一組欄位涵蓋多台設備（→ shared_label）：RF 冷卻水塔（多座）、B4F 冰水主機/冰水泵/冷卻水泵（多台）。
- 正常／異常判定：**沿用各樓層 sync 已正規化的 result_status**（含 measure＝量測／程度型，
  例水位高中低、電瓶電壓，不算異常；規則在 services/inspection_field_rules.py），不另判一次。
- 「拍照」欄位目前不在樓層巡檢圖呈現。
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.b1f_inspection import B1FInspectionBatch, B1FInspectionItem
from app.models.b2f_inspection import B2FInspectionBatch, B2FInspectionItem
from app.models.b4f_inspection import B4FInspectionBatch, B4FInspectionItem
from app.models.rf_inspection import RFInspectionBatch, RFInspectionItem
from app.services.floor_map.common import batch_out, hhmm, merge_group_status
from app.services.floor_map.providers.base import FloorMapProvider
from app.services.full_building_inspection_template import FULL_BUILDING_DAILY_INSPECTION_TEMPLATE

# tab → (Batch model, Item model, Ragic sheet path, 樓層文字)
SHEETS: dict[str, tuple[Any, Any, str, str]] = {
    "rf":  (RFInspectionBatch,  RFInspectionItem,  "full-building-inspection/1", "RF"),
    "b4f": (B4FInspectionBatch, B4FInspectionItem, "full-building-inspection/2", "B4F"),
    "b2f": (B2FInspectionBatch, B2FInspectionItem, "full-building-inspection/3", "B2F"),
    "b1f": (B1FInspectionBatch, B1FInspectionItem, "full-building-inspection/4", "B1F"),
}

# (tab, 設備組, 檢查內容) → Ragic 沒有此欄位
UNMAPPED: set[tuple[str, str, str]] = {
    ("b1f", "電力機房",                 "廠商年度保養"),
    ("b2f", "油脂截流槽",               "廠商年度保養"),
    ("b4f", "冰水主機/冰水泵/冷卻水泵", "廠商年度保養"),
    ("b4f", "汙廢水",                   "廠商年度保養"),
}

NOTE_FIELD: dict[tuple[str, str], str] = {
    ("rf",  "冷卻水塔"):                 "異常說明",
    ("rf",  "上水塔"):                   "異常說明2",
    ("b1f", "發電機"):                   "異常說明",
    ("b1f", "電力機房"):                 "異常說明2",
    ("b1f", "電信設備"):                 "異常說明3",
    ("b2f", "油脂截流槽"):               "異常說明",
    ("b4f", "冰水主機/冰水泵/冷卻水泵"): "異常說明",
    ("b4f", "連續壁"):                   "異常說明2",
    ("b4f", "汙廢水"):                   "異常說明3",
    ("b4f", "下水塔"):                   "異常說明4",
}

SYSTEM: dict[str, str] = {
    "冷卻水塔": "空調", "冰水主機/冰水泵/冷卻水泵": "空調",
    "上水塔": "給水", "下水塔": "給水",
    "發電機": "電力", "電力機房": "電力",
    "電信設備": "電信",
    "油脂截流槽": "排水", "汙廢水": "排水",
    "連續壁": "結構",
}

SHARED: dict[tuple[str, str], str] = {
    ("rf",  "冷卻水塔"):                 "多座冷卻水塔共用一筆",
    ("b4f", "冰水主機/冰水泵/冷卻水泵"): "冰水主機與泵浦多台共用一筆",
}

_STATUS_ORDER = ("abnormal", "pending", "unchecked", "measure", "normal")


def _template_groups() -> list[tuple[str, str]]:
    return list(dict.fromkeys((t["source_tab"], t["item"]) for t in FULL_BUILDING_DAILY_INSPECTION_TEMPLATE))


class FullBuildingInspectionProvider(FloorMapProvider):
    module          = "full_building_inspection"
    label           = "整棟巡檢"
    view_permission = "mall_full_building_inspection_view"
    edit_permission = "mall_full_building_inspection_floor_map_edit"
    floors          = ["rf", "b1f", "b2f", "b4f"]
    default_floor   = "b4f"
    attr_fields     = ["機房位置", "供應區域"]

    def groups(self) -> list[dict[str, Any]]:
        return [
            {
                "source_ref":   f"{tab}|{item}",
                "label":        f"{SHEETS[tab][3]}｜{item}",
                "system":       SYSTEM.get(item, ""),
                "shared_label": SHARED.get((tab, item), ""),
            }
            for tab, item in _template_groups()
        ]

    # ── 資料讀取 ─────────────────────────────────────────────────────────────
    @staticmethod
    def _load(db: Session, tab: str, cond_fn) -> tuple[list[Any], dict[str, dict[str, Any]]]:
        Batch, Item, _p, _l = SHEETS[tab]
        batches = db.query(Batch).filter(cond_fn(Batch)).all()
        values: dict[str, dict[str, Any]] = {b.ragic_id: {} for b in batches}
        if batches:
            for it in db.query(Item).filter(Item.batch_ragic_id.in_(list(values))).all():
                values.setdefault(it.batch_ragic_id, {})[it.item_name] = it
        batches.sort(key=lambda b: (hhmm(b.start_time or "") or "99:99", b.ragic_id))
        return batches, values

    @staticmethod
    def _rows(tab: str, item: str, batches: list[Any], values: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        multi = len(batches) > 1
        note_field = NOTE_FIELD.get((tab, item), "")
        notes = []
        for b in batches:
            n = values.get(b.ragic_id, {}).get(note_field) if note_field else None
            txt = (n.result_raw or "").strip() if n else ""
            if txt:
                notes.append((f"[{hhmm(b.start_time or '')}] " if multi else "") + txt)

        rows = []
        for t in FULL_BUILDING_DAILY_INSPECTION_TEMPLATE:
            if t["source_tab"] != tab or t["item"] != item:
                continue
            content = t["check_content"]
            kind = "unmapped" if (tab, item, content) in UNMAPPED else "status"
            results = []
            if kind == "status":
                for b in batches:
                    it = values.get(b.ragic_id, {}).get(content)
                    raw = (it.result_raw or "").strip() if it else ""
                    st = (it.result_status if it and raw else "unchecked") or "unchecked"
                    results.append({
                        "batch_ragic_id": b.ragic_id,
                        "time_label":     hhmm(b.start_time or "") if multi else "",
                        "status":         st,
                        "text":           raw,
                        "readings":       [],
                    })
            if kind == "unmapped":
                merged = "unmapped"
            elif not results:
                merged = "no_record"
            else:
                sts = [r["status"] for r in results]
                merged = next((p for p in _STATUS_ORDER if p in sts), "unchecked")
            rows.append({
                "check_content":  content,
                "result_options": t["result_options"],
                "minutes":        t["minutes"],
                "kind":           kind,
                "status":         merged,
                "results":        results,
                "abnormal":       merged in ("abnormal", "pending"),
                "abnormal_note":  "\n".join(notes),
            })
        return rows

    def _group_day(self, tab: str, item: str, batches: list[Any], values: dict) -> dict[str, Any]:
        _B, _I, path, _l = SHEETS[tab]
        rows = self._rows(tab, item, batches, values)
        bo = [batch_out(path, b.ragic_id, b) for b in batches]
        return {
            "status":         merge_group_status(rows, bool(batches)),
            "rows":           rows,
            "batches":        bo,
            "inspectors":     list(dict.fromkeys(x["inspector"] for x in bo if x["inspector"])),
            "actual_minutes": sum(x["actual_minutes"] for x in bo),
        }

    def day_status(self, db: Session, insp_date: str) -> dict[str, dict[str, Any]]:
        loaded = {tab: self._load(db, tab, lambda B: B.inspection_date == insp_date) for tab in SHEETS}
        out = {}
        for g in self.groups():
            tab, item = g["source_ref"].split("|", 1)
            out[g["source_ref"]] = {**g, **self._group_day(tab, item, *loaded[tab])}
        return out

    def month_status(self, db: Session, source_ref: str, year: int, month: int) -> list[dict[str, Any]]:
        tab, item = source_ref.split("|", 1)
        prefix = f"{year}/{month:02d}/"
        batches, values = self._load(db, tab, lambda B: B.inspection_date.like(f"{prefix}%"))
        by_day: dict[str, list[Any]] = defaultdict(list)
        for b in batches:
            by_day[b.inspection_date].append(b)
        days = []
        for d in range(1, calendar.monthrange(year, month)[1] + 1):
            date_str = f"{prefix}{d:02d}"
            bl = by_day.get(date_str, [])
            if not bl:
                days.append({"day": d, "date": date_str, "status": "no_record", "abnormal_rows": 0})
                continue
            gd = self._group_day(tab, item, bl, values)
            days.append({
                "day": d, "date": date_str, "status": gd["status"],
                "abnormal_rows": sum(1 for r in gd["rows"] if r["abnormal"]),
            })
        return days

    def data_end(self, db: Session) -> str | None:
        ends = [
            db.query(func.max(B.inspection_date)).filter(B.inspection_date != "").scalar()
            for B, _I, _p, _l in SHEETS.values()
        ]
        ends = [e for e in ends if e]
        return max(ends) if ends else None
