"""
保全巡檢統計 Dashboard API Router
Prefix: /api/v1/security/dashboard

端點：
  GET /summary  — KPI 摘要（今日各 Sheet 巡檢統計）
  GET /issues   — 異常 / 未完成清單
  GET /trend    — 近 N 日趨勢資料
"""
from datetime import date, timedelta, datetime, timezone
from app.core.time import twnow
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.security_patrol import SecurityPatrolBatch, SecurityPatrolItem
from app.schemas.security_dashboard import (
    DashboardSummary, SheetStats, IssueItem, IssueListResponse,
    TrendPoint, DashboardTrend,
)
from app.services.security_patrol_sync import SHEET_CONFIGS

router = APIRouter(dependencies=[Depends(get_current_user)])

ALL_SHEET_KEYS = list(SHEET_CONFIGS.keys())


# ── 輔助函式 ──────────────────────────────────────────────────────────────────

def _parse_date_str(s: Optional[str]) -> date:
    if not s:
        return date.today()
    try:
        clean = s.replace("-", "/").strip()
        y, m, d_ = clean.split("/")
        return date(int(y), int(m), int(d_))
    except Exception:
        return date.today()


def _sheet_stats(
    db: Session,
    sheet_key: str,
    sheet_name: str,
    target_date_str: str,
) -> SheetStats:
    batches = db.query(SecurityPatrolBatch).filter(
        SecurityPatrolBatch.sheet_key       == sheet_key,
        SecurityPatrolBatch.inspection_date == target_date_str,
    ).all()

    total = normal = abnormal = pending = unchecked = 0
    for b in batches:
        # 僅計入評分項目（排除 is_note=True 的異常說明類欄位）
        items = db.query(SecurityPatrolItem).filter(
            SecurityPatrolItem.batch_ragic_id == b.ragic_id,
            SecurityPatrolItem.is_note == False,  # noqa: E712
        ).all()
        for it in items:
            total += 1
            if   it.result_status == "normal":    normal    += 1
            elif it.result_status == "abnormal":  abnormal  += 1
            elif it.result_status == "pending":   pending   += 1
            else:                                 unchecked += 1

    checked = normal + abnormal + pending
    return SheetStats(
        sheet_key       = sheet_key,
        sheet_name      = sheet_name,
        total_batches   = len(batches),
        total_items     = total,
        checked_items   = checked,
        unchecked_items = unchecked,
        abnormal_items  = abnormal,
        pending_items   = pending,
        completion_rate = round(checked / total * 100, 1) if total > 0 else 0.0,
        normal_rate     = round(normal  / checked * 100, 1) if checked > 0 else 0.0,
        has_data        = total > 0,
    )


# ── /summary ──────────────────────────────────────────────────────────────────

@router.get("/summary", summary="取得 Dashboard KPI 摘要", response_model=DashboardSummary)
def get_summary(
    target_date: Optional[str] = Query(None, description="查詢日期 YYYY/MM/DD，預設今日"),
    db: Session = Depends(get_db),
):
    target     = _parse_date_str(target_date)
    target_str = target.strftime("%Y/%m/%d")

    sheets_stats = [
        _sheet_stats(db, sk, SHEET_CONFIGS[sk]["name"], target_str)
        for sk in ALL_SHEET_KEYS
    ]

    total_batches_all   = sum(s.total_batches   for s in sheets_stats)
    total_items_all     = sum(s.total_items     for s in sheets_stats)
    checked_items_all   = sum(s.checked_items   for s in sheets_stats)
    abnormal_items_all  = sum(s.abnormal_items + s.pending_items for s in sheets_stats)

    return DashboardSummary(
        target_date          = target_str,
        sheets               = sheets_stats,
        total_batches_all    = total_batches_all,
        total_items_all      = total_items_all,
        checked_items_all    = checked_items_all,
        abnormal_items_all   = abnormal_items_all,
        completion_rate_all  = round(
            checked_items_all / total_items_all * 100, 1
        ) if total_items_all > 0 else 0.0,
        generated_at         = twnow().strftime("%Y/%m/%d %H:%M"),
    )


# ── /issues ───────────────────────────────────────────────────────────────────

