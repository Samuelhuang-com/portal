"""
影音教學 Service Layer（模組主檔 + 單集影片）
影片與逐字稿檔案直接存於本機檔案系統，不經 Ragic 同步。
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.time import twnow
from app.models.tutorial_video import TutorialVideo
from app.models.tutorial_video_module import TutorialVideoModule
from app.schemas.tutorial_video import (
    TutorialVideoModuleCreate, TutorialVideoModuleUpdate, TutorialVideoUpdate,
)

# 檔案儲存目錄（backend 執行目錄下，與 memo_file / upload 慣例一致）
VIDEO_ROOT = Path("uploads/tutorial_videos")

ALLOWED_VIDEO_TYPES = {"video/mp4", "video/x-m4v", "video/quicktime"}
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500 MB／單支影片上限，超過請改用外部影音平台

VALID_CATEGORIES = {"hotel", "mall", "group"}


def _now():
    return twnow()


# ── 教學模組主檔 ──────────────────────────────────────────────────────────────

def list_modules(db: Session, category: Optional[str] = None) -> List[dict]:
    """回傳模組清單，附上各模組的影片數量（video_count）"""
    query = db.query(
        TutorialVideoModule,
        func.count(TutorialVideo.id).label("video_count"),
    ).outerjoin(TutorialVideo, TutorialVideo.module_id == TutorialVideoModule.id)
    if category:
        query = query.filter(TutorialVideoModule.category == category)
    query = query.group_by(TutorialVideoModule.id).order_by(
        TutorialVideoModule.category, TutorialVideoModule.sort_order,
    )
    results = []
    for module, video_count in query.all():
        results.append({
            "id": module.id,
            "category": module.category,
            "module_name": module.module_name,
            "module_route": module.module_route,
            "sort_order": module.sort_order,
            "video_count": video_count or 0,
            "created_at": module.created_at,
            "updated_at": module.updated_at,
        })
    return results


def get_module(module_id: str, db: Session) -> Optional[TutorialVideoModule]:
    return db.query(TutorialVideoModule).filter(TutorialVideoModule.id == module_id).first()


def create_module(payload: TutorialVideoModuleCreate, db: Session) -> TutorialVideoModule:
    max_order = (
        db.query(func.max(TutorialVideoModule.sort_order))
        .filter(TutorialVideoModule.category == payload.category)
        .scalar()
    )
    module = TutorialVideoModule(
        id=str(uuid.uuid4()),
        category=payload.category,
        module_name=payload.module_name,
        module_route=payload.module_route,
        sort_order=(max_order + 1) if max_order is not None else 0,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


def update_module(module_id: str, payload: TutorialVideoModuleUpdate, db: Session) -> tuple[bool, str]:
    module = get_module(module_id, db)
    if not module:
        return False, "not_found"
    for field in ("category", "module_name", "module_route"):
        value = getattr(payload, field)
        if value is not None:
            setattr(module, field, value)
    module.updated_at = _now()
    db.commit()
    return True, ""


def delete_module(module_id: str, db: Session) -> tuple[bool, str]:
    module = get_module(module_id, db)
    if not module:
        return False, "not_found"
    # 先清除該模組下所有影片的實體檔案，DB 列由 cascade 一併刪除
    for video in list(module.videos):
        _delete_video_files(video)
    db.delete(module)
    db.commit()
    return True, ""


def reorder_modules(category: str, ordered_ids: List[str], db: Session) -> None:
    for index, module_id in enumerate(ordered_ids):
        db.query(TutorialVideoModule).filter(
            TutorialVideoModule.id == module_id,
            TutorialVideoModule.category == category,
        ).update({"sort_order": index, "updated_at": _now()})
    db.commit()


# ── 單集影片 ──────────────────────────────────────────────────────────────────

def list_videos(db: Session, category: Optional[str] = None, module_id: Optional[str] = None) -> List[TutorialVideo]:
    query = db.query(TutorialVideo)
    if module_id:
        query = query.filter(TutorialVideo.module_id == module_id)
    if category:
        query = query.join(TutorialVideoModule).filter(TutorialVideoModule.category == category)
    return query.order_by(TutorialVideo.sort_order, TutorialVideo.episode).all()


def get_video(video_id: str, db: Session) -> Optional[TutorialVideo]:
    return db.query(TutorialVideo).filter(TutorialVideo.id == video_id).first()


def create_video(
    *,
    module_id: str,
    episode: str,
    title: str,
    description: str,
    sort_order: Optional[int],
    uploaded_by: str,
    video_file,           # starlette UploadFile
    script_file=None,     # starlette UploadFile | None
    db: Session,
) -> TutorialVideo:
    VIDEO_ROOT.mkdir(parents=True, exist_ok=True)

    video_content = video_file.file.read()
    video_suffix = Path(video_file.filename or "video.mp4").suffix or ".mp4"
    video_stored = f"{uuid.uuid4().hex}{video_suffix}"
    (VIDEO_ROOT / video_stored).write_bytes(video_content)

    script_stored = ""
    script_orig = ""
    if script_file is not None:
        script_content = script_file.file.read()
        script_suffix = Path(script_file.filename or "script.txt").suffix or ".txt"
        script_stored = f"{uuid.uuid4().hex}{script_suffix}"
        (VIDEO_ROOT / script_stored).write_bytes(script_content)
        script_orig = script_file.filename or script_stored

    if sort_order is None:
        max_order = (
            db.query(func.max(TutorialVideo.sort_order))
            .filter(TutorialVideo.module_id == module_id)
            .scalar()
        )
        sort_order = (max_order + 1) if max_order is not None else 0

    tv = TutorialVideo(
        id=str(uuid.uuid4()),
        module_id=module_id,
        episode=episode,
        title=title,
        description=description,
        video_stored_name=video_stored,
        video_orig_name=video_file.filename or video_stored,
        video_size_bytes=len(video_content),
        video_content_type=video_file.content_type or "video/mp4",
        script_stored_name=script_stored,
        script_orig_name=script_orig,
        sort_order=sort_order,
        uploaded_by=uploaded_by,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(tv)
    db.commit()
    db.refresh(tv)
    return tv


def update_video(video_id: str, payload: TutorialVideoUpdate, db: Session) -> tuple[bool, str]:
    tv = get_video(video_id, db)
    if not tv:
        return False, "not_found"
    for field in ("module_id", "episode", "title", "description", "sort_order"):
        value = getattr(payload, field)
        if value is not None:
            setattr(tv, field, value)
    tv.updated_at = _now()
    db.commit()
    return True, ""


def reorder_videos(module_id: str, ordered_ids: List[str], db: Session) -> None:
    for index, video_id in enumerate(ordered_ids):
        db.query(TutorialVideo).filter(
            TutorialVideo.id == video_id,
            TutorialVideo.module_id == module_id,
        ).update({"sort_order": index, "updated_at": _now()})
    db.commit()


def _delete_video_files(tv: TutorialVideo) -> None:
    for stored in (tv.video_stored_name, tv.script_stored_name):
        if stored:
            path = VIDEO_ROOT / stored
            if path.exists():
                path.unlink()


def delete_video(video_id: str, db: Session) -> tuple[bool, str]:
    tv = get_video(video_id, db)
    if not tv:
        return False, "not_found"
    _delete_video_files(tv)
    db.delete(tv)
    db.commit()
    return True, ""


def get_video_file_path(tv: TutorialVideo) -> Optional[Path]:
    if not tv.video_stored_name:
        return None
    path = VIDEO_ROOT / tv.video_stored_name
    return path if path.exists() else None


def get_script_file_path(tv: TutorialVideo) -> Optional[Path]:
    if not tv.script_stored_name:
        return None
    path = VIDEO_ROOT / tv.script_stored_name
    return path if path.exists() else None
