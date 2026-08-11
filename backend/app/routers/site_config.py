"""
站台基本設定端點（畫面上的三段顯示文字）。

2026-08-11 新增。取代前一版的 `frontend/public/config.json` 執行期設定檔——
該檔屬於 build 產物，每次重新部署前端都會被覆蓋回預設值，改存 DB 後才真正
與部署脫鉤（各 Server 有各自的 portal.db，天生就是一台一組設定）。

2026-08-11 同日調整：原本只存「品牌名稱」再由後端組出 `{brand}集團管理 Portal`，
改為**三段文字各自獨立、整段自由輸入**，不做任何組字。理由是各 Server 想改的
不一定只有前綴，組字規則反而變成限制。

⚠️ GET 刻意設計為**公開端點（不加 Depends(get_current_user)）**：
- 登入頁在拿到 token 之前就要顯示這些文字，加驗證會直接讓登入頁顯示不出來。
- 回傳內容只有畫面顯示文字，非機敏業務資料。
- 站上已有同型先例：`/api/v1/version`（見 version.py 檔頭說明）。
- **PUT 仍需系統管理員**（`Depends(is_system_admin)`），寫入沒有放寬。
  未來新增端點請勿比照 GET 省略 Depends。

⚠️ 註冊順序：`main.py` 的 `spa_fallback` 是 `@app.get("/{full_path:path}")` catch-all，
本 router 必須在它之前 `include_router`，否則 `/api/v1/site-config` 會拿到
**200 + index.html** 而不是 404（v1.90.36 踩過同一個坑）。

資料表 `system_settings` 由 `Base.metadata.create_all()` 自動建立，不需 migration。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import is_system_admin
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.schemas.site_config import (
    SiteConfigDetail,
    SiteConfigResponse,
    SiteConfigUpdate,
)

router = APIRouter()

# 設定鍵；採 `分類.欄位` 命名。
# 三段各存一列，未來要加 Logo、頁尾直接加 key，不必改資料表。
KEYS = ("site.title", "site.login_title", "site.login_subtitle")

# 資料表沒有資料時的保底值（＝現行畫面文字）。
# 前端 `siteConfig.ts` 也有一份同樣的常數，兩邊都掛掉時才會用到那一份。
DEFAULTS: dict[str, str] = {
    "site.title": "維春集團管理 Portal",
    "site.login_title": "集團管理 Portal",
    "site.login_subtitle": "維春集團內部作業與管理平台",
}

# API 欄位名 ←→ 設定鍵
_FIELD_TO_KEY = {
    "site_title": "site.title",
    "login_title": "site.login_title",
    "login_subtitle": "site.login_subtitle",
}


def _read_rows(db: Session) -> dict[str, SystemSetting]:
    rows = db.query(SystemSetting).filter(SystemSetting.key.in_(KEYS)).all()
    return {r.key: r for r in rows}


def _compose(rows: dict[str, SystemSetting]) -> dict:
    """組出回傳值；任一欄沒資料或存成空字串就退回該欄的預設值。"""
    result = {}
    for field, key in _FIELD_TO_KEY.items():
        row = rows.get(key)
        value = (row.value or "").strip() if row else ""
        result[field] = value or DEFAULTS[key]
    return result


def _latest_meta(rows: dict[str, SystemSetting]) -> dict:
    """三列各有自己的 updated_at，取最新的一筆當作「最後修改」。"""
    present = [r for r in rows.values() if r.updated_at]
    if not present:
        return {"updated_at": None, "updated_by": None}
    latest = max(present, key=lambda r: r.updated_at)
    return {
        "updated_at": latest.updated_at.strftime("%Y-%m-%d %H:%M"),
        "updated_by": latest.updated_by,
    }


@router.get("", response_model=SiteConfigResponse)
def get_site_config(db: Session = Depends(get_db)):
    """取得站台顯示文字。**公開端點**，登入頁未認證時也會呼叫（見檔頭說明）。"""
    return _compose(_read_rows(db))


@router.get("/detail", response_model=SiteConfigDetail)
def get_site_config_detail(
    db: Session = Depends(get_db),
    _: User = Depends(is_system_admin),
):
    """設定頁專用：比公開端點多帶最後異動時間與異動者。"""
    rows = _read_rows(db)
    return {**_compose(rows), **_latest_meta(rows)}


@router.put("", response_model=SiteConfigDetail)
def update_site_config(
    payload: SiteConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_system_admin),
):
    """更新三段顯示文字。僅系統管理員可操作。"""
    rows = _read_rows(db)

    for field, key in _FIELD_TO_KEY.items():
        row = rows.get(key)
        if row is None:
            row = SystemSetting(key=key)
            db.add(row)
            rows[key] = row
        row.value = getattr(payload, field)
        row.updated_by = current_user.email

    db.commit()

    rows = _read_rows(db)
    return {**_compose(rows), **_latest_meta(rows)}