@router.get("/issues", summary="取得異常/未完成清單", response_model=IssueListResponse)
def get_issues(
    sheet_key:  Optional[str] = Query(None, description="指定 sheet_key，空白=全部"),
    status:     Optional[str] = Query(None, description="abnormal|pending|unchecked|all"),
    start_date: Optional[str] = Query(None),
    end_date:   Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    today       = date.today()
    start       = _parse_date_str(start_date) if start_date else (today - timedelta(days=7))
    end         = _parse_date_str(end_date)   if end_date   else today
    start_str   = start.strftime("%Y/%m/%d")
    end_str     = end.strftime("%Y/%m/%d")

    target_sheets = [sheet_key] if sheet_key and sheet_key in SHEET_CONFIGS else ALL_SHEET_KEYS

    STATUS_LABEL_MAP = {
        "abnormal":  "異常",
        "pending":   "待處理",
        "unchecked": "未巡檢",
    }

    issues: list[IssueItem] = []

    for sk in target_sheets:
        sheet_name = SHEET_CONFIGS[sk]["name"]
        batches = db.query(SecurityPatrolBatch).filter(
            SecurityPatrolBatch.sheet_key       == sk,
            SecurityPatrolBatch.inspection_date >= start_str,
            SecurityPatrolBatch.inspection_date <= end_str,
        ).order_by(SecurityPatrolBatch.inspection_date.desc()).all()

        for b in batches:
            q = db.query(SecurityPatrolItem).filter(
                SecurityPatrolItem.batch_ragic_id == b.ragic_id,
                SecurityPatrolItem.is_note == False,  # noqa: E712 — 排除文字備註欄位
            )
            if status in (None, "all"):
                q = q.filter(
                    SecurityPatrolItem.result_status.in_(["abnormal", "pending", "unchecked"])
                )
            elif status in ("abnormal", "pending", "unchecked"):
                if status == "abnormal":
                    q = q.filter(SecurityPatrolItem.result_status.in_(["abnormal", "pending"]))
                else:
                    q = q.filter(SecurityPatrolItem.result_status == status)
            else:
                continue

            for it in q.all():
                issues.append(IssueItem(
                    id           = it.ragic_id,
                    issue_date   = b.inspection_date,
                    sheet_key    = sk,
                    sheet_name   = sheet_name,
                    item_name    = it.item_name,
                    status       = it.result_status,
                    status_label = STATUS_LABEL_MAP.get(it.result_status, it.result_status),
                    inspector    = b.inspector_name or "",
                    note         = it.result_raw or "",
                    batch_id     = b.ragic_id,
                ))

    issues.sort(key=lambda x: x.issue_date, reverse=True)
    return IssueListResponse(items=issues, total=len(issues))


# ── /trend ────────────────────────────────────────────────────────────────────

@router.get("/trend", summary="取得近 N 日巡檢趨勢", response_model=DashboardTrend)
def get_trend(
    days: int = Query(7, ge=3, le=30, description="趨勢天數"),
    db: Session = Depends(get_db),
):
    today = date.today()
    trend_points: list[TrendPoint] = []

    for i in range(days - 1, -1, -1):
        d     = today - timedelta(days=i)
        d_str = d.strftime("%Y/%m/%d")

        total_batches  = 0
        total_abnormal = 0
        by_sheet       = {}
        has_data       = False

        for sk in ALL_SHEET_KEYS:
            batches = db.query(SecurityPatrolBatch).filter(
                SecurityPatrolBatch.sheet_key       == sk,
                SecurityPatrolBatch.inspection_date == d_str,
            ).all()

            abn = 0
            for b in batches:
                abn += db.query(SecurityPatrolItem).filter(
                    SecurityPatrolItem.batch_ragic_id == b.ragic_id,
                    SecurityPatrolItem.result_status.in_(["abnormal", "pending"]),
                    SecurityPatrolItem.is_note == False,  # noqa: E712
                ).count()

            total_batches  += len(batches)
            total_abnormal += abn
            if batches:
                has_data = True
            by_sheet[sk] = {"batch_count": len(batches), "abnormal": abn}

        trend_points.append(TrendPoint(
            date           = d_str,
            abnormal_count = total_abnormal,
            total_batches  = total_batches,
            has_data       = has_data,
            by_sheet       = by_sheet,
        ))

    return DashboardTrend(trend=trend_points, days=days)


# ── /calendar — 月曆格（巡檢表 × 日）─────────────────────────────────────────

@router.get("/calendar", summary="保全巡檢月曆格（巡檢表 × 日）")
def get_calendar(
    year:  int = Query(..., description="年份，如 2026"),
    month: int = Query(..., ge=1, le=12, description="月份，如 5"),
    db:    Session = Depends(get_db),
):
    """
    回傳指定年月的巡檢表 × 日期月曆格資料。
    cell key = str(d)（非零填充，配合 MonthlyCalendarGrid）。
    2 次 DB 查詢（all_batches + all_items），純 Python 分組計算。
    """
    import calendar as cal_mod
    from collections import defaultdict

    max_day      = cal_mod.monthrange(year, month)[1]
    month_prefix = f"{year}/{month:02d}/"

    SHEET_SHORT_NAMES: dict[str, str] = {
        "b1f-b4f":  "B1F~B4F",
        "1f-3f":    "1F~3F",
        "5f-10f":   "5F~10F",
        "4f":       "4F",
        "1f-hotel": "1F飯店",
        "1f-close": "1F閉店",
        "1f-open":  "1F開店",
    }

    # ── 1. 一次撈全月批次 ───────────────────────────────────────────────────────
    all_batches = db.query(SecurityPatrolBatch).filter(
        SecurityPatrolBatch.inspection_date.like(f"{month_prefix}%"),
    ).all()

    # ── 2. 依 (sheet_key, day) 分組 ────────────────────────────────────────────
    sk_day_batches: dict = defaultdict(lambda: defaultdict(list))
    for b in all_batches:
        parts = b.inspection_date.split("/")
        try:
            day = int(parts[2])
        except (IndexError, ValueError):
            continue
        sk_day_batches[b.sheet_key][day].append(b)

    # ── 3. 一次撈所有相關巡檢項目（排除文字備註欄位）──────────────────────────
    items_by_batch: dict = defaultdict(list)
    batch_ids = [b.ragic_id for b in all_batches]
    if batch_ids:
        for it in db.query(SecurityPatrolItem).filter(
            SecurityPatrolItem.batch_ragic_id.in_(batch_ids),
            SecurityPatrolItem.is_note == False,  # noqa: E712
        ).all():
            items_by_batch[it.batch_ragic_id].append(it)

    # ── 4. 組裝輸出 ────────────────────────────────────────────────────────────
    rows_out = []
    for sk in ALL_SHEET_KEYS:
        label = SHEET_SHORT_NAMES.get(sk, sk)
        daily: dict = {}
        for d in range(1, max_day + 1):
            day_batches = sk_day_batches[sk].get(d, [])
            if not day_batches:
                daily[str(d)] = {
                    "has_record": False, "completion_rate": 0,
                    "abnormal_count": 0, "pending_count": 0,
                }
            else:
                total = normal = abnormal = pending = 0
                for b in day_batches:
                    for it in items_by_batch.get(b.ragic_id, []):
                        total += 1
                        if   it.result_status == "normal":   normal   += 1
                        elif it.result_status == "abnormal": abnormal += 1
                        elif it.result_status == "pending":  pending  += 1
                checked = normal + abnormal + pending
                daily[str(d)] = {
                    "has_record":      True,
                    "completion_rate": round(checked / total * 100, 1) if total > 0 else 0.0,
                    "abnormal_count":  abnormal,
                    "pending_count":   pending,
                }
        rows_out.append({"key": sk, "label": label, "daily": daily})

    return {"year": year, "month": month, "max_day": max_day, "rows": rows_out}


# ── /daily-form — 每日巡檢表（模板 × DB 比對）────────────────────────────────

@router.get("/daily-form", summary="保全巡檢每日巡檢表（樓層 × 項目 × 檢查內容）")
def get_daily_form(
    year:            int           = Query(...,  description="年份，如 2026"),
    month:           int           = Query(...,  ge=1, le=12, description="月份，如 5"),
    inspection_date: Optional[str] = Query(None, description="巡檢日期 YYYY/MM/DD（不填則顯示整月合併）"),
    db:              Session       = Depends(get_db),
):
    """
    回傳保全巡檢每日巡檢表列（依 Excel #2.4保全-每日巡檢表.xlsx），
    並與本地 DB 實際巡檢資料比對回傳結果。
    """
    from app.services.security_patrol_daily_builder import build_security_patrol_daily_table

    rows = build_security_patrol_daily_table(
        year=year,
        month=month,
        db=db,
        inspection_date=inspection_date,
    )

    return {
        "year":            year,
        "month":           month,
        "inspection_date": inspection_date or "",
        "rows":            rows,
    }


# ── /monthly-summary — 月份彙總（供 hotel/overview Dashboard 使用）─────────────

def _parse_minutes_sec(start: str, end: str) -> int:
    """解析 HH:MM 格式開始/結束時間，回傳分鐘差值；格式無效回傳 0。"""
    import re as _re
    def to_min(t: str) -> Optional[int]:
        m = _re.match(r"^(\d{1,2}):(\d{2})$", (t or "").strip())
        return int(m.group(1)) * 60 + int(m.group(2)) if m else None
    s, e = to_min(start), to_min(end)
    if s is None or e is None:
        return 0
    diff = e - s
    return diff + 24 * 60 if diff < 0 else diff


@router.get("/monthly-summary", summary="保全巡檢月份彙總統計（供飯店管理 Dashboard 使用）")
def get_monthly_summary(
    year:  int = Query(..., ge=2020, le=2030, description="年份"),
    month: int = Query(..., ge=1,    le=12,   description="月份（1–12）"),
    db: Session = Depends(get_db),
):
    """
    彙整指定年月內所有保全巡檢的月份統計（跨所有巡檢表），
    供飯店管理 Dashboard KPI Card「保全巡檢」顯示月份口徑資料。

    回傳：
      year_month      — 查詢年月（如 "2026/04"）
      total_items     — 月內所有巡檢項目總數
      checked_items   — 已確認項目數
      abnormal_items  — 異常項目數（abnormal + pending）
      total_minutes   — 月內總巡檢時間（分鐘，由 start_time/end_time 計算）
      completion_rate — 完成率（%）
      sheets          — 各巡檢表的月份彙總明細
    """
    year_month_prefix = f"{year}/{month:02d}/"

    sheets_result = []
    for sk in ALL_SHEET_KEYS:
        month_batches = db.query(SecurityPatrolBatch).filter(
            SecurityPatrolBatch.sheet_key == sk,
            SecurityPatrolBatch.inspection_date.like(f"{year_month_prefix}%"),
        ).all()

        total = normal = abnormal = pending = unchecked = total_minutes = 0
        for b in month_batches:
            items = db.query(SecurityPatrolItem).filter(
                SecurityPatrolItem.batch_ragic_id == b.ragic_id,
                SecurityPatrolItem.is_note == False,  # noqa: E712
            ).all()
            for it in items:
                total += 1
                if   it.result_status == "normal":   normal   += 1
                elif it.result_status == "abnormal": abnormal += 1
                elif it.result_status == "pending":  pending  += 1
                else:                                unchecked += 1
            total_minutes += _parse_minutes_sec(b.start_time or "", b.end_time or "")

        checked = normal + abnormal + pending
        sheets_result.append({
            "sheet_key":       sk,
            "sheet_name":      SHEET_CONFIGS[sk]["name"],
            "total_batches":   len(month_batches),
            "total_items":     total,
            "checked_items":   checked,
            "abnormal_items":  abnormal + pending,
            "unchecked_items": unchecked,
            "completion_rate": round(checked / total * 100, 1) if total > 0 else 0.0,
            "has_data":        total > 0,
            "total_minutes":   total_minutes,
        })

    total_items_all    = sum(s["total_items"]    for s in sheets_result)
    checked_items_all  = sum(s["checked_items"]  for s in sheets_result)
    abnormal_items_all = sum(s["abnormal_items"] for s in sheets_result)
    total_minutes_all  = sum(s["total_minutes"]  for s in sheets_result)
    overall_rate = (
        round(checked_items_all / total_items_all * 100, 1) if total_items_all > 0 else 0.0
    )

    return {
        "year":            year,
        "month":           month,
        "year_month":      f"{year}/{month:02d}",
        "total_items":     total_items_all,
        "checked_items":   checked_items_all,
        "abnormal_items":  abnormal_items_all,
        "total_minutes":   total_minutes_all,
        "completion_rate": overall_rate,
        "sheets":          sheets_result,
    }
