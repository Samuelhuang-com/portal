"""
工作日誌 API
Prefix: /api/v1/work-journal

彙整 10 個模組當日工作記錄，依人員分組回傳。
日誌時間基準：報修類用 occurred_at，保養/巡檢類用各自的 scheduled_date / inspection_date / maint_date。

回傳格式：
{
  "date": "2026/05/15",
  "persons": [
    { "person": "王大明", "rows": [ JournalRow, ... ] },
    { "person": "未指定", "rows": [...] }
  ],
  "total_rows": 38
}
"""

import io
import re
from datetime import date as _date, timedelta, datetime
from collections import defaultdict
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Query, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user

# ── Models ────────────────────────────────────────────────────────────────────
from app.models.dazhi_repair            import DazhiRepairCase
from app.models.luqun_repair            import LuqunRepairCase
from app.models.periodic_maintenance    import PeriodicMaintenanceBatch, PeriodicMaintenanceItem
from app.models.ihg_room_maintenance    import IHGRoomMaintenanceMaster
from app.models.hotel_daily_inspection  import HotelDIBatch
from app.models.security_patrol         import SecurityPatrolBatch
from app.models.mall_periodic_maintenance import MallPeriodicMaintenanceBatch, MallPeriodicMaintenanceItem
from app.models.full_building_maintenance import FullBldgPMBatch, FullBldgPMItem
from app.models.mall_facility_inspection  import MallFIBatch
from app.models.b1f_inspection  import B1FInspectionBatch
from app.models.b2f_inspection  import B2FInspectionBatch
from app.models.b4f_inspection  import B4FInspectionBatch
from app.models.rf_inspection   import RFInspectionBatch

router = APIRouter(dependencies=[Depends(get_current_user)])

# ── 常數 ─────────────────────────────────────────────────────────────────────

CATEGORIES = ["現場報修", "上級交辦", "緊急事件", "例行維護", "每日巡檢"]

_CATEGORY_RULES = [
    ("緊急事件",  ["緊急", "急修", "突發", "漏電緊急", "火警", "停電"]),
    ("每日巡檢",  ["巡檢", "巡視", "例巡", "日巡"]),
    ("例行維護",  ["例行", "定期", "保養", "維護", "定保", "年保", "季保", "月保"]),
    ("上級交辦",  ["交辦", "上級", "主管指示", "主管交辦", "院長", "指示", "指派"]),
]

SOURCE_LABEL = {
    "dazhi":        "飯店工務",
    "luqun":        "商場工務",
    "hotel_pm":     "飯店週期保養",
    "ihg":          "IHG客房保養",
    "hotel_di":     "飯店每日巡檢",
    "security":     "保全巡檢",
    "mall_pm":      "商場週期保養",
    "full_bldg_pm": "整棟保養",
    "mall_fi":      "商場設施巡檢",
    "full_bi":      "整棟巡檢",
}

SORT_ORDER = list(SOURCE_LABEL.keys())


# ── 工具函數 ───────────────────────────────────────────────────────────────────

def _classify(title: str, repair_type: str) -> str:
    text = (title or "") + (repair_type or "")
    for cat, keywords in _CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return cat
    return "現場報修"


def _parse_wm(val: str) -> Optional[int]:
    """'2.50 小時' / '30 分鐘' / '8'（無單位→分鐘）→ int 分鐘，解析不到 → None
    注意：巡檢模組 work_hours 欄位儲存的是純數字分鐘，無單位標記，因此無單位時直接視為分鐘。
    """
    if not val:
        return None
    s = str(val).strip()
    m = re.search(r"[\d.]+", s)
    if not m:
        return None
    num = float(m.group())
    if "分" in s:
        return round(num) if num > 0 else None
    if "時" in s:                          # 含「小時」字樣 → ×60
        mins = round(num * 60)
        return mins if mins > 0 else None
    # 無單位 → 視為分鐘（保全/巡檢 DB 欄位直接儲存分鐘數）
    return round(num) if num > 0 else None


