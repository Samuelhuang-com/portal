"""
角色權限管理 Router
GET  /api/v1/role-permissions/{role_id}   取得角色的 permission_key 清單
PUT  /api/v1/role-permissions/{role_id}   覆寫角色的 permission_key 清單
GET  /api/v1/role-permissions/keys        取得系統所有已知的 permission_key 定義

僅限 system_admin 操作。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.dependencies import is_system_admin
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User

router = APIRouter()


# ── Permission Key 定義（所有已知權限）──────────────────────────────────────────
# 【新增模組規則】：新模組開發期間，加入此清單但先不加入任何角色的 role_permissions。
# 待開發測試完成後，管理員再透過 Roles 頁面手動勾選授予。
PERMISSION_DEFINITIONS = [
    # ── 一階選單（獨立一階，不屬於任何群組）──────────────────────────────────
    {"key": "exec_dashboard_view",        "label": "高階主管 Dashboard", "group": "一階選單"},
    {"key": "work_category_analysis_view","label": "工項類別分析",       "group": "一階選單"},
    {"key": "calendar_view",              "label": "行事曆",             "group": "一階選單"},
    # ── 系統設定 ────────────────────────────────────────────────────────────
    {"key": "settings_users_manage",    "label": "人員管理",   "group": "系統設定"},
    {"key": "settings_roles_manage",    "label": "角色管理",   "group": "系統設定"},
    {"key": "settings_menu_manage",     "label": "選單管理",   "group": "系統設定"},
    {"key": "settings_ragic_manage",    "label": "Ragic 設定", "group": "系統設定"},
    # ── 飯店管理 ────────────────────────────────────────────────────────────
    {"key": "hotel_view",                        "label": "飯店模組",         "group": "飯店管理"},
    {"key": "hotel_room_maintenance_view",        "label": "客房保養",         "group": "飯店管理"},
    {"key": "hotel_periodic_maintenance_view",    "label": "飯店週期保養",     "group": "飯店管理"},
    {"key": "hotel_ihg_room_maintenance_view",    "label": "IHG 客房保養",     "group": "飯店管理"},
    {"key": "hotel_daily_inspection_view",        "label": "飯店每日巡檢",     "group": "飯店管理"},
    {"key": "hotel_meter_readings_view",          "label": "每日數值登錄表",   "group": "飯店管理"},
    # ── 商場管理 ────────────────────────────────────────────────────────────
    {"key": "mall_view",                          "label": "商場模組",          "group": "商場管理"},
    {"key": "mall_overview_view",                 "label": "商場管理 Dashboard","group": "商場管理"},
    {"key": "mall_dashboard_view",                "label": "商場例行維護統計",  "group": "商場管理"},
    {"key": "mall_periodic_maintenance_view",      "label": "商場週期保養",      "group": "商場管理"},
    {"key": "mall_full_building_maintenance_view", "label": "全棟例行維護",      "group": "商場管理"},
    {"key": "mall_facility_inspection_view",       "label": "商場工務巡檢",      "group": "商場管理"},
    {"key": "mall_full_building_inspection_view",  "label": "整棟巡檢",          "group": "商場管理"},
    # ── 工務報修 ────────────────────────────────────────────────────────────
    {"key": "luqun_repair_view",        "label": "樂群工務報修",  "group": "工務報修"},
    {"key": "dazhi_repair_view",        "label": "大直工務部",    "group": "工務報修"},
    # ── 保全管理 ────────────────────────────────────────────────────────────
    {"key": "security_view",            "label": "保全模組",      "group": "保全管理"},
    {"key": "security_dashboard_view",  "label": "保全巡檢統計",  "group": "保全管理"},
    {"key": "security_patrol_view",     "label": "保全巡檢記錄",  "group": "保全管理"},
    # ── 協作工具 ────────────────────────────────────────────────────────────
    {"key": "approvals_view",           "label": "簽核查看",      "group": "協作工具"},
    {"key": "approvals_manage",         "label": "簽核新增/管理", "group": "協作工具"},
    {"key": "memos_view",               "label": "公告查看",      "group": "協作工具"},
    {"key": "memos_manage",             "label": "公告新增/管理", "group": "協作工具"},
    # ── 財務 ────────────────────────────────────────────────────────────────
    {"key": "budget_view",              "label": "預算查看",      "group": "財務"},
    {"key": "budget_manage",            "label": "預算管理",      "group": "財務"},
    {"key": "budget_admin",             "label": "預算設定",      "group": "財務"},
]


# ── Pydantic Schemas ───────────────────────────────────────────────────────────

class PermissionKeyDef(BaseModel):
    key: str
    label: str
    group: str


class RolePermissionsOut(BaseModel):
    role_id: str
    role_name: str
    permissions: list[str]


class RolePermissionsSaveRequest(BaseModel):
    permissions: list[str]


# ── Endpoints ─────────────────────────────────────────────────────────────────

class RoleOut(BaseModel):
    id: str
    name: str
    scope: Optional[str] = None
    description: Optional[str] = None


@router.get("/keys", response_model=list[PermissionKeyDef])
def list_permission_keys(
    _: User = Depends(is_system_admin),
):
    """取得系統所有已知的 permission_key 定義（用於 Roles 頁面 checkbox 清單）"""
    return [PermissionKeyDef(**d) for d in PERMISSION_DEFINITIONS]


@router.get("/{role_id}", response_model=RolePermissionsOut)
def get_role_permissions(
    role_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(is_system_admin),
):
    """取得指定角色的 permission_key 清單"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    perms = (
        db.query(RolePermission.permission_key)
        .filter(RolePermission.role_id == role_id)
        .all()
    )
    return RolePermissionsOut(
        role_id=role_id,
        role_name=role.name,
        permissions=[p[0] for p in perms],
    )


@router.put("/{role_id}", response_model=RolePermissionsOut)
def save_role_permissions(
    role_id: str,
    payload: RolePermissionsSaveRequest,
    db: Session = Depends(get_db),
    _: User = Depends(is_system_admin),
):
    """
    覆寫指定角色的 permission_key 清單（完全取代）。
    system_admin 角色固定為萬用符（*），不允許個別設定。
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    if role.name == "system_admin":
        raise HTTPException(
            status_code=400,
            detail="system_admin 擁有所有權限，無需個別設定",
        )

    # 驗證傳入的 key 都在已知清單中
    valid_keys = {d["key"] for d in PERMISSION_DEFINITIONS}
    invalid = [k for k in payload.permissions if k not in valid_keys]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"不存在的 permission_key：{', '.join(invalid)}",
        )

    # 刪除舊記錄，插入新記錄
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
    for key in set(payload.permissions):  # 去重
        db.add(RolePermission(role_id=role_id, permission_key=key))
    db.commit()

    return RolePermissionsOut(
        role_id=role_id,
        role_name=role.name,
        permissions=list(set(payload.permissions)),
    )
