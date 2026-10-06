"""
人員動線 — 工作日誌位置解析（2026-10-05 新增）

把工作日誌的一筆 row（routers/work_journal.py::_make_row 的輸出）解析成「在哪裡」：

    confidence  意義                         例
    ─────────────────────────────────────────────────────────────────────
    room        精準到客房房號                IHG 房號 613、報修標題「613 門檔鐵片脫落」
    floor       精準到單一樓層                報修「發生樓層」= 2F、「B2熱油槽 → 巡檢」
    multi       跨多層（巡檢表、1F~3F 巡檢）  「1F～3F巡檢」、「B1-B4連排風設備」
    unknown     判斷不出位置                  「整理工作日誌、ragic填寫」

⚠️ 這是「工作地點」不是 GPS 軌跡：兩件工作之間實際走哪條路，資料裡沒有。
   前端畫的路徑是依時間把工作地點串起來的「推定動線」。

解析優先序（先命中先用，每一步都記錄 basis 供畫面顯示「依據」）：
  1. detail['房號']（IHG 客房保養）
  2. 工作內容／標題文字中的房號（必須在 IHG 規範房號清單內，避免把金額、編號誤認成房號）
  3. 結構化樓層欄位：detail['發生樓層'] / detail['樓層']
  4. 巡檢表名稱（每日巡檢、設施巡檢、抄表）
  5. 工作內容／區域／標題文字中的樓層字樣（含 1F~3F、B1-B4 範圍）
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

# 規範房號清單（單一來源在 IHG 模組，這裡只引用不另存）
from app.routers.ihg_room_maintenance import CANONICAL_ROOMS, CANONICAL_ROOM_SET
from app.services.floor_map.registry import FLOOR_MAP as _PLAN_FLOORS

# ── 建築樓層模型 ─────────────────────────────────────────────────────────────
# 春大直：B4F～10F＋RF；客房層 5F～10F（同 IHG 模組 FLOORS）
GUEST_FLOORS = ["5f", "6f", "7f", "8f", "9f", "10f"]
TOP_FLOOR = 10
BASEMENTS = 4

# 由上而下
FLOOR_ORDER: list[str] = (
    ["rf"] + [f"{n}f" for n in range(TOP_FLOOR, 0, -1)] + [f"b{n}f" for n in range(1, BASEMENTS + 1)]
)
FLOOR_INDEX = {k: i for i, k in enumerate(FLOOR_ORDER)}


def floor_label(key: str) -> str:
    return key.upper()


def building_floors() -> list[dict[str, Any]]:
    """樓層清單（由上而下）。kind：guest＝客房標準層（向量圖）／plan＝有共用底圖／none＝尚無平面圖"""
    rooms_by_floor = _rooms_by_floor()
    out = []
    for k in FLOOR_ORDER:
        if k in GUEST_FLOORS:
            kind = "guest"
        elif k in _PLAN_FLOORS:
            kind = "plan"
        else:
            kind = "none"
        out.append({
            "key": k,
            "label": floor_label(k),
            "kind": kind,
            "rooms": rooms_by_floor.get(k, []),
        })
    return out


@lru_cache(maxsize=1)
def _rooms_by_floor() -> dict[str, list[str]]:
    res: dict[str, list[str]] = {}
    for r in CANONICAL_ROOMS:
        res.setdefault(f"{int(r[:-2])}f", []).append(r)
    return res


@lru_cache(maxsize=1)
def load_hotel_plan() -> dict[str, Any]:
    """客房標準層向量幾何（由 Temp/build_hotel_std_floor.py 依 5F 疏散圖描繪產生）"""
    p = Path(__file__).with_name("hotel_std_floor.json")
    return json.loads(p.read_text(encoding="utf-8"))


# ── 樓層字樣解析 ─────────────────────────────────────────────────────────────
_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

# 範圍：1F~3F、1F～3F、B1-B4、B1F~B4F、4F-10F、4~10F
_RANGE_RE = re.compile(
    r"(?<![A-Za-z0-9])(B?\d{1,2})\s*(F|樓)?\s*[~～\-－至到]\s*(B?\d{1,2})\s*(F|樓)?(?![A-Za-z0-9])",
    re.IGNORECASE,
)
# 單層：B2、B1F、5F、5樓、RF、屋頂
_B_RE = re.compile(r"(?<![A-Za-z0-9])B\s?(\d{1,2})\s*F?(?![0-9])", re.IGNORECASE)
_F_RE = re.compile(r"(?<![A-Za-z0-9.])(\d{1,2})\s*(?:F|樓)(?![A-Za-z])", re.IGNORECASE)
_CN_RE = re.compile(r"(地下)?([一二三四五六七八九十]{1,2})樓")
_RF_RE = re.compile(r"(?<![A-Za-z])(RF|R/F|R1F)(?![A-Za-z])|屋頂|頂樓|屋突", re.IGNORECASE)


def _norm_token(tok: str) -> Optional[str]:
    t = tok.strip().upper()
    if t.startswith("B"):
        try:
            n = int(t[1:])
        except ValueError:
            return None
        return f"b{n}f" if 1 <= n <= BASEMENTS else None
    try:
        n = int(t)
    except ValueError:
        return None
    return f"{n}f" if 1 <= n <= TOP_FLOOR else None


def _cn_to_int(s: str) -> Optional[int]:
    if s == "十":
        return 10
    if len(s) == 1:
        return _CN_NUM.get(s)
    if s.startswith("十"):
        return 10 + _CN_NUM.get(s[1], 0)
    return None


def parse_floors(text: str) -> list[str]:
    """回傳文字中提到的樓層（依建築由上而下排序、去重；只收建築內存在的樓層）"""
    if not text:
        return []
    found: set[str] = set()
    work = text

    for m in _RANGE_RE.finditer(text):
        a, fa, b, fb = m.group(1), m.group(2), m.group(3), m.group(4)
        # 必須有 B 或 F／樓 字樣，避免把「1-3」「SP1-SP3」當樓層
        if not (a.upper().startswith("B") or b.upper().startswith("B") or fa or fb):
            continue
        ka, kb = _norm_token(a), _norm_token(b)
        if not ka or not kb:
            continue
        ia, ib = FLOOR_INDEX[ka], FLOOR_INDEX[kb]
        for i in range(min(ia, ib), max(ia, ib) + 1):
            found.add(FLOOR_ORDER[i])
        work = work.replace(m.group(0), " ")

    for m in _B_RE.finditer(work):
        k = _norm_token("B" + m.group(1))
        if k:
            found.add(k)
    for m in _F_RE.finditer(work):
        k = _norm_token(m.group(1))
        if k:
            found.add(k)
    for m in _CN_RE.finditer(work):
        n = _cn_to_int(m.group(2))
        if n:
            k = _norm_token(("B" if m.group(1) else "") + str(n))
            if k:
                found.add(k)
    if _RF_RE.search(work):
        found.add("rf")
    return sorted(found, key=lambda k: FLOOR_INDEX[k])


# ── 房號解析 ─────────────────────────────────────────────────────────────────
_ROOM_RE = re.compile(
    r"(?<![\dA-Za-z#\-/.:])(\d{3,4})(?![\d.:/])"
    r"(?!\s*(?:元|分|min|MIN|度|kg|KG|台|支|個|片|顆|組|w|W|V|A\b|mm|cm|M\b|號機|號|樓|F|年|月|日|%))"
)


def parse_rooms(text: str) -> list[str]:
    if not text:
        return []
    out: list[str] = []
    for m in _ROOM_RE.finditer(text):
        r = m.group(1)
        if r in CANONICAL_ROOM_SET and r not in out:
            out.append(r)
    return out


def room_floor(room: str) -> str:
    return f"{int(room[:-2])}f"


# ── 主函式 ───────────────────────────────────────────────────────────────────
_NAME_KEYS = ("巡檢表名稱", "抄表表名稱")


def resolve_row(row: dict) -> dict[str, Any]:
    """回傳 {confidence, floors, room, basis}"""
    d: dict = row.get("detail") or {}
    task = row.get("task") or ""

    # 1. IHG 房號
    rn = (d.get("房號") or "").strip()
    if rn in CANONICAL_ROOM_SET:
        return _loc("room", [room_floor(rn)], rn, "IHG 房號")

    # 2. 文字中的房號
    text_main = " ".join(filter(None, [task, d.get("標題") or "", d.get("問題說明") or ""]))
    rooms = parse_rooms(text_main)
    if len(rooms) == 1:
        return _loc("room", [room_floor(rooms[0])], rooms[0], "工作內容中的房號")
    if len(rooms) > 1:
        fl = sorted({room_floor(r) for r in rooms}, key=lambda k: FLOOR_INDEX[k])
        return _loc("room", fl[:1], rooms[0], f"工作內容中的房號（共 {len(rooms)} 間：{'、'.join(rooms)}）",
                    extra_rooms=rooms[1:])

    # 3. 結構化樓層欄位
    for key in ("發生樓層", "樓層"):
        fl = parse_floors(str(d.get(key) or ""))
        if fl:
            return _floors_loc(fl, f"{key}「{d.get(key)}」")

    # 4. 巡檢表名稱
    for key in _NAME_KEYS:
        if d.get(key):
            fl = parse_floors(str(d[key]))
            if fl:
                return _floors_loc(fl, f"{key}「{d[key]}」")

    # 5. 文字樓層
    text_all = " ".join(filter(None, [task, d.get("區域") or "", d.get("標題") or ""]))
    fl = parse_floors(text_all)
    if fl:
        return _floors_loc(fl, "工作內容中的樓層字樣")

    return _loc("unknown", [], None, "判斷不出位置")


def _floors_loc(fl: list[str], basis: str) -> dict[str, Any]:
    return _loc("floor" if len(fl) == 1 else "multi", fl, None, basis)


def _loc(conf: str, floors: list[str], room: Optional[str], basis: str,
         extra_rooms: Optional[list[str]] = None) -> dict[str, Any]:
    return {
        "confidence": conf,
        "floors": floors,
        "room": room,
        "extra_rooms": extra_rooms or [],
        "basis": basis,
    }
