"""
簽核系統 API Router
Prefix: /api/v1/approvals
"""
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.approval import (
    AddStepRequest,
    ApprovalActionRequest,
    ApprovalCreate,
    ApprovalDetail,
    ApprovalListResponse,
    ApprovalSearchItem,
    ReorderRequest,
)
from app.services import approval_service as svc

router = APIRouter()


# ── 清單 ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=ApprovalListResponse, summary="簽核清單")
def list_approvals(
    scope: str = Query("todo", description="all|mine|todo"),
    status: str = Query("all",  description="all|pending|approved|rejected"),
    q: str = Query("",    description="關鍵字"),
    date_from: str = Query(""),
    date_to: str = Query(""),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.list_approvals(
        user=current_user,
        db=db,
        scope=scope,
        status_filter=status,
        q=q,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page,
    )


# ── 搜尋（JSON，供清單頁 fetch） ───────────────────────────────────────────────

@router.get("/search", response_model=List[ApprovalSearchItem], summary="搜尋簽核單")
def search(
    q: str = Query(""),
    scope: str = Query("all"),
    status: str = Query("all"),
    date_from: str = Query(""),
    date_to: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.search_approvals(
        user=current_user,
        db=db,
        q=q,
        scope=scope,
        status_filter=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


# ── 可選簽核人清單（來自 Portal users） ──────────────────────────────────────

@router.get("/approvers", summary="取得可選簽核人清單")
def list_approvers(
    q: str = Query("", description="姓名/Email 關鍵字"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter(User.is_active == True)
    if q:
        like = f"%{q}%"
        query = query.filter(
            User.full_name.ilike(like) | User.email.ilike(like)
        )
    users = query.order_by(User.full_name).limit(100).all()
    return [
        {"user_id": u.id, "name": u.full_name, "email": u.email}
        for u in users
    ]


# ── 新增 ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=ApprovalDetail, status_code=status.HTTP_201_CREATED, summary="新增簽核單")
async def create_approval(
    payload: ApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.approver_chain:
        raise HTTPException(status_code=400, detail="至少需要一位簽核人")
    approval = svc.create_approval(payload=payload, user=current_user, db=db)
    detail = svc.get_approval(approval.id, current_user, db)
    return detail


# ── 新增（含附件，multipart） ─────────────────────────────────────────────────

@router.post("/with-files", response_model=ApprovalDetail, status_code=status.HTTP_201_CREATED, summary="新增簽核單（含附件）")
async def create_approval_with_files(
    subject: str = Form(...),
    description: str = Form(""),
    confidential: str = Form(""),
    requester_dept: str = Form(""),
    view_scope: str = Form("restricted"),
    publish_memo: int = Form(0),
    approver_chain: str = Form(...),   # JSON string
    files: List[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import json
    from app.schemas.approval import ApproverIn

    try:
        chain_raw = json.loads(approver_chain)
        chain = [ApproverIn(**x) for x in chain_raw]
    except Exception:
        raise HTTPException(status_code=400, detail="approver_chain 格式錯誤")

    if not chain:
        raise HTTPException(status_code=400, detail="至少需要一位簽核人")

    payload = ApprovalCreate(
        subject=subject,
        description=description,
        confidential=confidential,
        requester_dept=requester_dept,
        view_scope=view_scope,
        publish_memo=publish_memo,
        approver_chain=chain,
    )
    approval = svc.create_approval(payload=payload, user=current_user, db=db)

    valid_files = [f for f in files if f and f.filename]
    if valid_files:
        await svc.save_files_async(approval.id, current_user, valid_files, db)

    return svc.get_approval(approval.id, current_user, db)


# ── 詳情 ─────────────────────────────────────────────────────────────────────

@router.get("/{approval_id}", response_model=ApprovalDetail, summary="簽核詳情")
def get_approval(
    approval_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = svc.get_approval(approval_id, current_user, db)
    if detail is None:
        raise HTTPException(status_code=404, detail="不存在或無權限查閱")
    return detail


# ── 簽核動作（核准/退回） ──────────────────────────────────────────────────────

@router.post("/{approval_id}/action", summary="執行簽核（核准/退回）")
def do_action(
    approval_id: str,
    body: ApprovalActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action 必須是 approve 或 reject")
    ok, err = svc.do_action(approval_id, body.action, body.comment, current_user, db)
    if not ok:
        code_map = {
            "not_found": 404,
            "approval_not_pending": 400,
            "no_pending_step": 400,
            "not_approver": 403,
            "comment_required": 400,
        }
        raise HTTPException(status_code=code_map.get(err, 400), detail=err)
    return {"ok": True}


# ── 調整關卡順序 ─────────────────────────────────────────────────────────────

@router.post("/{approval_id}/steps/reorder", summary="調整未簽關卡順序")
def reorder_steps(
    approval_id: str,
    body: ReorderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok, err = svc.reorder_steps(approval_id, body.order, current_user, db)
    if not ok:
        code_map = {"not_found": 404, "permission_denied": 403}
        raise HTTPException(status_code=code_map.get(err, 400), detail=err)
    return {"ok": True}


# ── 插入關卡 ─────────────────────────────────────────────────────────────────

@router.post("/{approval_id}/steps/add", summary="插入新簽核關卡")
def add_step(
    approval_id: str,
    body: AddStepRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok, err = svc.add_step(approval_id, body, current_user, db)
    if not ok:
        code_map = {"not_found": 404, "permission_denied": 403}
        raise HTTPException(status_code=code_map.get(err, 400), detail=err)
    return {"ok": True}


# ── 移除關卡 ─────────────────────────────────────────────────────────────────

@router.delete("/{approval_id}/steps/{step_id}", summary="移除未簽關卡")
def remove_step(
    approval_id: str,
    step_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok, err = svc.remove_step(approval_id, step_id, current_user, db)
    if not ok:
        code_map = {"not_found": 404, "permission_denied": 403}
        raise HTTPException(status_code=code_map.get(err, 400), detail=err)
    return {"ok": True}


# ── 附件上傳 ─────────────────────────────────────────────────────────────────

@router.post("/{approval_id}/files", summary="上傳附件")
async def upload_file(
    approval_id: str,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.approval import Approval

    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="not_found")
    if not svc.can_view(a, current_user, db):
        raise HTTPException(status_code=403, detail="permission_denied")
    valid = [f for f in files if f and f.filename]
    if not valid:
        raise HTTPException(status_code=400, detail="no_files")
    await svc.save_files_async(approval_id, current_user, valid, db)
    return {"ok": True, "count": len(valid)}


# ── 附件下載 ─────────────────────────────────────────────────────────────────

@router.get("/{approval_id}/files/{file_id}", summary="下載附件")
def download_file(
    approval_id: str,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.approval import Approval, ApprovalFile

    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="not_found")
    if not svc.can_view(a, current_user, db):
        raise HTTPException(status_code=403, detail="permission_denied")

    f = (
        db.query(ApprovalFile)
        .filter(ApprovalFile.id == file_id, ApprovalFile.approval_id == approval_id)
        .first()
    )
    if not f:
        raise HTTPException(status_code=404, detail="file_not_found")

    path = svc.UPLOAD_ROOT / approval_id / f.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="file_missing_on_disk")

    return FileResponse(
        str(path),
        media_type=f.content_type or "application/octet-stream",
        filename=f.orig_name,
    )
