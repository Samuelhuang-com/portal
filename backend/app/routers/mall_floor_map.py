"""
樓層巡檢圖（Floor Plan Inspection Map）API Router
Prefix: /api/v1/mall-floor-map

規格：docs/SPEC_floor_plan_inspection.md

權限
  檢視：mall_facility_inspection_view（與商場工務巡檢頁面相同）
  編輯點位：mall_floor_map_edit（「樓層巡檢圖－編輯點位」，需明確指派）

端點
  GET    /floors                          — 樓層清單（含底圖尺寸）與可選設備組
  GET    /floors/{floor_key}/image        — 底圖（需登入；前端以 blob 載入，不走公開靜態檔）
  GET    /floors/{floor_key}/points       — 該樓層啟用中的點位
  GET    /floors/{floor_key}/status?date= — 該樓層點位＋當日各設備組狀態與檢查明細
  GET    /group-month?sheet_key&item&year&month — 某設備組整月每日狀態
  POST   /floors/{floor_key}/points       — 新增點位（編輯權限）
  PATCH  /points/{point_id}               — 修改／移動點位（編輯權限）
  DELETE /points/{point_id}               — 停用點位（編輯權限；不硬刪）
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.time import twnow
from app.dependencies import require_permission
from app.models.mall_floor_map import MallFloorMapPoint
from app.models.user import User
from app.services.mall_daily_inspection_sheet import normalize_date
from app.services import mall_floor_map_service as svc

VIEW_KEY = "mall_facility_inspection_view"
EDIT_KEY = "mall_floor_map_edit"

router = APIRouter(dependencies=[Depends(require_permission(VIEW_KEY))])


# ── Schema ────────────────────────────────────────────────────────────────────

class PointCreate(BaseModel):
    x:              float = Field(..., ge=0, le=1)
    y:              float = Field(..., ge=0, le=1)
    label:          str   = Field(..., min_length=1, max_length=100)
    equipment_code: Optional[str] = Field(None, max_length=50)
    sheet_key:      str   = Field(..., max_length=20)
    item:           str   = Field(..., max_length=50)
    location_desc:  Optional[str] = Field(None, max_length=100)
    supply_area:    Optional[str] = Field(None, max_length=200)
    note:           Optional[str] = Field(None, max_length=300)


class PointUpdate(BaseModel):
    x:              Optional[float] = Field(None, ge=0, le=1)
    y:              Optional[float] = Field(None, ge=0, le=1)
    label:          Optional[str]   = Field(None, min_length=1, max_length=100)
    equipment_code: Optional[str]   = Field(None, max_length=50)
    sheet_key:      Optional[str]   = Field(None, max_length=20)
    item:           Optional[str]   = Field(None, max_length=50)
    location_desc:  Optional[str]   = Field(None, max_length=100)
    supply_area:    Optional[str]   = Field(None, max_length=200)
    note:           Optional[str]   = Field(None, max_length=300)


# ── 輔助 ──────────────────────────────────────────────────────────────────────

def _check_floor(floor_key: str) -> None:
    if floor_key not in svc.FLOOR_KEYS:
        raise HTTPException(status_code=404, detail=f"未知的樓層：{floor_key}")


def _who(user: User) -> str:
    return (getattr(user, "full_name", None) or getattr(user, "email", None) or str(user.id))[:100]


def _point_out(p: MallFloorMapPoint) -> dict:
    meta = svc.group_meta(p.sheet_key, p.item)
    return {
        "id":             p.id,
        "floor_key":      p.floor_key,
        "x":              p.x,
        "y":              p.y,
        "label":          p.label,
        "equipment_code": p.equipment_code or "",
        "sheet_key":      p.sheet_key,
        "item":           p.item,
        "group_key":      meta["key"],
        "system":         meta["system"],
        "shared_label":   meta["shared_label"],
        "location_desc":  p.location_desc or "",
        "supply_area":    p.supply_area or "",
        "note":           p.note or "",
        "updated_by":     p.updated_by or "",
        "updated_at":     p.updated_at.strftime("%Y-%m-%d %H:%M") if p.updated_at else "",
    }


def _active_points(db: Session, floor_key: str) -> list[MallFloorMapPoint]:
    return (
        db.query(MallFloorMapPoint)
        .filter(MallFloorMapPoint.floor_key == floor_key, MallFloorMapPoint.is_active.is_(True))
        .order_by(MallFloorMapPoint.sort_order, MallFloorMapPoint.id)
        .all()
    )


# ── 讀取 ──────────────────────────────────────────────────────────────────────

@router.get("/floors", summary="樓層清單與可選設備組")
def list_floors():
    groups = [svc.group_meta(g["sheet_key"], g["item"]) for g in svc.EQUIPMENT_GROUPS]
    systems = list(dict.fromkeys(g["system"] for g in svc.EQUIPMENT_GROUPS))
    return {"floors": svc.FLOORS, "groups": groups, "systems": systems}


@router.get("/floors/{floor_key}/image", summary="樓層底圖（需登入）")
def floor_image(floor_key: str):
    _check_floor(floor_key)
    path = svc.FLOOR_PLAN_DIR / f"{floor_key}.webp"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"找不到底圖檔：{path.name}")
    return FileResponse(path, media_type="image/webp", headers={"Cache-Control": "private, max-age=86400"})


@router.get("/floors/{floor_key}/points", summary="樓層點位")
def list_points(floor_key: str, db: Session = Depends(get_db)):
    _check_floor(floor_key)
    return {"points": [_point_out(p) for p in _active_points(db, floor_key)]}


@router.get("/floors/{floor_key}/status", summary="樓層點位＋指定日期各設備組狀態")
def floor_status(
    floor_key: str,
    date: str = Query(..., description="YYYY-MM-DD 或 YYYY/MM/DD"),
    db: Session = Depends(get_db),
):
    _check_floor(floor_key)
    insp_date = normalize_date(date)
    if not insp_date:
        raise HTTPException(status_code=422, detail=f"日期格式錯誤：{date}")

    points = [_point_out(p) for p in _active_points(db, floor_key)]
    all_groups = svc.day_groups(db, insp_date)
    used = {p["group_key"] for p in points}
    groups = {k: v for k, v in all_groups.items() if k in used}
    for p in points:
        p["status"] = groups.get(p["group_key"], {}).get("status", "no_record")
    return {"date": insp_date, "floor_key": floor_key, "points": points, "groups": groups}


@router.get("/group-month", summary="某設備組整月每日狀態")
def group_month(
    sheet_key: str = Query(...),
    item:      str = Query(...),
    year:      int = Query(..., ge=2020, le=2035),
    month:     int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
):
    if not svc.is_valid_group(sheet_key, item):
        raise HTTPException(status_code=422, detail=f"未知的設備組：{sheet_key} / {item}")
    return {
        "year": year, "month": month,
        "group": svc.group_meta(sheet_key, item),
        "days": svc.month_group_days(db, sheet_key, item, year, month),
    }


# ── 編輯（需 mall_floor_map_edit）──────────────────────────────────────────────

@router.post("/floors/{floor_key}/points", summary="新增點位")
def create_point(
    floor_key: str,
    body: PointCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_KEY)),
):
    _check_floor(floor_key)
    if not svc.is_valid_group(body.sheet_key, body.item):
        raise HTTPException(status_code=422, detail=f"未知的設備組：{body.sheet_key} / {body.item}")
    now = twnow()
    p = MallFloorMapPoint(
        floor_key=floor_key, **body.model_dump(),
        sort_order=0, is_active=True,
        created_by=_who(user), updated_by=_who(user), created_at=now, updated_at=now,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _point_out(p)


@router.patch("/points/{point_id}", summary="修改／移動點位")
def update_point(
    point_id: int,
    body: PointUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_KEY)),
):
    p = db.get(MallFloorMapPoint, point_id)
    if not p or not p.is_active:
        raise HTTPException(status_code=404, detail="點位不存在")
    data = body.model_dump(exclude_unset=True)
    sk, item = data.get("sheet_key", p.sheet_key), data.get("item", p.item)
    if not svc.is_valid_group(sk, item):
        raise HTTPException(status_code=422, detail=f"未知的設備組：{sk} / {item}")
    for k, v in data.items():
        setattr(p, k, v)
    p.updated_by = _who(user)
    p.updated_at = twnow()
    db.commit()
    db.refresh(p)
    return _point_out(p)


@router.delete("/points/{point_id}", summary="停用點位（不硬刪）")
def delete_point(
    point_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_KEY)),
):
    p = db.get(MallFloorMapPoint, point_id)
    if not p or not p.is_active:
        raise HTTPException(status_code=404, detail="點位不存在")
    p.is_active = False
    p.updated_by = _who(user)
    p.updated_at = twnow()
    db.commit()
    return {"ok": True, "id": point_id}
