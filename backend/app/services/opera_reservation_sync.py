"""
營運分析 — 訂房分析：同步服務（rsvasync + blkasync）

建立日期：2026-08-07
資料表：`app/models/opera_reservation.py`
實測依據：`docs/EVAL_ohip_strategic_data.md` §4.1、§4.2

═══════════════════════════════════════════════════════════════════════════
兩支已實測確認的端點
═══════════════════════════════════════════════════════════════════════════
```
POST /rsv/async/v1/externalSystems/{ext}/hotels/{hotel}/reservations/dailySummary
     body {"criteria": {"timeSpan": {"startDate": ..., "endDate": ...}}}

POST /blk/async/v1/externalSystems/{ext}/hotels/{hotel}/blocks/allocationSummary
     body {"startDate": ..., "endDate": ...}
```

⚠️ **兩支的 body 形狀不一樣**（rsv 巢狀、blk 平放）。這不是筆誤，是 OPERA 的實況。

⚠️ 命名形狀是**斜線分段**（`reservations/dailySummary`），
   不是 `invasync` 的駝峰單段（`revenueInventoryStatistics`）。

═══════════════════════════════════════════════════════════════════════════
解析時必須注意的四件事（全部來自實測，不是推測）
═══════════════════════════════════════════════════════════════════════════
① **數值型別混雜。** `noOfRooms` 是字串 `"1"`、`children1` 是 int、
   `rateAmount` 是字串 `"1000"`、`roomRevenue` 是字串 `"952.380952380952"`，
   而 block 的 `originalRooms` 是 int、`roomRevenue` 是 float。
   → 一律用 `_i()` / `_num()` 轉換，不要假設型別。

② **日期是 ISO datetime 不是 date**（`"2026-01-05T00:00:00"`）。
   → 落地只取前 10 碼。時間部分一律是 00:00:00，沒有資訊量
   （這也是為什麼**退房時間分布做不到** —— `checkedOutDate` 同樣沒有時間）。

③ **值為 0／空的欄位會被整個省略。** 一律 `row.get(k)`，缺值存 None／空字串，
   **不補 0**。

④ **block 是三層巢狀**：`allocationDates[].allocations[]`。
   第一版誤以為兩層（見 CHANGELOG [1.90.15]）。

═══════════════════════════════════════════════════════════════════════════
⚠️ 個資：預設不落地訂房聯絡人姓名
═══════════════════════════════════════════════════════════════════════════
`resvContactName`（7%）是**自然人姓名**。本模組規劃的六類分析
（前置期／取消／在手／通路／RateCode／團體）**沒有任何一項需要它**，
依最小必要原則預設不存。

要存的話把 `STORE_CONTACT_NAME` 改成 True —— 但請先確認有業務理由，
不要「先存起來以後可能會用到」。
（`/opera/guest` 有存住客姓名，那是既有決定，不構成本模組也該存的理由。）
"""
from __future__ import annotations

import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import twnow
from app.models.opera_reservation import (OhipBlock, OhipBlockAllocation,
                                          OhipReservation, OhipReservationNight,
                                          OhipReservationSync)
from app.services import ohip_client

# ── 設定 ─────────────────────────────────────────────────────────────────────
BACKFILL_YEARS = 2
# ⚠️ 訂房是逐筆＋逐日，資料量比營收大得多。實測 2 個月＝2375 筆／5.68 MB，
#    所以切段比營收更小。**限制因素是單次回應大小與處理時間，不是 API 日期上限。**
RSV_CHUNK_DAYS = 31
BLK_CHUNK_DAYS = 92          # block 數量少很多（實測 2 個月只有 5 個）
INCREMENTAL_DAYS = 14        # 每日增量重抓最近幾天（涵蓋改單與排程漏跑）

# ⚠️ 個資：預設不落地訂房聯絡人姓名（見檔頭）
STORE_CONTACT_NAME = False

RSV_PATH = "/rsv/async/v1/externalSystems/{ext}/hotels/{hotel}/reservations/dailySummary"
BLK_PATH = "/blk/async/v1/externalSystems/{ext}/hotels/{hotel}/blocks/allocationSummary"

STATUS_OK = "ok"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"


# ── 型別轉換（實測：型別混雜，不能假設）──────────────────────────────────────

