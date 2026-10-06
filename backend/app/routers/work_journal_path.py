"""
人員動線 API（集團工務決策駕駛艙「人員動線」TAB）— 2026-10-05 新增
Prefix: /api/v1/work-journal/path

資料來源：與工作日誌頁籤同一份 rows（routers/work_journal.py::_build_daily，person_scope='named'），
          不另開口徑；位置由 services/staff_path/locator.py 解析。

⚠️ 畫出來的是「依時間串起工作地點的推定動線」，不是定位軌跡。

端點：
  GET /day               指定日期每位人員的停留點序列＋統計
  GET /hotel-floor-plan  客房標準層向量幾何（建築平面資訊，需登入＋權限，不放公開靜態路徑）
"""
from __future__ import annotations

import re
from datetime import date as _date, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.time import twnow
from app.core.config import settings
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.routers.work_journal import _build_daily, _row_venue, _MALL_FI_PATHS, _FULL_BI_PATHS
from app.models.floor_map import FloorMapPoint
from app.services.dazhi_repair_service import normalize_repair_type
from app.services.floor_map.providers import get_provider
from app.services.staff_path.locator import (
    FLOOR_INDEX, building_floors, load_hotel_plan, resolve_row,
)

# 沿用集團工務決策駕駛艙的頁面權限（行蹤資料，後端也要擋，不只靠前端藏選單）
PERM = "exec_work_dashboard_view"

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── 白名單（2026-10-05 使用者裁示：只有指定的人看得到，系統管理員也要限制）──────────
# 不用權限 key：system_admin 的 "*" 會自動通過任何 key，且 CLAUDE.md §11.4 禁止改 "*" 語意。
# 名單放在各 Server 的 .env：STAFF_PATH_ALLOWED_EMAILS（逗號／分號分隔；留空＝沒有人看得到）。
def _allowed_emails() -> set[str]:
    raw = settings.STAFF_PATH_ALLOWED_EMAILS or ""
    return {e.strip().lower() for e in re.split(r"[,;]", raw) if e.strip()}


def is_staff_path_allowed(user: User) -> bool:
    return (getattr(user, "email", "") or "").strip().lower() in _allowed_emails()


def require_staff_path(user: User = Depends(require_permission(PERM))) -> User:
    """頁面權限（集團決策 Dashboard）＋白名單，兩者都要有。"""
    if not is_staff_path_allowed(user):
        raise HTTPException(status_code=403, detail="人員動線尚未開放給此帳號")
    return user


@router.get("/access", summary="人員動線 — 目前帳號是否可看（前端據此決定是否顯示 TAB）")
def get_staff_path_access(user: User = Depends(get_current_user)):
    return {"allowed": is_staff_path_allowed(user)}

