"""
OPERA 營運分析 — 歷史同期查詢／房價預測／事件月曆 API Router
Prefix: /api/v1/opera/forecast

評估文件：docs/EVAL_opera_rate_forecasting.md

權限分工：
  * 歷史同期查詢（純查歷史事實）→ opera_view
  * 預測與回測（讀）             → opera_forecast_view
  * 估算係數／覆寫係數           → opera_admin（與分析門檻同屬模型參數維護）
  * 事件月曆新增／修改／刪除／學習 → opera_event_admin

所有端點皆為同步 def（見 CLAUDE.md：async def 直接呼叫同步 DB 會凍結整站）。
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.time import twnow
from app.dependencies import get_current_user, require_permission
from app.models.audit_log import AuditLog
from app.models.opera_forecast import (
    COEF_EDITABLE_KINDS,
    EVENT_CATEGORIES,
    EVENT_SOURCE_LEARNED,
    EVENT_SOURCE_MANUAL,
    MIN_EVENT_SAMPLES,
    OperaEvent,
    OperaForecastCoefficient,
    OperaForecastDaily,
    OperaForecastRun,
)
from app.models.user import User
from app.services import opera_forecast_service as FS
from app.services import opera_lookup_service as LS
from app.services import opera_period_service as PS

router = APIRouter(dependencies=[Depends(get_current_user)])

MAX_INDEX = 5.0     # 事件倍數上限（超過多半是打錯，例如把 130% 打成 130）
MIN_INDEX = 0.1


def _client_ip(request: Request) -> str | None:
    return request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else None
    )


def _user_name(user: User) -> str:
    return getattr(user, "full_name", "") or getattr(user, "username", "")


def _check_date(value: str, field: str) -> str:
    try:
        return PS.to_date(value).isoformat()
    except (ValueError, AttributeError, IndexError):
        raise HTTPException(status_code=400, detail=f"{field} 必須是 YYYY-MM-DD 格式")


# ══════════════════════════════════════════════════════════════════════════════
# 歷史同期查詢（評估文件 §3.1，需求 4）
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/lookup/date/{business_date}", summary="單日歷史同期查詢")
def lookup_date(
    business_date: str,
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_view")),
):
    return LS.get_date_lookup(db, _check_date(business_date, "business_date"), property_code)


@router.get("/lookup/period", summary="期間歷史同期查詢")
def lookup_period(
    start: str = Query(...),
    end: str = Query(...),
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_view")),
):
    return LS.get_period_lookup(
        db, _check_date(start, "start"), _check_date(end, "end"), property_code
    )


# ══════════════════════════════════════════════════════════════════════════════
# 係數
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/coefficients", summary="模型係數清單（含人工覆寫狀態）")
def get_coefficients(
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_forecast_view")),
):
    return FS.list_coefficients(db, property_code)


@router.post("/coefficients/fit", summary="重新估算係數（從歷史資料）")
def fit_coefficients(
    request: Request,
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opera_admin")),
):
    coef = FS.fit_coefficients(db, property_code)
    if not coef.is_usable:
        raise HTTPException(
            status_code=400,
            detail="資料不足以估算係數：" + ("；".join(coef.warnings) or "沒有可用的歷史日"),
        )
    written = FS.save_coefficients(
        db, coef, property_code,
        user_id=current_user.id, user_name=_user_name(current_user),
    )
    db.add(AuditLog(
        user_id=current_user.id,
        action="opera_forecast_fit",
        resource_type="opera_forecast_coefficient",
        resource_id=property_code or "(global)",
        ip_address=_client_ip(request),
        extra={
            "fit_start": coef.fit_start, "fit_end": coef.fit_end,
            "fit_days": coef.fit_days, "anchor_date": coef.anchor_date,
            "baseline_adr": round(coef.baseline_adr, 2),
            "growth_adr": round(coef.growth_adr, 4),
            "written": written,
        },
    ))
    db.flush()

    excluded = FS.load_excluded(db, coef.fit_start, coef.fit_end, property_code)
    return {
        "ok":       True,
        "written":  written,
        "fit_start": coef.fit_start,
        "fit_end":  coef.fit_end,
        "fit_days": coef.fit_days,
        "anchor_date":     coef.anchor_date,
        "baseline_adr":    round(coef.baseline_adr, 2),
        "baseline_occ":    round(coef.baseline_occ, 6),
        "growth_adr":      round(coef.growth_adr, 4),
        "growth_occ":      round(coef.growth_occ, 4),
        "available_rooms": round(coef.available_rooms, 1),
        "adr_interval":    [coef.adr_p10, coef.adr_p90],
        "occ_interval":    [coef.occ_p10, coef.occ_p90],
        "warnings":        coef.warnings,
        "excluded":        excluded,
        "excluded_count":  len(excluded),
        "note": "已被人工覆寫的係數不會被蓋掉（只更新對照用的自動估算值）。",
    }


@router.put("/coefficients", summary="人工覆寫係數")
def update_coefficients(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opera_admin")),
):
    """payload: {"property_code": "", "items": [{"id": 12, "value": 1.25, "is_manual": true}, ...]}

    `is_manual = false` 代表放棄人工值、改回自動估算值。
    """
    property_code = (payload.get("property_code") or "").strip()
    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="items 必須是非空的陣列")

    changed: list[dict] = []
    for item in items:
        row = db.query(OperaForecastCoefficient).filter(
            OperaForecastCoefficient.id == item.get("id")
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail=f"找不到係數 id={item.get('id')}")
        if row.property_code != property_code:
            raise HTTPException(status_code=400, detail="係數不屬於指定的飯店代碼")
        if row.kind not in COEF_EDITABLE_KINDS:
            raise HTTPException(
                status_code=400,
                detail=f"{row.kind} 係數是算出來的事實（錨點／區間），改了會讓模型自相矛盾，不開放覆寫",
            )

        before = float(row.value)
        want_manual = bool(item.get("is_manual", True))
        if not want_manual:
            row.is_manual = 0
            row.value = row.fitted_value
        else:
            try:
                value = float(item.get("value"))
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail=f"{row.kind}/{row.coef_key} 的值必須是數字")
            if value <= 0:
                raise HTTPException(status_code=400, detail=f"{row.kind}/{row.coef_key} 必須大於 0")
            if row.kind in ("dow", "month", "growth") and not (0.2 <= value <= 5.0):
                raise HTTPException(
                    status_code=400,
                    detail=f"{row.kind}/{row.coef_key} 的倍數 {value} 超出合理範圍（0.2～5.0）",
                )
            row.is_manual = 1
            row.value = value

        row.updated_at = twnow()
        row.updated_by_user_id = current_user.id
        row.updated_by_name = _user_name(current_user)
        changed.append({
            "id": row.id, "kind": row.kind, "coef_key": row.coef_key, "metric": row.metric,
            "before": before, "after": float(row.value), "is_manual": bool(row.is_manual),
        })

    db.add(AuditLog(
        user_id=current_user.id,
        action="opera_forecast_coefficient_update",
        resource_type="opera_forecast_coefficient",
        resource_id=property_code or "(global)",
        ip_address=_client_ip(request),
        extra={"changed": changed},
    ))
    db.flush()
    return {"ok": True, "changed": changed, **FS.list_coefficients(db, property_code)}


# ══════════════════════════════════════════════════════════════════════════════
# 預測
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/predict", summary="期間預測（含逐日、係數拆解、預測區間）")
def predict(
    start: str = Query(...),
    end: str | None = Query(None, description="留空 = 只預測 start 當天"),
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_forecast_view")),
):
    s = _check_date(start, "start")
    e = _check_date(end, "end") if end else s
    try:
        return FS.forecast_range(db, s, e, property_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/predict", summary="期間預測（可帶假設性事件、可存快照）")
def predict_with_scenario(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opera_forecast_view")),
):
    """payload:
    {
      "start": "2026-09-01", "end": "2026-09-30", "property_code": "",
      "events": [{"name": "國際電腦展", "start_date": "...", "end_date": "...",
                  "adr_index": 1.35, "occ_index": 1.1}],
      "save": false, "note": ""
    }

    `events` 是**假設情境**，不會寫入事件月曆。要長期保存請到事件月曆頁新增。
    """
    s = _check_date(payload.get("start") or "", "start")
    e = _check_date(payload.get("end") or payload.get("start") or "", "end")
    property_code = (payload.get("property_code") or "").strip()

    events = []
    for raw in (payload.get("events") or []):
        name = (raw.get("name") or "").strip()
        ev_s = _check_date(raw.get("start_date") or s, "events[].start_date")
        ev_e = _check_date(raw.get("end_date") or e, "events[].end_date")
        if ev_s > ev_e:
            raise HTTPException(status_code=400, detail=f"事件「{name}」的結束日早於起始日")
        try:
            adr_index = float(raw.get("adr_index", 1.0))
            occ_index = float(raw.get("occ_index", 1.0))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"事件「{name}」的倍數必須是數字")
        for label, v in (("ADR", adr_index), ("住房率", occ_index)):
            if not (MIN_INDEX <= v <= MAX_INDEX):
                raise HTTPException(
                    status_code=400,
                    detail=f"事件「{name}」的{label}倍數 {v} 超出合理範圍"
                           f"（{MIN_INDEX}～{MAX_INDEX}）。提醒：1.35 代表 +35%，不是 135。",
                )
        events.append({
            "name": name or "假設事件",
            "category": raw.get("category") or "其他",
            "start_date": ev_s, "end_date": ev_e,
            "adr_index": adr_index, "occ_index": occ_index,
        })

    try:
        result = FS.forecast_range(db, s, e, property_code, extra_events=events)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if result.get("ok") and payload.get("save"):
        run_id = FS.save_forecast_run(
            db, result, property_code,
            user_id=current_user.id, user_name=_user_name(current_user),
            note=(payload.get("note") or "")[:300],
        )
        db.add(AuditLog(
            user_id=current_user.id,
            action="opera_forecast_run_save",
            resource_type="opera_forecast_run",
            resource_id=str(run_id),
            ip_address=_client_ip(request),
            extra={"start": s, "end": e, "days": result["summary"]["days"],
                   "scenario_events": [ev["name"] for ev in events]},
        ))
        db.flush()
        result["saved_run_id"] = run_id

    result["scenario_events"] = events
    return result


@router.get("/backtest", summary="回測（嚴格切分訓練期／測試期，並列樸素基準）")
def backtest(
    property_code: str = Query(""),
    test_days: int = Query(365, ge=30, le=1095),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_forecast_view")),
):
    return FS.backtest(db, property_code, test_days=test_days)


# ══════════════════════════════════════════════════════════════════════════════
# 預測快照
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/runs", summary="預測快照清單")
def list_runs(
    property_code: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_forecast_view")),
):
    q = db.query(OperaForecastRun)
    if property_code:
        q = q.filter(OperaForecastRun.property_code == property_code)
    rows = q.order_by(OperaForecastRun.id.desc()).limit(limit).all()
    return {"items": [r.to_dict() for r in rows], "total": len(rows)}


@router.get("/runs/{run_id}", summary="預測快照明細")
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_forecast_view")),
):
    run = db.query(OperaForecastRun).filter(OperaForecastRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="找不到該筆預測快照")
    rows = (
        db.query(OperaForecastDaily)
        .filter(OperaForecastDaily.run_id == run_id)
        .order_by(OperaForecastDaily.business_date)
        .all()
    )
    return {"run": run.to_dict(), "items": [r.to_dict() for r in rows]}


@router.post("/runs/compare", summary="回填實際值並計算真實誤差")
def compare_runs(
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_forecast_view")),
):
    return FS.compare_runs_with_actual(db, property_code)


# ══════════════════════════════════════════════════════════════════════════════
# 事件月曆
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/events", summary="事件月曆清單")
def list_events(
    property_code: str = Query(""),
    start: str | None = Query(None),
    end: str | None = Query(None),
    include_inactive: bool = Query(True),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_forecast_view")),
):
    q = db.query(OperaEvent)
    if property_code:
        q = q.filter(OperaEvent.property_code.in_([property_code, ""]))
    if start and end:
        q = q.filter(
            OperaEvent.start_date <= _check_date(end, "end"),
            OperaEvent.end_date >= _check_date(start, "start"),
        )
    if not include_inactive:
        q = q.filter(OperaEvent.is_active == 1)

    rows = q.order_by(OperaEvent.start_date.desc()).all()
    return {
        "items":        [e.to_dict() for e in rows],
        "total":        len(rows),
        "categories":   EVENT_CATEGORIES,
        "min_samples":  MIN_EVENT_SAMPLES,
        "hint": f"同名事件累積 {MIN_EVENT_SAMPLES} 次以上才能改用「資料學習」的係數；"
                "少於這個次數等於拿單一樣本當結論。",
    }


def _apply_event_payload(row: OperaEvent, payload: dict) -> None:
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="事件名稱不可空白")
    category = (payload.get("category") or "其他").strip()
    if category not in EVENT_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"類別必須是：{'、'.join(EVENT_CATEGORIES)}",
        )
    start = _check_date(payload.get("start_date") or "", "start_date")
    end = _check_date(payload.get("end_date") or "", "end_date")
    if start > end:
        raise HTTPException(status_code=400, detail="結束日不可早於起始日")

    try:
        adr_index = float(payload.get("expected_adr_index", 1.0))
        occ_index = float(payload.get("expected_occ_index", 1.0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="預期倍數必須是數字")
    for label, v in (("ADR", adr_index), ("住房率", occ_index)):
        if not (MIN_INDEX <= v <= MAX_INDEX):
            raise HTTPException(
                status_code=400,
                detail=f"{label}倍數 {v} 超出合理範圍（{MIN_INDEX}～{MAX_INDEX}）。"
                       "提醒：1.35 代表 +35%，不是 135。",
            )

    source = payload.get("source") or EVENT_SOURCE_MANUAL
    if source not in (EVENT_SOURCE_MANUAL, EVENT_SOURCE_LEARNED):
        raise HTTPException(status_code=400, detail="source 只能是 manual 或 learned")
    # 樣本不足時不允許切到學習係數（評估文件 §3.4）
    if source == EVENT_SOURCE_LEARNED and row.sample_count < MIN_EVENT_SAMPLES:
        raise HTTPException(
            status_code=400,
            detail=f"這個事件只有 {row.sample_count} 次歷史紀錄（需 {MIN_EVENT_SAMPLES} 次），"
                   "不可採用資料學習的係數。請先按「學習事件係數」或維持人工設定。",
        )

    row.name = name[:120]
    row.category = category
    row.start_date = start
    row.end_date = end
    row.expected_adr_index = adr_index
    row.expected_occ_index = occ_index
    row.source = source
    row.is_active = 1 if payload.get("is_active", True) else 0
    row.note = (payload.get("note") or "")[:500]


@router.post("/events", summary="新增事件")
def create_event(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opera_event_admin")),
):
    row = OperaEvent(property_code=(payload.get("property_code") or "").strip())
    _apply_event_payload(row, payload)
    row.updated_by_user_id = current_user.id
    row.updated_by_name = _user_name(current_user)
    db.add(row)
    db.flush()

    db.add(AuditLog(
        user_id=current_user.id,
        action="opera_event_create",
        resource_type="opera_event",
        resource_id=str(row.id),
        ip_address=_client_ip(request),
        extra={"name": row.name, "start": row.start_date, "end": row.end_date,
               "adr_index": float(row.expected_adr_index)},
    ))
    db.flush()
    return {"ok": True, "item": row.to_dict()}


@router.put("/events/{event_id}", summary="修改事件")
def update_event(
    event_id: int,
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opera_event_admin")),
):
    row = db.query(OperaEvent).filter(OperaEvent.id == event_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="找不到該事件")

    before = row.to_dict()
    _apply_event_payload(row, payload)
    row.updated_at = twnow()
    row.updated_by_user_id = current_user.id
    row.updated_by_name = _user_name(current_user)
    db.flush()

    db.add(AuditLog(
        user_id=current_user.id,
        action="opera_event_update",
        resource_type="opera_event",
        resource_id=str(event_id),
        ip_address=_client_ip(request),
        extra={"before": {k: before[k] for k in
                          ("name", "category", "start_date", "end_date",
                           "expected_adr_index", "expected_occ_index", "is_active")},
               "after": {"name": row.name, "category": row.category,
                         "start_date": row.start_date, "end_date": row.end_date,
                         "expected_adr_index": float(row.expected_adr_index),
                         "expected_occ_index": float(row.expected_occ_index),
                         "is_active": bool(row.is_active)}},
    ))
    db.flush()
    return {"ok": True, "item": row.to_dict()}


@router.delete("/events/{event_id}", summary="刪除事件")
def delete_event(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opera_event_admin")),
):
    """事件月曆是人工維護的設定資料，允許真的刪除。

    刪除前的內容會寫入稽核日誌，需要追溯時查得到。
    若只是暫時不想套用，建議改用「停用」（is_active = false）而不是刪除。
    """
    row = db.query(OperaEvent).filter(OperaEvent.id == event_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="找不到該事件")

    snapshot = row.to_dict()
    db.delete(row)
    db.add(AuditLog(
        user_id=current_user.id,
        action="opera_event_delete",
        resource_type="opera_event",
        resource_id=str(event_id),
        ip_address=_client_ip(request),
        extra={"deleted": {k: snapshot[k] for k in
                           ("name", "category", "start_date", "end_date",
                            "expected_adr_index", "expected_occ_index", "note")}},
    ))
    db.flush()
    return {"ok": True, "deleted_id": event_id}


@router.post("/events/learn", summary="從歷史資料學習事件係數")
def learn_events(
    request: Request,
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opera_event_admin")),
):
    result = FS.learn_event_coefficients(db, property_code)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("reason", "學習失敗"))

    db.add(AuditLog(
        user_id=current_user.id,
        action="opera_event_learn",
        resource_type="opera_event",
        resource_id=property_code or "(global)",
        ip_address=_client_ip(request),
        extra={"total": result["total"], "reliable": result["reliable_count"]},
    ))
    db.flush()
    return result