def _clean_time(t: str) -> str:
    """'2026/05/15 09:00' → '09:00'，已是 HH:MM 則直接回傳"""
    if not t:
        return ""
    t = t.strip()
    if " " in t:
        t = t.split(" ")[-1]
    if re.match(r"^\d{1,2}:\d{2}$", t):
        return t
    return t[:5] if len(t) >= 5 else t


def _persons(name: str) -> list[str]:
    """executor_name 可能含多人（空格分隔），拆成 list；空白 → ['未指定']"""
    if not name or not name.strip():
        return ["未指定"]
    parts = [p.strip() for p in name.strip().split() if p.strip()]
    return parts if parts else ["未指定"]


def _date_str(year: int, month: int, day: int) -> str:
    return f"{year}/{month:02d}/{day:02d}"


def _make_row(
    source: str,
    category: str,
    task: str,
    person: str,
    est_min: Optional[int] = None,
    start_time: str = "",
    end_time: str = "",
    work_min: Optional[int] = None,
    remark: str = "",
    report: str = "",
    ragic_id: str = "",
    detail: Optional[dict] = None,
) -> dict:
    return {
        "source":       source,
        "source_label": SOURCE_LABEL.get(source, source),
        "category":     category,
        "task":         task.strip(),
        "person":       person or "未指定",
        "est_min":      est_min,
        "start_time":   _clean_time(start_time),
        "end_time":     _clean_time(end_time),
        "work_min":     work_min,
        "remark":       (remark or "").strip(),
        "report":       (report or "").strip(),
        "ragic_id":     ragic_id,
        "detail":       detail or {},
    }


# ── 10 個模組 helper ──────────────────────────────────────────────────────────

def _fetch_dazhi(db: Session, year: int, month: int, day: int) -> list[dict]:
    """大直工務報修：occurred_at 日期口徑"""
    rows = []
    target = _date(year, month, day)
    for c in db.query(DazhiRepairCase).all():
        if not c.occurred_at:
            continue
        if (c.status or "").strip() == "取消":
            continue
        if c.occurred_at.date() != target:
            continue
        person = (c.responsible_unit or "").strip() or "未指定"
        task = " ".join(filter(None, [c.repair_type, c.floor, c.title]))
        wm   = round(c.work_hours * 60) if c.work_hours and c.work_hours > 0 else None
        occ  = c.occurred_at.strftime("%Y/%m/%d %H:%M") if c.occurred_at else ""
        rows.append(_make_row(
            source="dazhi",
            category=_classify(c.title or "", c.repair_type or ""),
            task=task or "(無說明)",
            person=person,
            work_min=wm,
            remark=c.finance_note or "",
            ragic_id=c.ragic_id,
            detail={
                "報修編號":  c.case_no or "",
                "標題":      c.title or "",
                "報修人姓名": c.reporter_name or "",
                "報修類型":  c.repair_type or "",
                "發生樓層":  c.floor or "",
                "發生時間":  occ,
                "負責單位":  c.responsible_unit or "",
                "花費工時":  f"{c.work_hours:.2f} hr" if c.work_hours else "",
                "處理狀況":  c.status or "",
                "委外費用":  str(int(c.outsource_fee or 0)),
                "維修費用":  str(int(c.maintenance_fee or 0)),
                "總費用":    str(int(c.total_fee or 0)),
                "驗收者":    c.acceptor or "",
                "驗收":      c.accept_status or "",
                "結案人":    c.closer or "",
                "結案時間":  c.completed_at.strftime("%Y/%m/%d") if c.completed_at else "",
                "結案天數":  f"{c.close_days:.1f} 天" if c.close_days else "",
                "扣款事項":  c.deduction_item or "",
                "扣款費用":  str(int(c.deduction_fee or 0)),
                "財務備註":  c.finance_note or "",
            },
        ))
    return rows


