"""
簽核系統 Service Layer
負責所有業務邏輯，Router 僅做參數校驗 & 回傳
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from app.core.time import twnow
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.approval import Approval, ApprovalAction, ApprovalFile, ApprovalStep
from app.models.user import User
from app.schemas.approval import (
    AddStepRequest,
    ApprovalCreate,
    ApprovalDetail,
    ApprovalListItem,
    ApprovalListResponse,
    ApprovalSearchItem,
    FileOut,
    ActionOut,
    StepOut,
)

# 附件儲存目錄（與 main.py 同層即可）
UPLOAD_ROOT = Path("uploads/approvals")


# ── 工具函式 ────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return twnow()


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]*?>", "", s or "")


def _safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-\.]+", "_", name)


def _is_admin(user: User, db: Session) -> bool:
    from app.models.role import Role
    from app.models.user_role import UserRole

    rows = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    role_names = {r[0] for r in rows}
    return bool(role_names & {"system_admin", "tenant_admin", "admin"})


def _renumber_steps(approval_id: str, db: Session) -> None:
    """重新為 pending steps 編號（避免間隔）"""
    steps = (
        db.query(ApprovalStep)
        .filter(ApprovalStep.approval_id == approval_id)
        .order_by(ApprovalStep.step_order)
        .all()
    )
    for i, s in enumerate(steps):
        s.step_order = i
    db.commit()


def _user_involved(approval: Approval, user: User, db: Session) -> bool:
    """是否為申請人或其中一位簽核人"""
    if approval.requester_id == user.id:
        return True
    steps = db.query(ApprovalStep).filter(ApprovalStep.approval_id == approval.id).all()
    return any(s.approver_id == user.id or s.approver_name == user.full_name for s in steps)


def can_view(approval: Approval, user: User, db: Session) -> bool:
    if _is_admin(user, db):
        return True
    scope = (approval.view_scope or "restricted").strip().lower()
    if scope == "org":
        return True
    return _user_involved(approval, user, db)


def can_manage(approval: Approval, user: User, db: Session) -> bool:
    """申請人或 admin 可管理串簽鏈"""
    if _is_admin(user, db):
        return True
    return approval.requester_id == user.id


# ── CRUD ─────────────────────────────────────────────────────────────────────


def create_approval(
    payload: ApprovalCreate,
    user: User,
    db: Session,
    files: list[UploadFile] | None = None,
) -> Approval:
    approval = Approval(
        id=str(uuid.uuid4()),
        subject=payload.subject,
        description=payload.description,
        confidential=payload.confidential,
        requester=user.full_name,
        requester_id=user.id,
        requester_dept=payload.requester_dept,
        status="pending",
        current_step=0,
        view_scope=payload.view_scope,
        publish_memo=payload.publish_memo,
        submitted_at=_now(),
        updated_at=_now(),
    )
    db.add(approval)
    db.flush()  # 取得 id 後再插 steps

    for idx, appr in enumerate(payload.approver_chain):
        step = ApprovalStep(
            id=str(uuid.uuid4()),
            approval_id=approval.id,
            step_order=idx,
            approver_id=appr.user_id,
            approver_name=appr.name,
            approver_email=appr.email,
            status="pending",
        )
        db.add(step)

    action = ApprovalAction(
        id=str(uuid.uuid4()),
        approval_id=approval.id,
        actor=user.full_name,
        actor_id=user.id,
        action="submit",
        note="",
        created_at=_now(),
    )
    db.add(action)
    db.commit()
    db.refresh(approval)
    return approval


def save_files(approval_id: str, user: User, files: list[UploadFile], db: Session) -> None:
    """同步儲存附件（Router 端用 async 讀取後傳入 bytes）"""
    # 實際檔案讀取在 Router 端（async），這裡只做 DB 記錄
    pass


async def save_files_async(
    approval_id: str, user: User, files: list[UploadFile], db: Session
) -> None:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    updir = UPLOAD_ROOT / approval_id
    updir.mkdir(parents=True, exist_ok=True)

    for uf in files:
        if not uf or not uf.filename:
            continue
        orig = _safe_filename(uf.filename)
        ext = "".join(Path(orig).suffixes)
        stored = f"{uuid.uuid4().hex}{ext}"
        fullpath = updir / stored
        size = 0
        content = await uf.read()
        fullpath.write_bytes(content)
        size = len(content)

        rec = ApprovalFile(
            id=str(uuid.uuid4()),
            approval_id=approval_id,
            orig_name=orig,
            stored_name=stored,
            content_type=uf.content_type or "",
            size_bytes=size,
            uploaded_by=user.full_name,
            uploaded_at=_now(),
        )
        db.add(rec)
    db.commit()


def get_approval(approval_id: str, user: User, db: Session) -> ApprovalDetail | None:
    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a:
        return None
    if not can_view(a, user, db):
        return None  # caller should raise 403

    steps = (
        db.query(ApprovalStep)
        .filter(ApprovalStep.approval_id == approval_id)
        .order_by(ApprovalStep.step_order)
        .all()
    )
    actions = (
        db.query(ApprovalAction)
        .filter(ApprovalAction.approval_id == approval_id)
        .order_by(ApprovalAction.created_at)
        .all()
    )
    attachments = (
        db.query(ApprovalFile)
        .filter(ApprovalFile.approval_id == approval_id)
        .order_by(ApprovalFile.uploaded_at)
        .all()
    )

    # 判斷目前使用者是否可簽核
    can_act = False
    if a.status == "pending" and a.current_step >= 0:
        for s in steps:
            if s.step_order == a.current_step and s.status == "pending":
                if s.approver_id == user.id or s.approver_name == user.full_name:
                    can_act = True
                break

    # 是否隱藏機敏欄位
    show_confidential = _is_admin(user, db) or _user_involved(a, user, db)
    confidential_val = a.confidential if show_confidential else "（無權限查閱）"

    return ApprovalDetail(
        id=a.id,
        subject=a.subject,
        description=a.description,
        confidential=confidential_val,
        requester=a.requester,
        requester_id=a.requester_id,
        requester_dept=a.requester_dept,
        status=a.status,
        current_step=a.current_step,
        view_scope=a.view_scope,
        publish_memo=a.publish_memo,
        submitted_at=a.submitted_at,
        updated_at=a.updated_at,
        steps=[StepOut.model_validate(s) for s in steps],
        actions=[ActionOut.model_validate(ac) for ac in actions],
        attachments=[FileOut.model_validate(f) for f in attachments],
        can_act=can_act,
        can_manage=can_manage(a, user, db),
    )


def list_approvals(
    user: User,
    db: Session,
    scope: str = "todo",
    status_filter: str = "all",
    q: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    per_page: int = 50,
) -> ApprovalListResponse:
    is_admin = _is_admin(user, db)
    query = db.query(Approval)

    # 關鍵字
    if q:
        like = f"%{q}%"
        query = query.filter(
            Approval.subject.ilike(like) | Approval.description.ilike(like) | Approval.requester.ilike(like)
        )

    # 狀態
    if status_filter in ("pending", "approved", "rejected"):
        query = query.filter(Approval.status == status_filter)

    # 日期範圍
    if date_from:
        query = query.filter(Approval.submitted_at >= date_from)
    if date_to:
        query = query.filter(Approval.submitted_at <= date_to + " 23:59:59")

    # ── 範圍過濾 ─────────────────────────────────────────────────────────────
    if is_admin and scope == "all":
        # admin 看全部，不加限制
        pass

    elif scope == "mine":
        # 我送出的：不論狀態，只看我是申請人的
        query = query.filter(Approval.requester_id == user.id)

    elif scope == "todo":
        # 我的待簽：
        #   ① 目前輪到我且尚未處理（can_act = True）
        #   ② 所有進行中（status=pending）且我在簽核鏈中的（任一關卡）
        # 兩者取聯集，讓使用者一眼看到「與我有關的所有待辦」
        involved_ids = (
            db.query(ApprovalStep.approval_id)
            .join(Approval, Approval.id == ApprovalStep.approval_id)
            .filter(
                (ApprovalStep.approver_id == user.id)
                | (ApprovalStep.approver_name == user.full_name),
                Approval.status == "pending",
            )
            .distinct()
            .all()
        )
        ids = list({r[0] for r in involved_ids})
        query = query.filter(Approval.id.in_(ids))

    else:
        # 全部（非 admin）：我送出的（任何狀態）+ 進行中且我在鏈中的
        involved_pending_ids = (
            db.query(ApprovalStep.approval_id)
            .join(Approval, Approval.id == ApprovalStep.approval_id)
            .filter(
                (ApprovalStep.approver_id == user.id)
                | (ApprovalStep.approver_name == user.full_name),
                Approval.status == "pending",
            )
            .distinct()
            .all()
        )
        ids = list({r[0] for r in involved_pending_ids})
        query = query.filter(
            (Approval.requester_id == user.id) | Approval.id.in_(ids)
        )

    total = query.count()
    items = (
        query.order_by(Approval.submitted_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return ApprovalListResponse(
        items=[ApprovalListItem.model_validate(a) for a in items],
        total=total,
    )


def do_action(
    approval_id: str, action: str, comment: str, user: User, db: Session
) -> tuple[bool, str]:
    """
    執行簽核動作。
    Returns (ok, error_msg)
    """
    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a:
        return False, "not_found"
    if a.status != "pending":
        return False, "approval_not_pending"

    steps = (
        db.query(ApprovalStep)
        .filter(ApprovalStep.approval_id == approval_id)
        .order_by(ApprovalStep.step_order)
        .all()
    )
    cur_step = next((s for s in steps if s.step_order == a.current_step), None)
    if not cur_step or cur_step.status != "pending":
        return False, "no_pending_step"

    # 確認是本關簽核人
    if cur_step.approver_id != user.id and cur_step.approver_name != user.full_name:
        return False, "not_approver"

    if not comment.strip():
        return False, "comment_required"

    now = _now()
    cur_step.status = "approved" if action == "approve" else "rejected"
    cur_step.decided_at = now
    cur_step.comment = comment.strip()

    act = ApprovalAction(
        id=str(uuid.uuid4()),
        approval_id=approval_id,
        step_id=cur_step.id,
        actor=user.full_name,
        actor_id=user.id,
        action=action,
        note=comment.strip(),
        created_at=now,
    )
    db.add(act)

    if action == "reject":
        a.status = "rejected"
        a.current_step = -1
    else:
        # 是否還有下一關
        remaining = [s for s in steps if s.step_order > a.current_step]
        if remaining:
            next_s = min(remaining, key=lambda s: s.step_order)
            a.current_step = next_s.step_order
        else:
            a.status = "approved"
            a.current_step = -1
            # ── 自動建立 Memo（若申請人勾選 publish_memo）──────────────────
            if a.publish_memo == 1:
                try:
                    from app.services.memo_service import create_memo_from_approval
                    create_memo_from_approval(
                        approval_id=a.id,
                        title=a.subject,
                        body=a.description or "",
                        requester_name=a.requester,
                        requester_id=a.requester_id,
                        db=db,
                    )
                    print(f"[Memo] 簽核 {a.id} 完成，已自動建立公告：{a.subject}")
                except Exception as e:
                    print(f"[Memo] 自動建立公告失敗：{e}")

    a.updated_at = now
    db.commit()
    return True, ""


def reorder_steps(
    approval_id: str, new_order: list[str], user: User, db: Session
) -> tuple[bool, str]:
    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a:
        return False, "not_found"
    if a.status != "pending":
        return False, "approval_not_pending"
    if not can_manage(a, user, db):
        return False, "permission_denied"

    # 只允許調整尚未簽核的關卡（step_order > current_step）
    pending_steps = (
        db.query(ApprovalStep)
        .filter(
            ApprovalStep.approval_id == approval_id,
            ApprovalStep.status == "pending",
            ApprovalStep.step_order > a.current_step,
        )
        .all()
    )
    allowed_ids = {s.id for s in pending_steps}
    if set(new_order) != allowed_ids:
        return False, "invalid_ids"

    # 先加大 step_order 避免唯一性衝突
    SHIFT = 100000
    for s in pending_steps:
        s.step_order += SHIFT

    next_order = a.current_step + 1
    id_to_step = {s.id: s for s in pending_steps}
    for sid in new_order:
        id_to_step[sid].step_order = next_order
        next_order += 1

    log = ApprovalAction(
        id=str(uuid.uuid4()),
        approval_id=approval_id,
        actor=user.full_name,
        actor_id=user.id,
        action="reorder_steps",
        note="調整未簽關卡順序",
        created_at=_now(),
    )
    db.add(log)
    db.commit()
    return True, ""


def add_step(
    approval_id: str, req: AddStepRequest, user: User, db: Session
) -> tuple[bool, str]:
    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a:
        return False, "not_found"
    if a.status != "pending":
        return False, "approval_not_pending"
    if not can_manage(a, user, db):
        return False, "permission_denied"

    steps = (
        db.query(ApprovalStep)
        .filter(ApprovalStep.approval_id == approval_id)
        .order_by(ApprovalStep.step_order)
        .all()
    )

    insert_after = req.insert_after  # -1 = 最後
    # 找插入位置：insert_after 是 step_order 值
    if insert_after < 0 or insert_after >= len(steps):
        new_order = max((s.step_order for s in steps), default=0) + 1
    else:
        # 把 insert_after 之後的都 +1
        new_order = insert_after + 1
        for s in steps:
            if s.step_order >= new_order:
                s.step_order += 1

    new_step = ApprovalStep(
        id=str(uuid.uuid4()),
        approval_id=approval_id,
        step_order=new_order,
        approver_id=req.approver.user_id,
        approver_name=req.approver.name,
        approver_email=req.approver.email,
        status="pending",
    )
    db.add(new_step)

    log = ApprovalAction(
        id=str(uuid.uuid4()),
        approval_id=approval_id,
        actor=user.full_name,
        actor_id=user.id,
        action="add_step",
        note=f"新增簽核關卡：{req.approver.name}",
        created_at=_now(),
    )
    db.add(log)
    db.commit()
    return True, ""


def remove_step(
    approval_id: str, step_id: str, user: User, db: Session
) -> tuple[bool, str]:
    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a:
        return False, "not_found"
    if a.status != "pending":
        return False, "approval_not_pending"
    if not can_manage(a, user, db):
        return False, "permission_denied"

    step = (
        db.query(ApprovalStep)
        .filter(ApprovalStep.id == step_id, ApprovalStep.approval_id == approval_id)
        .first()
    )
    if not step:
        return False, "step_not_found"
    if step.status != "pending":
        return False, "step_already_decided"
    if step.step_order == a.current_step:
        return False, "cannot_remove_current_step"

    name = step.approver_name
    db.delete(step)
    _renumber_steps(approval_id, db)

    log = ApprovalAction(
        id=str(uuid.uuid4()),
        approval_id=approval_id,
        actor=user.full_name,
        actor_id=user.id,
        action="remove_step",
        note=f"移除簽核關卡：{name}",
        created_at=_now(),
    )
    db.add(log)
    db.commit()
    return True, ""


def search_approvals(
    user: User,
    db: Session,
    q: str = "",
    scope: str = "all",
    status_filter: str = "all",
    date_from: str = "",
    date_to: str = "",
    limit: int = 50,
) -> list[ApprovalSearchItem]:
    result = list_approvals(
        user=user,
        db=db,
        scope=scope,
        status_filter=status_filter,
        q=q,
        date_from=date_from,
        date_to=date_to,
        page=1,
        per_page=limit,
    )
    item_ids = [i.id for i in result.items]

    approvals_raw = (
        db.query(Approval)
        .filter(Approval.id.in_(item_ids))
        .all()
    )
    desc_map = {a.id: a.description for a in approvals_raw}

    # ── 取出每張單子的「目前關卡簽核人」────────────────────────────────────────
    # 只撈 pending 且 current_step >= 0 的關卡，一次批次查詢避免 N+1
    pending_items = [i for i in result.items if i.status == "pending" and i.current_step >= 0]
    current_approver_map: dict[str, str] = {}
    if pending_items:
        # 取各單子目前關卡的步驟記錄
        steps_rows = (
            db.query(ApprovalStep.approval_id, ApprovalStep.approver_name)
            .filter(
                ApprovalStep.approval_id.in_([i.id for i in pending_items]),
                ApprovalStep.status == "pending",
            )
            .all()
        )
        # step_order 需對應 current_step，用 approval_id 反查
        current_step_map = {i.id: i.current_step for i in pending_items}
        steps_full = (
            db.query(ApprovalStep)
            .filter(
                ApprovalStep.approval_id.in_([i.id for i in pending_items]),
            )
            .all()
        )
        for s in steps_full:
            if s.step_order == current_step_map.get(s.approval_id):
                current_approver_map[s.approval_id] = s.approver_name

    return [
        ApprovalSearchItem(
            id=i.id,
            subject=i.subject,
            requester=i.requester,
            status=i.status,
            current_step=i.current_step,
            submitted_at=i.submitted_at,
            preview=_strip_html(desc_map.get(i.id, ""))[:120],
            current_approver_name=current_approver_map.get(i.id, ""),
        )
        for i in result.items
    ]
