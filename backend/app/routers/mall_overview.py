"""
商場管理 Dashboard — 跨模組彙整 API
GET /api/v1/mall/daily-hours   每日工時彙總（五項工項）

來源（均查本地 DB，不打 Ragic）：
  ① 現場報修 — luqun_repair_cases（_stat_dt 口徑：已結案→completed_at，其餘→occurred_at，排除取消）
  ② 上級交辦 — 固定 0（模組未開發）
  ③ 緊急事件 — 固定 0（模組未開發）
  ④ 例行維護 — mall_pm_batch_item + full_bldg_pm_batch_item（start_time / end_time 實際保養時間）
  ⑤ 每日巡檢 — mall_facility_inspection_batch + rf_inspection_batch（start/end_time）

回傳格式與 work-category-analysis _build_daily 一致，供前端直接套用相同表格元件。
"""
import calendar
import re
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.full_building_maintenance import FullBldgPMBatch, FullBldgPMItem
from app.models.luqun_repair import LuqunRepairCase
from app.services.time_utils import parse_minutes as _parse_minutes
from app.models.mall_facility_inspection import MallFIBatch
from app.models.mall_periodic_maintenance import (
    MallPeriodicMaintenanceBatch,
    MallPeriodicMaintenanceItem,
)
from app.models.rf_inspection import RFInspectionBatch
from app.models.other_tasks import OtherTask
from app.models.schedule import StaffMember

router = APIRouter(prefix="/mall", tags=["商場管理 Dashboard"])

# 固定五項工項（順序即表格列順序）
MALL_CATEGORIES = ["現場報修", "上級交辦", "緊急事件", "例行維護", "每日巡檢"]


def _norm_name(s: str) -> str:
    """
    人名正規化：去除所有空白（含全形空白）、統一全形英數→半形，供白名單比對。
    比對兩端（staff 名單與 Ragic 人名）都須過此函式，避免格式差異造成誤判。
    """
    if not s:
        return ""
    out = []
    for ch in s:
        code = ord(ch)
        # 全形英數／符號（FF01–FF5E）→ 半形（差 0xFEE0）
        if 0xFF01 <= code <= 0xFF5E:
            ch = chr(code - 0xFEE0)
        # 略過所有空白字元（半形空白、全形空白 U+3000、tab 等）
        if ch.isspace() or ch == "　":
            continue
        out.append(ch)
    return "".join(out)


def _load_staff_allowed(db: Session) -> set[str]:
    """
    讀取班表人員名單（schedule/staff），建立正規化後的白名單 set。
    收錄條件：is_active=True 且未軟刪除；name 與 source_name 皆納入（任一相符即在名單內）。
    """
    allowed: set[str] = set()
    for s in (
        db.query(StaffMember)
        .filter(StaffMember.is_active == True, StaffMember.is_deleted == False)  # noqa: E712
        .all()
    ):
        for raw in (s.name, s.source_name):
            n = _norm_name(raw or "")
            if n:
                allowed.add(n)
    return allowed



