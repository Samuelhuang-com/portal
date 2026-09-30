"""
權限群組「限系統管理員」鎖定（2026-09-30 Samuel 裁示）

在「系統設定 > 角色管理 > 權限設定」每個模組群組（PERMISSION_DEFINITIONS 的 group）
旁有一個 V。勾選後，該群組內的所有 permission_key 對「非系統管理員」一律失效：
  - get_user_permissions() 會扣掉這些 key → /me、選單、路由守衛、所有 require_permission API 同步擋下
  - 角色原本勾的 key 不會被刪（role_permissions 原樣保留），取消鎖定後立即恢復
  - system_admin（*）不受影響

設定存在 system_settings（key-value），值為 JSON 陣列（群組名稱）。
"""
import json

from sqlalchemy.orm import Session

SETTING_KEY = "permissions.sysadmin_only_groups"


def _all_definitions() -> list[dict]:
    # 延遲 import：role_permissions router 在模組層 import app.dependencies，避免循環
    from app.routers.role_permissions import PERMISSION_DEFINITIONS
    return PERMISSION_DEFINITIONS


def all_groups() -> list[str]:
    seen: list[str] = []
    for d in _all_definitions():
        if d["group"] not in seen:
            seen.append(d["group"])
    return seen


def get_locked_groups(db: Session) -> list[str]:
    from app.models.system_setting import SystemSetting
    row = db.query(SystemSetting).filter(SystemSetting.key == SETTING_KEY).first()
    if not row or not row.value:
        return []
    try:
        data = json.loads(row.value)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [g for g in data if isinstance(g, str)]


def set_locked_groups(db: Session, groups: list[str], updated_by: str | None) -> list[str]:
    from app.models.system_setting import SystemSetting
    known = all_groups()
    clean = [g for g in known if g in set(groups)]  # 依定義順序、去重、過濾未知群組
    row = db.query(SystemSetting).filter(SystemSetting.key == SETTING_KEY).first()
    if not row:
        row = SystemSetting(key=SETTING_KEY)
        db.add(row)
    row.value = json.dumps(clean, ensure_ascii=False)
    row.updated_by = updated_by
    db.commit()
    return clean


def get_locked_keys(db: Session) -> set[str]:
    locked = set(get_locked_groups(db))
    if not locked:
        return set()
    return {d["key"] for d in _all_definitions() if d["group"] in locked}
