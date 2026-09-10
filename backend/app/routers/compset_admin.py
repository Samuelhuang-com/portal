"""
競品分析 — 管理 API（競爭組、訂閱與配額、抓取節奏、手動觸發、CSV 匯入）

Prefix: `/api/v1/compset`
規格書：`docs/SPEC_compset_analysis.md` §8、§3.5

⚠️ **全部同步 `def`**，唯一例外是 `POST /import/upload`
   （必須 `await UploadFile.read()`）。

⚠️ **本檔案有本模組唯一會碰到錢的端點**（`/subscribers/{id}/grant-quota`）。
   防提權三條（SPEC §3.5）：
     P-1 不得對自己所屬的訂閱加發 —— 由 `compset_quota_service.grant_quota()` 強制
     P-2 只有 `compset_subscriber_admin` 可呼叫 —— 這裡的 `_SUB_ADMIN` 把關
     P-3 同時寫 `compset_quota_grants` 與 `audit_logs` —— service 層做
"""
from __future__ import annotations

from fastapi import (APIRouter, Body, Depends, File, HTTPException, Query,
                     Request, Response, UploadFile)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.audit_log import AuditLog
from app.models.compset_analysis import (PLAN_LEVELS, CompsetHotel,
                                         CompsetSubscriber,
                                         CompsetSubscriberUser)
from app.models.user import User
from app.routers.compset_rates import (is_subscriber_admin,
                                       resolve_subscriber_id)
from app.services import compset_fetch_service as F
from app.services import compset_import_service as IS
from app.services import compset_quota_service as QS
from app.services import compset_search_service as SEARCH
from app.services import compset_stats_service as S

router = APIRouter(dependencies=[Depends(get_current_user)])

_HOTELS = require_permission("compset_hotels_admin")
_SETTINGS = require_permission("compset_settings_admin")
_SUB_ADMIN = require_permission("compset_subscriber_admin")
_RUN = require_permission("compset_fetch_run")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _client_ip(request: Request) -> str | None:
    return request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else None
    )


def _attachment_headers(utf8_name: str, ascii_name: str) -> dict[str, str]:
    """
    中文檔名的 `Content-Disposition`（RFC 5987）。

    ⚠️ HTTP header 只能放 latin-1，中文檔名直接塞會 `UnicodeEncodeError` → **500**，
       而且是在回應組裝階段炸掉，前端只看到「下載失敗」。
       這個坑在 OTA 模組出現過兩次，所以這裡照抄正確寫法。
    """
    from urllib.parse import quote
    return {"Content-Disposition":
            f'attachment; filename="{ascii_name}"; '
            f"filename*=UTF-8''{quote(utf8_name)}"}


# ══════════════════════════════════════════════════════════════════════════
# 1. 競爭組
# ══════════════════════════════════════════════════════════════════════════
def _assert_exactly_one_self(db: Session, subscriber_id: int) -> None:
    """
    ⭐ 每個訂閱必須恰有一筆 `is_self`（SPEC §4.3）。

    ⚠️ DB 層沒辦法用簡單 constraint 表達「恰一筆」，所以這條規則**只在這裡**。
       改 CRUD 時不要繞過 —— 缺了它，價位指數的分子分母都算不出來，
       而畫面只會顯示「沒有資料」，看不出是設定錯了。
    """
    n = len(db.execute(
        select(CompsetHotel.id).where(CompsetHotel.subscriber_id == subscriber_id,
                                      CompsetHotel.is_self.is_(True))
    ).scalars().all())
    if n != 1:
        raise HTTPException(
            status_code=400,
            detail=f"競爭組必須恰有一家標記為「自己」，目前有 {n} 家。"
                   "價位指數的分子與分母都靠它。")


