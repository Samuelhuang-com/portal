"""
通用上傳 Router — 供 Rich Text Editor 插入圖片使用
Prefix: /api/v1/upload

回傳格式：{ "url": "/api/v1/upload/image/<filename>" }
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

# 圖片儲存目錄（backend 執行目錄下）
IMAGE_ROOT = Path("uploads/images")

ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "image/svg+xml", "image/bmp",
}
MAX_SIZE = 10 * 1024 * 1024   # 10 MB


@router.post("/image", summary="上傳圖片（供 Editor 使用）")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="只接受圖片格式（jpg/png/gif/webp）")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="圖片大小不得超過 10 MB")

    IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "img.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{suffix}"
    (IMAGE_ROOT / filename).write_bytes(content)

    return {"url": f"/api/v1/upload/image/{filename}"}


@router.get("/image/{filename}", summary="取得圖片")
async def get_image(filename: str):
    # 防止路徑穿越
    safe = Path(filename).name
    path = IMAGE_ROOT / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="image not found")
    return FileResponse(str(path))