def _i(v: Any) -> int | None:
    """→ int。⚠️ 缺值回 None，**不補 0**。"""
    if v is None or v == "":
        return None
    try:
        return int(Decimal(str(v)))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _num(v: Any) -> Decimal | None:
    """→ Decimal。⚠️ 金額全程 Decimal，用 float 累加會有精度誤差。"""
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _d(v: Any) -> str:
    """ISO datetime → 日期字串。⚠️ 時間部分一律 00:00:00，沒有資訊量。"""
    if not v:
        return ""
    return str(v)[:10]


def _dt(v: Any) -> str:
    return str(v)[:19] if v else ""


def _s(v: Any, n: int) -> str:
    return str(v)[:n] if v not in (None, "") else ""


def _confirmation_no(rec: dict) -> str:
    """從 `reservationIdList[]` 取 type=='Confirmation' 的 id。100% 有值。"""
    for item in rec.get("reservationIdList") or []:
        if str(item.get("type", "")).lower() == "confirmation":
            return _s(item.get("id"), 40)
    # 沒有 Confirmation 就退而求其次取第一個，避免整筆掉落
    for item in rec.get("reservationIdList") or []:
        if item.get("id"):
            return _s(item.get("id"), 40)
    return ""


def _guest_ext_id(rec: dict) -> str:
    """`externalReferences[]` 中 idContext=='GUESTID' 的值（56%）。

    ⚠️ **能不能當回訪識別尚未驗證** —— 落地是為了之後能驗證，
       不代表現在可以拿來做回訪分析。
    """
    for ref in rec.get("externalReferences") or []:
        if str(ref.get("idContext", "")).upper() == "GUESTID":
            return _s(ref.get("id"), 80)
    return ""


def _nested_id(rec: dict, key: str) -> str:
    """`travelAgentId` / `companyId` / `groupId` 都是 `{id, type}` 物件。"""
    obj = rec.get(key)
    if isinstance(obj, dict):
        return _s(obj.get("id"), 40)
    return _s(obj, 40)


def _lead_days(booking: str, arrival: str) -> int | None:
    """🎯 訂房前置期 = 到達日 − 訂房日。本模組的核心衍生欄位。"""
    if not booking or not arrival:
        return None
    try:
        return (date.fromisoformat(arrival) - date.fromisoformat(booking)).days
    except ValueError:
        return None


def _nights(arrival: str, departure: str) -> int | None:
    if not arrival or not departure:
        return None
    try:
        return (date.fromisoformat(departure) - date.fromisoformat(arrival)).days
    except ValueError:
        return None


# ── 切段 ─────────────────────────────────────────────────────────────────────

def _chunks(start: date, end: date, size: int) -> list[tuple[date, date]]:
    out: list[tuple[date, date]] = []
    cur = start
    while cur <= end:
        seg_end = min(cur + timedelta(days=size - 1), end)
        out.append((cur, seg_end))
        cur = seg_end + timedelta(days=1)
    return out


def backfill_start_date(today: date | None = None) -> date:
    t = today or date.today()
    try:
        return t.replace(year=t.year - BACKFILL_YEARS)
    except ValueError:
        return t.replace(year=t.year - BACKFILL_YEARS, day=28)


def _all_chunks(dataset: str, today: date | None = None) -> list[tuple[date, date]]:
    """⚠️ 段界固定（從最早往後推），「補到哪一段」才有穩定定義。"""
    t = today or date.today()
    size = RSV_CHUNK_DAYS if dataset == "reservation" else BLK_CHUNK_DAYS
    return _chunks(backfill_start_date(t), t - timedelta(days=1), size)


# ── 解析：訂房 ───────────────────────────────────────────────────────────────

