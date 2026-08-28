"""
即時營運 — 每日快照（房況 + 營收）

建立日期：2026-08-07
決策依據：`docs/EVAL_ohip_strategic_data.md` §4.4（順位 1）
資料表：`app/models/realtime.py` 的 `OhipSnapshotRun` / `OhipInventorySnapshot`
        / `OhipRevenueSnapshot`

═══════════════════════════════════════════════════════════════════════════
為什麼要有這個服務
═══════════════════════════════════════════════════════════════════════════
OHIP 給的是「**現在看到的那一天**」，不是「那一天當時的樣子」。
今天查 8/20 拿到此刻的 8/20；明天再查，數字變了，而**昨天的版本永遠拿不回來**。

所以「距離入住還有 30 天時，這一天已經賣了幾間」（pickup／booking pace）
**只能靠每天自己存一份快照累積**。這件事有時效性 ——
今天沒開始存，昨天的就永遠補不回來。

═══════════════════════════════════════════════════════════════════════════
設定（2026-08-07 與使用者確認）
═══════════════════════════════════════════════════════════════════════════
| 項目 | 值 | 備註 |
|------|-----|------|
| 視野 | 今日 + 未來 180 天 | 涵蓋團體與長假期的長前置期訂房 |
| **回看** | **往前 7 天** | 見下方「為什麼需要回看」 |
| 房況粒度 | 全館層 + 房型層 | 同一次 API 回應就含兩種粒度，不多花呼叫 |
| 營收粒度 | 全館 + 房型別 + 市場區隔 | `groupBy=[MarketCode, RoomType]`，全館由加總得出 |
| 執行時間 | 每日 06:00 | 重點不是幾點，而是**每天固定同一時間** |
| 保留期限 | **永久，不清理** | 刪了補不回來，這正是本模組存在的理由 |

═══════════════════════════════════════════════════════════════════════════
為什麼需要「回看」（2026-08-07 追加，`LOOKBACK_DAYS`）
═══════════════════════════════════════════════════════════════════════════
最初的實作是 `start = 今天`，只抓未來。上線後檢查才發現一個缺口：

**這樣永遠拿不到任何一天的「最終實績」。**

快照每天 06:00 跑，所以每個 business_date 最早在 `lead_days=179` 被捕捉，
**最晚在 `lead_days=0`，也就是當天早上** —— 那天的營業都還沒發生。

pickup 分析要看的是「**最終**賣到幾間 vs 各前置天數的進度」。
沒有終點就沒有基準線，曲線畫得出來，卻無法判讀「這個進度算好還是壞」。

> 終點能不能改從 TXT（`opera_revenue_daily`）拿？全館層可以，
> 但 **TXT 沒有 market code 與房型**，所以房型別／市場區隔的 pickup 依然沒有終點。
> 而房型別與市場區隔正是 API 相對於 TXT 的核心價值。

因此把起點往前推 `LOOKBACK_DAYS` 天。過去日期兩支 API 都吃得到
（`/realtime/compare` 已在用同步版查過去 30 天；非同步版 2026-08-06 實測過整月）。

**為什麼是 7 天而不是 1 天**：1 天只夠拿終點，但排程掉一次就永遠缺那天的終點，
連帶讓那天整條 pickup 曲線失去基準線。7 天給一週的補救空間，
順便看得到 EOD 完成後的帳務修正（`lead_days` 為 -1 ～ -7 的那幾筆）。

⚠️ **回看的日期 `lead_days` 是負數**，這是刻意的：
   `lead_days = 0` 代表「入住當天早上」，`-1` 代表「隔天回頭看」（＝最終實績）。
   查詢 pickup 曲線的終點時要取 **`lead_days` 最小的那一筆**，不是 0。

⚠️ 每天固定同一時間為什麼重要
   pickup 曲線的 X 軸是「提前幾天」。若今天 06:00 抓、明天 15:00 抓，
   兩點之間實際隔了 33 小時而不是 24 小時，曲線就失真了。
   排程 misfire 時寧可**跳過**也不要延後補跑（見 main.py 的 misfire_grace_time）。

═══════════════════════════════════════════════════════════════════════════
三個實作上的取捨（都有可能被誤解，所以寫清楚）
═══════════════════════════════════════════════════════════════════════════
① **房況與營收分開切段，段長不同。**
   房況走同步版，硬上限 62 天 → 180 天切 3 段。
   營收走非同步版，日期上限寬（400/94 天），但**回應超過 2 MB 會被靜默截斷**，
   而三維度交叉（日期 × 房型 × 市場區隔）很容易踩到。
   所以營收刻意切成 45 天一段（4 段），**限制因素是回應大小不是日期上限**。

② **截斷只能「示警」不能「偵測」。**
   直覺的做法是比對「回傳的日期數 vs 預期天數」，少了就是被截斷。
   **這個檢查對未來日期不成立** —— 一個完全沒有訂房的未來日期本來就可能
   整列不回傳（OHIP 省略 0 值）。日期少不代表被截斷。
   因此這裡只用 `ohip_client` 量到的回應大小示警，
   並如實記成 `partial`，**不宣稱「已偵測到截斷」**。

③ **營收不走 `ohip_async_cache` 快取。**
   排程一天一次、且每天的日期區間都不同，本來就不會命中快取；
   走快取只會在快取表塞進大量再也用不到的列。
   直接用 `RS._fetch`。30 分鐘限流也不受影響（參數天天不同 = 不是 identical request）。
"""
from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import twnow
from app.models.realtime import (OhipInventorySnapshot, OhipRevenueSnapshot,
                                 OhipSnapshotRun)
