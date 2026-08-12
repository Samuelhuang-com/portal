"""
營運分析 — 市場區隔／房型別歷史營收：同步服務

建立日期：2026-08-07
資料表：`app/models/opera_segment.py`
決策依據：`docs/EVAL_ohip_strategic_data.md` §4.3（重寫後的順位 2'）

═══════════════════════════════════════════════════════════════════════════
兩種模式
═══════════════════════════════════════════════════════════════════════════
| 模式 | 何時跑 | 範圍 |
|------|-------|------|
| `backfill` | 網頁手動，可重複按到補完 | 往前 2 年，**每次補一段** |
| `backfill`（全部） | `sync_tool.py`，補完自動 skip | 往前 2 年，**一次跑完所有待補段** |
| `incremental` | 每日 06:30 排程 | 最近 `INCREMENTAL_DAYS` 天 |

⚠️ **為什麼回補要做成「每次補一段」而不是一次跑完**
   兩年 = 730 天，三維度交叉容易撞 2 MB 靜默截斷，所以切成 45 天一段 → 約 17 段。
   每段約 3 秒，一次跑完會讓 HTTP 請求逾時。
   做成可續跑之後，中斷了也能接著補，不必從頭來。

⚠️ **為什麼增量要重抓最近幾天而不是只抓昨天**
   OPERA 的日結（EOD）之後帳務還可能修正，而且排程有可能漏跑。
   重抓最近幾天是用 upsert 覆蓋，成本低、但能自動修好這兩種情況。

═══════════════════════════════════════════════════════════════════════════
三件事情刻意不做
═══════════════════════════════════════════════════════════════════════════
① **不走 `ohip_async_cache`。** 回補與增量的日期區間每次都不同，
   本來就不會命中快取；走快取只會在快取表塞進大量再也用不到的列。
   也因為參數天天不同，不受 30 分鐘限流影響。

② **不碰 `opera_revenue_daily`。** 那是 TXT 上傳的落地結果，
   兩者粒度、來源、口徑都不同（理由詳見 model 檔頭）。
   本服務只寫 `ohip_revenue_history`，一個欄位都不動既有表。

③ **不做「哪一份才對」的仲裁。** API 與 TXT 有差異時，本服務照實落地 API 的值，
   不去調整成 TXT 的口徑。差異的比對是 `/realtime/compare` 的職責。
"""
from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import twnow
from app.models.opera_segment import OhipRevenueHistory, OhipRevenueHistorySync
from app.services import ohip_client
from app.services import realtime_revenue_service as RS

# ── 設定 ─────────────────────────────────────────────────────────────────────
BACKFILL_YEARS = 2              # 往前回補幾年（可做 YoY 同期比較）
CHUNK_DAYS = 45                 # ⚠️ 限制因素是 2 MB 回應大小，不是 API 的日期上限
INCREMENTAL_DAYS = 14           # 每日增量重抓最近幾天（涵蓋 EOD 修正與漏跑）
GROUP_BY = [RS.GROUP_BY_MARKET, RS.GROUP_BY_ROOM_TYPE]

STATUS_OK = "ok"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"


def backfill_start_date(today: date | None = None) -> date:
    t = today or date.today()
    try:
        return t.replace(year=t.year - BACKFILL_YEARS)
    except ValueError:
        # 2/29 的閏年處理
        return t.replace(year=t.year - BACKFILL_YEARS, day=28)


# ── 回補進度 ─────────────────────────────────────────────────────────────────

def _all_chunks(today: date | None = None) -> list[tuple[date, date]]:
    """把回補範圍切成固定的段。⚠️ 段界固定（從最早往後推），
    這樣「已補到哪一段」才有穩定的定義，不會因為今天日期不同而位移。"""
    t = today or date.today()
    start = backfill_start_date(t)
    end = t - timedelta(days=1)          # 今天還沒過完，交給增量處理
    out: list[tuple[date, date]] = []
    cur = start
    while cur <= end:
        seg_end = min(cur + timedelta(days=CHUNK_DAYS - 1), end)
        out.append((cur, seg_end))
        cur = seg_end + timedelta(days=1)
    return out