@router.get("/daily-hours", summary="商場管理 — 每日工時彙總（五項工項，含主管交辦／緊急事件）")
def get_mall_daily_hours(
    year:  int = Query(..., ge=2020, le=2030, description="年份"),
    month: int = Query(..., ge=1,    le=12,   description="月份（1–12）"),
    db: Session = Depends(get_db),
):
    """
    彙整五項工作類別的每日工時（HR），供商場管理 Dashboard「B. 每日累計」Tab 使用。

    回傳格式：
    ```json
    {
      "year": 2026, "month": 4,
      "days": [1, 2, ..., 30],
      "weekdays": ["二", "三", ...],
      "rows": [
        {"category": "現場報修", "hours": [1.5, 0.0, ...], "total": 10.5, "pct": 35.0},
        ...
        {"category": "TOTAL",   "hours": [...],            "total": 30.0, "pct": 100.0}
      ]
    }
    ```
    """
    _, days_in_month = calendar.monthrange(year, month)
    days = list(range(1, days_in_month + 1))
    zh = ["一", "二", "三", "四", "五", "六", "日"]
    weekdays = [zh[date(year, month, d).weekday()] for d in days]

    bucket: dict[str, dict[int, float]] = {c: defaultdict(float) for c in MALL_CATEGORIES}
    case_bucket: dict[str, dict[int, int]] = {c: defaultdict(int) for c in MALL_CATEGORIES}

    # ── ① 現場報修：_stat_dt 口徑（已結案→completed_at，其餘→occurred_at，排除取消）─
    for c in db.query(LuqunRepairCase).all():
        if c.is_excluded_flag:
            continue
        stat_dt = c.completed_at if (c.is_completed_flag and c.completed_at) else c.occurred_at
        if not stat_dt:
            continue
        if stat_dt.year == year and stat_dt.month == month:
            case_bucket["現場報修"][stat_dt.day] += 1
            if (c.work_hours or 0) > 0:
                bucket["現場報修"][stat_dt.day] += c.work_hours

    # ── ④ 例行維護：mall_pm_batch_item ───────────────────────────────────────
    # period_month 可能儲存為 "2026/04" 或 "2026/4"，用 LIKE + Python 過濾
    # 確保不遺漏任何零填充格式差異
    def _pm_day(sched: str) -> int:
        """
        scheduled_date 格式 "MM/DD" → day；
        無法解析（空白或格式異常）→ 1（落回月初，確保實際保養時間不漏算）
        """
        s = (sched or "").strip()
        if "/" in s:
            try:
                d = int(s.split("/")[1])
                if 1 <= d <= days_in_month:
                    return d
            except (ValueError, IndexError):
                pass
        return 1   # 未排定 / 格式不符 → 歸入第 1 天

    mall_pm_batches = (
        db.query(MallPeriodicMaintenanceBatch)
        .filter(MallPeriodicMaintenanceBatch.period_month.like(f"{year}/%"))
        .all()
    )
    mall_pm_batch_ids = [
        b.ragic_id for b in mall_pm_batches
        if b.period_month and int(b.period_month.split("/")[1]) == month
    ]
    if mall_pm_batch_ids:
        for item in (
            db.query(MallPeriodicMaintenanceItem)
            .filter(MallPeriodicMaintenanceItem.batch_ragic_id.in_(mall_pm_batch_ids))
            .all()
        ):
            mins = _parse_minutes(item.start_time or "", item.end_time or "")
            case_bucket["例行維護"][_pm_day(item.scheduled_date)] += 1
            if mins > 0:
                bucket["例行維護"][_pm_day(item.scheduled_date)] += mins / 60

    # ── ④ 例行維護：full_bldg_pm_batch_item ──────────────────────────────────
    fb_pm_batches = (
        db.query(FullBldgPMBatch)
        .filter(FullBldgPMBatch.period_month.like(f"{year}/%"))
        .all()
    )
    fb_batch_ids = [
        b.ragic_id for b in fb_pm_batches
        if b.period_month and int(b.period_month.split("/")[1]) == month
    ]
    if fb_batch_ids:
        for item in (
            db.query(FullBldgPMItem)
            .filter(FullBldgPMItem.batch_ragic_id.in_(fb_batch_ids))
            .all()
        ):
            mins = _parse_minutes(item.start_time or "", item.end_time or "")
            case_bucket["例行維護"][_pm_day(item.scheduled_date)] += 1
            if mins > 0:
                bucket["例行維護"][_pm_day(item.scheduled_date)] += mins / 60

    # ── ⑤ 每日巡檢：mall_facility_inspection_batch（實際+缺漏補算）─────────────
    # 5 張固定巡檢表（4F/3F/1F-3F/1F/B1F-B4F），每天每表應巡一次
    MALL_FI_SHEET_COUNT = 5
    _today = date.today()
    counting_end_day = _today.day if (year == _today.year and month == _today.month) else days_in_month
    date_prefix = f"{year}/{month:02d}/"

    fi_sheets_by_day: dict[int, set] = defaultdict(set)
    for b in (
        db.query(MallFIBatch)
        .filter(MallFIBatch.inspection_date.like(f"{date_prefix}%"))
        .all()
    ):
        try:
            day = int(b.inspection_date.split("/")[2])
            if 1 <= day <= days_in_month:
                fi_sheets_by_day[day].add(b.sheet_key)
                mins = _parse_minutes(b.start_time or "", b.end_time or "")
                bucket["每日巡檢"][day] += mins / 60
        except (ValueError, IndexError):
            pass

    # 實際場次 + 缺漏場次（≤ counting_end_day 才補缺漏）
    for d in days:
        actual = len(fi_sheets_by_day.get(d, set()))
        if d <= counting_end_day:
            case_bucket["每日巡檢"][d] += actual + max(0, MALL_FI_SHEET_COUNT - actual)
        else:
            case_bucket["每日巡檢"][d] += actual

    # ── ⑤ 每日巡檢：rf_inspection_batch（整棟巡檢，實際批次數）─────────────────
    for b in (
        db.query(RFInspectionBatch)
        .filter(RFInspectionBatch.inspection_date.like(f"{date_prefix}%"))
        .all()
    ):
        try:
            day = int(b.inspection_date.split("/")[2])
            if 1 <= day <= days_in_month:
                mins = _parse_minutes(b.start_time or "", b.end_time or "")
                case_bucket["每日巡檢"][day] += 1
                bucket["每日巡檢"][day] += mins / 60
        except (ValueError, IndexError):
            pass

    # ── ② 上級交辦 / ③ 緊急事件：OtherTask，venue='商場'，created_at 歸屬日 ─────
    for ot in (
        db.query(OtherTask)
        .filter(OtherTask.year == year, OtherTask.month == month, OtherTask.venue == "商場")
        .all()
    ):
        tt = ot.task_type
        if tt not in ("上級交辦", "緊急事件"):
            continue
        if ot.created_at is None:
            continue
        d = ot.created_at.day
        if 1 <= d <= days_in_month:
            case_bucket[tt][d] += 1
            wh = ot.work_hours or 0
            if wh > 0:
                bucket[tt][d] += wh

    # ── 組裝結果（與 WCA _build_daily 格式完全一致）──────────────────────────
    result_rows: list[dict] = []
    grand_total = 0.0
    grand_day = [0.0] * len(days)
    grand_cases_total = 0
    grand_cases_day = [0] * len(days)

    for cat in MALL_CATEGORIES:
        day_h = [round(bucket[cat][d], 1) for d in days]
        total = round(sum(day_h), 1)
        grand_total += total
        for i, h in enumerate(day_h):
            grand_day[i] += h
        day_c = [case_bucket[cat][d] for d in days]
        cases_total = sum(day_c)
        grand_cases_total += cases_total
        for i, c in enumerate(day_c):
            grand_cases_day[i] += c
        result_rows.append({"category": cat, "hours": day_h, "total": total, "pct": 0.0,
                            "cases": day_c, "cases_total": cases_total, "cases_pct": 0.0})

    # 計算各列 %
    for row in result_rows:
        row["pct"] = round(row["total"] / grand_total * 100, 1) if grand_total else 0.0
        row["cases_pct"] = round(row["cases_total"] / grand_cases_total * 100, 1) if grand_cases_total else 0.0

    # TOTAL 合計列
    result_rows.append({
        "category":    "TOTAL",
        "hours":       [round(h, 1) for h in grand_day],
        "total":       round(grand_total, 1),
        "pct":         100.0,
        "cases":       grand_cases_day,
        "cases_total": grand_cases_total,
        "cases_pct":   100.0,
    })

    return {
        "year":     year,
        "month":    month,
        "days":     days,
        "weekdays": weekdays,
        "rows":     result_rows,
    }


