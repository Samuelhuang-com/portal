"""
競品分析 — 查詢 API

Prefix: `/api/v1/compset`
規格書：`docs/SPEC_compset_analysis.md` §8

⚠️ **全部端點皆為同步 `def`** —— `async def` 內直接呼叫同步 `db.query()`
   會凍結整站（記憶 project_async_def_blocking_fix，Portal 曾因此全站無回應）。
   唯一例外是必須 `await UploadFile.read()` 的 CSV 匯入端點（在 `compset_admin.py`）。

⚠️ **訂閱隔離**：每個端點都先 `resolve_subscriber_id()` 解出當前使用者的訂閱，
   **不接受前端直接指定**。持有 `compset_subscriber_admin` 的人可以切換檢視對象，
   但仍然由後端驗證，不是靠前端隱藏下拉選單。
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import (get_current_user, get_user_permissions,
                              require_permission)
from app.models.compset_analysis import (CompsetFetchLog, CompsetHotel,
                                         CompsetRateSnapshot,
                                         CompsetSubscriber)
from app.models.user import User
from app.services import compset_quota_service as QS
from app.services import compset_stats_service as S

router = APIRouter(dependencies=[Depends(get_current_user)])

_VIEW = require_permission("compset_view")
_MATRIX = require_permission("compset_matrix_view")
_TREND = require_permission("compset_trend_view")

INTERNAL_CODE = "INTERNAL"


# ══════════════════════════════════════════════════════════════════════════
# 訂閱解析
# ══════════════════════════════════════════════════════════════════════════
def resolve_subscriber_id(db: Session, user: User, requested: int | None,
                          *, allow_any: bool = False) -> int:
    """
    解出這次請求該用哪個訂閱客戶。

    規則（SPEC §8）：
      · 有指定 `subscriber_id`：`allow_any`（＝持有 `compset_subscriber_admin`）
        才准跨訂閱；否則必須是自己所屬的訂閱，不是就 403。
      · 沒指定：取自己所屬的第一個訂閱。
      · **完全沒有歸屬的使用者 → 用 `INTERNAL`**。
        這是刻意的（SPEC D14）：內部人員不會登錄在 `compset_subscriber_users` 裡，
        但他們要看的本來就是 INTERNAL 那一份。外部客戶一定有歸屬。
    """
    mine = QS.user_subscriber_ids(db, user.id)

    if requested is not None:
        if allow_any or requested in mine:
            return requested
        raise HTTPException(status_code=403, detail="沒有這個訂閱客戶的檢視權限")

    if mine:
        return sorted(mine)[0]

    internal = db.execute(
        select(CompsetSubscriber.id)
        .where(CompsetSubscriber.code == INTERNAL_CODE)
    ).scalar_one_or_none()
    if internal is not None:
        return internal

    first = db.execute(
        select(CompsetSubscriber.id)
        .where(CompsetSubscriber.is_active.is_(True))
        .order_by(CompsetSubscriber.id).limit(1)
    ).scalar_one_or_none()
    if first is None:
        raise HTTPException(status_code=404,
                            detail="尚未建立任何訂閱客戶（請先跑 "
                                   "scripts/compset_seed_internal.py）")
    return first


def is_subscriber_admin(db: Session, user: User) -> bool:
    """
    是否可以跨訂閱檢視。

    ⚠️ 用 `get_user_permissions()` 直接問，**不要**呼叫 `require_permission()`
       —— 那支是 FastAPI dependency，會直接丟 403 把整個請求擋掉；
       這裡只是想「問問看有沒有」。
    ⚠️ `"*"` 是 system_admin 的萬用符，要一併認。
    """
    perms = get_user_permissions(user.id, db)
    return "*" in perms or "compset_subscriber_admin" in perms


# ══════════════════════════════════════════════════════════════════════════
# 端點
# ══════════════════════════════════════════════════════════════════════════
@router.get("/dashboard", summary="競品分析 Dashboard")
def get_dashboard(subscriber_id: int | None = Query(None),
                  db: Session = Depends(get_db),
                  current_user: User = Depends(_VIEW)):
    """
    ⚠️ 指數與排名一律附帶 `sample_count` / `is_low_sample`。
       只回一個數字會讓「4 家算出來的指數」和「1 家算出來的指數」長得一模一樣。
    """
    sid = resolve_subscriber_id(db, current_user, subscriber_id,
                                allow_any=is_subscriber_admin(db, current_user))
    data = S.dashboard(db, sid)
    data["quota"] = QS.quota_status(db, sid)
    data["subscriber"] = _subscriber_brief(db, sid)
    return data


@router.get("/rates/matrix", summary="價格矩陣")
def get_matrix(stay_from: str = Query(..., description="入住日起（YYYY-MM-DD）"),
               stay_to: str = Query(..., description="入住日迄"),
               snapshot_date: str | None = Query(None, description="留空 ＝ 最新一批"),
               subscriber_id: int | None = Query(None),
               db: Session = Depends(get_db),
               current_user: User = Depends(_MATRIX)):
    sid = resolve_subscriber_id(db, current_user, subscriber_id,
                                allow_any=is_subscriber_admin(db, current_user))
    _check_range(stay_from, stay_to)
    return S.matrix(db, sid, stay_from=stay_from, stay_to=stay_to,
                    snapshot_date=snapshot_date)


@router.get("/rates/trend", summary="價格軌跡（固定入住日，看各快照日）")
def get_trend(stay_date: str = Query(..., description="入住日（YYYY-MM-DD）"),
              snapshot_from: str | None = Query(None),
              snapshot_to: str | None = Query(None),
              subscriber_id: int | None = Query(None),
              db: Session = Depends(get_db),
              current_user: User = Depends(_TREND)):
    """⭐ 這張圖是 `snapshot_date` 進唯一鍵的唯一目的（SPEC §5.5）。"""
    sid = resolve_subscriber_id(db, current_user, subscriber_id,
                                allow_any=is_subscriber_admin(db, current_user))
    return S.trend(db, sid, stay_date=stay_date,
                   snapshot_from=snapshot_from, snapshot_to=snapshot_to)


@router.get("/rates/detail", summary="明細 Drawer")
def get_detail(snapshot_id: int = Query(...),
               db: Session = Depends(get_db),
               current_user: User = Depends(_MATRIX)):
    """
    單一格的明細（CLAUDE.md §7 的 Drawer）。

    ⚠️ 非 Ragic 模組沒有 `ragic_url`，原始連結改用該筆報價的通路資訊
       （等價替代，比照 `SPEC_ota_reviews.md` §9.3）。
    ⚠️ 仍然要檢查這筆屬不屬於使用者的訂閱 —— 直接吃 id 不檢查等於全庫可讀。
    """
    row = db.get(CompsetRateSnapshot, snapshot_id)
    if row is None:
        raise HTTPException(status_code=404, detail="找不到這筆快照")
    sid = resolve_subscriber_id(db, current_user, row.subscriber_id,
                                allow_any=is_subscriber_admin(db, current_user))
    if sid != row.subscriber_id:
        raise HTTPException(status_code=403, detail="沒有這筆資料的檢視權限")

    hotel = db.get(CompsetHotel, row.compset_hotel_id)
    import json as _json
    offers = _json.loads(row.raw_json) if row.raw_json else []
    return {
        "id": row.id,
        "hotel": {"id": hotel.id if hotel else None,
                  "name": hotel.display_name if hotel else "",
                  "is_self": bool(hotel.is_self) if hotel else False,
                  "room_count": hotel.room_count if hotel else None,
                  "registered_address": hotel.registered_address if hotel else ""},
        "snapshot_date": row.snapshot_date,
        "stay_date": row.stay_date,
        "tier": row.tier,
        "fetch_path": row.fetch_path,
        "source": row.source,
        "price_gross": float(row.price_gross) if row.price_gross is not None else None,
        "price_pretax": float(row.price_pretax) if row.price_pretax is not None else None,
        "currency": row.currency,
        "tax_included": row.tax_included,
        "is_sold_out": row.is_sold_out,
        "ota_name": row.ota_name,
        "is_official": bool(row.is_official),
        "num_guests": row.num_guests,
        "free_cancellation": bool(row.free_cancellation),
        "room_type_raw": row.room_type_raw,
        "typical_low": float(row.typical_low) if row.typical_low is not None else None,
        "typical_high": float(row.typical_high) if row.typical_high is not None else None,
        # 精簡後的通路報價（`raw_json`）。日後做 rate parity 的原料
        "offers": offers,
        "created_at": row.created_at,
    }


@router.get("/logs", summary="抓取批次紀錄")
def get_logs(limit: int = Query(50, le=500),
             subscriber_id: int | None = Query(None),
             db: Session = Depends(get_db),
             current_user: User = Depends(_VIEW)):
    """⚠️ `warnings` 與 `error_message` 分開回傳，畫面要用不同顏色。"""
    import json as _json
    sid = resolve_subscriber_id(db, current_user, subscriber_id,
                                allow_any=is_subscriber_admin(db, current_user))
    rows = db.execute(
        select(CompsetFetchLog)
        .where(CompsetFetchLog.subscriber_id == sid)
        .order_by(CompsetFetchLog.started_at.desc())
        .limit(limit)
    ).scalars().all()
    return {"items": [{
        "id": r.id, "tier": r.tier, "fetch_path": r.fetch_path,
        "started_at": r.started_at, "finished_at": r.finished_at,
        "stay_date_from": r.stay_date_from, "stay_date_to": r.stay_date_to,
        "request_count": r.request_count, "row_count": r.row_count,
        "quota_before": r.quota_before, "quota_after": r.quota_after,
        "status": r.status,
        "params": _json.loads(r.params_json) if r.params_json else None,
        "warnings": _json.loads(r.warnings_json) if r.warnings_json else [],
        "error_message": r.error_message,
    } for r in rows]}


# ══════════════════════════════════════════════════════════════════════════
# 小工具
# ══════════════════════════════════════════════════════════════════════════
def _subscriber_brief(db: Session, subscriber_id: int) -> dict:
    sub = db.get(CompsetSubscriber, subscriber_id)
    if sub is None:
        return {}
    return {"id": sub.id, "code": sub.code, "name": sub.name,
            "plan_level": sub.plan_level, "is_active": bool(sub.is_active)}


def _check_range(stay_from: str, stay_to: str) -> None:
    try:
        a, b = date.fromisoformat(stay_from), date.fromisoformat(stay_to)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"日期格式錯誤：{exc}") from exc
    if b < a:
        raise HTTPException(status_code=400, detail="入住日迄不可早於起日")
    if (b - a).days > 400:
        # 400 天上限：C 級最遠 120 天，留很大餘裕，但擋掉「一次拉十年」的查詢
        raise HTTPException(status_code=400, detail="區間過長（上限 400 天）")
