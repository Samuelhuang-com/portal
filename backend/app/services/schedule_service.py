"""
班表模組業務邏輯 Service
統計計算、資料查詢輔助函數
"""
import calendar
from datetime import date
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.schedule import (
    Schedule, ScheduleDetail, StaffMember, ShiftType, Department
)


def get_schedule_table(
    db: Session,
    year: int,
    month: int,
    staff_id: str | None = None,
    department_id: str | None = None,
    shift_code: str | None = None,
) -> dict:
    """
    取得橫向表格式班表資料。
    回傳結構：
    {
        "schedule": Schedule,
        "days_in_month": int,
        "headers": [{"day": 1, "weekday": "五"}, ...],
        "rows": [
            {
                "staff_id": str,
                "staff_name": str,
                "employment_type": str,
                "department_name": str,
                "cells": {1: {"shift_code": "N1", "color": "#3b82f6"}, ...},
                "stats": {"work_days": 20, "work_minutes": 9600}
            }
        ]
    }
    """
    WEEKDAY_MAP = ["一", "二", "三", "四", "五", "六", "日"]

    schedule = (
        db.query(Schedule)
        .filter(
            Schedule.schedule_year == year,
            Schedule.schedule_month == month,
            Schedule.is_deleted == False,
        )
        .first()
    )
    if not schedule:
        return {"schedule": None, "headers": [], "rows": []}

    days_in_month = calendar.monthrange(year, month)[1]
    headers = []
    for day in range(1, days_in_month + 1):
        wd = date(year, month, day).weekday()
        headers.append({"day": day, "weekday": WEEKDAY_MAP[wd]})

    # 取得此班表所有明細
    query = (
        db.query(ScheduleDetail)
        .filter(
            ScheduleDetail.schedule_id == schedule.id,
            ScheduleDetail.is_deleted == False,
        )
    )
    if staff_id:
        query = query.filter(ScheduleDetail.staff_id == staff_id)
    if shift_code:
        query = query.filter(ScheduleDetail.shift_code == shift_code)

    details = query.all()

    # 班別顏色 lookup
    shift_color: dict[str, str] = {
        s.code: s.color
        for s in db.query(ShiftType).filter(ShiftType.is_deleted == False).all()
    }

    # 人員資訊 lookup
    staff_info: dict[str, dict] = {}
    for s in db.query(StaffMember).filter(StaffMember.is_deleted == False).all():
        staff_info[s.id] = {
            "name": s.source_name,
            "employment_type": s.employment_type,
            "department_name": s.department_name,
            "department_id": s.department_id,
        }

    # 按人員分組
    by_staff: dict[str, dict] = {}
    for d in details:
        key = d.staff_id or d.staff_name
        if key not in by_staff:
            info = staff_info.get(d.staff_id, {}) if d.staff_id else {}
            # department filter
            if department_id and info.get("department_id") != department_id:
                continue
            by_staff[key] = {
                "staff_id": d.staff_id,
                "staff_name": d.staff_name,
                "employment_type": info.get("employment_type", ""),
                "department_name": info.get("department_name", ""),
                "cells": {},
                "work_days": 0,
                "work_minutes": 0,
            }
        day = d.work_date.day
        by_staff[key]["cells"][day] = {
            "detail_id": d.id,
            "shift_code": d.shift_code,
            "color": shift_color.get(d.shift_code, "#6b7280"),
            "work_minutes": d.work_minutes,
        }
        by_staff[key]["work_days"] += 1
        by_staff[key]["work_minutes"] += d.work_minutes

    # raw_summary 統計（來自 Excel 原始欄位）
    raw_sum = schedule.raw_summary or {}

    rows = []
    for key, row in by_staff.items():
        # 加入 Excel 原始統計
        rs = raw_sum.get(row["staff_name"], {})
        row["raw_summary"] = rs
        rows.append(row)

    # 依姓名排序
    rows.sort(key=lambda r: r["staff_name"])

    return {
        "schedule": schedule,
        "days_in_month": days_in_month,
        "headers": headers,
        "rows": rows,
    }


def get_monthly_stats(db: Session, year: int, month: int) -> dict:
    """取得月統計摘要"""
    schedule = (
        db.query(Schedule)
        .filter(
            Schedule.schedule_year == year,
            Schedule.schedule_month == month,
            Schedule.is_deleted == False,
        )
        .first()
    )
    if not schedule:
        return {}

    details = (
        db.query(ScheduleDetail)
        .filter(
            ScheduleDetail.schedule_id == schedule.id,
            ScheduleDetail.is_deleted == False,
        )
        .all()
    )

    # 人員統計
    person_stats: dict[str, dict] = defaultdict(
        lambda: {"work_days": 0, "work_minutes": 0, "shifts": defaultdict(int)}
    )
    shift_stats: dict[str, int] = defaultdict(int)
    daily_stats: dict[str, dict] = defaultdict(lambda: defaultdict(int))

    for d in details:
        key = d.staff_name
        person_stats[key]["work_days"] += 1
        person_stats[key]["work_minutes"] += d.work_minutes
        person_stats[key]["shifts"][d.shift_code] += 1
        shift_stats[d.shift_code] += 1
        date_str = d.work_date.isoformat()
        daily_stats[date_str][d.shift_code] += 1

    return {
        "schedule_id": schedule.id,
        "year": year,
        "month": month,
        "total_staff": len(person_stats),
        "total_details": len(details),
        "person_stats": dict(person_stats),
        "shift_stats": dict(shift_stats),
        "daily_stats": dict(daily_stats),
    }