from app.services import ohip_client
from app.services import realtime_revenue_service as RS
from app.services import realtime_status_service as LS
from app.services.ohip_client import OhipError

logger = logging.getLogger(__name__)

# ── 設定 ─────────────────────────────────────────────────────────────────────
HORIZON_DAYS = 180              # 今日 + 未來 179 天，共 180 天
LOOKBACK_DAYS = 7               # 往前 7 天 —— 為了拿到 pickup 曲線的終點（見檔頭）
INVENTORY_CHUNK_DAYS = 62       # 同步版 API 的硬上限
REVENUE_CHUNK_DAYS = 45         # ⚠️ 限制因素是 2 MB 回應大小，不是日期上限
REVENUE_GROUP_BY = [RS.GROUP_BY_MARKET, RS.GROUP_BY_ROOM_TYPE]

STATUS_OK = "ok"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"


def _chunks(start: date, end: date, size: int) -> list[tuple[date, date]]:
    out: list[tuple[date, date]] = []
    cur = start
    while cur <= end:
        seg_end = min(cur + timedelta(days=size - 1), end)
        out.append((cur, seg_end))
        cur = seg_end + timedelta(days=1)
    return out


def _as_int(v: Any) -> int | None:
    """OHIP 的數值可能是字串。⚠️ 缺值回 None，**不補 0**。"""
    if v is None or v == "":
        return None
    try:
        return int(Decimal(str(v)))
    except Exception:
        return None


def _lead(snapshot: date, business: str) -> int:
    try:
        return (date.fromisoformat(business) - snapshot).days
    except (ValueError, TypeError):
        return 0


# ── 房況 ─────────────────────────────────────────────────────────────────────