def _parse_reservations(payload: Any, hotel_id: str
                        ) -> tuple[list[OhipReservation], list[OhipReservationNight]]:
    """回應形狀（實測）：`{"reservations": [ {...}, ... ]}`"""
    recs = []
    if isinstance(payload, dict):
        recs = payload.get("reservations") or []
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                recs.extend(item.get("reservations") or [])

    parents: list[OhipReservation] = []
    children: list[OhipReservationNight] = []
    seen_nights: set[tuple[str, str]] = set()

    for r in recs:
        conf = _confirmation_no(r)
        if not conf:
            continue

        arrival = _d(r.get("arrival"))
        departure = _d(r.get("departure"))
        booking = _d(r.get("bookingDate"))

        # children1/2/3 是三個獨立欄位（不同年齡層），合計才是總童數
        kids = [_i(r.get(k)) for k in ("children1", "children2", "children3")]
        kids_total = sum(k for k in kids if k is not None) if any(
            k is not None for k in kids) else None

        parents.append(OhipReservation(
            hotel_id=hotel_id, confirmation_no=conf,
            arrival=arrival, departure=departure, booking_date=booking,
            checked_out_date=_d(r.get("checkedOutDate")),
            lead_days=_lead_days(booking, arrival),
            nights=_nights(arrival, departure),
            resv_status=_s(r.get("resvStatus"), 30),
            resv_type=_s(r.get("resvType"), 30),
            no_of_rooms=_i(r.get("noOfRooms")),
            shared_yn=_s(r.get("sharedYn"), 2),
            origin_of_booking=_s(r.get("origin_of_booking"), 20),
            cancellation_date=_d(r.get("cancellationDate")),
            cancellation_reason_code=_s(r.get("cancellationReasonCode"), 30),
            travel_agent_name=_s(r.get("travelAgentName"), 160),
            travel_agent_id=_nested_id(r, "travelAgentId"),
            iata_code=_s(r.get("iataCode"), 20),
            company_name=_s(r.get("companyName"), 160),
            company_id=_nested_id(r, "companyId"),
            group_name=_s(r.get("groupName"), 160),
            group_id=_nested_id(r, "groupId"),
            block_code=_s(r.get("blockCode"), 40),
            nationality=_s(r.get("nationality"), 10),
            guest_country=_s(r.get("guestCountry"), 10),
            children_total=kids_total,
            # ⚠️ 個資：預設不存（見檔頭）
            resv_contact_name=(_s(r.get("resvContactName"), 160)
                               if STORE_CONTACT_NAME else ""),
            guest_ext_id=_guest_ext_id(r),
            created_datetime=_dt(r.get("createDateTime")),
            last_modified_date=_dt(r.get("lastModifiedDate")),
        ))

        for n in r.get("dailySummary") or []:
            trx = _d(n.get("trxDate"))
            if not trx or (conf, trx) in seen_nights:
                continue
            seen_nights.add((conf, trx))
            children.append(OhipReservationNight(
                hotel_id=hotel_id, confirmation_no=conf, trx_date=trx,
                market_code=_s(n.get("marketCode"), 40),
                rate_code=_s(n.get("rateCode"), 40),
                source_code=_s(n.get("sourceCode"), 40),
                room_type=_s(n.get("roomType"), 40),
                booked_room_type=_s(n.get("bookedRoomType"), 40),
                room_type_charged=_s(n.get("roomTypeCharged"), 40),
                channel=_s(n.get("channel"), 40),
                room=_s(n.get("room"), 20),
                adults=_i(n.get("adults")),
                children=_i(n.get("children")),
                rate_amount=_num(n.get("rateAmount")),
                net_rate_amount=_num(n.get("netRateAmount")),
                room_revenue=_num(n.get("roomRevenue")),
                total_revenue=_num(n.get("totalRevenue")),
                tax=_num(n.get("tax")),
                currency=_s(n.get("roomRevenueCurrency") or n.get("rateAmountCurrency"), 10),
            ))

    return parents, children


# ── 解析：團體 ───────────────────────────────────────────────────────────────

def _block_company(b: dict) -> tuple[str, str]:
    """從 `blockProfiles.blockProfile[].profile.company.companyName` 取公司名。

    ⚠️ 這是四層巢狀，而且 `blockProfiles` 是 **dict** 不是 list
       （裡面才是 `blockProfile` 陣列）—— 實測形狀，容易寫錯。
    """
    bp = b.get("blockProfiles")
    items = bp.get("blockProfile") if isinstance(bp, dict) else bp
    for item in items or []:
        prof = (item or {}).get("profile") or {}
        company = prof.get("company") or {}
        name = company.get("companyName")
        if name:
            return _s(name, 200), _s(item.get("blockProfileType")
                                     or prof.get("profileType"), 40)
    return "", ""