def _fetch_luqun(db: Session, year: int, month: int, day: int) -> list[dict]:
    """商場工務報修：occurred_at 日期口徑"""
    rows = []
    target = _date(year, month, day)
    for c in db.query(LuqunRepairCase).all():
        if not c.occurred_at:
            continue
        if (c.status or "").strip() == "取消":
            continue
        if c.occurred_at.date() != target:
            continue
        person = (c.responsible_unit or "").strip() or "未指定"
        task = " ".join(filter(None, [c.repair_type, c.floor, c.title]))
        wm   = round(c.work_hours * 60) if c.work_hours and c.work_hours > 0 else None
        occ  = c.occurred_at.strftime("%Y/%m/%d %H:%M") if c.occurred_at else ""
        rows.append(_make_row(
            source="luqun",
            category=_classify(c.title or "", c.repair_type or ""),
            task=task or "(無說明)",
            person=person,
            work_min=wm,
            remark=c.mgmt_response or c.finance_note or "",
            ragic_id=c.ragic_id,
            detail={
                "報修編號":  c.case_no or "",
                "標題":      c.title or "",
                "報修人姓名": c.reporter_name or "",
                "報修類型":  c.repair_type or "",
                "發生樓層":  c.floor or "",
                "發生時間":  occ,
                "負責單位":  c.responsible_unit or "",
                "花費工時":  f"{c.work_hours:.2f} hr" if c.work_hours else "",
                "處理狀況":  c.status or "",
                "委外費用":  str(int(c.outsource_fee or 0)),
                "維修費用":  str(int(c.maintenance_fee or 0)),
                "總費用":    str(int(c.total_fee or 0)),
                "驗收者":    c.acceptor or "",
                "驗收":      c.accept_status or "",
                "結案人":    c.closer or "",
                "結案時間":  c.completed_at.strftime("%Y/%m/%d") if c.completed_at else "",
                "結案天數":  f"{c.close_days:.1f} 天" if c.close_days else "",
                "扣款事項":  c.deduction_item or "",
                "扣款費用":  str(int(c.deduction_fee or 0)),
                "管理回應":  c.mgmt_response or "",
                "財務備註":  c.finance_note or "",
            },
        ))
    return rows


def _fetch_hotel_pm(db: Session, year: int, month: int, day: int) -> list[dict]:
    """飯店週期保養：batch.period_month + item.scheduled_date"""
    rows = []
    period_month = f"{year}/{month:02d}"
    sched_day    = f"{month:02d}/{day:02d}"

    batches = (
        db.query(PeriodicMaintenanceBatch)
        .filter(PeriodicMaintenanceBatch.period_month == period_month)
        .all()
    )
    if not batches:
        return rows
    batch_map = {b.ragic_id: b for b in batches}
    batch_ids = set(batch_map.keys())

    items = (
        db.query(PeriodicMaintenanceItem)
        .filter(
            PeriodicMaintenanceItem.batch_ragic_id.in_(batch_ids),
            PeriodicMaintenanceItem.scheduled_date == sched_day,
        )
        .all()
    )
    for item in items:
        batch = batch_map.get(item.batch_ragic_id)
        task = " ".join(filter(None, [item.task_name, item.location]))
        wm = None
        if item.ragic_work_minutes and item.ragic_work_minutes > 0:
            wm = int(item.ragic_work_minutes)
        elif item.estimated_minutes and item.estimated_minutes > 0:
            wm = int(item.estimated_minutes)
        est = item.estimated_minutes if item.estimated_minutes else None
        for person in _persons(item.executor_name):
            rows.append(_make_row(
                source="hotel_pm",
                category="例行維護",
                task=task or "(無說明)",
                person=person,
                est_min=est,
                start_time=item.start_time or "",
                end_time=item.end_time or "",
                work_min=wm,
                remark=item.result_note or "",
                ragic_id=item.ragic_id,
                detail={
                    "日誌編號":  (batch.journal_no if batch else "") or "",
                    "保養月份":  (batch.period_month if batch else "") or "",
                    "類別":      item.category or "",
                    "頻率":      item.frequency or "",
                    "區域":      item.location or "",
                    "排定日期":  item.scheduled_date or "",
                    "排定人員":  item.scheduler_name or "",
                    "執行人員":  item.executor_name or "",
                    "完成狀況":  "已完成" if item.is_completed else "未完成",
                    "執行結果":  item.result_note or "",
                    "異常說明":  item.abnormal_note if getattr(item, "abnormal_flag", False) else "",
                },
            ))
    return rows


