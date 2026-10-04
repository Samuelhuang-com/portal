"""
樓層巡檢圖 — 啟動時資料保底（main.py `_ensure_floor_map_data`）

為什麼需要（2026-10-04 事故）：
  開發環境 start-dev.bat 只跑 uvicorn、**不跑 alembic upgrade**。後端啟動時 create_all 會先把
  空的 floor_map_points 建出來，而商場既有的 22 個點位還在舊表 mall_floor_map_points →
  畫面上所有點位「不見了」，也沒有任何錯誤訊息。

這裡做的事與 Alembic fmapgen／fmapfbi 相同、且同樣可重跑：
  1. 舊表有資料、新表沒有該模組資料 → 從舊表搬過來（module／source_ref／placement／attrs 補齊）
  2. 某模組一筆點位都沒有（含已停用的）→ 寫入草稿點位
之後再跑 alembic upgrade 也不會重複（fmapgen 見新表已有資料就不搬、fmapfbi 見已有點位就不寫）。
有人停用過全部點位時，資料列仍在（is_active=False），不會被重新種回來。
"""
from __future__ import annotations

import logging

import sqlalchemy as sa

from app.core.time import twnow

logger = logging.getLogger(__name__)

TABLE, LEGACY = "floor_map_points", "mall_floor_map_points"

_COLS = (
    "module", "floor_key", "x", "y", "label", "equipment_code", "source_ref", "placement", "note",
    "sort_order", "is_active", "created_by", "updated_by", "created_at", "updated_at",
    "sheet_key", "item", "location_desc", "supply_area",
)
_tbl = sa.table(TABLE, sa.column("attrs", sa.JSON(none_as_null=True)), *(sa.column(c) for c in _COLS))


def _pending(i: int) -> tuple[float, float]:
    return 0.04, round(0.07 + 0.065 * i, 3)


# ── 草稿點位（與 migration mflmap／fmapfbi 相同內容）────────────────────────
# module, floor_key, x, y(或待定位序號), label, equipment_code, source_ref, attrs, placement
_SEED = {
    "mall_facility_inspection": [
        ("3f", 0.33, 0.27, "靜電機", "靜電機", "3f|靜電機", {"機房位置": "3-04空調機房", "供應區域": "3-01.3-02.3-03.3-04.2-04"}, "draft"),
        ("3f", 0.37, 0.31, "AH-R33 空調箱", "AH-R33", "1f-3f|空調箱", {"機房位置": "3-04空調機房", "供應區域": "3-04"}, "draft"),
        ("3f", 0.23, 0.60, "AH-R31 空調箱", "AH-R31", "1f-3f|空調箱", {"機房位置": "3F九華樓廚房", "供應區域": "3-01+3-02a+3-02b"}, "draft"),
        ("3f", 0.66, 0.62, "AH-R34 空調箱", "AH-R34", "1f-3f|空調箱", {"機房位置": "3-06空調機房", "供應區域": "3-05a+3-05b+3-06(部分使用)"}, "draft"),
        ("2f", 0.80, 0.62, "AH-R26 空調箱", "AH-R26", "1f-3f|空調箱", {"機房位置": "2F雅室廚房", "供應區域": "2-05+06+公區"}, "draft"),
        ("2f", 0.85, 0.57, "AH-R27 空調箱（供 1F）", "AH-R27", "1f-3f|空調箱", {"機房位置": "2F雅室廚房", "供應區域": "1-11+12+公區"}, "draft"),
        ("2f", None, 0, "AH-R21 空調箱（供 1F）", "AH-R21", "1f-3f|空調箱", {"機房位置": "2F空調機房", "供應區域": "1-01+02+公區"}, "pending"),
        ("2f", None, 1, "AH-R23 空調箱（供 1F）", "AH-R23", "1f-3f|空調箱", {"機房位置": "2F空調機房", "供應區域": "1-03+04+公區"}, "pending"),
        ("2f", None, 2, "AH-R22 空調箱", "AH-R22", "1f-3f|空調箱", {"機房位置": "2F空調機房", "供應區域": "2-01+公區"}, "pending"),
        ("2f", None, 3, "AH-R24 空調箱", "AH-R24", "1f-3f|空調箱", {"機房位置": "2F空調機房", "供應區域": "2-02+03+公區"}, "pending"),
        ("2f", None, 4, "AH-R25 空調箱", "AH-R25", "1f-3f|空調箱", {"機房位置": "2F空調機房", "供應區域": "2-04+公區"}, "pending"),
        ("1f", None, 0, "水洗機", "水洗機", "1f|水洗機", {"機房位置": "1F廁所後方", "供應區域": "1F櫃位及中島"}, "pending"),
        ("1f", None, 1, "AH-R32 空調箱", "AH-R32", "1f-3f|空調箱", {"機房位置": "1FB梯", "供應區域": "1F中島公區"}, "pending"),
        ("1f", None, 2, "PAH-R21 空調箱", "PAH-R21", "1f-3f|空調箱", {"機房位置": "小後院廚房上方", "供應區域": "小後苑"}, "pending"),
        ("b1f", 0.26, 0.42, "SF-B12 送風機", "SF-B12", "b1f-b4f|抽排風設備", {"機房位置": "B1停車場", "供應區域": "B1驗收區"}, "draft"),
        ("b1f", 0.55, 0.62, "EF-B11 排風機", "EF-B11", "b1f-b4f|抽排風設備", {"機房位置": "B1停車場", "供應區域": "B1停車場"}, "draft"),
        ("b1f", None, 0, "EF-HB12 排風機", "EF-HB12", "b1f-b4f|抽排風設備", {"機房位置": "B1機房", "供應區域": "B1垃圾處理室"}, "pending"),
        ("b1f", None, 1, "EF-RB11 排風機", "EF-RB11", "b1f-b4f|抽排風設備", {"機房位置": "B1機房", "供應區域": "B1垃圾處理室"}, "pending"),
        ("b1f", None, 2, "電信設備", None, "b1f-b4f|電信設備", None, "pending"),
        ("b2f", 0.55, 0.55, "EF-B21 排風機", "EF-B21", "b1f-b4f|抽排風設備", {"機房位置": "B2停車場", "供應區域": "B2停車場"}, "draft"),
        ("b3f", 0.55, 0.55, "EF-B31 排風機", "EF-B31", "b1f-b4f|抽排風設備", {"機房位置": "B3停車場", "供應區域": "B3停車場"}, "draft"),
        ("b4f", 0.55, 0.55, "EF-B41 排風機", "EF-B41", "b1f-b4f|抽排風設備", {"機房位置": "B4停車場", "供應區域": "B4停車場"}, "draft"),
    ],
    "full_building_inspection": [
        ("rf", 0.57, 0.30, "冷卻水塔", None, "rf|冷卻水塔", {"機房位置": "頂樓"}, "draft"),
        ("rf", None, 0, "上水塔", None, "rf|上水塔", {"機房位置": "頂樓"}, "pending"),
        ("b1f", 0.64, 0.61, "電力機房", None, "b1f|電力機房", {"機房位置": "B1F機電設備空間"}, "draft"),
        ("b1f", None, 0, "發電機", None, "b1f|發電機", None, "pending"),
        ("b1f", None, 1, "電信設備", None, "b1f|電信設備", None, "pending"),
        ("b2f", None, 0, "油脂截流槽", None, "b2f|油脂截流槽", None, "pending"),
        ("b4f", None, 0, "冰水主機/冰水泵/冷卻水泵", None, "b4f|冰水主機/冰水泵/冷卻水泵", {"機房位置": "B4冰水主機機房"}, "pending"),
        ("b4f", None, 1, "連續壁", None, "b4f|連續壁", None, "pending"),
        ("b4f", None, 2, "汙廢水", None, "b4f|汙廢水", None, "pending"),
        ("b4f", None, 3, "下水塔", None, "b4f|下水塔", None, "pending"),
    ],
}


