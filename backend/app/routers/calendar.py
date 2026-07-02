"""
行事曆聚合 API Router
Prefix: /api/v1/calendar

端點：
  GET  /events           — 聚合所有跨模組事件（依日期範圍 + 類型篩選）
  GET  /today            — 今日摘要 KPI
  GET  /custom           — 自訂事件清單
  POST /custom           — 新增自訂事件
  PUT  /custom/{id}      — 更新自訂事件
  DELETE /custom/{id}    — 刪除自訂事件

事件來源：
  hotel_pm    — 飯店週期保養（pm_batch_item.scheduled_date + pm_batch.period_month）
  mall_pm     — 商場週期保養（mall_pm_batch_item.scheduled_date + mall_pm_batch.period_month）
  pm_plan     — 週期保養預排（pm_plan_item.scheduled_date，來源 Sheet /7、/13、/20 主管排定）
  inspection  — 工務巡檢（b1f/b2f/rf/b4f_inspection_batch.inspection_date）
  approval    — 簽核管理（approvals.submitted_at）
  memo        — 公告牆（memos.created_at）
  custom      — 自訂事件（calendar_custom_events）

注意：附件舊 DB 連線一概不採用，僅使用 Portal 現有 SQLAlchemy Session (get_db)。
"""
import re
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.calendar_event import CalendarCustomEvent
from app.models.periodic_maintenance import PeriodicMaintenanceBatch, PeriodicMaintenanceItem
from app.models.mall_periodic_maintenance import (
    MallPeriodicMaintenanceBatch,
    MallPeriodicMaintenanceItem,
)
from app.models.mall_pm_schedule import MallPMSchedule
from app.models.pm_plan import PmPlanItem
from app.models.full_building_maintenance import FullBldgPMBatch, FullBldgPMItem
from app.models.full_bldg_pm_schedule import FullBldgPMSchedule
from app.models.b1f_inspection import B1FInspectionBatch
from app.models.b2f_inspection import B2FInspectionBatch
from app.models.rf_inspection import RFInspectionBatch
from app.models.b4f_inspection import B4FInspectionBatch
from app.models.approval import Approval
from app.models.memo import Memo
from app.schemas.calendar import (
    CalendarEventOut,
    CalendarEventsResponse,
    TodaySummary,
    CustomEventCreate,
    CustomEventUpdate,
    CustomEventOut,
    EVENT_TYPE_COLORS,
    EVENT_TYPE_LABELS,
    ZONE_VALUES,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


# ─────────────────────────────────────────────────────────────────────────────
# 日期工具
# ─────────────────────────────────────────────────────────────────────────────

def _slash_to_date(s: str) -> Optional[date]:
    """YYYY/MM/DD 或 YYYY-MM-DD → date；失敗回傳 None"""
    if not s:
        return None
    try:
        parts = s.replace("-", "/").split("/")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        return None


def _iso_to_date(s: str) -> Optional[date]:
    """YYYY-MM-DD → date；失敗回傳 None"""
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def _date_to_iso(d: Optional[date]) -> str:
    if d is None:
        return ""
    return d.isoformat()


def _pm_item_full_date(period_month: str, scheduled_date: str) -> Optional[date]:
    """
    飯店/商場週期保養項目的完整日期計算，支援兩種格式：

    格式 A（完整日期，Ragic 直接存 YYYY/MM/DD）：
      scheduled_date = "2026/06/26"  →  直接解析，不需要 period_month
      scheduled_date = "2026-06-26"  →  同上

    格式 B（MM/DD，需搭配 period_month 補年份）：
      period_month   = "2026/04"
      scheduled_date = "04/23"
      → full = "2026/" + "04/23" = "2026/04/23"
    """
    if not scheduled_date:
        return None

    # ── 格式 A：已包含年份（4 位數字開頭）──────────────────────────────────
    if re.match(r'^\d{4}[/-]', scheduled_date):
        return _slash_to_date(scheduled_date)

    # ── 格式 B：MM/DD，需要 period_month 補年份 ──────────────────────────────
    if not period_month:
        return None
    try:
        full = period_month[:5] + scheduled_date   # "2026/" + "06/26"
        return _slash_to_date(full)
    except Exception:
        return None


def _should_include(event_type: str, types_filter: Optional[str]) -> bool:
    """判斷是否需要收集此類型事件"""
    if not types_filter:
        return True
    return event_type in [t.strip() for t in types_filter.split(",")]


def _clean_title(title: str) -> str:
    """去掉標題開頭的 [xxx] 前綴（如 "[商場保養] "、"[季保] "），取得純任務名稱。
    用於跨事件類型比對是否為同一個保養任務（見 pm_plan 與執行類事件去重邏輯）。"""
    return re.sub(r'^\[.*?\]\s*', '', title).strip()


def _pm_plan_batch_id(ragic_id: str) -> int:
    """從 pm_plan_item.ragic_id（格式 "{sheet_no}_{batch_id}_{row_key}"）解析出 batch_id，
    用於同一任務跨批次重複時判斷哪個批次較新（batch_id 越大越新）。解析失敗回傳 0。"""
    parts = ragic_id.split("_")
    if len(parts) >= 2:
        try:
            return int(parts[1])
        except ValueError:
            return 0
    return 0


def _safe_batch_num(ragic_id: str) -> int:
    """將批次 ragic_id 轉為整數以比較新舊（batch_id 越大越新）。解析失敗回傳 0。
    用於 hotel_pm/mall_pm/full_pm 批次明細跨批次重複時的去重判斷。"""
    try:
        return int(ragic_id)
    except (ValueError, TypeError):
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# 各模組事件收集函式
# ─────────────────────────────────────────────────────────────────────────────

def _collect_hotel_pm(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集飯店週期保養事件（pm_batch + pm_batch_item）"""
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["hotel_pm"]
    label = EVENT_TYPE_LABELS["hotel_pm"]

    # 以 period_month 範圍篩選批次（月份字串 "2026/04" 可直接比較）
    start_month = start.strftime("%Y/%m")
    end_month   = end.strftime("%Y/%m")

    batches = db.query(PeriodicMaintenanceBatch).filter(
        PeriodicMaintenanceBatch.period_month >= start_month,
        PeriodicMaintenanceBatch.period_month <= end_month,
    ).all()

    # ── 去重（2026-07-01 修正）─────────────────────────────────────────────────
    # 新批次常以複製舊批次建立，若某任務「排定日期」未隨批次更新／清除，
    # 查詢範圍跨批次月份時，舊批次與新批次會各自產生一筆相同任務同一天的事件。
    # 以 (task_name, item_date, zone) 為 key，只保留批次 ID 較大（較新）的一筆。
    candidates: dict = {}
    for batch in batches:
        batch_num = _safe_batch_num(batch.ragic_id)
        items = db.query(PeriodicMaintenanceItem).filter(
            PeriodicMaintenanceItem.batch_ragic_id == batch.ragic_id,
            PeriodicMaintenanceItem.scheduled_date != "",
        ).all()

        for item in items:
            item_date = _pm_item_full_date(batch.period_month, item.scheduled_date)
            if not item_date or not (start <= item_date <= end):
                continue

            key = (item.task_name, item_date, "飯店")
            existing = candidates.get(key)
            if existing is None or batch_num > existing[0]:
                candidates[key] = (batch_num, batch, item, item_date)

    for batch_num, batch, item, item_date in candidates.values():
        if item.is_completed:
            status, status_label = "completed", "已完成"
        elif item.abnormal_flag:
            status, status_label = "abnormal", "異常"
        else:
            status, status_label = "pending", "待執行"

        events.append(CalendarEventOut(
            id           = f"hotel_pm_{item.ragic_id}",
            title        = f"[飯店保養] {item.task_name}",
            start        = _date_to_iso(item_date),
            all_day      = True,
            event_type   = "hotel_pm",
            module_label = label,
            source_id    = item.ragic_id,
            status       = status,
            status_label = status_label,
            responsible  = item.executor_name or item.scheduler_name,
            description  = f"{item.category} | {item.location}",
            deep_link    = "/hotel/periodic-maintenance",
            color        = color,
            zone         = "飯店",
            ragic_url    = f"https://ap12.ragic.com/soutlet001/periodic-maintenance/6/{batch.ragic_id}",
        ))
    return events


def _collect_mall_pm(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集商場週期保養事件（mall_pm_batch + mall_pm_batch_item）"""
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["mall_pm"]
    label = EVENT_TYPE_LABELS["mall_pm"]

    start_month = start.strftime("%Y/%m")
    end_month   = end.strftime("%Y/%m")

    batches = db.query(MallPeriodicMaintenanceBatch).filter(
        MallPeriodicMaintenanceBatch.period_month >= start_month,
        MallPeriodicMaintenanceBatch.period_month <= end_month,
    ).all()

    # ── 去重（2026-07-01 修正，理由同 _collect_hotel_pm）────────────────────────
    candidates: dict = {}
    for batch in batches:
        batch_num = _safe_batch_num(batch.ragic_id)
        items = db.query(MallPeriodicMaintenanceItem).filter(
            MallPeriodicMaintenanceItem.batch_ragic_id == batch.ragic_id,
            MallPeriodicMaintenanceItem.scheduled_date != "",
        ).all()

        for item in items:
            item_date = _pm_item_full_date(batch.period_month, item.scheduled_date)
            if not item_date or not (start <= item_date <= end):
                continue

            key = (item.task_name, item_date, "商場")
            existing = candidates.get(key)
            if existing is None or batch_num > existing[0]:
                candidates[key] = (batch_num, batch, item, item_date)

    for batch_num, batch, item, item_date in candidates.values():
        if item.is_completed:
            status, status_label = "completed", "已完成"
        elif item.abnormal_flag:
            status, status_label = "abnormal", "異常"
        else:
            status, status_label = "pending", "待執行"

        events.append(CalendarEventOut(
            id           = f"mall_pm_{item.ragic_id}",
            title        = f"[商場保養] {item.task_name}",
            start        = _date_to_iso(item_date),
            all_day      = True,
            event_type   = "mall_pm",
            module_label = label,
            source_id    = item.ragic_id,
            status       = status,
            status_label = status_label,
            responsible  = item.executor_name or item.scheduler_name,
            description  = f"{item.category} | {item.location}",
            deep_link    = "/mall/periodic-maintenance",
            color        = color,
            zone         = "商場",
            ragic_url    = f"https://ap12.ragic.com/soutlet001/periodic-maintenance/18/{batch.ragic_id}",
        ))
    return events


def _collect_mall_pm_schedule(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """
    收集商場 Portal 自有排程事件（mall_pm_schedule.scheduled_date）。

    行事曆整合邏輯：
      - scheduled_date 格式 "MM/DD"；搭配 year_month[:5]（"YYYY/"）組出完整日期
      - 只取落在 [start, end] 日期範圍內的記錄
      - 與 _collect_mall_pm（Ragic 批次）合併時，以本函式事件為優先（相同 title+date 去重）
    """
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["mall_pm"]
    label = EVENT_TYPE_LABELS["mall_pm"]

    recs = (
        db.query(MallPMSchedule)
        .filter(
            MallPMSchedule.scheduled_date != "",
        )
        .all()
    )

    # ── 去重（2026-07-01 修正）─────────────────────────────────────────────────
    # 「產生本月排程」對於只有「執行月份」（無明確排定日期）的項目，會在每個
    # 月份都各自產生一筆「下次執行日」預告列（year_month 不同，但 scheduled_date
    # 算出來是同一天），導致同一任務在行事曆同一天重複顯示多次。這裡僅在
    # 行事曆聚合層做去重（同一 item_ragic_id + 同一計算後日期只取一筆），
    # 不影響「本月排程」列表頁本身的資料與既有預告機制。
    seen_keys: set = set()

    for rec in recs:
        item_date = _pm_item_full_date(rec.year_month, rec.scheduled_date)
        if not item_date or not (start <= item_date <= end):
            continue

        dedup_key = (rec.item_ragic_id, item_date)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        if rec.is_completed or (rec.start_time and rec.end_time):
            status, status_label = "completed", "已完成"
        elif rec.abnormal_flag:
            status, status_label = "abnormal", "異常"
        elif rec.start_time:
            status, status_label = "in_progress", "進行中"
        else:
            status, status_label = "pending", "待執行"

        events.append(CalendarEventOut(
            id           = f"mall_pm_sched_{rec.id}",
            title        = f"[商場保養] {rec.task_name}",
            start        = _date_to_iso(item_date),
            all_day      = True,
            event_type   = "mall_pm",
            module_label = label,
            source_id    = str(rec.id),
            status       = status,
            status_label = status_label,
            responsible  = rec.executor_name or "",
            description  = f"{rec.category} | {rec.location} | {rec.frequency}",
            deep_link    = "/mall/periodic-maintenance",
            color        = color,
            zone         = "商場",
        ))

    return events


def _collect_full_bldg_pm_schedule(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """
    收集全棟 Portal 排程事件（full_bldg_pm_schedule.scheduled_date）。
    與 _collect_full_bldg_pm（Ragic 批次）合併時，以本函式事件為優先（相同 title+date 去重）。
    """
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["full_pm"]
    label = EVENT_TYPE_LABELS["full_pm"]

    recs = (
        db.query(FullBldgPMSchedule)
        .filter(FullBldgPMSchedule.scheduled_date != "")
        .all()
    )

    # ── 去重（2026-07-01 修正，理由同商場 PM，見 _collect_mall_pm_schedule）──────
    seen_keys: set = set()

    for rec in recs:
        item_date = _pm_item_full_date(rec.year_month, rec.scheduled_date)
        if not item_date or not (start <= item_date <= end):
            continue

        dedup_key = (rec.item_ragic_id, item_date)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        if rec.is_completed or (rec.start_time and rec.end_time):
            status, status_label = "completed", "已完成"
        elif rec.abnormal_flag:
            status, status_label = "abnormal", "異常"
        elif rec.start_time:
            status, status_label = "in_progress", "進行中"
        else:
            status, status_label = "pending", "待執行"

        events.append(CalendarEventOut(
            id           = f"full_pm_sched_{rec.id}",
            title        = f"[全棟維護] {rec.task_name}",
            start        = _date_to_iso(item_date),
            all_day      = True,
            event_type   = "full_pm",
            module_label = label,
            source_id    = str(rec.id),
            status       = status,
            status_label = status_label,
            responsible  = rec.executor_name or "",
            description  = f"{rec.category} | {rec.location} | {rec.frequency}",
            deep_link    = "/full-building/periodic-maintenance",
            color        = color,
            zone         = "公區",
        ))

    return events


def _collect_full_bldg_pm(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集全棟例行維護事件（full_bldg_pm_batch + full_bldg_pm_batch_item）"""
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["full_pm"]
    label = EVENT_TYPE_LABELS["full_pm"]

    start_month = start.strftime("%Y/%m")
    end_month   = end.strftime("%Y/%m")

    batches = db.query(FullBldgPMBatch).filter(
        FullBldgPMBatch.period_month >= start_month,
        FullBldgPMBatch.period_month <= end_month,
    ).all()

    # ── 去重（2026-07-01 修正，理由同 _collect_hotel_pm）────────────────────────
    # 新批次（如「棟週保202607-001」）常以複製上月批次建立，若某任務「排定日期」
    # 未隨批次更新／清除（如同一天在 6月批次與 7月批次都存在），查詢範圍跨批次
    # 月份時會各自產生一筆重複事件。以 (task_name, item_date, zone) 為 key，
    # 只保留批次 ID 較大（較新）的一筆。
    candidates: dict = {}
    for batch in batches:
        batch_num = _safe_batch_num(batch.ragic_id)
        items = db.query(FullBldgPMItem).filter(
            FullBldgPMItem.batch_ragic_id == batch.ragic_id,
            FullBldgPMItem.scheduled_date != "",
        ).all()

        for item in items:
            item_date = _pm_item_full_date(batch.period_month, item.scheduled_date)
            if not item_date or not (start <= item_date <= end):
                continue

            key = (item.task_name, item_date, "公區")
            existing = candidates.get(key)
            if existing is None or batch_num > existing[0]:
                candidates[key] = (batch_num, batch, item, item_date)

    for batch_num, batch, item, item_date in candidates.values():
        if item.is_completed:
            status, status_label = "completed", "已完成"
        elif item.abnormal_flag:
            status, status_label = "abnormal", "異常"
        else:
            status, status_label = "pending", "待執行"

        events.append(CalendarEventOut(
            id           = f"full_pm_{item.ragic_id}",
            title        = f"[全棟維護] {item.task_name}",
            start        = _date_to_iso(item_date),
            all_day      = True,
            event_type   = "full_pm",
            module_label = label,
            source_id    = item.ragic_id,
            status       = status,
            status_label = status_label,
            responsible  = item.executor_name or item.scheduler_name,
            description  = f"{item.category} | {item.location}",
            deep_link    = "/mall/full-building-maintenance",
            color        = color,
            zone         = "公區",
            ragic_url    = f"https://ap12.ragic.com/soutlet001/periodic-maintenance/21/{batch.ragic_id}",
        ))
    return events


def _collect_pm_plan(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集週期保養預排事件（pm_plan_item，來源 Sheet /7 /13 /20 主管排定）"""
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["pm_plan"]
    label = EVENT_TYPE_LABELS["pm_plan"]

    start_iso = _date_to_iso(start)
    end_iso   = _date_to_iso(end)

    items = db.query(PmPlanItem).filter(
        PmPlanItem.scheduled_date >= start_iso,
        PmPlanItem.scheduled_date <= end_iso,
        PmPlanItem.scheduled_date != "",
    ).all()

    # ── 去重（2026-07-01 修正）─────────────────────────────────────────────────
    # 同一張 Sheet 內，若新批次是複製舊批次建立、舊批次未清除，會造成同一任務
    # 同一天在兩個批次各出現一次（診斷資料證實：33 組重複皆為同 Sheet 跨批次
    # 完全重覆）。僅保留同組 (source_sheet, scheduled_date, task_name) 中
    # batch_id 較大（較新）的一筆，避免行事曆重複顯示。
    dedup_map: dict = {}
    for _item in items:
        _key = (_item.source_sheet, _item.scheduled_date, _item.task_name)
        _existing = dedup_map.get(_key)
        if _existing is None or _pm_plan_batch_id(_item.ragic_id) > _pm_plan_batch_id(_existing.ragic_id):
            dedup_map[_key] = _item
    items = list(dedup_map.values())

    # 頻率 → 中文顯示
    FREQ_TAG: dict = {
        "年":   "年保",
        "半年": "半年保",
        "季":   "季保",
        "月":   "月保",
    }

    for item in items:
        item_date = _iso_to_date(item.scheduled_date)
        if not item_date:
            continue

        freq_tag   = FREQ_TAG.get(item.frequency, item.frequency)
        title_text = f"[{freq_tag}] {item.task_name}" if freq_tag else f"[預排] {item.task_name}"
        src_label  = item.source_label or ""   # 飯店/商場/全棟

        # deep_link：指向對應的週期保養模組
        DEEP_LINK_MAP = {
            "飯店": "/hotel/periodic-maintenance",
            "商場": "/mall/periodic-maintenance",
            "全棟": "/hotel/full-building-maintenance",
        }
        deep_link = DEEP_LINK_MAP.get(src_label, "/hotel/periodic-maintenance")

        # zone：依主管排定來源決定
        ZONE_MAP = {"飯店": "飯店", "商場": "商場", "全棟": "公區"}
        item_zone = ZONE_MAP.get(src_label, "其它")

        events.append(CalendarEventOut(
            id           = f"pm_plan_{item.ragic_id}",
            title        = title_text,
            start        = _date_to_iso(item_date),
            all_day      = True,
            event_type   = "pm_plan",
            module_label = f"{label}（{src_label}）" if src_label else label,
            source_id    = item.ragic_id,
            status       = "pending",
            status_label = "預排",
            responsible  = item.scheduler_name,
            description  = (
                f"{item.category}｜{item.location}｜頻率：{item.frequency}"
                if (item.category or item.location)
                else f"頻率：{item.frequency}"
            ),
            deep_link    = deep_link,
            color        = color,
            zone         = item_zone,
            ragic_url    = item.ragic_url or "",
        ))

    return events


def _collect_inspection(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集工務巡檢事件（B1F / B2F / RF / B4F）"""
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["inspection"]
    label = EVENT_TYPE_LABELS["inspection"]

    start_str = start.strftime("%Y/%m/%d")
    end_str   = end.strftime("%Y/%m/%d")

    INSPECTION_CONFIGS = [
        ("b1f", "B1F 工務巡檢", B1FInspectionBatch, "/mall/b1f-inspection"),
        ("b2f", "B2F 工務巡檢", B2FInspectionBatch, "/mall/b2f-inspection"),
        ("rf",  "RF 工務巡檢",  RFInspectionBatch,  "/mall/rf-inspection"),
        ("b4f", "B4F 工務巡檢", B4FInspectionBatch, "/mall/b4f-inspection"),
    ]

    for floor_key, floor_label, BatchModel, deep_link in INSPECTION_CONFIGS:
        try:
            batches = db.query(BatchModel).filter(
                BatchModel.inspection_date >= start_str,
                BatchModel.inspection_date <= end_str,
            ).all()
        except Exception:
            continue

        seen_dates: set = set()
        for b in batches:
            if b.inspection_date in seen_dates:
                continue
            seen_dates.add(b.inspection_date)

            item_date = _slash_to_date(b.inspection_date)
            if not item_date:
                continue

            events.append(CalendarEventOut(
                id           = f"inspection_{floor_key}_{b.inspection_date.replace('/', '')}",
                title        = f"[工務巡檢] {floor_label}",
                start        = _date_to_iso(item_date),
                all_day      = True,
                event_type   = "inspection",
                module_label = label,
                source_id    = b.ragic_id,
                status       = "completed",
                status_label = "已巡檢",
                responsible  = getattr(b, "inspector_name", "") or "",
                description  = f"{floor_label}，巡檢日期：{b.inspection_date}",
                deep_link    = deep_link,
                color        = color,
                zone         = "商場",
            ))
    return events


def _collect_approvals(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集簽核事件（approvals.submitted_at）"""
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["approval"]
    label = EVENT_TYPE_LABELS["approval"]

    start_dt = datetime(start.year, start.month, start.day, 0, 0, 0)
    end_dt   = datetime(end.year,   end.month,   end.day,   23, 59, 59)

    approvals = db.query(Approval).filter(
        Approval.submitted_at >= start_dt,
        Approval.submitted_at <= end_dt,
    ).all()

    STATUS_MAP = {
        "pending":  ("pending",   "待簽核"),
        "approved": ("completed", "已核准"),
        "rejected": ("abnormal",  "已退回"),
    }

    for ap in approvals:
        status, slabel = STATUS_MAP.get(ap.status, ("pending", ap.status))
        start_iso = (
            ap.submitted_at.strftime("%Y-%m-%d")
            if ap.submitted_at else _date_to_iso(start)
        )

        events.append(CalendarEventOut(
            id           = f"approval_{ap.id}",
            title        = f"[簽核] {ap.subject}",
            start        = start_iso,
            all_day      = True,
            event_type   = "approval",
            module_label = label,
            source_id    = ap.id,
            status       = status,
            status_label = slabel,
            responsible  = ap.requester,
            description  = f"申請人：{ap.requester}｜部門：{ap.requester_dept}",
            deep_link    = f"/approvals/{ap.id}",
            color        = color,
            zone         = "其它",
        ))
    return events


def _collect_memos(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集公告牆事件（memos.created_at）"""
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["memo"]
    label = EVENT_TYPE_LABELS["memo"]

    start_dt = datetime(start.year, start.month, start.day, 0, 0, 0)
    end_dt   = datetime(end.year,   end.month,   end.day,   23, 59, 59)

    memos = db.query(Memo).filter(
        Memo.created_at >= start_dt,
        Memo.created_at <= end_dt,
    ).all()

    # ── 去重（2026-07-02 修正）───────────────────────────────────────────────
    # 系統自動來源的公告（如合約到期提醒 source='contract_expiry'）設計上每個
    # 來源記錄（source_id）同一天只會產生一筆，但排程若曾經歷背景 process 重複
    # 執行（競態條件，兩邊都在對方 commit 前查到「尚無記錄」），仍可能寫入 2 筆
    # 內容相同的 memo。僅針對「有明確 source + source_id」的系統公告，以
    # (source, source_id, 日期) 去重，保留最早建立的一筆；使用者手動發布的公告
    # （source 為空）不受影響，一律照常全部顯示。
    dedup_map: dict = {}
    plain_memos: list = []
    for _m in memos:
        if _m.source and _m.source_id:
            _day_key = _m.created_at.strftime("%Y-%m-%d") if _m.created_at else ""
            _key = (_m.source, _m.source_id, _day_key)
            _existing = dedup_map.get(_key)
            if _existing is None or (
                _m.created_at and _existing.created_at and _m.created_at < _existing.created_at
            ):
                dedup_map[_key] = _m
        else:
            plain_memos.append(_m)
    memos = list(dedup_map.values()) + plain_memos

    for memo in memos:
        start_iso = (
            memo.created_at.strftime("%Y-%m-%d")
            if memo.created_at else _date_to_iso(start)
        )
        events.append(CalendarEventOut(
            id           = f"memo_{memo.id}",
            title        = f"[公告] {memo.title}",
            start        = start_iso,
            all_day      = True,
            event_type   = "memo",
            module_label = label,
            source_id    = memo.id,
            status       = "completed",
            status_label = "已發布",
            responsible  = memo.author,
            description  = f"發文者：{memo.author}",
            deep_link    = f"/memos/{memo.id}",
            color        = color,
            zone         = "其它",
        ))
    return events


def _collect_custom(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集使用者自訂事件（calendar_custom_events）"""
    events: List[CalendarEventOut] = []
    label = EVENT_TYPE_LABELS["custom"]

    start_iso = _date_to_iso(start)
    end_iso   = _date_to_iso(end)

    customs = db.query(CalendarCustomEvent).filter(
        CalendarCustomEvent.start_date >= start_iso,
        CalendarCustomEvent.start_date <= end_iso,
    ).all()

    for ev in customs:
        events.append(CalendarEventOut(
            id           = f"custom_{ev.id}",
            title        = ev.title,
            start        = ev.start_date,
            end          = ev.end_date or None,
            all_day      = ev.all_day,
            event_type   = "custom",
            module_label = label,
            source_id    = ev.id,
            status       = "pending",
            status_label = "自訂",
            responsible  = ev.responsible,
            description  = ev.description,
            deep_link    = "",
            color        = ev.color or EVENT_TYPE_COLORS["custom"],
            zone         = getattr(ev, "zone", "其它") or "其它",
        ))
    return events


# ─────────────────────────────────────────────────────────────────────────────
# /events — 聚合查詢
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/events", summary="取得行事曆聚合事件", response_model=CalendarEventsResponse)
def get_calendar_events(
    start:  str           = Query(..., description="查詢起始日期 YYYY-MM-DD"),
    end:    str           = Query(..., description="查詢結束日期 YYYY-MM-DD"),
    types:  Optional[str] = Query(
        None,
        description="事件類型篩選，逗號分隔：hotel_pm,mall_pm,full_pm,pm_plan,inspection,approval,memo,custom"
    ),
    db: Session = Depends(get_db),
):
    start_date = _iso_to_date(start)
    end_date   = _iso_to_date(end)

    if not start_date or not end_date:
        return CalendarEventsResponse(events=[], total=0)

    all_events: List[CalendarEventOut] = []

    # ── 週期預排（pm_plan）優先於執行類事件（hotel_pm/mall_pm/full_pm）────────
    # pm_plan 來源 Sheet 7/13/20（主管排定）與執行類 Sheet 6/8、18、21（同仁執行）
    # 追蹤的常是同一個保養任務；同一任務同一天兩邊都有記錄時，行事曆固定以
    # pm_plan（主管排定）為準，避免同一任務重複顯示（2026-07-01 修正，飯店/商場/
    # 全棟三個區域一併處理）。若使用者在類型篩選中關閉「週期預排」，則不進行
    # 此去重（pm_plan_keys 會是空集合）。
    pm_plan_events: List[CalendarEventOut] = []
    if _should_include("pm_plan", types):
        pm_plan_events = _collect_pm_plan(db, start_date, end_date)
        all_events.extend(pm_plan_events)

    pm_plan_keys = {
        (_clean_title(e.title), e.start, e.zone) for e in pm_plan_events
    }

    if _should_include("hotel_pm",   types):
        hotel_events = _collect_hotel_pm(db, start_date, end_date)
        hotel_events = [
            e for e in hotel_events
            if (_clean_title(e.title), e.start, e.zone) not in pm_plan_keys
        ]
        all_events.extend(hotel_events)
    if _should_include("mall_pm",    types):
        # 合併 Ragic 批次事件 + Portal 排程事件；Portal 排程優先（相同 title+date 去重）
        batch_events  = _collect_mall_pm(db, start_date, end_date)
        sched_events  = _collect_mall_pm_schedule(db, start_date, end_date)
        sched_keys    = {(e.title, e.start) for e in sched_events}
        merged_mall   = [e for e in batch_events if (e.title, e.start) not in sched_keys]
        merged_mall  += sched_events
        merged_mall   = [
            e for e in merged_mall
            if (_clean_title(e.title), e.start, e.zone) not in pm_plan_keys
        ]
        all_events.extend(merged_mall)
    if _should_include("full_pm",    types):
        # 合併 Ragic 批次事件 + Portal 排程事件；Portal 排程優先（相同 title+date 去重）
        full_batch_events = _collect_full_bldg_pm(db, start_date, end_date)
        full_sched_events = _collect_full_bldg_pm_schedule(db, start_date, end_date)
        full_sched_keys   = {(e.title, e.start) for e in full_sched_events}
        merged_full       = [e for e in full_batch_events if (e.title, e.start) not in full_sched_keys]
        merged_full      += full_sched_events
        merged_full       = [
            e for e in merged_full
            if (_clean_title(e.title), e.start, e.zone) not in pm_plan_keys
        ]
        all_events.extend(merged_full)
    if _should_include("inspection", types):
        all_events.extend(_collect_inspection(db, start_date, end_date))
    if _should_include("approval",   types):
        all_events.extend(_collect_approvals(db, start_date, end_date))
    if _should_include("memo",       types):
        all_events.extend(_collect_memos(db, start_date, end_date))
    if _should_include("custom",     types):
        all_events.extend(_collect_custom(db, start_date, end_date))

    all_events.sort(key=lambda e: e.start)
    return CalendarEventsResponse(events=all_events, total=len(all_events))


# ─────────────────────────────────────────────────────────────────────────────
# /today — 今日摘要 KPI
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/today", summary="取得今日摘要 KPI", response_model=TodaySummary)
def get_today_summary(db: Session = Depends(get_db)):
    today = date.today()
    today_iso = _date_to_iso(today)

    result = get_calendar_events(
        start=today_iso,
        end=today_iso,
        types=None,
        db=db,
    )

    ev_list = result.events
    total   = len(ev_list)

    pending_count  = sum(1 for e in ev_list if e.status == "pending")
    abnormal_count = sum(1 for e in ev_list if e.status == "abnormal")
    overdue_count  = sum(1 for e in ev_list if e.status == "overdue")

    # 全系統待簽核件數（不限日期）
    approval_pending = db.query(Approval).filter(Approval.status == "pending").count()

    high_risk = abnormal_count + overdue_count

    # 事件類型分布
    type_counts: dict = {}
    for e in ev_list:
        type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1

    return TodaySummary(
        today            = today.strftime("%Y/%m/%d"),
        total_events     = total,
        pending_count    = pending_count,
        abnormal_count   = abnormal_count,
        overdue_count    = overdue_count,
        approval_pending = approval_pending,
        high_risk_count  = high_risk,
        event_by_type    = type_counts,
    )


# ─────────────────────────────────────────────────────────────────────────────
# /custom — 自訂事件 CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/custom", summary="取得自訂事件清單", response_model=List[CustomEventOut])
def list_custom_events(
    start: Optional[str] = Query(None, description="起始日期 YYYY-MM-DD"),
    end:   Optional[str] = Query(None, description="結束日期 YYYY-MM-DD"),
    db:    Session = Depends(get_db),
):
    q = db.query(CalendarCustomEvent)
    if start:
        q = q.filter(CalendarCustomEvent.start_date >= start)
    if end:
        q = q.filter(CalendarCustomEvent.start_date <= end)
    return q.order_by(CalendarCustomEvent.start_date).all()


@router.post("/custom", summary="新增自訂事件", status_code=201, response_model=CustomEventOut)
def create_custom_event(
    payload: CustomEventCreate,
    db: Session = Depends(get_db),
):
    zone_val = payload.zone if payload.zone in ZONE_VALUES else "其它"
    ev = CalendarCustomEvent(
        title       = payload.title,
        description = payload.description,
        start_date  = payload.start_date,
        end_date    = payload.end_date or "",
        all_day     = payload.all_day,
        start_time  = payload.start_time or "",
        end_time    = payload.end_time or "",
        color       = payload.color or EVENT_TYPE_COLORS["custom"],
        zone        = zone_val,
        responsible = payload.responsible or "",
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


@router.put("/custom/{event_id}", summary="更新自訂事件", response_model=CustomEventOut)
def update_custom_event(
    event_id: str,
    payload:  CustomEventUpdate,
    db: Session = Depends(get_db),
):
    ev = db.query(CalendarCustomEvent).filter(
        CalendarCustomEvent.id == event_id
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="事件不存在")

    for field, val in payload.dict(exclude_unset=True).items():
        setattr(ev, field, val)
    db.commit()
    db.refresh(ev)
    return ev


@router.delete("/custom/{event_id}", summary="刪除自訂事件", status_code=204)
def delete_custom_event(
    event_id: str,
    db: Session = Depends(get_db),
):
    ev = db.query(CalendarCustomEvent).filter(
        CalendarCustomEvent.id == event_id
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="事件不存在")
    db.delete(ev)
    db.commit()