def _fetch_ihg(db: Session, year: int, month: int, day: int) -> list[dict]:
    """IHG客房保養：maint_date YYYY/MM/DD"""
    rows = []
    date_prefix = _date_str(year, month, day)
    for rec in (
        db.query(IHGRoomMaintenanceMaster)
        .filter(IHGRoomMaintenanceMaster.maint_date == date_prefix)
        .all()
    ):
        person = (rec.assignee_name or "").strip() or "未指定"
        task   = f"IHG客房保養 {rec.room_no}".strip()
        # 工時：raw_json 工時計算（分鐘）；無則固定 30 分鐘
        try:
            raw = rec.get_raw() if hasattr(rec, "get_raw") else {}
            mins_val = raw.get("工時計算", "")
            wm_raw = float(re.search(r"[\d.]+", str(mins_val)).group()) if mins_val and re.search(r"[\d.]+", str(mins_val)) else None
        except Exception:
            wm_raw = None
        wm = round(wm_raw) if wm_raw and wm_raw > 0 else 30
        rows.append(_make_row(
            source="ihg",
            category="例行維護",
            task=task,
            person=person,
            est_min=30,
            work_min=wm,
            remark=rec.notes or "",
            ragic_id=rec.ragic_id,
            detail={
                "房號":     rec.room_no or "",
                "樓層":     rec.floor or "",
                "保養類型": rec.maint_type or "",
                "保養人員": rec.assignee_name or "",
                "複核人員": rec.checker_name or "",
                "保養日期": rec.maint_date or "",
                "完成日期": rec.completion_date or "",
                "狀態":     rec.status or "",
                "備註":     rec.notes or "",
            },
        ))
    return rows


def _fetch_hotel_di(db: Session, year: int, month: int, day: int) -> list[dict]:
    """飯店每日巡檢：hotel_di_inspection_batch"""
    rows = []
    date_str = _date_str(year, month, day)
    for b in (
        db.query(HotelDIBatch)
        .filter(HotelDIBatch.inspection_date == date_str)
        .all()
    ):
        person = (b.inspector_name or "").strip() or "未指定"
        task   = f"{b.sheet_name} 巡檢" if b.sheet_name else "飯店每日巡檢"
        wm     = _parse_wm(b.work_hours)
        rows.append(_make_row(
            source="hotel_di",
            category="每日巡檢",
            task=task,
            person=person,
            start_time=b.start_time or "",
            end_time=b.end_time or "",
            work_min=wm,
            ragic_id=b.ragic_id,
            detail={
                "巡檢表名稱": b.sheet_name or "",
                "巡檢人員":   b.inspector_name or "",
                "巡檢日期":   b.inspection_date or "",
                "開始時間":   b.start_time or "",
                "結束時間":   b.end_time or "",
                "工時":       f"{wm} min" if wm else "",
            },
        ))
    return rows


def _fetch_security(db: Session, year: int, month: int, day: int) -> list[dict]:
    """保全巡檢：security_patrol_batch"""
    rows = []
    date_str = _date_str(year, month, day)
    for b in (
        db.query(SecurityPatrolBatch)
        .filter(SecurityPatrolBatch.inspection_date == date_str)
        .all()
    ):
        person = (b.inspector_name or "").strip() or "未指定"
        task   = f"{b.sheet_name} 保全巡邏" if b.sheet_name else "保全巡邏"
        wm     = _parse_wm(b.work_hours)
        rows.append(_make_row(
            source="security",
            category="每日巡檢",
            task=task,
            person=person,
            start_time=b.start_time or "",
            end_time=b.end_time or "",
            work_min=wm,
            ragic_id=b.ragic_id,
            detail={
                "巡邏表名稱": b.sheet_name or "",
                "巡邏人員":   b.inspector_name or "",
                "巡檢日期":   b.inspection_date or "",
                "開始時間":   b.start_time or "",
                "結束時間":   b.end_time or "",
                "工時":       f"{wm} min" if wm else "",
            },
        ))
    return rows