def _placement_from_note(note: str | None) -> str:
    n = (note or "").strip()
    return "pending" if n.startswith("待定位") else "draft" if n.startswith("草稿") else "confirmed"


def _count(conn, module: str) -> int:
    return conn.execute(sa.text(f"SELECT COUNT(*) FROM {TABLE} WHERE module = :m"), {"m": module}).scalar() or 0


def _copy_legacy(conn) -> int:
    rows = conn.execute(sa.text(
        f"SELECT floor_key, x, y, label, equipment_code, sheet_key, item, location_desc, supply_area, "
        f"note, sort_order, is_active, created_by, updated_by, created_at, updated_at FROM {LEGACY}"
    )).mappings().all()
    out = []
    for r in rows:
        r = dict(r)
        attrs = {k: v for k, v in (("機房位置", r.get("location_desc")), ("供應區域", r.get("supply_area"))) if v}
        out.append({
            **r,
            "module":     "mall_facility_inspection",
            "source_ref": f"{r.get('sheet_key') or ''}|{r.get('item') or ''}",
            "placement":  _placement_from_note(r.get("note")),
            "attrs":      attrs or None,
        })
    if out:
        conn.execute(_tbl.insert(), out)
    return len(out)


def _seed(conn, module: str) -> int:
    now, rows = twnow(), []
    tag = f"startup:{module}"
    for i, (fk, x, y, label, code, ref, attrs, placement) in enumerate(_SEED[module]):
        if placement == "pending":
            x, y = _pending(int(y))
            note = "待定位：底圖上看不出位置，請用編輯點位拖到正確位置"
        else:
            loc = (attrs or {}).get("機房位置", "")
            note = f"草稿：依機房位置「{loc}」概估，請現場校正" if loc else "草稿：概估位置，請現場校正"
        rows.append({
            "module": module, "floor_key": fk, "x": x, "y": y, "label": label, "equipment_code": code,
            "source_ref": ref, "placement": placement, "attrs": attrs, "note": note,
            "sort_order": i, "is_active": True, "created_by": tag, "updated_by": tag,
            "created_at": now, "updated_at": now,
            "sheet_key": None, "item": None, "location_desc": None, "supply_area": None,
        })
    conn.execute(_tbl.insert(), rows)
    return len(rows)


def ensure_floor_map_data(engine) -> dict[str, str]:
    """回傳每個模組做了什麼（寫 log 用）。表不存在時什麼都不做。"""
    result: dict[str, str] = {}
    with engine.begin() as conn:
        insp = sa.inspect(conn)
        if not insp.has_table(TABLE):
            return {"skip": f"{TABLE} 不存在"}
        if _count(conn, "mall_facility_inspection") == 0:
            if insp.has_table(LEGACY) and (conn.execute(sa.text(f"SELECT COUNT(*) FROM {LEGACY}")).scalar() or 0):
                result["mall_facility_inspection"] = f"從 {LEGACY} 搬入 {_copy_legacy(conn)} 筆"
            else:
                result["mall_facility_inspection"] = f"寫入草稿 {_seed(conn, 'mall_facility_inspection')} 筆"
        if _count(conn, "full_building_inspection") == 0:
            result["full_building_inspection"] = f"寫入草稿 {_seed(conn, 'full_building_inspection')} 筆"
    for k, v in result.items():
        logger.warning(f"[FloorMap] {k}：{v}")
    return result
