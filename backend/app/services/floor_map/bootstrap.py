"""
樓層巡檢圖 — 啟動時資料保底（main.py `_ensure_floor_map_data`）

為什麼需要（2026-10-04 事故）：
  開發環境 start-dev.bat 只跑 uvicorn、**不跑 alembic upgrade**。後端啟動時 create_all 會先把
  空的 floor_map_points 建出來，而商場既有的 22 個點位還在舊表 mall_floor_map_points →
  畫面上所有點位「不見了」，也沒有任何錯誤訊息。

這裡做的事與 Alembic fmapgen／fmapfbi 相同、且同樣可重跑：
  1. 舊表有資料、新表沒有該模組資料 → 從舊表搬過來（module／source_ref／placement／attrs 補齊）
  2. 某模組一筆點位都沒有（含已停用的）→ 寫入草稿點位
  3. 套用最新點位清單 sync_point_list（2026-10-05，_1005.xlsx）：補缺點、更新機房位置／供應區域，
     不動已校正的位置、不蓋掉使用者自己改過的值（與 Alembic fmap1005 共用同一個函式）
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
_upd = sa.table(TABLE, sa.column("id"), sa.column("attrs", sa.JSON(none_as_null=True)),
                sa.column("equipment_code"), sa.column("updated_by"), sa.column("updated_at"))


def _pending(i: int) -> tuple[float, float]:
    return 0.04, round(0.07 + 0.065 * i, 3)


# ── 點位清單（2026-10-05 起以「樓層巡檢圖_點位清單與修正紀錄_1005.xlsx」為準）───────
# module, floor_key, x, y(或待定位序號), label, equipment_code, source_ref, attrs, placement
# 新環境：_seed() 直接寫入這份；既有環境：sync_point_list() 補缺、更新屬性（見下方說明）。
_SEED = {
    "mall_facility_inspection": [
        ("3f", 0.33, 0.27, "靜電機", "靜電機", "3f|靜電機", {"機房位置": "3-04空調機房", "供應區域": "3-01.3-02.3-03.3-04.2-04"}, "draft"),
        ("3f", 0.37, 0.31, "AH-R33 空調箱", "AH-R33", "1f-3f|空調箱", {"機房位置": "3-04空調機房", "供應區域": "3-04"}, "draft"),
        ("3f", 0.23, 0.60, "AH-R31 空調箱", "AH-R31", "1f-3f|空調箱", {"機房位置": "3F九華樓廚房", "供應區域": "3-01+3-02a+3-02b"}, "draft"),
        ("3f", 0.66, 0.62, "AH-R34 空調箱", "AH-R34", "1f-3f|空調箱", {"機房位置": "3-06空調機房", "供應區域": "3-05a+3-05b+3-06(部分使用)"}, "draft"),
        ("2f", 0.80, 0.62, "AH-R26 空調箱", "AH-R26", "1f-3f|空調箱", {"機房位置": "2F雅室廚房", "供應區域": "2-05+06+公區"}, "draft"),
        ("2f", 0.85, 0.57, "AH-R27 空調箱（供 1F）", "AH-R27", "1f-3f|空調箱", {"機房位置": "2F雅室廚房", "供應區域": "1-11+12.1-10.1-09+公區"}, "draft"),
        ("2f", None, 0, "AH-R21 空調箱（供 1F）", "AH-R21", "1f-3f|空調箱", {"機房位置": "2F空調機房", "供應區域": "1-01+02+公區.1-03.1-04+公區"}, "pending"),
        ("2f", None, 1, "AH-R23 空調箱（供 1F）", "AH-R23", "1f-3f|空調箱", {"機房位置": "2F空調機房", "供應區域": "1-05.1-06.1-07.1-08+公區"}, "pending"),
        ("2f", None, 2, "AH-R22 空調箱", "AH-R22", "1f-3f|空調箱", {"機房位置": "2F空調機房", "供應區域": "2-01+公區"}, "pending"),
        ("2f", None, 3, "AH-R24 空調箱", "AH-R24", "1f-3f|空調箱", {"機房位置": "2F空調機房", "供應區域": "2-02+03+公區"}, "pending"),
        ("2f", None, 4, "AH-R25 空調箱", "AH-R25", "1f-3f|空調箱", {"機房位置": "2F空調機房", "供應區域": "2-04+公區"}, "pending"),
        ("1f", None, 0, "水洗機", "水洗機", "1f|水洗機", {"機房位置": "1F廁所後方", "供應區域": "1F櫃位及中島"}, "pending"),
        ("1f", None, 1, "AH-R32 空調箱", "AH-R32", "1f-3f|空調箱", {"機房位置": "1FB梯", "供應區域": "1-05.1-06.1-07.1-08補氣"}, "pending"),
        ("1f", None, 2, "PAH-R21 空調箱", "PAH-R21", "1f-3f|空調箱", {"機房位置": "小後院廚房上方", "供應區域": "小後苑"}, "pending"),
        ("b1f", 0.26, 0.42, "SF-B12 送風機", "SF-B12", "b1f-b4f|抽排風設備", {"機房位置": "B1停車場", "供應區域": "B1驗收區"}, "draft"),
        ("b1f", 0.55, 0.62, "EF-B11 排風機", "EF-B11", "b1f-b4f|抽排風設備", {"機房位置": "B1停車場", "供應區域": "B1停車場"}, "draft"),
        ("b1f", None, 0, "EF-HB12 排風機", "EF-HB12", "b1f-b4f|抽排風設備", {"機房位置": "B1機房", "供應區域": "B1垃圾處理室"}, "pending"),
        ("b1f", None, 1, "EF-RB11 排風機", "EF-RB11", "b1f-b4f|抽排風設備", {"機房位置": "B1機房", "供應區域": "B1垃圾處理室"}, "pending"),
        # ⚠ 1005 清單原文：點位名稱「SF-B11 送風機」、設備編號「EF-RB12」，兩者不一致，照原文寫入待確認
        ("b1f", None, 2, "SF-B11 送風機", "EF-RB12", "b1f-b4f|抽排風設備", {"機房位置": "B1機房", "供應區域": "B1停車場"}, "pending"),
        ("b1f", None, 3, "電信設備", None, "b1f-b4f|電信設備", {"機房位置": "B1電信室"}, "pending"),
        ("b2f", 0.45, 0.55, "SF-B21 送風機", "SF-B21", "b1f-b4f|抽排風設備", {"機房位置": "B2停車場", "供應區域": "B2停車場"}, "draft"),
        ("b2f", 0.55, 0.55, "EF-B21 排風機", "EF-B21", "b1f-b4f|抽排風設備", {"機房位置": "B2停車場", "供應區域": "B2停車場"}, "draft"),
        ("b3f", 0.45, 0.55, "SF-B31 排風機", "SF-B31", "b1f-b4f|抽排風設備", {"機房位置": "B3停車場", "供應區域": "B3停車場"}, "draft"),
        ("b3f", 0.55, 0.55, "EF-B31 排風機", "EF-B31", "b1f-b4f|抽排風設備", {"機房位置": "B3停車場", "供應區域": "B3停車場"}, "draft"),
        ("b4f", 0.45, 0.55, "SF-B41 排風機", "SF-B41", "b1f-b4f|抽排風設備", {"機房位置": "B4停車場", "供應區域": "B4停車場"}, "draft"),
        ("b4f", 0.55, 0.55, "EF-B41 排風機", "EF-B41", "b1f-b4f|抽排風設備", {"機房位置": "B4停車場", "供應區域": "B4停車場"}, "draft"),
    ],
    "full_building_inspection": [
        ("rf", 0.57, 0.30, "冷卻水塔", None, "rf|冷卻水塔", {"機房位置": "頂樓", "供應區域": "B4冰水主機"}, "draft"),
        ("rf", None, 0, "上水塔", None, "rf|上水塔", {"機房位置": "頂樓"}, "pending"),
        ("b1f", 0.64, 0.61, "電力機房", None, "b1f|電力機房", {"機房位置": "B1F機電設備空間"}, "draft"),
        ("b1f", None, 0, "發電機", None, "b1f|發電機", {"機房位置": "B1發電機室", "供應區域": "1~3樓緊急用電"}, "pending"),
        ("b1f", None, 1, "電信設備", None, "b1f|電信設備", {"機房位置": "B1電信室"}, "pending"),
        ("b2f", None, 0, "油脂截流槽", None, "b2f|油脂截流槽", {"機房位置": "B2截油機室"}, "pending"),
        ("b4f", None, 0, "冰水主機/冰水泵/冷卻水泵", None, "b4f|冰水主機/冰水泵/冷卻水泵", {"機房位置": "B4冰水主機機房"}, "pending"),
        ("b4f", None, 1, "連續壁", None, "b4f|連續壁", {"機房位置": "B4"}, "pending"),
        # 汙廢水：2026-10-05 由 1 點拆成 6 台泵浦（共用同一組 Ragic 資料 b4f|汙廢水）
        ("b4f", None, 2, "SP-1 汙水", "SP-1", "b4f|汙廢水", {"機房位置": "B4送風機房"}, "pending"),
        ("b4f", None, 3, "SP-2 汙水", "SP-2", "b4f|汙廢水", {"機房位置": "B4停車場313車位"}, "pending"),
        ("b4f", None, 4, "SP-3 汙水", "SP-3", "b4f|汙廢水", {"機房位置": "B4送風機房"}, "pending"),
        ("b4f", None, 5, "WP-1 廢水", "WP-1", "b4f|汙廢水", {"機房位置": "B4停車場345車位"}, "pending"),
        ("b4f", None, 6, "WP-2 廢水", "WP-2", "b4f|汙廢水", {"機房位置": "B4冰水主機室(飯店)"}, "pending"),
        ("b4f", None, 7, "WP-3 廢水", "WP-3", "b4f|汙廢水", {"機房位置": "B4停車場302車位"}, "pending"),
        ("b4f", None, 8, "下水塔", None, "b4f|下水塔", {"機房位置": "B4"}, "pending"),
    ],
}

# 舊清單（v2.10.107～.113，2026-10-04 版）寫入過的值 —— sync_point_list 只覆蓋「還是舊值或空白」的欄位，
# 使用者在畫面上自己改過的機房位置／供應區域／設備編號不會被蓋掉。
_PREV_VALUES: dict[tuple[str, str], dict[str, str | None]] = {
    ("mall_facility_inspection", "AH-R27 空調箱（供 1F）"): {"供應區域": "1-11+12+公區"},
    ("mall_facility_inspection", "AH-R21 空調箱（供 1F）"): {"供應區域": "1-01+02+公區"},
    ("mall_facility_inspection", "AH-R23 空調箱（供 1F）"): {"供應區域": "1-03+04+公區"},
    ("mall_facility_inspection", "AH-R32 空調箱"):          {"供應區域": "1F中島公區"},
}

# 改名：舊 label → 新 label（保留原點位位置；只在新 label 不存在時改）
_RENAMES: dict[tuple[str, str, str], str] = {
    ("full_building_inspection", "b4f", "汙廢水"): "SP-1 汙水",
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


def _note_for(placement: str, attrs: dict | None) -> str:
    if placement == "pending":
        return "待定位：底圖上看不出位置，請用編輯點位拖到正確位置"
    loc = (attrs or {}).get("機房位置", "")
    return f"草稿：依機房位置「{loc}」概估，請現場校正" if loc else "草稿：概估位置，請現場校正"


def sync_point_list(conn, module: str, tag: str = "pointlist:20261005") -> dict[str, int]:
    """
    既有環境套用最新點位清單（可重跑；與 Alembic fmap1005 共用）：
      1. 改名（_RENAMES）：舊點保留位置，改成新名稱／設備編號
      2. 清單有、DB 沒有（依 樓層＋名稱，含已停用的點）→ 新增（草稿或待定位，待定位排在該樓層既有待定位之後）
      3. 清單有、DB 也有 → 機房位置／供應區域／設備編號只在「空白或仍是舊清單值」時更新；
         **不動 x／y／placement**（已拖過、已校正的位置不受影響）
    已停用（is_active=False）的點不會被重新啟用。
    """
    import json

    stat = {"renamed": 0, "inserted": 0, "updated": 0}
    rows = conn.execute(sa.text(
        f"SELECT id, floor_key, label, equipment_code, attrs, placement, is_active, x, y "
        f"FROM {TABLE} WHERE module = :m"
    ), {"m": module}).mappings().all()
    rows = [dict(r) for r in rows]
    for r in rows:
        a = r["attrs"]
        r["attrs"] = (json.loads(a) if isinstance(a, str) else a) or {}

    labels = {(r["floor_key"], r["label"]) for r in rows}
    now = twnow()

    # 1. 改名
    for (mod, fk, old), new in _RENAMES.items():
        if mod != module or (fk, new) in labels:
            continue
        for r in rows:
            if r["floor_key"] == fk and r["label"] == old:
                conn.execute(sa.text(f"UPDATE {TABLE} SET label = :l, updated_by = :t, updated_at = :n WHERE id = :i"),
                             {"l": new, "t": tag, "n": now, "i": r["id"]})
                r["label"] = new
                labels.discard((fk, old)); labels.add((fk, new))
                stat["renamed"] += 1
                break

    by_label = {(r["floor_key"], r["label"]): r for r in rows}
    # 待定位欄（圖左上一列）已被佔用的格子；新增的待定位點排進空格，不與既有點重疊
    occupied: dict[str, set[int]] = {}
    for r in rows:
        if r["is_active"] and r["x"] is not None and abs(float(r["x"]) - _pending(0)[0]) < 1e-6:
            occupied.setdefault(r["floor_key"], set()).add(round((float(r["y"]) - _pending(0)[1]) / 0.065))

    def _free_slot(fk: str) -> int:
        used = occupied.setdefault(fk, set())
        n = 0
        while n in used:
            n += 1
        used.add(n)
        return n

    inserts = []
    for i, (fk, x, y, label, code, ref, attrs, placement) in enumerate(_SEED[module]):
        cur = by_label.get((fk, label))
        if cur is None:
            if placement == "pending":
                x, y = _pending(_free_slot(fk))
            inserts.append({
                "module": module, "floor_key": fk, "x": x, "y": y, "label": label, "equipment_code": code,
                "source_ref": ref, "placement": placement, "attrs": attrs, "note": _note_for(placement, attrs),
                "sort_order": i, "is_active": True, "created_by": tag, "updated_by": tag,
                "created_at": now, "updated_at": now,
                "sheet_key": None, "item": None, "location_desc": None, "supply_area": None,
            })
            continue

        prev = _PREV_VALUES.get((module, label), {})
        new_attrs = dict(cur["attrs"])
        changed = False
        for k, v in (attrs or {}).items():
            old = new_attrs.get(k)
            if old != v and (not old or old == prev.get(k)):
                new_attrs[k] = v
                changed = True
        new_code = cur["equipment_code"]
        if code and new_code != code and (not new_code or new_code == prev.get("equipment_code")):
            new_code, changed = code, True
        if changed:
            conn.execute(
                _upd.update().where(_upd.c.id == cur["id"]).values(
                    attrs=new_attrs, equipment_code=new_code, updated_by=tag, updated_at=now,
                )
            )
            stat["updated"] += 1

    if inserts:
        conn.execute(_tbl.insert(), inserts)
        stat["inserted"] = len(inserts)
    return stat


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
        # 2026-10-05：套用最新點位清單（補缺、更新屬性；不動已校正的位置）
        for mod in _SEED:
            st = sync_point_list(conn, mod)
            if any(st.values()):
                result[f"{mod}:pointlist"] = f"改名 {st['renamed']}、新增 {st['inserted']}、更新屬性 {st['updated']} 筆"
    for k, v in result.items():
        logger.warning(f"[FloorMap] {k}：{v}")
    return result
