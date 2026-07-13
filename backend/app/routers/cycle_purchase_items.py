"""
週期採購 — 料號主檔 + 料號對照表 API Router
Prefix: /api/v1/cycle-purchase

GET    /items                              料號清單（分頁／搜尋）
GET    /items/{item_id}                    料號詳情（含料號對照表）
POST   /items                              新增料號
PUT    /items/{item_id}                    更新料號
GET    /items/{item_id}/mappings           料號對照清單
POST   /items/{item_id}/mappings          新增料號對照
PUT    /items/{item_id}/mappings/{id}     更新料號對照
DELETE /items/{item_id}/mappings/{id}     刪除料號對照
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.cycle_purchase_item import (
    ItemCreate, ItemDetail, ItemListResponse, ItemMappingCreate,
    ItemMappingOut, ItemMappingUpdate, ItemOut, ItemUpdate,
)
from app.services import cycle_purchase_service as svc

router = APIRouter()


# ── 料號主檔 ──────────────────────────────────────────────────────────────────

@router.get("/items", response_model=ItemListResponse, summary="週期採購料號清單")
def list_items(
    q: str = Query("", description="關鍵字（料號／品名）"),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=5, le=200),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    items, total = svc.list_items(
        db, q=q, category=category, is_active=is_active, page=page, per_page=per_page
    )
    return ItemListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/items/{item_id}", response_model=ItemDetail, summary="料號詳情（含料號對照表）")
def get_item(
    item_id: int,
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    item = svc.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="料號不存在")
    return item


@router.post("/items", response_model=ItemOut, status_code=status.HTTP_201_CREATED, summary="新增料號")
def create_item(
    payload: ItemCreate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    try:
        return svc.create_item(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="集團料號已存在")


@router.put("/items/{item_id}", response_model=ItemOut, summary="更新料號")
def update_item(
    item_id: int,
    payload: ItemUpdate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    try:
        item = svc.update_item(db, item_id, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="集團料號已存在")
    if not item:
        raise HTTPException(status_code=404, detail="料號不存在")
    return item


# ── 料號對照表（集團料號 ↔ 公司原料號）────────────────────────────────────────
# ⚠️ 依規劃報告第四節：新增對照前，請先人工確認品名／廠商／單價，
#    不要只憑原始料號字串相同就視為同一品項。

@router.get(
    "/items/{item_id}/mappings",
    response_model=list[ItemMappingOut],
    summary="料號對照清單",
)
def list_item_mappings(
    item_id: int,
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_item_mappings(db, item_id)


@router.post(
    "/items/{item_id}/mappings",
    response_model=ItemMappingOut,
    status_code=status.HTTP_201_CREATED,
    summary="新增料號對照",
)
def create_item_mapping(
    item_id: int,
    payload: ItemMappingCreate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    try:
        mapping = svc.create_item_mapping(db, item_id, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="此料號已有該公司的對照紀錄")
    if not mapping:
        raise HTTPException(status_code=404, detail="料號不存在")
    return mapping


@router.put(
    "/items/{item_id}/mappings/{mapping_id}",
    response_model=ItemMappingOut,
    summary="更新料號對照",
)
def update_item_mapping(
    item_id: int,
    mapping_id: int,
    payload: ItemMappingUpdate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    mapping = svc.update_item_mapping(db, item_id, mapping_id, payload)
    if not mapping:
        raise HTTPException(status_code=404, detail="料號對照不存在")
    return mapping


@router.delete("/items/{item_id}/mappings/{mapping_id}", summary="刪除料號對照")
def delete_item_mapping(
    item_id: int,
    mapping_id: int,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    ok = svc.delete_item_mapping(db, item_id, mapping_id)
    if not ok:
        raise HTTPException(status_code=404, detail="料號對照不存在")
    return {"ok": True}
