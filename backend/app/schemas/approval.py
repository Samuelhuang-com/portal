"""
簽核系統 Pydantic Schemas
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ── 關卡 ─────────────────────────────────────────────────────────────────────

class StepOut(BaseModel):
    id: str
    step_order: int
    approver_id: str
    approver_name: str
    approver_email: str
    status: str                    # pending | approved | rejected
    decided_at: Optional[datetime]
    comment: str

    class Config:
        from_attributes = True


# ── 歷程 ─────────────────────────────────────────────────────────────────────

class ActionOut(BaseModel):
    id: str
    step_id: Optional[str]
    actor: str
    actor_id: str
    action: str
    note: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── 附件 ─────────────────────────────────────────────────────────────────────

class FileOut(BaseModel):
    id: str
    orig_name: str
    content_type: str
    size_bytes: int
    uploaded_by: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ── 主單清單 ─────────────────────────────────────────────────────────────────

class ApprovalListItem(BaseModel):
    id: str
    subject: str
    requester: str
    requester_id: str
    status: str
    current_step: int
    submitted_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApprovalListResponse(BaseModel):
    items: List[ApprovalListItem]
    total: int


# ── 主單詳情 ─────────────────────────────────────────────────────────────────

class ApprovalDetail(BaseModel):
    id: str
    subject: str
    description: str
    confidential: str              # 僅 admin/申請人/簽核人可見
    requester: str
    requester_id: str
    requester_dept: str
    status: str
    current_step: int
    view_scope: str
    publish_memo: int
    submitted_at: datetime
    updated_at: datetime
    steps: List[StepOut]
    actions: List[ActionOut]
    attachments: List[FileOut]
    can_act: bool                  # 是否可簽核（目前輪到我）
    can_manage: bool               # 是否可管理串簽（申請人或 admin）

    class Config:
        from_attributes = True


# ── 新增簽核單 ────────────────────────────────────────────────────────────────

class ApproverIn(BaseModel):
    user_id: str                   # Portal user.id（可為空字串代表純姓名輸入）
    name: str                      # full_name
    email: str = ""

class ApprovalCreate(BaseModel):
    subject: str
    description: str = ""
    confidential: str = ""
    requester_dept: str = ""
    view_scope: str = "restricted"
    publish_memo: int = 0
    approver_chain: List[ApproverIn]


# ── 簽核動作 ─────────────────────────────────────────────────────────────────

class ApprovalActionRequest(BaseModel):
    action: str    # approve | reject
    comment: str


# ── 調整關卡順序 ─────────────────────────────────────────────────────────────

class ReorderRequest(BaseModel):
    order: List[str]               # step id 清單，新順序


# ── 新增關卡（已流轉中插入） ──────────────────────────────────────────────────

class AddStepRequest(BaseModel):
    approver: ApproverIn
    insert_after: int = -1         # 插入在哪一關之後（-1=加在最後）


# ── 搜尋結果 ─────────────────────────────────────────────────────────────────

class ApprovalSearchItem(BaseModel):
    id: str
    subject: str
    requester: str
    status: str
    current_step: int
    submitted_at: datetime
    preview: str                         # description 前 120 字（純文字）
    current_approver_name: str = ""      # 目前待簽關卡的簽核人姓名（pending 時才有值）
