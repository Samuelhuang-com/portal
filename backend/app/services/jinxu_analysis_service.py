"""
金旭 PMS 分析 — 分析服務（所有計算邏輯集中於此，router 不得自行運算）

規格書：docs/SPEC_jinxu_analytics.md §11

⚠️ 本模組全部是同步函式（def），由 router 透過 run_in_threadpool 呼叫。

═══ 三條不可違反的規則 ═══════════════════════════════════════════════════════

1. **母體條件自帶（§11.4 / E19）**
   每個查詢函式必須自己帶母體條件，不可依賴呼叫端記得傳。
   實測取消訂房佔 29.7%，母體選錯數字差三成。
       營運統計 → is_cancelled=0 AND is_dummy=0
       取消分析 → 含取消，排除 dummy
   `DUMY-RV` 一律排除（J15：非實際可入住房間，不計入可售房數與住房率）。

2. **淨額口徑（§11.2 / J6）**
   收入 = Σ amount（正負相加，沖帳自然抵銷）。
   沖帳判定用 is_reversal（收入類 + 負值），**不可比對備註字串**。
   純記錄性分錄 is_memo_only（39/67/61）一律排除於收入統計（J20）。

3. **備註欄不得外流（J17）**
   `JinxuLedgerEntry.remark` 儲存於 DB 供稽核，但**任何回傳給前端的 dict
   都不得包含它**。本模組所有 to-dict 函式都不放 remark。

═══ 加權公式 ════════════════════════════════════════════════════════════════
    ADR = Σ 報價總額 / Σ 房晚數        ← 先加總再相除
    ❌ 不可逐筆算 ADR 再平均（OPERA 規格書 §9.3 已驗證的原則）
"""
from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import Numeric, case, cast, func
from sqlalchemy.orm import Query, Session

from app.models.jinxu_ledger import (
    DEPOSIT_IN_CODES,
    DEPOSIT_OUT_CODES,
    GROUP_LABELS,
    ROOM_KIND_GUEST,
    SIDE_REVENUE,
    SIDE_SETTLEMENT,
    JinxuLedgerEntry,
    JinxuSubjectMap,
)
from app.models.jinxu_reservation import (
    STATUS_LABELS,
    JinxuReservation,
    JinxuReservationStay,
)

logger = logging.getLogger(__name__)

# 付款方式大類（§11.5）
PAYMENT_MACRO = {
    "CARD": ("信用卡", ("73", "74", "75", "77", "78", "79")),
    "EPAY": ("電子支付", ("71A", "71B")),
    "CASH": ("現金", ("71",)),
    "AR": ("簽帳", ("86", "86A")),
    "DEPOSIT_OUT": ("沖預收訂金", DEPOSIT_OUT_CODES),
    "OTHER_SET": ("其他", ("95",)),
}


def _f(v) -> float:
    """Decimal / None → float，供 JSON 序列化。"""
    if v is None:
        return 0.0
    return float(v) if isinstance(v, (Decimal, int, float)) else 0.0


def _pct(part: float, whole: float) -> float:
    return round(part / whole * 100, 2) if whole else 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  母體 Query（規則 1）
# ══════════════════════════════════════════════════════════════════════════════

def _ledger_q(
    db: Session,
    *,
    start_date: str = "",
    end_date: str = "",
    include_memo: bool = False,
    room_kind: str | None = None,
    subject_side: str | None = None,
    subject_code: str | None = None,
    subject_group: str | None = None,
    shift: str | None = None,
    operator_id: str | None = None,
    folio_type: str | None = None,
    booking_no: str | None = None,
    include_reversal: bool = True,
) -> Query:
    """分錄查詢母體。

    `include_memo=False` → 排除純記錄性分錄（J20，39/67/61 金額恆 0）。
    `room_kind=None` → **不篩選**，總額才對得上報表總計列。
                       要拆客房／非客房請明確傳入（J24）。
    `include_reversal=False` → 排除沖帳列，用於「僅看原始入帳」的查核視圖；
                       預設 True（淨額口徑，正負相加自然抵銷）。
    """
    q = db.query(JinxuLedgerEntry)
    if not include_memo:
        q = q.filter(JinxuLedgerEntry.is_memo_only == 0)
    if start_date:
        q = q.filter(JinxuLedgerEntry.business_date >= start_date)
    if end_date:
        q = q.filter(JinxuLedgerEntry.business_date <= end_date)
    if room_kind:
        q = q.filter(JinxuLedgerEntry.room_kind == room_kind)
    if subject_side:
        q = q.filter(JinxuLedgerEntry.subject_side == subject_side)
    if subject_code:
        q = q.filter(JinxuLedgerEntry.subject_code == subject_code)
    if subject_group:
        q = q.filter(JinxuLedgerEntry.subject_group == subject_group)
    if shift:
        q = q.filter(JinxuLedgerEntry.shift == shift)
    if operator_id:
        q = q.filter(JinxuLedgerEntry.operator_id == operator_id)
    if folio_type:
        q = q.filter(JinxuLedgerEntry.folio_type == folio_type)
    if booking_no:
        q = q.filter(JinxuLedgerEntry.booking_no == booking_no)
    if not include_reversal:
        q = q.filter(JinxuLedgerEntry.is_reversal == 0)
    return q


def _resv_q(
    db: Session,
    *,
    start_date: str = "",
    end_date: str = "",
    date_basis: str = "arrival",
    include_cancelled: bool = False,
    company_name: str | None = None,
    rate_code: str | None = None,
    source_name: str | None = None,
    resv_type: str | None = None,
    status_code: str | None = None,
) -> Query:
    """訂房查詢母體。

    ⚠️ `is_dummy=0` **永遠**成立（J15：虛擬訂房不計入任何統計）。
    ⚠️ `include_cancelled` 預設 False——營運統計必須排除取消（實測 29.7%）。
       只有取消分析才傳 True。
    """
    q = db.query(JinxuReservation).filter(JinxuReservation.is_dummy == 0)
    if not include_cancelled:
        q = q.filter(JinxuReservation.is_cancelled == 0)

    col = (
        JinxuReservation.departure_date
        if date_basis == "departure"
        else JinxuReservation.arrival_date
    )
    if start_date:
        q = q.filter(col >= start_date)
    if end_date:
        q = q.filter(col <= end_date)

    if company_name:
        q = q.filter(JinxuReservation.company_name == company_name)
    if rate_code:
        q = q.filter(JinxuReservation.rate_code == rate_code)
    if source_name:
        q = q.filter(JinxuReservation.source_name == source_name)
    if resv_type:
        q = q.filter(JinxuReservation.resv_type == resv_type)
    if status_code:
        q = q.filter(JinxuReservation.status_code == status_code)
    return q


