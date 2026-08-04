"""
OPERA 營運分析 — 營收分析 API Router
Prefix: /api/v1/opera/revenue

規格書：docs/SPEC_opera_analytics.md §10.2

資料來源一律為 History and Forecast（決策 D7）。
所有端點皆為同步 def（見 CLAUDE.md：async def 直接呼叫同步 DB 會凍結整站）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.time import twnow
from app.dependencies import get_current_user, require_permission
from app.models.audit_log import AuditLog
from app.models.opera_revenue import (
    DEFAULT_ANALYSIS_SETTINGS,
    OperaAnalysisSetting,
    RECORD_TYPE_FORECAST,
    RECORD_TYPE_HISTORY,
)
from app.models.user import User
from app.services import opera_analysis_service as AS
from app.services import opera_import_service as IMP
from app.services import opera_period_service as PS

router = APIRouter(dependencies=[Depends(get_current_user)])


def _resolve_range(db: Session, start: str | None, end: str | None,
                   property_code: str) -> tuple[str, str]:
    if start and end:
        return start, end
    default_start, default_end = PS.default_range(db, property_code)
    return start or default_start, end or default_end


# ── KPI ──────────────────────────────────────────────────────────────────────

@router.get("/kpi", summary="期間 KPI（營收／ADR／住房率／RevPAR + 同期比較）")
def revenue_kpi(
    start: str | None = Query(None, description="ISO YYYY-MM-DD"),
    end: str | None = Query(None),
    property_code: str = Query(""),
    include_forecast: bool = Query(False),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_view")),
):
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_kpi(db, s, e, property_code, include_forecast=include_forecast)


# ── 每日 ─────────────────────────────────────────────────────────────────────

@router.get("/daily", summary="每日營收明細")
def revenue_daily(
    start: str | None = Query(None),
    end: str | None = Query(None),
    property_code: str = Query(""),
    record_type: str = Query(RECORD_TYPE_HISTORY, description="History / Forecast"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_revenue_view")),
):
    if record_type not in (RECORD_TYPE_HISTORY, RECORD_TYPE_FORECAST):
        raise HTTPException(status_code=400, detail="record_type 只能是 History 或 Forecast")
    s, e = _resolve_range(db, start, end, property_code)
    return {
        "items": AS.get_daily(db, s, e, property_code, record_type),
        "start": s,
        "end": e,
        "record_type": record_type,
        "source_label": "資料來源：History and Forecast",
    }


@router.get("/daily/{business_date}", summary="單日明細（Drawer 用）")
def revenue_day_detail(
    business_date: str,
    property_code: str = Query(""),
    record_type: str = Query(RECORD_TYPE_HISTORY),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_revenue_view")),
):
    row = AS.get_day_detail(db, business_date, property_code, record_type)
    if not row:
        raise HTTPException(status_code=404, detail="找不到該日資料")
    return row


# ── 每月 / 每年 ──────────────────────────────────────────────────────────────

@router.get("/monthly", summary="月彙總 + 去年同期")
def revenue_monthly(
    year: int = Query(..., ge=2000, le=2100),
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_revenue_view")),
):
    return AS.get_monthly(db, year, property_code)


@router.get("/yearly", summary="年彙總 + 去年同期")
def revenue_yearly(
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_revenue_view")),
):
    return AS.get_yearly(db, property_code)


# ── 四象限 ───────────────────────────────────────────────────────────────────

@router.get("/quadrant", summary="ADR × 住房率四象限")
def revenue_quadrant(
    start: str | None = Query(None),
    end: str | None = Query(None),
    property_code: str = Query(""),
    basis: str = Query("common", description="common = 共同基準；annual = 年度自有基準"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_revenue_view")),
):
    if basis not in ("common", "annual"):
        raise HTTPException(status_code=400, detail="basis 只能是 common 或 annual")
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_quadrant(db, s, e, property_code, basis)


# ── 異常 / 客層 ──────────────────────────────────────────────────────────────

@router.get("/anomalies", summary="營收異常清單")
def revenue_anomalies(
    start: str | None = Query(None),
    end: str | None = Query(None),
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_revenue_view")),
):
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_anomalies(db, s, e, property_code)


@router.get("/segment", summary="散客 vs 團體拆分")
def revenue_segment(
    start: str | None = Query(None),
    end: str | None = Query(None),
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_view")),
):
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_segment(db, s, e, property_code)


# ── Dashboard 綜合端點 ───────────────────────────────────────────────────────

@router.get("/dashboard", summary="Dashboard 一次取回（KPI + 月趨勢 + 客層 + 異常摘要）")
def revenue_dashboard(
    year: int | None = Query(None),
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_view")),
):
    status = IMP.get_import_status(db)
    if not status["has_data"]:
        return {"has_data": False, "status": status}

    default_start, default_end = PS.default_range(db, property_code)
    target_year = year or int(default_end[:4])
    y_start, y_end = PS.year_range(target_year)
    # 當年尚未過完 → 截到資料最後一天（讓同期比較走 YTD）
    y_end = min(y_end, default_end)
    y_start = max(y_start, default_start)

    kpi = AS.get_kpi(db, y_start, y_end, property_code)
    monthly = AS.get_monthly(db, target_year, property_code)
    segment = AS.get_segment(db, y_start, y_end, property_code)
    anomalies = AS.get_anomalies(db, y_start, y_end, property_code)
    stay = AS.get_stay_summary(db, y_start, y_end, property_code)

    years = [int(y["year"]) for y in AS.get_yearly(db, property_code)["years"]]

    return {
        "has_data":      True,
        "year":          target_year,
        "available_years": years,
        "status":        status,
        "kpi":           kpi,
        "monthly":       monthly,
        "segment":       segment,
        "stay_summary":  stay,
        "anomaly_summary": {
            "total":       anomalies["total"],
            "type_counts": anomalies["type_counts"],
            "monthly_series": anomalies["monthly_series"],
        },
    }


# ── 門檻設定 ─────────────────────────────────────────────────────────────────

@router.get("/settings", summary="分析門檻設定")
def get_settings(
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_view")),
):
    return {"items": AS.list_settings(db, property_code)}


@router.put("/settings", summary="更新分析門檻設定")
def update_settings(
    request: Request,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opera_admin")),
):
    """payload: {"property_code": "", "settings": {"long_stay_nights": 7, ...}}"""
    property_code = (payload.get("property_code") or "").strip()
    incoming = payload.get("settings") or {}
    if not isinstance(incoming, dict) or not incoming:
        raise HTTPException(status_code=400, detail="settings 必須是非空的物件")

    before = AS.get_settings(db, property_code)
    changed: list[dict] = []

    for key, value in incoming.items():
        if key not in DEFAULT_ANALYSIS_SETTINGS:
            raise HTTPException(status_code=400, detail=f"不支援的設定項：{key}")
        _default, vtype, desc = DEFAULT_ANALYSIS_SETTINGS[key]
        try:
            typed = int(value) if vtype == "int" else float(value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"{key} 的值必須是數字")
        if typed <= 0:
            raise HTTPException(status_code=400, detail=f"{key} 必須大於 0")

        row = (
            db.query(OperaAnalysisSetting)
            .filter(
                OperaAnalysisSetting.property_code == property_code,
                OperaAnalysisSetting.setting_key == key,
            )
            .first()
        )
        if row is None:
            row = OperaAnalysisSetting(property_code=property_code, setting_key=key)
            db.add(row)
        row.setting_value = str(typed)
        row.value_type = vtype
        row.description = desc
        row.updated_at = twnow()
        row.updated_by_user_id = current_user.id
        row.updated_by_name = getattr(current_user, "full_name", "") or getattr(current_user, "username", "")
        changed.append({"key": key, "before": before.get(key), "after": typed})

    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else None
    )
    db.add(AuditLog(
        user_id=current_user.id,
        action="opera_settings_update",
        resource_type="opera_analysis_setting",
        resource_id=property_code or "(global)",
        ip_address=ip,
        extra={"changed": changed},
    ))
    db.flush()
    return {"ok": True, "changed": changed, "items": AS.list_settings(db, property_code)}