def _split_chunks(db: Session, today: date | None = None
                  ) -> tuple[list[tuple[date, date]], list[tuple[date, date]]]:
    """把所有段分成 (已補, 待補)。

    ⚠️ 判斷「這一段補過了沒」用的是**該段有沒有任何一列資料**，
       而不是同步紀錄 —— 紀錄可能被清、也可能因為當機沒寫完，
       但資料在不在是客觀事實。
    """
    hotel_id = settings.OHIP_HOTEL_ID
    done: list[tuple[date, date]] = []
    pending: list[tuple[date, date]] = []
    for a, b in _all_chunks(today):
        exists = (db.query(OhipRevenueHistory.id)
                    .filter(OhipRevenueHistory.hotel_id == hotel_id,
                            OhipRevenueHistory.business_date >= a.isoformat(),
                            OhipRevenueHistory.business_date <= b.isoformat())
                    .first())
        (done if exists else pending).append((a, b))
    return done, pending


def backfill_progress(db: Session, today: date | None = None) -> dict[str, Any]:
    """回補進度。"""
    chunks = _all_chunks(today)
    done, pending = _split_chunks(db, today)

    return {
        "total_chunks": len(chunks),
        "done_chunks": len(done),
        "pending_chunks": len(pending),
        "chunk_days": CHUNK_DAYS,
        "range": {
            "start": chunks[0][0].isoformat() if chunks else None,
            "end": chunks[-1][1].isoformat() if chunks else None,
            "years": BACKFILL_YEARS,
        },
        "next_chunk": ({"start": pending[0][0].isoformat(),
                        "end": pending[0][1].isoformat()} if pending else None),
        "estimated_remaining_seconds": len(pending) * 4,
    }


# ── 核心：抓一段並落地 ───────────────────────────────────────────────────────

def _sync_range(db: Session, start: date, end: date, *, mode: str,
                triggered_by: str) -> dict[str, Any]:
    """抓 start～end 一段並 upsert 落地。回傳執行摘要。"""
    started = time.perf_counter()
    hotel_id = settings.OHIP_HOTEL_ID
    rec = OhipRevenueHistorySync(
        hotel_id=hotel_id, mode=mode,
        date_start=start.isoformat(), date_end=end.isoformat(),
        started_at=twnow(), triggered_by=triggered_by[:120],
    )

    if not ohip_client.is_configured():
        rec.status = STATUS_FAILED
        rec.error = "OHIP 尚未設定完成，缺少：" + "、".join(ohip_client.missing_settings())
        rec.finished_at = twnow()
        return _finish(db, rec, started)

    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    api_calls = 0
    total_bytes = 0

    for a, b in _chunks(start, end):
        try:
            raw, meta = RS._fetch(db, a, b, GROUP_BY, triggered_by)
        except Exception as e:
            # ⚠️ 抓 Exception 不只 OhipError：連線／解析／限流各種例外都要留下紀錄，
            #    否則失敗時連「試過哪一段」都查不到
            rec.status = STATUS_FAILED
            rec.error = f"{a}～{b} 取數失敗：{type(e).__name__}: {e}"
            rec.api_calls = api_calls
            rec.finished_at = twnow()
            return _finish(db, rec, started)

        api_calls += 1
        total_bytes += int(meta.get("response_bytes") or 0)
        if meta.get("truncation_risk"):
            # ⚠️「可能」不是「已」—— 我們無法確認（官方沒提供任何截斷訊號）
            warnings.append(
                f"{a}～{b}：回應 {meta.get('response_bytes'):,} bytes，"
                f"已逼近 2 MB 上限，資料**可能**被靜默截斷。"
                f"建議調小 CHUNK_DAYS（目前 {CHUNK_DAYS}）後重補這一段。"
            )

        for r in raw:
            rows.append(RS._normalize(r))

    written = _upsert(db, hotel_id, rows)

    rec.rows_written = written
    rec.api_calls = api_calls
    rec.response_bytes = total_bytes
    rec.warnings = "\n".join(warnings)
    rec.status = STATUS_PARTIAL if warnings else STATUS_OK
    rec.finished_at = twnow()
    return _finish(db, rec, started)


def _chunks(start: date, end: date) -> list[tuple[date, date]]:
    out: list[tuple[date, date]] = []
    cur = start
    while cur <= end:
        seg_end = min(cur + timedelta(days=CHUNK_DAYS - 1), end)
        out.append((cur, seg_end))
        cur = seg_end + timedelta(days=1)
    return out