def _collect_inventory(db: Session, snap: date, start: date, end: date,
                       triggered_by: str) -> tuple[list[OhipInventorySnapshot], dict]:
    """同步版 inventoryStatistics，逐段取數並攤平成 ORM 物件。"""
    hotel_id = settings.OHIP_HOTEL_ID
    endpoint = f"/inv/v1/hotels/{hotel_id}/inventoryStatistics"
    rows: list[OhipInventorySnapshot] = []
    stat = {"api_calls": 0, "bytes": 0, "warnings": []}

    for seg_start, seg_end in _chunks(start, end, INVENTORY_CHUNK_DAYS):
        params: list[tuple[str, str]] = [
            ("dateRangeStart", seg_start.isoformat()),
            ("dateRangeEnd", seg_end.isoformat()),
            ("reportCode", LS.REPORT_CODE),
        ]
        for p in LS._PARAMETERS:
            params.append(("parameterName", p))
            params.append(("parameterValue", "Y"))    # ⚠️ 必須成對

        try:
            payload, meta = ohip_client.get(endpoint, params=params, hotel_id=hotel_id)
        except OhipError as e:
            LS._log_call(db, endpoint=endpoint, hotel_id=hotel_id,
                         date_start=seg_start.isoformat(), date_end=seg_end.isoformat(),
                         meta={"status_code": e.status_code or 0,
                               "request_id": e.request_id or ""},
                         success=False, error=str(e), triggered_by=triggered_by)
            raise

        stat["api_calls"] += 1
        LS._log_call(db, endpoint=endpoint, hotel_id=hotel_id,
                     date_start=seg_start.isoformat(), date_end=seg_end.isoformat(),
                     meta=meta, success=True, triggered_by=triggered_by)

        parsed = LS._parse(payload)

        for d in parsed.get("house") or []:
            rows.append(_inv_row(snap, hotel_id, d, scope="house"))
        for rt in parsed.get("room_types") or []:
            for d in rt.get("days") or []:
                rows.append(_inv_row(
                    snap, hotel_id, d, scope="roomtype",
                    room_type=rt.get("room_type") or "",
                    desc=rt.get("description") or "",
                ))

    return rows, stat


def _inv_row(snap: date, hotel_id: str, d: dict, *, scope: str,
             room_type: str = "", desc: str = "") -> OhipInventorySnapshot:
    bd = d.get("business_date") or ""
    return OhipInventorySnapshot(
        snapshot_date=snap.isoformat(),
        business_date=bd,
        lead_days=_lead(snap, bd),
        hotel_id=hotel_id,
        scope=scope,
        room_type=room_type[:40],
        room_type_desc=desc[:120],
        inventory_rooms=_as_int(d.get("inventory_rooms")),
        rooms_sold=_as_int(d.get("rooms_sold")),
        available_rooms=_as_int(d.get("available_rooms")),
        ooo_rooms=_as_int(d.get("ooo_rooms")),
        arrival_rooms=_as_int(d.get("arrival_rooms")),
        departure_rooms=_as_int(d.get("departure_rooms")),
        people_in_house=_as_int(d.get("people_in_house")),
        comp_rooms=_as_int(d.get("comp_rooms")),
        house_use_rooms=_as_int(d.get("house_use_rooms")),
        day_use_rooms=_as_int(d.get("day_use_rooms")),
        overbooking_rooms=_as_int(d.get("overbooking_rooms")),
        sell_limit_rooms=_as_int(d.get("sell_limit_rooms")),
        occupancy=d.get("occupancy"),
        is_weekend=bool(d.get("is_weekend")),
    )


# ── 營收 ─────────────────────────────────────────────────────────────────────

