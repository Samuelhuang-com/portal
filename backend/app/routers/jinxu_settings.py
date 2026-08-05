"""
金旭 PMS 分析 — 科目分類與門檻設定 API
Prefix: /api/v1/jinxu/settings     規格書：§12.6

科目分類存 DB 不寫死在程式碼（E7）——金旭可能新增科目，寫死會導致每次都要
改程式重新部署。管理員在此維護。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.time import twnow
from app.dependencies import get_current_user, require_permission
from app.models.jinxu_ledger import (
    GROUP_LABELS,
    SIDE_REVENUE,
    SIDE_SETTLEMENT,
    JinxuSubjectMap,
)
from app.models.jinxu_setting import JinxuAnalysisSetting
from app.models.user import User

router = APIRouter(dependencies=[Depends(get_current_user)])


class SubjectUpdate(BaseModel):
    subject_name: str | None = None
    side: str | None = Field(None, pattern="^(REVENUE|SETTLEMENT)$")
    group_code: str | None = None
    sort_order: int | None = None
    is_memo_only: int | None = Field(None, ge=0, le=1)
    is_active: int | None = Field(None, ge=0, le=1)


class ThresholdUpdate(BaseModel):
    setting_key: str
    setting_value: str


def _subject_dict(r: JinxuSubjectMap) -> dict:
    return {
        "subject_code": r.subject_code,
        "subject_name": r.subject_name,
        "side": r.side,
        "side_label": "收入" if r.side == SIDE_REVENUE else "抵充",
        "group_code": r.group_code,
        "group_label": GROUP_LABELS.get(r.group_code, r.group_code),
        "sort_order": r.sort_order,
        "is_memo_only": r.is_memo_only,
        "is_active": r.is_active,
        "updated_at": r.updated_at.isoformat(sep=" ", timespec="seconds") if r.updated_at else "",
    }


@router.get("/subjects", summary="科目分類對照表")
async def list_subjects(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("jinxu_view")),
):
    def _run():
        q = db.query(JinxuSubjectMap)
        if not include_inactive:
            q = q.filter(JinxuSubjectMap.is_active == 1)
        rows = q.order_by(JinxuSubjectMap.sort_order, JinxuSubjectMap.subject_code).all()
        return {
            "items": [_subject_dict(r) for r in rows],
            "group_options": [{"value": k, "label": v} for k, v in GROUP_LABELS.items()],
            "note": (
                "is_memo_only=1 的科目（轉帳／換房／弈夢空間）金額恆為 0，"
                "屬純記錄性分錄，一律排除於收入統計。"
            ),
        }

    return await run_in_threadpool(_run)


@router.put("/subjects/{subject_code}", summary="維護單一科目分類")
async def update_subject(
    subject_code: str,
    payload: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("jinxu_admin")),
):
    def _run():
        row = (
            db.query(JinxuSubjectMap)
            .filter(JinxuSubjectMap.subject_code == subject_code)
            .first()
        )
        if not row:
            return None
        data = payload.model_dump(exclude_none=True)
        for k, v in data.items():
            setattr(row, k, v)
        row.updated_at = twnow()
        row.updated_by_user_id = str(current_user.id)
        db.commit()
        db.refresh(row)
        return _subject_dict(row)

    out = await run_in_threadpool(_run)
    if out is None:
        raise HTTPException(404, f"科目 {subject_code} 不存在")
    return out


@router.get("/thresholds", summary="分析門檻")
async def list_thresholds(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("jinxu_view")),
):
    def _run():
        rows = (
            db.query(JinxuAnalysisSetting)
            .order_by(JinxuAnalysisSetting.setting_key)
            .all()
        )
        return {"items": [{
            "setting_key": r.setting_key,
            "setting_value": r.setting_value,
            "value_type": r.value_type,
            "description": r.description,
            "updated_at": r.updated_at.isoformat(sep=" ", timespec="seconds") if r.updated_at else "",
        } for r in rows]}

    return await run_in_threadpool(_run)


@router.put("/thresholds", summary="更新分析門檻")
async def update_threshold(
    payload: ThresholdUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("jinxu_admin")),
):
    def _run():
        row = (
            db.query(JinxuAnalysisSetting)
            .filter(JinxuAnalysisSetting.setting_key == payload.setting_key)
            .first()
        )
        if not row:
            return None
        row.setting_value = payload.setting_value
        row.updated_at = twnow()
        row.updated_by_user_id = str(current_user.id)
        db.commit()
        return {"setting_key": row.setting_key, "setting_value": row.setting_value}

    out = await run_in_threadpool(_run)
    if out is None:
        raise HTTPException(404, f"設定 {payload.setting_key} 不存在")
    return out
