"""站台基本設定 Schemas。

三段顯示文字**各自獨立、整段自由輸入**（2026-08-11 決策）：
原本是「品牌名稱」一個欄位自動組出 `{brand}集團管理 Portal`，
但各 Server 想改的不一定只有前綴，因此改為整段可改，不做任何組字。
"""
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# 三段文字的長度上限（顯示在側邊欄與登入頁，過長會破版）
_MAX_LEN = 40


class SiteConfigResponse(BaseModel):
    """GET /api/v1/site-config 的回傳。

    刻意只回傳前端顯示需要的欄位，不含 updated_by 等內部資訊——
    這是公開端點（登入頁未認證就要用），回傳內容愈少愈好。
    """

    site_title: str = Field(..., description="側邊欄標題＋瀏覽器分頁標題")
    login_title: str = Field(..., description="登入頁大標")
    login_subtitle: str = Field(..., description="登入頁副標")


class SiteConfigUpdate(BaseModel):
    """PUT /api/v1/site-config 的 request body。三欄皆必填。"""

    site_title: str = Field(..., min_length=1, max_length=_MAX_LEN)
    login_title: str = Field(..., min_length=1, max_length=_MAX_LEN)
    login_subtitle: str = Field(..., min_length=1, max_length=_MAX_LEN)

    @field_validator("site_title", "login_title", "login_subtitle")
    @classmethod
    def _strip_and_check(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("不可為空白")
        return v


class SiteConfigDetail(SiteConfigResponse):
    """設定頁專用（需登入），比公開端點多帶異動資訊。"""

    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
