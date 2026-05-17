"""
靜態頁面管理 Router
GET  /api/v1/settings/static-pages   列出 portal/docs/ 下的所有可瀏覽檔案
"""
import os
import pathlib
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List

from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

# docs 目錄的絕對路徑（相對於本檔案：routers/ → app/ → backend/ → portal/docs/）
_DOCS_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "docs"

# 允許瀏覽的副檔名
_ALLOWED_EXTS = {".html", ".htm", ".pdf", ".md"}


class StaticPageItem(BaseModel):
    filename: str        # 原始檔名，例如 Ragic_Reload_預算功能說明.html
    url: str             # 供前端 iframe src 使用的路徑，例如 /docs-static/...


@router.get(
    "/static-pages",
    response_model=List[StaticPageItem],
    summary="列出 docs-static 靜態頁面清單",
)
def list_static_pages(
    current_user: User = Depends(get_current_user),
):
    """
    掃描 portal/docs/ 目錄，回傳允許瀏覽的靜態頁面清單。
    檔名依字母排序；僅回傳副檔名為 .html / .htm / .pdf 的檔案。
    """
    items: List[StaticPageItem] = []

    if not _DOCS_DIR.is_dir():
        return items

    for entry in sorted(_DOCS_DIR.iterdir()):
        if entry.is_file() and entry.suffix.lower() in _ALLOWED_EXTS:
            items.append(StaticPageItem(
                filename=entry.name,
                url=f"/docs-static/{entry.name}",
            ))

    return items
