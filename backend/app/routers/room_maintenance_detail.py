"""
客房保養明細 API Router
Prefix: /api/v1/room-maintenance-detail

端點：
  POST /sync                    — 手動從 Ragic 同步
  GET  /                        — 明細列表（支援篩選 + 分頁，含日期區間）
  GET  /summary                 — 總表：全房間清單 × 保養狀態（含日期區間聚合、工時加總）
  GET  /staff-hours             — 人員工時月報表（人員 × 月份 pivot，分鐘→小時）
  GET  /room-history/{room_no}  — 單一房間保養歷史（月曆摘要 + 全記錄）
  GET  /{record_id}             — 單筆
"""
import re
from collections import defaultdict
from datetime import date
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.room import Room
from app.models.room_maintenance_detail import RoomMaintenanceDetailRecord
from app.services.room_maintenance_detail_sync import sync_from_ragic

router = APIRouter()

# ── 常數：所有檢查項目欄位名稱 ────────────────────────────────────────────────
CHECK_FIELDS = [
    ("chk_door",      "房門"),
    ("chk_fire",      "消防"),
    ("chk_equipment", "設備"),
    ("chk_furniture", "傢俱"),
    ("chk_light",     "客房燈/電源"),
    ("chk_window",    "客房窗"),
    ("chk_sink",      "面盆/台面"),
    ("chk_toilet",    "浴厠"),
    ("chk_bath",      "浴間"),
    ("chk_surface",   "天地壁"),
    ("chk_ac",        "客房空調"),
    ("chk_balcony",   "陽台"),
]


def _parse_minutes(val: str) -> float:
    """解析 '22.00  分鐘' → 22.0"""
    if not val:
        return 0.0
    m = re.search(r"[\d.]+", str(val))
    return float(m.group()) if m else 0.0


def _record_to_dict(r: RoomMaintenanceDetailRecord) -> dict:
    return {
        "ragic_id":       r.ragic_id,
        "maintain_date":  r.maintain_date,
        "staff_name":     r.staff_name,
        "room_no":        r.room_no,
        "work_hours":     r.work_hours,
        "created_date":   r.created_date,
        "chk_door":       r.chk_door,
        "chk_fire":       r.chk_fire,
        "chk_equipment":  r.chk_equipment,
        "chk_furniture":  r.chk_furniture,
        "chk_light":      r.chk_light,
        "chk_window":     r.chk_window,
        "chk_sink":       r.chk_sink,
        "chk_toilet":     r.chk_toilet,
        "chk_bath":       r.chk_bath,
        "chk_surface":    r.chk_surface,
        "chk_ac":         r.chk_ac,
        "chk_balcony":    r.chk_balcony,
        "synced_at":      r.synced_at.isoformat() if r.synced_at else None,
    }


# ── POST /sync ────────────────────────────────────────────────────────────────
@router.post("/sync", summary="從 Ragic 同步客房保養明細資料到本地 DB（背景執行）")
async def sync_records(background_tasks: BackgroundTasks):
    """觸發背景同步：Ragic → SQLite，立即回傳，不阻塞畫面"""
    background_tasks.add_task(sync_from_ragic)
    return {"success": True, "message": "同步已在背景啟動"}


