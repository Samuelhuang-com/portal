"""
OTA 口碑分析 — 來源設定 service

規格書：`docs/SPEC_ota_reviews.md` §8.3
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ota_review import OtaReview, OtaSource
from app.schemas.ota_review import OtaSourceCreate, OtaSourceOut, OtaSourceUpdate
from app.services.ota_normalize import PLATFORM_LABEL, PLATFORM_SCALE


def _fmt_dt(value) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _to_out(source: OtaSource, stored_count: int = 0) -> OtaSourceOut:
    return OtaSourceOut(
        id=source.id,
        hotel_code=source.hotel_code,
        hotel_name=source.hotel_name,
        platform=source.platform,
        url=source.url,
        score_scale=source.score_scale,
        is_enabled=source.is_enabled,
        max_pages=source.max_pages,
        sort_order=source.sort_order,
        overall_score=float(source.overall_score) if source.overall_score is not None else None,
        overall_score_10=float(source.overall_score_10) if source.overall_score_10 is not None else None,
        review_count_site=source.review_count_site,
        last_sync_at=_fmt_dt(source.last_sync_at),
        last_status=source.last_status or "never",
        last_message=source.last_message or "",
        stored_count=stored_count,
    )


def list_sources(db: Session, enabled_only: bool = False) -> list[OtaSourceOut]:
    """
    來源清單，附上「實際落地筆數」。

    `stored_count` 不含跨站重複（`is_duplicate=0`），用來與站方公布的
    `review_count_site` 比對抓取完整度 —— 兩者差距過大就代表翻頁沒抓完。
    """
    stmt = select(OtaSource)
    if enabled_only:
        stmt = stmt.where(OtaSource.is_enabled.is_(True))
    stmt = stmt.order_by(OtaSource.sort_order, OtaSource.hotel_code, OtaSource.platform)
    sources = db.execute(stmt).scalars().all()

    counts = dict(
        db.execute(
            select(OtaReview.source_id, func.count(OtaReview.id))
            .where(OtaReview.is_duplicate.is_(False))
            .group_by(OtaReview.source_id)
        ).all()
    )
    return [_to_out(s, counts.get(s.id, 0)) for s in sources]


def get_source(db: Session, source_id: int) -> OtaSource | None:
    return db.get(OtaSource, source_id)


def _assert_hotel_code_consistent(db: Session, hotel_code: str, exclude_id: int | None = None) -> None:
    """
    擋住「只有大小寫不同」的 hotel_code。

    ⚠️ 2026-08-22 加這個是因為現場已經出現 `HANNS` 與 `HANNS_Summer` 並存。
       那兩個是不同飯店沒問題，但若日後有人把 Tripadvisor 來源打成
       `HANNS_SUMMER`（全大寫），就會變成第三間飯店：

         - 所有統計（月度趨勢、雙館比較、平台對照）都 group by hotel_code，
           大小寫不同就各自成一組，圖表上會多出一條線
         - 跨站去重的指紋含 hotel_code，大小寫不同就永遠比不中，
           Booking 與 Tripadvisor 的同一則評論會各算一次

       兩個症狀都不會報錯，只會讓數字悄悄變得不對。
       **這裡刻意不自動改寫使用者輸入的大小寫** —— 直接擋下並要求沿用既有寫法，
       比默默改掉他打的字更好（他可能真的想新增一間叫不同名字的飯店）。
    """
    normalized = hotel_code.strip().upper()
    stmt = select(OtaSource.hotel_code).distinct()
    if exclude_id is not None:
        stmt = stmt.where(OtaSource.id != exclude_id)
    for existing in db.execute(stmt).scalars().all():
        if existing and existing.upper() == normalized and existing != hotel_code.strip():
            raise ValueError(
                f"已經有飯店代碼「{existing}」，你輸入的「{hotel_code.strip()}」"
                f"只有大小寫不同。請直接沿用「{existing}」——"
                f"大小寫不一致會讓統計把它們當成兩間飯店，跨站去重也會失效。"
            )


def _assert_platform_exists(db: Session, platform: str) -> None:
    """
    平台代碼必須是平台表裡啟用中的一筆。

    ⚠️ 這個檢查從 Pydantic 的 `Literal` 搬下來（2026-08-23）——
       平台改成資料驅動之後，schema 層不可能知道現在有哪些平台。
       留在 schema 的話使用者剛建好的平台會被擋掉，
       而且錯誤訊息只會列出五個內建代碼，看不出問題在哪一層。
    """
    from app.services.ota_platform_service import list_platforms

    rows = list_platforms(db)
    enabled = {r.code for r in rows if r.is_enabled}
    if platform in enabled:
        return

    disabled = {r.code for r in rows} - enabled
    if platform in disabled:
        raise ValueError(
            f"平台「{platform}」目前是停用狀態，無法建立新來源。"
            f"請先到平台管理把它啟用。"
        )
    raise ValueError(
        f"沒有「{platform}」這個平台。現有的是："
        f"{'、'.join(sorted(enabled))}。"
        f"要新增其他 OTA 網站，請到「平台管理」建立後再回來設定來源。"
    )


def _assert_url_matches_platform(db: Session, url: str, platform: str) -> None:
    """
    擋住「網址與平台對不上」的來源。

    ⚠️ 2026-08-22 補上。`platform_from_url()` 先前只用在 `--diagnose`，
       **建檔這條路徑完全沒檢查** —— 在下拉選 Expedia 卻貼 Booking 的網址，
       系統照收，然後：

         Booking 的頁面 → 交給 ExpediaParser → 解析 0 筆 → 判 failed

       畫面上看到的是「擷取失敗」，實際上是設定錯了。
       而 selector 一組都不會命中，很容易被誤判成「爬蟲壞了」往錯的方向查。

    ⚠️ 認不出來的網域**放行**（只在 `--diagnose` 時警告）——
       網址千奇百怪（短網址、追蹤參數、地區站台），擋掉會誤傷。
       這裡只擋「明確認得出來、而且對不上」的那種。
    """
    from app.services.ota_normalize import PLATFORM_LABEL, platform_from_url
    from app.services.ota_platform_service import refresh_caches

    # ⭐ 先把 DB 的平台同步進 `DOMAIN_PLATFORM`（2026-08-23）。
    #    平台改成資料驅動之後，使用者自建的平台（例：Hotels.com）也要享有
    #    這套防呆 —— 不同步的話它的網域永遠認不出來，等於自建平台沒人守。
    refresh_caches(db)

    detected, note = platform_from_url(url)
    if note:
        raise ValueError(
            f"這個網址是 {note}。"
            f"你選的平台是「{PLATFORM_LABEL.get(platform, platform)}」，對不上。"
        )
    if detected and detected != platform:
        raise ValueError(
            f"網址看起來是 {PLATFORM_LABEL.get(detected, detected)}，"
            f"但平台選的是 {PLATFORM_LABEL.get(platform, platform)}。"
            f"請改選「{PLATFORM_LABEL.get(detected, detected)}」，"
            f"或確認網址是否貼錯 —— 用錯 parser 會解析出 0 筆並被判為失敗。"
        )


def create_source(db: Session, payload: OtaSourceCreate) -> OtaSourceOut:
    _assert_platform_exists(db, payload.platform)
    _assert_url_matches_platform(db, payload.url, payload.platform)
    _assert_hotel_code_consistent(db, payload.hotel_code)
    source = OtaSource(
        hotel_code=payload.hotel_code.strip(),
        hotel_name=payload.hotel_name.strip(),
        platform=payload.platform,
        url=payload.url.strip(),
        # 使用者沒特別指定就用平台預設分制
        score_scale=payload.score_scale or PLATFORM_SCALE.get(payload.platform, 10),
        is_enabled=payload.is_enabled,
        max_pages=payload.max_pages,
        sort_order=payload.sort_order,
    )
    db.add(source)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("這個網址已經在來源清單中") from exc
    db.refresh(source)
    return _to_out(source)


def update_source(db: Session, source_id: int, payload: OtaSourceUpdate) -> OtaSourceOut:
    source = db.get(OtaSource, source_id)
    if source is None:
        raise ValueError("找不到來源")

    _assert_platform_exists(db, payload.platform)
    _assert_url_matches_platform(db, payload.url, payload.platform)
    _assert_hotel_code_consistent(db, payload.hotel_code, exclude_id=source_id)
    source.hotel_code = payload.hotel_code.strip()
    source.hotel_name = payload.hotel_name.strip()
    source.platform = payload.platform
    source.url = payload.url.strip()
    source.score_scale = payload.score_scale
    source.is_enabled = payload.is_enabled
    source.max_pages = payload.max_pages
    source.sort_order = payload.sort_order

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("這個網址已經在來源清單中") from exc

    # 飯店代碼或平台改了，既有評論的反正規化欄位要跟著更新，否則統計會對不上
    db.execute(
        OtaReview.__table__.update()
        .where(OtaReview.source_id == source_id)
        .values(hotel_code=source.hotel_code, platform=source.platform)
    )
    db.commit()
    db.refresh(source)
    return _to_out(source)


def toggle_source(db: Session, source_id: int) -> OtaSourceOut:
    source = db.get(OtaSource, source_id)
    if source is None:
        raise ValueError("找不到來源")
    source.is_enabled = not source.is_enabled
    db.commit()
    db.refresh(source)
    return _to_out(source)


def delete_source(db: Session, source_id: int) -> None:
    """
    刪除來源。

    ⚠️ 底下還有評論時**拒絕刪除**（FK 是 RESTRICT）。
    比照 CLAUDE.md §9 規則 6：來源端消失不可連帶硬刪已落地的資料。
    要停用請用 toggle，不要刪。
    """
    source = db.get(OtaSource, source_id)
    if source is None:
        raise ValueError("找不到來源")

    count = db.execute(
        select(func.count(OtaReview.id)).where(OtaReview.source_id == source_id)
    ).scalar_one()
    if count:
        raise ValueError(
            f"此來源底下還有 {count} 則評論，無法刪除。"
            f"若不想再同步，請改用「停用」。"
        )

    db.delete(source)
    db.commit()


def platform_options(db: Session) -> list[dict]:
    """
    前端下拉選單用：平台代碼、顯示名稱、預設分制、**有沒有自動擷取器**。

    ⚠️ 2026-08-22 補上 `has_parser`：`PLATFORM_SCALE` 有 5 個平台，
       但 `PARSERS` 只有 3 個有擷取器。原本下拉選單五個都給選，
       使用者選了 Agoda 建完來源，同步時只會拿到一個紅色「失敗」，
       完全看不出來是「這個平台還沒做」而不是「壞掉了」。

       選單仍然讓選 —— 這些來源可以用 CSV／HTML 檔匯入，
       建檔本身是有意義的。但**必須標示清楚**。
    """
    from app.services.ota_parser import PARSERS
    from app.services.ota_platform_service import list_platforms

    return [
        {
            "value": row.code,
            "label": row.label,
            "score_scale": row.score_scale,
            # ⚠️ `has_parser` 現算不存 DB —— 程式碼才是唯一真相，
            #    存進 DB 會變成兩份會不同步的事實。
            "has_parser": row.code in PARSERS,
            "note": row.note,
        }
        for row in list_platforms(db, enabled_only=True)
    ]