def _parse_blocks(payload: Any, hotel_id: str
                  ) -> tuple[list[OhipBlock], list[OhipBlockAllocation]]:
    """回應形狀（實測）：最外層直接是 block 的 list。"""
    blocks = payload if isinstance(payload, list) else [payload]

    parents: list[OhipBlock] = []
    children: list[OhipBlockAllocation] = []
    seen: set[tuple[str, str, str]] = set()

    for b in blocks:
        if not isinstance(b, dict):
            continue
        bid = _s(b.get("blockId"), 40)
        if not bid:
            continue

        company, ptype = _block_company(b)
        parents.append(OhipBlock(
            hotel_id=hotel_id, block_id=bid,
            block_code=_s(b.get("blockCode"), 40),
            block_name=_s(b.get("blockName"), 200),
            status=_s(b.get("status"), 20),
            block_type=_s(b.get("blockType"), 20),
            market_code=_s(b.get("marketCode"), 40),
            source_code=_s(b.get("sourceCode"), 40),
            booking_medium=_s(b.get("bookingMedium"), 40),
            rate_plan_code=_s(b.get("ratePlanCode"), 40),
            start_date=_d(b.get("startDate")), end_date=_d(b.get("endDate")),
            cut_off_days=_i(b.get("cutOffDays")),
            currency=_s(b.get("currency"), 10),
            company_name=company, profile_type=ptype,
            cancellation_code=_s(b.get("cancellationCode"), 30),
            cancellation_date=_d(b.get("cancellationDate")),
            cancellation_description=_s(b.get("cancellationDescription"), 2000),
            create_datetime=_dt(b.get("createDateTime")),
            last_modified_date=_dt(b.get("lastModifiedDate")),
        ))

        # ⚠️ 三層巢狀：allocationDates[] → allocations[]
        for ad in b.get("allocationDates") or []:
            adate = _d(ad.get("allocationDate"))
            for al in ad.get("allocations") or []:
                rt = _s(al.get("roomType"), 40)
                key = (bid, adate, rt)
                if not adate or key in seen:
                    continue
                seen.add(key)
                rev = al.get("actualRevenue") or {}
                rates = al.get("rates") or {}
                inv = al.get("inventory") or {}
                children.append(OhipBlockAllocation(
                    hotel_id=hotel_id, block_id=bid,
                    allocation_date=adate, room_type=rt,
                    original_rooms=_i(al.get("originalRooms")),
                    current_rooms=_i(al.get("currentRooms")),
                    pickup_rooms=_i(al.get("pickupRooms")),
                    sell_limit=_i(inv.get("sellLimit")),
                    rate_one_person=_num(rates.get("onePerson")),
                    rate_two_person=_num(rates.get("twoPerson")),
                    room_revenue=_num(rev.get("roomRevenue")),
                    food_revenue=_num(rev.get("foodRevenue")),
                    other_revenue=_num(rev.get("otherRevenue")),
                    total_revenue=_num(rev.get("totalRevenue")),
                    currency=_s(rev.get("currency"), 10),
                ))

    return parents, children


# ── 取數與落地 ───────────────────────────────────────────────────────────────

def _sync_range(db: Session, dataset: str, start: date, end: date, *,
                mode: str, triggered_by: str) -> dict[str, Any]:
    started = time.perf_counter()
    hotel_id = settings.OHIP_HOTEL_ID
    ext = settings.OHIP_EXT_SYSTEM_CODE
    rec = OhipReservationSync(
        hotel_id=hotel_id, dataset=dataset, mode=mode,
        date_start=start.isoformat(), date_end=end.isoformat(),
        started_at=twnow(), triggered_by=triggered_by[:120],
    )

    if not ohip_client.is_configured():
        rec.status = STATUS_FAILED
        rec.error = "OHIP 尚未設定完成，缺少：" + "、".join(ohip_client.missing_settings())
        return _finish(db, rec, started)

    is_rsv = dataset == "reservation"
    path = (RSV_PATH if is_rsv else BLK_PATH).format(ext=ext, hotel=hotel_id)
    size = RSV_CHUNK_DAYS if is_rsv else BLK_CHUNK_DAYS

    warnings: list[str] = []
    calls = total_bytes = n_parent = n_child = 0

    for a, b in _chunks(start, end, size):
        # ⚠️ 兩支端點的 body 形狀不同（rsv 巢狀、blk 平放）—— 實測如此，非筆誤
        body = ({"criteria": {"timeSpan": {"startDate": a.isoformat(),
                                           "endDate": b.isoformat()}}}
                if is_rsv else
                {"startDate": a.isoformat(), "endDate": b.isoformat()})
        try:
            payload, meta = ohip_client.async_read(path, body, hotel_id=hotel_id)
        except Exception as e:
            # ⚠️ 抓 Exception 不只 OhipError：失敗時至少要留下「試過哪一段」
            rec.status = STATUS_FAILED
            rec.error = f"{a}～{b} 取數失敗：{type(e).__name__}: {e}"
            rec.api_calls = calls
            return _finish(db, rec, started)

        calls += 1
        total_bytes += int(meta.get("response_bytes") or 0)
        if meta.get("truncation_risk"):
            # ⚠️ 措辭是「可能」—— 實測 5.68 MB 仍完整解析，官方的 2 MB 說法存疑
            warnings.append(
                f"{a}～{b}：回應 {meta.get('response_bytes'):,} bytes 已逾 2 MB。"
                f"官方稱會靜默截斷，但實測未必；若擔心請縮小 CHUNK 後比對筆數。")

        parents, children = (_parse_reservations(payload, hotel_id) if is_rsv
                             else _parse_blocks(payload, hotel_id))
        p, c = _upsert(db, dataset, hotel_id, parents, children)
        n_parent += p
        n_child += c

    rec.parent_rows, rec.child_rows = n_parent, n_child
    rec.api_calls, rec.response_bytes = calls, total_bytes
    rec.warnings = "\n".join(warnings)
    rec.status = STATUS_PARTIAL if warnings else STATUS_OK
    return _finish(db, rec, started)


