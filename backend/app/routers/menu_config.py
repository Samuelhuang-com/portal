"""
選單設定 Router
GET  /api/v1/settings/menu-config          取得目前設定
PUT  /api/v1/settings/menu-config          批次儲存設定（同時寫入歷史）
GET  /api/v1/settings/menu-config/history  取得最近 5 筆變更記錄
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.time import twnow

from app.core.database import get_db
from app.dependencies import get_current_user, is_system_admin
from app.models.menu_config import MenuConfig, MenuConfigHistory
from app.models.user import User

router = APIRouter()

# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class MenuConfigItem(BaseModel):
    menu_key: str
    parent_key: Optional[str] = None
    custom_label: Optional[str] = None
    sort_order: int
    is_visible: bool = True


class MenuConfigSaveRequest(BaseModel):
    items: list[MenuConfigItem]


class MenuConfigItemOut(BaseModel):
    menu_key: str
    parent_key: Optional[str] = None
    custom_label: Optional[str] = None
    sort_order: int
    is_visible: bool

    model_config = {"from_attributes": True}


class MenuConfigHistoryOut(BaseModel):
    id: str
    changed_at: str
    changed_by: str
    diff_json: str
    snapshot_json: str

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[MenuConfigItemOut])
def get_menu_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取得目前所有 menu 設定（空清單表示尚未自訂，前端應使用預設值）"""
    rows = db.query(MenuConfig).order_by(MenuConfig.sort_order).all()
    return rows


@router.put("", response_model=list[MenuConfigItemOut])
def save_menu_config(
    payload: MenuConfigSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_system_admin),
):
    """
    批次覆寫全部 menu 設定。
    流程：
    1. 讀取舊設定，計算 diff
    2. 刪除舊設定，寫入新設定
    3. 寫入歷史快照；若超過 5 筆，刪除最舊的
    """
    # ── 1. 計算 diff ──────────────────────────────────────────────────────────
    old_rows = {r.menu_key: r for r in db.query(MenuConfig).all()}
    new_map = {item.menu_key: item for item in payload.items}

    diff = []
    for key, new_item in new_map.items():
        old = old_rows.get(key)
        changes: dict = {}
        if old is None:
            changes["action"] = "added"
        else:
            if old.custom_label != new_item.custom_label:
                changes["label"] = {"from": old.custom_label, "to": new_item.custom_label}
            if old.sort_order != new_item.sort_order:
                changes["order"] = {"from": old.sort_order, "to": new_item.sort_order}
        if changes:
            diff.append({"key": key, **changes})

    # ── 2. 覆寫設定 ───────────────────────────────────────────────────────────
    # 用 Core-level DELETE + INSERT 繞過 ORM identity map，
    # 避免 flush 時因相同 primary key 殘留舊物件導致 UNIQUE constraint 衝突
    db.execute(MenuConfig.__table__.delete())
    actor = current_user.full_name or current_user.email
    now = twnow()
    # 去重：同一 menu_key 只保留第一筆（防止前端重複送出相同 key）
    seen_keys: set[str] = set()
    unique_items = []
    for it in payload.items:
        if it.menu_key not in seen_keys:
            seen_keys.add(it.menu_key)
            unique_items.append(it)
    if unique_items:
        db.execute(
            MenuConfig.__table__.insert(),
            [
                {
                    "menu_key": item.menu_key,
                    "parent_key": item.parent_key,
                    "custom_label": item.custom_label.strip() if item.custom_label and item.custom_label.strip() else None,
                    "sort_order": item.sort_order,
                    "is_visible": item.is_visible,
                    "updated_at": now,
                    "updated_by": actor,
                }
                for item in unique_items
            ],
        )
    db.flush()

    # ── 3. 寫入歷史（最多保留 5 筆）──────────────────────────────────────────
    snapshot = [item.model_dump() for item in payload.items]
    history = MenuConfigHistory(
        changed_by=actor,
        diff_json=json.dumps(diff, ensure_ascii=False),
        snapshot_json=json.dumps(snapshot, ensure_ascii=False),
    )
    db.add(history)
    db.flush()

    # 超過 5 筆則刪除最舊
    all_history = (
        db.query(MenuConfigHistory)
        .order_by(MenuConfigHistory.changed_at.desc())
        .all()
    )
    if len(all_history) > 5:
        for old_h in all_history[5:]:
            db.delete(old_h)

    db.flush()

    result = db.query(MenuConfig).order_by(MenuConfig.sort_order).all()
    return result


@router.get("/history", response_model=list[MenuConfigHistoryOut])
def get_menu_config_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(is_system_admin),
):
    """取得最近 5 筆變更記錄"""
    rows = (
        db.query(MenuConfigHistory)
        .order_by(MenuConfigHistory.changed_at.desc())
        .limit(5)
        .all()
    )
    return [
        MenuConfigHistoryOut(
            id=r.id,
            changed_at=r.changed_at.strftime("%Y-%m-%d %H:%M:%S"),
            changed_by=r.changed_by,
            diff_json=r.diff_json,
            snapshot_json=r.snapshot_json,
        )
        for r in rows
    ]