def _hotel_out(h: CompsetHotel) -> dict:
    return {"id": h.id, "subscriber_id": h.subscriber_id,
            "hotel_code": h.hotel_code, "display_name": h.display_name,
            "short_name": h.short_name, "short_label": h.short_label,
            "google_property_token": h.google_property_token,
            "google_query_name": h.google_query_name,
            "is_self": bool(h.is_self), "is_enabled": bool(h.is_enabled),
            "sort_order": h.sort_order, "room_count": h.room_count,
            "registered_address": h.registered_address, "note": h.note,
            "latitude": float(h.latitude) if h.latitude is not None else None,
            "longitude": float(h.longitude) if h.longitude is not None else None,
            "has_token": bool((h.google_property_token or "").strip())}


@router.get("/hotels", summary="競爭組清單")
def list_hotels(subscriber_id: int | None = Query(None),
                db: Session = Depends(get_db),
                current_user: User = Depends(_HOTELS)):
    sid = resolve_subscriber_id(db, current_user, subscriber_id,
                                allow_any=is_subscriber_admin(db, current_user))
    rows = db.execute(
        select(CompsetHotel).where(CompsetHotel.subscriber_id == sid)
        .order_by(CompsetHotel.sort_order, CompsetHotel.id)
    ).scalars().all()
    missing = [h.display_name for h in rows
               if not (h.google_property_token or "").strip()]
    return {
        "items": [_hotel_out(h) for h in rows],
        # ⚠️ 缺 token 的家 A 級抓不到（會記 warning）。畫面要提示，不要讓人以為壞了。
        "warnings": ([f"以下競爭組成員缺 property_token，A 級抓取會跳過："
                      f"{'、'.join(missing)}"] if missing else []),
    }