def _upsert(db: Session, dataset: str, hotel_id: str,
            parents: list, children: list) -> tuple[int, int]:
    """依唯一鍵覆寫。

    ⚠️ 用「先讀既有 → 更新或新增」而不是「先刪整段再插入」：
       若這次 API 只回了部分資料，整段刪除會把上次抓到的也刪掉。
    """
    if not parents and not children:
        return 0, 0

    is_rsv = dataset == "reservation"
    PModel = OhipReservation if is_rsv else OhipBlock
    CModel = OhipReservationNight if is_rsv else OhipBlockAllocation
    pkey = "confirmation_no" if is_rsv else "block_id"

    # ── 父表 ────────────────────────────────────────────────────────────────
    keys = [getattr(o, pkey) for o in parents]
    existing = {
        getattr(e, pkey): e
        for e in db.query(PModel).filter(PModel.hotel_id == hotel_id,
                                         getattr(PModel, pkey).in_(keys)).all()
    } if keys else {}

    now = twnow()
    skip = {"id", "_sa_instance_state", "synced_at"}
    for obj in parents:
        k = getattr(obj, pkey)
        cur = existing.get(k)
        if cur is None:
            obj.synced_at = now
            db.add(obj)
            existing[k] = obj
        else:
            for col in PModel.__table__.columns.keys():
                if col not in skip:
                    setattr(cur, col, getattr(obj, col))
            cur.synced_at = now

    # ── 子表 ────────────────────────────────────────────────────────────────
    # 子表用「該父鍵整批換掉」：明細本來就是父的附屬，父被重抓時明細應同步反映
    parent_ids = set(keys)
    if parent_ids:
        col = CModel.confirmation_no if is_rsv else CModel.block_id
        db.query(CModel).filter(CModel.hotel_id == hotel_id,
                                col.in_(list(parent_ids))).delete(
            synchronize_session=False)
    if children:
        db.bulk_save_objects(children)

    db.commit()
    return len(parents), len(children)


def _finish(db: Session, rec: OhipReservationSync, started: float) -> dict[str, Any]:
    rec.elapsed_ms = int((time.perf_counter() - started) * 1000)
    if rec.finished_at is None:
        rec.finished_at = twnow()
    try:
        db.add(rec)
        db.commit()
    except Exception:
        db.rollback()
    return {
        "dataset": rec.dataset, "mode": rec.mode,
        "date_start": rec.date_start, "date_end": rec.date_end,
        "status": rec.status, "parent_rows": rec.parent_rows,
        "child_rows": rec.child_rows, "api_calls": rec.api_calls,
        "response_bytes": rec.response_bytes, "elapsed_ms": rec.elapsed_ms,
        "warnings": [w for w in (rec.warnings or "").split("\n") if w],
        "error": rec.error or "",
    }


# ── 回補進度 ─────────────────────────────────────────────────────────────────

