"""
OPERA 房價預測 — 可解釋的乘法分解模型 + 樸素基準 + 回測

評估文件：docs/EVAL_opera_rate_forecasting.md §3.2、§3.3、§6

模型
────
    預測 ADR   = 基準 ADR   × 星期係數 × 月份係數 × 年成長^Δ年 × 事件係數
    預測住房率 = 基準住房率 × 星期係數 × 月份係數 × 年成長^Δ年 × 事件係數（上限 100%）
    預測房晚   = 預測住房率 × 近期可售房晚中位數
    預測營收   = 預測 ADR × 預測房晚

為什麼不是機器學習（評估文件 §3.2）
  1. **可解釋**：畫面能攤開「基準 2,479 × 週六 1.22 × 8 月 1.05 × 成長 1.09」，
     收益經理看得懂、可以反駁、可以人工覆寫。黑箱給不出理由就沒人敢用。
  2. **資料量夠**：958 天估 7 個星期 + 12 個月係數綽綽有餘；上 XGBoost 反而過擬合。
  3. 研究顯示小型獨立飯店用傳統方法表現不輸複雜模型。

錨點設計（很重要，不可改成「用全期平均當基準」）
  基準值取**最近 365 天**的加權值，而不是全期平均。理由是全期平均含較早的低價年份，
  若再乘上年成長係數會**重複計算成長**。錨定在資料最後一天，成長就只往前推一次。

誠實原則
  * 一律同時算樸素基準（去年同期同星期），兩者的 MAPE 並列顯示。
    分解模型若沒有明顯勝出，就不該取代規則。
  * 一律輸出預測區間（殘差的 10%／90% 分位數），不給單一數字。
  * 回測**嚴格切分訓練期與測試期**，用測試期之前的資料重新估係數，不可資料洩漏。
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.opera_forecast import (
    COEF_ANCHOR,
    COEF_BASELINE,
    COEF_DOW,
    COEF_EDITABLE_KINDS,
    COEF_GROWTH,
    COEF_INTERVAL,
    COEF_MONTH,
    EVENT_SOURCE_LEARNED,
    METRIC_ADR,
    METRIC_OCC,
    MIN_COEF_SAMPLE_DAYS,
    MIN_EVENT_SAMPLES,
    MODEL_DECOMP,
    MODEL_LABELS,
    MODEL_NAIVE,
    MODEL_VERSION,
    OperaEvent,
    OperaForecastCoefficient,
    OperaForecastDaily,
    OperaForecastRun,
)
from app.models.opera_revenue import OperaRevenueDaily, RECORD_TYPE_HISTORY
from app.services import opera_analysis_service as AS
from app.services import opera_period_service as PS

SOURCE_NOTE = "資料來源：History and Forecast（實績）＋事件月曆"

# 錨點與成長率的取樣窗（364 = 52 週，星期分布完全對齊，不會偏向某幾天）
ANCHOR_WINDOW_DAYS = 364
# 可售房晚取近 N 天的中位數（用中位數而非平均，避免整修期把數字拉低）
AVAILABLE_WINDOW_DAYS = 90
# 預測區間的分位數
INTERVAL_LOW = 0.10
INTERVAL_HIGH = 0.90
# 年成長率的合理範圍（超出多半是資料問題而非真的成長，夾住避免外推爆炸）
GROWTH_MIN, GROWTH_MAX = 0.80, 1.30
# 單一係數的合理範圍
FACTOR_MIN, FACTOR_MAX = 0.30, 3.00
# 預測期最長天數（避免使用者一次要 10 年，算出一堆沒意義的外推）
MAX_HORIZON_DAYS = 731


# ══════════════════════════════════════════════════════════════════════════════
# 資料載入與離群值處理
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class DayFact:
    business_date: str
    weekday: int
    month: int
    revenue: float
    sold_rooms: int
    available_rooms: int

    @property
    def adr(self) -> float:
        return self.revenue / self.sold_rooms if self.sold_rooms else 0.0

    @property
    def occupancy(self) -> float:
        return self.sold_rooms / self.available_rooms if self.available_rooms else 0.0


def load_facts(db: Session, start: str, end: str, property_code: str = "") -> list[DayFact]:
    """載入可用於估算的歷史日（已排除離群值，評估文件 §9.3）。

    排除條件：
      * 營收為負（沖銷／調整，實測 2026-02-23 ADR −1,921）
      * 售出房晚 = 0（ADR 無法計算）
      * 可售房晚 = 0（住房率無法計算）
    這些日子**不是壞資料**，只是不能拿來估係數，畫面上仍看得到。
    """
    q = (
        db.query(OperaRevenueDaily)
        .filter(
            OperaRevenueDaily.is_current == 1,
            OperaRevenueDaily.record_type == RECORD_TYPE_HISTORY,
            OperaRevenueDaily.business_date >= start,
            OperaRevenueDaily.business_date <= end,
        )
    )
    if property_code:
        q = q.filter(OperaRevenueDaily.property_code == property_code)

    facts: list[DayFact] = []
    for r in q.order_by(OperaRevenueDaily.business_date).all():
        revenue = float(r.revenue)
        if revenue < 0 or r.sold_rooms <= 0 or r.available_rooms <= 0:
            continue
        facts.append(DayFact(
            business_date=r.business_date,
            weekday=AS._weekday_index(r.business_date),
            month=int(r.business_date[5:7]),
            revenue=revenue,
            sold_rooms=r.sold_rooms,
            available_rooms=r.available_rooms,
        ))
    return facts


def load_excluded(db: Session, start: str, end: str, property_code: str = "") -> list[dict]:
    """被排除的日子（畫面要能交代「為什麼 958 天只用了 N 天」）。"""
    q = (
        db.query(OperaRevenueDaily)
        .filter(
            OperaRevenueDaily.is_current == 1,
            OperaRevenueDaily.record_type == RECORD_TYPE_HISTORY,
            OperaRevenueDaily.business_date >= start,
            OperaRevenueDaily.business_date <= end,
        )
    )
    if property_code:
        q = q.filter(OperaRevenueDaily.property_code == property_code)

    out: list[dict] = []
    for r in q.order_by(OperaRevenueDaily.business_date).all():
        revenue = float(r.revenue)
        reasons = []
        if revenue < 0:
            reasons.append("負營收")
        if r.sold_rooms <= 0:
            reasons.append("無售出房晚")
        if r.available_rooms <= 0:
            reasons.append("無可售房晚")
        if reasons:
            out.append({
                "business_date": r.business_date,
                "revenue":       round(revenue, 2),
                "sold_rooms":    r.sold_rooms,
                "available_rooms": r.available_rooms,
                "reasons":       reasons,
            })
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 係數估算
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Coefficients:
    """一組完整的模型參數。可以是資料庫存的，也可以是回測時臨時算的。"""

    anchor_date: str = ""
    baseline_adr: float = 0.0
    baseline_occ: float = 0.0
    growth_adr: float = 1.0
    growth_occ: float = 1.0
    available_rooms: float = 0.0

    dow_adr: dict[int, float] = field(default_factory=dict)
    dow_occ: dict[int, float] = field(default_factory=dict)
    month_adr: dict[int, float] = field(default_factory=dict)
    month_occ: dict[int, float] = field(default_factory=dict)

    dow_days: dict[int, int] = field(default_factory=dict)
    month_days: dict[int, int] = field(default_factory=dict)

    adr_p10: float = 0.85
    adr_p90: float = 1.15
    occ_p10: float = 0.70
    occ_p90: float = 1.30

    fit_start: str = ""
    fit_end: str = ""
    fit_days: int = 0
    is_usable: bool = False
    warnings: list[str] = field(default_factory=list)

    def dow_factor(self, wd: int, metric: str) -> float:
        src = self.dow_adr if metric == METRIC_ADR else self.dow_occ
        return src.get(wd, 1.0)

    def month_factor(self, m: int, metric: str) -> float:
        src = self.month_adr if metric == METRIC_ADR else self.month_occ
        return src.get(m, 1.0)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _weighted_adr(facts: list[DayFact]) -> float:
    sold = sum(f.sold_rooms for f in facts)
    return sum(f.revenue for f in facts) / sold if sold else 0.0


def _weighted_occ(facts: list[DayFact]) -> float:
    avail = sum(f.available_rooms for f in facts)
    return sum(f.sold_rooms for f in facts) / avail if avail else 0.0


def fit_coefficients(db: Session, property_code: str = "",
                     fit_end: str | None = None) -> Coefficients:
    """從歷史資料估出一整組係數。

    `fit_end` 用於回測：只准看這個日期（含）以前的資料，避免資料洩漏。
    """
    data_start, data_end = PS.default_range(db, property_code)
    end = fit_end or data_end
    facts = load_facts(db, data_start, end, property_code)

    coef = Coefficients(fit_start=data_start, fit_end=end, fit_days=len(facts))
    if len(facts) < 60:
        coef.warnings.append(f"可用歷史日只有 {len(facts)} 天，不足以估算季節性係數（至少需 60 天）")
        return coef

    anchor = PS.to_date(facts[-1].business_date)
    coef.anchor_date = anchor.isoformat()

    # ── 基準值：錨定最近 364 天（不可用全期平均，會與年成長重複計算）──────
    win_start = (anchor - timedelta(days=ANCHOR_WINDOW_DAYS - 1)).isoformat()
    recent = [f for f in facts if f.business_date >= win_start]
    if len(recent) < 30:
        recent = facts[-min(len(facts), 90):]
        coef.warnings.append("最近一年的資料不足，基準值改用最後 90 天估算")
    coef.baseline_adr = _weighted_adr(recent)
    coef.baseline_occ = _weighted_occ(recent)

    # ── 可售房晚：近 90 天中位數（用中位數避免整修期把數字拉低）────────────
    avail_win = (anchor - timedelta(days=AVAILABLE_WINDOW_DAYS - 1)).isoformat()
    avail_vals = [f.available_rooms for f in facts if f.business_date >= avail_win]
    coef.available_rooms = float(statistics.median(avail_vals)) if avail_vals else 0.0

    # ── 年成長：最近 364 天 vs 前一個 364 天（同樣長度、同樣星期分布）────────
    prev_start = (anchor - timedelta(days=ANCHOR_WINDOW_DAYS * 2 - 1)).isoformat()
    prev_end = (anchor - timedelta(days=ANCHOR_WINDOW_DAYS)).isoformat()
    prev = [f for f in facts if prev_start <= f.business_date <= prev_end]
    if len(prev) >= 60 and coef.baseline_adr:
        prev_adr = _weighted_adr(prev)
        prev_occ = _weighted_occ(prev)
        coef.growth_adr = _clamp(coef.baseline_adr / prev_adr, GROWTH_MIN, GROWTH_MAX) if prev_adr else 1.0
        coef.growth_occ = _clamp(coef.baseline_occ / prev_occ, GROWTH_MIN, GROWTH_MAX) if prev_occ else 1.0
    else:
        coef.warnings.append("去年同期資料不足，年成長係數固定為 1.00（不做成長外推）")

    # ── 星期係數：加權比值 ÷ 全期基準 ─────────────────────────────────────
    overall_adr = _weighted_adr(facts)
    overall_occ = _weighted_occ(facts)

    dow_groups: dict[int, list[DayFact]] = defaultdict(list)
    for f in facts:
        dow_groups[f.weekday].append(f)

    for wd in range(7):
        g = dow_groups.get(wd, [])
        coef.dow_days[wd] = len(g)
        if len(g) < MIN_COEF_SAMPLE_DAYS or not overall_adr or not overall_occ:
            coef.dow_adr[wd] = 1.0
            coef.dow_occ[wd] = 1.0
            if len(g) < MIN_COEF_SAMPLE_DAYS:
                coef.warnings.append(
                    f"{AS.WEEKDAY_LABELS[wd]}只有 {len(g)} 天樣本，係數固定為 1.00"
                )
            continue
        coef.dow_adr[wd] = _clamp(_weighted_adr(g) / overall_adr, FACTOR_MIN, FACTOR_MAX)
        coef.dow_occ[wd] = _clamp(_weighted_occ(g) / overall_occ, FACTOR_MIN, FACTOR_MAX)

    # ── 月份係數：**先扣掉星期效應**再估，否則兩者會重複解釋同一段變異 ──────
    month_groups: dict[int, list[DayFact]] = defaultdict(list)
    for f in facts:
        month_groups[f.month].append(f)

    for m in range(1, 13):
        g = month_groups.get(m, [])
        coef.month_days[m] = len(g)
        if len(g) < MIN_COEF_SAMPLE_DAYS or not overall_adr or not overall_occ:
            coef.month_adr[m] = 1.0
            coef.month_occ[m] = 1.0
            if len(g) < MIN_COEF_SAMPLE_DAYS:
                coef.warnings.append(f"{m} 月只有 {len(g)} 天樣本，係數固定為 1.00")
            continue
        # 以售出房晚為權重的「去星期化」比值
        num_adr = sum(f.revenue / coef.dow_factor(f.weekday, METRIC_ADR) for f in g)
        den_adr = sum(f.sold_rooms for f in g)
        num_occ = sum(f.sold_rooms / coef.dow_factor(f.weekday, METRIC_OCC) for f in g)
        den_occ = sum(f.available_rooms for f in g)
        coef.month_adr[m] = _clamp((num_adr / den_adr) / overall_adr, FACTOR_MIN, FACTOR_MAX) if den_adr else 1.0
        coef.month_occ[m] = _clamp((num_occ / den_occ) / overall_occ, FACTOR_MIN, FACTOR_MAX) if den_occ else 1.0

    coef.is_usable = coef.baseline_adr > 0 and coef.baseline_occ > 0

    # ── 預測區間：用**訓練期自身**的殘差比值分位數（不含事件係數）──────────
    if coef.is_usable:
        adr_ratios, occ_ratios = [], []
        for f in facts:
            p_adr = _raw_predict_adr(coef, f.business_date)
            p_occ = _raw_predict_occ(coef, f.business_date)
            if p_adr > 0:
                adr_ratios.append(f.adr / p_adr)
            if p_occ > 0:
                occ_ratios.append(f.occupancy / p_occ)
        if len(adr_ratios) >= 30:
            coef.adr_p10 = round(_quantile(adr_ratios, INTERVAL_LOW), 4)
            coef.adr_p90 = round(_quantile(adr_ratios, INTERVAL_HIGH), 4)
        if len(occ_ratios) >= 30:
            coef.occ_p10 = round(_quantile(occ_ratios, INTERVAL_LOW), 4)
            coef.occ_p90 = round(_quantile(occ_ratios, INTERVAL_HIGH), 4)

    return coef


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 1.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return s[lo] * (1 - frac) + s[hi] * frac


# ══════════════════════════════════════════════════════════════════════════════
# 單日預測（分解模型）
# ══════════════════════════════════════════════════════════════════════════════

def _years_from_anchor(coef: Coefficients, iso: str) -> float:
    if not coef.anchor_date:
        return 0.0
    return (PS.to_date(iso) - PS.to_date(coef.anchor_date)).days / 365.25


def _raw_predict_adr(coef: Coefficients, iso: str) -> float:
    """不含事件係數的 ADR 預測（估區間與學習事件係數時要用這個當分母）。"""
    wd = AS._weekday_index(iso)
    m = int(iso[5:7])
    growth = coef.growth_adr ** _years_from_anchor(coef, iso)
    return (coef.baseline_adr
            * coef.dow_factor(wd, METRIC_ADR)
            * coef.month_factor(m, METRIC_ADR)
            * growth)


def _raw_predict_occ(coef: Coefficients, iso: str) -> float:
    wd = AS._weekday_index(iso)
    m = int(iso[5:7])
    growth = coef.growth_occ ** _years_from_anchor(coef, iso)
    return (coef.baseline_occ
            * coef.dow_factor(wd, METRIC_OCC)
            * coef.month_factor(m, METRIC_OCC)
            * growth)


def predict_day(coef: Coefficients, iso: str,
                events: list[dict] | None = None) -> dict:
    """單日預測，回傳含完整係數拆解的 dict（畫面必須攤開給使用者看）。"""
    wd = AS._weekday_index(iso)
    m = int(iso[5:7])
    years = _years_from_anchor(coef, iso)
    growth_adr = coef.growth_adr ** years
    growth_occ = coef.growth_occ ** years

    ev = events or []
    ev_adr = 1.0
    ev_occ = 1.0
    for e in ev:
        ev_adr *= float(e.get("effective_adr_index") or 1.0)
        ev_occ *= float(e.get("effective_occ_index") or 1.0)

    adr = (coef.baseline_adr * coef.dow_factor(wd, METRIC_ADR)
           * coef.month_factor(m, METRIC_ADR) * growth_adr * ev_adr)
    occ = (coef.baseline_occ * coef.dow_factor(wd, METRIC_OCC)
           * coef.month_factor(m, METRIC_OCC) * growth_occ * ev_occ)
    occ = max(0.0, min(1.0, occ))       # 住房率不可能超過 100%

    sold = occ * coef.available_rooms
    revenue = adr * sold

    return {
        "business_date":        iso,
        "weekday":              wd,
        "weekday_label":        AS.WEEKDAY_LABELS[wd],
        "predicted_adr":        round(adr, 2),
        "predicted_occupancy":  round(occ, 6),
        "predicted_sold_rooms": round(sold, 1),
        "predicted_revenue":    round(revenue, 2),
        "adr_lower":  round(adr * coef.adr_p10, 2),
        "adr_upper":  round(adr * coef.adr_p90, 2),
        "occ_lower":  round(max(0.0, min(1.0, occ * coef.occ_p10)), 6),
        "occ_upper":  round(max(0.0, min(1.0, occ * coef.occ_p90)), 6),
        "events":     [{"id": e.get("id"), "name": e.get("name"),
                        "category": e.get("category"),
                        "adr_index": float(e.get("effective_adr_index") or 1.0),
                        "occ_index": float(e.get("effective_occ_index") or 1.0),
                        "source_label": e.get("source_label", "")} for e in ev],
        "breakdown": {
            "baseline_adr":  round(coef.baseline_adr, 2),
            "baseline_occ":  round(coef.baseline_occ, 6),
            "dow_adr":       round(coef.dow_factor(wd, METRIC_ADR), 4),
            "dow_occ":       round(coef.dow_factor(wd, METRIC_OCC), 4),
            "month_adr":     round(coef.month_factor(m, METRIC_ADR), 4),
            "month_occ":     round(coef.month_factor(m, METRIC_OCC), 4),
            "growth_adr":    round(growth_adr, 4),
            "growth_occ":    round(growth_occ, 4),
            "event_adr":     round(ev_adr, 4),
            "event_occ":     round(ev_occ, 4),
            "years_from_anchor": round(years, 3),
            "anchor_date":   coef.anchor_date,
            "available_rooms": round(coef.available_rooms, 1),
            "formula_adr": (
                f"{coef.baseline_adr:,.0f} × {coef.dow_factor(wd, METRIC_ADR):.3f}"
                f" × {coef.month_factor(m, METRIC_ADR):.3f} × {growth_adr:.3f}"
                + (f" × {ev_adr:.3f}" if abs(ev_adr - 1.0) > 1e-9 else "")
                + f" = {adr:,.0f}"
            ),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# 樸素基準（去年同期同星期）
# ══════════════════════════════════════════════════════════════════════════════

def _actual_map(db: Session, start: str, end: str, property_code: str) -> dict[str, DayFact]:
    return {f.business_date: f for f in load_facts(db, start, end, property_code)}


def predict_day_naive(actuals: dict[str, DayFact], iso: str,
                      max_lookback: int = 3) -> dict | None:
    """去年同一星期（−364 天）。找不到就再往前推一年，最多 `max_lookback` 次。"""
    d = PS.to_date(iso)
    for k in range(1, max_lookback + 1):
        ref = (d - timedelta(days=364 * k)).isoformat()
        f = actuals.get(ref)
        if f:
            return {
                "business_date":        iso,
                "reference_date":       ref,
                "predicted_adr":        round(f.adr, 2),
                "predicted_occupancy":  round(f.occupancy, 6),
                "predicted_sold_rooms": f.sold_rooms,
                "predicted_revenue":    round(f.revenue, 2),
            }
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 係數存取（資料庫）
# ══════════════════════════════════════════════════════════════════════════════

def _coef_rows(db: Session, property_code: str) -> list[OperaForecastCoefficient]:
    q = db.query(OperaForecastCoefficient)
    if property_code:
        q = q.filter(OperaForecastCoefficient.property_code.in_([property_code, ""]))
    return q.all()


def save_coefficients(db: Session, coef: Coefficients, property_code: str = "",
                      user_id: str | None = None, user_name: str = "") -> int:
    """把估算結果寫回資料庫。**已被人工覆寫的係數不會被蓋掉**，只更新 fitted_value。"""
    payload: list[tuple[str, str, str, float, int]] = [
        (COEF_BASELINE, "-", METRIC_ADR, coef.baseline_adr, coef.fit_days),
        (COEF_BASELINE, "-", METRIC_OCC, coef.baseline_occ, coef.fit_days),
        (COEF_GROWTH,   "-", METRIC_ADR, coef.growth_adr, coef.fit_days),
        (COEF_GROWTH,   "-", METRIC_OCC, coef.growth_occ, coef.fit_days),
    ]
    for wd in range(7):
        payload.append((COEF_DOW, str(wd), METRIC_ADR, coef.dow_adr.get(wd, 1.0), coef.dow_days.get(wd, 0)))
        payload.append((COEF_DOW, str(wd), METRIC_OCC, coef.dow_occ.get(wd, 1.0), coef.dow_days.get(wd, 0)))
    for m in range(1, 13):
        payload.append((COEF_MONTH, str(m), METRIC_ADR, coef.month_adr.get(m, 1.0), coef.month_days.get(m, 0)))
        payload.append((COEF_MONTH, str(m), METRIC_OCC, coef.month_occ.get(m, 1.0), coef.month_days.get(m, 0)))
    payload += [
        (COEF_INTERVAL, "p10", METRIC_ADR, coef.adr_p10, coef.fit_days),
        (COEF_INTERVAL, "p90", METRIC_ADR, coef.adr_p90, coef.fit_days),
        (COEF_INTERVAL, "p10", METRIC_OCC, coef.occ_p10, coef.fit_days),
        (COEF_INTERVAL, "p90", METRIC_OCC, coef.occ_p90, coef.fit_days),
        (COEF_ANCHOR, "available_rooms", METRIC_OCC, coef.available_rooms, coef.fit_days),
    ]

    existing = {
        (r.kind, r.coef_key, r.metric): r
        for r in db.query(OperaForecastCoefficient)
        .filter(OperaForecastCoefficient.property_code == property_code).all()
    }

    written = 0
    for kind, key, metric, value, sample in payload:
        row = existing.get((kind, key, metric))
        if row is None:
            row = OperaForecastCoefficient(
                property_code=property_code, kind=kind, coef_key=key, metric=metric,
            )
            db.add(row)
        row.fitted_value = value
        row.sample_days = sample
        row.fit_start = coef.fit_start
        row.fit_end = coef.fit_end
        row.fitted_at = twnow()
        # 人工覆寫過的係數不動 value，只更新 fitted_value 供對照
        if not row.is_manual:
            row.value = value
            row.updated_by_user_id = user_id
            row.updated_by_name = user_name
        written += 1

    # anchor_date 是字串，另外用 note 存不合適 → 存成 coef_key='date' 的日期序號
    anchor_row = existing.get((COEF_ANCHOR, "date", METRIC_ADR))
    if anchor_row is None:
        anchor_row = OperaForecastCoefficient(
            property_code=property_code, kind=COEF_ANCHOR, coef_key="date", metric=METRIC_ADR,
        )
        db.add(anchor_row)
    anchor_row.value = 0
    anchor_row.fitted_value = 0
    anchor_row.fit_start = coef.fit_start
    anchor_row.fit_end = coef.anchor_date or coef.fit_end
    anchor_row.sample_days = coef.fit_days
    anchor_row.fitted_at = twnow()

    db.flush()
    return written


def load_coefficients(db: Session, property_code: str = "") -> Coefficients | None:
    """讀取資料庫中的係數（含人工覆寫）。沒有估算過就回 None。"""
    rows = _coef_rows(db, property_code)
    if not rows:
        return None
    coef = Coefficients()
    got_baseline = False
    for r in rows:
        v = float(r.value)
        if r.kind == COEF_BASELINE:
            got_baseline = True
            if r.metric == METRIC_ADR:
                coef.baseline_adr = v
            else:
                coef.baseline_occ = v
            coef.fit_start, coef.fit_end, coef.fit_days = r.fit_start, r.fit_end, r.sample_days
        elif r.kind == COEF_GROWTH:
            if r.metric == METRIC_ADR:
                coef.growth_adr = v
            else:
                coef.growth_occ = v
        elif r.kind == COEF_DOW:
            wd = int(r.coef_key)
            (coef.dow_adr if r.metric == METRIC_ADR else coef.dow_occ)[wd] = v
            coef.dow_days[wd] = r.sample_days
        elif r.kind == COEF_MONTH:
            m = int(r.coef_key)
            (coef.month_adr if r.metric == METRIC_ADR else coef.month_occ)[m] = v
            coef.month_days[m] = r.sample_days
        elif r.kind == COEF_INTERVAL:
            if r.metric == METRIC_ADR:
                if r.coef_key == "p10":
                    coef.adr_p10 = v
                else:
                    coef.adr_p90 = v
            else:
                if r.coef_key == "p10":
                    coef.occ_p10 = v
                else:
                    coef.occ_p90 = v
        elif r.kind == COEF_ANCHOR:
            if r.coef_key == "available_rooms":
                coef.available_rooms = v
            elif r.coef_key == "date":
                coef.anchor_date = r.fit_end

    if not got_baseline:
        return None
    coef.is_usable = coef.baseline_adr > 0 and coef.baseline_occ > 0
    return coef


def list_coefficients(db: Session, property_code: str = "") -> dict:
    rows = sorted(
        _coef_rows(db, property_code),
        key=lambda r: (r.kind, r.metric, int(r.coef_key) if r.coef_key.isdigit() else 0, r.coef_key),
    )
    items = []
    for r in rows:
        d = r.to_dict()
        if r.kind == COEF_DOW and r.coef_key.isdigit():
            d["key_label"] = AS.WEEKDAY_LABELS[int(r.coef_key)]
        elif r.kind == COEF_MONTH and r.coef_key.isdigit():
            d["key_label"] = f"{int(r.coef_key)} 月"
        elif r.kind == COEF_BASELINE:
            d["key_label"] = "基準"
        elif r.kind == COEF_GROWTH:
            d["key_label"] = "每年"
        else:
            d["key_label"] = r.coef_key
        items.append(d)
    return {
        "items":          items,
        "editable_kinds": list(COEF_EDITABLE_KINDS),
        "has_fitted":     bool(rows),
        "source_label":   SOURCE_NOTE,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 事件係數學習
# ══════════════════════════════════════════════════════════════════════════════

def _event_key(name: str) -> str:
    return (name or "").strip().lower()


def learn_event_coefficients(db: Session, property_code: str = "") -> dict:
    """從歷史資料學習事件係數（評估文件 §3.4）。

    做法：事件期間的實際值 ÷ **不含事件**的模型預測值。
    以「同名事件」歸類，樣本數 = 有歷史資料的**發生次數**（不是天數）。
    少於 MIN_EVENT_SAMPLES 次就不寫入 learned_*，也不允許切到 learned 來源 ——
    只辦過一次的展覽，係數等於拿單一樣本當結論。
    """
    coef = load_coefficients(db, property_code)
    if not coef or not coef.is_usable:
        return {"ok": False, "reason": "尚未估算係數，請先按「重新估算係數」", "items": []}

    data_start, data_end = PS.default_range(db, property_code)
    actuals = _actual_map(db, data_start, data_end, property_code)

    q = db.query(OperaEvent)
    if property_code:
        q = q.filter(OperaEvent.property_code.in_([property_code, ""]))
    events = q.all()

    groups: dict[str, list[OperaEvent]] = defaultdict(list)
    for e in events:
        groups[_event_key(e.name)].append(e)

    results = []
    for key, group in groups.items():
        occurrences = 0
        num_adr = den_adr = 0.0
        num_occ = den_occ = 0.0
        covered_days = 0

        for e in group:
            days = [
                d for d in PS.iter_dates(e.start_date, e.end_date)
                if d in actuals
            ]
            if not days:
                continue
            occurrences += 1
            covered_days += len(days)
            for d in days:
                f = actuals[d]
                p_adr = _raw_predict_adr(coef, d)
                p_occ = _raw_predict_occ(coef, d)
                if p_adr > 0:
                    # 以售出房晚加權：房賣得多的那天更能代表事件影響
                    num_adr += (f.adr / p_adr) * f.sold_rooms
                    den_adr += f.sold_rooms
                if p_occ > 0:
                    num_occ += (f.occupancy / p_occ) * f.available_rooms
                    den_occ += f.available_rooms

        learned_adr = round(num_adr / den_adr, 4) if den_adr else None
        learned_occ = round(num_occ / den_occ, 4) if den_occ else None
        reliable = occurrences >= MIN_EVENT_SAMPLES

        for e in group:
            e.sample_count = occurrences
            e.learned_adr_index = learned_adr
            e.learned_occ_index = learned_occ
            e.learned_at = twnow() if learned_adr is not None else None
            # 樣本不足時強制退回人工設定，不可讓使用者誤用不可靠的學習值
            if not reliable and e.source == EVENT_SOURCE_LEARNED:
                e.source = "manual"

        results.append({
            "name":          group[0].name,
            "category":      group[0].category,
            "occurrences":   occurrences,
            "covered_days":  covered_days,
            "learned_adr_index": learned_adr,
            "learned_occ_index": learned_occ,
            "is_reliable":   reliable,
            "note": "" if reliable else f"只有 {occurrences} 次歷史紀錄（需 {MIN_EVENT_SAMPLES} 次），維持人工設定",
        })

    db.flush()
    results.sort(key=lambda r: (-r["occurrences"], r["name"]))
    return {
        "ok":            True,
        "items":         results,
        "min_samples":   MIN_EVENT_SAMPLES,
        "reliable_count": sum(1 for r in results if r["is_reliable"]),
        "total":         len(results),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 預測（對外主要入口）
# ══════════════════════════════════════════════════════════════════════════════

def _events_by_date(db: Session, start: str, end: str, property_code: str) -> dict[str, list[dict]]:
    q = db.query(OperaEvent).filter(
        OperaEvent.is_active == 1,
        OperaEvent.start_date <= end,
        OperaEvent.end_date >= start,
    )
    if property_code:
        q = q.filter(OperaEvent.property_code.in_([property_code, ""]))

    out: dict[str, list[dict]] = defaultdict(list)
    for e in q.all():
        d = e.to_dict()
        for iso in PS.iter_dates(max(e.start_date, start), min(e.end_date, end)):
            out[iso].append(d)
    return out


def forecast_range(db: Session, start: str, end: str, property_code: str = "",
                   extra_events: list[dict] | None = None) -> dict:
    """期間預測（評估文件 §3.2、§3.3）。

    `extra_events` 是「假設性事件」：使用者在畫面上臨時填入的事件
    （例如「如果國際電腦展辦在這個週末會怎樣」），**不會寫入資料庫**。
    """
    s, e = PS.to_date(start), PS.to_date(end)
    if s > e:
        s, e = e, s
    horizon = (e - s).days + 1
    if horizon > MAX_HORIZON_DAYS:
        raise ValueError(f"預測期間最長 {MAX_HORIZON_DAYS} 天（約兩年），目前為 {horizon} 天。"
                         "再往外推的數字已無參考價值。")

    coef = load_coefficients(db, property_code)
    if not coef or not coef.is_usable:
        return {
            "ok": False,
            "reason": "尚未估算模型係數。請先到本頁按「重新估算係數」。",
            "items": [],
        }

    data_start, data_end = PS.default_range(db, property_code)
    actuals = _actual_map(db, data_start, data_end, property_code)
    ev_map = _events_by_date(db, s.isoformat(), e.isoformat(), property_code)

    # 假設性事件：只作用在使用者指定的區間內
    for ex in (extra_events or []):
        ex_start = max(ex.get("start_date", ""), s.isoformat())
        ex_end = min(ex.get("end_date", ""), e.isoformat())
        if not ex_start or not ex_end or ex_start > ex_end:
            continue
        payload = {
            "id": None,
            "name": ex.get("name") or "假設事件",
            "category": ex.get("category") or "其他",
            "effective_adr_index": float(ex.get("adr_index") or 1.0),
            "effective_occ_index": float(ex.get("occ_index") or 1.0),
            "source_label": "假設情境（未存檔）",
        }
        for iso in PS.iter_dates(ex_start, ex_end):
            ev_map[iso].append(payload)

    items: list[dict] = []
    for iso in PS.iter_dates(s.isoformat(), e.isoformat()):
        row = predict_day(coef, iso, ev_map.get(iso))
        naive = predict_day_naive(actuals, iso)
        row["naive"] = naive
        actual = actuals.get(iso)
        row["actual"] = {
            "adr":        round(actual.adr, 2),
            "occupancy":  round(actual.occupancy, 6),
            "revenue":    round(actual.revenue, 2),
            "sold_rooms": actual.sold_rooms,
        } if actual else None
        row["is_history"] = actual is not None
        items.append(row)

    # ── 期間彙總（⚠️ 加權，不是把每日 ADR 平均）────────────────────────────
    total_sold = sum(i["predicted_sold_rooms"] for i in items)
    total_revenue = sum(i["predicted_revenue"] for i in items)
    total_available = coef.available_rooms * len(items)
    summary = {
        "days":            len(items),
        "predicted_revenue":  round(total_revenue, 2),
        "predicted_sold_rooms": round(total_sold, 1),
        "available_rooms": round(total_available, 1),
        "predicted_adr":   round(total_revenue / total_sold, 2) if total_sold else 0.0,
        "predicted_occupancy": round(total_sold / total_available, 6) if total_available else 0.0,
        "predicted_revpar": round(total_revenue / total_available, 2) if total_available else 0.0,
        "adr_lower": round(sum(i["adr_lower"] * i["predicted_sold_rooms"] for i in items) / total_sold, 2) if total_sold else 0.0,
        "adr_upper": round(sum(i["adr_upper"] * i["predicted_sold_rooms"] for i in items) / total_sold, 2) if total_sold else 0.0,
    }

    # 樸素基準的期間彙總（供並列比較）
    naive_rows = [i["naive"] for i in items if i["naive"]]
    naive_summary = None
    if naive_rows:
        n_sold = sum(r["predicted_sold_rooms"] for r in naive_rows)
        n_rev = sum(r["predicted_revenue"] for r in naive_rows)
        naive_summary = {
            "days":          len(naive_rows),
            "predicted_adr": round(n_rev / n_sold, 2) if n_sold else 0.0,
            "predicted_revenue": round(n_rev, 2),
            "predicted_sold_rooms": n_sold,
        }

    history_days = sum(1 for i in items if i["is_history"])

    return {
        "ok":       True,
        "start":    s.isoformat(),
        "end":      e.isoformat(),
        "items":    items,
        "summary":  summary,
        "naive_summary": naive_summary,
        "coefficients": {
            "anchor_date":     coef.anchor_date,
            "baseline_adr":    round(coef.baseline_adr, 2),
            "baseline_occ":    round(coef.baseline_occ, 6),
            "growth_adr":      round(coef.growth_adr, 4),
            "growth_occ":      round(coef.growth_occ, 4),
            "available_rooms": round(coef.available_rooms, 1),
            "fit_start":       coef.fit_start,
            "fit_end":         coef.fit_end,
            "fit_days":        coef.fit_days,
            "adr_interval":    [coef.adr_p10, coef.adr_p90],
        },
        "events":   sorted(
            {e["name"]: e for lst in ev_map.values() for e in lst}.values(),
            key=lambda x: x["name"],
        ),
        "history_days": history_days,
        "warnings": (
            ([f"預測期間有 {history_days} 天已經有實績，這幾天顯示的是「模型回頭看會怎麼猜」，"
              "可以用來檢查模型準不準"] if history_days else [])
            + (["模型錨點早於預測起日超過一年，年成長外推的不確定性會明顯放大"]
               if coef.anchor_date and (s - PS.to_date(coef.anchor_date)).days > 365 else [])
        ),
        "source_label": SOURCE_NOTE,
    }


def save_forecast_run(db: Session, result: dict, property_code: str = "",
                      user_id: str | None = None, user_name: str = "",
                      note: str = "") -> int:
    """把一次預測存成快照（評估文件 §9.1）——日後才能算真實 MAPE。"""
    summary = result["summary"]
    run = OperaForecastRun(
        property_code=property_code,
        horizon_start=result["start"],
        horizon_end=result["end"],
        model=MODEL_DECOMP,
        model_version=MODEL_VERSION,
        params_json=json.dumps(result.get("coefficients", {}), ensure_ascii=False),
        days=summary["days"],
        predicted_adr=summary["predicted_adr"],
        predicted_occ=summary["predicted_occupancy"],
        predicted_revenue=summary["predicted_revenue"],
        created_by_user_id=user_id,
        created_by_name=user_name,
        note=note,
    )
    db.add(run)
    db.flush()

    for i in result["items"]:
        db.add(OperaForecastDaily(
            run_id=run.id,
            property_code=property_code,
            business_date=i["business_date"],
            predicted_adr=i["predicted_adr"],
            predicted_occupancy=i["predicted_occupancy"],
            predicted_sold_rooms=i["predicted_sold_rooms"],
            predicted_revenue=i["predicted_revenue"],
            adr_lower=i["adr_lower"],
            adr_upper=i["adr_upper"],
            occ_lower=i["occ_lower"],
            occ_upper=i["occ_upper"],
            breakdown_json=json.dumps(i["breakdown"], ensure_ascii=False),
        ))
    db.flush()
    return run.id


def compare_runs_with_actual(db: Session, property_code: str = "") -> dict:
    """把已到期的預測快照回填實際值，算出**真實** MAPE（不是理論值）。"""
    data_start, data_end = PS.default_range(db, property_code)
    actuals = _actual_map(db, data_start, data_end, property_code)

    q = db.query(OperaForecastDaily).filter(
        OperaForecastDaily.business_date <= data_end,
        OperaForecastDaily.compared_at.is_(None),
    )
    if property_code:
        q = q.filter(OperaForecastDaily.property_code == property_code)

    filled = 0
    for row in q.all():
        f = actuals.get(row.business_date)
        if not f:
            continue
        row.actual_adr = f.adr
        row.actual_occupancy = f.occupancy
        row.actual_revenue = f.revenue
        row.compared_at = twnow()
        filled += 1
    db.flush()

    # 彙總所有已比對的預測
    q2 = db.query(OperaForecastDaily).filter(OperaForecastDaily.compared_at.isnot(None))
    if property_code:
        q2 = q2.filter(OperaForecastDaily.property_code == property_code)
    rows = q2.all()

    pairs_adr = [(float(r.actual_adr), float(r.predicted_adr)) for r in rows if r.actual_adr]
    pairs_occ = [(float(r.actual_occupancy), float(r.predicted_occupancy)) for r in rows if r.actual_occupancy]
    pairs_rev = [(float(r.actual_revenue), float(r.predicted_revenue)) for r in rows if r.actual_revenue]

    return {
        "filled":       filled,
        "compared":     len(rows),
        "adr":          _error_metrics(pairs_adr),
        "occupancy":    _error_metrics(pairs_occ),
        "revenue":      _error_metrics(pairs_rev),
        "note": "這是把過去存下來的預測快照與實際值比對的結果，屬於真實表現，"
                "與「回測」用的是不同資料（回測是模型回頭重算）。",
    }


# ══════════════════════════════════════════════════════════════════════════════
# 回測
# ══════════════════════════════════════════════════════════════════════════════

def _error_metrics(pairs: list[tuple[float, float]]) -> dict:
    """pairs = [(actual, predicted), ...]"""
    valid = [(a, p) for a, p in pairs if a not in (0, None)]
    if not valid:
        return {"n": 0, "mape": None, "mae": None, "rmse": None, "bias": None}
    n = len(valid)
    mape = sum(abs(a - p) / abs(a) for a, p in valid) / n
    mae = sum(abs(a - p) for a, p in valid) / n
    rmse = (sum((a - p) ** 2 for a, p in valid) / n) ** 0.5
    bias = sum(p - a for a, p in valid) / n
    return {
        "n":    n,
        "mape": round(mape, 4),
        "mae":  round(mae, 4),
        "rmse": round(rmse, 4),
        "bias": round(bias, 4),   # 正數 = 系統性高估
    }


def backtest(db: Session, property_code: str = "", test_days: int = 365) -> dict:
    """回測（評估文件 §5 階段二）。

    ⚠️ **嚴格切分**：用測試期起日之前的資料重新估係數，再去預測測試期。
       若直接拿全期估的係數去回測，等於偷看答案，MAPE 會虛低。

    同時跑樸素基準（去年同期同星期），兩者並列 —— 分解模型沒有明顯勝出時，
    畫面必須誠實顯示，不可只報自己的數字。
    """
    data_start, data_end = PS.default_range(db, property_code)
    all_facts = load_facts(db, data_start, data_end, property_code)
    if len(all_facts) < 400:
        return {
            "ok": False,
            "reason": f"可用歷史日只有 {len(all_facts)} 天。回測需要「訓練期 + 測試期」，"
                      "至少要 400 天以上才有意義。",
        }

    end_d = PS.to_date(all_facts[-1].business_date)
    test_start_d = end_d - timedelta(days=test_days - 1)
    train_end_d = test_start_d - timedelta(days=1)

    train_facts = [f for f in all_facts if f.business_date <= train_end_d.isoformat()]
    test_facts = [f for f in all_facts if f.business_date >= test_start_d.isoformat()]
    if len(train_facts) < 200 or len(test_facts) < 30:
        return {
            "ok": False,
            "reason": f"切分後訓練期 {len(train_facts)} 天、測試期 {len(test_facts)} 天，"
                      "樣本不足以回測。請縮短測試期天數。",
        }

    # ── 只用訓練期重新估係數（關鍵：不可資料洩漏）──────────────────────────
    coef = fit_coefficients(db, property_code, fit_end=train_end_d.isoformat())
    if not coef.is_usable:
        return {"ok": False, "reason": "訓練期資料不足以估算係數：" + "；".join(coef.warnings)}

    train_actuals = {f.business_date: f for f in train_facts}
    ev_map = _events_by_date(db, test_start_d.isoformat(), end_d.isoformat(), property_code)

    decomp_adr, decomp_occ, decomp_rev = [], [], []
    naive_adr, naive_occ, naive_rev = [], [], []
    series: list[dict] = []
    monthly: dict[str, dict[str, list]] = defaultdict(
        lambda: {"decomp": [], "naive": []}
    )

    for f in test_facts:
        iso = f.business_date
        pred = predict_day(coef, iso, ev_map.get(iso))
        nv = predict_day_naive(train_actuals, iso)

        decomp_adr.append((f.adr, pred["predicted_adr"]))
        decomp_occ.append((f.occupancy, pred["predicted_occupancy"]))
        decomp_rev.append((f.revenue, pred["predicted_revenue"]))
        monthly[iso[:7]]["decomp"].append((f.adr, pred["predicted_adr"]))

        if nv:
            naive_adr.append((f.adr, nv["predicted_adr"]))
            naive_occ.append((f.occupancy, nv["predicted_occupancy"]))
            naive_rev.append((f.revenue, nv["predicted_revenue"]))
            monthly[iso[:7]]["naive"].append((f.adr, nv["predicted_adr"]))

        series.append({
            "business_date": iso,
            "actual_adr":    round(f.adr, 2),
            "decomp_adr":    pred["predicted_adr"],
            "naive_adr":     nv["predicted_adr"] if nv else None,
            "actual_occupancy": round(f.occupancy, 6),
            "decomp_occupancy": pred["predicted_occupancy"],
            "adr_lower":     pred["adr_lower"],
            "adr_upper":     pred["adr_upper"],
            "in_interval":   pred["adr_lower"] <= f.adr <= pred["adr_upper"],
        })

    monthly_series = [
        {
            "month":       m,
            "days":        len(monthly[m]["decomp"]),
            "decomp_mape": _error_metrics(monthly[m]["decomp"])["mape"],
            "naive_mape":  _error_metrics(monthly[m]["naive"])["mape"],
        }
        for m in sorted(monthly)
    ]

    d_adr = _error_metrics(decomp_adr)
    n_adr = _error_metrics(naive_adr)
    coverage = sum(1 for s in series if s["in_interval"]) / len(series) if series else 0.0

    improvement = None
    if d_adr["mape"] and n_adr["mape"]:
        improvement = round(1 - d_adr["mape"] / n_adr["mape"], 4)

    beats = bool(d_adr["mape"] and n_adr["mape"] and d_adr["mape"] < n_adr["mape"])

    return {
        "ok": True,
        "train": {"start": train_facts[0].business_date, "end": train_end_d.isoformat(),
                  "days": len(train_facts)},
        "test":  {"start": test_start_d.isoformat(), "end": end_d.isoformat(),
                  "days": len(test_facts)},
        "models": [
            {
                "model": MODEL_DECOMP, "label": MODEL_LABELS[MODEL_DECOMP],
                "adr": d_adr, "occupancy": _error_metrics(decomp_occ),
                "revenue": _error_metrics(decomp_rev),
            },
            {
                "model": MODEL_NAIVE, "label": MODEL_LABELS[MODEL_NAIVE],
                "adr": n_adr, "occupancy": _error_metrics(naive_occ),
                "revenue": _error_metrics(naive_rev),
            },
        ],
        "series":         series,
        "monthly_series": monthly_series,
        "interval_coverage": round(coverage, 4),
        "interval_target":   round(INTERVAL_HIGH - INTERVAL_LOW, 2),
        "beats_naive":    beats,
        "improvement":    improvement,
        "verdict": (
            f"分解模型的 ADR MAPE 為 {d_adr['mape']:.1%}，樸素基準為 "
            f"{n_adr['mape']:.1%}，相對改善 {improvement:.1%}。"
            if beats and improvement is not None and d_adr["mape"] and n_adr["mape"]
            else (
                f"分解模型的 ADR MAPE 為 {d_adr['mape']:.1%}，**沒有勝過**樸素基準的 "
                f"{n_adr['mape']:.1%}。這代表模型沒學到日曆以外的東西，"
                "建議直接用「去年同期同星期」這個規則，比較好解釋。"
                if d_adr["mape"] and n_adr["mape"]
                else "樣本不足以判定模型是否勝過樸素基準。"
            )
        ),
        "warnings":     coef.warnings,
        "source_label": SOURCE_NOTE,
    }