def _upsert(db: Session, hotel_id: str, rows: list[dict[str, Any]]) -> int:
    """依唯一鍵（hotel, business_date, market_code, room_type）覆寫。

    ⚠️ 用「先讀既有 → 更新或新增」而不是「先刪整段再插入」：
       若這次 API 只回了部分維度，整段刪除會把上次抓到的其他維度也刪掉，
       而歷史資料一旦刪掉要重抓（雖然補得回來，但沒必要冒這個險）。
    """
    if not rows:
        return 0

    keys = {(r.get("business_date") or "",
             (r.get("market_code") or "")[:40],
             (r.get("room_type") or "")[:40]) for r in rows}
    dates = sorted({k[0] for k in keys if k[0]})
    if not dates:
        return 0

    existing = {
        (e.business_date, e.market_code, e.room_type): e
        for e in db.query(OhipRevenueHistory).filter(
            OhipRevenueHistory.hotel_id == hotel_id,
            OhipRevenueHistory.business_date >= dates[0],
            OhipRevenueHistory.business_date <= dates[-1],
        ).all()
    }

    now = twnow()
    written = 0
    for r in rows:
        bd = r.get("business_date") or ""
        if not bd:
            continue
        mc = (r.get("market_code") or "")[:40]
        rt = (r.get("room_type") or "")[:40]
        obj = existing.get((bd, mc, rt))
        if obj is None:
            obj = OhipRevenueHistory(hotel_id=hotel_id, business_date=bd,
                                     market_code=mc, room_type=rt)
            db.add(obj)
            existing[(bd, mc, rt)] = obj

        obj.res_type = (r.get("res_type") or "")[:40]
        obj.physical_rooms = _i(r.get("physical_rooms"))
        obj.ooo_rooms = _i(r.get("ooo_rooms"))
        obj.oos_rooms = _i(r.get("oos_rooms"))
        obj.rooms_sold = _i(r.get("rooms_sold"))
        obj.arrival_rooms = _i(r.get("arrival_rooms"))
        obj.departure_rooms = _i(r.get("departure_rooms"))
        obj.cancelled_rooms = _i(r.get("cancelled_rooms"))
        obj.no_show_rooms = _i(r.get("no_show_rooms"))
        obj.room_revenue = r.get("room_revenue")
        obj.total_revenue = r.get("total_revenue")
        obj.food_revenue = r.get("food_revenue")
        obj.synced_at = now
        written += 1

    db.commit()
    return written


def _i(v: Any) -> int | None:
    """⚠️ 缺值回 None，**不補 0**（0 與「沒有」是不同的事）。"""
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _finish(db: Session, rec: OhipRevenueHistorySync, started: float) -> dict[str, Any]:
    rec.elapsed_ms = int((time.perf_counter() - started) * 1000)
    if rec.finished_at is None:
        rec.finished_at = twnow()
    try:
        db.add(rec)
        db.commit()
    except Exception:
        db.rollback()
    return {
        "mode": rec.mode,
        "date_start": rec.date_start,
        "date_end": rec.date_end,
        "status": rec.status,
        "rows_written": rec.rows_written,
        "api_calls": rec.api_calls,
        "response_bytes": rec.response_bytes,
        "elapsed_ms": rec.elapsed_ms,
        "warnings": [w for w in (rec.warnings or "").split("\n") if w],
        "error": rec.error or "",
    }


# ── 對外 ─────────────────────────────────────────────────────────────────────

def backfill_next_chunk(db: Session, *, triggered_by: str = "",
                        today: date | None = None) -> dict[str, Any]:
    """補下一個還沒補的段。可以重複呼叫直到補完。"""
    prog = backfill_progress(db, today)
    nxt = prog.get("next_chunk")
    if not nxt:
        return {"done": True, "progress": prog,
                "message": "回補已完成，沒有待補的區段。"}

    result = _sync_range(db, date.fromisoformat(nxt["start"]),
                         date.fromisoformat(nxt["end"]),
                         mode="backfill", triggered_by=triggered_by)
    return {"done": False, "result": result,
            "progress": backfill_progress(db, today)}


