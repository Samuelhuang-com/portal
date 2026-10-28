"""
角色管理 Router
GET    /api/v1/roles                取得所有角色清單
POST   /api/v1/roles                新增自訂角色
DELETE /api/v1/roles/{role_id}      刪除自訂角色（內建角色受保護）

需具備 settings_roles_manage 權限（system_admin 透過萬用符 * 自動通過）。

── 2026-08-12 權限收斂改版 ───────────────────────────────────────────────────
與 role_permissions.py 同批改動：原本四支端點都是 Depends(is_system_admin)，
使得「能管角色」必須是 system_admin，連帶看得到 Opera／金旭／即時營運營收。

刪除角色另加一道防護：不得刪除「含有呼叫者無權管理之 permission key」的角色。
否則只要能管角色，就能把別人賴以存取營運分析的角色整個刪掉。
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.dependencies import get_user_permissions, require_permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole
from app.models.user import User

router = APIRouter()

# 管理角色所需的 permission key
_MANAGE = require_permission("settings_roles_manage")

# 受保護的內建角色名稱（不可修改或刪除）
BUILT_IN_ROLES = {"system_admin", "tenant_admin", "module_manager", "viewer"}


# ── Pydantic Schemas ───────────────────────────────────────────────────────────

class RoleOut(BaseModel):
    id: str
    name: str
    scope: Optional[str] = None
    description: Optional[str] = None
    is_builtin: bool = False

    class Config:
        from_attributes = True


class RoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="角色識別名稱（英文小寫+底線）")
    description: Optional[str] = Field(None, max_length=200)


# ── Endpoints ─────────────────────────────────────────────────────────────────

def _list_roles_impl(db: Session) -> list[RoleOut]:
    rows = db.query(Role).order_by(Role.created_at).all()
    return [
        RoleOut(
            id=r.id,
            name=r.name,
            scope=r.scope,
            description=r.description,
            is_builtin=(r.name in BUILT_IN_ROLES),
        )
        for r in rows
    ]


@router.get("/", response_model=list[RoleOut])
def list_roles_slash(
    db: Session = Depends(get_db),
    _: User = Depends(_MANAGE),
):
    """取得所有角色清單（含 id，供前端角色管理頁面使用）"""
    return _list_roles_impl(db)


@router.get("", response_model=list[RoleOut])
def list_roles(
    db: Session = Depends(get_db),
    _: User = Depends(_MANAGE),
):
    """取得所有角色清單（無 trailing slash 版本）"""
    return _list_roles_impl(db)


@router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=RoleOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_role(
    payload: RoleCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(_MANAGE),
):
    """
    新增自訂角色。
    - 名稱必須唯一且不能與內建角色同名
    - scope 預設為 'tenant'
    """
    # 名稱格式驗證：只允許小寫英文、數字、底線
    import re
    if not re.match(r'^[a-z0-9_]+$', payload.name):
        raise HTTPException(
            status_code=422,
            detail="角色名稱只允許小寫英文字母、數字和底線（例如 hotel_manager）",
        )

    # 禁止使用內建角色名稱
    if payload.name in BUILT_IN_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"'{payload.name}' 是系統內建角色名稱，請使用其他名稱",
        )

    # 檢查名稱重複
    existing = db.query(Role).filter(Role.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"角色名稱 '{payload.name}' 已存在",
        )

    new_role = Role(
        id=str(uuid.uuid4()),
        name=payload.name,
        scope="tenant",
        description=payload.description,
    )
    db.add(new_role)
    db.commit()
    db.refresh(new_role)

    return RoleOut(
        id=new_role.id,
        name=new_role.name,
        scope=new_role.scope,
        description=new_role.description,
        is_builtin=False,
    )


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(_MANAGE),
):
    """
    刪除自訂角色。
    - 內建角色（system_admin / tenant_admin / module_manager / viewer）受保護，不可刪除
    - 不得刪除含有呼叫者無權管理之 permission key 的角色（見檔頭說明）
    - 自動清除 role_permissions 與 user_roles 中的關聯記錄
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    if role.name in BUILT_IN_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"'{role.name}' 是系統內建角色，不可刪除",
        )

    # 不得刪除自己管不到的角色（例如含 opera_* 的營運分析角色）
    my_perms = set(get_user_permissions(current_user.id, db))
    if "*" not in my_perms:
        role_perms = {
            p[0]
            for p in db.query(RolePermission.permission_key)
            .filter(RolePermission.role_id == role_id)
            .all()
        }
        beyond = sorted(role_perms - my_perms)
        if beyond:
            joined = ", ".join(beyond)
            raise HTTPException(
                status_code=403,
                detail=f"無法刪除角色「{role.name}」：其中包含你未擁有的權限（{joined}）",
            )

    # 1. 清除此角色的所有 permission 設定
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()

    # 2. 清除此角色的所有使用者關聯
    db.query(UserRole).filter(UserRole.role_id == role_id).delete()

    # 3. 刪除角色本身
    db.delete(role)
    db.commit()
