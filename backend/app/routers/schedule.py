"""
班表模組 Router
所有路由前綴：/api/v1/schedule

端點總覽：
  班表主檔：  GET/DELETE /                         - 列表（含年月篩選）
             GET/DELETE /{id}                     - 單筆
  班表明細：  GET        /{id}/details             - 取得表格式資料
             POST       /{id}/details             - 新增單筆明細
             PUT        /{id}/details/{detail_id} - 編輯單筆明細
             DELETE     /{id}/details/{detail_id} - 軟刪除明細
  Excel匯入：POST       /import                   - 上傳 Excel
             GET        /import-logs              - 匯入紀錄列表
  統計：      GET        /stats                    - 月統計
  部門管理：  CRUD       /departments
  人員管理：  CRUD       /staff
  班別管理：  CRUD       /shifts
"""
import uuid
from datetime import datetime, date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.schedule import (
    Department, StaffMember, ShiftType,
    Schedule, ScheduleDetail, ScheduleImportLog,
)
from app.services.schedule_import_service import import_excel
from app.services.schedule_service import get_schedule_table, get_monthly_stats

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# Pydantic Schemas（輕量內嵌，不另建 schemas 檔）
# ─────────────────────────────────────────────────────────────

class DeptIn(BaseModel):
    name: str
    remark: str = ""
    sort_order: int = 0
    is_active: bool = True

class DeptOut(BaseModel):
    id: str
    name: str
    remark: str
    sort_order: int
    is_active: bool
    class Config:
        from_attributes = True


class StaffIn(BaseModel):
    name: str
    source_name: str = ""
    staff_code: str = ""
    department_id: str | None = None
    employment_type: str = "正職"
    remark: str = ""
    is_active: bool = True

class StaffOut(BaseModel):
    id: str
    name: str
    source_name: str
    staff_code: str
    department_id: str | None
    department_name: str
    employment_type: str
    remark: str
    is_active: bool
    class Config:
        from_attributes = True


class ShiftIn(BaseModel):
    code: str
    name: str
    start_time: str = ""
    end_time: str = ""
    work_minutes: int = 480
    is_overnight: bool = False
    color: str = "#6b7280"
    is_active: bool = True

class ShiftOut(BaseModel):
    id: str
    code: str
    name: str
    start_time: str
    end_time: str
    work_minutes: int
    is_overnight: bool
    color: str
    is_active: bool
    class Config:
        from_attributes = True


class DetailEditIn(BaseModel):
    shift_code: str
    remark: str = ""

class DetailAddIn(BaseModel):
    work_date: date
    staff_id: str
    shift_code: str
    remark: str = ""


# ─────────────────────────────────────────────────────────────
# 輔助：寫 AuditLog
# ─────────────────────────────────────────────────────────────
def _audit(
    db: Session,
    user: User,
    action: str,
    resource_type: str,
    resource_id: str,
    extra: dict | None = None,
) -> None:
    db.add(AuditLog(
        user_id=user.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        extra=extra or {},
    ))


# ─────────────────────────────────────────────────────────────
# 部門管理
# ─────────────────────────────────────────────────────────────

@router.get("/departments", summary="部門列表")
def list_departments(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("schedule_view")),
):
    rows = (
        db.query(Department)
        .filter(Department.is_deleted == False)
        .order_by(Department.sort_order, Department.name)
        .all()
    )
    return [DeptOut.model_validate(r) for r in rows]


@router.post("/departments", summary="新增部門", status_code=201)
def create_department(
    body: DeptIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schedule_admin")),
):
    exist = db.query(Department).filter(
        Department.name == body.name, Department.is_deleted == False
    ).first()
    if exist:
        raise HTTPException(status_code=400, detail=f"部門「{body.name}」已存在")
    dept = Department(**body.model_dump())
    db.add(dept)
    db.flush()
    _audit(db, current_user, "create", "department", dept.id, {"name": dept.name})
    db.commit()
    return DeptOut.model_validate(dept)


@router.put("/departments/{dept_id}", summary="編輯部門")
def update_department(
    dept_id: str,
    body: DeptIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schedule_admin")),
):
    dept = db.query(Department).filter(Department.id == dept_id, Department.is_deleted == False).first()
    if not dept:
        raise HTTPException(status_code=404, detail="部門不存在")
    for k, v in body.model_dump().items():
        setattr(dept, k, v)
    _audit(db, current_user, "update", "department", dept_id, body.model_dump())
    db.commit()
    return DeptOut.model_validate(dept)


