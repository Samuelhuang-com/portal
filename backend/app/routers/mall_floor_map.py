"""
［舊路徑相容層］樓層巡檢圖 v2.10.107 的商場專用 API —— Prefix: /api/v1/mall-floor-map

⚠️ 2026-10-04 共用化後，正式路徑是 /api/v1/floor-map/{module}（routers/floor_map.py）。
   這裡依 CLAUDE.md §5「不可移除現有端點」保留，全部轉呼叫共用實作（module 固定為
   mall_facility_inspection），前端已不再使用。確認沒有呼叫者後可另案移除。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.routers import floor_map as shared
from app.services.floor_map.providers import get_provider

MODULE = "mall_facility_inspection"

router = APIRouter(dependencies=[Depends(get_current_user)])


class LegacyPointCreate(BaseModel):
    x:              float = Field(..., ge=0, le=1)
    y:              float = Field(..., ge=0, le=1)
    label:          str   = Field(..., min_length=1, max_length=100)
    equipment_code: Optional[str] = Field(None, max_length=50)
    sheet_key:      str   = Field(..., max_length=20)
    item:           str   = Field(..., max_length=50)
    location_desc:  Optional[str] = Field(None, max_length=100)
    supply_area:    Optional[str] = Field(None, max_length=200)
    note:           Optional[str] = Field(None, max_length=300)


class LegacyPointUpdate(BaseModel):
    x:              Optional[float] = Field(None, ge=0, le=1)
    y:              Optional[float] = Field(None, ge=0, le=1)
    label:          Optional[str]   = Field(None, min_length=1, max_length=100)
    equipment_code: Optional[str]   = Field(None, max_length=50)
    sheet_key:      Optional[str]   = Field(None, max_length=20)
    item:           Optional[str]   = Field(None, max_length=50)
    location_desc:  Optional[str]   = Field(None, max_length=100)
    supply_area:    Optional[str]   = Field(None, max_length=200)
    note:           Optional[str]   = Field(None, max_length=300)


def _to_shared(d: dict) -> dict:
    out = {k: d[k] for k in ("x", "y", "label", "equipment_code", "note") if k in d}
    if "sheet_key" in d or "item" in d:
        out["source_ref"] = f"{d.get('sheet_key', '')}|{d.get('item', '')}"
    attrs = {}
    if "location_desc" in d:
        attrs["機房位置"] = d["location_desc"]
    if "supply_area" in d:
        attrs["供應區域"] = d["supply_area"]
    if attrs:
        out["attrs"] = attrs
    return out


@router.get("/floors", summary="［舊］樓層清單與設備組")
def list_floors(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return shared.module_meta(MODULE, db, user)


@router.get("/floors/{floor_key}/image", summary="［舊］樓層底圖")
def floor_image(floor_key: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return shared.floor_image(floor_key, db, user)


@router.get("/floors/{floor_key}/points", summary="［舊］樓層點位")
def list_points(floor_key: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = get_provider(MODULE)
    shared._require(user, db, p.view_permission)
    shared._floor(p, floor_key)
    return {"points": [shared.svc.point_out(x, p) for x in shared.svc.active_points(db, MODULE, floor_key)]}


@router.get("/floors/{floor_key}/status", summary="［舊］點位＋當日狀態")
def floor_status(floor_key: str, date: str = Query(...),
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return shared.floor_status(MODULE, floor_key, date, db, user)


@router.get("/group-month", summary="［舊］設備組整月每日狀態")
def group_month(sheet_key: str = Query(...), item: str = Query(...),
                year: int = Query(..., ge=2020, le=2035), month: int = Query(..., ge=1, le=12),
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return shared.month_status(MODULE, f"{sheet_key}|{item}", year, month, db, user)


@router.post("/floors/{floor_key}/points", summary="［舊］新增點位")
def create_point(floor_key: str, body: LegacyPointCreate,
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return shared.create_point(MODULE, floor_key, shared.PointCreate(**_to_shared(body.model_dump())), db, user)


@router.patch("/points/{point_id}", summary="［舊］修改／移動點位")
def update_point(point_id: int, body: LegacyPointUpdate,
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    data = _to_shared(body.model_dump(exclude_unset=True))
    return shared.update_point(MODULE, point_id, shared.PointUpdate(**data), db, user)


@router.delete("/points/{point_id}", summary="［舊］停用點位")
def delete_point(point_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return shared.delete_point(MODULE, point_id, db, user)
