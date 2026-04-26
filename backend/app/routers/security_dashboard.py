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