def _collect_revenue(db: Session, snap: date, start: date, end: date,
                     triggered_by: str) -> tuple[list[OhipRevenueSnapshot], dict]:
    """非同步版 revenueInventoryStatistics，三維度交叉。

    ⚠️ 刻意**不走** `RS.fetch_rows`（落地快取）—— 見檔頭取捨 ③。
    """
    hotel_id = settings.OHIP_HOTEL_ID
    rows: list[OhipRevenueSnapshot] = []
    stat: dict[str, Any] = {"api_calls": 0, "bytes": 0, "warnings": []}
    seen: set[tuple[str, str, str]] = set()

    for seg_start, seg_end in _chunks(start, end, REVENUE_CHUNK_DAYS):
        raw, meta = RS._fetch(db, seg_start, seg_end, REVENUE_GROUP_BY, triggered_by)
        stat["api_calls"] += 1
        stat["bytes"] += int(meta.get("response_bytes") or 0)

        if meta.get("truncation_risk"):
            # ⚠️ 措辭是「可能」不是「已」—— 我們無法確認（見檔頭取捨 ②）
            stat["warnings"].append(
                f"營收 {seg_start}～{seg_end}：回應 {meta.get('response_bytes'):,} bytes，"
                f"已逼近 2 MB 上限，資料**可能**被靜默截斷。"
                f"建議調小 REVENUE_CHUNK_DAYS（目前 {REVENUE_CHUNK_DAYS}）。"
            )

        for r in raw:
            n = RS._normalize(r)
            bd = n.get("business_date") or ""
            mc = (n.get("market_code") or "")[:40]
            rt = (n.get("room_type") or "")[:40]

            # ⚠️ 唯一鍵去重：同一段內理論上不會重複，但切段邊界若 OPERA 端
            #    有重疊回傳，直接 insert 會炸 UNIQUE constraint 而讓整批失敗。
            key = (bd, mc, rt)
            if key in seen:
                continue
            seen.add(key)

            rows.append(OhipRevenueSnapshot(
                snapshot_date=snap.isoformat(),
                business_date=bd,
                lead_days=_lead(snap, bd),
                hotel_id=hotel_id,
                market_code=mc,
                room_type=rt,
                res_type=(n.get("res_type") or "")[:40],
                physical_rooms=_as_int(n.get("physical_rooms")),
                ooo_rooms=_as_int(n.get("ooo_rooms")),
                oos_rooms=_as_int(n.get("oos_rooms")),
                rooms_sold=_as_int(n.get("rooms_sold")),
                arrival_rooms=_as_int(n.get("arrival_rooms")),
                departure_rooms=_as_int(n.get("departure_rooms")),
                cancelled_rooms=_as_int(n.get("cancelled_rooms")),
                no_show_rooms=_as_int(n.get("no_show_rooms")),
                room_revenue=n.get("room_revenue"),
                total_revenue=n.get("total_revenue"),
                food_revenue=n.get("food_revenue"),
            ))

    return rows, stat


# ── 主流程 ───────────────────────────────────────────────────────────────────