def sync_backfill_all(*, triggered_by: str = "sync_tool",
                      today: date | None = None) -> dict[str, Any]:
    """把所有待補的段一次補完（給 `sync_tool.py` 用）。

    ⚠️ **和網頁的「補下一段」是同一件事，只是不受 HTTP 逾時限制。**
       切成 45 天一段的理由是 2 MB 回應上限，不是 API 的日期上限；
       「每次只補一段」則純粹是為了讓網頁請求不逾時。sync_tool 是本機
       GUI、跑在背景執行緒，沒有這個限制，所以可以一次跑完（約 17 段 × 3～4 秒）。

    ⚠️ **補完就 skip，不打 OHIP。** sync_tool 的自動同步最短 15 分一輪，
       每輪都重跑會白白消耗 API 配額。`pending_chunks == 0` 時只做一次
       DB 查詢就回報「無事可做」。

    ⚠️ **一次執行只走過一輪 pending 清單，不重算進度。**
       `_split_chunks()` 判定「補過了沒」看的是該段**有沒有資料**，
       所以飯店開業前那種本來就沒有資料的段，抓完仍然是 pending。
       若改成「迴圈到 pending 歸零」會在那種段上無窮打 API。
       （網頁的「補下一段」在這種情況會卡在同一段，屬既有行為，本函式不處理。）

    ⚠️ **不碰增量。** 昨天的資料由 `main.py` 每日 06:30 的 `sync_incremental`
       負責（重抓最近 14 天）。兩邊都跑只是重複打 OHIP。

    回傳格式對齊 sync_tool 的期待：`fetched` / `upserted` / `errors`。
    """
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        if not ohip_client.is_configured():
            # 未設定就跑會讓 sync_tool 每輪紅燈。這是「沒設定」不是「失敗」。
            return {
                "fetched": 0, "upserted": 0, "errors": 0,
                "chunks_total": 0, "chunks_done": 0, "chunks_failed": 0,
                "skipped": True,
                "message": "OHIP 尚未設定完成，缺少：" + "、".join(ohip_client.missing_settings()),
            }

        _, pending = _split_chunks(db, today)
        if not pending:
            return {
                "fetched": 0, "upserted": 0, "errors": 0,
                "chunks_total": 0, "chunks_done": 0, "chunks_failed": 0,
                "skipped": True, "message": "回補已完成，沒有待補的區段。",
            }

        written = 0
        ok = 0
        failed = 0
        errors: list[str] = []
        warnings: list[str] = []
        for a, b in pending:
            r = _sync_range(db, a, b, mode="backfill", triggered_by=triggered_by)
            written += int(r.get("rows_written") or 0)
            warnings.extend(r.get("warnings") or [])
            if r.get("status") == STATUS_FAILED:
                failed += 1
                errors.append(r.get("error") or f"{a}～{b} 失敗")
                # ⚠️ 失敗多半是連線／認證問題，後面的段大概率也會失敗。
                #    繼續跑只是把同一個錯誤重複 17 次，直接停掉。
                break
            ok += 1

        return {
            "fetched": written, "upserted": written, "errors": failed,
            "chunks_total": len(pending),
            "chunks_done": ok,
            "chunks_failed": failed,
            "skipped": False,
            "error_messages": errors,
            "warnings": warnings,
        }
    finally:
        db.close()


def sync_incremental(db: Session, *, days: int = INCREMENTAL_DAYS,
                     triggered_by: str = "scheduler") -> dict[str, Any]:
    """每日增量：重抓最近 N 天並覆蓋（涵蓋 EOD 後的帳務修正與排程漏跑）。"""
    end = date.today() - timedelta(days=1)      # 今天還沒過完
    start = end - timedelta(days=max(days, 1) - 1)
    return _sync_range(db, start, end, mode="incremental", triggered_by=triggered_by)


def list_syncs(db: Session, *, limit: int = 30) -> list[dict[str, Any]]:
    q = (db.query(OhipRevenueHistorySync)
           .order_by(OhipRevenueHistorySync.started_at.desc())
           .limit(max(min(limit, 200), 1)))
    return [{
        "mode": r.mode, "date_start": r.date_start, "date_end": r.date_end,
        "status": r.status, "rows_written": r.rows_written,
        "api_calls": r.api_calls, "elapsed_ms": r.elapsed_ms,
        "started_at": r.started_at.isoformat(timespec="seconds") if r.started_at else None,
        "warnings": [w for w in (r.warnings or "").split("\n") if w],
        "error": r.error or "", "triggered_by": r.triggered_by,
    } for r in q.all()]
