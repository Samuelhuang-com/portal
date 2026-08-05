"""
OPERA 營運分析 — 住客與通路分析 API Router
Prefix: /api/v1/opera/guest

規格書：docs/SPEC_opera_analytics.md §10.3

資料來源一律為 Departure All（決策 D7）。
維度統計支援雙口徑 basis=room / reservation（決策 D5，規格書 §11.10）。

⚠️ 本 Router 回傳的住客姓名一律是遮罩後版本；原始姓名與會員卡號不曾寫入資料庫。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.services import opera_analysis_service as AS
from app.services import opera_period_service as PS

router = APIRouter(dependencies=[Depends(get_current_user)])

_VALID_BASIS = (AS.BASIS_ROOM, AS.BASIS_RESERVATION)


def _resolve_range(db: Session, start: str | None, end: str | None,
                   property_code: str) -> tuple[str, str]:
    if start and end:
        return start, end
    default_start, default_end = PS.default_range(db, property_code)
    return start or default_start, end or default_end


def _check_basis(basis: str) -> str:
    if basis not in _VALID_BASIS:
        raise HTTPException(
            status_code=400,
            detail=f"basis 只能是 {AS.BASIS_ROOM}（以房數計）或 {AS.BASIS_RESERVATION}（以訂單計）",
        )
    return basis


# ── 住宿明細 ─────────────────────────────────────────────────────────────────

@router.get("/stays", summary="住宿明細清單（分頁）")
def list_stays(
    start: str | None = Query(None),
    end: str | None = Query(None),
    property_code: str = Query(""),
    basis: str = Query(AS.BASIS_RESERVATION),
    channel: str = Query(""),
    room_category: str = Query(""),
    rate_code: str = Query(""),
    search: str = Query(""),
    sort_field: str = Query("departure_date"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_stays(
        db, s, e, property_code, basis, page, page_size,
        channel=channel, room_category=room_category, rate_code=rate_code,
        search=search, sort_field=sort_field, sort_order=sort_order,
    )


@router.get("/stays/{stay_id}", summary="單筆住宿明細（Drawer 用）")
def get_stay(
    stay_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    row = AS.get_stay_detail(db, stay_id)
    if not row:
        raise HTTPException(status_code=404, detail="找不到此住宿紀錄")
    return row


# ── 維度統計（雙口徑）─────────────────────────────────────────────────────────

@router.get("/dimension/{dimension}",
            summary="維度統計（channel/room_category/rate_code/company/payment/group）")
def dimension_stats(
    dimension: str,
    start: str | None = Query(None),
    end: str | None = Query(None),
    property_code: str = Query(""),
    basis: str = Query(AS.BASIS_ROOM),
    limit: int = Query(0, ge=0, le=200, description="0 = 不限制"),
    min_nights: int = Query(0, ge=0, le=365, description="只計住宿晚數 ≥ 此值（長住拆解用）"),
    exclude_person: bool = Query(True, description="僅 dimension=group 有效：排除疑似個人訂房"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    if dimension not in AS.DIMENSION_COLUMNS:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的維度：{dimension}（可用：{'、'.join(AS.DIMENSION_COLUMNS)}）",
        )
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_dimension_stats(
        db, dimension, s, e, property_code, basis, limit,
        min_nights=min_nights, exclude_person=exclude_person,
    )


@router.get("/payment", summary="付款方式統計")
def payment_stats(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""), basis: str = Query(AS.BASIS_ROOM),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_dimension_stats(db, "payment", s, e, property_code, basis)


@router.get("/group", summary="團體統計（自動剝除 OTA 訂房參考號並排除個人訂房）")
def group_stats(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""), basis: str = Query(AS.BASIS_ROOM),
    limit: int = Query(0, ge=0, le=200),
    exclude_person: bool = Query(True),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_dimension_stats(
        db, "group", s, e, property_code, basis, limit, exclude_person=exclude_person,
    )


@router.get("/room-usage", summary="房號使用分析（含疑似停用推論）")
def room_usage(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""), basis: str = Query(AS.BASIS_ROOM),
    inactive_months: int = Query(3, ge=1, le=24, description="連續幾個月零銷售視為疑似停用"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_room_usage(db, s, e, property_code, basis, inactive_months)


@router.get("/guest-mix", summary="客群結構：每房人數分布與家庭客分析")
def guest_mix(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""), basis: str = Query(AS.BASIS_ROOM),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_guest_mix(db, s, e, property_code, basis)


@router.get("/checkout-time", summary="退房時間分布（櫃台／房務人力安排用）")
def checkout_time(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""), basis: str = Query(AS.BASIS_ROOM),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_checkout_time_distribution(db, s, e, property_code, basis)


@router.get("/weekday", summary="入退房星期分布（到店／離店事件，非在住房晚）")
def stay_weekday(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""), basis: str = Query(AS.BASIS_ROOM),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_stay_weekday(db, s, e, property_code, basis)


@router.get("/los-buckets", summary="住宿天數（LOS）分桶")
def los_buckets(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""), basis: str = Query(AS.BASIS_ROOM),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_los_buckets(db, s, e, property_code, basis)


# 為了前端可讀性另外提供具名捷徑（行為等同 /dimension/{name}）
@router.get("/channel", summary="通路統計")
def channel_stats(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""), basis: str = Query(AS.BASIS_ROOM),
    limit: int = Query(0, ge=0, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_dimension_stats(db, "channel", s, e, property_code, basis, limit)


@router.get("/room-category", summary="房型統計")
def room_category_stats(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""), basis: str = Query(AS.BASIS_ROOM),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_dimension_stats(db, "room_category", s, e, property_code, basis)


@router.get("/rate-code", summary="Rate Code 統計")
def rate_code_stats(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""), basis: str = Query(AS.BASIS_ROOM),
    limit: int = Query(15, ge=0, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_dimension_stats(db, "rate_code", s, e, property_code, basis, limit)


@router.get("/company", summary="公司統計")
def company_stats(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""), basis: str = Query(AS.BASIS_ROOM),
    limit: int = Query(20, ge=0, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_dimension_stats(db, "company", s, e, property_code, basis, limit)


# ── 回訪 / 長住 ──────────────────────────────────────────────────────────────

@router.get("/repeat", summary="回訪住客統計（附分析母體涵蓋率）")
def repeat_guests(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""), basis: str = Query(AS.BASIS_RESERVATION),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_repeat_guests(db, s, e, property_code, basis, limit)


@router.get("/long-stay", summary="住宿晚數分布與長住客統計")
def long_stay(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""), basis: str = Query(AS.BASIS_ROOM),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    _check_basis(basis)
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_long_stay(db, s, e, property_code, basis)


# ── 期間總覽 / 篩選選項 ──────────────────────────────────────────────────────

@router.get("/summary", summary="Departure 期間總覽（兩種口徑並列）")
def stay_summary(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_view")),
):
    s, e = _resolve_range(db, start, end, property_code)
    return AS.get_stay_summary(db, s, e, property_code)


@router.get("/filter-options", summary="篩選下拉選項（通路／房型／Rate Code）")
def filter_options(
    start: str | None = Query(None), end: str | None = Query(None),
    property_code: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_guest_view")),
):
    s, e = _resolve_range(db, start, end, property_code)
    out = {}
    for dim, limit in (("channel", 0), ("room_category", 0), ("rate_code", 0)):
        stats = AS.get_dimension_stats(db, dim, s, e, property_code, AS.BASIS_RESERVATION, limit)
        out[dim] = [i["key"] for i in stats["items"]]
    out["start"] = s
    out["end"] = e
    return out