def run_snapshot(db: Session, *, horizon_days: int = HORIZON_DAYS,
                 lookback_days: int = LOOKBACK_DAYS,
                 include_revenue: bool = True,
                 triggered_by: str = "scheduler") -> dict[str, Any]:
    """執行一次快照。**同一天重跑會覆蓋當天的快照**（冪等）。

    Returns:
        執行摘要 dict（同時已寫入 `ohip_snapshot_run`）

    ⚠️ 房況失敗 → 整批 `failed`（沒有房況就沒有 pickup，這批沒有價值）。
       營收失敗 → `partial`，**房況照樣保留**（房況本身就能做 rooms pickup）。
       這個不對稱是刻意的。
    """
    started = time.perf_counter()
    snap = date.today()
    # ⚠️ 起點往前推 LOOKBACK_DAYS —— 沒有回看就拿不到任何一天的最終實績，
    #    pickup 曲線會沒有基準線（見檔頭「為什麼需要回看」）
    start = snap - timedelta(days=max(lookback_days, 0))
    end = snap + timedelta(days=max(horizon_days, 1) - 1)
    hotel_id = settings.OHIP_HOTEL_ID

    run = OhipSnapshotRun(
        snapshot_date=snap.isoformat(), hotel_id=hotel_id,
        started_at=twnow(), status="", horizon_days=horizon_days,
        lookback_days=lookback_days,
        triggered_by=triggered_by[:120],
    )

    if not ohip_client.is_configured():
        run.status = STATUS_FAILED
        run.error = "OHIP 尚未設定完成，缺少：" + "、".join(ohip_client.missing_settings())
        run.finished_at = twnow()
        _save_run(db, run)
        return _summary(run)

    warnings: list[str] = []
    api_calls = 0
    total_bytes = 0

    # ── 房況（必要）──────────────────────────────────────────────────────────
    try:
        inv_rows, inv_stat = _collect_inventory(db, snap, start, end, triggered_by)
    except Exception as e:
        # ⚠️ 抓 `Exception` 而不是只抓 `OhipError`（2026-08-07 測試發現的漏洞）：
        #    連線中斷、解析錯誤、DB 問題都不是 OhipError。原本會直接往外拋，
        #    結果**連一筆執行紀錄都不會寫** —— 而這張表存在的唯一理由，
        #    就是要能事後回答「那天為什麼沒有資料」。往外拋等於自廢武功。
        run.status = STATUS_FAILED
        run.error = f"房況取數失敗：{type(e).__name__}: {e}"
        run.finished_at = twnow()
        run.elapsed_ms = int((time.perf_counter() - started) * 1000)
        _save_run(db, run)
        return _summary(run)

    api_calls += inv_stat["api_calls"]
    warnings.extend(inv_stat["warnings"])

    # ── 營收（可選，失敗不致命）──────────────────────────────────────────────
    rev_rows: list[OhipRevenueSnapshot] = []
    if include_revenue:
        try:
            rev_rows, rev_stat = _collect_revenue(db, snap, start, end, triggered_by)
            api_calls += rev_stat["api_calls"]
            total_bytes += rev_stat["bytes"]
            warnings.extend(rev_stat["warnings"])
        except Exception as e:
            # ⚠️ 這裡故意抓 Exception 而不只是 OhipError：
            #    營收那條路徑會經過 CooldownActive 等非 OhipError 的例外，
            #    而**任何**營收問題都不該讓已經拿到的房況白費。
            warnings.append(f"營收取數失敗（房況已保留）：{type(e).__name__}: {e}")

    # ── 寫入（先刪同日舊資料，達成冪等）──────────────────────────────────────
    #
    # ⚠️ **只有拿到新資料時才刪舊的**（2026-08-07 測試發現的資料遺失風險）。
    #    情境：06:00 排程完整成功 → 10:00 有人手動重跑，但這次營收失敗。
    #    原本的寫法會無條件刪掉當天的營收快照，於是**早上抓到的好資料就沒了**，
    #    而快照是刪掉就補不回來的東西（API 沒有「回到過去」的參數）。
    #    所以：拿到新的才覆蓋，沒拿到就原封不動。
    try:
        if inv_rows:
            db.query(OhipInventorySnapshot).filter(
                OhipInventorySnapshot.snapshot_date == snap.isoformat(),
                OhipInventorySnapshot.hotel_id == hotel_id,
            ).delete(synchronize_session=False)
            db.bulk_save_objects(inv_rows)
        else:
            warnings.append("房況這次沒有回傳任何資料，當天既有的房況快照保持不變。")

        if rev_rows:
            db.query(OhipRevenueSnapshot).filter(
                OhipRevenueSnapshot.snapshot_date == snap.isoformat(),
                OhipRevenueSnapshot.hotel_id == hotel_id,
            ).delete(synchronize_session=False)
            db.bulk_save_objects(rev_rows)
        elif include_revenue:
            kept = (db.query(OhipRevenueSnapshot)
                      .filter(OhipRevenueSnapshot.snapshot_date == snap.isoformat(),
                              OhipRevenueSnapshot.hotel_id == hotel_id)
                      .count())
            if kept:
                warnings.append(
                    f"這次沒有取得營收，當天既有的 {kept} 列營收快照**保留未動** —— "
                    "快照刪掉就補不回來，不會因為重跑失敗而清空。"
                )

        db.commit()
    except Exception as e:
        db.rollback()
        run.status = STATUS_FAILED
        run.error = f"寫入快照失敗：{type(e).__name__}: {e}"
        run.finished_at = twnow()
        run.elapsed_ms = int((time.perf_counter() - started) * 1000)
        _save_run(db, run)
        return _summary(run)

    run.house_rows = sum(1 for r in inv_rows if r.scope == "house")
    run.room_type_rows = sum(1 for r in inv_rows if r.scope == "roomtype")
    run.revenue_rows = len(rev_rows)
    run.api_calls = api_calls
    run.response_bytes = total_bytes
    run.warnings = "\n".join(warnings)
    run.status = STATUS_PARTIAL if warnings else STATUS_OK
    run.finished_at = twnow()
    run.elapsed_ms = int((time.perf_counter() - started) * 1000)
    _save_run(db, run)
    return _summary(run)


