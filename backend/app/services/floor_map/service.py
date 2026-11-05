"""
樓層巡檢圖 — 點位 CRUD 與狀態（所有模組共用，DEV_SPEC §4、§6）
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.floor_map import PLACEMENTS, FloorMapDisabledSource, FloorMapPoint
from app.services.floor_map.providers.base import FloorMapProvider


class FloorMapError(ValueError):
    """輸入錯誤（router 轉成 422）"""


def point_out(p: FloorMapPoint, provider: FloorMapProvider,
              gmap: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    g = (gmap if gmap is not None else provider.group_map()).get(p.source_ref, {})
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
        "child_ref":      p.child_ref or "",
        "kind":           "child" if p.child_ref else "parent",
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


def module_known_refs(db: Session, module: str) -> set[str]:
    """
    模組內所有樓層「有點位紀錄」的資料來源，**含已停用的點**。
    給「未對應」判定用：停用＝刻意不放在圖上，不再列為未對應（Samuel 2026-11-04 裁示）。
    """
    rows = (
        db.query(FloorMapPoint.source_ref)
        .filter(FloorMapPoint.module == module)
        .distinct()
        .all()
    )
    return {r[0] for r in rows}


def floor_status(db: Session, provider: FloorMapProvider, floor_key: str, insp_date: str) -> dict[str, Any]:
    gmap = provider.group_map(db)
    points = [point_out(p, provider, gmap) for p in active_points(db, provider.module, floor_key)]
    used = {p["source_ref"] for p in points}
    all_groups = provider.day_status_floor(db, insp_date, floor_key) if used else {}
    groups = {k: v for k, v in all_groups.items() if k in used}
    for p in points:
        g = groups.get(p["source_ref"], {})
        if p.get("child_ref"):
            # 子項點位：狀態取該子項；子項停用時只在編輯模式顯示
            c = next((k for k in g.get("children", []) if k["source_ref"] == p["child_ref"]), None)
            p["status"] = c["status"] if c else "no_record"
            p["hidden"] = bool(c and c["disabled"])
        else:
            p["status"] = g.get("status", "no_record")
            # two_level：該層子項全部停用的母項點位，只在編輯模式顯示（前端依 hidden 判斷）
            p["hidden"] = bool(g.get("all_disabled"))
    # 未對應（2026-11-04）：Provider 有實作才有內容；巡檢模組一律回空陣列。
    # 有點位紀錄（含已停用）就不算未對應。
    unmapped = provider.unmapped(db, insp_date, module_known_refs(db, provider.module))
    return {"date": insp_date, "module": provider.module, "floor_key": floor_key,
            "points": points, "groups": groups, "unmapped": unmapped}


# ── 寫入 ──────────────────────────────────────────────────────────────────────

_WRITABLE = ("x", "y", "label", "equipment_code", "source_ref", "placement", "attrs", "note")


def _validate(provider: FloorMapProvider, data: dict[str, Any], db: Session | None = None) -> None:
    if "source_ref" in data and not provider.has_source(data["source_ref"], db):
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


def create_child_points(db: Session, provider: FloorMapProvider, floor_key: str,
                        data: dict[str, Any], child_refs: list[str], who: str) -> list[FloorMapPoint]:
    """
    two_level（例行維護類）新增點位：必須同時選母項與子項（2026-11-05 裁示）。
    一次可多選子項，每個子項各建一個點，放在同一個位置（之後可各自拖曳）。
    單一子項且有填顯示名稱 → 用該名稱；其餘一律用子項名稱。
    """
    parent = data.get("source_ref") or ""
    if not parent or not provider.has_source(parent, db):
        raise FloorMapError(f"未知的母項：{parent}")
    if not child_refs:
        raise FloorMapError("請至少選擇一個子項")
    if len(set(child_refs)) != len(child_refs):
        raise FloorMapError("子項重複")
    valid = set(provider.child_keys(db, parent))
    bad = [c for c in child_refs if c not in valid]
    if bad:
        raise FloorMapError(f"子項不屬於此母項：{bad[0]}")
    data = {k: v for k, v in data.items() if k != "child_refs"}
    _validate(provider, data, db)
    now = twnow()
    out: list[FloorMapPoint] = []
    for c in child_refs:
        label = data.get("label") if (len(child_refs) == 1 and data.get("label")) else c
        p = FloorMapPoint(
            module=provider.module, floor_key=floor_key,
            x=data["x"], y=data["y"], label=label,
            equipment_code=data.get("equipment_code"),
            source_ref=parent, child_ref=c,
            placement=data.get("placement") or "confirmed",
            attrs=data.get("attrs"), note=data.get("note"),
            sort_order=0, is_active=True,
            created_by=who, updated_by=who, created_at=now, updated_at=now,
        )
        db.add(p)
        out.append(p)
    db.commit()
    for p in out:
        db.refresh(p)
    return out


def create_point(db: Session, provider: FloorMapProvider, floor_key: str,
                 data: dict[str, Any], who: str) -> FloorMapPoint:
    if getattr(provider, "two_level", False):
        raise FloorMapError("例行維護類新增點位需同時選擇母項與子項")
    _validate(provider, data, db)
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
    if p.child_ref and "source_ref" in data and data["source_ref"] != p.source_ref:
        raise FloorMapError("子項點位不可變更母項；請停用後重新新增")
    _validate(provider, data, db)
    for k, v in data.items():
        setattr(p, k, v)
    p.updated_by = who
    p.updated_at = twnow()
    db.commit()
    db.refresh(p)
    return p


def disabled_sources(db: Session, module: str) -> set[str]:
    """停用的子項（two_level 模組）"""
    return {r[0] for r in db.query(FloorMapDisabledSource.source_ref).filter(FloorMapDisabledSource.module == module).all()}


def set_source_disabled(db: Session, provider: FloorMapProvider, source_ref: str, disabled: bool, who: str) -> bool:
    """子項停用／恢復（一個子項停用＝全部樓層）。回傳變更後是否停用。"""
    if not provider.two_level:
        raise FloorMapError(f"{provider.label} 不支援子項停用")
    if not provider.has_detail_source(source_ref, db):
        raise FloorMapError(f"未知的子項：{source_ref}")
    row = (db.query(FloorMapDisabledSource)
           .filter(FloorMapDisabledSource.module == provider.module, FloorMapDisabledSource.source_ref == source_ref)
           .first())
    if disabled and row is None:
        db.add(FloorMapDisabledSource(module=provider.module, source_ref=source_ref, disabled_by=who, disabled_at=twnow()))
    elif not disabled and row is not None:
        db.delete(row)
    db.commit()
    return disabled


def deactivate_point(db: Session, p: FloorMapPoint, who: str) -> None:
    p.is_active = False
    p.updated_by = who
    p.updated_at = twnow()
    db.commit()
