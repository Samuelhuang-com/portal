"""
OTA 口碑分析 — 落地與去重（爬蟲與 CSV 匯入的共同終點）

建立日期：2026-08-21
規格書：`docs/SPEC_ota_reviews.md` §5.3、§6.1、§6.6

═══════════════════════════════════════════════════════════════════════════
兩條資料進入路徑，一個落地出口
═══════════════════════════════════════════════════════════════════════════
    ota_scraper_service（P2）─┐
                              ├─▶ ota_normalize.normalize_review ─▶ 本模組 upsert
    ota_import_service（CSV）─┘

分歧只到「怎麼拿到原始資料」為止。正規化、指紋、去重、寫入一律共用，
否則兩條路會產出兩種資料品質，日後「為什麼匯入的評論算不進趨勢圖」會查很久。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.ota_review import OtaReview, OtaSource, OtaSyncLog
from app.services.ota_normalize import NormalizedReview


@dataclass
class UpsertResult:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    marked_duplicate: int = 0
    warnings: list[str] = field(default_factory=list)


def upsert_reviews(
    db: Session,
    source: OtaSource,
    reviews: list[NormalizedReview],
    *,
    sync_log_id: int | None = None,
) -> UpsertResult:
    """
    把正規化後的評論寫進 `ota_reviews`（存在則更新）。

    ⚠️ **人工營運欄位一律不碰**：`alert_status` / `alert_note` /
       `alert_handler_id` / `alert_handled_at`。
       這四欄是使用者在畫面上填的，重新同步或重跑匯入不可覆蓋
       （CLAUDE.md §9 規則 4 的精神）。

    ⚠️ **分析結果也不覆蓋**：`sentiment_*` / `topics_json` / `analyzed_at`
       只在評論**內容有變動**時才清空重新排隊分析，內容沒變就別浪費 API。
    """
    result = UpsertResult()
    if not reviews:
        return result

    now = twnow()

    for nr in reviews:
        result.warnings.extend(nr.warnings)

        existing = db.execute(
            select(OtaReview).where(
                OtaReview.source_id == source.id,
                OtaReview.fingerprint == nr.fingerprint,
            )
        ).scalar_one_or_none()

        if existing is None:
            db.add(OtaReview(
                source_id=source.id,
                hotel_code=source.hotel_code,
                platform=source.platform,
                external_id=nr.external_id,
                fingerprint=nr.fingerprint,
                cross_fingerprint=nr.cross_fingerprint,
                author=nr.author,
                nationality=nr.nationality,
                traveler_type=nr.traveler_type,
                room_type=nr.room_type,
                nights=nr.nights,
                score_raw=nr.score_raw,
                score_scale=nr.score_scale,
                score_10=nr.score_10,
                title=nr.title,
                positive_text=nr.positive_text,
                negative_text=nr.negative_text,
                comment=nr.comment,
                review_date=nr.review_date,
                review_month=nr.review_month,
                stay_month=nr.stay_month,
                review_url=nr.review_url or source.url,
                raw_json=json.dumps(nr.raw, ensure_ascii=False) if nr.raw else None,
                sync_log_id=sync_log_id,
                fetched_at=now,
                analyzed_at=None,          # 待分析
            ))
            result.inserted += 1
            continue

        # ── 既有筆：只更新來源端欄位 ────────────────────────────────────
        content_changed = (
            existing.positive_text != nr.positive_text
            or existing.negative_text != nr.negative_text
            or existing.comment != nr.comment
            or existing.title != nr.title
        )

        existing.hotel_code = source.hotel_code
        existing.platform = source.platform
        existing.external_id = nr.external_id or existing.external_id
        existing.cross_fingerprint = nr.cross_fingerprint
        existing.author = nr.author
        existing.nationality = nr.nationality or existing.nationality
        existing.traveler_type = nr.traveler_type or existing.traveler_type
        existing.room_type = nr.room_type or existing.room_type
        existing.nights = nr.nights if nr.nights is not None else existing.nights
        existing.score_raw = nr.score_raw
        existing.score_scale = nr.score_scale
        existing.score_10 = nr.score_10
        existing.title = nr.title
        existing.positive_text = nr.positive_text
        existing.negative_text = nr.negative_text
        existing.comment = nr.comment
        existing.review_date = nr.review_date
        existing.review_month = nr.review_month
        existing.stay_month = nr.stay_month or existing.stay_month
        existing.review_url = nr.review_url or existing.review_url
        if nr.raw:
            existing.raw_json = json.dumps(nr.raw, ensure_ascii=False)
        existing.sync_log_id = sync_log_id
        existing.fetched_at = now

        if content_changed:
            # 內容變了才重新排隊分析；沒變就保留既有結果，別浪費 API
            existing.analyzed_at = None

        # ⚠️ 這裡刻意不動：alert_status / alert_note / alert_handler_id /
        #    alert_handled_at / is_alert（is_alert 由分析階段重算）
        result.updated += 1

    db.flush()
    result.marked_duplicate = mark_cross_duplicates(db, source.hotel_code)
    return result


def mark_cross_duplicates(db: Session, hotel_code: str) -> int:
    """
    跨 OTA 去重（規格書 §5.3）。

    同一位客人可能在 Booking 與 Expedia 貼同一段話，不去重會被算兩次。

    ⚠️ **只標記 `is_duplicate`，絕不刪除**：
       - 判斷錯了刪掉就救不回來
       - 各站的原始筆數還要對得上站方公布的評論總數

    保留規則：同一個 `cross_fingerprint` 群組中，保留 `review_date` 最早者；
    日期相同則保留 `id` 較小者（先抓到的）。其餘標記為重複。

    回傳本次「狀態有變動」的筆數（新標記 + 取消標記），不是重複總數。
    """
    if not hotel_code:
        return 0

    rows = db.execute(
        select(OtaReview)
        .where(
            OtaReview.hotel_code == hotel_code,
            OtaReview.cross_fingerprint != "",
        )
        .order_by(OtaReview.cross_fingerprint, OtaReview.review_date, OtaReview.id)
    ).scalars().all()

    groups: dict[str, list[OtaReview]] = {}
    for row in rows:
        groups.setdefault(row.cross_fingerprint, []).append(row)

    changed = 0
    for members in groups.values():
        if len(members) == 1:
            # 單筆群組：若之前被誤標為重複（來源被刪等情況），還原
            if members[0].is_duplicate:
                members[0].is_duplicate = False
                changed += 1
            continue

        # 已依 review_date, id 排序；但空日期會排在最前面（"" < "2026-.."），
        # 而「沒有日期」不代表最早，所以把空日期的排到最後再挑保留者
        ordered = sorted(
            members,
            key=lambda r: (r.review_date == "", r.review_date, r.id),
        )
        keeper = ordered[0]
        for row in ordered:
            should_be_dup = row.id != keeper.id
            if row.is_duplicate != should_be_dup:
                row.is_duplicate = should_be_dup
                changed += 1

    if changed:
        db.flush()
    return changed


# ══════════════════════════════════════════════════════════════════════════
# 同步紀錄
# ══════════════════════════════════════════════════════════════════════════
def start_sync_log(
    db: Session,
    source_id: int,
    trigger_type: str,
    triggered_by: str | None = None,
) -> OtaSyncLog:
    # ⚠️ host+pid 一定要在這裡寫進去（2026-08-24）。
    #    status='running' 下一行就 commit 落地，而收尾只在 except Exception 裡 ——
    #    Ctrl-C／行程被砍／後端重啟都不會經過它，那一列就永遠停在 running，
    #    然後 run_sync() 的 409 會讓整個模組再也同步不了。
    #    留下身分，`ota_sync_recovery` 才能問「那個行程還活著嗎」而不是猜逾時。
    from app.services.ota_sync_recovery import worker_identity

    host, pid = worker_identity()
    log = OtaSyncLog(
        source_id=source_id,
        trigger_type=trigger_type,
        started_at=twnow(),
        status="running",
        triggered_by=triggered_by,
        worker_host=host,
        worker_pid=pid,
    )
    db.add(log)
    db.flush()
    return log


def finish_sync_log(
    db: Session,
    log: OtaSyncLog,
    *,
    status: str,
    pages_fetched: int = 0,
    found_count: int = 0,
    result: UpsertResult | None = None,
    warnings: list[str] | None = None,
    error_message: str = "",
) -> None:
    """
    收尾同步紀錄。

    ⚠️ `warnings` 與 `error_message` 的分工不可混用（CLAUDE.md §9 規則 8）：
       「某頁沒抓到／某筆日期解析不了／分制判不出來」歸 warnings；
       **只有整個來源失敗才寫 error_message**。
       把 warning 當 error 記，畫面上就會永遠黃燈，久了沒人看。
    """
    all_warnings = list(warnings or [])
    if result:
        all_warnings.extend(result.warnings)

    log.completed_at = twnow()
    log.status = status
    log.pages_fetched = pages_fetched
    log.found_count = found_count
    if result:
        log.inserted_count = result.inserted
        log.updated_count = result.updated
        log.skipped_count = result.skipped
    # warnings 可能重複很多次（同一種解析失敗），去重後保留順序，最多記 100 筆
    seen: set[str] = set()
    deduped: list[str] = []
    for w in all_warnings:
        if w and w not in seen:
            seen.add(w)
            deduped.append(w)
    log.warnings_json = json.dumps(deduped[:100], ensure_ascii=False) if deduped else None
    log.error_message = (error_message or "")[:1000]

    if log.started_at and log.completed_at:
        log.duration_ms = int((log.completed_at - log.started_at).total_seconds() * 1000)

    # 同步結果回寫來源
    source = db.get(OtaSource, log.source_id)
    if source:
        source.last_sync_at = log.completed_at
        source.last_status = status
        source.last_message = (error_message or (deduped[0] if deduped else ""))[:500]

    db.flush()