def _fetch_mall_pm(db: Session, year: int, month: int, day: int) -> list[dict]:
    """商場週期保養：mall_pm_batch + mall_pm_batch_item"""
    rows = []
    period_month = f"{year}/{month:02d}"
    sched_day    = f"{month:02d}/{day:02d}"

    batches = (
        db.query(MallPeriodicMaintenanceBatch)
        .filter(MallPeriodicMaintenanceBatch.period_month == period_month)
        .all()
    )
    if not batches:
        return rows
    batch_map = {b.ragic_id: b for b in batches}
    batch_ids = set(batch_map.keys())

    items = (
        db.query(MallPeriodicMaintenanceItem)
        .filter(
            MallPeriodicMaintenanceItem.batch_ragic_id.in_(batch_ids),
            MallPeriodicMaintenanceItem.scheduled_date == sched_day,
        )
        .all()
    )
    for item in items:
        batch = batch_map.get(item.batch_ragic_id)
        task = " ".join(filter(None, [item.task_name, item.location]))
        est  = item.estimated_minutes if item.estimated_minutes else None
        wm   = int(item.estimated_minutes) if item.estimated_minutes and item.estimated_minutes > 0 else None
        for person in _persons(item.executor_name):
            rows.append(_make_row(
                source="mall_pm",
                category="例行維護",
                task=task or "(無說明)",
                person=person,
                est_min=est,
                start_time=item.start_time or "",
                end_time=item.end_time or "",
                work_min=wm,
                remark=item.result_note or "",
                ragic_id=item.ragic_id,
                detail={
                    "日誌編號":  (batch.journal_no if batch else "") or "",
                    "保養月份":  (batch.period_month if batch else "") or "",
                    "類別":      item.category or "",
                    "頻率":      item.frequency or "",
                    "區域":      item.location or "",
                    "排定日期":  item.scheduled_date or "",
                    "排定人員":  item.scheduler_name or "",
                    "執行人員":  item.executor_name or "",
                    "完成狀況":  "已完成" if item.is_completed else "未完成",
                    "執行結果":  item.result_note or "",
                    "異常說明":  item.abnormal_note if getattr(item, "abnormal_flag", False) else "",
                },
            ))
    return rows


def _fetch_full_bldg_pm(db: Session, year: int, month: int, day: int) -> list[dict]:
    """整棟保養：full_bldg_pm_batch + full_bldg_pm_batch_item"""
    rows = []
    period_month = f"{year}/{month:02d}"
    sched_day    = f"{month:02d}/{day:02d}"

    batches = (
        db.query(FullBldgPMBatch)
        .filter(FullBldgPMBatch.period_month == period_month)
        .all()
    )
    if not batches:
        return rows
    batch_map = {b.ragic_id: b for b in batches}
    batch_ids = set(batch_map.keys())

    items = (
        db.query(FullBldgPMItem)
        .filter(
            FullBldgPMItem.batch_ragic_id.in_(batch_ids),
            FullBldgPMItem.scheduled_date == sched_day,
        )
        .all()
    )
    for item in items:
        batch = batch_map.get(item.batch_ragic_id)
        task = " ".join(filter(None, [item.task_name, item.location]))
        est  = item.estimated_minutes if item.estimated_minutes else None
        wm   = int(item.estimated_minutes) if item.estimated_minutes and item.estimated_minutes > 0 else None
        for person in _persons(item.executor_name):
            rows.append(_make_row(
                source="full_bldg_pm",
                category="例行維護",
                task=task or "(無說明)",
                person=person,
                est_min=est,
                start_time=item.start_time or "",
                end_time=item.end_time or "",
                work_min=wm,
                remark=item.result_note or "",
                ragic_id=item.ragic_id,
                detail={
                    "日誌編號":  (batch.journal_no if batch else "") or "",
                    "保養月份":  (batch.period_month if batch else "") or "",
                    "類別":      item.category or "",
                    "頻率":      item.frequency or "",
                    "區域":      item.location or "",
                    "排定日期":  item.scheduled_date or "",
                    "排定人員":  item.scheduler_name or "",
                    "執行人員":  item.executor_name or "",
                    "完成狀況":  "已完成" if item.is_completed else "未完成",
                    "執行結果":  item.result_note or "",
                    "異常說明":  item.abnormal_note if getattr(item, "abnormal_flag", False) else "",
                },
            ))
    return rows


