"""
OHIP 非同步端點 — 落地快取與 30 分鐘冷卻

背景（2026-08-07 建立，起因見 docs/EVAL_ohip_strategic_data.md §3.1）
────────────────────────────────────────────────────────────────────────────
Oracle 官方對**所有** async 端點規定：

> Every identical request (employing the same query parameters) necessitates
> a mandatory 30-minute interval between submissions.
> **這個限制不管 POST／HEAD／GET 循環有沒有跑完都算。**

適用於 `revenueInventoryStatistics`、以及未來要接的
`getReservationsDailySummary`（RSVASYNC）、`getBlockAllocationSummary`（BLKASYNC）。

因此本模組刻意做成**通用**的，不綁定營收 —— 之後接新端點時直接沿用，
不要各自再寫一份（各寫一份必然會有一份忘記更新間隔）。

⚠️ 三件目前「不知道」的事，一律不猜（詳見 EVAL 文件 §3、§6）
────────────────────────────────────────────────────────────────────────────
① **OHIP 對違規重複請求實際回哪個 HTTP 狀態碼，官方文件沒有寫。**
   → 本模組因此採取「**寧可自己先擋住**」的策略：不去猜對方回什麼碼、
     也不依賴解析錯誤訊息，而是在本地記錄上次呼叫時間，時間沒到就不發。
     這樣不論對方回什麼碼都不會踩到。
② **「identical request」的判定範圍**（是否含 hotelId／extSystemCode）文件沒寫。
   → `cache_key` 一律**從寬**涵蓋所有會送出的參數。從寬的代價只是多快取幾筆，
     從嚴的代價是踩限制 —— 兩者不對稱，所以選從寬。
③ 冷卻時間是否會隨 OPERA Cloud 版本改變，未知。
   → 抽成 `MIN_INTERVAL_SECONDS` 常數，不要散落在各處。
"""
from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.realtime import OhipAsyncCache

# Oracle 規定的相同請求最小間隔（秒）。⚠️ 官方值是 30 分鐘，這裡不加保險係數 ——
# 加了會讓「為什麼還不能重查」變成無法對照文件解釋的黑箱。
MIN_INTERVAL_SECONDS = 1800


def build_key(*parts: Any) -> str:
    """組 cache key。⚠️ 從寬涵蓋所有送出的參數（見檔頭 ②）。

    用 `|` 分隔而不用 hash，是為了讓 DB 裡的紀錄**人眼可讀** ——
    出問題時要能直接看出是哪一組參數被擋住。
    """
    return "|".join("" if p is None else str(p) for p in parts)[:255]


def lookup(db: Session, cache_key: str) -> OhipAsyncCache | None:
    return (db.query(OhipAsyncCache)
              .filter(OhipAsyncCache.cache_key == cache_key)
              .one_or_none())


def age_seconds(row: OhipAsyncCache | None) -> float | None:
    """這份快取幾秒前抓的。沒有快取回 None。"""
    if row is None or not row.fetched_epoch:
        return None
    return max(time.time() - row.fetched_epoch, 0.0)


def cooldown_remaining(db: Session, cache_key: str) -> int:
    """距離「可以再打一次相同請求」還剩幾秒。0 表示現在就可以打。"""
    age = age_seconds(lookup(db, cache_key))
    if age is None:
        return 0
    return max(int(MIN_INTERVAL_SECONDS - age), 0)


def get(db: Session, cache_key: str, ttl_seconds: int = MIN_INTERVAL_SECONDS
        ) -> tuple[Any, dict, float] | None:
    """讀快取。回傳 (payload, meta, fetched_epoch)；未命中或已過期回 None。

    ⚠️ `ttl_seconds` 預設就等於冷卻時間 —— 兩者相同才不會出現
       「快取過期了但還不能重打」的空窗期。要縮短請先想清楚空窗期怎麼處理。
    """
    row = lookup(db, cache_key)
    if row is None:
        return None

    age = age_seconds(row)
    if age is None or age >= ttl_seconds:
        return None

    try:
        payload = json.loads(row.payload_json) if row.payload_json else None
        meta = json.loads(row.meta_json) if row.meta_json else {}
    except (ValueError, TypeError):
        # 快取內容壞掉不是致命錯誤 —— 當作沒有快取，重打一次即可
        return None

    try:
        row.hit_count = (row.hit_count or 0) + 1
        db.commit()
    except Exception:
        db.rollback()

    return payload, meta, row.fetched_epoch


def put(db: Session, cache_key: str, payload: Any, meta: dict | None = None, *,
        endpoint: str = "", hotel_id: str = "",
        date_start: str = "", date_end: str = "") -> float:
    """寫入／覆寫快取。回傳寫入當下的 epoch。

    ⚠️ 寫入失敗**不能**讓主流程失敗 —— 使用者已經拿到資料了，
       快取寫不進去頂多是下次多打一次 API。
    """
    now = time.time()
    try:
        row = lookup(db, cache_key)
        if row is None:
            row = OhipAsyncCache(cache_key=cache_key)
            db.add(row)
        row.endpoint = endpoint[:200]
        row.hotel_id = hotel_id[:40]
        row.date_start = date_start[:10]
        row.date_end = date_end[:10]
        row.payload_json = json.dumps(payload, ensure_ascii=False, default=str)
        row.meta_json = json.dumps(meta or {}, ensure_ascii=False, default=str)
        row.fetched_at = twnow()
        row.fetched_epoch = now
        row.hit_count = 0
        db.commit()
    except Exception:
        db.rollback()
    return now


def purge(db: Session, cache_key: str | None = None) -> int:
    """清除快取。不給 key 就全清。回傳刪掉幾筆。

    ⚠️ 清快取**不會**解除 OHIP 那邊的 30 分鐘限制 —— 對方是依自己的紀錄判定。
       清完馬上重打仍可能被拒。這個函式只適合用在「快取內容格式改版」的場合。
    """
    try:
        q = db.query(OhipAsyncCache)
        if cache_key:
            q = q.filter(OhipAsyncCache.cache_key == cache_key)
        n = q.delete(synchronize_session=False)
        db.commit()
        return n
    except Exception:
        db.rollback()
        return 0


class CooldownActive(RuntimeError):
    """相同請求尚在 30 分鐘冷卻內，本地主動擋下（沒有真的發出請求）。"""

    def __init__(self, remaining_seconds: int, cache_key: str = ""):
        self.remaining_seconds = remaining_seconds
        self.cache_key = cache_key
        mins = remaining_seconds // 60
        secs = remaining_seconds % 60
        super().__init__(
            f"這組查詢條件距離上次取數還不到 30 分鐘，還需等待 {mins} 分 {secs} 秒。"
            "OPERA Cloud 對相同條件的非同步查詢規定最短間隔 30 分鐘，"
            "為避免被對方拒絕，Portal 在本地先擋下。"
            "期間請改看已顯示的快取資料，或調整查詢區間（條件不同就不受此限）。"
        )