def _save_run(db: Session, run: OhipSnapshotRun) -> None:
    """⚠️ 執行紀錄寫入失敗不能讓主流程失敗 —— 快照資料本身已經存好了。

    ⚠️⚠️ **但失敗必須留下痕跡**（2026-08-28 修正）。
       原本這裡是 `except Exception: db.rollback()`，完全靜默。
       實際發生過的後果：`lookback_days` 欄位加進 model 卻沒進 DB，
       於是從 2026-08-07 起**每天的執行紀錄都寫入失敗而沒有任何人知道**，
       `ohip_snapshot_run` 一直是 0 筆。連帶讓 `sync_snapshot()` 的
       「今天已完成就跳過」判斷永遠不成立，每次觸發都重打一次會計費的 OHIP API。

       這張表存在的唯一理由就是「事後回答那天為什麼沒有資料」，
       它自己寫不進去卻不出聲，等於自廢武功。例外照樣不外拋，但要留紀錄。
    """
    try:
        db.add(run)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(
            "[OhipSnapshot] 執行紀錄寫入失敗（快照資料本身不受影響）："
            "%s: %s ｜ snapshot_date=%s status=%s",
            type(exc).__name__, exc, run.snapshot_date, run.status,
        )
        # 排程在背景跑、logger 可能沒接 handler，主控台再印一次確保看得到
        print(f"[OhipSnapshot] ⚠️ 執行紀錄寫入失敗：{type(exc).__name__}: {exc}")


def _summary(run: OhipSnapshotRun) -> dict[str, Any]:
    return {
        "snapshot_date": run.snapshot_date,
        "hotel_id": run.hotel_id,
        "status": run.status,
        "horizon_days": run.horizon_days,
        "lookback_days": run.lookback_days,
        "house_rows": run.house_rows,
        "room_type_rows": run.room_type_rows,
        "revenue_rows": run.revenue_rows,
        "api_calls": run.api_calls,
        "response_bytes": run.response_bytes,
        "elapsed_ms": run.elapsed_ms,
        "warnings": [w for w in (run.warnings or "").split("\n") if w],
        "error": run.error or "",
        "started_at": run.started_at.isoformat(timespec="seconds") if run.started_at else None,
        "finished_at": run.finished_at.isoformat(timespec="seconds") if run.finished_at else None,
    }


# ── sync_tool.py 專用的零參數包裝（2026-08-13 新增）──────────────────────────