# ── GET /summary — 總表（全房間 + 日期區間）───────────────────────────────────
@router.get("/summary", summary="客房保養總表（全房間清單，含未保養灰底資料）")
async def get_summary(
    date_from: Optional[str] = Query(None, description="起始日期 YYYY/MM/DD"),
    date_to:   Optional[str] = Query(None, description="結束日期 YYYY/MM/DD"),
    db: Session = Depends(get_db),
):
    """
    回傳 Room 主檔的所有房間，並標記其在指定日期區間的保養狀態：
    - serviced=True：有保養記錄，顯示最近一筆的明細 + 檢查項目
    - serviced=False：無保養記錄，以灰底呈現

    stats：
      total_records       保養記錄總數（區間內所有筆數）
      total_abnormal      異常項次總數（區間內所有記錄的 X 加總）
      fully_ok_count      全項目正常房間數（最近一筆全 V 的房間數）
      work_hours_total    工時數（區間內所有記錄工時分鐘加總）
      unserviced_count    未保養房間數
    """
    # ── 取得日期區間內的保養記錄 ────────────────────────────────────────────
    q = db.query(RoomMaintenanceDetailRecord)
    if date_from:
        q = q.filter(RoomMaintenanceDetailRecord.maintain_date >= date_from)
    if date_to:
        q = q.filter(RoomMaintenanceDetailRecord.maintain_date <= date_to)
    records = q.all()

    # ── 依房號分組 ──────────────────────────────────────────────────────────
    room_records: dict[str, list[RoomMaintenanceDetailRecord]] = defaultdict(list)
    for r in records:
        room_records[r.room_no].append(r)

    # ── 全域統計（針對所有記錄） ────────────────────────────────────────────
    total_records   = len(records)
    total_abnormal  = 0
    work_hours_total = 0.0
    for r in records:
        for field_name, _ in CHECK_FIELDS:
            if getattr(r, field_name, "").upper() == "X":
                total_abnormal += 1
        work_hours_total += _parse_minutes(r.work_hours)

    # ── 取得 Room 主檔（依樓層 → 房號排序）────────────────────────────────
    all_rooms = (
        db.query(Room)
        .order_by(Room.floor_no.asc(), Room.room_no.asc())
        .all()
    )

    # ── 逐房間組裝摘要 ──────────────────────────────────────────────────────
    summary_rows = []
    unserviced_rooms: list[str] = []
    fully_ok_count = 0

    for room in all_rooms:
        recs = room_records.get(room.room_no, [])

        if not recs:
            # 未保養
            unserviced_rooms.append(room.room_no)
            summary_rows.append({
                "floor":          room.floor,
                "floor_no":       room.floor_no,
                "room_no":        room.room_no,
                "serviced":       False,
                "maintain_date":  None,
                "staff_name":     None,
                "work_hours":     None,
                "created_date":   None,
                "checks":         {},
                "abnormal_count": 0,
                "total_checks":   12,
                "record_count":   0,
            })
        else:
            # 取最近一筆（以 maintain_date 降冪，再以 created_date 降冪）
            latest = max(recs, key=lambda x: (x.maintain_date or "", x.created_date or ""))
            checks: dict[str, str] = {}
            abnormal = 0
            for field_name, label in CHECK_FIELDS:
                val = getattr(latest, field_name, "") or ""
                checks[label] = val
                if val.upper() == "X":
                    abnormal += 1

            if abnormal == 0:
                fully_ok_count += 1

            summary_rows.append({
                "floor":          room.floor,
                "floor_no":       room.floor_no,
                "room_no":        room.room_no,
                "serviced":       True,
                "maintain_date":  latest.maintain_date,
                "staff_name":     latest.staff_name,
                "work_hours":     latest.work_hours,
                "created_date":   latest.created_date,
                "checks":         checks,
                "abnormal_count": abnormal,
                "total_checks":   12,
                "record_count":   len(recs),
            })

    stats = {
        "total_records":    total_records,
        "total_abnormal":   total_abnormal,
        "fully_ok_count":   fully_ok_count,
        "work_hours_total": round(work_hours_total, 1),
        "unserviced_count": len(unserviced_rooms),
    }

    return {
        "data":             summary_rows,
        "stats":            stats,
        "unserviced_rooms": unserviced_rooms,
    }


