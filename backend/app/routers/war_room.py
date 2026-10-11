"""
戰情 KPI（War Room）API — 2026-10-10 新增，第一階模組
Prefix: /api/v1/war-room

把「人員動態（工作日誌動線）」「樓層巡檢圖點位狀態」「未完成報修」「IHG 客房保養」
依樓層／房間／設備整合成一張整棟戰情圖，並提供房間與設備的履歷查詢。

權限（兩者都要有，見 CLAUDE.md §11.7）：
  1. 頁面權限 war_room_view
  2. 白名單 .env WAR_ROOM_ALLOWED_EMAILS（留空＝沒有任何人看得到，系統管理員也受限）

端點：
  GET /access                 目前帳號能否看（只需登入）
  GET /floors?date=           各樓層戰情（人員工作、巡檢點位狀態、未完成報修）＋全棟 KPI
  GET /hotel-floor-plan       客房標準層向量幾何（3D 樓層視圖用）
  GET /points                 全部樓層巡檢圖點位（履歷查詢下拉用）
  GET /point/{id}?date=&year=&month=   設備履歷：當日檢查結果＋當月每日狀況
  GET /room/{room_no}?days=   房間履歷：報修紀錄＋IHG 客房保養紀錄
  GET /alerts?date=           異常告警清單 A1～A5（只偵測，不寄信）
  POST /alerts/send           寄出所選告警（dry_run=true 只回傳會寄給誰）
  GET/PUT /alert-settings     告警門檻與自動寄送開關
  GET /alert-log              最近的寄送紀錄
  GET/PUT /alert-recipients   告警收件人名單（飯店／商場分開，由使用者維護）

口徑（皆為「今日現況」）：
  - 未完成報修：排除 Ragic 已刪除（is_ragic_deleted）與取消／作廢；
      飯店＝處理狀態 ∈ dazhi_repair_service.UNFINISHED_STATUSES；
      商場＝處理狀態 ∉ luqun_repair_service.COMPLETED_STATUSES
  - 巡檢點位狀態：provider.day_status（與樓層巡檢圖同一份，四種狀態）
  - 人員工作：人員動線 /work-journal/path/day 同一份資料
"""
from __future__ import annotations

import re
from datetime import date as _date, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.time import twnow
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.models.dazhi_repair import DazhiRepairCase
from app.models.luqun_repair import LuqunRepairCase
from app.models.floor_map import FloorMapPoint
from app.models.ihg_room_maintenance import IHGRoomMaintenanceMaster, IHGRoomMaintenanceDetail
from app.routers.ihg_room_maintenance import CANONICAL_ROOM_SET, _calc_record_status
from app.routers.work_journal import _ragic_url, _SOURCE_PATH
from app.routers.work_journal_path import get_staff_path_day
from app.services import dazhi_repair_service as dazhi_svc
from app.services import luqun_repair_service as luqun_svc
from app.services.floor_map.providers import PROVIDERS, get_provider
from app.services.staff_path.locator import (
    FLOOR_INDEX, building_floors, load_hotel_plan, parse_floors, parse_rooms, room_floor,
)

PERM = "war_room_view"

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── 白名單（CLAUDE.md §11.7）─────────────────────────────────────────────────
def _allowed_emails() -> set[str]:
    raw = getattr(settings, "WAR_ROOM_ALLOWED_EMAILS", "") or ""
    return {e.strip().lower() for e in re.split(r"[,;]", raw) if e.strip()}


def is_war_room_allowed(user: User) -> bool:
    return (getattr(user, "email", "") or "").strip().lower() in _allowed_emails()


def require_war_room(user: User = Depends(require_permission(PERM))) -> User:
    if not is_war_room_allowed(user):
        raise HTTPException(status_code=403, detail="戰情 KPI 尚未開放給此帳號")
    return user


@router.get("/access", summary="戰情 KPI — 目前帳號是否可看")
def get_access(user: User = Depends(get_current_user)):
    return {"allowed": is_war_room_allowed(user)}


# ── 共用 ─────────────────────────────────────────────────────────────────────
def _parse_date(s: Optional[str]) -> _date:
    if not s:
        return twnow().date()
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="date 格式須為 YYYY-MM-DD")


def _repair_location(c: Any) -> tuple[Optional[str], list[str]]:
    """報修案件 → (房號, 樓層清單)。房號優先用同步時解析好的 room_no，須在 IHG 規範清單內。"""
    room = (c.room_no or "").strip()
    if room not in CANONICAL_ROOM_SET:
        rooms = parse_rooms(f"{c.floor or ''} {c.title or ''}")
        room = rooms[0] if rooms else ""
    if room:
        return room, [room_floor(room)]
    floors = parse_floors(c.floor or "") or parse_floors(c.title or "")
    return None, floors


