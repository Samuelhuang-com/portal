"""
樓層巡檢圖 — 點位 CRUD 與狀態（所有模組共用，DEV_SPEC §4、§6）
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.floor_map import PLACEMENTS, FloorMapPoint
from app.services.floor_map.providers.base import FloorMapProvider


class FloorMapError(ValueError):
    """輸入錯誤（router 轉成 422）"""


def point_out(p: FloorMapPoint, provider: FloorMapProvider) -> dict[str, Any]:
    g = provider.group_map().get(p.source_ref, {})
    attrs = p.attrs if isinstance(p.attrs, dict) else {}
    return {
        "id":             p.id,
        "module":         p.module,
        "floor_key":      p.floor_key,
        "x":              p.x,
        "y":              p.y,
        "label":          p.label,
        "equipment_code": p.equipment_code or "",
        "source_ref":     p.source_ref,
        "group_label":    g.get("label", p.source_ref),
        "system":         g.get("system", ""),
        "shared_label":   g.get("shared_label", ""),
        "placement":      p.placement or "confirmed",
        "attrs":          {k: v for k, v in attrs.items() if v not in (None, "")},
        "note":           p.note or "",
        "updated_by":     p.updated_by or "",
        "updated_at":     p.updated_at.strftime("%Y-%m-%d %H:%M") if p.updated_at else "",
    }


def active_points(db: Session, module: str, floor_key: str) -> list[FloorMapPoint]:
    return (
        db.query(FloorMapPoint)
        .filter(
            FloorMapPoint.module == module,
            FloorMapPoint.floor_key == floor_key,
            FloorMapPoint.is_active.is_(True),
        )
        .order_by(FloorMapPoint.sort_order, FloorMapPoint.id)
        .all()
    )


def floor_status(db: Session, provider: FloorMapProvider, floor_key: str, insp_date: str) -> dict[str, Any]:
    points = [point_out(p, provider) for p in active_points(db, provider.module, floor_key)]
    used = {p["source_ref"] for p in points}
    all_groups = provider.day_status(db, insp_date) if used else {}
    groups = {k: v for k, v in all_groups.items() if k in used}
    for p in points:
        p["status"] = groups.get(p["source_ref"], {}).get("status", "no_record")
    return {"date": insp_date, "module": provider.module, "floor_key": floor_key,
            "points": points, "groups": groups}


# ── 寫入 ──────────────────────────────────────────────────────────────────────

_WRITABLE = ("x", "y", "label", "equipment_code", "source_ref", "placement", "attrs", "note")


def _validate(provider: FloorMapProvider, data: dict[str, Any]) -> None:
    if "source_ref" in data and not provider.has_source(data["source_ref"]):
        raise FloorMapError(f"未知的資料來源：{data['source_ref']}")
    if "placement" in data and data["placement"] not in PLACEMENTS:
        raise FloorMapError(f"placement 必須是 {PLACEMENTS} 之一")
    if "attrs" in data and data["attrs"] is not None:
        if not isinstance(data["attrs"], dict):
            raise FloorMapError("attrs 必須是物件")
        allowed = set(provider.attr_fields)
        extra = set(data["attrs"]) - allowed
        if extra:
            raise FloorMapError(f"attrs 只接受 {sorted(allowed)}，收到 {sorted(extra)}")


def create_point(db: Session, provider: FloorMapProvider, floor_key: str,
                 data: dict[str, Any], who: str) -> FloorMapPoint:
    _validate(provider, data)
    now = twnow()
    p = FloorMapPoint(
        module=provider.module, floor_key=floor_key,
        **{k: data.get(k) for k in _WRITABLE if k in data},
        sort_order=0, is_active=True,
        created_by=who, updated_by=who, created_at=now, updated_at=now,
    )
    if not p.placement:
        p.placement = "confirmed"
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def get_active(db: Session, provider: FloorMapProvider, point_id: int) -> FloorMapPoint | None:
    p = db.get(FloorMapPoint, point_id)
    if not p or not p.is_active or p.module != provider.module:   # 只能動自己模組的點
        return None
    return p


def update_point(db: Session, provider: FloorMapProvider, p: FloorMapPoint,
                 data: dict[str, Any], who: str) -> FloorMapPoint:
    data = {k: v for k, v in data.items() if k in _WRITABLE}
    _validate(provider, data)
    for k, v in data.items():
        setattr(p, k, v)
    p.updated_by = who
    p.updated_at = twnow()
    db.commit()
    db.refresh(p)
    return p


def deactivate_point(db: Session, p: FloorMapPoint, who: str) -> None:
    p.is_active = False
    p.updated_by = who
    p.updated_at = twnow()
    db.commit()