def population_note(include_cancelled: bool = False) -> str:
    """前端每張圖表／KPI 都必須顯示的母體說明（§11.4）。"""
    return "母體：含取消訂房，已排除虛擬訂房" if include_cancelled \
        else "母體：已排除取消與虛擬訂房"


# ══════════════════════════════════════════════════════════════════════════════
#  期間
# ══════════════════════════════════════════════════════════════════════════════

def data_coverage(db: Session) -> dict:
    led = db.query(
        func.min(JinxuLedgerEntry.business_date),
        func.max(JinxuLedgerEntry.business_date),
    ).one()
    rv = db.query(
        func.min(JinxuReservation.arrival_date),
        func.max(JinxuReservation.arrival_date),
    ).one()
    years = {d[:4] for d in (led[0], led[1], rv[0], rv[1]) if d}
    return {
        "ledger_start": led[0] or "",
        "ledger_end": led[1] or "",
        "resv_start": rv[0] or "",
        "resv_end": rv[1] or "",
        "years_covered": sorted(years),
        # YoY 需跨年度資料。實測檔只有 2026 年 → 前端必須顯示「資料不足」
        "yoy_available": len(years) > 1,
    }


def period_label(start_date: str, end_date: str, coverage_end: str) -> str:
    """期間狀態標籤（§11.3）。"""
    if not start_date or not end_date:
        return "全部期間"
    same_month = start_date[:7] == end_date[:7]
    same_year = start_date[:4] == end_date[:4]
    partial = bool(coverage_end) and end_date > coverage_end
    tail = f"（至 {coverage_end[5:]}）" if partial else ""
    if same_month:
        return ("部分月份" if partial else "完整月份") + tail
    if same_year and start_date[5:] == "01-01" and end_date[5:] == "12-31":
        return ("部分年度" if partial else "完整年度") + tail
    return "自訂期間" + tail


# ══════════════════════════════════════════════════════════════════════════════
#  收入結構分析（主軸一）
# ══════════════════════════════════════════════════════════════════════════════

def revenue_summary(db: Session, *, start_date: str = "", end_date: str = "", **kw) -> dict:
    """KPI：總收入（淨額）、總抵充、沖帳率、交易筆數。"""
    base = _ledger_q(db, start_date=start_date, end_date=end_date, **kw)

    agg = base.with_entities(
        func.count(JinxuLedgerEntry.id),
        func.sum(case((JinxuLedgerEntry.subject_side == SIDE_REVENUE,
                       JinxuLedgerEntry.amount), else_=0)),
        func.sum(case((JinxuLedgerEntry.subject_side == SIDE_SETTLEMENT,
                       JinxuLedgerEntry.amount), else_=0)),
        func.sum(case((JinxuLedgerEntry.is_reversal == 1, 1), else_=0)),
        func.sum(case((JinxuLedgerEntry.is_reversal == 1,
                       -JinxuLedgerEntry.amount), else_=0)),
        func.sum(case(((JinxuLedgerEntry.subject_side == SIDE_REVENUE)
                       & (JinxuLedgerEntry.amount > 0),
                       JinxuLedgerEntry.amount), else_=0)),
    ).one()

    cnt, rev, settle, rev_cnt, rev_amt, gross_rev = agg
    cnt = cnt or 0
    return {
        "transaction_count": cnt,
        "revenue_net": _f(rev),
        "settlement_total": abs(_f(settle)),
        "reversal_count": int(rev_cnt or 0),
        "reversal_amount": _f(rev_amt),
        "reversal_rate_by_count": _pct(int(rev_cnt or 0), cnt),
        "reversal_rate_by_amount": _pct(_f(rev_amt), _f(gross_rev)),
        "note": (
            "收入為淨額（沖帳已抵銷）；已排除純記錄性分錄（轉帳／換房／弈夢空間）。"
            "沖帳筆數為收入統計口徑——全表 953 筆中有 103 筆落在純記錄科目"
            "（39.轉帳 102、61.弈夢空間 1，本身即正負配對淨額為 0），"
            "既已排除於收入統計，其內部配對亦不計入沖帳率。"
        ),
    }


def revenue_by_subject(
    db: Session, *, start_date: str = "", end_date: str = "",
    group_by: str = "code", **kw
) -> dict:
    """科目別或大類別彙總。group_by = 'code' | 'group'。"""
    base = _ledger_q(db, start_date=start_date, end_date=end_date,
                     subject_side=SIDE_REVENUE, **kw)
    key = (JinxuLedgerEntry.subject_group if group_by == "group"
           else JinxuLedgerEntry.subject_code)

    rows = base.with_entities(
        key,
        func.min(JinxuLedgerEntry.subject_name),
        func.count(JinxuLedgerEntry.id),
        func.sum(JinxuLedgerEntry.amount),
        func.sum(case((JinxuLedgerEntry.is_reversal == 1, 1), else_=0)),
    ).group_by(key).all()

    total = sum(_f(r[3]) for r in rows)
    items = [{
        "key": r[0] or "",
        "label": (GROUP_LABELS.get(r[0], r[0]) if group_by == "group" else (r[1] or "")),
        "count": r[2],
        "amount": _f(r[3]),
        "share_pct": _pct(_f(r[3]), total),
        "reversal_count": int(r[4] or 0),
    } for r in rows]
    items.sort(key=lambda x: -x["amount"])
    return {"total": total, "group_by": group_by, "items": items}