# ── GET / — 明細列表 ───────────────────────────────────────────────────────────
@router.get("", summary="客房保養明細清單")
@router.get("/", summary="客房保養明細清單", include_in_schema=False)
async def list_records(
    room_no:       Optional[str] = Query(None, description="依房號篩選"),
    staff_name:    Optional[str] = Query(None, description="依保養人員篩選"),
    maintain_date: Optional[str] = Query(None, description="單日篩選 YYYY/MM/DD"),
    date_from:     Optional[str] = Query(None, description="起始日期 YYYY/MM/DD"),
    date_to:       Optional[str] = Query(None, description="結束日期 YYYY/MM/DD"),
    page:          int = Query(1,   ge=1),
    per_page:      int = Query(50,  ge=1, le=200),
    db: Session = Depends(get_db),
):
    """從本地 SQLite 讀取客房保養明細清單，支援篩選與分頁"""
    try:
        q = db.query(RoomMaintenanceDetailRecord)

        if room_no:
            q = q.filter(RoomMaintenanceDetailRecord.room_no.ilike(f"%{room_no}%"))
        if staff_name:
            q = q.filter(RoomMaintenanceDetailRecord.staff_name.ilike(f"%{staff_name}%"))
        if maintain_date:
            q = q.filter(RoomMaintenanceDetailRecord.maintain_date.ilike(f"%{maintain_date}%"))
        if date_from:
            q = q.filter(RoomMaintenanceDetailRecord.maintain_date >= date_from)
        if date_to:
            q = q.filter(RoomMaintenanceDetailRecord.maintain_date <= date_to)

        total = q.count()
        items = (
            q.order_by(
                RoomMaintenanceDetailRecord.maintain_date.desc(),
                RoomMaintenanceDetailRecord.room_no,
            )
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return {
            "data": [_record_to_dict(r) for r in items],
            "meta": {"total": total, "page": page, "per_page": per_page},
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"讀取資料失敗：{str(e)}",
        )


# ── GET /room-history/{room_no} — 單一房間保養歷史 ───────────────────────────
@router.get("/room-history/{room_no}", summary="單一房間保養歷史（月曆摘要 + 全記錄）")
async def get_room_history(
    room_no: str,
    months:  int = Query(12, ge=1, le=36, description="查詢最近幾個月（預設 12）"),
    db: Session = Depends(get_db),
):
    """
    回傳指定房號的保養歷史記錄，包含：
    - room：房號基本資訊（floor, room_no）
    - monthly_summary：近 N 個月每月保養狀態
    - records：所有保養記錄（時序降冪）
    - stats：
        total_records         全部記錄筆數
        last_serviced         上次保養日期
        consecutive_missed    連續未保養月數（從最近月份往回算）
        serviced_months       近 N 月中已保養月數
    """
    # ── 取得 Room 主檔 ─────────────────────────────────────────────────────
    room = db.query(Room).filter(Room.room_no == room_no).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"房號 {room_no} 不在客房主檔中",
        )

    # ── 取得全部保養記錄（時序降冪）────────────────────────────────────────
    records = (
        db.query(RoomMaintenanceDetailRecord)
        .filter(RoomMaintenanceDetailRecord.room_no == room_no)
        .order_by(RoomMaintenanceDetailRecord.maintain_date.desc())
        .all()
    )

    # ── 建立 (year, month) → [records] 的映射 ─────────────────────────────
    rec_by_ym: dict[tuple[int, int], list] = defaultdict(list)
    for r in records:
        ym = _extract_ym(r.maintain_date)
        if ym:
            rec_by_ym[ym].append(r)

    # ── 計算近 N 個月的月曆摘要 ────────────────────────────────────────────
    today       = date.today()
    cur_year    = today.year
    cur_month   = today.month
    monthly_summary = []

    for i in range(months - 1, -1, -1):
        y, m = _offset_month(cur_year, cur_month, -i)
        is_current_or_future = (y > cur_year) or (y == cur_year and m >= cur_month)
        recs = rec_by_ym.get((y, m), [])

        # 工時合計（該月）
        wh_total = sum(_parse_minutes(r.work_hours) for r in recs)

        # 最近一筆明細
        latest = recs[0] if recs else None
        checks: dict[str, str] = {}
        if latest:
            for fn, label in CHECK_FIELDS:
                checks[label] = getattr(latest, fn, "") or ""

        monthly_summary.append({
            "year":           y,
            "month":          m,
            "month_label":    f"{y}/{m:02d}",
            "is_current":     is_current_or_future,
            "serviced":       len(recs) > 0,
            "record_count":   len(recs),
            "work_hours_sum": round(wh_total, 1),
            "latest_date":    latest.maintain_date if latest else None,
            "latest_staff":   latest.staff_name    if latest else None,
            "checks":         checks,
        })

    # ── 連續未保養月數（從最近月往回） ─────────────────────────────────────
    consecutive_missed = 0
    for ms in reversed(monthly_summary):
        if ms["is_current"] and not ms["serviced"]:
            # 當月尚未完成不算 missed
            continue
        if not ms["serviced"]:
            consecutive_missed += 1
        else:
            break

    # ── Stats ──────────────────────────────────────────────────────────────
    total_records  = len(records)
    last_serviced  = records[0].maintain_date if records else None
    serviced_months = sum(1 for ms in monthly_summary if ms["serviced"])

    return {
        "room": {
            "floor":   room.floor,
            "room_no": room.room_no,
        },
        "monthly_summary": monthly_summary,
        "records":         [_record_to_dict(r) for r in records],
        "stats": {
            "total_records":      total_records,
            "last_serviced":      last_serviced,
            "consecutive_missed": consecutive_missed,
            "serviced_months":    serviced_months,
            "total_months":       months,
        },
    }


