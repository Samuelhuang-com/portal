"""
競品分析 — 抓取服務（排程入口）

建立日期：2026-09-09
規格書：`docs/SPEC_compset_analysis.md` v1.3 §3、§6
相依：`compset_quota_service`（配額）、`compset_serpapi_client`（連線與解析）

═══════════════════════════════════════════════════════════════════════════
這支把前面三塊接起來
═══════════════════════════════════════════════════════════════════════════
    排程 04:10 / sync_tool.py / 手動觸發
        └─ fetch_all_due(db)
             └─ 逐一 subscriber
                  ├─ ensure_period()                 配額週期
                  ├─ 判定 A/B/C 哪幾級「今天該跑」    ← 錨定日，不是「距上次成功」
                  ├─ A 級：token 逐家查（整組原子預留）
                  └─ B/C 級：地點查詢（每個入住日 1 次）

═══════════════════════════════════════════════════════════════════════════
五條不可以改的規則
═══════════════════════════════════════════════════════════════════════════
1. **⭐ 用錨定日判定該不該跑，不用「距上次成功幾天」**（SPEC §6.2）
   失敗一次，「距上次成功」的節奏就永久往後漂移，
   一個月後沒有人說得出「這筆資料是哪一天的第幾次抓取」。

2. **⭐ 整組原子預留（SPEC D15）**
   A 級一個入住日要 N 次（N ＝ 有 token 的競爭組家數）。
   `reserve(N)` 失敗就**整個入住日跳過**，絕不「跑到配額用完為止」——
   那會產生「部分競品有價、部分沒有」的半套資料，
   `compset_rate_daily` 的中位數會被算歪，而且看起來完全正常。

3. **⭐ 先預留 → commit → 再送 API**（`compset_quota_service` 檔頭規則 1）
   少算比多算危險：少算會讓我們一路超額打到供應商停權；
   多算可以用 `refund()` 補回來。

4. **抓到 0 筆視為錯誤不是成功**（SPEC §6.3）
   `SPEC_ota_reviews.md` R3 的教訓：原型會靜默寫入「成功，新增 0 則」。

5. **`warnings` 與 `error_message` 分工不可混用**
   跳過／某家沒抓到／部分失敗 → warnings；**只有真正的失敗才寫 error_message**。
   把 warning 當 error 記，來源端只要有一點小狀況就永遠黃燈，久了沒人看。

⚠️ **全部同步 `def`**（見記憶 project_async_def_blocking_fix）。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.compset_analysis import (CompsetFetchLog, CompsetHotel,
                                         CompsetRateSnapshot,
                                         CompsetSubscriber)
from app.services import compset_quota_service as QS
from app.services import compset_serpapi_client as SC

logger = logging.getLogger(__name__)

TIER_ORDER = ("A", "B", "C")
TIER_A, TIER_B, TIER_C = TIER_ORDER

STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"
STATUS_QUOTA = "quota_exceeded"
STATUS_SKIPPED = "skipped"

SOURCE_SERPAPI = "serpapi"

# 名稱比對時要拿掉的字元。Google 的飯店名常帶不同的分隔符
# （「承攜行旅 - 台北台大館」vs 我們建檔的「承攜行旅-台北台大館」）。
_STRIP_CHARS = " \t　-－—–·・()（）"


# ══════════════════════════════════════════════════════════════════════════
# 純函式：級別、窗口、節奏
# ══════════════════════════════════════════════════════════════════════════
def tiers_open(plan_level: str) -> tuple[str, ...]:
    """
    ⭐ 級別是**累進**的（SPEC D2）：`plan_level` 是「開放到哪一級」。

    A → ("A",)　B → ("A","B")　C → ("A","B","C")
    只買 B 不買 A（看得到 D+15 之後、看不到下週）沒有營運意義。
    """
    level = (plan_level or "A").upper()
    if level not in TIER_ORDER:
        level = "A"
    return TIER_ORDER[: TIER_ORDER.index(level) + 1]


def tier_window(sub: CompsetSubscriber, tier: str) -> tuple[int, int]:
    """回傳該級別的（起始天數, 結束天數），都是「距今天幾天」且含端點。"""
    a, b, c = int(sub.window_a_days), int(sub.window_b_days), int(sub.window_c_days)
    if tier == TIER_A:
        return 1, a
    if tier == TIER_B:
        return a + 1, b
    return b + 1, c


def tier_freq(sub: CompsetSubscriber, tier: str) -> int:
    freq = {TIER_A: sub.freq_a_days, TIER_B: sub.freq_b_days,
            TIER_C: sub.freq_c_days}[tier]
    return max(int(freq), 1)


def tier_path(tier: str) -> str:
    """
    ⭐ 混合路徑（SPEC D10）：A 級 token 逐家查、B／C 級地點查詢。

    A 級要精準而且**需要滿房訊號**（只有 token 路徑拿得到）；
    B／C 級只是看趨勢，地點查詢一次涵蓋多家，成本差 6 倍。
    """
    return SC.PATH_TOKEN if tier == TIER_A else SC.PATH_LOCATION


def is_tier_due(period_start: str, today: date, freq_days: int) -> bool:
    """
    ⭐ **錨定日**判定：以計費週期起算日為基準取餘數。

    刻意**不用**「距離上次成功抓取幾天」——失敗一次，節奏就永久往後漂移。
    錨定法的好處是：任何一天回頭算，都算得出「今天該不該跑」，
    補跑、重跑、換機器都不會影響節奏。

    ⚠️ 已知性質（可接受）：跨計費週期時相位會重置，
       所以週期交界處可能連續兩天都跑、或間隔拉長到 `freq_days + 1`。
       對價格趨勢的影響可以忽略，但**對帳時要記得**。
    """
    if not period_start:
        return True
    delta = (today - date.fromisoformat(period_start)).days
    return delta >= 0 and delta % max(freq_days, 1) == 0


DAYS_PER_MONTH = 30.4          # 平均月長，用來把「每 N 天一次」換算成月次數


def estimate_monthly_requests(sub: CompsetSubscriber, *,
                              token_hotel_count: int) -> dict[str, Any]:
    """
    以目前設定試算「每月大約要送出幾次查詢」。

    給「抓取節奏設定」頁即時顯示用（SPEC §9.3）——
    **讓人在按下儲存之前就看到成本**，而不是月底看帳單才發現。

    ⚠️ A 級是 token 逐家查，所以要乘上**有 token 的家數**；
       B／C 級是地點查詢，一個入住日一次，與家數無關（D10）。

    ⚠️ 這是估算不是保證：實際次數會因為 API 失敗退還、配額用盡提早停止而變少。
    """
    per_tier: dict[str, int] = {}
    for tier in tiers_open(sub.plan_level):
        start, end = tier_window(sub, tier)
        days = max(end - start + 1, 0)
        times_per_month = DAYS_PER_MONTH / tier_freq(sub, tier)
        multiplier = token_hotel_count if tier == TIER_A else 1
        per_tier[tier] = int(round(days * times_per_month * multiplier))

    total = sum(per_tier.values())
    quota = int(sub.monthly_quota or 0)
    return {
        "per_tier": per_tier,
        "total": total,
        "monthly_quota": quota,
        "usage_ratio": (total / quota) if quota else None,
        "over_quota": bool(quota and total > quota),
    }


def stay_dates_for(today: date, start_offset: int, end_offset: int) -> list[str]:
    if end_offset < start_offset:
        return []
    return [(today + timedelta(days=n)).isoformat()
            for n in range(start_offset, end_offset + 1)]


def _norm(name: str) -> str:
    """名稱比對用的正規化：去分隔符與空白、轉小寫。"""
    s = (name or "").strip().lower()
    for ch in _STRIP_CHARS:
        s = s.replace(ch, "")
    return s


# ══════════════════════════════════════════════════════════════════════════
# 執行結果
# ══════════════════════════════════════════════════════════════════════════
@dataclass
class TierResult:
    subscriber_id: int = 0
    tier: str = ""
    status: str = STATUS_SKIPPED
    request_count: int = 0
    row_count: int = 0
    stay_date_from: str = ""
    stay_date_to: str = ""
    warnings: list[str] = field(default_factory=list)
    error_message: str = ""


# ══════════════════════════════════════════════════════════════════════════
# 寫入
# ══════════════════════════════════════════════════════════════════════════
def upsert_snapshot(db: Session, *, sub_id: int, hotel_id: int,
                    snapshot_date: str, stay_date: str, tier: str,
                    fetch_path: str, parsed: SC.ParsedRate,
                    source: str = SOURCE_SERPAPI) -> None:
    """
    寫入一筆快照。唯一鍵重複時**更新**而不是報錯 ——
    同一天重跑（手動觸發、補跑）是正常操作。

    ⚠️ 但唯一鍵含 `snapshot_date`，所以「更新」只會蓋掉**當天**那一筆，
       歷史快照不受影響（SPEC §5.5）。

    ⚠️ 唯一鍵也含 `source`，所以 CSV 匯入（`source='csv'`）**不會覆蓋**
       同一格的 SerpApi 資料，兩列並存。統計時採哪一筆由
       `compset_analysis.SOURCE_PRIORITY` 決定（D16：SerpApi 優先）。

    ⚠️ **這是本模組唯一的落地入口**，抓取層與 CSV 匯入都走這裡。
       不要為了方便再寫第二份寫入邏輯 —— 兩份遲早會長歪。
    """
    row = db.execute(
        select(CompsetRateSnapshot).where(
            CompsetRateSnapshot.subscriber_id == sub_id,
            CompsetRateSnapshot.snapshot_date == snapshot_date,
            CompsetRateSnapshot.stay_date == stay_date,
            CompsetRateSnapshot.compset_hotel_id == hotel_id,
            CompsetRateSnapshot.source == source,
        )
    ).scalar_one_or_none()

    if row is None:
        row = CompsetRateSnapshot(
            subscriber_id=sub_id, compset_hotel_id=hotel_id,
            snapshot_date=snapshot_date, stay_date=stay_date,
            source=source,
        )
        db.add(row)

    row.tier = tier
    row.fetch_path = fetch_path
    row.price_gross = parsed.price_gross
    row.price_pretax = parsed.price_pretax
    row.currency = parsed.currency or "TWD"
    row.tax_included = parsed.tax_included
    row.ota_name = parsed.ota_name or ""
    row.is_official = bool(parsed.is_official)
    row.num_guests = parsed.num_guests
    row.free_cancellation = bool(parsed.free_cancellation)
    row.room_type_raw = parsed.room_type_raw or ""
    row.is_sold_out = parsed.is_sold_out
    row.typical_low = parsed.typical_low
    row.typical_high = parsed.typical_high
    row.raw_json = parsed.offers_json()


def _write_log(db: Session, res: TierResult, *, quota_before: int | None,
               quota_after: int | None, params: dict[str, Any],
               started_at: Any) -> None:
    db.add(CompsetFetchLog(
        subscriber_id=res.subscriber_id,
        tier=res.tier,
        fetch_path=tier_path(res.tier),
        started_at=started_at,
        finished_at=twnow(),
        stay_date_from=res.stay_date_from,
        stay_date_to=res.stay_date_to,
        request_count=res.request_count,
        row_count=res.row_count,
        quota_before=quota_before,
        quota_after=quota_after,
        status=res.status,
        params_json=json.dumps(params, ensure_ascii=False),
        warnings_json=(json.dumps(res.warnings, ensure_ascii=False)
                       if res.warnings else None),
        error_message=res.error_message[:500],
    ))
    db.flush()


# ══════════════════════════════════════════════════════════════════════════
# A 級：token 逐家查
# ══════════════════════════════════════════════════════════════════════════
def _run_tier_a(db: Session, sub: CompsetSubscriber, hotels: list[CompsetHotel],
                stay_dates: list[str], snapshot_date: str,
                period_start: str, res: TierResult) -> None:
    """
    每個入住日一組，**整組原子預留**（規則 2）。

    沒有 `google_property_token` 的競爭組成員無法用這條路徑抓 ——
    記 warning 並排除在預留數之外（不要為抓不到的家預留額度）。
    """
    usable = [h for h in hotels if (h.google_property_token or "").strip()]
    for h in hotels:
        if h not in usable:
            res.warnings.append(f"{h.display_name}：缺 google_property_token，A 級跳過")
    if not usable:
        res.status = STATUS_SKIPPED
        res.error_message = ""
        return

    group_size = len(usable)
    any_success = False

    for stay_date in stay_dates:
        # ⭐ 規則 2 ＋ 3：整組預留，先 commit 再送 API
        if not QS.reserve(db, sub.id, group_size):
            res.status = STATUS_QUOTA
            res.warnings.append(
                f"{stay_date}：配額不足（需 {group_size} 次），整個入住日跳過"
            )
            break
        db.commit()

        consumed = 0
        for h in usable:
            try:
                payload = SC.fetch_property(
                    property_token=h.google_property_token,
                    q=h.google_query_name or h.display_name,
                    check_in_date=stay_date,
                    adults=sub.param_adults, nights=sub.param_nights,
                    gl=sub.param_gl, hl=sub.param_hl, currency=sub.param_currency,
                )
                consumed += 1
                parsed = SC.parse_property_response(payload)
                upsert_snapshot(db, sub_id=sub.id, hotel_id=h.id,
                                 snapshot_date=snapshot_date, stay_date=stay_date,
                                 tier=TIER_A, fetch_path=SC.PATH_TOKEN,
                                 parsed=parsed)
                res.row_count += 1
                any_success = True
            except SC.SerpApiError as exc:
                res.warnings.append(f"{stay_date} / {h.display_name}：{exc}")

        res.request_count += consumed
        # 預留了但沒送出的（連線失敗）退還；跨期一律不退（見 quota service）
        QS.refund(db, sub.id, group_size - consumed, period_start)
        db.commit()

    if res.status != STATUS_QUOTA:
        res.status = _final_status(any_success, res)


# ══════════════════════════════════════════════════════════════════════════
# B／C 級：地點查詢
# ══════════════════════════════════════════════════════════════════════════
def _run_tier_bc(db: Session, sub: CompsetSubscriber, hotels: list[CompsetHotel],
                 stay_dates: list[str], snapshot_date: str, tier: str,
                 period_start: str, res: TierResult) -> None:
    """
    一次查詢涵蓋多家。**抓不到的家不寫列**（不是寫一筆空的 unknown）——
    「沒查到」與「沒有價」是兩件事，寫空列會讓 `sample_count` 看起來很健康，
    實際上分母是假的。

    ⚠️ 這條路徑拿不到滿房訊號，`is_sold_out` 一律 `unknown`（SPEC D13）。
    """
    if not (sub.location_query or "").strip():
        res.status = STATUS_SKIPPED
        res.warnings.append("未設定 location_query，B／C 級無法執行")
        return

    by_token = {(h.google_property_token or "").strip(): h
                for h in hotels if (h.google_property_token or "").strip()}
    by_name: dict[str, CompsetHotel] = {}
    for h in hotels:
        for candidate in (h.google_query_name, h.display_name):
            if candidate:
                by_name.setdefault(_norm(candidate), h)

    any_success = False

    for stay_date in stay_dates:
        if not QS.reserve(db, sub.id, 1):
            res.status = STATUS_QUOTA
            res.warnings.append(f"{stay_date}：配額不足，跳過")
            break
        db.commit()

        try:
            payload = SC.fetch_location(
                q=sub.location_query, check_in_date=stay_date,
                adults=sub.param_adults, nights=sub.param_nights,
                gl=sub.param_gl, hl=sub.param_hl, currency=sub.param_currency,
            )
            res.request_count += 1
        except SC.SerpApiError as exc:
            QS.refund(db, sub.id, 1, period_start)
            db.commit()
            res.warnings.append(f"{stay_date}：{exc}")
            continue

        rows = SC.parse_location_response(payload)
        matched: set[int] = set()
        for parsed in rows:
            hotel = by_token.get(parsed.property_token) or by_name.get(_norm(parsed.name))
            if hotel is None:
                continue                       # 不在競爭組裡，忽略
            upsert_snapshot(db, sub_id=sub.id, hotel_id=hotel.id,
                             snapshot_date=snapshot_date, stay_date=stay_date,
                             tier=tier, fetch_path=SC.PATH_LOCATION, parsed=parsed)
            matched.add(hotel.id)
            res.row_count += 1
            any_success = True

        missing = [h.display_name for h in hotels if h.id not in matched]
        if missing:
            res.warnings.append(
                f"{stay_date}：地點查詢未涵蓋 {len(missing)} 家（{'、'.join(missing[:5])}）"
            )
        db.commit()

    if res.status != STATUS_QUOTA:
        res.status = _final_status(any_success, res)


def _final_status(any_success: bool, res: TierResult) -> str:
    """⭐ 規則 4：抓到 0 筆視為錯誤，不是成功。"""
    if not any_success:
        if not res.error_message:
            res.error_message = "本次沒有寫入任何一筆快照"
        return STATUS_FAILED
    return STATUS_PARTIAL if res.warnings else STATUS_SUCCESS


# ══════════════════════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════════════════════
def fetch_subscriber(db: Session, sub: CompsetSubscriber,
                     today: date | None = None,
                     only_tiers: tuple[str, ...] | None = None) -> list[TierResult]:
    """單一訂閱客戶的抓取。手動觸發端點也走這支。"""
    today = today or date.today()
    snapshot_date = today.isoformat()
    results: list[TierResult] = []

    period_start = QS.ensure_period(db, sub.id, today)
    db.commit()

    hotels = list(db.execute(
        select(CompsetHotel)
        .where(CompsetHotel.subscriber_id == sub.id,
               CompsetHotel.is_enabled.is_(True))
        .order_by(CompsetHotel.sort_order, CompsetHotel.id)
    ).scalars().all())

    if not hotels:
        logger.warning("compset: subscriber %s 沒有啟用中的競爭組成員", sub.code)
        return results

    # ⚠️ 缺 is_self 不會擋下抓取（資料照收），但指數算不出來，必須醒目提示
    if sum(1 for h in hotels if h.is_self) != 1:
        logger.warning("compset: subscriber %s 的 is_self 不是恰一筆，"
                       "價位指數將無法計算", sub.code)

    for tier in tiers_open(sub.plan_level):
        if only_tiers and tier not in only_tiers:
            continue

        res = TierResult(subscriber_id=sub.id, tier=tier)
        if not is_tier_due(period_start, today, tier_freq(sub, tier)):
            continue

        start_off, end_off = tier_window(sub, tier)
        stay_dates = stay_dates_for(today, start_off, end_off)
        if not stay_dates:
            continue
        res.stay_date_from, res.stay_date_to = stay_dates[0], stay_dates[-1]

        started_at = twnow()
        quota_before = QS.quota_status(db, sub.id, today)["used"]
        params = {
            "gl": sub.param_gl, "hl": sub.param_hl,
            "currency": sub.param_currency, "adults": sub.param_adults,
            "nights": sub.param_nights, "tier": tier,
            "window_days": [start_off, end_off],
            "freq_days": tier_freq(sub, tier),
            "location_query": sub.location_query if tier != TIER_A else None,
        }

        try:
            if tier == TIER_A:
                _run_tier_a(db, sub, hotels, stay_dates, snapshot_date,
                            period_start, res)
            else:
                _run_tier_bc(db, sub, hotels, stay_dates, snapshot_date, tier,
                             period_start, res)
        except Exception as exc:                       # noqa: BLE001
            db.rollback()
            res.status = STATUS_FAILED
            res.error_message = f"{type(exc).__name__}: {exc}"
            logger.exception("compset: subscriber %s tier %s 失敗", sub.code, tier)

        quota_after = QS.quota_status(db, sub.id, today)["used"]
        _write_log(db, res, quota_before=quota_before, quota_after=quota_after,
                   params=params, started_at=started_at)
        db.commit()
        results.append(res)

    return results


def fetch_all_due(db: Session, today: date | None = None) -> dict[str, Any]:
    """
    排程與 `sync_tool.py` 的入口（登錄名「競品價格抓取」）。

    ⚠️ 任一 subscriber 失敗不影響其他人 —— 一家客戶的 token 失效
       不可以讓其他客戶當天完全沒有資料。

    ⚠️ 未設定 `SERPAPI_API_KEY` 時**不拋例外**，只回 skipped ＋ warning。
       整個排程不該因為一個沒設定好的模組而中斷。
    """
    today = today or date.today()
    out: dict[str, Any] = {"total": 0, "success": 0, "fetched": 0,
                           "upserted": 0, "warnings": [], "errors": []}

    if not SC.is_configured():
        out["warnings"].append("SERPAPI_API_KEY 未設定，競品抓取全部跳過")
        logger.warning("compset: SERPAPI_API_KEY 未設定，跳過")
        return out

    subs = list(db.execute(
        select(CompsetSubscriber)
        .where(CompsetSubscriber.is_active.is_(True))
        .order_by(CompsetSubscriber.id)
    ).scalars().all())
    out["total"] = len(subs)

    for sub in subs:
        try:
            results = fetch_subscriber(db, sub, today)
        except Exception as exc:                       # noqa: BLE001
            db.rollback()
            out["warnings"].append(f"{sub.code}：{type(exc).__name__}: {exc}")
            logger.exception("compset: subscriber %s 整體失敗", sub.code)
            continue

        if results and all(r.status in (STATUS_SUCCESS, STATUS_PARTIAL)
                           for r in results):
            out["success"] += 1
        for r in results:
            out["fetched"] += r.request_count
            out["upserted"] += r.row_count
            for w in r.warnings:
                out["warnings"].append(f"{sub.code}/{r.tier}：{w}")
            # ⚠️ warnings 與 errors 分開：只有真正的失敗進 errors。
            #    把 warning 當 error 記，sync_tool 的狀態燈就永遠是黃的。
            if r.error_message:
                out["errors"].append(f"{sub.code}/{r.tier}：{r.error_message}")

    return out


# ══════════════════════════════════════════════════════════════════════════
# 排程與 sync_tool 的無參數入口
# ══════════════════════════════════════════════════════════════════════════
def sync_all_enabled() -> dict[str, Any]:
    """
    **給 `sync_tool.py` 用**（登錄名「競品價格抓取」）。

    ⚠️ 刻意**不加 `sync_lock`** —— `sync_tool.py` 外層已經加了，
       兩邊都加會自我死鎖（比照 `ota_scraper_service.sync_all_enabled`）。

    ⚠️ `sync_tool.py` 用 `func()` 無參數呼叫，所以這支自己開 session。
    """
    from app.core.database import SessionLocal          # ⚠️ 就地 import，避免循環

    db = SessionLocal()
    try:
        return fetch_all_due(db)
    finally:
        db.close()


def run_scheduled_fetch() -> dict[str, Any]:
    """
    **給 `main.py` 的 APScheduler 用**。

    ⚠️ 這條路徑**沒有外層鎖**，所以自己包 `sync_lock`
       （比照 `ota_scraper_service.run_scheduled_sync`）。
    """
    from app.core.sync_lock import sync_lock

    with sync_lock("競品價格抓取"):
        return sync_all_enabled()
