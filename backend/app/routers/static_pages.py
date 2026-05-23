"""
靜態頁面管理 Router
GET  /api/v1/settings/static-pages              列出 portal/docs/ 下的所有可瀏覽檔案
GET  /api/v1/settings/static-pages/content      回傳檔案原始內容（HTML / MD / PDF）
"""
import pathlib
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from typing import List

from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

# docs 目錄的絕對路徑（routers/ -> app/ -> backend/ -> portal/ -> docs/）
_DOCS_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "docs"

# 允許瀏覽的副檔名
_ALLOWED_EXTS = {".html", ".htm", ".pdf", ".md"}

# 副檔名 -> Content-Type
_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm":  "text/html; charset=utf-8",
    ".md":   "text/plain; charset=utf-8",
    ".pdf":  "application/pdf",
}


class StaticPageItem(BaseModel):
    filename: str   # 原始檔名
    url: str        # 供前端 apiClient.get() 使用（不含 /api/v1 前綴）


def _resolve(filename: str) -> pathlib.Path:
    """解析並驗證檔案路徑（防止目錄遊走）。"""
    decoded = urllib.parse.unquote(filename)
    path = (_DOCS_DIR / decoded).resolve()
    if not str(path).startswith(str(_DOCS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="非法檔案路徑")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="檔案不存在")
    if path.suffix.lower() not in _ALLOWED_EXTS:
        raise HTTPException(status_code=403, detail="不允許的檔案類型")
    return path


@router.get(
    "/static-pages",
    response_model=List[StaticPageItem],
    summary="列出 docs 靜態頁面清單",
)
def list_static_pages(
    current_user: User = Depends(get_current_user),
):
    """掃描 portal/docs/ 目錄，回傳允許瀏覽的靜態頁面清單（依檔名排序）。"""
    items: List[StaticPageItem] = []

    if not _DOCS_DIR.is_dir():
        return items

    for entry in sorted(_DOCS_DIR.iterdir()):
        if entry.is_file() and entry.suffix.lower() in _ALLOWED_EXTS:
            encoded = urllib.parse.quote(entry.name)
            # url 不含 /api/v1，apiClient 的 baseURL 會自動補上
            items.append(StaticPageItem(
                filename=entry.name,
                url=f"/settings/static-pages/content?filename={encoded}",
            ))

    return items


@router.get(
    "/static-pages/content",
    summary="回傳靜態頁面原始內容",
)
def get_static_page_content(
    filename: str,
    current_user: User = Depends(get_current_user),
):
    """
    讀取 portal/docs/<filename> 的原始內容並回傳。
    HTML / MD 回傳文字；PDF 回傳二進位。
    """
    path = _resolve(filename)
    content_type = _CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")

    if path.suffix.lower() == ".pdf":
        return Response(
            content=path.read_bytes(),
            media_type=content_type,
            headers={"Content-Disposition": f'inline; filename="{urllib.parse.quote(path.name)}"'},
        )

    return Response(
        content=path.read_text(encoding="utf-8"),
        media_type=content_type,
    )