@router.post("/hotels", summary="新增競爭組成員")
def create_hotel(payload: dict = Body(...), db: Session = Depends(get_db),
                 current_user: User = Depends(_HOTELS)):
    sid = resolve_subscriber_id(db, current_user, payload.get("subscriber_id"),
                                allow_any=is_subscriber_admin(db, current_user))
    name = (payload.get("display_name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="display_name 不可空白")

    row = CompsetHotel(subscriber_id=sid, display_name=name)
    _apply_hotel(row, payload)
    db.add(row)
    db.flush()
    _assert_exactly_one_self(db, sid)
    db.commit()
    return {"ok": True, "item": _hotel_out(row)}


@router.post("/hotels/search", summary="搜尋競爭組候選（⚠️ 會扣配額）")
def search_hotels(request: Request, payload: dict = Body(default={}),
                  subscriber_id: int | None = Query(None),
                  db: Session = Depends(get_db),
                  current_user: User = Depends(_HOTELS)):
    """
    跑一次地點查詢，回傳候選飯店（含經緯度）供地圖與清單挑選。

    ⚠️⚠️ **會扣配額**（每頁 1 次）。這是排程以外的第二個花錢入口，
       所以與排程走完全相同的手續：原子預留 → 送出前 commit → 寫 fetch_logs。

    ⚠️ 權限沿用 `compset_hotels_admin`（能改競爭組的人就能搜尋）——
       改競爭組本來就會影響成本，再多開一個 key 只會讓權限表更難維護。

    ⚠️ 搜尋不到的家**仍然要手動新增**。地圖不是完整世界地圖，
       是「這次查詢回了什麼」（P0 實測五月家不在前 38 名裡）。
    """
    sid = resolve_subscriber_id(db, current_user, subscriber_id,
                                allow_any=is_subscriber_admin(db, current_user))
    pages = int(payload.get("pages") or 1)
    db.add(AuditLog(user_id=current_user.id, action="compset_hotel_search",
                    resource_type="compset_subscriber", resource_id=str(sid),
                    ip_address=_client_ip(request),
                    extra={"q": payload.get("q") or "", "pages": pages}))
    db.commit()
    try:
        return SEARCH.search_candidates(
            db, sid, q=payload.get("q") or "",
            check_in_date=payload.get("check_in_date") or "", pages=pages)
    except SEARCH.QuotaUnavailable as exc:
        # 402 Payment Required：語意上剛好 —— 不是壞掉，是額度不夠
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except SEARCH.SearchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/hotels/{hotel_id}", summary="修改競爭組成員")
def update_hotel(hotel_id: int, payload: dict = Body(...),
                 db: Session = Depends(get_db),
                 current_user: User = Depends(_HOTELS)):
    row = db.get(CompsetHotel, hotel_id)
    if row is None:
        raise HTTPException(status_code=404, detail="找不到這筆競爭組成員")
    resolve_subscriber_id(db, current_user, row.subscriber_id,
                          allow_any=is_subscriber_admin(db, current_user))
    _apply_hotel(row, payload)
    db.flush()
    _assert_exactly_one_self(db, row.subscriber_id)
    db.commit()
    return {"ok": True, "item": _hotel_out(row)}


@router.delete("/hotels/{hotel_id}", summary="刪除競爭組成員")
def delete_hotel(hotel_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(_HOTELS)):
    """
    ⚠️ 已有快照的成員**不可刪除**（FK 是 RESTRICT）——
       刪了歷史就對不回去了。要停用請改 `is_enabled=false`。
    """
    row = db.get(CompsetHotel, hotel_id)
    if row is None:
        raise HTTPException(status_code=404, detail="找不到這筆競爭組成員")
    sid = row.subscriber_id
    resolve_subscriber_id(db, current_user, sid,
                          allow_any=is_subscriber_admin(db, current_user))
    if row.is_self:
        raise HTTPException(status_code=400,
                            detail="不可刪除標記為「自己」的那一家。"
                                   "請先把 is_self 移到別家。")
    try:
        db.delete(row)
        db.flush()
    except Exception as exc:                                        # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="這家已經有歷史快照，不能刪除（刪了歷史就對不回去）。"
                   "請改成停用（is_enabled=false）。") from exc
    _assert_exactly_one_self(db, sid)
    db.commit()
    return {"ok": True}


def _apply_hotel(row: CompsetHotel, payload: dict) -> None:
    for field in ("hotel_code", "display_name", "short_name",
                  "google_property_token",
                  "google_query_name", "registered_address", "note"):
        if field in payload:
            setattr(row, field, (payload.get(field) or "").strip())
    for field in ("is_self", "is_enabled"):
        if field in payload:
            setattr(row, field, bool(payload.get(field)))
    for field in ("sort_order", "room_count"):
        if field in payload:
            v = payload.get(field)
            setattr(row, field, int(v) if v not in ("", None) else None)
    # ⚠️ 經緯度可以是 NULL（手動新增的家不一定有），空字串要轉成 None 不是 0.0 ——
    #    0.0 是幾內亞灣外海，地圖上會出現一個莫名其妙的點。
    for field in ("latitude", "longitude"):
        if field in payload:
            v = payload.get(field)
            setattr(row, field, float(v) if v not in ("", None) else None)
    if row.sort_order is None:
        row.sort_order = 0


# ══════════════════════════════════════════════════════════════════════════
# 2. 訂閱與配額
# ══════════════════════════════════════════════════════════════════════════
def _subscriber_out(db: Session, sub: CompsetSubscriber) -> dict:
    st = QS.quota_status(db, sub.id)
    return {
        "id": sub.id, "code": sub.code, "name": sub.name,
        "plan_level": sub.plan_level, "is_active": bool(sub.is_active),
        "location_query": sub.location_query,
        "windows": {"A": sub.window_a_days, "B": sub.window_b_days,
                    "C": sub.window_c_days},
        "freqs": {"A": sub.freq_a_days, "B": sub.freq_b_days, "C": sub.freq_c_days},
        "params": {"adults": sub.param_adults, "nights": sub.param_nights,
                   "gl": sub.param_gl, "hl": sub.param_hl,
                   "currency": sub.param_currency},
        "contact_name": sub.contact_name, "contact_email": sub.contact_email,
        "note": sub.note,
        "quota": st,
    }


@router.get("/subscribers", summary="訂閱客戶清單")
def list_subscribers(db: Session = Depends(get_db),
                     current_user: User = Depends(_SUB_ADMIN)):
    rows = db.execute(select(CompsetSubscriber)
                      .order_by(CompsetSubscriber.id)).scalars().all()
    return {"items": [_subscriber_out(db, s) for s in rows]}


@router.put("/subscribers/{subscriber_id}", summary="修改訂閱設定")
def update_subscriber(subscriber_id: int, payload: dict = Body(...),
                      db: Session = Depends(get_db),
                      current_user: User = Depends(_SUB_ADMIN)):
    """
    ⚠️ `quota_anchor_day` 只接受 1～28（`validate_anchor_day` 擋）。
       29～31 在 2 月會歸零失敗，而且一年只有一兩個月會出錯、極難發現。
    """
    sub = db.get(CompsetSubscriber, subscriber_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="找不到這筆訂閱客戶")

    if "plan_level" in payload:
        level = (payload.get("plan_level") or "A").upper()
        if level not in PLAN_LEVELS:
            raise HTTPException(status_code=400,
                                detail=f"plan_level 只接受 {'/'.join(PLAN_LEVELS)}")
        sub.plan_level = level
    if "quota_anchor_day" in payload:
        try:
            sub.quota_anchor_day = QS.validate_anchor_day(int(payload["quota_anchor_day"]))
        except (QS.InvalidAnchorDay, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    for field in ("name", "location_query", "contact_name", "contact_email", "note"):
        if field in payload:
            setattr(sub, field, (payload.get(field) or "").strip())
    if "monthly_quota" in payload:
        sub.monthly_quota = max(int(payload["monthly_quota"]), 0)
    if "is_active" in payload:
        sub.is_active = bool(payload["is_active"])

    db.commit()
    return {"ok": True, "item": _subscriber_out(db, sub)}


@router.post("/subscribers/{subscriber_id}/grant-quota", summary="手動加發配額")
def grant_quota(subscriber_id: int, request: Request, payload: dict = Body(...),
                db: Session = Depends(get_db),
                current_user: User = Depends(_SUB_ADMIN)):
    """
    ⭐ 本模組唯一會提高額度的端點。

    P-1（不得對自己所屬的訂閱加發）與 P-3（雙份紀錄）在 service 層強制；
    P-2 由 `_SUB_ADMIN` 把關。**不要在這裡「順手」放寬任何一條。**

    ⚠️ 加發**不修改 `monthly_quota`**，只加在當期 —— 避免「臨時加一次」
       變成「永久漲價」。
    """
    try:
        row = QS.grant_quota(
            db, subscriber_id=subscriber_id,
            granted_qty=int(payload.get("granted_qty") or 0),
            reason=payload.get("reason") or "",
            granted_by_user_id=current_user.id,
            ip_address=_client_ip(request),
        )
    except QS.SelfGrantForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (QS.InvalidGrant, QS.SubscriberNotFound, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return {"ok": True, "granted_qty": row.granted_qty,
            "period_start": row.period_start,
            "quota": QS.quota_status(db, subscriber_id)}


@router.get("/subscribers/{subscriber_id}/grants", summary="加發紀錄")
def list_grants(subscriber_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(_SUB_ADMIN)):
    rows = QS.list_grants(db, subscriber_id)
    return {"items": [{"id": r.id, "granted_qty": r.granted_qty,
                       "reason": r.reason, "period_start": r.period_start,
                       "granted_by_user_id": r.granted_by_user_id,
                       "granted_at": r.granted_at} for r in rows]}


@router.get("/subscribers/{subscriber_id}/users", summary="訂閱歸屬的使用者")
def list_subscriber_users(subscriber_id: int, db: Session = Depends(get_db),
                          current_user: User = Depends(_SUB_ADMIN)):
    """⚠️ 這份名單是防提權 P-1 的依據（SPEC D14），不是單純的顯示欄位。"""
    rows = db.execute(
        select(CompsetSubscriberUser)
        .where(CompsetSubscriberUser.subscriber_id == subscriber_id)
    ).scalars().all()
    return {"items": [{"id": r.id, "user_id": r.user_id,
                       "created_at": r.created_at} for r in rows]}


# ══════════════════════════════════════════════════════════════════════════
# 3. 抓取節奏
# ══════════════════════════════════════════════════════════════════════════
@router.get("/settings/cadence", summary="抓取節奏設定（含成本試算）")
def get_cadence(subscriber_id: int | None = Query(None),
                db: Session = Depends(get_db),
                current_user: User = Depends(_SETTINGS)):
    sid = resolve_subscriber_id(db, current_user, subscriber_id,
                                allow_any=is_subscriber_admin(db, current_user))
    sub = db.get(CompsetSubscriber, sid)
    return {"subscriber": _subscriber_out(db, sub),
            "estimate": _estimate(db, sub)}


@router.put("/settings/cadence", summary="修改抓取節奏")
def put_cadence(payload: dict = Body(...), subscriber_id: int | None = Query(None),
                db: Session = Depends(get_db),
                current_user: User = Depends(_SETTINGS)):
    """
    ⚠️ **改任何一個擷取參數（gl／hl／currency／adults／nights）都是資料斷點**
       —— 前後期的價格不再可比。回應會帶 `data_break_warning`，
       畫面必須顯示出來再讓人確認。

    ⚠️ 窗口必須遞增（A < B < C），否則 `tier_window()` 會算出負區間，
       該級別整個不跑而且不會有任何錯誤訊息。
    """
    sid = resolve_subscriber_id(db, current_user, subscriber_id,
                                allow_any=is_subscriber_admin(db, current_user))
    sub = db.get(CompsetSubscriber, sid)

    breaks: list[str] = []
    for field, label in (("param_adults", "入住人數"), ("param_nights", "住宿晚數"),
                         ("param_gl", "國別"), ("param_hl", "語系"),
                         ("param_currency", "幣別")):
        if field in payload and str(payload[field]) != str(getattr(sub, field)):
            breaks.append(f"{label}：{getattr(sub, field)} → {payload[field]}")

    for field in ("window_a_days", "window_b_days", "window_c_days",
                  "freq_a_days", "freq_b_days", "freq_c_days",
                  "param_adults", "param_nights"):
        if field in payload:
            setattr(sub, field, max(int(payload[field]), 1))
    for field in ("param_gl", "param_hl", "param_currency"):
        if field in payload:
            setattr(sub, field, (payload[field] or "").strip())

    if not (sub.window_a_days < sub.window_b_days < sub.window_c_days):
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"窗口必須遞增：A({sub.window_a_days}) < B({sub.window_b_days}) "
                   f"< C({sub.window_c_days})。否則該級別會整個不跑而且沒有錯誤訊息。")

    db.commit()
    est = _estimate(db, sub)
    return {
        "ok": True,
        "subscriber": _subscriber_out(db, sub),
        "estimate": est,
        "data_break_warning": (
            "以下參數已變更，前後期的價格不再可比（SPEC §5.6）：" + "；".join(breaks)
        ) if breaks else None,
        "over_quota_warning": (
            f"以目前設定每月約需 {est['total']} 次查詢，超過配額 "
            f"{est['monthly_quota']} 次 —— 月中就會被硬停。"
        ) if est["over_quota"] else None,
    }


def _estimate(db: Session, sub: CompsetSubscriber) -> dict:
    n = len(db.execute(
        select(CompsetHotel.id).where(
            CompsetHotel.subscriber_id == sub.id,
            CompsetHotel.is_enabled.is_(True),
            CompsetHotel.google_property_token != "")
    ).scalars().all())
    return F.estimate_monthly_requests(sub, token_hotel_count=n)


# ══════════════════════════════════════════════════════════════════════════
# 4. 手動觸發與重算
# ══════════════════════════════════════════════════════════════════════════
@router.post("/fetch/run", summary="手動觸發抓取")
def run_fetch(request: Request, payload: dict = Body(default={}),
              subscriber_id: int | None = Query(None),
              db: Session = Depends(get_db),
              current_user: User = Depends(_RUN)):
    """
    ⚠️ **會真的花錢**（每次查詢都扣配額）。所以：
      · 寫 `audit_log`，誰按的要查得到
      · 只跑「今天該跑」的級別（錨定日判定），不會因為多按幾次就多抓
        —— 但**配額仍然會被扣**，因為 API 真的送出去了。
    """
    sid = resolve_subscriber_id(db, current_user, subscriber_id,
                                allow_any=is_subscriber_admin(db, current_user))
    sub = db.get(CompsetSubscriber, sid)
    if sub is None:
        raise HTTPException(status_code=404, detail="找不到這筆訂閱客戶")

    tiers = tuple(t.upper() for t in (payload.get("tiers") or []) if t) or None
    db.add(AuditLog(user_id=current_user.id, action="compset_fetch_run",
                    resource_type="compset_subscriber", resource_id=str(sid),
                    ip_address=_client_ip(request),
                    extra={"tiers": list(tiers) if tiers else "auto"}))
    db.commit()

    results = F.fetch_subscriber(db, sub, only_tiers=tiers)
    stay_dates = [r for r in results if r.stay_date_from]
    if stay_dates:
        S.recompute_daily(db, sid,
                          stay_from=min(r.stay_date_from for r in stay_dates),
                          stay_to=max(r.stay_date_to for r in stay_dates))
        db.commit()
    return {"ok": True,
            "results": [{"tier": r.tier, "status": r.status,
                         "request_count": r.request_count,
                         "row_count": r.row_count,
                         "stay_date_from": r.stay_date_from,
                         "stay_date_to": r.stay_date_to,
                         "warnings": r.warnings,
                         "error_message": r.error_message} for r in results],
            "quota": QS.quota_status(db, sid)}


@router.post("/stats/recompute", summary="重算彙總快取")
def recompute(payload: dict = Body(default={}),
              subscriber_id: int | None = Query(None),
              db: Session = Depends(get_db),
              current_user: User = Depends(_SETTINGS)):
    """
    ⚠️ `compset_rate_daily` 是**快取不是來源**。
       數字怪怪的第一件事是按這裡重算，不是去改那張表。
       這支不打任何外部 API，**不花錢**。
    """
    sid = resolve_subscriber_id(db, current_user, subscriber_id,
                                allow_any=is_subscriber_admin(db, current_user))
    n = S.recompute_daily(db, sid,
                          snapshot_date=payload.get("snapshot_date"),
                          stay_from=payload.get("stay_from"),
                          stay_to=payload.get("stay_to"))
    db.commit()
    return {"ok": True, "rows": n}


# ══════════════════════════════════════════════════════════════════════════
# 5. CSV 備援
# ══════════════════════════════════════════════════════════════════════════
@router.get("/import/template", summary="CSV 匯入範本")
def import_template(current_user: User = Depends(_HOTELS)):
    return Response(
        content=IS.csv_template(),
        media_type="text/csv; charset=utf-8",
        headers=_attachment_headers("競品價格匯入範本.csv", "compset_template.csv"),
    )


@router.post("/import/upload", summary="CSV 備援匯入")
async def import_upload(file: UploadFile = File(...),
                        subscriber_id: int | None = Query(None),
                        db: Session = Depends(get_db),
                        current_user: User = Depends(_HOTELS)):
    """
    ⚠️ 這是本模組**唯一**的 `async def` —— 因為必須 `await UploadFile.read()`。
       讀完檔案之後不要再做任何同步 DB 以外的事。

    ⚠️ 匯入的資料 `source='csv'`，**不會覆蓋** SerpApi 那一列（D16）；
       統計時採 SerpApi。CSV 是補上抓不到的格子。
    """
    sid = resolve_subscriber_id(db, current_user, subscriber_id,
                                allow_any=is_subscriber_admin(db, current_user))
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413,
                            detail=f"檔案過大（上限 {MAX_UPLOAD_BYTES // 1024 // 1024}MB）")

    result = IS.import_rates(db, subscriber_id=sid, content=content)
    if result.inserted:
        S.recompute_daily(db, sid)
        db.commit()
    return result.as_dict()