def revenue_monthly(db: Session, *, start_date: str = "", end_date: str = "", **kw) -> dict:
    """月趨勢（依大類拆分）。"""
    base = _ledger_q(db, start_date=start_date, end_date=end_date,
                     subject_side=SIDE_REVENUE, **kw)
    month = func.substr(JinxuLedgerEntry.business_date, 1, 7)
    rows = base.with_entities(
        month, JinxuLedgerEntry.subject_group,
        func.sum(JinxuLedgerEntry.amount), func.count(JinxuLedgerEntry.id),
    ).group_by(month, JinxuLedgerEntry.subject_group).all()

    by_month: dict[str, dict] = {}
    for m, g, amt, c in rows:
        d = by_month.setdefault(m, {"month": m, "total": 0.0, "groups": {}})
        d["groups"][g] = {"label": GROUP_LABELS.get(g, g),
                          "amount": _f(amt), "count": c}
        d["total"] += _f(amt)
    return {"items": [by_month[k] for k in sorted(by_month)]}


def revenue_daily(db: Session, *, start_date: str = "", end_date: str = "", **kw) -> dict:
    base = _ledger_q(db, start_date=start_date, end_date=end_date, **kw)
    rows = base.with_entities(
        JinxuLedgerEntry.business_date,
        func.sum(case((JinxuLedgerEntry.subject_side == SIDE_REVENUE,
                       JinxuLedgerEntry.amount), else_=0)),
        func.sum(case((JinxuLedgerEntry.subject_side == SIDE_SETTLEMENT,
                       JinxuLedgerEntry.amount), else_=0)),
        func.count(JinxuLedgerEntry.id),
    ).group_by(JinxuLedgerEntry.business_date).order_by(JinxuLedgerEntry.business_date).all()
    return {"items": [{
        "business_date": r[0],
        "revenue_net": _f(r[1]),
        "settlement_total": abs(_f(r[2])),
        "transaction_count": r[3],
    } for r in rows]}


def revenue_by_room_kind(db: Session, *, start_date: str = "", end_date: str = "") -> dict:
    """客房 vs 非客房拆分（J24）。

    非客房（H0／M0／OT／RV）實測 1,615 筆，**其中含 623 筆房租**，
    因此不可靜默丟棄；客房統計排除，但另立此區塊供檢視。
    """
    base = _ledger_q(db, start_date=start_date, end_date=end_date,
                     subject_side=SIDE_REVENUE)
    rows = base.with_entities(
        JinxuLedgerEntry.room_kind,
        func.count(JinxuLedgerEntry.id),
        func.sum(JinxuLedgerEntry.amount),
    ).group_by(JinxuLedgerEntry.room_kind).all()

    out = {"items": [], "note": "非客房房號（H0/M0/OT/RV）語意待確認，暫不併入客房統計"}
    for kind, cnt, amt in rows:
        detail = base.filter(JinxuLedgerEntry.room_kind == kind).with_entities(
            JinxuLedgerEntry.subject_code,
            func.min(JinxuLedgerEntry.subject_name),
            func.count(JinxuLedgerEntry.id),
            func.sum(JinxuLedgerEntry.amount),
        ).group_by(JinxuLedgerEntry.subject_code).all()
        out["items"].append({
            "room_kind": kind,
            "label": "客房" if kind == ROOM_KIND_GUEST else "非客房",
            "count": cnt,
            "amount": _f(amt),
            "subjects": sorted([{
                "subject_code": d[0], "subject_name": d[1] or "",
                "count": d[2], "amount": _f(d[3]),
            } for d in detail], key=lambda x: -abs(x["amount"]))[:20],
        })
    return out


def shift_summary(db: Session, *, start_date: str = "", end_date: str = "") -> dict:
    """班別與操作員統計（§11.9 / J16）。

    只統計人工班別（A/B/C/D）。`N`（轉帳作業）排除——實測 204 筆金額恆 0。
    ⚠️ `X`（自助洗衣與電話自動計費 596,194）與 `Y`（洗衣 375,166）是**真實
       收入**，J16 明確指示保留於所有金額統計，因此仍列於本表。
    """
    # ⚠️ 必須 include_memo=True：班別 N 的 204 筆**全部**是 39.轉帳，而 39 是
    #    純記錄科目（J20）預設會被 _ledger_q 濾掉。不放行的話「已排除 N」這個
    #    區塊永遠是空的，使用者根本不知道 N 存在。
    base = _ledger_q(db, start_date=start_date, end_date=end_date, include_memo=True)
    rows = base.filter(JinxuLedgerEntry.is_manual_shift == 1).with_entities(
        JinxuLedgerEntry.shift,
        func.count(JinxuLedgerEntry.id),
        func.sum(JinxuLedgerEntry.amount),
        func.sum(case((JinxuLedgerEntry.is_reversal == 1, 1), else_=0)),
    ).group_by(JinxuLedgerEntry.shift).all()

    excluded = base.filter(JinxuLedgerEntry.is_manual_shift == 0).with_entities(
        JinxuLedgerEntry.shift,
        func.count(JinxuLedgerEntry.id),
        func.sum(JinxuLedgerEntry.amount),
    ).group_by(JinxuLedgerEntry.shift).all()

    return {
        "shifts": [{
            "shift": r[0], "count": r[1], "amount": _f(r[2]),
            "reversal_count": int(r[3] or 0),
        } for r in sorted(rows, key=lambda x: x[0] or "")],
        "excluded_shifts": [{
            "shift": r[0], "count": r[1], "amount": _f(r[2]),
        } for r in excluded],
        "note": "已排除系統作業班別 N（轉帳）。X／Y 為自動計費但屬真實收入，仍列入。",
    }


# ══════════════════════════════════════════════════════════════════════════════
#  付款方式分析（主軸二）
# ══════════════════════════════════════════════════════════════════════════════