@router.delete("/departments/{dept_id}", summary="刪除部門（軟刪除）")
def delete_department(
    dept_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schedule_admin")),
):
    dept = db.query(Department).filter(Department.id == dept_id, Department.is_deleted == False).first()
    if not dept:
        raise HTTPException(status_code=404, detail="部門不存在")
    dept.is_deleted = True
    _audit(db, current_user, "delete", "department", dept_id)
    db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────
# 人員管理
# ─────────────────────────────────────────────────────────────

@router.get("/staff", summary="人員列表")
def list_staff(
    department_id: str | None = Query(None),
    employment_type: str | None = Query(None),
    is_active: bool | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("schedule_view")),
):
    q = db.query(StaffMember).filter(StaffMember.is_deleted == False)
    if department_id:
        q = q.filter(StaffMember.department_id == department_id)
    if employment_type:
        q = q.filter(StaffMember.employment_type == employment_type)
    if is_active is not None:
        q = q.filter(StaffMember.is_active == is_active)
    rows = q.order_by(StaffMember.name).all()
    return [StaffOut.model_validate(r) for r in rows]


@router.post("/staff", summary="新增人員", status_code=201)
def create_staff(
    body: StaffIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schedule_admin")),
):
    # 更新 department_name 快照
    dept_name = ""
    if body.department_id:
        dept = db.query(Department).filter(Department.id == body.department_id).first()
        dept_name = dept.name if dept else ""

    staff = StaffMember(
        **{k: v for k, v in body.model_dump().items()},
        department_name=dept_name,
        source_name=body.source_name or body.name,
    )
    db.add(staff)
    db.flush()
    _audit(db, current_user, "create", "staff_member", staff.id, {"name": staff.name})
    db.commit()
    return StaffOut.model_validate(staff)


@router.put("/staff/{staff_id}", summary="編輯人員")
def update_staff(
    staff_id: str,
    body: StaffIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schedule_admin")),
):
    staff = db.query(StaffMember).filter(StaffMember.id == staff_id, StaffMember.is_deleted == False).first()
    if not staff:
        raise HTTPException(status_code=404, detail="人員不存在")

    dept_name = ""
    if body.department_id:
        dept = db.query(Department).filter(Department.id == body.department_id).first()
        dept_name = dept.name if dept else ""

    old_name = staff.name
    for k, v in body.model_dump().items():
        setattr(staff, k, v)
    staff.department_name = dept_name
    _audit(db, current_user, "update", "staff_member", staff_id,
           {"old_name": old_name, "new_name": body.name})
    db.commit()
    return StaffOut.model_validate(staff)


@router.delete("/staff/{staff_id}", summary="停用人員（軟刪除）")
def delete_staff(
    staff_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schedule_admin")),
):
    staff = db.query(StaffMember).filter(StaffMember.id == staff_id, StaffMember.is_deleted == False).first()
    if not staff:
        raise HTTPException(status_code=404, detail="人員不存在")
    staff.is_deleted = True
    staff.is_active = False
    _audit(db, current_user, "delete", "staff_member", staff_id)
    db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────
# 班別管理
# ─────────────────────────────────────────────────────────────

@router.get("/shifts", summary="班別列表")
def list_shifts(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("schedule_view")),
):
    rows = (
        db.query(ShiftType)
        .filter(ShiftType.is_deleted == False)
        .order_by(ShiftType.code)
        .all()
    )
    return [ShiftOut.model_validate(r) for r in rows]


@router.post("/shifts", summary="新增班別", status_code=201)
def create_shift(
    body: ShiftIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schedule_admin")),
):
    exist = db.query(ShiftType).filter(
        ShiftType.code == body.code, ShiftType.is_deleted == False
    ).first()
    if exist:
        raise HTTPException(status_code=400, detail=f"班別代碼「{body.code}」已存在")
    shift = ShiftType(**body.model_dump())
    db.add(shift)
    db.flush()
    _audit(db, current_user, "create", "shift_type", shift.id, {"code": shift.code})
    db.commit()
    return ShiftOut.model_validate(shift)