def backfill_progress(db: Session, dataset: str,
                      today: date | None = None) -> dict[str, Any]:
    """⚠️ 判斷「這段補過沒」用**該段有沒有資料**，不是同步紀錄 ——
    紀錄可能被清、也可能寫到一半當機，資料在不在是客觀事實。"""
    hotel_id = settings.OHIP_HOTEL_ID
    chunks = _all_chunks(dataset, today)
    pending = []
    for a, b in chunks:
        if dataset == "reservation":
            q = db.query(OhipReservation.id).filter(
                OhipReservation.hotel_id == hotel_id,
                OhipReservation.arrival >= a.isoformat(),
                OhipReservation.arrival <= b.isoformat())
        else:
            q = db.query(OhipBlock.id).filter(
                OhipBlock.hotel_id == hotel_id,
                OhipBlock.start_date >= a.isoformat(),
                OhipBlock.start_date <= b.isoformat())
        if not q.first():
            pending.append((a, b))

    return {
        "dataset": dataset,
        "total_chunks": len(chunks), "pending_chunks": len(pending),
        "done_chunks": len(chunks) - len(pending),
        "chunk_days": RSV_CHUNK_DAYS if dataset == "reservation" else BLK_CHUNK_DAYS,
        "range": {"start": chunks[0][0].isoformat() if chunks else None,
                  "end": chunks[-1][1].isoformat() if chunks else None,
                  "years": BACKFILL_YEARS},
        "next_chunk": ({"start": pending[0][0].isoformat(),
                        "end": pending[0][1].isoformat()} if pending else None),
        "estimated_remaining_seconds": len(pending) * 15,
    }


# ── 對外 ─────────────────────────────────────────────────────────────────────

def backfill_next_chunk(db: Session, dataset: str, *, triggered_by: str = "",
                        today: date | None = None) -> dict[str, Any]:
    """補下一個還沒補的段。可重複呼叫直到補完。

    ⚠️ 刻意不做成「一次補完兩年」：訂房兩年約 24 段、每段約 15 秒，
       一次跑完 HTTP 必逾時。做成可續跑後中斷也能接著補。
    """
    prog = backfill_progress(db, dataset, today)
    nxt = prog.get("next_chunk")
    if not nxt:
        return {"done": True, "progress": prog, "message": "回補已完成。"}
    result = _sync_range(db, dataset,
                         date.fromisoformat(nxt["start"]),
                         date.fromisoformat(nxt["end"]),
                         mode="backfill", triggered_by=triggered_by)
    return {"done": False, "result": result,
            "progress": backfill_progress(db, dataset, today)}


def sync_incremental(db: Session, *, days: int = INCREMENTAL_DAYS,
                     triggered_by: str = "scheduler") -> dict[str, Any]:
    """每日增量：訂房與團體各重抓最近 N 天。

    ⚠️ 重抓（而非只抓昨天）是刻意的：訂房會被改單、取消，排程也可能漏跑，
       覆蓋式重抓能自動修好這兩種情況。
    ⚠️ 訂房的區間**含未來** —— 在手訂房分析需要未來資料，
       只抓過去會讓「未來 60 天在手」永遠是空的。
    """
    today = date.today()
    out = {}
    # 訂房：過去 N 天 ～ 未來 180 天（在手訂房）
    out["reservation"] = _sync_range(
        db, "reservation", today - timedelta(days=max(days, 1)),
        today + timedelta(days=180), mode="incremental", triggered_by=triggered_by)
    # 團體：同樣涵蓋未來（cut-off 與 pickup 都是看未來）
    out["block"] = _sync_range(
        db, "block", today - timedelta(days=max(days, 1)),
        today + timedelta(days=180), mode="incremental", triggered_by=triggered_by)
    return out


def list_syncs(db: Session, *, limit: int = 30) -> list[dict[str, Any]]:
    q = (db.query(OhipReservationSync)
           .order_by(OhipReservationSync.started_at.desc())
           .limit(max(min(limit, 200), 1)))
    return [{
        "dataset": r.dataset, "mode": r.mode,
        "date_start": r.date_start, "date_end": r.date_end,
        "status": r.status, "parent_rows": r.parent_rows, "child_rows": r.child_rows,
        "api_calls": r.api_calls, "elapsed_ms": r.elapsed_ms,
        "started_at": r.started_at.isoformat(timespec="seconds") if r.started_at else None,
        "warnings": [w for w in (r.warnings or "").split("\n") if w],
        "error": r.error or "", "triggered_by": r.triggered_by,
    } for r in q.all()]