def payment_summary(db: Session, *, start_date: str = "", end_date: str = "", **kw) -> dict:
    """各付款方式金額與佔比。抵充側金額為負，一律取絕對值呈現（§11.5）。

    ⚠️ 信用卡手續費不在 FCR02 內，**無法計算淨收**（§19.2 Q5）。
       前端只能呈現總額，不可標示為「實收」。
    """
    base = _ledger_q(db, start_date=start_date, end_date=end_date,
                     subject_side=SIDE_SETTLEMENT, **kw)
    rows = base.with_entities(
        JinxuLedgerEntry.subject_code,
        func.min(JinxuLedgerEntry.subject_name),
        func.count(JinxuLedgerEntry.id),
        func.sum(JinxuLedgerEntry.amount),
    ).group_by(JinxuLedgerEntry.subject_code).all()

    detail = [{
        "subject_code": r[0], "subject_name": r[1] or "",
        "count": r[2], "amount": abs(_f(r[3])),
    } for r in rows]
    total = sum(d["amount"] for d in detail)
    for d in detail:
        d["share_pct"] = _pct(d["amount"], total)
    detail.sort(key=lambda x: -x["amount"])

    macro = []
    for key, (label, codes) in PAYMENT_MACRO.items():
        amt = sum(d["amount"] for d in detail if d["subject_code"] in codes)
        cnt = sum(d["count"] for d in detail if d["subject_code"] in codes)
        if cnt:
            macro.append({"key": key, "label": label, "count": cnt,
                          "amount": amt, "share_pct": _pct(amt, total)})
    macro.sort(key=lambda x: -x["amount"])

    return {
        "total": total, "by_subject": detail, "by_macro": macro,
        "note": "金額為刷卡／收款總額，不含手續費，非淨收",
    }


def payment_monthly(db: Session, *, start_date: str = "", end_date: str = "", **kw) -> dict:
    base = _ledger_q(db, start_date=start_date, end_date=end_date,
                     subject_side=SIDE_SETTLEMENT, **kw)
    month = func.substr(JinxuLedgerEntry.business_date, 1, 7)
    rows = base.with_entities(
        month, JinxuLedgerEntry.subject_group,
        func.sum(JinxuLedgerEntry.amount), func.count(JinxuLedgerEntry.id),
    ).group_by(month, JinxuLedgerEntry.subject_group).all()

    by_month: dict[str, dict] = {}
    for m, g, amt, c in rows:
        d = by_month.setdefault(m, {"month": m, "total": 0.0, "groups": {}})
        d["groups"][g] = {"label": GROUP_LABELS.get(g, g),
                          "amount": abs(_f(amt)), "count": c}
        d["total"] += abs(_f(amt))
    return {"items": [by_month[k] for k in sorted(by_month)]}


# ══════════════════════════════════════════════════════════════════════════════
#  預收訂金追蹤（主軸三，J21：只做總額層級）
# ══════════════════════════════════════════════════════════════════════════════

def deposit_summary(db: Session, *, start_date: str = "", end_date: str = "") -> dict:
    """預收訂金發生／沖銷／未沖餘額。

    ⚠️ 「未沖餘額」在只有部分期間資料時**不可信**——沖掉的訂金有一部分是
       本期之前收的。前端必須顯示資料起始日警告（§11.8）。
    ⚠️ J21：只做總額層級，不做 64A↔81A 逐筆配對。
    """
    base = _ledger_q(db, start_date=start_date, end_date=end_date)
    inflow = base.filter(
        JinxuLedgerEntry.subject_code.in_(DEPOSIT_IN_CODES)
    ).with_entities(
        func.count(JinxuLedgerEntry.id), func.sum(JinxuLedgerEntry.amount)
    ).one()
    outflow = base.filter(
        JinxuLedgerEntry.subject_code.in_(DEPOSIT_OUT_CODES)
    ).with_entities(
        func.count(JinxuLedgerEntry.id), func.sum(JinxuLedgerEntry.amount)
    ).one()

    cov = data_coverage(db)
    inflow_amt = _f(inflow[1])
    outflow_amt = abs(_f(outflow[1]))
    return {
        "inflow_count": inflow[0] or 0,
        "inflow_amount": inflow_amt,
        "outflow_count": outflow[0] or 0,
        "outflow_amount": outflow_amt,
        "net_balance": round(inflow_amt - outflow_amt, 2),
        "data_start_date": cov["ledger_start"],
        # 前端必須把這句原樣顯示為 Alert
        "warning": (
            f"未沖餘額需完整歷史資料才準確，目前資料起始於 {cov['ledger_start']}；"
            "本期沖銷的訂金可能有一部分是此日期之前收取的。"
        ),
        "note": "僅總額層級比較，未做 64A↔81A 逐筆配對",
    }


def deposit_monthly(db: Session, *, start_date: str = "", end_date: str = "") -> dict:
    base = _ledger_q(db, start_date=start_date, end_date=end_date)
    month = func.substr(JinxuLedgerEntry.business_date, 1, 7)
    rows = base.filter(
        JinxuLedgerEntry.subject_code.in_(tuple(DEPOSIT_IN_CODES) + tuple(DEPOSIT_OUT_CODES))
    ).with_entities(
        month,
        func.sum(case((JinxuLedgerEntry.subject_code.in_(DEPOSIT_IN_CODES),
                       JinxuLedgerEntry.amount), else_=0)),
        func.sum(case((JinxuLedgerEntry.subject_code.in_(DEPOSIT_OUT_CODES),
                       JinxuLedgerEntry.amount), else_=0)),
    ).group_by(month).order_by(month).all()

    items = []
    running = 0.0
    for m, i_amt, o_amt in rows:
        inflow, outflow = _f(i_amt), abs(_f(o_amt))
        running += inflow - outflow
        items.append({"month": m, "inflow": inflow, "outflow": outflow,
                      "net": round(inflow - outflow, 2),
                      "cumulative_balance": round(running, 2)})
    return {"items": items}


# ══════════════════════════════════════════════════════════════════════════════
#  訂房與通路分析（主軸四）
# ══════════════════════════════════════════════════════════════════════════════

_RESV_AGG = (
    func.count(JinxuReservation.id),
    func.sum(JinxuReservation.total_room_nights),
    func.sum(JinxuReservation.total_quoted_amount),
    func.sum(JinxuReservation.nights),
    func.sum(JinxuReservation.billable_nights),
)


def _resv_metrics(row) -> dict:
    """加權 ADR = Σ 報價總額 / Σ 房晚數。**不可逐筆算 ADR 再平均**。

    J27：`nights`（日期差，Day Use=0）與 `billable_nights`（max(nights,1)）
    兩種平均晚數都回傳，由前端切換；服務層不預設任何一種。
    """
    cnt, rn, amt, nights, bnights = row
    cnt = cnt or 0
    rn = int(rn or 0)
    amt = _f(amt)
    return {
        "reservation_count": cnt,
        "room_nights": rn,
        "quoted_amount": amt,
        "adr": round(amt / rn, 2) if rn else 0.0,
        "avg_nights": round(_f(nights) / cnt, 2) if cnt else 0.0,
        "avg_billable_nights": round(_f(bnights) / cnt, 2) if cnt else 0.0,
    }