@router.put("/shifts/{shift_id}", summary="編輯班別")
def update_shift(
    shift_id: str,
    body: ShiftIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schedule_admin")),
):
    shift = db.query(ShiftType).filter(ShiftType.id == shift_id, ShiftType.is_deleted == False).first()
    if not shift:
        raise HTTPException(status_code=404, detail="班別不存在")
    old_code = shift.code
    for k, v in body.model_dump().items():
        setattr(shift, k, v)
    _audit(db, current_user, "update", "shift_type", shift_id,
           {"old_code": old_code, "new_code": body.code})
    db.commit()
    return ShiftOut.model_validate(shift)


@router.delete("/shifts/{shift_id}", summary="停用班別（軟刪除）")
def delete_shift(
    shift_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schedule_admin")),
):
    shift = db.query(ShiftType).filter(ShiftType.id == shift_id, ShiftType.is_deleted == False).first()
    if not shift:
        raise HTTPException(status_code=404, detail="班別不存在")
    shift.is_deleted = True
    shift.is_active = False
    _audit(db, current_user, "delete", "shift_type", shift_id)
    db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────
# Excel 匯入
# ─────────────────────────────────────────────────────────────

@router.post("/import", summary="匯入 Excel 班表")
async def import_schedule(
    file: UploadFile = File(...),
    override_year: int | None = Form(None),
    override_month: int | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schedule_manage")),
):
    """
    上傳 .xlsx 班表檔案，自動解析並寫入資料庫。
    - override_year / override_month：手動指定年月（fallback UI 用）
    - 同年月已存在時回傳 already_exists=True，不寫入
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="僅支援 .xlsx / .xls 格式")

    content = await file.read()
    result = import_excel(
        db=db,
        file_content=content,
        file_name=file.filename,
        override_year=override_year,
        override_month=override_month,
    )

    if result.get("schedule_id"):
        _audit(db, current_user, "import", "schedule", result["schedule_id"],
               {"file": file.filename, "year": result.get("schedule_year"),
                "month": result.get("schedule_month")})
        db.commit()

    return result


@router.get("/import-logs", summary="匯入紀錄列表")
def list_import_logs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("schedule_manage")),
):
    rows = (
        db.query(ScheduleImportLog)
        .order_by(ScheduleImportLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "import_batch_id": r.import_batch_id,
            "file_name": r.file_name,
            "sheet_name": r.sheet_name,
            "schedule_year": r.schedule_year,
            "schedule_month": r.schedule_month,
            "total_details": r.total_details,
            "success_count": r.success_count,
            "warning_count": r.warning_count,
            "error_count": r.error_count,
            "unknown_shift_codes": r.unknown_shift_codes,
            "new_staff_names": r.new_staff_names,
            "message": r.message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────
# 班表主檔
# ─────────────────────────────────────────────────────────────

@router.get("/", summary="班表列表")
def list_schedules(
    year: int | None = Query(None),
    month: int | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("schedule_view")),
):
    q = db.query(Schedule).filter(Schedule.is_deleted == False)
    if year:
        q = q.filter(Schedule.schedule_year == year)
    if month:
        q = q.filter(Schedule.schedule_month == month)
    rows = q.order_by(Schedule.schedule_year.desc(), Schedule.schedule_month.desc()).all()
    return [
        {
            "id": r.id,
            "schedule_year": r.schedule_year,
            "schedule_month": r.schedule_month,
            "title": r.title,
            "source_file_name": r.source_file_name,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.delete("/{schedule_id}", summary="刪除班表（軟刪除）")
def delete_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schedule_admin")),
):
    sch = db.query(Schedule).filter(Schedule.id == schedule_id, Schedule.is_deleted == False).first()
    if not sch:
        raise HTTPException(status_code=404, detail="班表不存在")
    # 同時軟刪除所有明細
    db.query(ScheduleDetail).filter(ScheduleDetail.schedule_id == schedule_id).update(
        {"is_deleted": True}
    )
    sch.is_deleted = True
    _audit(db, current_user, "delete", "schedule", schedule_id,
           {"year": sch.schedule_year, "month": sch.schedule_month})
    db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────
# 班表明細（表格式資料）
# ─────────────────────────────────────────────────────────────

@router.get("/{schedule_id}/details", summary="取得表格式班表資料")
def get_details(
    schedule_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("schedule_view")),
):
    sch = db.query(Schedule).filter(Schedule.id == schedule_id, Schedule.is_deleted == False).first()
    if not sch:
        raise HTTPException(status_code=404, detail="班表不存在")
    return get_schedule_table(db, sch.schedule_year, sch.schedule_month)


@router.post("/{schedule_id}/details", summary="新增單筆班表明細", status_code=201)
def add_detail(
    schedule_id: str,
    body: DetailAddIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schedule_manage")),
):
    sch = db.query(Schedule).filter(Schedule.id == schedule_id, Schedule.is_deleted == False).first()
    if not sch:
        raise HTTPException(status_code=404, detail="班表不存在")

    staff = db.query(StaffMember).filter(StaffMember.id == body.staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="人員不存在")

    shift = db.query(ShiftType).filter(
        ShiftType.code == body.shift_code, ShiftType.is_deleted == False
    ).first()

    detail = ScheduleDetail(
        schedule_id=schedule_id,
        work_date=body.work_date,
        staff_id=body.staff_id,
        staff_name=staff.source_name or staff.name,
        shift_code=body.shift_code,
        shift_type_id=shift.id if shift else None,
        start_time=shift.start_time if shift else "",
        end_time=shift.end_time if shift else "",
        work_minutes=shift.work_minutes if shift else 0,
        remark=body.remark,
    )
    db.add(detail)
    db.flush()
    _audit(db, current_user, "create", "schedule_detail", detail.id,
           {"staff": staff.name, "date": str(body.work_date), "shift": body.shift_code})
    db.commit()
    return {"id": detail.id, "ok": True}


@router.put("/{schedule_id}/details/{detail_id}", summary="編輯單筆班表明細")
def edit_detail(
    schedule_id: str,
    detail_id: str,
    body: DetailEditIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schedule_manage")),
):
    detail = db.query(ScheduleDetail).filter(
        ScheduleDetail.id == detail_id,
        ScheduleDetail.schedule_id == schedule_id,
        ScheduleDetail.is_deleted == False,
    ).first()
    if not detail:
        raise HTTPException(status_code=404, detail="明細不存在")

    old_shift = detail.shift_code
    shift = db.query(ShiftType).filter(
        ShiftType.code == body.shift_code, ShiftType.is_deleted == False
    ).first()

    detail.shift_code = body.shift_code
    detail.shift_type_id = shift.id if shift else None
    detail.start_time = shift.start_time if shift else ""
    detail.end_time = shift.end_time if shift else ""
    detail.work_minutes = shift.work_minutes if shift else 0
    detail.remark = body.remark

    _audit(db, current_user, "update", "schedule_detail", detail_id,
           {"staff": detail.staff_name, "date": str(detail.work_date),
            "old_shift": old_shift, "new_shift": body.shift_code})
    db.commit()
    return {"ok": True}


@router.delete("/{schedule_id}/details/{detail_id}", summary="刪除單筆班表明細（軟刪除）")
def delete_detail(
    schedule_id: str,
    detail_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("schedule_manage")),
):
    detail = db.query(ScheduleDetail).filter(
        ScheduleDetail.id == detail_id,
        ScheduleDetail.schedule_id == schedule_id,
        ScheduleDetail.is_deleted == False,
    ).first()
    if not detail:
        raise HTTPException(status_code=404, detail="明細不存在")

    detail.is_deleted = True
    _audit(db, current_user, "delete", "schedule_detail", detail_id,
           {"staff": detail.staff_name, "date": str(detail.work_date),
            "shift": detail.shift_code})
    db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────
# 統計
# ─────────────────────────────────────────────────────────────

@router.get("/stats", summary="月統計摘要")
def get_stats(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("schedule_view")),
):
    return get_monthly_stats(db, year, month)


# ─────────────────────────────────────────────────────────────
# 明細列表（單純列表模式，用於明細頁）
# ─────────────────────────────────────────────────────────────

@router.get("/details/list", summary="明細列表（可篩選）")
def list_details(
    year: int = Query(...),
    month: int = Query(...),
    staff_id: str | None = Query(None),
    shift_code: str | None = Query(None),
    department_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("schedule_view")),
):
    sch = db.query(Schedule).filter(
        Schedule.schedule_year == year,
        Schedule.schedule_month == month,
        Schedule.is_deleted == False,
    ).first()
    if not sch:
        return []

    q = db.query(ScheduleDetail).filter(
        ScheduleDetail.schedule_id == sch.id,
        ScheduleDetail.is_deleted == False,
    )
    if staff_id:
        q = q.filter(ScheduleDetail.staff_id == staff_id)
    if shift_code:
        q = q.filter(ScheduleDetail.shift_code == shift_code)

    rows = q.order_by(ScheduleDetail.work_date, ScheduleDetail.staff_name).all()

    shift_info: dict[str, dict] = {
        s.code: {"name": s.name, "color": s.color, "start": s.start_time, "end": s.end_time}
        for s in db.query(ShiftType).filter(ShiftType.is_deleted == False).all()
    }
    staff_info: dict[str, dict] = {
        s.id: {"dept_name": s.department_name, "employment_type": s.employment_type}
        for s in db.query(StaffMember).filter(StaffMember.is_deleted == False).all()
    }

    WEEKDAY_MAP = ["一", "二", "三", "四", "五", "六", "日"]

    results = []
    for r in rows:
        si = shift_info.get(r.shift_code, {})
        sti = staff_info.get(r.staff_id, {}) if r.staff_id else {}
        # department filter
        if department_id and sti.get("dept_id") != department_id:
            continue
        results.append({
            "id": r.id,
            "work_date": r.work_date.isoformat(),
            "weekday": WEEKDAY_MAP[r.work_date.weekday()],
            "staff_id": r.staff_id,
            "staff_name": r.staff_name,
            "department_name": sti.get("dept_name", ""),
            "employment_type": sti.get("employment_type", ""),
            "shift_code": r.shift_code,
            "shift_name": si.get("name", ""),
            "shift_color": si.get("color", "#6b7280"),
            "start_time": r.start_time or si.get("start", ""),
            "end_time": r.end_time or si.get("end", ""),
            "work_minutes": r.work_minutes,
            "remark": r.remark,
            "schedule_id": r.schedule_id,
        })
    return results


# ─────────────────────────────────────────────────────────────
# 班別區間查詢（供工作日誌 TAB 整合班別顯示用）
# ─────────────────────────────────────────────────────────────

@router.get("/shifts-range", summary="班別查詢（日期區間）— 供工作日誌整合使用")
def get_shifts_range(
    date_from: str = Query(..., description="起始日期 YYYY-MM-DD"),
    date_to:   str = Query(..., description="結束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    回傳指定日期區間內每日人員班別映射。
    格式：{ "2026-05-20": { "王大明": { "shift_code": "Y", "shift_color": "#10b981", "is_working": true } } }

    is_working 判斷邏輯：
      - 班別存在於 shift_types → 以 shift_types.work_minutes > 0 判斷
      - 班別不在 shift_types（未知代碼）→ 以 schedule_details.work_minutes > 0 判斷
      - 兩者皆無法取得 → is_working = False
    區間上限 93 天，超過時截斷。
    """
    from datetime import timedelta

    try:
        start = date.fromisoformat(date_from)
        end   = date.fromisoformat(date_to)
    except ValueError:
        return {}

    if end < start:
        start, end = end, start
    if (end - start).days > 92:
        end = start + timedelta(days=92)

    # 班別 code → { color, work_minutes, name }
    shift_type_map: dict[str, dict] = {
        s.code: {"color": s.color, "work_minutes": s.work_minutes, "name": s.name}
        for s in db.query(ShiftType).filter(ShiftType.is_deleted == False).all()
    }

    # 查範圍內所有班表明細（非軟刪除）
    details = (
        db.query(ScheduleDetail)
        .filter(
            ScheduleDetail.work_date >= start,
            ScheduleDetail.work_date <= end,
            ScheduleDetail.is_deleted == False,
        )
        .all()
    )

    result: dict[str, dict] = {}
    for d in details:
        date_str = d.work_date.isoformat()          # "2026-05-20"
        if date_str not in result:
            result[date_str] = {}

        st = shift_type_map.get(d.shift_code)
        if st is not None:
            color      = st["color"]
            is_working = st["work_minutes"] > 0
            shift_name = st["name"]
        else:
            # 未知班別代碼：以明細本身的 work_minutes 判斷
            color      = "#6b7280"
            is_working = (d.work_minutes or 0) > 0
            shift_name = ""

        # 同一人同一天若有多筆（理論上不應發生），以 is_working=True 優先
        existing = result[date_str].get(d.staff_name)
        if existing and existing["is_working"]:
            continue

        result[date_str][d.staff_name] = {
            "shift_code":  d.shift_code,
            "shift_name":  shift_name,
            "shift_color": color,
            "is_working":  is_working,
        }

    return result
