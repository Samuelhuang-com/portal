"""
公告系統 API Router
Prefix: /api/v1/memos
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.memo import MemoCreate, MemoDetail, MemoFileOut, MemoListResponse, MemoUpdate
from app.services import memo_service as svc

router = APIRouter()


# ── 清單（分頁 + 搜尋） ────────────────────────────────────────────────────────

@router.get("", response_model=MemoListResponse, summary="公告清單")
def list_memos(
    q: str = Query("", description="關鍵字（主旨/內文/作者）"),
    visibility: str = Query("all", description="all|org|restricted"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=5, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.list_memos(
        user=current_user,
        db=db,
        q=q,
        visibility=visibility,
        page=page,
        per_page=per_page,
    )


# ── 詳情 ─────────────────────────────────────────────────────────────────────

@router.get("/{memo_id}", response_model=MemoDetail, summary="公告詳情")
def get_memo(
    memo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = svc.get_memo(memo_id, current_user, db)
    if detail is None:
        raise HTTPException(status_code=404, detail="公告不存在或無權限查閱")
    return detail


# ── 新增 ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=MemoDetail, status_code=status.HTTP_201_CREATED, summary="新增公告")
def create_memo(
    payload: MemoCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="標題不得為空")
    memo = svc.create_memo(payload=payload, user=current_user, db=db, source="manual")
    return svc.get_memo(memo.id, current_user, db)


# ── 更新 ─────────────────────────────────────────────────────────────────────

@router.patch("/{memo_id}", response_model=MemoDetail, summary="更新公告")
def update_memo(
    memo_id: str,
    payload: MemoUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok, err = svc.update_memo(memo_id, payload, current_user, db)
    if not ok:
        raise HTTPException(status_code=403 if err == "permission_denied" else 404, detail=err)
    return svc.get_memo(memo_id, current_user, db)


# ── 刪除 ─────────────────────────────────────────────────────────────────────

@router.delete("/{memo_id}", summary="刪除公告")
def delete_memo(
    memo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok, err = svc.delete_memo(memo_id, current_user, db)
    if not ok:
        raise HTTPException(status_code=403 if err == "permission_denied" else 404, detail=err)
    return {"ok": True}


# ── 附件上傳 ─────────────────────────────────────────────────────────────────

@router.post(
    "/{memo_id}/files",
    response_model=List[MemoFileOut],
    status_code=status.HTTP_201_CREATED,
    summary="上傳公告附件",
)
def upload_memo_files(
    memo_id: str,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 確認公告存在且有權限
    detail = svc.get_memo(memo_id, current_user, db)
    if detail is None:
        raise HTTPException(status_code=404, detail="公告不存在或無權限")
    saved = svc.save_memo_files(
        memo_id=memo_id,
        files=files,
        uploader_name=current_user.full_name,
        db=db,
    )
    return saved


# ── 附件下載 ─────────────────────────────────────────────────────────────────

@router.get("/{memo_id}/files/{file_id}", summary="下載公告附件")
def download_memo_file(
    memo_id: str,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 確認公告可見
    detail = svc.get_memo(memo_id, current_user, db)
    if detail is None:
        raise HTTPException(status_code=404, detail="公告不存在或無權限")
    result = svc.get_memo_file(memo_id, file_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="附件不存在")
    mf, path = result
    return FileResponse(
        str(path),
        media_type=mf.content_type,
        filename=mf.orig_name,
    )