@router.get("/monthly-hours", summary="商場管理 — 每月工時彙總（五項工項，含主管交辦／緊急事件）")
def get_mall_monthly_hours(
    year: int = Query(..., ge=2020, le=2030, description="年份"),
    db: Session = Depends(get_db),
):
    """
    彙整五項工作類別的每月工時（HR），供商場管理 Dashboard「C. 每月累計」Tab 使用。

    回傳格式：
    ```json
    {
      "year": 2026,
      "months": [1, 2, ..., 12],
      "rows": [
        {"category": "現場報修", "hours": [1.5, 3.0, ...], "total": 45.0, "pct": 35.0},
        ...
        {"category": "TOTAL",   "hours": [...],            "total": 128.0, "pct": 100.0}
      ]
    }
    ```
    """
    bucket: dict[str, dict[int, float]] = {c: defaultdict(float) for c in MALL_CATEGORIES}
    case_bucket: dict[str, dict[int, int]] = {c: defaultdict(int) for c in MALL_CATEGORIES}
    year_prefix = f"{year}/"

    # ── ① 現場報修：_stat_dt 口徑（已結案→completed_at，其餘→occurred_at，排除取消）─
    for c in db.query(LuqunRepairCase).all():
        if c.is_excluded_flag:
            continue
        stat_dt = c.completed_at if (c.is_completed_flag and c.completed_at) else c.occurred_at
        if not stat_dt:
            continue
        if stat_dt.year == year and 1 <= stat_dt.month <= 12:
            case_bucket["現場報修"][stat_dt.month] += 1
            if (c.work_hours or 0) > 0:
                bucket["現場報修"][stat_dt.month] += c.work_hours

    # ── ④ 例行維護：mall_pm ──────────────────────────────────────────────────
    # 先撈 batch（1 次），再用 IN 一次撈全部 items（1 次），避免 N+1
    _mall_pm_batches = (
        db.query(MallPeriodicMaintenanceBatch)
        .filter(MallPeriodicMaintenanceBatch.period_month.like(f"{year_prefix}%"))
        .all()
    )
    _mall_pm_batch_month: dict[str, int] = {}
    for _b in _mall_pm_batches:
        try:
            _m = int(_b.period_month.split("/")[1])
            if 1 <= _m <= 12:
                _mall_pm_batch_month[_b.ragic_id] = _m
        except (ValueError, IndexError, AttributeError):
            pass

    if _mall_pm_batch_month:
        for item in db.query(MallPeriodicMaintenanceItem).filter(
            MallPeriodicMaintenanceItem.batch_ragic_id.in_(_mall_pm_batch_month.keys())
        ).all():
            m = _mall_pm_batch_month.get(item.batch_ragic_id)
            if m is None:
                continue
            mins = _parse_minutes(item.start_time or "", item.end_time or "")
            case_bucket["例行維護"][m] += 1
            bucket["例行維護"][m] += mins / 60

    # ── ④ 例行維護：full_bldg_pm ─────────────────────────────────────────────
    # 先撈 batch（1 次），再用 IN 一次撈全部 items（1 次），避免 N+1
    _fbldg_pm_batches = (
        db.query(FullBldgPMBatch)
        .filter(FullBldgPMBatch.period_month.like(f"{year_prefix}%"))
        .all()
    )
    _fbldg_pm_batch_month: dict[str, int] = {}
    for _b in _fbldg_pm_batches:
        try:
            _m = int(_b.period_month.split("/")[1])
            if 1 <= _m <= 12:
                _fbldg_pm_batch_month[_b.ragic_id] = _m
        except (ValueError, IndexError, AttributeError):
            pass

    if _fbldg_pm_batch_month:
        for item in db.query(FullBldgPMItem).filter(
            FullBldgPMItem.batch_ragic_id.in_(_fbldg_pm_batch_month.keys())
        ).all():
            m = _fbldg_pm_batch_month.get(item.batch_ragic_id)
            if m is None:
                continue
            mins = _parse_minutes(item.start_time or "", item.end_time or "")
            case_bucket["例行維護"][m] += 1
            bucket["例行維護"][m] += mins / 60

    # ── ⑤ 每日巡檢：mall_facility ────────────────────────────────────────────
    for b in db.query(MallFIBatch).filter(MallFIBatch.inspection_date.like(f"{year_prefix}%")).all():
        try:
            m = int(b.inspection_date.split("/")[1])
        except (ValueError, IndexError, AttributeError):
            continue
        if 1 <= m <= 12:
            case_bucket["每日巡檢"][m] += 1
            bucket["每日巡檢"][m] += _parse_minutes(b.start_time or "", b.end_time or "") / 60

    # ── ⑤ 每日巡檢：rf_inspection ────────────────────────────────────────────
    for b in db.query(RFInspectionBatch).filter(RFInspectionBatch.inspection_date.like(f"{year_prefix}%")).all():
        try:
            m = int(b.inspection_date.split("/")[1])
        except (ValueError, IndexError, AttributeError):
            continue
        if 1 <= m <= 12:
            case_bucket["每日巡檢"][m] += 1
            bucket["每日巡檢"][m] += _parse_minutes(b.start_time or "", b.end_time or "") / 60

    # ── ② 上級交辦 / ③ 緊急事件：OtherTask，venue='商場'，year+month 歸屬月 ────
    for ot in (
        db.query(OtherTask)
        .filter(OtherTask.year == year, OtherTask.venue == "商場")
        .all()
    ):
        tt = ot.task_type
        if tt not in ("上級交辦", "緊急事件"):
            continue
        m = ot.month
        if m and 1 <= m <= 12:
            case_bucket[tt][m] += 1
            wh = ot.work_hours or 0
            if wh > 0:
                bucket[tt][m] += wh

    # ── 組裝結果 ─────────────────────────────────────────────────────────────
    result_rows: list[dict] = []
    grand_total = 0.0
    grand_m = [0.0] * 12
    grand_cases_total = 0
    grand_cases_m = [0] * 12

    for cat in MALL_CATEGORIES:
        mh = [round(bucket[cat][m], 1) for m in range(1, 13)]
        total = round(sum(mh), 1)
        grand_total += total
        for i, h in enumerate(mh):
            grand_m[i] += h
        mc = [case_bucket[cat][m] for m in range(1, 13)]
        cases_total = sum(mc)
        grand_cases_total += cases_total
        for i, c in enumerate(mc):
            grand_cases_m[i] += c
        result_rows.append({"category": cat, "hours": mh, "total": total, "pct": 0.0,
                            "cases": mc, "cases_total": cases_total, "cases_pct": 0.0})

    for row in result_rows:
        row["pct"] = round(row["total"] / grand_total * 100, 1) if grand_total else 0.0
        row["cases_pct"] = round(row["cases_total"] / grand_cases_total * 100, 1) if grand_cases_total else 0.0

    result_rows.append({
        "category":    "TOTAL",
        "hours":       [round(h, 1) for h in grand_m],
        "total":       round(grand_total, 1),
        "pct":         100.0,
        "cases":       grand_cases_m,
        "cases_total": grand_cases_total,
        "cases_pct":   100.0,
    })

    return {"year": year, "months": list(range(1, 13)), "rows": result_rows}


