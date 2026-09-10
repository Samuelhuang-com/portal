"""
競品分析 — 配額服務（週期、預留、扣減、手動加發）

建立日期：2026-09-09
規格書：`docs/SPEC_compset_analysis.md` v1.1 §3.3～§3.5、D14、D15

═══════════════════════════════════════════════════════════════════════════
這支是整個模組唯一碰到錢的地方
═══════════════════════════════════════════════════════════════════════════
配額 ＝ SerpApi 的查詢次數 ＝ 直接的 API 成本，未來也直接對應對外收費。
所以本檔案的每個決定都往保守的方向做：

  · 扣減一律走**單一原子 UPDATE**，不做「先讀再寫」
  · 預留失敗就整組不跑，不做「跑到停為止」
  · 退還一律綁定期間，跨期不退
  · 加發一定留兩份紀錄（`compset_quota_grants` ＋ `audit_logs`）

⚠️ **全部是同步 `def`**。`async def` 內直接呼叫同步 `db.query()` 會凍結整站
   （見記憶 project_async_def_blocking_fix，Portal 曾因此整站無回應）。

═══════════════════════════════════════════════════════════════════════════
四個一定要照做的規則
═══════════════════════════════════════════════════════════════════════════
1. **⭐ 先預留、再送 API，而且預留要先 commit。**
   `reserve()` 只 flush，交易由呼叫端掌握。呼叫端必須在**送出任何 API 請求之前**
   把預留 commit 出去。
   理由：如果先送請求、後扣配額，中途崩潰就會「供應商那邊算了、我們這邊沒算」——
   **少算比多算危險**，因為少算會讓我們一路超額打到供應商停權。
   反過來多算（預留了但沒送出）可以用 `refund()` 補回來，是可修復的。

2. **⭐ 整組原子化（SPEC D15）。**
   A 級是 token 逐家查，一個入住日要 N 次（N ＝ 競爭組家數）。
   開跑前用 `reserve(db, sid, N)` 一次預留整組，回 False 就**整個入住日跳過**並記 warning。
   絕不可以「跑到配額用完為止」——那會產生「部分競品有價、部分沒有」的半套資料，
   `compset_rate_daily` 的中位數會被算歪，而且看起來完全正常。

3. **⭐ `quota_anchor_day` 只接受 1～28。**
   29～31 在 2 月會歸零失敗。這種「一年只有一兩個月會出錯」的 bug 最難被發現，
   所以在**寫入時**就擋掉，而不是在歸零時才處理。

4. **⭐ 加發不改 `monthly_quota`。**
   加發是「這一期多給你 N 次」，寫成一筆 `compset_quota_grants`；
   期間一滾動就自動失效。改 `monthly_quota` 會讓「臨時加一次」變成「永久漲價」。

═══════════════════════════════════════════════════════════════════════════
本期可用額度的定義
═══════════════════════════════════════════════════════════════════════════
    available = monthly_quota
              + SUM(compset_quota_grants.granted_qty WHERE period_start = 本期)
              - quota_used

`quota_used` 在期間滾動時歸零；加發額度綁在 `period_start`，**不結轉到下一期**。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.compset_analysis import (CompsetQuotaGrant, CompsetSubscriber,
                                         CompsetSubscriberUser)

MIN_ANCHOR_DAY = 1
MAX_ANCHOR_DAY = 28          # ⚠️ 29~31 會讓 2 月歸零失敗，見檔頭規則 3


# ══════════════════════════════════════════════════════════════════════════
# 例外
# ══════════════════════════════════════════════════════════════════════════
class QuotaError(RuntimeError):
    """配額相關錯誤的基底。router 層轉成 400/403。"""


class SubscriberNotFound(QuotaError):
    pass


class InvalidAnchorDay(QuotaError):
    pass


class SelfGrantForbidden(QuotaError):
    """防提權 P-1：不得對自己所屬的 subscriber 加發配額。"""


class InvalidGrant(QuotaError):
    pass


# ══════════════════════════════════════════════════════════════════════════
# 1. 計費週期
# ══════════════════════════════════════════════════════════════════════════
def validate_anchor_day(anchor_day: int) -> int:
    """`quota_anchor_day` 的唯一驗證入口。任何寫入路徑都要先過這裡。"""
    if not isinstance(anchor_day, int) or not (
        MIN_ANCHOR_DAY <= anchor_day <= MAX_ANCHOR_DAY
    ):
        raise InvalidAnchorDay(
            f"quota_anchor_day 必須是 {MIN_ANCHOR_DAY}~{MAX_ANCHOR_DAY} 的整數"
            f"（收到 {anchor_day!r}）。"
            "不接受 29~31 是因為 2 月沒有那幾天，歸零會失敗，"
            "而且一年只有一兩個月會出錯、極難發現。"
        )
    return anchor_day


def period_start_for(day: date, anchor_day: int) -> str:
    """
    回傳 `day` 所屬計費週期的起算日（ISO 字串 `YYYY-MM-DD`）。

    週期是 [本月 anchor, 下月 anchor)。
    例：anchor=15，2026-09-20 → "2026-09-15"；2026-09-03 → "2026-08-15"。

    因為 anchor 已限制 ≤ 28，不會有「該月沒有這一天」的問題。
    """
    validate_anchor_day(anchor_day)
    if day.day >= anchor_day:
        year, month = day.year, day.month
    elif day.month == 1:
        year, month = day.year - 1, 12
    else:
        year, month = day.year, day.month - 1
    return f"{year:04d}-{month:02d}-{anchor_day:02d}"


def ensure_period(db: Session, subscriber_id: int,
                  today: date | None = None) -> str:
    """
    把 subscriber 的計費週期滾到 `today` 所屬的那一期，回傳現行 `period_start`。

    ⚠️ 刻意寫成**條件式 UPDATE** 而不是「讀出來、比一比、寫回去」：
       排程與手動觸發可能同時進來，先讀再寫會讓兩個行程都以為自己該歸零，
       第二個把第一個已經扣掉的 `quota_used` 又清成 0。
       條件 `quota_period_start < want` 天生冪等，滾第二次不會有任何效果。

    ⚠️ ISO 日期字串的字典序 ＝ 時間序，所以 `<` 比得對；
       第一次啟用時 `quota_period_start` 是空字串，空字串小於任何日期，也會正確滾動。
    """
    sub = db.get(CompsetSubscriber, subscriber_id)
    if sub is None:
        raise SubscriberNotFound(f"compset_subscribers.id={subscriber_id} 不存在")

    want = period_start_for(today or date.today(), sub.quota_anchor_day)
    if sub.quota_period_start == want:
        return want

    db.execute(
        update(CompsetSubscriber)
        .where(
            CompsetSubscriber.id == subscriber_id,
            CompsetSubscriber.quota_period_start < want,
        )
        .values(quota_period_start=want, quota_used=0)
    )
    db.flush()
    db.refresh(sub)          # 上面走的是 Core UPDATE，ORM 物件會是舊的
    return sub.quota_period_start


# ══════════════════════════════════════════════════════════════════════════
# 2. 額度查詢
# ══════════════════════════════════════════════════════════════════════════
def _granted_total(db: Session, subscriber_id: int, period_start: str) -> int:
    """本期已加發的總額度。"""
    return int(
        db.execute(
            select(func.coalesce(func.sum(CompsetQuotaGrant.granted_qty), 0))
            .where(
                CompsetQuotaGrant.subscriber_id == subscriber_id,
                CompsetQuotaGrant.period_start == period_start,
            )
        ).scalar_one()
    )


def quota_status(db: Session, subscriber_id: int,
                 today: date | None = None) -> dict[str, Any]:
    """
    本期配額現況。Dashboard 的常駐配額條與 `/compset/subscribers` 都用這支。

    `usage_ratio` 是給畫面用的：>= 0.8 轉黃、>= 1.0 轉紅並顯示「已停止抓取」。
    """
    period_start = ensure_period(db, subscriber_id, today)
    sub = db.get(CompsetSubscriber, subscriber_id)
    granted = _granted_total(db, subscriber_id, period_start)
    limit = int(sub.monthly_quota) + granted
    used = int(sub.quota_used)
    return {
        "subscriber_id": subscriber_id,
        "period_start": period_start,
        "monthly_quota": int(sub.monthly_quota),
        "granted": granted,
        "limit": limit,
        "used": used,
        "available": max(limit - used, 0),
        "usage_ratio": (used / limit) if limit > 0 else 1.0,
        "is_exhausted": used >= limit,
        "is_active": bool(sub.is_active),
    }


def is_exhausted(db: Session, subscriber_id: int,
                 today: date | None = None) -> bool:
    return quota_status(db, subscriber_id, today)["is_exhausted"]


# ══════════════════════════════════════════════════════════════════════════
# 3. 預留與退還
# ══════════════════════════════════════════════════════════════════════════
def reserve(db: Session, subscriber_id: int, n: int,
            today: date | None = None) -> bool:
    """
    ⭐ 原子預留 `n` 次查詢額度。**全有全無**。

    回 True  ＝ 額度已扣，呼叫端可以送出最多 n 次請求
    回 False ＝ 額度不足（或訂閱已停用），呼叫端**整組跳過**並記 warning

    ⚠️ 這是**唯一**可以扣配額的入口。不要在別的地方寫
       `sub.quota_used += n` —— 那是先讀再寫，兩個行程同時跑會互相蓋掉。

    ⚠️ 上限是在 SQL 裡即時算的（`monthly_quota` ＋ 本期加發），
       所以不會有「讀出上限之後、扣款之前，別人剛好加發了」的時間差問題。

    ⚠️ 本函式只 `flush()`，**交易由呼叫端掌握**。
       呼叫端必須在送出任何 API 請求之前 `commit()`（見檔頭規則 1）。
    """
    if n <= 0:
        return True

    period_start = ensure_period(db, subscriber_id, today)

    granted_sq = (
        select(func.coalesce(func.sum(CompsetQuotaGrant.granted_qty), 0))
        .where(
            CompsetQuotaGrant.subscriber_id == subscriber_id,
            CompsetQuotaGrant.period_start == period_start,
        )
        .scalar_subquery()
    )

    result = db.execute(
        update(CompsetSubscriber)
        .where(
            CompsetSubscriber.id == subscriber_id,
            CompsetSubscriber.is_active.is_(True),
            # 期間必須還是同一期：若剛好跨期被別人滾動了，這次預留作廢重來
            CompsetSubscriber.quota_period_start == period_start,
            CompsetSubscriber.quota_used + n
            <= CompsetSubscriber.monthly_quota + granted_sq,
        )
        .values(quota_used=CompsetSubscriber.quota_used + n)
    )
    db.flush()

    sub = db.get(CompsetSubscriber, subscriber_id)
    if sub is not None:
        db.refresh(sub)
    return result.rowcount == 1


def refund(db: Session, subscriber_id: int, n: int, period_start: str) -> int:
    """
    把「預留了但實際沒送出」的額度還回去。回傳實際退還的數量（0 或 n）。

    典型情境：整組預留 6 次，跑到第 4 家時對方 API 連續失敗而放棄 → 退還 2 次。

    ⚠️ **必須帶 `period_start`**（呼叫端從 `reserve()` 當時的 `quota_status`
       或 `ensure_period()` 拿到）。如果期間在這中間滾動了，這筆退還就不屬於
       現行期間 —— 直接放棄（回 0），否則會把新期間的 `quota_used` 扣成負的，
       等於憑空多給一批額度。

    ⚠️ 只有在 `quota_used >= n` 時才退，避免任何情況下扣成負數。
    """
    if n <= 0:
        return 0

    result = db.execute(
        update(CompsetSubscriber)
        .where(
            CompsetSubscriber.id == subscriber_id,
            CompsetSubscriber.quota_period_start == period_start,
            CompsetSubscriber.quota_used >= n,
        )
        .values(quota_used=CompsetSubscriber.quota_used - n)
    )
    db.flush()

    sub = db.get(CompsetSubscriber, subscriber_id)
    if sub is not None:
        db.refresh(sub)
    return n if result.rowcount == 1 else 0


# ══════════════════════════════════════════════════════════════════════════
# 4. 使用者歸屬（防提權 P-1 的依據）
# ══════════════════════════════════════════════════════════════════════════
def user_subscriber_ids(db: Session, user_id: str) -> set[int]:
    """
    這個使用者屬於哪些訂閱客戶。

    ⚠️ 沒有任何關聯的使用者回空集合，代表**不屬於任何 subscriber**，P-1 不會擋他。
       這是刻意的（SPEC D14）：內部工程人員調整 INTERNAL 的配額是成本決策，
       不是提權。P-1 要防的是「客戶的管理員幫自己加額度」。
    """
    rows = db.execute(
        select(CompsetSubscriberUser.subscriber_id)
        .where(CompsetSubscriberUser.user_id == user_id)
    ).scalars().all()
    return {int(r) for r in rows}


# ══════════════════════════════════════════════════════════════════════════
# 5. 手動加發（唯一會提高額度的入口）
# ══════════════════════════════════════════════════════════════════════════
def grant_quota(
    db: Session,
    *,
    subscriber_id: int,
    granted_qty: int,
    reason: str,
    granted_by_user_id: str,
    ip_address: str | None = None,
    today: date | None = None,
) -> CompsetQuotaGrant:
    """
    對某訂閱客戶的**本期**加發一次性額度。

    防提權三條（SPEC §3.5）：
      P-1 不得對自己所屬的 subscriber 加發 —— **本函式強制**，不靠前端隱藏按鈕
      P-2 只有 `compset_subscriber_admin` 可呼叫 —— 由 router 的
          `require_permission("compset_subscriber_admin")` 把關（不在本層）
      P-3 每次加發同時寫 `compset_quota_grants` 與 `audit_logs` —— 本函式做

    ⚠️ **不修改 `monthly_quota`**（檔頭規則 4）。加發綁在 `period_start`，
       期間一滾動就自動失效。

    ⚠️ `reason` 必填。加發是花錢的動作，沒有理由的加發在事後無法稽核。
    """
    if granted_qty <= 0:
        raise InvalidGrant("加發數量必須大於 0")
    reason = (reason or "").strip()
    if not reason:
        raise InvalidGrant("加發必須填寫理由（事後稽核用）")

    sub = db.get(CompsetSubscriber, subscriber_id)
    if sub is None:
        raise SubscriberNotFound(f"compset_subscribers.id={subscriber_id} 不存在")

    # ── P-1 ──────────────────────────────────────────────────────────
    if subscriber_id in user_subscriber_ids(db, granted_by_user_id):
        raise SelfGrantForbidden(
            "不得對自己所屬的訂閱客戶加發配額。"
            "請由不屬於該訂閱的管理員操作。"
        )

    period_start = ensure_period(db, subscriber_id, today)

    row = CompsetQuotaGrant(
        subscriber_id=subscriber_id,
        granted_qty=int(granted_qty),
        reason=reason,
        granted_by_user_id=granted_by_user_id,
        period_start=period_start,
    )
    db.add(row)
    db.flush()

    # ── P-3：稽核軌跡（比照 opera_forecast.py 的寫法）────────────────
    db.add(AuditLog(
        user_id=granted_by_user_id,
        action="compset_quota_grant",
        resource_type="compset_subscriber",
        resource_id=str(subscriber_id),
        ip_address=ip_address,
        extra={
            "subscriber_code": sub.code,
            "granted_qty": int(granted_qty),
            "period_start": period_start,
            "reason": reason,
            "monthly_quota": int(sub.monthly_quota),
            "quota_used_at_grant": int(sub.quota_used),
        },
    ))
    db.flush()
    return row


def list_grants(db: Session, subscriber_id: int,
                period_start: str | None = None,
                limit: int = 200) -> list[CompsetQuotaGrant]:
    """加發紀錄。不帶 `period_start` 就列全部（最新在前）。"""
    stmt = select(CompsetQuotaGrant).where(
        CompsetQuotaGrant.subscriber_id == subscriber_id
    )
    if period_start:
        stmt = stmt.where(CompsetQuotaGrant.period_start == period_start)
    stmt = stmt.order_by(CompsetQuotaGrant.granted_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())
