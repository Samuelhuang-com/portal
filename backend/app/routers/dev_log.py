"""
開發統計 API（/api/v1/dev-log）
- view：查看統計與條目；manage：匯入 CHANGELOG、編輯開始／結束時間
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.time import twnow
from app.dependencies import require_permission
from app.models.dev_log import DevLogEntry
from app.services.dev_log_service import REPO_ROOT, import_entries, stats, sync_from_git

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
        "updated_by": e.updated_by or "",
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


@router.get("/entries", summary="條目清單（可依模組、月份、只看時間未知篩選）")
def list_entries(
    module: Optional[str] = None,
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    unknown_only: bool = False,
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
    who = getattr(user, "email", None) or getattr(user, "username", None) or "unknown"
    return import_entries(db, text, who=who, now=twnow())


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


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"時間格式錯誤：{s}（需 YYYY-MM-DD HH:mm）")


@router.patch("/entries/{entry_id}", summary="編輯開始／結束時間")
def patch_entry(
    entry_id: int,
    body: TimePatch,
    db: Session = Depends(get_db),
    user=Depends(require_permission(MANAGE)),
):
    e = db.query(DevLogEntry).filter_by(id=entry_id).first()
    if e is None:
        raise HTTPException(status_code=404, detail="找不到條目")
    start = _parse_dt(body.start_at)
    end = _parse_dt(body.end_at)
    if start and end and end < start:
        raise HTTPException(status_code=400, detail="結束時間不可早於開始時間")
    e.start_at, e.end_at = start, end
    if body.time_note is not None:
        e.time_note = body.time_note
    e.updated_by = getattr(user, "email", None) or getattr(user, "username", None) or "unknown"
    e.updated_at = twnow()
    db.commit()
    return _to_dict(e)