def resv_summary(db: Session, *, start_date: str = "", end_date: str = "",
                 date_basis: str = "arrival", **kw) -> dict:
    """訂房 KPI。取消率另外用含取消的母體算。"""
    active = _resv_q(db, start_date=start_date, end_date=end_date,
                     date_basis=date_basis, **kw)
    m = _resv_metrics(active.with_entities(*_RESV_AGG).one())

    allq = _resv_q(db, start_date=start_date, end_date=end_date,
                   date_basis=date_basis, include_cancelled=True, **kw)
    total_cnt, cancelled_cnt, noshow_cnt = allq.with_entities(
        func.count(JinxuReservation.id),
        func.sum(JinxuReservation.is_cancelled),
        func.sum(JinxuReservation.is_no_show),
    ).one()

    m.update({
        "total_count_incl_cancelled": total_cnt or 0,
        "cancelled_count": int(cancelled_cnt or 0),
        "cancel_rate_by_count": _pct(int(cancelled_cnt or 0), total_cnt or 0),
        "no_show_count": int(noshow_cnt or 0),
        "population_note": population_note(False),
        "nights_note": (
            "avg_nights 以日期差計（Day Use = 0）；"
            "avg_billable_nights 以 max(日期差,1) 計（Day Use = 1）"
        ),
    })
    return m


def _resv_group_by(db: Session, col, label_fn=None, **kw) -> dict:
    q = _resv_q(db, **kw)
    rows = q.with_entities(col, *_RESV_AGG).group_by(col).all()

    total_rn = sum(int(r[2] or 0) for r in rows)
    total_amt = sum(_f(r[3]) for r in rows)
    items = []
    for r in rows:
        m = _resv_metrics(r[1:])
        key = r[0] or ""
        m.update({
            "key": key,
            "label": label_fn(key) if label_fn else (key or "（未指定）"),
            "room_nights_share_pct": _pct(m["room_nights"], total_rn),
            "amount_share_pct": _pct(m["quoted_amount"], total_amt),
        })
        items.append(m)
    items.sort(key=lambda x: -x["room_nights"])
    return {
        "total_room_nights": total_rn,
        "total_quoted_amount": total_amt,
        "items": items,
        "population_note": population_note(kw.get("include_cancelled", False)),
    }


def resv_by_channel(db: Session, **kw) -> dict:
    """通路別。J19：**不合併**同一 OTA 的不同付款方式，照原值呈現。"""
    out = _resv_group_by(db, JinxuReservation.company_name, **kw)
    out["note"] = "通路名稱照金旭原值呈現，未合併（如 Expedia 與 Expedia-前台付款 分列）"
    return out


def resv_by_ratecode(db: Session, **kw) -> dict:
    """業務碼別。J18：SiteMinder 視為一個正常 Rate Code，不特別處理。"""
    return _resv_group_by(db, JinxuReservation.rate_code, **kw)


def resv_by_source(db: Session, **kw) -> dict:
    return _resv_group_by(db, JinxuReservation.source_name, **kw)


def resv_by_type(db: Session, **kw) -> dict:
    return _resv_group_by(db, JinxuReservation.resv_type, **kw)


def resv_by_roomtype(db: Session, *, start_date: str = "", end_date: str = "",
                     date_basis: str = "arrival", include_cancelled: bool = False,
                     **kw) -> dict:
    """房型別（資料源為子表 jinxu_reservation_stay）。

    J23：**只顯示代碼**，不顯示中文名、不做分級或分群——房務尚未提供正式
    對照表（§19.2 Q17），自行推斷（如 V 前綴 = 景觀）會讓分析失真。
    """
    sub = _resv_q(db, start_date=start_date, end_date=end_date,
                  date_basis=date_basis, include_cancelled=include_cancelled,
                  **kw).with_entities(JinxuReservation.id).subquery()

    rows = (
        db.query(
            JinxuReservationStay.room_type_code,
            func.count(func.distinct(JinxuReservationStay.reservation_id)),
            func.sum(JinxuReservationStay.room_nights),
            func.sum(JinxuReservationStay.segment_amount),
            func.count(JinxuReservationStay.id),
        )
        .filter(JinxuReservationStay.reservation_id.in_(sub))
        .group_by(JinxuReservationStay.room_type_code)
        .all()
    )

    total_rn = sum(int(r[2] or 0) for r in rows)
    total_amt = sum(_f(r[3]) for r in rows)
    items = []
    for code, resv_cnt, rn, amt, seg_cnt in rows:
        rn = int(rn or 0)
        items.append({
            "room_type_code": code,
            "label": code,      # J23：不提供中文名
            "reservation_count": resv_cnt,
            "segment_count": seg_cnt,
            "room_nights": rn,
            "quoted_amount": _f(amt),
            "adr": round(_f(amt) / rn, 2) if rn else 0.0,
            "room_nights_share_pct": _pct(rn, total_rn),
        })
    items.sort(key=lambda x: -x["room_nights"])
    return {
        "total_room_nights": total_rn,
        "total_quoted_amount": total_amt,
        "items": items,
        "population_note": population_note(include_cancelled),
        "note": "房型僅顯示代碼——房務尚未提供正式中文對照表，不做任何推斷分類",
    }


