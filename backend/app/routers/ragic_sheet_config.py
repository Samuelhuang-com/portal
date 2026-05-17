"""
Ragic Sheet 設定管理 API

端點：
  GET  /api/v1/settings/ragic-sheet-config          — 列出所有設定（可依 module 篩選）
  GET  /api/v1/settings/ragic-sheet-config/{id}     — 取得單筆
  PUT  /api/v1/settings/ragic-sheet-config/{id}     — 更新單筆（list_path / detail_path / is_active）
  POST /api/v1/settings/ragic-sheet-config/reseed   — 重新 seed（補回缺少的預設值）

權限：system_admin only
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import is_system_admin
from app.models.ragic_sheet_config import RagicSheetConfig
from app.models.user import User

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class SheetConfigOut(BaseModel):
    id:           int
    module:       str
    display_name: str
    ragic_dept:   str
    list_path:    str
    detail_path:  str
    extra_json:   str
    sort_order:   int
    is_active:    bool

    class Config:
        from_attributes = True


class SheetConfigUpdate(BaseModel):
    list_path:   Optional[str]  = None
    detail_path: Optional[str]  = None
    extra_json:  Optional[str]  = None
    sort_order:  Optional[int]  = None
    is_active:   Optional[bool] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[SheetConfigOut])
def list_sheet_configs(
    module: Optional[str] = None,
    db:     Session       = Depends(get_db),
    _:      User          = Depends(is_system_admin),
):
    """列出所有 Ragic Sheet 設定，可依 module 篩選。"""
    q = db.query(RagicSheetConfig)
    if module:
        q = q.filter(RagicSheetConfig.module == module)
    return q.order_by(RagicSheetConfig.module, RagicSheetConfig.sort_order).all()


@router.get("/{config_id}", response_model=SheetConfigOut)
def get_sheet_config(
    config_id: int,
    db:        Session = Depends(get_db),
    _:         User    = Depends(is_system_admin),
):
    row = db.query(RagicSheetConfig).filter(RagicSheetConfig.id == config_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="找不到設定")
    return row


@router.put("/{config_id}", response_model=SheetConfigOut)
def update_sheet_config(
    config_id: int,
    payload:   SheetConfigUpdate,
    db:        Session = Depends(get_db),
    _:         User    = Depends(is_system_admin),
):
    """
    更新單筆 Ragic Sheet 設定。
    只更新有傳入的欄位（None 表示不異動）。
    """
    row = db.query(RagicSheetConfig).filter(RagicSheetConfig.id == config_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="找不到設定")

    if payload.list_path   is not None: row.list_path   = payload.list_path
    if payload.detail_path is not None: row.detail_path = payload.detail_path
    if payload.extra_json  is not None:
        # 驗證 JSON 格式
        try:
            json.loads(payload.extra_json)
        except Exception:
            raise HTTPException(status_code=422, detail="extra_json 格式錯誤，需為合法 JSON 字串")
        row.extra_json = payload.extra_json
    if payload.sort_order  is not None: row.sort_order  = payload.sort_order
    if payload.is_active   is not None: row.is_active   = payload.is_active

    db.commit()
    db.refresh(row)
    return row


@router.post("/reseed")
def reseed_sheet_config(
    _: User = Depends(is_system_admin),
):
    """
    重新執行 seed（補回缺少的預設值，不覆蓋已有設定）。
    用於首次部署或手動加回被刪除的預設部門。
    """
    from app.services.ragic_sheet_config_service import seed_ragic_sheet_config
    seed_ragic_sheet_config()
    return {"detail": "reseed 完成"}
