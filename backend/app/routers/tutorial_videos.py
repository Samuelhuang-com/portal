"""
影音教學 API Router
Prefix: /api/v1/tutorial-videos

觀看：所有登入使用者（get_current_user）
模組／影片的新增、編輯、刪除、排序：需 tutorial_videos_manage 權限
"""
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.tutorial_video import (
    TutorialVideoListResponse, TutorialVideoModuleCreate, TutorialVideoModuleOut,
    TutorialVideoModuleReorderRequest, TutorialVideoModuleUpdate, TutorialVideoOut,
    TutorialVideoReorderRequest, TutorialVideoUpdate,
)
from app.services import tutorial_video_service as svc

router = APIRouter()


def _verify_query_token(token: Optional[str], db: Session) -> User:
    """
    供 <video> 標籤直接播放使用（瀏覽器無法在媒體請求上帶 Authorization header）。
    與 luqun_repair / dazhi_repair 匯出端點相同的 ?token=<JWT> 慣例。
    """
    if not token:
        raise HTTPException(status_code=401, detail="未提供驗證 token")
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="token 無效或已過期")
    user = db.query(User).filter(User.id == payload.get("sub"), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="使用者不存在或已停用")
    return user


_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")
_STREAM_CHUNK_SIZE = 1024 * 1024  # 1MB