def _repair_out(c: Any, source: str, now: datetime) -> dict[str, Any]:
    room, floors = _repair_location(c)
    occ = c.occurred_at
    return {
        "source": source,
        "source_label": "飯店工務報修" if source == "dazhi" else "商場工務報修",
        "ragic_id": c.ragic_id,
        "ragic_url": _ragic_url(_SOURCE_PATH[source], c.ragic_id),
        "case_no": c.case_no or "",
        "title": c.title or "",
        "status": c.status or "",
        "repair_type": c.repair_type or "",
        "floor_raw": c.floor or "",
        "room": room,
        "floors": floors,
        "responsible_unit": c.responsible_unit or "",
        "occurred_at": occ.strftime("%Y-%m-%d %H:%M") if occ else "",
        "completed_at": c.completed_at.strftime("%Y-%m-%d") if c.completed_at else "",
        "wait_days": (now - occ).days if occ else None,
    }


def _open_repairs(db: Session) -> list[dict[str, Any]]:
    """目前未完成的報修（今日現況），飯店＋商場。"""
    now = twnow()
    out: list[dict[str, Any]] = []
    hotel = (
        db.query(DazhiRepairCase)
        .filter(DazhiRepairCase.is_ragic_deleted.is_(False),
                DazhiRepairCase.status.in_(list(dazhi_svc.UNFINISHED_STATUSES)))
        .all()
    )
    out += [_repair_out(c, "dazhi", now) for c in hotel if not c.is_excluded_flag]
    mall = (
        db.query(LuqunRepairCase)
        .filter(LuqunRepairCase.is_ragic_deleted.is_(False))
        .all()
    )
    out += [
        _repair_out(c, "luqun", now) for c in mall
        if not c.is_excluded_flag and not luqun_svc.is_completed(c.status or "")
    ]
    out.sort(key=lambda r: -(r["wait_days"] or 0))
    return out


def _point_out(p: FloorMapPoint, group: dict, day: dict) -> dict[str, Any]:
    provider = get_provider(p.module)
    return {
        "id": p.id,
        "module": p.module,
        "module_label": provider.label if provider else p.module,
        "floor_key": p.floor_key,
        "x": p.x,
        "y": p.y,
        "label": p.label,
        "equipment_code": p.equipment_code or "",
        "source_ref": p.source_ref,
        "group_label": group.get("label", p.source_ref),
        "system": group.get("system", ""),
        "shared_label": group.get("shared_label", ""),
        "placement": p.placement or "confirmed",
        "status": (day.get(p.source_ref) or {}).get("status", "no_record"),
    }