def _extract_ym(date_str: str) -> tuple[int, int] | None:
    """'2026/04/09' → (2026, 4)"""
    if not date_str:
        return None
    parts = date_str.split("/")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _offset_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """月份偏移（delta 可為負）"""
    total = (year * 12 + month - 1) + delta
    return total // 12, total % 12 + 1


# ── GET /staff-hours — 人員工時月報表 ────────────────────────────────────────
@router.get("/staff-hours", summary="人員工時月報表（近 N 個月 pivot）")
async def get_staff_hours(
    months:   int           = Query(12, ge=1, le=36, description="顯示最近幾個月（預設 12）"),
    date_from: Optional[str] = Query(None, description="起始日期 YYYY/MM/DD，若指定則覆蓋 months 計算"),
    date_to:   Optional[str] = Query(None, description="結束日期 YYYY/MM/DD"),
    db: Session = Depends(get_db),
):
    """
    回傳每位人員在近 N 個月的工時彙總（分鐘→小時）：
    - months：要顯示的月份標籤列表（e.g. ["2025/05", ..., "2026/04"]）
    - rows：每位人員一列，monthly_hours[月份] = 小時數，total_hours = 合計小時
    - month_totals：每月全員工時合計（小時）
    - grand_total_hours：全期間所有人員工時總計（小時）
    """
    today = date.today()
    cur_year, cur_month = today.year, today.month

    # 建立月份標籤列表（由舊到新）
    month_labels: list[str] = []
    for i in range(months - 1, -1, -1):
        y, m = _offset_month(cur_year, cur_month, -i)
        month_labels.append(f"{y}/{m:02d}")

    # 查詢記錄（依指定日期區間，否則取最早 month_label 以後的所有記錄）
    q = db.query(RoomMaintenanceDetailRecord)
    if date_from:
        q = q.filter(RoomMaintenanceDetailRecord.maintain_date >= date_from)
    else:
        start_date = month_labels[0] + "/01"
        q = q.filter(RoomMaintenanceDetailRecord.maintain_date >= start_date)
    if date_to:
        q = q.filter(RoomMaintenanceDetailRecord.maintain_date <= date_to)
    records = q.all()

    # 依「人員 → 月份」聚合分鐘數
    staff_month: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in records:
        if not r.staff_name or not r.maintain_date:
            continue
        parts = r.maintain_date.split("/")
        if len(parts) < 2:
            continue
        ym = f"{parts[0]}/{parts[1]}"
        staff_month[r.staff_name][ym] += _parse_minutes(r.work_hours)

    # 組裝每人列（分鐘→小時，四捨五入兩位）
    staff_list = sorted(staff_month.keys())
    rows = []
    for staff in staff_list:
        monthly_minutes = staff_month[staff]
        monthly_hours: dict[str, float] = {}
        total_minutes = 0.0
        for ym in month_labels:
            mins = monthly_minutes.get(ym, 0.0)
            monthly_hours[ym] = round(mins / 60, 2)
            total_minutes += mins
        rows.append({
            "staff_name":    staff,
            "monthly_hours": monthly_hours,          # {月份: 小時}
            "total_hours":   round(total_minutes / 60, 2),
            "total_minutes": round(total_minutes, 1),
        })

    # 每月全員合計
    month_totals: dict[str, float] = {}
    grand_total_minutes = 0.0
    for ym in month_labels:
        total_m = sum(staff_month[s].get(ym, 0.0) for s in staff_list)
        month_totals[ym] = round(total_m / 60, 2)
        grand_total_minutes += total_m

    return {
        "months":             month_labels,
        "rows":               rows,
        "month_totals":       month_totals,
        "grand_total_hours":  round(grand_total_minutes / 60, 2),
    }