@router.get("/person-hours", summary="商場管理 — 人員工時佔比（五項工項，含主管交辦／緊急事件）")
def get_mall_person_hours(
    year: int = Query(..., ge=2020, le=2030, description="年份"),
    db: Session = Depends(get_db),
):
    """
    彙整五項工作類別各人員工時佔比，供商場管理 Dashboard「D. 人員工時%」Tab 使用。
    格式與 WCA _build_person_table 完全一致。

    人員識別規則：
      ① 現場報修 — LuqunRepairCase.acceptor（結案人）
      ② 上級交辦 — OtherTask.engineer（task_type='上級交辦'，venue='商場'）
      ③ 緊急事件 — OtherTask.engineer（task_type='緊急事件'，venue='商場'）
      ④ 例行維護 — MallPeriodicMaintenanceItem / FullBldgPMItem.executor_name（可空格分隔多人）
      ⑤ 每日巡檢 — MallFIBatch / RFInspectionBatch.inspector_name

    回傳格式：
    ```json
    {
      "year": 2026,
      "persons": ["王小明", "李大華", ...],
      "rows": [
        {"category": "現場報修", "pct_by_person": [45.2, 30.1, ...]},
        ...
      ]
    }
    ```
    """
    year_prefix = f"{year}/"

    # person → category → hours 彙整
    ph: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    # ── ① 現場報修：acceptor ─────────────────────────────────────────────────
    for c in db.query(LuqunRepairCase).filter(LuqunRepairCase.occ_year == year).all():
        person = (c.acceptor or "").strip()
        if person and person != "未指定" and (c.work_hours or 0) > 0:
            ph[person]["現場報修"] += c.work_hours

    # ── ④ 例行維護：executor_name（可多人空格分隔）──────────────────────────────
    # 先撈 batch（1 次），再用 IN 一次撈全部 items（1 次），避免 N+1
    _mall_pm_ids = [
        b.ragic_id for b in
        db.query(MallPeriodicMaintenanceBatch)
        .filter(MallPeriodicMaintenanceBatch.period_month.like(f"{year_prefix}%"))
        .all()
    ]
    if _mall_pm_ids:
        for item in db.query(MallPeriodicMaintenanceItem).filter(
            MallPeriodicMaintenanceItem.batch_ragic_id.in_(_mall_pm_ids)
        ).all():
            names = [n.strip() for n in (item.executor_name or "").split() if n.strip() and n.strip() != "未指定"]
            mins = _parse_minutes(item.start_time or "", item.end_time or "")
            if names and mins > 0:
                share = (mins / 60) / len(names)
                for n in names:
                    ph[n]["例行維護"] += share

    _fbldg_pm_ids = [
        b.ragic_id for b in
        db.query(FullBldgPMBatch)
        .filter(FullBldgPMBatch.period_month.like(f"{year_prefix}%"))
        .all()
    ]
    if _fbldg_pm_ids:
        for item in db.query(FullBldgPMItem).filter(
            FullBldgPMItem.batch_ragic_id.in_(_fbldg_pm_ids)
        ).all():
            names = [n.strip() for n in (item.executor_name or "").split() if n.strip() and n.strip() != "未指定"]
            mins = _parse_minutes(item.start_time or "", item.end_time or "")
            if names and mins > 0:
                share = (mins / 60) / len(names)
                for n in names:
                    ph[n]["例行維護"] += share

    # ── ⑤ 每日巡檢：inspector_name ───────────────────────────────────────────
    for b in db.query(MallFIBatch).filter(MallFIBatch.inspection_date.like(f"{year_prefix}%")).all():
        person = (b.inspector_name or "").strip()
        if person and person != "未指定":
            mins = _parse_minutes(b.start_time or "", b.end_time or "")
            if mins > 0:
                ph[person]["每日巡檢"] += mins / 60

    for b in db.query(RFInspectionBatch).filter(RFInspectionBatch.inspection_date.like(f"{year_prefix}%")).all():
        person = (b.inspector_name or "").strip()
        if person and person != "未指定":
            mins = _parse_minutes(b.start_time or "", b.end_time or "")
            if mins > 0:
                ph[person]["每日巡檢"] += mins / 60

    # ── ② 上級交辦 / ③ 緊急事件：OtherTask，engineer 人員，venue='商場' ──────────
    for ot in (
        db.query(OtherTask)
        .filter(OtherTask.year == year, OtherTask.venue == "商場")
        .all()
    ):
        tt = ot.task_type
        if tt not in ("上級交辦", "緊急事件"):
            continue
        person = (ot.engineer or "").strip()
        if not person or person == "未指定":
            continue
        wh = ot.work_hours or 0
        if wh > 0:
            ph[person][tt] += wh

    # ── staff 白名單過濾：不在班表名單的人員整筆剔除（不顯示、不計算）──────────────
    allowed = _load_staff_allowed(db)
    excluded_persons: list[str] = []
    for p in list(ph.keys()):
        if _norm_name(p) not in allowed:
            excluded_persons.append(p)
            del ph[p]
    excluded_persons = sorted(set(excluded_persons))

    # ── 找出 Top-15 人員（依全類別合計工時降冪）─────────────────────────────────
    person_totals: dict[str, float] = {
        p: sum(cats.values()) for p, cats in ph.items()
    }
    persons = sorted(person_totals, key=lambda p: -person_totals[p])[:15]

    if not persons:
        return {"year": year, "persons": [], "rows": [], "excluded_persons": excluded_persons}

    # ── 組裝結果（格式與 WCA _build_person_table 完全一致）───────────────────────
    result_rows = []
    for cat in MALL_CATEGORIES:
        cat_total = sum(ph[p][cat] for p in persons)
        result_rows.append({
            "category":      cat,
            "pct_by_person": [
                round(ph[p][cat] / cat_total * 100, 1) if cat_total else 0.0
                for p in persons
            ],
            # 每位人員在該工項的「真實工時(HR)」，供分解圖堆疊（各工項相加 = person_totals）
            "hours_by_person": [round(ph[p][cat], 1) for p in persons],
        })

    return {
        "year":             year,
        "persons":          persons,
        "person_totals":    [round(person_totals[p], 1) for p in persons],
        "rows":             result_rows,
        "excluded_persons": excluded_persons,
    }
