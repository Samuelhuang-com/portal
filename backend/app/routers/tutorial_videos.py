"""
影音教學 API Router
Prefix: /api/v1/tutorial-videos

觀看：所有登入使用者（get_current_user）
模組／影片的新增、編輯、刪除、排序：需 tutorial_videos_manage 權限
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
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
    if video_file.content_type not in svc.ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="只接受 MP4／MOV 影片格式")

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
    return FileResponse(str(path), media_type=tv.video_content_type or "video/mp4")


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
