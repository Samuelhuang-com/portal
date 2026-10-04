"""
樓層巡檢圖（共用）API Router —— Prefix: /api/v1/floor-map
規格：docs/DEV_SPEC_floor_plan_map.md §6

權限由各模組 Provider 宣告（view_permission／edit_permission），module 不在註冊表 → 404。

  GET    /floors                                   樓層登錄表（登入即可）
  GET    /floors/{floor_key}/image                 底圖（需有任一 Provider 的檢視權限）
  GET    /{module}/meta                            模組設定：樓層、設備組、系統、屬性欄位、資料最後一天
  GET    /{module}/floors/{floor_key}/status?date= 點位＋當日狀態
  GET    /{module}/month?source_ref&year&month     本月每日狀況
  POST   /{module}/floors/{floor_key}/points       新增點位（編輯權限）
  PATCH  /{module}/points/{point_id}               修改／移動（編輯權限）
  DELETE /{module}/points/{point_id}               停用（編輯權限，不硬刪）
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, get_user_permissions
from app.models.user import User
from app.services.floor_map import service as svc
from app.services.floor_map.common import normalize_date
from app.services.floor_map.providers import PROVIDERS, get_provider
from app.services.floor_map.providers.base import FloorMapProvider
from app.services.floor_map.registry import FLOOR_MAP, FLOORS, floor_image_path

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── Schema ────────────────────────────────────────────────────────────────────

class PointCreate(BaseModel):
    x:              float = Field(..., ge=0, le=1)
    y:              float = Field(..., ge=0, le=1)
    label:          str   = Field(..., min_length=1, max_length=100)
    equipment_code: Optional[str] = Field(None, max_length=50)
    source_ref:     str   = Field(..., min_length=1, max_length=200)
    placement:      str   = Field("confirmed", max_length=20)
    attrs:          Optional[dict[str, Optional[str]]] = None
    note:           Optional[str] = Field(None, max_length=300)


class PointUpdate(BaseModel):
    x:              Optional[float] = Field(None, ge=0, le=1)
    y:              Optional[float] = Field(None, ge=0, le=1)
    label:          Optional[str]   = Field(None, min_length=1, max_length=100)
    equipment_code: Optional[str]   = Field(None, max_length=50)
    source_ref:     Optional[str]   = Field(None, min_length=1, max_length=200)
    placement:      Optional[str]   = Field(None, max_length=20)
    attrs:          Optional[dict[str, Optional[str]]] = None
    note:           Optional[str]   = Field(None, max_length=300)


# ── 權限／參數 ────────────────────────────────────────────────────────────────

def _perms(user: User, db: Session) -> list[str]:
    return get_user_permissions(user.id, db)


def _require(user: User, db: Session, key: str) -> None:
    perms = _perms(user, db)
    if "*" not in perms and key not in perms:
        raise HTTPException(status_code=403, detail=f"權限不足（需要 {key}）")


def _provider(module: str) -> FloorMapProvider:
    p = get_provider(module)
    if not p:
        raise HTTPException(status_code=404, detail=f"未知的模組：{module}")
    return p


def _floor(provider: FloorMapProvider, floor_key: str) -> None:
    if floor_key not in FLOOR_MAP or floor_key not in provider.floors:
        raise HTTPException(status_code=404, detail=f"{provider.label} 沒有樓層：{floor_key}")


def _who(user: User) -> str:
    return (getattr(user, "full_name", None) or getattr(user, "email", None) or str(user.id))[:100]


def _call(fn, *args):
    try:
        return fn(*args)
    except svc.FloorMapError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ── 底圖（全站共用）──────────────────────────────────────────────────────────

@router.get("/floors", summary="樓層登錄表")
def list_floors():
    return {"floors": [{k: f[k] for k in ("key", "label", "width", "height", "version")} for f in FLOORS]}


@router.get("/floors/{floor_key}/image", summary="底圖（需登入且有任一模組檢視權限）")
def floor_image(floor_key: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if floor_key not in FLOOR_MAP:
        raise HTTPException(status_code=404, detail=f"未知的樓層：{floor_key}")
    perms = _perms(user, db)
    if "*" not in perms and not any(p.view_permission in perms for p in PROVIDERS.values()):
        raise HTTPException(status_code=403, detail="權限不足（需要任一樓層巡檢圖模組的檢視權限）")
    path = floor_image_path(floor_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"找不到底圖檔：{path.name}")
    return FileResponse(path, media_type="image/webp", headers={"Cache-Control": "private, max-age=86400"})


# ── 模組 ──────────────────────────────────────────────────────────────────────

@router.get("/{module}/meta", summary="模組設定")
def module_meta(module: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = _provider(module)
    _require(user, db, p.view_permission)
    return {**p.meta(), "data_end": p.data_end(db)}


@router.get("/{module}/floors/{floor_key}/status", summary="點位＋當日狀態")
def floor_status(
    module: str, floor_key: str,
    date: str = Query(..., description="YYYY-MM-DD 或 YYYY/MM/DD"),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    p = _provider(module)
    _require(user, db, p.view_permission)
    _floor(p, floor_key)
    d = normalize_date(date)
    if not d:
        raise HTTPException(status_code=422, detail=f"日期格式錯誤：{date}")
    return svc.floor_status(db, p, floor_key, d)


@router.get("/{module}/month", summary="本月每日狀況")
def month_status(
    module: str,
    source_ref: str = Query(...),
    year: int = Query(..., ge=2020, le=2035),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    p = _provider(module)
    _require(user, db, p.view_permission)
    if not p.has_source(source_ref):
        raise HTTPException(status_code=422, detail=f"未知的資料來源：{source_ref}")
    return {"year": year, "month": month, "source_ref": source_ref,
            "days": p.month_status(db, source_ref, year, month)}


@router.post("/{module}/floors/{floor_key}/points", summary="新增點位")
def create_point(
    module: str, floor_key: str, body: PointCreate,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    p = _provider(module)
    _require(user, db, p.edit_permission)
    _floor(p, floor_key)
    pt = _call(svc.create_point, db, p, floor_key, body.model_dump(), _who(user))
    return svc.point_out(pt, p)


@router.patch("/{module}/points/{point_id}", summary="修改／移動點位")
def update_point(
    module: str, point_id: int, body: PointUpdate,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    p = _provider(module)
    _require(user, db, p.edit_permission)
    pt = svc.get_active(db, p, point_id)
    if not pt:
        raise HTTPException(status_code=404, detail="點位不存在")
    data: dict[str, Any] = body.model_dump(exclude_unset=True)
    pt = _call(svc.update_point, db, p, pt, data, _who(user))
    return svc.point_out(pt, p)


@router.delete("/{module}/points/{point_id}", summary="停用點位（不硬刪）")
def delete_point(
    module: str, point_id: int,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    p = _provider(module)
    _require(user, db, p.edit_permission)
    pt = svc.get_active(db, p, point_id)
    if not pt:
        raise HTTPException(status_code=404, detail="點位不存在")
    svc.deactivate_point(db, pt, _who(user))
    return {"ok": True, "id": point_id}
