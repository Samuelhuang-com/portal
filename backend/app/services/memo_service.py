"""
公告系統 Service Layer
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from app.core.time import twnow
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.memo import Memo
from app.models.memo_file import MemoFile
from app.models.user import User
from app.schemas.memo import MemoCreate, MemoDetail, MemoListItem, MemoListResponse, MemoUpdate

# 附件儲存目錄（backend 執行目錄下）
MEMO_FILE_ROOT = Path("uploads/memo_files")


def _now() -> datetime:
    return twnow()


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]*?>", "", s or "")


def _is_admin(user: User, db: Session) -> bool:
    from app.models.role import Role
    from app.models.user_role import UserRole
    rows = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    return bool({r[0] for r in rows} & {"system_admin", "tenant_admin", "admin"})


def can_view(memo: Memo, user: User, db: Session) -> bool:
    if _is_admin(user, db):
        return True
    vis = (memo.visibility or "org").lower()
    if vis == "org":
        return True
    # restricted：僅作者本人
    return memo.author_id == user.id


# ── CRUD ─────────────────────────────────────────────────────────────────────

def create_memo(
    payload: MemoCreate,
    user: User,
    db: Session,
    source: str = "manual",
    source_id: str = "",
) -> Memo:
    memo = Memo(
        id=str(uuid.uuid4()),
        title=payload.title,
        body=payload.body,
        visibility=payload.visibility,
        author=user.full_name,
        author_id=user.id,
        doc_no=payload.doc_no,
        recipient=payload.recipient,
        source=source,
        source_id=source_id,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(memo)
    db.commit()
    db.refresh(memo)
    return memo


def create_memo_from_approval(
    approval_id: str,
    title: str,
    body: str,
    requester_name: str,
    requester_id: str,
    db: Session,
) -> Memo:
    """簽核完成後自動建立 Memo（內部呼叫，不需 User 物件）"""
    memo = Memo(
        id=str(uuid.uuid4()),
        title=f"【簽核公告】{title}",
        body=body,
        visibility="org",
        author=requester_name,
        author_id=requester_id,
        doc_no="",
        recipient="",
        source="approval",
        source_id=approval_id,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(memo)
    # 不在此 commit — 由 caller 統一 commit
    return memo


def list_memos(
    user: User,
    db: Session,
    q: str = "",
    visibility: str = "all",
    page: int = 1,
    per_page: int = 20,
) -> MemoListResponse:
    is_admin = _is_admin(user, db)
    query = db.query(Memo)

    # 可見性限制
    if not is_admin:
        query = query.filter(
            (Memo.visibility == "org") | (Memo.author_id == user.id)
        )

    if q:
        like = f"%{q}%"
        query = query.filter(
            Memo.title.ilike(like) | Memo.body.ilike(like) | Memo.author.ilike(like)
        )

    if visibility in ("org", "restricted"):
        query = query.filter(Memo.visibility == visibility)

    total = query.count()
    memos = (
        query.order_by(Memo.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    items = [
        MemoListItem(
            id=m.id,
            title=m.title,
            preview=_strip_html(m.body)[:160],
            visibility=m.visibility,
            author=m.author,
            doc_no=m.doc_no,
            recipient=m.recipient,
            source=m.source,
            source_id=m.source_id,
            created_at=m.created_at,
        )
        for m in memos
    ]
    return MemoListResponse(items=items, total=total, page=page, per_page=per_page)


def get_memo(memo_id: str, user: User, db: Session) -> Optional[MemoDetail]:
    m = db.query(Memo).filter(Memo.id == memo_id).first()
    if not m:
        return None
    if not can_view(m, user, db):
        return None
    return MemoDetail.model_validate(m)


def update_memo(
    memo_id: str, payload: MemoUpdate, user: User, db: Session
) -> tuple[bool, str]:
    m = db.query(Memo).filter(Memo.id == memo_id).first()
    if not m:
        return False, "not_found"
    # 僅作者或 admin 可改
    if m.author_id != user.id and not _is_admin(user, db):
        return False, "permission_denied"
    if payload.title is not None:
        m.title = payload.title
    if payload.body is not None:
        m.body = payload.body
    if payload.visibility is not None:
        m.visibility = payload.visibility
    if payload.doc_no is not None:
        m.doc_no = payload.doc_no
    if payload.recipient is not None:
        m.recipient = payload.recipient
    m.updated_at = _now()
    db.commit()
    return True, ""


def delete_memo(memo_id: str, user: User, db: Session) -> tuple[bool, str]:
    m = db.query(Memo).filter(Memo.id == memo_id).first()
    if not m:
        return False, "not_found"
    if m.author_id != user.id and not _is_admin(user, db):
        return False, "permission_denied"
    db.delete(m)
    db.commit()
    return True, ""


# ── 附件管理 ──────────────────────────────────────────────────────────────────

def save_memo_files(
    memo_id: str,
    files: list,          # list of starlette UploadFile
    uploader_name: str,
    db: Session,
) -> List[MemoFile]:
    """儲存上傳的附件並寫入 DB，回傳 MemoFile list"""
    MEMO_FILE_ROOT.mkdir(parents=True, exist_ok=True)
    saved: List[MemoFile] = []
    for f in files:
        content = f.file.read()
        suffix = Path(f.filename or "file").suffix or ""
        stored = f"{uuid.uuid4().hex}{suffix}"
        (MEMO_FILE_ROOT / stored).write_bytes(content)
        mf = MemoFile(
            id=str(uuid.uuid4()),
            memo_id=memo_id,
            orig_name=f.filename or stored,
            stored_name=stored,
            content_type=f.content_type or "application/octet-stream",
            size_bytes=len(content),
            uploaded_by=uploader_name,
            uploaded_at=_now(),
        )
        db.add(mf)
        saved.append(mf)
    db.commit()
    return saved


def get_memo_file(memo_id: str, file_id: str, db: Session) -> Optional[tuple]:
    """回傳 (MemoFile, Path) 或 None"""
    mf = (
        db.query(MemoFile)
        .filter(MemoFile.id == file_id, MemoFile.memo_id == memo_id)
        .first()
    )
    if not mf:
        return None
    path = MEMO_FILE_ROOT / mf.stored_name
    if not path.exists():
        return None
    return mf, path