_DT_RE = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})")
_HM_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def _minutes(dt_full: str, hm: str, base: _date) -> Optional[int]:
    """換算成「距所選日期 00:00 的分鐘數」；跨日會小於 0 或大於 1440。"""
    m = _DT_RE.match(dt_full or "")
    if m:
        y, mo, d, hh, mi = map(int, m.groups())
        try:
            delta = datetime(y, mo, d, hh, mi) - datetime(base.year, base.month, base.day)
        except ValueError:
            return None
        return int(delta.total_seconds() // 60)
    m = _HM_RE.match(hm or "")
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    return None


# ── 工作視角人物樣式（2026-10-06 使用者採用 P01～P15）───────────────────────────
# 由上往下，第一個符合的就用；前端 staffPoses.tsx 依代碼畫人物。
_PM_SOURCES = {"hotel_pm", "mall_pm", "full_bldg_pm"}
_TRAIN_RE = re.compile(r"訓練|上課|會議|講習")
_LOCK_RE = re.compile(r"門鎖|房卡|讀卡|電子鎖")
_REPAIR_POSE = {   # 報修類型（normalize_repair_type 標準類型）→ 樣式
    "空調": "P08",
    "衛廁": "P09", "給排水": "P09",
    "機電": "P10", "照明": "P10",
    "內裝": "P11", "建築": "P11",
    "弱電": "P12", "監控": "P12",
}


def _pose_of(r: dict) -> str:
    src = r.get("source") or ""
    task = r.get("task") or ""
    cat = r.get("category") or ""
    if src == "other_tasks" and cat == "緊急事件":
        return "P13"                       # 緊急事件・警示燈奔跑
    if _TRAIN_RE.search(task):
        return "P14"                       # 白板・訓練／會議
    if src == "full_bi":
        return "P02"                       # 整棟巡檢（機房／地下室）＝安全帽＋手電筒
    if src in ("mall_fi", "hotel_di"):
        return "P03"                       # 商場工務巡檢／飯店每日巡檢＝安全帽＋檢查板
    if src == "hotel_mr":
        return "P04"                       # 抄表
    if src in _PM_SOURCES:
        return "P05"                       # 例行維護＝安全帽＋扳手
    if src == "ihg":
        return "P06"                       # 客房保養＝清潔推車
    if src in ("dazhi", "luqun"):
        if _LOCK_RE.search(task):
            return "P12"                   # 門鎖（資料上常歸「內裝」，以關鍵字優先）
        d = r.get("detail") or {}
        t = normalize_repair_type(d.get("報修類型") or "", d.get("標題") or task, d.get("發生樓層") or "")
        return _REPAIR_POSE.get(t, "P07")  # 其他報修＝提工具箱
    if src == "other_tasks":
        return "P15"                       # 上級交辦＝拿文件走動
    return "P01"                           # 預設＝坐著打字


def _build_stops(rows: list[dict], base: _date) -> list[dict[str, Any]]:
    stops = []
    for r in rows:
        loc = resolve_row(r)
        st = _minutes(r.get("start_dt") or "", r.get("start_time") or "", base)
        et = _minutes(r.get("end_dt") or "", r.get("end_time") or "", base)
        wm = r.get("work_min")
        # 進行中：已打卡開始、還沒填結束（2026-10-06，工作視角／LIVE 用）
        is_open = st is not None and not (r.get("end_dt") or r.get("end_time"))
        if st is not None and et is None and wm:
            et = st + int(wm)
        if st is not None and et is not None and et < st:
            et = st
        stops.append({
            **loc,
            "start_min": st,
            "end_min": et,
            "start_time": r.get("start_time") or "",
            "end_time": r.get("end_time") or "",
            "start_dt": r.get("start_dt") or "",
            "end_dt": r.get("end_dt") or "",
            "work_min": wm,
            "open": is_open,
            "pose": _pose_of(r),
            # 沒有實際起迄、工時只是預估（週期保養 fallback）——畫面需可辨識
            "estimated": bool(r.get("est_min")) and not (r.get("start_time") or r.get("end_time")),
            "venue": _row_venue(r),
            # 原始 row（明細 Drawer 用，§7）
            "row": r,
        })

    # 有時間的依起始時間排序；沒時間的排最後（維持工作日誌原順序）
    timed = sorted([s for s in stops if s["start_min"] is not None], key=lambda s: (s["start_min"], s["end_min"] or 0))
    untimed = [s for s in stops if s["start_min"] is None]
    ordered = timed + untimed

    prev_end: Optional[int] = None
    for i, s in enumerate(ordered, 1):
        s["seq"] = i
        s["overlap"] = bool(s["start_min"] is not None and prev_end is not None and s["start_min"] < prev_end)
        if s["end_min"] is not None:
            prev_end = max(prev_end or s["end_min"], s["end_min"])
    return ordered


# ── 巡檢點位（樓層巡檢圖）────────────────────────────────────────────────────
# 工作日誌來源 → 樓層巡檢圖模組；巡檢表以 Ragic 路徑對回 sheet_key（＝點位 source_ref 的前半段）
_POINT_SOURCES: dict[str, tuple[str, dict[str, str]]] = {
    "mall_fi": ("mall_facility_inspection", _MALL_FI_PATHS),
    "full_bi": ("full_building_inspection", _FULL_BI_PATHS),
}


def _sheet_key_of(row: dict) -> Optional[tuple[str, str]]:
    spec = _POINT_SOURCES.get(row.get("source") or "")
    if not spec:
        return None
    module, paths = spec
    url = row.get("ragic_url") or ""
    for sk, path in paths.items():
        if f"/{path}/" in url:
            return module, sk
    return None


def _attach_points(db: Session, base: _date, persons: list[dict]) -> None:
    """巡檢類停留點：掛上該巡檢表涵蓋的樓層巡檢圖點位（座標＋當日狀態）。

    ⚠️ 巡檢紀錄只有整張表的起迄時間，沒有每一點的檢查時間；點位順序沿用樓層巡檢圖的
       sort_order（＝推測的巡檢順序），前端連線時須標示「順序為推測」。
    """
    wanted: dict[str, set[str]] = {}
    for p in persons:
        for s in p["stops"]:
            mk = _sheet_key_of(s["row"])
            if mk:
                s["_mk"] = mk
                wanted.setdefault(mk[0], set()).add(mk[1])
    if not wanted:
        return

    insp_date = base.strftime("%Y/%m/%d")
    by_sheet: dict[tuple[str, str], list[dict]] = {}
    for module, sheets in wanted.items():
        provider = get_provider(module)
        if not provider:
            continue
        pts = (
            db.query(FloorMapPoint)
            .filter(FloorMapPoint.module == module, FloorMapPoint.is_active.is_(True))
            .order_by(FloorMapPoint.sort_order, FloorMapPoint.id)
            .all()
        )
        pts = [pt for pt in pts if pt.source_ref.split("|", 1)[0] in sheets]
        if not pts:
            continue
        try:
            day = provider.day_status(db, insp_date)
        except Exception:  # 狀態算不出來不影響動線本身
            day = {}
        gmap = provider.group_map()
        for pt in pts:
            sk = pt.source_ref.split("|", 1)[0]
            g = gmap.get(pt.source_ref, {})
            by_sheet.setdefault((module, sk), []).append({
                "id": pt.id,
                "floor_key": pt.floor_key,
                "x": pt.x,
                "y": pt.y,
                "label": pt.label,
                "equipment_code": pt.equipment_code or "",
                "group_label": g.get("label", pt.source_ref),
                "shared_label": g.get("shared_label", ""),
                "placement": pt.placement or "confirmed",
                "status": (day.get(pt.source_ref) or {}).get("status", "no_record"),
            })

    for p in persons:
        for s in p["stops"]:
            mk = s.pop("_mk", None)
            pts = by_sheet.get(mk) if mk else None
            if not pts:
                continue
            s["points"] = pts
            fl = {pt["floor_key"] for pt in pts}
            s["floors"] = sorted(set(s["floors"]) | fl, key=lambda k: FLOOR_INDEX.get(k, 99))
            s["confidence"] = "point"
            s["basis"] = f"樓層巡檢圖點位 {len(pts)} 點（巡檢表 {mk[1].upper()}；點位順序為推測）"


def _person_stats(stops: list[dict]) -> dict[str, Any]:
    located = [s for s in stops if s["confidence"] != "unknown"]
    # 換層次數：依時間序，單一樓層停留點之間樓層不同的次數
    single = [s["floors"][0] for s in stops
              if s["start_min"] is not None and len(s["floors"]) == 1]
    changes = sum(1 for a, b in zip(single, single[1:]) if a != b)
    # 垂直移動層數（例：5F→B2 = 6 層，B1 與 1F 相鄰）
    vertical = sum(abs(FLOOR_INDEX[a] - FLOOR_INDEX[b]) for a, b in zip(single, single[1:]))
    floors = sorted({f for s in stops for f in s["floors"]}, key=lambda k: FLOOR_INDEX[k])
    timed = [s for s in stops if s["start_min"] is not None]
    return {
        "stops": len(stops),
        "located": len(located),
        "rooms": len({s["room"] for s in stops if s["room"]}),
        "floor_changes": changes,
        "vertical_floors": vertical,
        "floors": floors,
        "work_min": sum(int(s["work_min"] or 0) for s in stops),
        "first_min": min((s["start_min"] for s in timed), default=None),
        "last_min": max((s["end_min"] if s["end_min"] is not None else s["start_min"] for s in timed), default=None),
        "overlaps": sum(1 for s in stops if s["overlap"]),
        "untimed": len(stops) - len(timed),
    }


@router.get("/day", summary="人員動線 — 指定日期每位人員的工作地點序列",
            dependencies=[Depends(require_staff_path)])
def get_staff_path_day(
    date: Optional[str] = Query(None, description="YYYY-MM-DD；省略＝今天（台灣時間）"),
    venue: str = Query("all", pattern="^(all|hotel|mall)$"),
    db: Session = Depends(get_db),
):
    if date:
        try:
            base = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=422, detail="date 格式須為 YYYY-MM-DD")
    else:
        base = twnow().date()

    daily = _build_daily(db, base.year, base.month, base.day, person_scope="named", venue=venue)

    persons = []
    for p in daily["persons"]:
        stops = _build_stops(p["rows"], base)
        persons.append({"person": p["person"], "stats": _person_stats(stops), "stops": stops})
    _attach_points(db, base, persons)
    for p in persons:
        p["stats"] = _person_stats(p["stops"])
    persons.sort(key=lambda p: (-p["stats"]["work_min"], p["person"]))

    all_stops = [s for p in persons for s in p["stops"]]
    conf_count: dict[str, int] = {"room": 0, "point": 0, "floor": 0, "multi": 0, "unknown": 0}
    for s in all_stops:
        conf_count[s["confidence"]] = conf_count.get(s["confidence"], 0) + 1

    return {
        "date": base.isoformat(),
        "venue": venue,
        "floors": building_floors(),
        "persons": persons,
        "summary": {
            "persons": len(persons),
            "stops": len(all_stops),
            "confidence": conf_count,
            "located_pct": round(100 * (len(all_stops) - conf_count["unknown"]) / len(all_stops), 1) if all_stops else 0,
        },
    }


@router.get("/hotel-floor-plan", summary="人員動線 — 客房標準層向量平面圖",
            dependencies=[Depends(require_staff_path)])
def get_hotel_floor_plan():
    return load_hotel_plan()