def _all_points(db: Session, insp_date: Optional[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for module, provider in PROVIDERS.items():
        pts = (
            db.query(FloorMapPoint)
            .filter(FloorMapPoint.module == module, FloorMapPoint.is_active.is_(True))
            .order_by(FloorMapPoint.floor_key, FloorMapPoint.sort_order, FloorMapPoint.id)
            .all()
        )
        if not pts:
            continue
        day: dict = {}
        if insp_date:
            try:
                day = provider.day_status(db, insp_date)
            except Exception:
                db.rollback()
                day = {}
        gmap = provider.group_map()
        out += [_point_out(p, gmap.get(p.source_ref, {}), day) for p in pts]
    return out


# ── 樓層戰情 ─────────────────────────────────────────────────────────────────
@router.get("/floors", summary="戰情 KPI — 各樓層人員工作／巡檢點位／未完成報修",
            dependencies=[Depends(require_war_room)])
def get_floors(
    date: Optional[str] = Query(None, description="YYYY-MM-DD；省略＝今天"),
    db: Session = Depends(get_db),
):
    base = _parse_date(date)
    floors = building_floors()
    keys = [f["key"] for f in floors]
    board: dict[str, dict[str, Any]] = {
        k: {"people": {}, "stops": 0, "work_min": 0, "rooms": set(), "points": [], "repairs": []}
        for k in keys + ["__unknown"]
    }

    # 1. 人員工作（與人員動態同一份）
    day = get_staff_path_day(date=base.isoformat(), venue="all", db=db)
    for p in day["persons"]:
        for s in p["stops"]:
            fl = s["floors"] or ["__unknown"]
            for f in fl:
                b = board.get(f) or board["__unknown"]
                b["stops"] += 1
                b["work_min"] += int(s.get("work_min") or 0) // max(1, len(fl))
                person = b["people"].setdefault(p["person"], {"person": p["person"], "stops": []})
                person["stops"].append({
                    "seq": s["seq"], "start_time": s["start_time"], "end_time": s["end_time"],
                    "task": s["row"]["task"], "room": s["room"], "confidence": s["confidence"],
                    "source_label": s["row"]["source_label"], "row": s["row"],
                })
                if s["room"] and f == room_floor(s["room"]):
                    b["rooms"].add(s["room"])

    # 2. 巡檢點位（當日狀態）
    for pt in _all_points(db, base.strftime("%Y/%m/%d")):
        (board.get(pt["floor_key"]) or board["__unknown"])["points"].append(pt)

    # 3. 未完成報修（今日現況）
    repairs = _open_repairs(db)
    for r in repairs:
        fl = r["floors"] or ["__unknown"]
        (board.get(fl[0]) or board["__unknown"])["repairs"].append(r)

    out_floors = []
    for f in floors + [{"key": "__unknown", "label": "未定位", "kind": "none", "rooms": []}]:
        b = board[f["key"]]
        pts = b["points"]
        cnt = {s: sum(1 for p in pts if p["status"] == s) for s in ("normal", "abnormal", "unchecked", "no_record")}
        out_floors.append({
            "key": f["key"],
            "label": f["label"],
            "kind": f["kind"],
            "rooms": f.get("rooms", []),
            "people": sorted(b["people"].values(), key=lambda x: x["person"]),
            "people_count": len(b["people"]),
            "stops": b["stops"],
            "work_min": b["work_min"],
            "rooms_visited": sorted(b["rooms"]),
            "points": pts,
            "point_status": cnt,
            "repairs": b["repairs"],
            "repairs_count": len(b["repairs"]),
        })

    all_pts = [p for f in out_floors for p in f["points"]]
    return {
        "date": base.isoformat(),
        "generated_at": twnow().strftime("%Y-%m-%d %H:%M"),
        "floors": out_floors,
        "summary": {
            "persons": day["summary"]["persons"],
            "stops": day["summary"]["stops"],
            "work_min": sum(p["stats"]["work_min"] for p in day["persons"]),
            "points": len(all_pts),
            "abnormal": sum(1 for p in all_pts if p["status"] == "abnormal"),
            "unchecked": sum(1 for p in all_pts if p["status"] == "unchecked"),
            "no_record": sum(1 for p in all_pts if p["status"] == "no_record"),
            "repairs_open": len(repairs),
            "repairs_open_hotel": sum(1 for r in repairs if r["source"] == "dazhi"),
            "repairs_open_mall": sum(1 for r in repairs if r["source"] == "luqun"),
            "repairs_over_7d": sum(1 for r in repairs if (r["wait_days"] or 0) > 7),
        },
    }


# ── 設備（巡檢點位）履歷 ──────────────────────────────────────────────────────
@router.get("/hotel-floor-plan", summary="戰情 KPI — 客房標準層向量平面圖（3D 樓層用）",
            dependencies=[Depends(require_war_room)])
def get_hotel_floor_plan():
    """與人員動線同一份幾何；另開端點是因為戰情 KPI 不要求 STAFF_PATH_ALLOWED_EMAILS。"""
    return load_hotel_plan()


@router.get("/points", summary="戰情 KPI — 全部樓層巡檢圖點位清單",
            dependencies=[Depends(require_war_room)])
def list_points(db: Session = Depends(get_db)):
    pts = _all_points(db, None)
    pts.sort(key=lambda p: (FLOOR_INDEX.get(p["floor_key"], 99), p["module"], p["label"]))
    rooms = [r for f in building_floors() for r in f.get("rooms", [])]
    return {"points": pts, "rooms": rooms}


@router.get("/point/{point_id}", summary="戰情 KPI — 設備履歷（當日檢查結果＋當月每日狀況）",
            dependencies=[Depends(require_war_room)])
def get_point(
    point_id: int,
    date: Optional[str] = Query(None, description="YYYY-MM-DD；省略＝今天"),
    db: Session = Depends(get_db),
):
    p = db.query(FloorMapPoint).filter(FloorMapPoint.id == point_id, FloorMapPoint.is_active.is_(True)).first()
    if not p:
        raise HTTPException(status_code=404, detail="找不到這個點位")
    provider = get_provider(p.module)
    if not provider:
        raise HTTPException(status_code=404, detail=f"未知的模組：{p.module}")
    base = _parse_date(date)
    day = provider.day_status(db, base.strftime("%Y/%m/%d"))
    g = day.get(p.source_ref) or {}
    month = provider.month_status(db, p.source_ref, base.year, base.month)
    info = _point_out(p, provider.group_map().get(p.source_ref, {}), day)
    attrs = p.attrs if isinstance(p.attrs, dict) else {}
    info["attrs"] = {k: v for k, v in attrs.items() if v not in (None, "")}
    info["note"] = p.note or ""
    return {
        "date": base.isoformat(),
        "point": info,
        "today": {
            "status": g.get("status", "no_record"),
            "rows": g.get("rows", []),
            "batches": g.get("batches", []),
            "inspectors": g.get("inspectors", []),
            "actual_minutes": g.get("actual_minutes", 0),
        },
        "month": month,
    }


# ── 房間履歷 ─────────────────────────────────────────────────────────────────
@router.get("/room/{room_no}", summary="戰情 KPI — 房間履歷（報修＋IHG 客房保養）",
            dependencies=[Depends(require_war_room)])
def get_room(
    room_no: str,
    days: int = Query(180, ge=7, le=730, description="報修紀錄往回看幾天（未完成的不受限）"),
    db: Session = Depends(get_db),
):
    room = room_no.strip()
    if room not in CANONICAL_ROOM_SET:
        raise HTTPException(status_code=404, detail=f"{room} 不在 IHG 規範房號清單")
    now = twnow()
    since = now - timedelta(days=days)

    repairs: list[dict[str, Any]] = []
    for model, source in ((DazhiRepairCase, "dazhi"), (LuqunRepairCase, "luqun")):
        rows = (
            db.query(model)
            .filter(model.is_ragic_deleted.is_(False))
            .filter((model.room_no == room) | (model.title.contains(room)) | (model.floor.contains(room)))
            .all()
        )
        for c in rows:
            if c.is_excluded_flag:
                continue
            r_room, _ = _repair_location(c)
            if r_room != room:
                continue      # 標題含 613 但其實是別的數字（金額等）→ 以解析結果為準
            open_ = (dazhi_svc.is_unfinished(c.status or "") if source == "dazhi"
                     else not luqun_svc.is_completed(c.status or ""))
            if not open_ and (not c.occurred_at or c.occurred_at < since):
                continue
            item = _repair_out(c, source, now)
            item["open"] = open_
            repairs.append(item)
    repairs.sort(key=lambda r: r["occurred_at"], reverse=True)

    ihg = (
        db.query(IHGRoomMaintenanceMaster)
        .filter(IHGRoomMaintenanceMaster.room_no == room)
        .order_by(IHGRoomMaintenanceMaster.maint_date.desc())
        .limit(12)
        .all()
    )
    ng: dict[str, int] = {}
    if ihg:
        for d in (
            db.query(IHGRoomMaintenanceDetail)
            .filter(IHGRoomMaintenanceDetail.master_ragic_id.in_([m.ragic_id for m in ihg]))
            .all()
        ):
            if (d.result or "").strip().upper() == "NG":
                ng[d.master_ragic_id] = ng.get(d.master_ragic_id, 0) + 1
    ihg_out = [{
        "ragic_id": m.ragic_id,
        "ragic_url": _ragic_url(_SOURCE_PATH["ihg"], m.ragic_id),
        "maint_date": (m.maint_date or "")[:10].replace("/", "-"),
        "maint_year": m.maint_year or "",
        "maint_month": m.maint_month or "",
        "maint_type": m.maint_type or "",
        # 與 IHG 客房保養模組同一判定（raw_json 檢查欄位）：completed / abnormal / pending
        "status": _calc_record_status(m.raw_json),
        "is_completed": bool(m.is_completed),
        "assignee": m.assignee_name or "",
        "checker": m.checker_name or "",
        "work_minutes": round(m.work_minutes) if m.work_minutes is not None else None,
        "ng_count": ng.get(m.ragic_id, 0),
        "notes": m.notes or "",
    } for m in ihg]

    return {
        "room": room,
        "floor": room_floor(room),
        "days": days,
        "repairs": repairs,
        "repairs_open": sum(1 for r in repairs if r["open"]),
        "ihg": ihg_out,
    }


# ── 異常告警（A1～A5；規格 docs/SPEC_war_room.md §7）─────────────────────────
from app.services import war_room_alert_service as alert_svc   # noqa: E402


class AlertSendBody(BaseModel):
    keys: list[str]
    dry_run: bool = True          # 預設乾跑：必須明確傳 false 才會真的寄
    force: bool = False           # True＝忽略去重（已寄過也再寄）


class AlertRecipient(BaseModel):
    email: str
    name: str = ""
    venues: list[str]
    enabled: bool = True


class AlertRecipientsBody(BaseModel):
    recipients: list[AlertRecipient]


class AlertSettingsBody(BaseModel):
    enabled: Optional[dict[str, bool]] = None
    repair_warn_days: Optional[int] = None
    repair_critical_days: Optional[int] = None
    inspect_deadline: Optional[str] = None
    ihg_lookback_days: Optional[int] = None
    repeat_critical_days: Optional[int] = None
    room_repeat_count: Optional[int] = None
    room_repeat_days: Optional[int] = None
    auto_send: Optional[bool] = None


@router.get("/alerts", summary="戰情 KPI — 異常告警清單（只偵測，不寄信）",
            dependencies=[Depends(require_war_room)])
def get_alerts(
    date: Optional[str] = Query(None, description="YYYY-MM-DD；省略＝今天"),
    db: Session = Depends(get_db),
):
    base = _parse_date(date)
    alerts = alert_svc.compute_alerts(db, ref_date=base)
    rc = alert_svc.recipients(db)
    cfg = alert_svc.get_settings(db)
    by_type = {t: sum(1 for a in alerts if a["type"] == t) for t in alert_svc.TYPE_LABEL}
    return {
        "date": base.isoformat(),
        "generated_at": twnow().strftime("%Y-%m-%d %H:%M"),
        "alerts": alerts,
        "summary": {
            "total": len(alerts),
            "critical": sum(1 for a in alerts if a["level"] == "critical"),
            "warning": sum(1 for a in alerts if a["level"] == "warning"),
            "info": sum(1 for a in alerts if a["level"] == "info"),
            "due": sum(1 for a in alerts if a["due"]),
            "by_type": by_type,
        },
        "recipients": {"hotel": rc["hotel"], "mall": rc["mall"]},
        "auto_send": cfg["auto_send"],
        "type_labels": alert_svc.TYPE_LABEL,
    }


@router.post("/alerts/send", summary="戰情 KPI — 寄出所選告警（預設乾跑）")
def post_alerts_send(
    body: AlertSendBody,
    user: User = Depends(require_war_room),
    db: Session = Depends(get_db),
):
    # 不信任前端傳來的內容：用 key 重新偵測，只寄後端自己算出來的項目
    wanted = set(body.keys)
    if not wanted:
        raise HTTPException(status_code=422, detail="請先勾選要寄出的告警")
    alerts = [a for a in alert_svc.compute_alerts(db)
              if a["key"] in wanted and (body.force or a["due"] or body.dry_run)]
    if not alerts:
        raise HTTPException(status_code=409, detail="所選項目已不存在，或今天已寄過（需要再寄請勾「強制再寄」）")
    return alert_svc.send_alerts(
        db, alerts, by=getattr(user, "email", "") or "user", mode="manual",
        dry_run=body.dry_run, title="異常告警",
    )


@router.get("/alert-settings", summary="戰情 KPI — 告警設定",
            dependencies=[Depends(require_war_room)])
def get_alert_settings(db: Session = Depends(get_db)):
    return alert_svc.get_settings(db)


@router.put("/alert-settings", summary="戰情 KPI — 儲存告警設定")
def put_alert_settings(
    body: AlertSettingsBody,
    user: User = Depends(require_war_room),
    db: Session = Depends(get_db),
):
    try:
        return alert_svc.save_settings(
            db, body.model_dump(exclude_none=True), getattr(user, "email", "") or "user")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/alert-log", summary="戰情 KPI — 告警寄送紀錄",
            dependencies=[Depends(require_war_room)])
def get_alert_log(db: Session = Depends(get_db)):
    return {"log": alert_svc.get_log(db)}


@router.get("/alert-recipients", summary="戰情 KPI — 告警收件人名單",
            dependencies=[Depends(require_war_room)])
def get_alert_recipients(db: Session = Depends(get_db)):
    return {"recipients": alert_svc.get_recipient_list(db)}


@router.put("/alert-recipients", summary="戰情 KPI — 儲存告警收件人名單（整份取代）")
def put_alert_recipients(
    body: AlertRecipientsBody,
    user: User = Depends(require_war_room),
    db: Session = Depends(get_db),
):
    try:
        return {"recipients": alert_svc.save_recipient_list(
            db, [x.model_dump() for x in body.recipients], getattr(user, "email", "") or "user")}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