# ── GET /maintenance-stats — 保養統計分析（Phase 1+2+3）───────────────────────
@router.get("/maintenance-stats", summary="保養統計分析（完成率趨勢、異常項目、樓層分析、高風險房間、月份對比）")
async def get_maintenance_stats(
    months: int = Query(12, ge=1, le=36, description="顯示最近幾個月（預設 12）"),
    db: Session = Depends(get_db),
):
    """
    彙整三大分析面向：

    Phase 1 — 月別完成率趨勢 + 高風險房間
      monthly_trend：近 N 月每月 完成率% / 異常率% / 工時
      risk_rooms：連續未保養（≥2月）/ 重複異常（同項目連續2月X）/ 全正常

    Phase 2 — 異常項目分佈
      check_item_stats：12 個檢查項目的累計 X 次數排行

    Phase 3 — 樓層分析 + 月份對比
      floor_stats：各樓層當月完成率 + 全期異常次數
      comparison：當月 vs 上月 vs 去年同月

    kpi：主管 KPI 摘要（6 個指標）
    """
    today = date.today()
    cur_year, cur_month = today.year, today.month
    cur_ym = f"{cur_year}/{cur_month:02d}"

    # ── 建立月份標籤列表（由舊到新）──────────────────────────────────────────
    month_labels: list[str] = []
    for i in range(months - 1, -1, -1):
        y, m = _offset_month(cur_year, cur_month, -i)
        month_labels.append(f"{y}/{m:02d}")

    start_date = month_labels[0] + "/01"

    # ── 取得全部記錄（僅在月份範圍內）───────────────────────────────────────
    all_records = (
        db.query(RoomMaintenanceDetailRecord)
        .filter(RoomMaintenanceDetailRecord.maintain_date >= start_date)
        .all()
    )

    # ── 取得所有客房主檔 ─────────────────────────────────────────────────────
    all_rooms = (
        db.query(Room)
        .order_by(Room.floor_no.asc(), Room.room_no.asc())
        .all()
    )
    total_rooms = len(all_rooms)
    room_set    = {r.room_no for r in all_rooms}

    # ── 依月份 / 依房號分組 ──────────────────────────────────────────────────
    rec_by_ym:   dict[str, list] = defaultdict(list)
    rec_by_room: dict[str, list] = defaultdict(list)

    for r in all_records:
        if not r.maintain_date:
            continue
        parts = r.maintain_date.split("/")
        if len(parts) >= 2:
            ym = f"{parts[0]}/{parts[1]}"
            if ym in month_labels:          # 只納入目標月份範圍
                rec_by_ym[ym].append(r)
        rec_by_room[r.room_no].append(r)

    # ══════════════════════════════════════════════════════════════════
    # Phase 1A — 月別完成率趨勢
    # ══════════════════════════════════════════════════════════════════
    monthly_trend = []
    for ym in month_labels:
        recs            = rec_by_ym.get(ym, [])
        serviced_rooms  = {r.room_no for r in recs if r.room_no in room_set}
        serviced_count  = len(serviced_rooms)
        completion_rate = round(serviced_count / total_rooms * 100, 1) if total_rooms > 0 else 0.0

        rooms_with_abnormal: set[str] = set()
        total_abnormal_items  = 0
        total_wh              = 0.0
        for r in recs:
            has_x = False
            for fn, _ in CHECK_FIELDS:
                if getattr(r, fn, "").upper() == "X":
                    total_abnormal_items += 1
                    has_x = True
            if has_x:
                rooms_with_abnormal.add(r.room_no)
            total_wh += _parse_minutes(r.work_hours)

        abnormal_rate = (
            round(len(rooms_with_abnormal) / serviced_count * 100, 1)
            if serviced_count > 0 else 0.0
        )
        monthly_trend.append({
            "month_label":           ym,
            "completion_rate":       completion_rate,
            "serviced_count":        serviced_count,
            "total_rooms":           total_rooms,
            "abnormal_item_count":   total_abnormal_items,
            "rooms_with_abnormal":   len(rooms_with_abnormal),
            "abnormal_rate":         abnormal_rate,
            "work_hours_total":      round(total_wh, 1),
        })

    # ══════════════════════════════════════════════════════════════════
    # Phase 2 — 異常項目分佈
    # ══════════════════════════════════════════════════════════════════
    total_record_count = len(all_records)
    check_item_stats   = []
    for fn, label in CHECK_FIELDS:
        x_count = sum(1 for r in all_records if getattr(r, fn, "").upper() == "X")
        v_count = sum(1 for r in all_records if getattr(r, fn, "").upper() == "V")
        check_item_stats.append({
            "field_name":     fn,
            "label":          label,
            "abnormal_count": x_count,
            "normal_count":   v_count,
            "total_count":    total_record_count,
            "abnormal_rate":  round(x_count / total_record_count * 100, 1) if total_record_count > 0 else 0.0,
        })
    check_item_stats.sort(key=lambda x: x["abnormal_count"], reverse=True)

    # ══════════════════════════════════════════════════════════════════
    # Phase 3A — 樓層分析
    # ══════════════════════════════════════════════════════════════════
    floor_rooms: dict[str, list] = defaultdict(list)
    for r in all_rooms:
        floor_rooms[r.floor].append(r)

    # 當月已保養房號集合
    cur_recs          = rec_by_ym.get(cur_ym, [])
    cur_serviced_set  = {r.room_no for r in cur_recs}

    floor_stats = []
    for floor, rooms in sorted(floor_rooms.items(), key=lambda x: x[1][0].floor_no):
        floor_room_nos        = {r.room_no for r in rooms}
        serviced_this_month   = len(floor_room_nos & cur_serviced_set)
        completion_rate       = round(serviced_this_month / len(rooms) * 100, 1) if rooms else 0.0
        floor_recs            = [r for r in all_records if r.room_no in floor_room_nos]
        total_abnormal        = sum(
            1
            for r in floor_recs
            for fn, _ in CHECK_FIELDS
            if getattr(r, fn, "").upper() == "X"
        )
        floor_stats.append({
            "floor":                floor,
            "floor_no":             rooms[0].floor_no,
            "total_rooms":          len(rooms),
            "serviced_this_month":  serviced_this_month,
            "completion_rate":      completion_rate,
            "abnormal_count":       total_abnormal,
            "total_records":        len(floor_recs),
        })

    # ══════════════════════════════════════════════════════════════════
    # Phase 1B — 高風險房間清單
    # ══════════════════════════════════════════════════════════════════
    recent_6  = month_labels[-6:]  if len(month_labels) >= 6  else month_labels
    last_2    = month_labels[-2:]  if len(month_labels) >= 2  else month_labels

    consecutive_missed_rooms: list[dict] = []
    repeated_abnormal_rooms:  list[dict] = []
    fully_ok_rooms:           list[dict] = []

    for room in all_rooms:
        room_recs = sorted(
            rec_by_room.get(room.room_no, []),
            key=lambda x: (x.maintain_date or ""),
            reverse=True,
        )

        # 連續未保養（從最近月份往回計算）
        missed = 0
        for ym in reversed(recent_6):
            has_rec = any(
                r.maintain_date and r.maintain_date.startswith(ym)
                for r in room_recs
            )
            if not has_rec:
                missed += 1
            else:
                break
        if missed >= 2:
            consecutive_missed_rooms.append({
                "room_no":      room.room_no,
                "floor":        room.floor,
                "missed_months": missed,
                "last_serviced": room_recs[0].maintain_date if room_recs else None,
            })

        # 同一項目連續2月都是 X
        if len(last_2) == 2:
            month_x: dict[str, set] = {}
            for ym in last_2:
                x_fields: set[str] = set()
                for r in room_recs:
                    if r.maintain_date and r.maintain_date.startswith(ym):
                        for fn, _ in CHECK_FIELDS:
                            if getattr(r, fn, "").upper() == "X":
                                x_fields.add(fn)
                month_x[ym] = x_fields
            common_x = month_x.get(last_2[0], set()) & month_x.get(last_2[1], set())
            for fn in common_x:
                label = next((l for f, l in CHECK_FIELDS if f == fn), fn)
                repeated_abnormal_rooms.append({
                    "room_no":           room.room_no,
                    "floor":             room.floor,
                    "field_name":        fn,
                    "field_label":       label,
                    "consecutive_months": 2,
                })

        # 全正常（最近3筆保養記錄均無 X）
        if room_recs:
            recent3 = room_recs[:3]

            def _is_fully_ok(rec) -> bool:
                vals = [getattr(rec, fn, "").upper() for fn, _ in CHECK_FIELDS]
                return all(v in ("V", "") for v in vals) and any(v == "V" for v in vals)

            if all(_is_fully_ok(r) for r in recent3):
                fully_ok_rooms.append({
                    "room_no":        room.room_no,
                    "floor":          room.floor,
                    "ok_record_count": len(recent3),
                    "last_serviced":   recent3[0].maintain_date,
                })

    consecutive_missed_rooms.sort(key=lambda x: x["missed_months"], reverse=True)

    # ══════════════════════════════════════════════════════════════════
    # Phase 3B — 月份對比（當月 / 上月 / 去年同月）
    # ══════════════════════════════════════════════════════════════════
    def _month_snapshot(ym: str) -> dict:
        recs       = rec_by_ym.get(ym, [])
        serviced   = len({r.room_no for r in recs if r.room_no in room_set})
        completion = round(serviced / total_rooms * 100, 1) if total_rooms > 0 else 0.0
        abnormal   = sum(
            1 for r in recs for fn, _ in CHECK_FIELDS if getattr(r, fn, "").upper() == "X"
        )
        wh = sum(_parse_minutes(r.work_hours) for r in recs)
        return {
            "month_label":      ym,
            "serviced_count":   serviced,
            "completion_rate":  completion,
            "abnormal_count":   abnormal,
            "work_hours_total": round(wh, 1),
            "record_count":     len(recs),
        }

    prev_y, prev_m            = _offset_month(cur_year, cur_month, -1)
    prev_ym                   = f"{prev_y}/{prev_m:02d}"
    same_last_year_ym         = f"{cur_year - 1}/{cur_month:02d}"

    # ══════════════════════════════════════════════════════════════════
    # KPI 摘要
    # ══════════════════════════════════════════════════════════════════
    cur_trend  = monthly_trend[-1]  if monthly_trend            else {}
    prev_trend = monthly_trend[-2]  if len(monthly_trend) >= 2  else {}
    avg_comp   = (
        round(sum(t["completion_rate"] for t in monthly_trend) / len(monthly_trend), 1)
        if monthly_trend else 0.0
    )
    cur_rate  = cur_trend.get("completion_rate",  0)
    prev_rate = prev_trend.get("completion_rate", 0)
    trend_dir = (
        "up"   if cur_rate > prev_rate + 2 else
        "down" if cur_rate < prev_rate - 2 else
        "stable"
    )

    return {
        "months":         month_labels,
        "monthly_trend":  monthly_trend,
        "check_item_stats": check_item_stats,
        "floor_stats":    floor_stats,
        "risk_rooms": {
            "consecutive_missed": consecutive_missed_rooms,
            "repeated_abnormal":  repeated_abnormal_rooms,
            "fully_ok":           fully_ok_rooms,
        },
        "comparison": {
            "current_month":         _month_snapshot(cur_ym),
            "prev_month":            _month_snapshot(prev_ym),
            "same_month_last_year":  _month_snapshot(same_last_year_ym),
        },
        "kpi": {
            "current_month_completion_rate": cur_rate,
            "current_month_abnormal_rate":   cur_trend.get("abnormal_rate", 0),
            "consecutive_missed_rooms":      len(consecutive_missed_rooms),
            "fully_ok_rooms":                len(fully_ok_rooms),
            "avg_completion_rate_12m":       avg_comp,
            "trend_direction":               trend_dir,
        },
    }


# ── GET /{record_id} — 單筆 ──────────────────────────────────────────────────
@router.get("/{record_id}", summary="單筆客房保養明細")
async def get_record(record_id: str, db: Session = Depends(get_db)):
    rec = db.get(RoomMaintenanceDetailRecord, record_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"記錄 {record_id} 不存在",
        )
    return {"data": _record_to_dict(rec)}
