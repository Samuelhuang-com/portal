"""
KPO 稽核（稽核檢查子模組）— FastAPI Router
Prefix: /api/v1/audit-check/kpo

中文名稱：KPO 稽核 ／ 英文名稱：Audit KPO
前端路由：/audit-check/kpo/*
對應 Excel：財#1稽核系統建構（整合／2026.11執行／各部門 Sheet）
規格：docs/SPEC_audit_kpo.md

權限（沿用稽核檢查既有三個 key，不新增 key）
    audit_check_view   檢視期別與小計
    audit_check_edit   建立期別、選定稽核項目、填寫判定與備註
    audit_check_admin  部門／稽核項目主檔維護、刪除期別

⚠️ 所有端點一律掛 require_permission（CLAUDE.md §11.6）。
⚠️ 本模組非 Ragic 同步模組，sync_tool.py / RagicConnections.tsx 一律不動。
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_permission
from app.models.audit_kpo import (
    AuditKpoDept, AuditKpoItem, AuditKpoPeriod, AuditKpoPeriodItem,
)
from app.models.reference_data import RefDepartment
from app.models.user import User
from app.schemas.audit_kpo import (
    KpoDeptCreate, KpoDeptOut, KpoDeptUpdate, KpoItemCreate, KpoItemOut,
    KpoDeptOrderUpdate, KpoItemUpdate, KpoLineOrderUpdate, KpoLineUpdate, KpoPeriodCreate, KpoPeriodDetail,
    KpoPeriodSummary, KpoPeriodUpdate, KpoSelectionUpdate,
)
from app.services import audit_kpo_service as svc
from app.services.audit_check_html import sanitize_html

router = APIRouter()

VIEW = "audit_check_view"
EDIT = "audit_check_edit"
ADMIN = "audit_check_admin"


def _404(detail: str = "查無資料") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _409(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _get_period(db: Session, period_id: int) -> AuditKpoPeriod:
    p = db.get(AuditKpoPeriod, period_id)
    if p is None:
        raise _404("查無此稽核期別")
    return p


# ════════════════════════════════════════════════════════════════════════════
# 部門
# ════════════════════════════════════════════════════════════════════════════
def _dept_out(db: Session, d: AuditKpoDept) -> KpoDeptOut:
    row = (
        db.query(
            func.count(AuditKpoItem.id),
            func.coalesce(func.sum(AuditKpoItem.score), 0),
        )
        .filter(AuditKpoItem.department_id == d.id, AuditKpoItem.is_active.is_(True))
        .one()
    )
    key_cnt = (
        db.query(func.count(AuditKpoItem.id))
        .filter(AuditKpoItem.department_id == d.id, AuditKpoItem.is_active.is_(True),
                AuditKpoItem.is_key.is_(True))
        .scalar()
    )
    return KpoDeptOut(
        id=d.id, name=d.name, display_name=d.display_name,
        company_id=d.company_id, company_name=d.company.name if d.company else None,
        ref_department_id=d.ref_department_id, source_title=d.source_title, sort_order=d.sort_order,
        is_active=d.is_active, item_count=int(row[0]), key_count=int(key_cnt or 0),
        total_score=int(row[1] or 0),
    )


@router.get("/departments", response_model=List[KpoDeptOut])
def list_departments(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    svc.seed_kpo_master(db)
    depts = db.query(AuditKpoDept).order_by(AuditKpoDept.sort_order, AuditKpoDept.id).all()
    return [_dept_out(db, d) for d in depts]


def _resolve_ref_department(db: Session, company_id: int, ref_department_id: int) -> RefDepartment:
    """部門一律取自 settings/company-departments（2026-10-10 裁示，比照財#3 稽核檢查）：
    必須存在、屬於所選公司別、且未停用。"""
    rd = db.get(RefDepartment, ref_department_id)
    if rd is None:
        raise HTTPException(status_code=400, detail="查無此部門")
    if rd.company_id != company_id:
        raise HTTPException(status_code=400, detail=f"{rd.name} 不屬於所選的公司別")
    if not rd.is_active:
        raise HTTPException(status_code=400, detail=f"{rd.name} 已停用")
    return rd


def _assert_dept_unique(db: Session, company_id: Optional[int], name: str, exclude_id: Optional[int] = None) -> None:
    q = db.query(AuditKpoDept.id).filter(AuditKpoDept.name == name)
    q = q.filter(AuditKpoDept.company_id.is_(None)) if company_id is None else q.filter(AuditKpoDept.company_id == company_id)
    if exclude_id is not None:
        q = q.filter(AuditKpoDept.id != exclude_id)
    if q.first():
        raise _409(f"部門「{name}」已存在")


@router.post("/departments", response_model=KpoDeptOut, status_code=201)
def create_department(
    body: KpoDeptCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(ADMIN)),
):
    rd = _resolve_ref_department(db, body.company_id, body.ref_department_id)
    _assert_dept_unique(db, body.company_id, rd.name)
    max_order = db.query(func.coalesce(func.max(AuditKpoDept.sort_order), 0)).scalar()
    d = AuditKpoDept(
        name=rd.name, company_id=body.company_id, ref_department_id=rd.id,
        source_title=body.source_title,
        sort_order=body.sort_order if body.sort_order is not None else int(max_order) + 10,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return _dept_out(db, d)


@router.put("/departments/{dept_id}", response_model=KpoDeptOut)
def update_department(
    dept_id: int,
    body: KpoDeptUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(ADMIN)),
):
    d = db.get(AuditKpoDept, dept_id)
    if d is None:
        raise _404("查無此部門")
    data = body.model_dump(exclude_unset=True)
    if data.get("ref_department_id") is not None:
        company_id = data.get("company_id") or d.company_id
        if company_id is None:
            raise HTTPException(status_code=400, detail="請先選擇公司別")
        rd = _resolve_ref_department(db, company_id, data["ref_department_id"])
        _assert_dept_unique(db, company_id, rd.name, exclude_id=dept_id)
        d.company_id, d.ref_department_id, d.name = company_id, rd.id, rd.name
    elif "name" in data:
        if d.ref_department_id is not None:
            raise HTTPException(status_code=400, detail="已連結部門主檔，名稱由 settings/company-departments 決定；請改選部門")
        name = data["name"].strip()
        _assert_dept_unique(db, d.company_id, name, exclude_id=dept_id)
        d.name = name
    for k in ("source_title", "sort_order", "is_active"):
        if k in data:
            setattr(d, k, data[k])
    db.commit()
    db.refresh(d)
    return _dept_out(db, d)


# ════════════════════════════════════════════════════════════════════════════
# 稽核項目主檔
# ════════════════════════════════════════════════════════════════════════════
def _item_out(it: AuditKpoItem, in_use: bool) -> KpoItemOut:
    return KpoItemOut(
        id=it.id, department_id=it.department_id, item_no=it.item_no, is_key=it.is_key,
        name=it.name, score=int(it.score or 0), method=it.method,
        sort_order=it.sort_order, is_active=it.is_active, in_use=in_use,
    )


@router.get("/items", response_model=List[KpoItemOut])
def list_items(
    department_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    svc.seed_kpo_master(db)
    q = db.query(AuditKpoItem)
    if department_id is not None:
        q = q.filter(AuditKpoItem.department_id == department_id)
    items = q.order_by(AuditKpoItem.department_id, AuditKpoItem.sort_order, AuditKpoItem.id).all()
    used = {
        r[0] for r in db.query(AuditKpoPeriodItem.source_item_id)
        .filter(AuditKpoPeriodItem.source_item_id.isnot(None)).distinct().all()
    }
    return [_item_out(it, it.id in used) for it in items]


@router.post("/items", response_model=KpoItemOut, status_code=201)
def create_item(
    body: KpoItemCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(ADMIN)),
):
    if db.get(AuditKpoDept, body.department_id) is None:
        raise _404("查無此部門")
    max_order = db.query(func.coalesce(func.max(AuditKpoItem.sort_order), 0)).filter(
        AuditKpoItem.department_id == body.department_id).scalar()
    max_no = db.query(func.coalesce(func.max(AuditKpoItem.item_no), 0)).filter(
        AuditKpoItem.department_id == body.department_id).scalar()
    it = AuditKpoItem(
        department_id=body.department_id,
        item_no=body.item_no if body.item_no is not None else int(max_no) + 1,
        is_key=body.is_key, name=body.name.strip(),
        score=body.score if body.score is not None else svc.default_score(body.is_key),
        method=sanitize_html(body.method) or None, sort_order=int(max_order) + 10,
    )
    db.add(it)
    db.commit()
    db.refresh(it)
    return _item_out(it, False)


@router.put("/items/{item_id}", response_model=KpoItemOut)
def update_item(
    item_id: int,
    body: KpoItemUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(ADMIN)),
):
    it = db.get(AuditKpoItem, item_id)
    if it is None:
        raise _404("查無此稽核項目")
    data = body.model_dump(exclude_unset=True)
    if "name" in data:
        data["name"] = data["name"].strip()
    if "method" in data:
        data["method"] = sanitize_html(data["method"]) or None   # 備註為 Web 編輯器 HTML，白名單清理
    for k, v in data.items():
        setattr(it, k, v)
    db.commit()
    db.refresh(it)
    in_use = db.query(AuditKpoPeriodItem.id).filter(
        AuditKpoPeriodItem.source_item_id == it.id).first() is not None
    return _item_out(it, in_use)


@router.delete("/items/{item_id}", status_code=204)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(ADMIN)),
):
    """刪除主檔項目。已選定於歷史期別的快照保留（source_item_id 轉 NULL），不受影響。"""
    it = db.get(AuditKpoItem, item_id)
    if it is None:
        raise _404("查無此稽核項目")
    db.query(AuditKpoPeriodItem).filter(
        AuditKpoPeriodItem.source_item_id == item_id
    ).update({AuditKpoPeriodItem.source_item_id: None}, synchronize_session=False)
    db.delete(it)
    db.commit()


# ════════════════════════════════════════════════════════════════════════════
# 期別
# ════════════════════════════════════════════════════════════════════════════
@router.get("/periods", response_model=List[KpoPeriodSummary])
def list_periods(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    periods = db.query(AuditKpoPeriod).order_by(
        AuditKpoPeriod.period.desc(), AuditKpoPeriod.id.desc()).all()
    return [svc.build_period_summary(p) for p in periods]


@router.post("/periods", response_model=KpoPeriodDetail, status_code=201)
def create_period(
    body: KpoPeriodCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT)),
):
    p = AuditKpoPeriod(
        period=body.period, title=body.title.strip() or "財#1稽核系統建構",
        note=body.note, created_by=str(user.id),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return svc.build_period_detail(db, p)


@router.get("/periods/{period_id}", response_model=KpoPeriodDetail)
def get_period(
    period_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return svc.build_period_detail(db, _get_period(db, period_id))


@router.put("/periods/{period_id}", response_model=KpoPeriodDetail)
def update_period(
    period_id: int,
    body: KpoPeriodUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(EDIT)),
):
    p = _get_period(db, period_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        if k in ("period", "title") and not v:
            continue
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return svc.build_period_detail(db, p)


@router.delete("/periods/{period_id}", status_code=204)
def delete_period(
    period_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(ADMIN)),
):
    p = _get_period(db, period_id)
    db.delete(p)
    db.commit()


@router.put("/periods/{period_id}/selection", response_model=KpoPeriodDetail)
def update_selection(
    period_id: int,
    body: KpoSelectionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(EDIT)),
):
    """
    整組替換某部門在本期選定的項目：
      - 新勾選的 → 由主檔複製一份快照（含 ★、分數、備註）
      - 取消勾選的 → 移除該列（其判定與備註一併消失）
      - 原本就選定的 → 保留不動（本期已編輯的內容與判定不會被主檔覆蓋）
    """
    p = _get_period(db, period_id)
    if db.get(AuditKpoDept, body.department_id) is None:
        raise _404("查無此部門")
    wanted = list(dict.fromkeys(body.item_ids))
    masters = {
        it.id: it for it in db.query(AuditKpoItem).filter(
            AuditKpoItem.department_id == body.department_id,
            AuditKpoItem.id.in_(wanted or [0]),
        ).all()
    }
    bad = [i for i in wanted if i not in masters]
    if bad:
        raise HTTPException(status_code=400, detail=f"稽核項目不屬於該部門或不存在：{bad}")

    existing_lines = [ln for ln in p.lines if ln.department_id == body.department_id]
    next_order = max([ln.sort_order or 0 for ln in existing_lines], default=0)
    existing = {
        ln.source_item_id: ln for ln in p.lines
        if ln.department_id == body.department_id and ln.source_item_id is not None
    }
    for sid, ln in list(existing.items()):
        if sid not in masters:
            p.lines.remove(ln)
    # 新勾選的項目接在該部門現有順序之後（依主檔順序），不會插進使用者調整過的順序中間
    for sid in sorted((i for i in wanted if i not in existing), key=lambda i: (masters[i].sort_order, i)):
        m = masters[sid]
        next_order += 10
        p.lines.append(AuditKpoPeriodItem(
            department_id=body.department_id, source_item_id=m.id,
            item_no=m.item_no, is_key=m.is_key, name=m.name, score=m.score,
            method=m.method, sort_order=next_order,
        ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _409("選定項目重複，請重新整理後再試")
    db.refresh(p)
    return svc.build_period_detail(db, p)


@router.put("/periods/{period_id}/dept-order", response_model=KpoPeriodDetail)
def update_dept_order(
    period_id: int,
    body: KpoDeptOrderUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(EDIT)),
):
    """儲存本期部門顯示順序（只影響本期，不動部門主檔順序）。"""
    p = _get_period(db, period_id)
    ids = list(dict.fromkeys(body.department_ids))
    valid = {r[0] for r in db.query(AuditKpoDept.id).filter(AuditKpoDept.id.in_(ids or [0])).all()}
    bad = [i for i in ids if i not in valid]
    if bad:
        raise HTTPException(status_code=400, detail=f"查無部門：{bad}")
    p.dept_order = ",".join(str(i) for i in ids) or None
    db.commit()
    db.refresh(p)
    return svc.build_period_detail(db, p)


@router.put("/periods/{period_id}/lines-order", response_model=KpoPeriodDetail)
def update_lines_order(
    period_id: int,
    body: KpoLineOrderUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(EDIT)),
):
    """儲存某部門在本期的項目順序（只影響本期這個部門）。"""
    p = _get_period(db, period_id)
    mine = {ln.id: ln for ln in p.lines if ln.department_id == body.department_id}
    ids = list(dict.fromkeys(body.line_ids))
    bad = [i for i in ids if i not in mine]
    if bad:
        raise HTTPException(status_code=400, detail=f"選定項目不屬於本期該部門：{bad}")
    rest = sorted((ln for i, ln in mine.items() if i not in ids),
                  key=lambda x: (x.sort_order or 0, x.id))
    for idx, ln in enumerate([mine[i] for i in ids] + rest):
        ln.sort_order = (idx + 1) * 10
    db.commit()
    db.refresh(p)
    return svc.build_period_detail(db, p)


@router.put("/periods/{period_id}/lines/{line_id}", response_model=KpoPeriodDetail)
def update_line(
    period_id: int,
    line_id: int,
    body: KpoLineUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(EDIT)),
):
    """編輯本期選定項目的內容／判定／備註（只影響本期這一列，不動主檔）。"""
    p = _get_period(db, period_id)
    ln = db.get(AuditKpoPeriodItem, line_id)
    if ln is None or ln.period_id != p.id:
        raise _404("查無此選定項目")
    data = body.model_dump(exclude_unset=True)
    if "result" in data:
        ln.result = data.pop("result") or None
    if "name" in data:
        data["name"] = data["name"].strip()
    if "method" in data:
        data["method"] = sanitize_html(data["method"]) or None   # 備註為 Web 編輯器 HTML，白名單清理
    for k, v in data.items():
        setattr(ln, k, v)
    db.commit()
    db.refresh(p)
    return svc.build_period_detail(db, p)