def run_snapshot_job(*, triggered_by: str = "sync_tool") -> dict[str, Any]:
    """每日快照，給 `sync_tool.py` 用（零參數、自己開 session）。

    ⚠️ 背景：DEV 機器 `SCHEDULER_ENABLED=false`（改用 sync_tool.py），
       但本模組先前沒登錄進 `sync_tool.py MODULES`，所以 main.py 每日 06:00 的
       `ohip_daily_snapshot` **從未執行** —— 2026-08-13 實測
       `ohip_inventory_snapshot` 是 0 筆，「快照精確版」永遠不會開始累積。

    ⚠️ **一天只跑一次。** sync_tool 最短 15 分一輪，每輪都抓
       (7 + 180) 天 × 兩條資料流會把 OHIP 配額燒光。今天已成功跑過就
       只做一次 DB 查詢後 skip，不打 OHIP。

    ⚠️ **錯過的日子補不回來** —— OPERA 不提供歷史查詢，快照只能存「當下」。
       所以這一支寧可每天多跑一次無效檢查，也不要漏跑。

    回傳格式對齊 sync_tool 的期待：`fetched` / `upserted` / `errors`。
    """
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        if not ohip_client.is_configured():
            # 「沒設定」不是「失敗」，不能讓 sync_tool 每輪紅燈
            return {
                "fetched": 0, "upserted": 0, "errors": 0, "skipped": True,
                "message": ("OHIP 尚未設定完成，缺少："
                            + "、".join(ohip_client.missing_settings())),
            }

        today_s = date.today().isoformat()
        done = (db.query(OhipSnapshotRun.id)
                  .filter(OhipSnapshotRun.snapshot_date == today_s,
                          OhipSnapshotRun.hotel_id == settings.OHIP_HOTEL_ID,
                          OhipSnapshotRun.status != "failed")
                  .first())
        if done:
            return {"fetched": 0, "upserted": 0, "errors": 0, "skipped": True,
                    "message": f"{today_s} 的快照今天已完成。"}

        out = run_snapshot(db, triggered_by=triggered_by)
        rows = (int(out.get("house_rows") or 0)
                + int(out.get("room_type_rows") or 0)
                + int(out.get("revenue_rows") or 0))
        return {
            "fetched": rows, "upserted": rows,
            "errors": 1 if out.get("status") == "failed" else 0,
            "skipped": False, "detail": out,
        }
    finally:
        db.close()


# ── 查詢（給狀態頁用）────────────────────────────────────────────────────────

def list_runs(db: Session, *, limit: int = 60) -> dict[str, Any]:
    """最近幾次的執行紀錄 + 累積覆蓋情形。

    `distinct_snapshot_days` 是最重要的一個數字：
    **它就是「我們已經累積了幾天的歷史」** —— pickup 分析要有意義，
    至少需要數十天。這個數字直接回答「現在能不能做訂房進度分析」。
    """
    q = (db.query(OhipSnapshotRun)
           .order_by(OhipSnapshotRun.started_at.desc())
           .limit(max(min(limit, 365), 1)))
    runs = [_summary(r) for r in q.all()]

    distinct_days = (db.query(OhipInventorySnapshot.snapshot_date)
                       .distinct().count())
    first = (db.query(OhipInventorySnapshot.snapshot_date)
               .order_by(OhipInventorySnapshot.snapshot_date.asc()).first())
    last = (db.query(OhipInventorySnapshot.snapshot_date)
              .order_by(OhipInventorySnapshot.snapshot_date.desc()).first())

    return {
        "runs": runs,
        "coverage": {
            "distinct_snapshot_days": distinct_days,
            # 有幾個 business_date 已經取得「入住日之後回頭看」的紀錄
            # —— 這才是 pickup 曲線**有基準線**的天數，通常比上面那個數字少
            "business_days_with_final": (
                db.query(OhipInventorySnapshot.business_date)
                  .filter(OhipInventorySnapshot.lead_days < 0,
                          OhipInventorySnapshot.scope == "house")
                  .distinct().count()
            ),
            "first_snapshot_date": first[0] if first else None,
            "last_snapshot_date": last[0] if last else None,
            "inventory_rows": db.query(OhipInventorySnapshot).count(),
            "revenue_rows": db.query(OhipRevenueSnapshot).count(),
        },
        "config": {
            "horizon_days": HORIZON_DAYS,
            "lookback_days": LOOKBACK_DAYS,
            "inventory_chunk_days": INVENTORY_CHUNK_DAYS,
            "revenue_chunk_days": REVENUE_CHUNK_DAYS,
            "revenue_group_by": REVENUE_GROUP_BY,
            "retention": "永久保留，不自動清理",
        },
    }