def _range_file_response(path: Path, range_header: Optional[str], media_type: str) -> StreamingResponse:
    """
    支援 HTTP Range Requests 的檔案回應，讓 <video> 播放器可以拖曳進度條／快轉快退。

    starlette==0.37.2（目前 fastapi==0.111.1 對應版本）的 FileResponse 不支援 Range
    request，瀏覽器送出的 Range 請求會被忽略、永遠整檔回傳 200，導致播放器的進度條
    拖曳、點擊跳轉、快轉快退全部失效。這裡自行解析 Range header，只讀取請求範圍內的
    bytes，回傳 206 Partial Content（沒有 Range header 時仍回傳 200 全檔，但附上
    Accept-Ranges: bytes 讓瀏覽器知道之後可以送 Range 請求)。
    """
    file_size = path.stat().st_size
    start, end = 0, file_size - 1
    status_code = 200

    if range_header:
        match = _RANGE_RE.match(range_header.strip())
        if match:
            start_str, end_str = match.groups()
            if start_str == "" and end_str != "":
                # 後綴範圍："bytes=-500" 表示最後 500 bytes
                length = min(int(end_str), file_size)
                start = max(file_size - length, 0)
                end = file_size - 1
            elif start_str != "":
                start = int(start_str)
                end = int(end_str) if end_str != "" else file_size - 1
            status_code = 206

    start = max(0, start)
    end = min(end, file_size - 1)
    if start > end or start >= file_size:
        raise HTTPException(
            status_code=416,
            detail="Range Not Satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    content_length = end - start + 1

    def _iter_file():
        with open(path, "rb") as f:
            f.seek(start)
            remaining = content_length
            while remaining > 0:
                chunk = f.read(min(_STREAM_CHUNK_SIZE, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
    }
    if status_code == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

    return StreamingResponse(_iter_file(), status_code=status_code, media_type=media_type, headers=headers)


# ── 教學模組主檔 ──────────────────────────────────────────────────────────────

@router.get("/modules", response_model=list[TutorialVideoModuleOut], summary="教學模組清單")
def list_modules(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.list_modules(db, category=category)


@router.post(
    "/modules",
    response_model=TutorialVideoModuleOut,
    status_code=status.HTTP_201_CREATED,
    summary="新增教學模組",
)
def create_module(
    payload: TutorialVideoModuleCreate,
    current_user: User = Depends(require_permission("tutorial_videos_manage")),
    db: Session = Depends(get_db),
):
    if payload.category not in svc.VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail="category 必須是 hotel / mall / group 其中之一")
    if not payload.module_name.strip():
        raise HTTPException(status_code=400, detail="模組名稱不得為空")
    module = svc.create_module(payload, db)
    return {
        "id": module.id, "category": module.category, "module_name": module.module_name,
        "module_route": module.module_route, "sort_order": module.sort_order,
        "video_count": 0, "created_at": module.created_at, "updated_at": module.updated_at,
    }


@router.patch("/modules/{module_id}", response_model=TutorialVideoModuleOut, summary="編輯教學模組")
def update_module(
    module_id: str,
    payload: TutorialVideoModuleUpdate,
    current_user: User = Depends(require_permission("tutorial_videos_manage")),
    db: Session = Depends(get_db),
):
    ok, err = svc.update_module(module_id, payload, db)
    if not ok:
        raise HTTPException(status_code=404, detail=err)
    matches = [m for m in svc.list_modules(db) if m["id"] == module_id]
    return matches[0]


@router.delete("/modules/{module_id}", summary="刪除教學模組（含所有集數與檔案）")
def delete_module(
    module_id: str,
    current_user: User = Depends(require_permission("tutorial_videos_manage")),
    db: Session = Depends(get_db),
):
    ok, err = svc.delete_module(module_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail=err)
    return {"ok": True}


@router.put("/modules/reorder", summary="拖曳排序：模組順序")
def reorder_modules(
    payload: TutorialVideoModuleReorderRequest,
    current_user: User = Depends(require_permission("tutorial_videos_manage")),
    db: Session = Depends(get_db),
):
    svc.reorder_modules(payload.category, payload.ordered_ids, db)
    return {"ok": True}


# ── 單集影片 ──────────────────────────────────────────────────────────────────

@router.get("", response_model=TutorialVideoListResponse, summary="影音教學清單")
def list_tutorial_videos(
    category: Optional[str] = None,
    module_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = svc.list_videos(db, category=category, module_id=module_id)
    return TutorialVideoListResponse(
        items=[TutorialVideoOut.model_validate(v) for v in items],
        total=len(items),
    )


@router.get("/{video_id}", response_model=TutorialVideoOut, summary="影音教學詳情")
def get_tutorial_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tv = svc.get_video(video_id, db)
    if not tv:
        raise HTTPException(status_code=404, detail="找不到此教學影片")
    return tv


@router.post(
    "",
    response_model=TutorialVideoOut,
    status_code=status.HTTP_201_CREATED,
    summary="上傳教學影片",
)
def create_tutorial_video(
    module_id: str = Form(...),
    episode: str = Form(""),
    title: str = Form(...),
    description: str = Form(""),
    sort_order: Optional[int] = Form(None),
    video_file: UploadFile = File(...),
    script_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_permission("tutorial_videos_manage")),
    db: Session = Depends(get_db),
):
    if not svc.get_module(module_id, db):
        raise HTTPException(status_code=404, detail="找不到指定的教學模組")
    if not svc.is_allowed_video_file(video_file):
        raise HTTPException(
            status_code=400,
            detail=f"只接受 MP4／MOV 影片格式（偵測到的格式：{video_file.content_type or '未知'}，檔名：{video_file.filename}）",
        )

    tv = svc.create_video(
        module_id=module_id,
        episode=episode,
        title=title,
        description=description,
        sort_order=sort_order,
        uploaded_by=current_user.full_name,
        video_file=video_file,
        script_file=script_file,
        db=db,
    )
    return tv


@router.patch("/{video_id}", response_model=TutorialVideoOut, summary="編輯教學影片資訊")
def update_tutorial_video(
    video_id: str,
    payload: TutorialVideoUpdate,
    current_user: User = Depends(require_permission("tutorial_videos_manage")),
    db: Session = Depends(get_db),
):
    ok, err = svc.update_video(video_id, payload, db)
    if not ok:
        raise HTTPException(status_code=404, detail=err)
    return svc.get_video(video_id, db)


@router.delete("/{video_id}", summary="刪除教學影片")
def delete_tutorial_video(
    video_id: str,
    current_user: User = Depends(require_permission("tutorial_videos_manage")),
    db: Session = Depends(get_db),
):
    ok, err = svc.delete_video(video_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail=err)
    return {"ok": True}


@router.put("/{module_id}/videos/reorder", summary="拖曳排序：模組內集數順序")
def reorder_tutorial_videos(
    module_id: str,
    payload: TutorialVideoReorderRequest,
    current_user: User = Depends(require_permission("tutorial_videos_manage")),
    db: Session = Depends(get_db),
):
    svc.reorder_videos(module_id, payload.ordered_ids, db)
    return {"ok": True}


@router.get("/{video_id}/stream", summary="播放教學影片（MP4 串流，支援拖曳進度）")
def stream_tutorial_video(
    video_id: str,
    request: Request,
    token: Optional[str] = Query(None, description="供 <video> 標籤播放使用；一般 API 呼叫請改用 Authorization header"),
    db: Session = Depends(get_db),
):
    _verify_query_token(token, db)
    tv = svc.get_video(video_id, db)
    if not tv:
        raise HTTPException(status_code=404, detail="找不到此教學影片")
    path = svc.get_video_file_path(tv)
    if not path:
        raise HTTPException(status_code=404, detail="影片檔案不存在")
    return _range_file_response(
        path, request.headers.get("range"), tv.video_content_type or "video/mp4",
    )


@router.get("/{video_id}/script", summary="下載 TTS 逐字稿")
def download_tutorial_script(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tv = svc.get_video(video_id, db)
    if not tv:
        raise HTTPException(status_code=404, detail="找不到此教學影片")
    path = svc.get_script_file_path(tv)
    if not path:
        raise HTTPException(status_code=404, detail="此集沒有逐字稿檔案")
    return FileResponse(str(path), filename=tv.script_orig_name or "script.txt")