def _fetch_mall_fi(db: Session, year: int, month: int, day: int) -> list[dict]:
    """商場設施巡檢：mall_fi_inspection_batch"""
    rows = []
    date_str = _date_str(year, month, day)
    for b in (
        db.query(MallFIBatch)
        .filter(MallFIBatch.inspection_date == date_str)
        .all()
    ):
        person = (b.inspector_name or "").strip() or "未指定"
        task   = f"{b.sheet_name} 設施巡檢" if b.sheet_name else "商場設施巡檢"
        wm     = _parse_wm(b.work_hours)
        rows.append(_make_row(
            source="mall_fi",
            category="每日巡檢",
            task=task,
            person=person,
            start_time=b.start_time or "",
            end_time=b.end_time or "",
            work_min=wm,
            ragic_id=b.ragic_id,
            detail={
                "巡檢表名稱": b.sheet_name or "",
                "巡檢人員":   b.inspector_name or "",
                "巡檢日期":   b.inspection_date or "",
                "開始時間":   b.start_time or "",
                "結束時間":   b.end_time or "",
                "工時":       f"{wm} min" if wm else "",
            },
        ))
    return rows


def _fetch_full_bi(db: Session, year: int, month: int, day: int) -> list[dict]:
    """整棟巡檢：B1F / B2F / B4F / RF inspection_batch"""
    rows = []
    date_str = _date_str(year, month, day)
    SHEETS = [
        (B1FInspectionBatch, "B1F 整棟巡檢"),
        (B2FInspectionBatch, "B2F 整棟巡檢"),
        (B4FInspectionBatch, "B4F 整棟巡檢"),
        (RFInspectionBatch,  "RF 整棟巡檢"),
    ]
    for Model, label in SHEETS:
        for b in (
            db.query(Model)
            .filter(Model.inspection_date == date_str)
            .all()
        ):
            person = (b.inspector_name or "").strip() or "未指定"
            wm     = _parse_wm(b.work_hours)
            rows.append(_make_row(
                source="full_bi",
                category="每日巡檢",
                task=label,
                person=person,
                start_time=b.start_time or "",
                end_time=b.end_time or "",
                work_min=wm,
                ragic_id=b.ragic_id,
                detail={
                    "巡檢表名稱": label,
                    "巡檢人員":   b.inspector_name or "",
                    "巡檢日期":   b.inspection_date or "",
                    "開始時間":   b.start_time or "",
                    "結束時間":   b.end_time or "",
                    "工時":       f"{wm} min" if wm else "",
                },
            ))
    return rows


# ── 端點 ─────────────────────────────────────────────────────────────────────