def resv_monthly(db: Session, *, start_date: str = "", end_date: str = "",
                 date_basis: str = "arrival", **kw) -> dict:
    q = _resv_q(db, start_date=start_date, end_date=end_date,
                date_basis=date_basis, **kw)
    col = (JinxuReservation.departure_date if date_basis == "departure"
           else JinxuReservation.arrival_date)
    month = func.substr(col, 1, 7)
    rows = q.with_entities(month, *_RESV_AGG).group_by(month).order_by(month).all()
    return {
        "date_basis": date_basis,
        "items": [dict(month=r[0], **_resv_metrics(r[1:])) for r in rows],
        "population_note": population_note(False),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  取消分析（主軸五）—— OPERA 的 Departure 做不到的
# ══════════════════════════════════════════════════════════════════════════════

CANCEL_NOTE = (
    "取消率以「到達日期」歸期。本報表無取消日期欄位，"
    "因此無法分析提前多久取消（規格書 §19.2 Q16）。"
)


def cancellation_summary(db: Session, *, start_date: str = "", end_date: str = "",
                         date_basis: str = "arrival", **kw) -> dict:
    """整體取消率（筆數／房晚兩種口徑）與取消損失報價。"""
    q = _resv_q(db, start_date=start_date, end_date=end_date,
                date_basis=date_basis, include_cancelled=True, **kw)
    row = q.with_entities(
        func.count(JinxuReservation.id),
        func.sum(JinxuReservation.is_cancelled),
        func.sum(JinxuReservation.is_no_show),
        func.sum(JinxuReservation.total_room_nights),
        func.sum(case((JinxuReservation.is_cancelled == 1,
                       JinxuReservation.total_room_nights), else_=0)),
        func.sum(case((JinxuReservation.is_cancelled == 1,
                       JinxuReservation.total_quoted_amount), else_=0)),
    ).one()

    total, cancelled, noshow, rn_all, rn_cancel, amt_cancel = row
    total = total or 0
    return {
        "total_count": total,
        "cancelled_count": int(cancelled or 0),
        "cancel_rate_by_count": _pct(int(cancelled or 0), total),
        "total_room_nights": int(rn_all or 0),
        "cancelled_room_nights": int(rn_cancel or 0),
        "cancel_rate_by_room_nights": _pct(int(rn_cancel or 0), int(rn_all or 0)),
        "cancelled_quoted_amount": _f(amt_cancel),
        "no_show_count": int(noshow or 0),
        "no_show_rate": _pct(int(noshow or 0), total),
        "population_note": population_note(True),
        "note": CANCEL_NOTE,
    }


def _cancel_group_by(db: Session, col, **kw) -> dict:
    q = _resv_q(db, include_cancelled=True, **kw)
    rows = q.with_entities(
        col,
        func.count(JinxuReservation.id),
        func.sum(JinxuReservation.is_cancelled),
        func.sum(JinxuReservation.total_room_nights),
        func.sum(case((JinxuReservation.is_cancelled == 1,
                       JinxuReservation.total_room_nights), else_=0)),
        func.sum(case((JinxuReservation.is_cancelled == 1,
                       JinxuReservation.total_quoted_amount), else_=0)),
    ).group_by(col).all()

    items = [{
        "key": r[0] or "",
        "label": r[0] or "（未指定）",
        "total_count": r[1],
        "cancelled_count": int(r[2] or 0),
        "cancel_rate_by_count": _pct(int(r[2] or 0), r[1]),
        "total_room_nights": int(r[3] or 0),
        "cancelled_room_nights": int(r[4] or 0),
        "cancel_rate_by_room_nights": _pct(int(r[4] or 0), int(r[3] or 0)),
        "cancelled_quoted_amount": _f(r[5]),
    } for r in rows]
    items.sort(key=lambda x: -x["cancelled_room_nights"])
    return {"items": items, "population_note": population_note(True), "note": CANCEL_NOTE}


def cancellation_by_channel(db: Session, **kw) -> dict:
    return _cancel_group_by(db, JinxuReservation.company_name, **kw)


def cancellation_by_ratecode(db: Session, **kw) -> dict:
    return _cancel_group_by(db, JinxuReservation.rate_code, **kw)


def cancellation_monthly(db: Session, *, start_date: str = "", end_date: str = "",
                         **kw) -> dict:
    q = _resv_q(db, start_date=start_date, end_date=end_date,
                include_cancelled=True, **kw)
    month = func.substr(JinxuReservation.arrival_date, 1, 7)
    rows = q.with_entities(
        month,
        func.count(JinxuReservation.id),
        func.sum(JinxuReservation.is_cancelled),
        func.sum(JinxuReservation.total_room_nights),
        func.sum(case((JinxuReservation.is_cancelled == 1,
                       JinxuReservation.total_room_nights), else_=0)),
        func.sum(case((JinxuReservation.is_cancelled == 1,
                       JinxuReservation.total_quoted_amount), else_=0)),
    ).group_by(month).order_by(month).all()

    return {
        "items": [{
            "month": r[0],
            "total_count": r[1],
            "cancelled_count": int(r[2] or 0),
            "cancel_rate_by_count": _pct(int(r[2] or 0), r[1]),
            "cancel_rate_by_room_nights": _pct(int(r[4] or 0), int(r[3] or 0)),
            "cancelled_quoted_amount": _f(r[5]),
        } for r in rows],
        "population_note": population_note(True),
        "note": CANCEL_NOTE,
    }


def status_breakdown(db: Session, *, start_date: str = "", end_date: str = "") -> dict:
    """7 種訂房狀態的分布（含 DUMY，供稽核；統計仍不計入）。"""
    q = db.query(JinxuReservation)
    if start_date:
        q = q.filter(JinxuReservation.arrival_date >= start_date)
    if end_date:
        q = q.filter(JinxuReservation.arrival_date <= end_date)
    rows = q.with_entities(
        JinxuReservation.status_code,
        func.count(JinxuReservation.id),
        func.sum(JinxuReservation.total_room_nights),
    ).group_by(JinxuReservation.status_code).all()
    total = sum(r[1] for r in rows)
    return {"items": sorted([{
        "status_code": r[0],
        "label": STATUS_LABELS.get(r[0], r[0]),
        "count": r[1],
        "share_pct": _pct(r[1], total),
        "room_nights": int(r[2] or 0),
        "excluded_from_stats": r[0].startswith("DUMY"),
    } for r in rows], key=lambda x: -x["count"])}


# ══════════════════════════════════════════════════════════════════════════════
#  訂價 vs 實收（兩檔交叉分析，§11.7）
# ══════════════════════════════════════════════════════════════════════════════

# 「實際房租」採用的科目：01.房租 + 01A.客房加價。
# 刻意**不含** 04.加床費——RV_detail 的住宿資料房價是「每房每晚房價」，
# 加床是另計項目，併進來會讓落差失真。
ROOM_REVENUE_PREFIX = "01"
ROOM_REVENUE_CODES_NOTE = "實收房租＝01.房租 ＋ 01A.客房加價（不含 04.加床費）"


def rate_gap(db: Session, *, start_date: str = "", end_date: str = "",
             gap_alert_pct: float = 10.0, limit: int = 200, **kw) -> dict:
    """訂房報價 vs FCR02 實際房租。

    ⚠️ 落差是**特徵不是錯誤**（延住／升等／加床／現場改價）。實測整體
       -3.05%、91.9% 逐筆完全相符。前端措辭必須中性（「差異」不是「異常」）。
    ⚠️ 只有兩個來源都匯入時才可用；否則回 available=False，前端整區隱藏，
       **不可顯示空圖表或 0**。
    """
    cov = data_coverage(db)
    if not cov["ledger_start"] or not cov["resv_start"]:
        return {
            "available": False,
            "reason": "需同時匯入「客帳帳目明細表」與「訂房狀況表」才能比對訂價與實收",
        }

    actual_sub = (
        db.query(
            JinxuLedgerEntry.booking_no.label("bno"),
            func.sum(JinxuLedgerEntry.amount).label("actual"),
        )
        .filter(JinxuLedgerEntry.subject_code.like(f"{ROOM_REVENUE_PREFIX}%"))
        .group_by(JinxuLedgerEntry.booking_no)
        .subquery()
    )

    q = (
        _resv_q(db, start_date=start_date, end_date=end_date, **kw)
        .join(actual_sub, actual_sub.c.bno == JinxuReservation.booking_no)
    )

    agg = q.with_entities(
        func.count(JinxuReservation.id),
        func.sum(JinxuReservation.total_quoted_amount),
        func.sum(actual_sub.c.actual),
    ).one()
    cnt, quoted, actual = agg[0] or 0, _f(agg[1]), _f(agg[2])

    rows = q.with_entities(
        JinxuReservation.booking_no,
        JinxuReservation.status_code,
        JinxuReservation.arrival_date,
        JinxuReservation.departure_date,
        JinxuReservation.company_name,
        JinxuReservation.room_type_codes,
        JinxuReservation.total_room_nights,
        JinxuReservation.total_quoted_amount,
        actual_sub.c.actual,
    ).all()

    exact = 0
    items = []
    for r in rows:
        qv, av = _f(r[7]), _f(r[8])
        gap = round(av - qv, 2)
        if abs(gap) < 0.01:
            exact += 1
        items.append({
            "booking_no": r[0], "status_code": r[1],
            "arrival_date": r[2], "departure_date": r[3],
            "company_name": r[4], "room_type_codes": r[5],
            "room_nights": int(r[6] or 0),
            "quoted_amount": qv, "actual_amount": av,
            "gap": gap, "gap_pct": _pct(gap, qv) if qv else 0.0,
        })

    flagged = [i for i in items if abs(i["gap_pct"]) > gap_alert_pct]
    flagged.sort(key=lambda x: -abs(x["gap"]))

    return {
        "available": True,
        "matched_count": cnt,
        "quoted_total": quoted,
        "actual_total": actual,
        "gap_total": round(actual - quoted, 2),
        "gap_pct": _pct(actual - quoted, quoted),
        "exact_match_count": exact,
        "exact_match_pct": _pct(exact, cnt),
        "flagged_count": len(flagged),
        "flagged": flagged[:limit],
        "subject_scope": ROOM_REVENUE_CODES_NOTE,
        "gap_definition": "gap = 實收 − 訂價（正值代表實收較高）",
        "note": (
            "「差異」來自延住、升等加價、加床、現場改價等正常營業行為，"
            "非資料錯誤。訂房記的是當下報價，帳目記的是實際過帳。"
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  回訪分析（J12 / J13）
# ══════════════════════════════════════════════════════════════════════════════

REPEAT_NOTE = (
    "回訪判定：登記名稱去頭尾空白後**字串完全一致**才視為同一人"
    "（業主指定，未做大小寫或姓名順序正規化）。"
    "已排除 OTHERS／公司名／訂房壓房等非人名資料。"
    "同一人若在金旭以不同寫法登記會被算成兩人，數字為估計值。"
)


def repeat_guests(db: Session, *, start_date: str = "", end_date: str = "",
                  min_visits: int = 2, limit: int = 200, **kw) -> dict:
    """回訪住客分析。

    ⚠️ 母體必須排除 `guest_is_placeholder=1`（J14）——否則 37 筆 `OTHERS`
       會被算成同一位回訪 37 次的常客，直接登上排行榜第一。
    """
    q = _resv_q(db, start_date=start_date, end_date=end_date, **kw).filter(
        JinxuReservation.guest_is_placeholder == 0,
        JinxuReservation.guest_identity_hash != "",
    )

    rows = q.with_entities(
        JinxuReservation.guest_identity_hash,
        func.min(JinxuReservation.guest_name_masked),
        func.count(JinxuReservation.id),
        func.sum(JinxuReservation.total_room_nights),
        func.sum(JinxuReservation.total_quoted_amount),
        func.min(JinxuReservation.arrival_date),
        func.max(JinxuReservation.arrival_date),
        func.count(func.distinct(JinxuReservation.company_name)),
    ).group_by(JinxuReservation.guest_identity_hash).all()

    total_guests = len(rows)
    repeats = [r for r in rows if r[2] >= min_visits]
    repeat_stays = sum(r[2] for r in repeats)
    total_stays = sum(r[2] for r in rows)

    items = [{
        # ⚠️ 只回傳遮罩後姓名，identity_hash 不外流（避免成為可比對的識別碼）
        "guest_name_masked": r[1] or "",
        "visit_count": r[2],
        "room_nights": int(r[3] or 0),
        "quoted_amount": _f(r[4]),
        "first_arrival": r[5],
        "last_arrival": r[6],
        "channel_count": r[7],
    } for r in repeats]
    items.sort(key=lambda x: (-x["visit_count"], -x["quoted_amount"]))

    return {
        "unique_guests": total_guests,
        "repeat_guests": len(repeats),
        "repeat_guest_rate": _pct(len(repeats), total_guests),
        "total_stays": total_stays,
        "repeat_stays": repeat_stays,
        "repeat_stay_rate": _pct(repeat_stays, total_stays),
        "min_visits": min_visits,
        "items": items[:limit],
        "population_note": population_note(False),
        "note": REPEAT_NOTE,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  明細列表與 Drawer
# ══════════════════════════════════════════════════════════════════════════════

def _ledger_dict(e: JinxuLedgerEntry) -> dict:
    """⚠️ J17：**絕不可加入 remark**。"""
    return {
        "id": e.id,
        "create_seq": e.create_seq,
        "business_date": e.business_date,
        "created_at_text": e.created_at_text,
        "shift": e.shift,
        "operator_id": e.operator_id,
        "room_no": e.room_no,
        "room_kind": e.room_kind,
        "folio_name": e.folio_name,
        "folio_seq": e.folio_seq,
        "folio_type": e.folio_type,
        "subject_code": e.subject_code,
        "subject_name": e.subject_name,
        "subject_side": e.subject_side,
        "subject_group": e.subject_group,
        "subject_group_label": GROUP_LABELS.get(e.subject_group, e.subject_group),
        "amount": _f(e.amount),
        "is_reversal": e.is_reversal,
        "is_memo_only": e.is_memo_only,
        "booking_no": e.booking_no,
        "document_no": e.document_no,
        "ar_code": e.ar_code,
        "transfer_no": e.transfer_no,
    }


def ledger_entries(db: Session, *, page: int = 1, page_size: int = 50,
                   start_date: str = "", end_date: str = "", **kw) -> dict:
    q = _ledger_q(db, start_date=start_date, end_date=end_date, **kw)
    total = q.count()
    rows = (
        q.order_by(JinxuLedgerEntry.business_date.desc(),
                   JinxuLedgerEntry.create_seq.desc())
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    return {"total": total, "page": page, "page_size": page_size,
            "items": [_ledger_dict(e) for e in rows]}


def ledger_entry_detail(db: Session, entry_id: int) -> dict | None:
    """Drawer 用。含同訂房的其他分錄，供追溯。"""
    e = db.get(JinxuLedgerEntry, entry_id)
    if not e:
        return None
    out = _ledger_dict(e)
    if e.booking_no:
        siblings = (
            db.query(JinxuLedgerEntry)
            .filter(JinxuLedgerEntry.booking_no == e.booking_no,
                    JinxuLedgerEntry.id != e.id)
            .order_by(JinxuLedgerEntry.business_date)
            .limit(100).all()
        )
        out["related_entries"] = [_ledger_dict(s) for s in siblings]
        resv = (
            db.query(JinxuReservation)
            .filter(JinxuReservation.booking_no == e.booking_no).first()
        )
        out["reservation"] = None if not resv else _resv_dict(resv)
    return out


def _resv_dict(r: JinxuReservation) -> dict:
    return {
        "id": r.id,
        "booking_no": r.booking_no,
        "status_code": r.status_code,
        "status_label": STATUS_LABELS.get(r.status_code, r.status_code),
        "is_cancelled": r.is_cancelled,
        "is_dummy": r.is_dummy,
        "is_no_show": r.is_no_show,
        "arrival_date": r.arrival_date,
        "departure_date": r.departure_date,
        "nights": r.nights,
        "billable_nights": r.billable_nights,
        "is_day_use": r.is_day_use,
        "guest_name_masked": r.guest_name_masked,
        "guest_is_placeholder": r.guest_is_placeholder,
        "company_name": r.company_name,
        "rate_code": r.rate_code,
        "source_name": r.source_name,
        "resv_type": r.resv_type,
        "is_group": r.is_group,
        "stay_segment_count": r.stay_segment_count,
        "total_room_nights": r.total_room_nights,
        "total_quoted_amount": _f(r.total_quoted_amount),
        "room_type_codes": r.room_type_codes,
        "has_nights_mismatch": r.has_nights_mismatch,
    }


def resv_list(db: Session, *, page: int = 1, page_size: int = 50, **kw) -> dict:
    q = _resv_q(db, **kw)
    total = q.count()
    rows = (
        q.order_by(JinxuReservation.arrival_date.desc(),
                   JinxuReservation.booking_no.desc())
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    return {
        "total": total, "page": page, "page_size": page_size,
        "items": [_resv_dict(r) for r in rows],
        "population_note": population_note(kw.get("include_cancelled", False)),
    }


def resv_detail(db: Session, resv_id: int) -> dict | None:
    """Drawer 用：訂房 + 住宿明細段 + 關聯帳務分錄（§13.7）。"""
    r = db.get(JinxuReservation, resv_id)
    if not r:
        return None
    out = _resv_dict(r)

    segs = (
        db.query(JinxuReservationStay)
        .filter(JinxuReservationStay.reservation_id == r.id)
        .order_by(JinxuReservationStay.seq_no).all()
    )
    out["segments"] = [{
        "seq_no": s.seq_no,
        "room_type_code": s.room_type_code,
        "rooms": s.rooms,
        "nights": s.nights,
        "amount_per_night": _f(s.amount_per_night),
        "unit_rate": _f(s.unit_rate),
        "room_nights": s.room_nights,
        "segment_amount": _f(s.segment_amount),
        "has_n_suffix": s.has_n_suffix,
        "raw_segment": s.raw_segment,
    } for s in segs]

    entries = (
        db.query(JinxuLedgerEntry)
        .filter(JinxuLedgerEntry.booking_no == r.booking_no)
        .order_by(JinxuLedgerEntry.business_date, JinxuLedgerEntry.create_seq)
        .limit(300).all()
    )
    out["ledger_entries"] = [_ledger_dict(e) for e in entries]
    out["ledger_available"] = bool(entries)

    actual = sum(
        _f(e.amount) for e in entries
        if e.subject_code.startswith(ROOM_REVENUE_PREFIX)
    )
    quoted = _f(r.total_quoted_amount)
    out["rate_comparison"] = {
        "quoted_amount": quoted,
        "actual_room_revenue": round(actual, 2),
        "gap": round(actual - quoted, 2),
        "gap_pct": _pct(actual - quoted, quoted) if quoted else 0.0,
    } if entries else None
    return out
