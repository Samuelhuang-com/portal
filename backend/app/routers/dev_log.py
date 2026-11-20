"""
開發統計 API（/api/v1/dev-log）
- view：查看統計、條目與需求；manage：匯入 CHANGELOG／Jira CSV、編輯時間、建立與編輯需求、綁定需求（2026-11-20）
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.time import twnow
from app.dependencies import require_permission
from app.models.dev_log import DevLogEntry
from app.models.requirement import Requirement
from app.services.dev_log_service import (
    REPO_ROOT, REQ_PRIORITIES, REQ_STATUSES, apply_requirement_fields, import_entries,
    import_jira_csv, req_no, requirement_summary, stats, sync_from_git,
)

router = APIRouter()
VIEW = "dev_log_view"
MANAGE = "dev_log_manage"


def _to_dict(e: DevLogEntry) -> dict:
    return {
        "id": e.id,
        "entry_date": e.entry_date.isoformat(),
        "category": e.category,
        "title": e.title,
        "module": e.module,
        "route": e.route or "",
        "start_at": e.start_at.strftime("%Y-%m-%d %H:%M") if e.start_at else None,
        "end_at": e.end_at.strftime("%Y-%m-%d %H:%M") if e.end_at else None,
        "time_note": e.time_note or "",
        "requirement_id": e.requirement_id,
        "requirement_no": req_no(e.requirement_id) if e.requirement_id else None,
        "updated_by": e.updated_by or "",
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


def _who(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", None) or "unknown"


@router.get("/entries", summary="條目清單（可依模組、月份、只看時間未知、只看未綁定需求篩選）")
def list_entries(
    module: Optional[str] = None,
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    unknown_only: bool = False,
    unbound_only: bool = False,
    db: Session = Depends(get_db),
    _=Depends(require_permission(VIEW)),
):
    q = db.query(DevLogEntry)
    if module:
        q = q.filter(DevLogEntry.module == module)
    if month:
        from datetime import date
        q = q.filter(DevLogEntry.entry_date >= date.fromisoformat(f"{month}-01"))
    if unknown_only:
        q = q.filter(DevLogEntry.start_at.is_(None), DevLogEntry.end_at.is_(None))
    if unbound_only:
        q = q.filter(DevLogEntry.requirement_id.is_(None))
    rows = q.order_by(DevLogEntry.entry_date.desc(), DevLogEntry.id).all()
    return {"total": len(rows), "items": [_to_dict(e) for e in rows]}


@router.get("/stats", summary="統計")
def get_stats(
    module: Optional[str] = None,
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    _=Depends(require_permission(VIEW)),
):
    return stats(db, module=module, month=month)


@router.post("/import", summary="匯入 CHANGELOG.md（只新增，不覆寫既有時間）")
async def import_changelog(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_permission(MANAGE)),
):
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="檔案必須是 UTF-8 編碼的 CHANGELOG.md")
    return import_entries(db, text, who=_who(user), now=twnow())


@router.post("/sync-git", summary="從 git 歷史同步 commit（每個 commit 一筆，只新增，不覆寫）")
def sync_git(
    db: Session = Depends(get_db),
    user=Depends(require_permission(MANAGE)),
):
    try:
        return sync_from_git(db, REPO_ROOT, now=twnow())
    except RuntimeError as ex:
        raise HTTPException(status_code=400, detail=str(ex))


class TimePatch(BaseModel):
    start_at: Optional[str] = None   # "YYYY-MM-DD HH:mm" 或 null
    end_at: Optional[str] = None
    time_note: Optional[str] = None
    requirement_id: Optional[int] = None   # null＝解除綁定（只有明確送出此欄位才會變更）


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"時間格式錯誤：{s}（需 YYYY-MM-DD HH:mm）")


@router.patch("/entries/{entry_id}", summary="編輯開始／結束時間、時間說明、需求綁定（只更新有送出的欄位）")
def patch_entry(
    entry_id: int,
    body: TimePatch,
    db: Session = Depends(get_db),
    user=Depends(require_permission(MANAGE)),
):
    e = db.query(DevLogEntry).filter_by(id=entry_id).first()
    if e is None:
        raise HTTPException(status_code=404, detail="找不到條目")
    sent = body.model_fields_set
    start = _parse_dt(body.start_at) if "start_at" in sent else e.start_at
    end = _parse_dt(body.end_at) if "end_at" in sent else e.end_at
    if start and end and end < start:
        raise HTTPException(status_code=400, detail="結束時間不可早於開始時間")
    if "start_at" in sent or "end_at" in sent:
        e.start_at, e.end_at = start, end
    if "time_note" in sent and body.time_note is not None:
        e.time_note = body.time_note
    if "requirement_id" in sent:
        if body.requirement_id is not None and db.query(Requirement.id).filter_by(id=body.requirement_id).first() is None:
            raise HTTPException(status_code=400, detail="指定的需求不存在")
        e.requirement_id = body.requirement_id
    e.updated_by = _who(user)
    e.updated_at = twnow()
    db.commit()
    return _to_dict(e)


# ── 需求管理（2026-11-20）─────────────────────────────────────────────

class RequirementIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    requester: Optional[str] = Field(None, max_length=120)
    module: Optional[str] = Field(None, max_length=120)
    status: str = "待評估"
    priority: str = "中"


class RequirementPatch(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    requester: Optional[str] = Field(None, max_length=120)
    module: Optional[str] = Field(None, max_length=120)
    status: Optional[str] = None
    priority: Optional[str] = None


def _check_enums(data: dict) -> None:
    if "status" in data and data["status"] not in REQ_STATUSES:
        raise HTTPException(status_code=400, detail=f"狀態必須是：{'、'.join(REQ_STATUSES)}")
    if "priority" in data and data["priority"] not in REQ_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"優先度必須是：{'、'.join(REQ_PRIORITIES)}")


def _clean(data: dict) -> dict:
    # 文字欄位去除前後空白；空字串視為未填
    out = {}
    for k, v in data.items():
        if isinstance(v, str):
            v = v.strip()
            if k in ("description", "requester", "module") and v == "":
                v = None if k != "module" else ""
        out[k] = v
    return out


@router.get("/requirements", summary="需求清單與匯整（變更數、涉及模組、工時；需求×模組矩陣）")
def list_requirements(
    db: Session = Depends(get_db),
    _=Depends(require_permission(VIEW)),
):
    return requirement_summary(db)


@router.post("/requirements", summary="新增需求（限管理者）")
def create_requirement(
    body: RequirementIn,
    db: Session = Depends(get_db),
    user=Depends(require_permission(MANAGE)),
):
    data = _clean(body.model_dump())
    _check_enums(data)
    r = Requirement(created_by=_who(user), created_at=twnow())
    apply_requirement_fields(r, data, _who(user), twnow())
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "req_no": req_no(r.id)}


@router.patch("/requirements/{requirement_id}", summary="編輯需求（限管理者）")
def patch_requirement(
    requirement_id: int,
    body: RequirementPatch,
    db: Session = Depends(get_db),
    user=Depends(require_permission(MANAGE)),
):
    r = db.query(Requirement).filter_by(id=requirement_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail="找不到需求")
    data = _clean(body.model_dump(exclude_unset=True))
    if "title" in data and not data["title"]:
        raise HTTPException(status_code=400, detail="標題不可為空")
    if "status" in data and data["status"] is None or "priority" in data and data["priority"] is None:
        raise HTTPException(status_code=400, detail="狀態與優先度不可為空")
    _check_enums(data)
    apply_requirement_fields(r, data, _who(user), twnow())
    db.commit()
    return {"id": r.id, "req_no": req_no(r.id)}


@router.post("/requirements/import-jira", summary="匯入 Jira 匯出的 CSV（只新增，以 Issue key 去重；限管理者）")
async def import_jira(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_permission(MANAGE)),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="請上傳 Jira 匯出的 .csv 檔案")
    raw = await file.read()
    try:
        return import_jira_csv(db, raw, who=_who(user), now=twnow())
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))