def _build_daily(db: Session, year: int, month: int, day: int) -> dict:
    """內部共用：聚合指定日期的全模組工作記錄，回傳 WorkJournalDaily dict。"""
    all_rows: list[dict] = []
    all_rows += _fetch_dazhi(db, year, month, day)
    all_rows += _fetch_luqun(db, year, month, day)
    all_rows += _fetch_hotel_pm(db, year, month, day)
    all_rows += _fetch_ihg(db, year, month, day)
    all_rows += _fetch_hotel_di(db, year, month, day)
    all_rows += _fetch_security(db, year, month, day)
    all_rows += _fetch_mall_pm(db, year, month, day)
    all_rows += _fetch_full_bldg_pm(db, year, month, day)
    all_rows += _fetch_mall_fi(db, year, month, day)
    all_rows += _fetch_full_bi(db, year, month, day)

    person_map: dict[str, list[dict]] = defaultdict(list)
    for r in all_rows:
        person_map[r["person"]].append(r)

    named = sorted(
        [p for p in person_map if p != "未指定"],
        key=lambda p: sum(r["work_min"] or 0 for r in person_map[p]),
        reverse=True,
    )
    persons_order = named + (["未指定"] if "未指定" in person_map else [])

    def _row_sort_key(r: dict):
        st = r["start_time"]
        has_time = bool(st and re.match(r"^\d{1,2}:\d{2}$", st))
        src_order = SORT_ORDER.index(r["source"]) if r["source"] in SORT_ORDER else 99
        return (0 if has_time else 1, st or "99:99", src_order)

    persons_data = []
    for p in persons_order:
        sorted_rows = sorted(person_map[p], key=_row_sort_key)
        for i, row in enumerate(sorted_rows, 1):
            row["seq"] = i
        persons_data.append({"person": p, "rows": sorted_rows})

    return {
        "date":       _date_str(year, month, day),
        "persons":    persons_data,
        "total_rows": len(all_rows),
    }


@router.get("/daily", summary="工作日誌 — 指定日期所有人員工作記錄")
def get_work_journal_daily(
    year:  int = Query(..., ge=2020, le=2030),
    month: int = Query(..., ge=1,    le=12),
    day:   int = Query(..., ge=1,    le=31),
    db:    Session = Depends(get_db),
):
    """聚合 10 個模組當日工作記錄，依人員分組回傳。"""
    return _build_daily(db, year, month, day)


@router.get("/range", summary="工作日誌 — 日期區間（最多 31 天）")
def get_work_journal_range(
    date_from: str = Query(..., description="起始日期 YYYY-MM-DD"),
    date_to:   str = Query(..., description="結束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """
    聚合 date_from～date_to 區間的工作記錄（最多 31 天）。
    僅回傳有記錄的日期（total_rows > 0）。
    整月查詢：date_from=YYYY-MM-01, date_to=YYYY-MM-{last_day}。
    """
    try:
        start = _date.fromisoformat(date_from)
        end   = _date.fromisoformat(date_to)
    except ValueError:
        return {"date_from": date_from, "date_to": date_to, "days": [], "total_rows": 0}

    if end < start:
        start, end = end, start
    if (end - start).days > 30:
        end = start + timedelta(days=30)

    days = []
    cur  = start
    while cur <= end:
        daily = _build_daily(db, cur.year, cur.month, cur.day)
        if daily["total_rows"] > 0:
            days.append(daily)
        cur += timedelta(days=1)

    return {
        "date_from": start.isoformat(),
        "date_to":   end.isoformat(),
        "days":      days,
        "total_rows": sum(d["total_rows"] for d in days),
    }


@router.get("/export-excel", summary="工作日誌匯出 Excel（每人一 Sheet）")
def export_work_journal_excel(
    date_from: str = Query(..., description="起始日期 YYYY-MM-DD"),
    date_to:   str = Query(..., description="結束日期 YYYY-MM-DD"),
    person:    Optional[str] = Query(None, description="指定人員；不傳則匯出全員"),
    db: Session = Depends(get_db),
):
    """匯出指定日期區間工作日誌為 Excel；全員模式每人一 Sheet，最多 93 天。"""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="openpyxl 未安裝")

    try:
        start = _date.fromisoformat(date_from)
        end   = _date.fromisoformat(date_to)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="日期格式錯誤，需 YYYY-MM-DD")

    if end < start:
        start, end = end, start
    if (end - start).days > 92:
        end = start + timedelta(days=92)

    # ── 收集資料 ───────────────────────────────────────────────────────────────
    days_data = []
    cur = start
    while cur <= end:
        daily = _build_daily(db, cur.year, cur.month, cur.day)
        if daily["total_rows"] > 0:
            days_data.append(daily)
        cur += timedelta(days=1)

    # ── 人員清單 ───────────────────────────────────────────────────────────────
    if person:
        persons_order = [person]
    else:
        seen: set = set()
        persons_order = []
        for daily in days_data:
            for pd in daily["persons"]:
                if pd["person"] not in seen:
                    persons_order.append(pd["person"])
                    seen.add(pd["person"])

    # ── 樣式 ───────────────────────────────────────────────────────────────────
    HEADERS    = ["日期", "模組", "類別", "工作事項", "預估耗時(min)", "起", "迄", "工時(min)", "備註", "回報事項"]
    COL_WIDTHS = [12,     12,    10,    35,          14,              8,   8,   10,       25,   25]
    header_fill = PatternFill(start_color="1B3A5C", end_color="1B3A5C", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=10)
    thin = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    cat_colors = {
        "現場報修": "4BA8E8", "上級交辦": "52C41A",
        "緊急事件": "FF4D4F", "例行維護": "FA8C16", "每日巡檢": "722ED1",
    }
    total_fill = PatternFill(start_color="EBF3FB", end_color="EBF3FB", fill_type="solid")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    for pname in persons_order:
        ws = wb.create_sheet(title=(pname or "未指定")[:31])

        # 標題行
        for ci, h in enumerate(HEADERS, 1):
            cell = ws.cell(row=1, column=ci, value=h)
            cell.fill      = header_fill
            cell.font      = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border    = thin
        ws.row_dimensions[1].height = 20

        row_idx   = 2
        total_min = 0

        for daily in days_data:
            for pd in daily["persons"]:
                if pd["person"] != pname:
                    continue
                for r in pd["rows"]:
                    cat = r.get("category", "")
                    wm  = r.get("work_min")
                    if isinstance(wm, int):
                        total_min += wm
                    row_data = [
                        daily["date"],
                        r.get("source_label", ""),
                        cat,
                        r.get("task", ""),
                        r.get("est_min") or "",
                        r.get("start_time") or "",
                        r.get("end_time") or "",
                        wm if wm is not None else "",
                        r.get("remark", ""),
                        r.get("report", ""),
                    ]
                    for ci, val in enumerate(row_data, 1):
                        cell = ws.cell(row=row_idx, column=ci, value=val)
                        cell.border    = thin
                        cell.alignment = Alignment(vertical="center")
                    if cat in cat_colors:
                        ws.cell(row=row_idx, column=3).font = Font(color=cat_colors[cat], bold=True)
                    if r.get("report"):
                        ws.cell(row=row_idx, column=10).font = Font(color="D46B08")
                    row_idx += 1

        # 合計行
        if row_idx > 2:
            ws.cell(row=row_idx, column=1, value="合計").font = Font(bold=True)
            tc = ws.cell(row=row_idx, column=8, value=total_min)
            tc.font   = Font(bold=True, color="1B3A5C")
            tc.border = thin
            for ci in range(1, len(HEADERS) + 1):
                ws.cell(row=row_idx, column=ci).fill = total_fill

        # 欄寬
        for ci, w in enumerate(COL_WIDTHS, 1):
            ws.column_dimensions[ws.cell(row=1, column=ci).column_letter].width = w

    if not wb.sheetnames:
        ws = wb.create_sheet("無記錄")
        ws.cell(row=1, column=1, value="查詢區間內無工作記錄")

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    label         = f"{date_from}_{date_to}" + (f"_{person}" if person else "")
    filename_safe = f"work_journal_{label}.xlsx"
    filename_cn   = f"工作日誌_{label}.xlsx"

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{filename_safe}\"; "
                f"filename*=UTF-8\'\'{quote(filename_cn)}"
            ),
        },
    )
