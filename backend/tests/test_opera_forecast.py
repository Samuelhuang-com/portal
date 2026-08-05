"""
OPERA 房價預測 — 單元測試

評估文件：docs/EVAL_opera_rate_forecasting.md

測試策略
────────
用**合成資料**驗證，而不是只跑真實資料看有沒有噴錯。合成資料的好處是
「真值已知」：先塞入指定的星期／月份／年成長係數，再檢查模型能不能還原出來。
還原不出來就代表估算邏輯有錯，這是真實資料測不出來的。

執行：
    cd backend && python -m pytest tests/test_opera_forecast.py -v
"""
from __future__ import annotations

import math
import random
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.opera_forecast import (
    EVENT_SOURCE_LEARNED,
    EVENT_SOURCE_MANUAL,
    MIN_EVENT_SAMPLES,
    OperaEvent,
)
from app.models.opera_revenue import OperaRevenueDaily, RECORD_TYPE_HISTORY
from app.services import opera_forecast_service as FS

# ── 合成資料的「真值」──────────────────────────────────────────────────────────
TRUE_DOW_ADR = [0.88, 0.87, 0.89, 0.93, 1.10, 1.27, 0.93]      # 0 = 星期一
TRUE_DOW_OCC = [0.85, 0.86, 0.90, 1.01, 1.17, 1.28, 0.91]
TRUE_MONTH = {1: 0.95, 2: 1.10, 3: 0.98, 4: 0.97, 5: 0.98, 6: 1.02,
              7: 1.05, 8: 1.08, 9: 0.99, 10: 1.00, 11: 0.96, 12: 1.02}
TRUE_GROWTH = 1.09
BASE_ADR = 2500.0
BASE_OCC = 0.68
AVAILABLE = 69

SYNTH_START = date(2023, 1, 1)
SYNTH_END = date(2026, 8, 3)
PROPERTY = "TEST"


@pytest.fixture()
def db():
    """記憶體資料庫 + 只建立預測需要的資料表。"""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    names = {
        "opera_revenue_daily", "opera_analysis_setting", "opera_event",
        "opera_forecast_coefficient", "opera_forecast_run", "opera_forecast_daily",
    }
    Base.metadata.create_all(
        bind=engine,
        tables=[t for n, t in Base.metadata.tables.items() if n in names],
    )
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed(db, start: date = SYNTH_START, end: date = SYNTH_END, seed: int = 42) -> int:
    """依真值產生逐日資料（含對數常態雜訊，模擬真實的隨機波動）。"""
    random.seed(seed)
    rows = []
    d = start
    while d <= end:
        years = (d - end).days / 365.25
        adr = (BASE_ADR * TRUE_DOW_ADR[d.weekday()] * TRUE_MONTH[d.month]
               * (TRUE_GROWTH ** years) * random.lognormvariate(0, 0.11))
        occ = (BASE_OCC * TRUE_DOW_OCC[d.weekday()] * TRUE_MONTH[d.month]
               * (TRUE_GROWTH ** (years * 0.3)) * random.lognormvariate(0, 0.16))
        occ = max(0.05, min(1.0, occ))
        sold = max(1, round(occ * AVAILABLE))
        rows.append(OperaRevenueDaily(
            property_code=PROPERTY, record_type=RECORD_TYPE_HISTORY,
            business_date=d.isoformat(), revenue=adr * sold, sold_rooms=sold,
            available_rooms=AVAILABLE, inventory_rooms=AVAILABLE, is_current=1,
        ))
        d += timedelta(days=1)
    db.add_all(rows)
    db.commit()
    return len(rows)


# ══════════════════════════════════════════════════════════════════════════════
# 離群值處理（評估文件 §9.3）
# ══════════════════════════════════════════════════════════════════════════════

def test_load_facts_排除負營收與無房晚(db):
    db.add_all([
        OperaRevenueDaily(property_code=PROPERTY, record_type=RECORD_TYPE_HISTORY,
                          business_date="2026-01-01", revenue=100000, sold_rooms=40,
                          available_rooms=69, is_current=1),
        # 負營收（實測 2026-02-23 就是這種）
        OperaRevenueDaily(property_code=PROPERTY, record_type=RECORD_TYPE_HISTORY,
                          business_date="2026-01-02", revenue=-5000, sold_rooms=3,
                          available_rooms=69, is_current=1),
        # 有營收但沒房晚 → ADR 無法計算
        OperaRevenueDaily(property_code=PROPERTY, record_type=RECORD_TYPE_HISTORY,
                          business_date="2026-01-03", revenue=5000, sold_rooms=0,
                          available_rooms=69, is_current=1),
        # 沒有可售房晚 → 住房率無法計算
        OperaRevenueDaily(property_code=PROPERTY, record_type=RECORD_TYPE_HISTORY,
                          business_date="2026-01-04", revenue=5000, sold_rooms=2,
                          available_rooms=0, is_current=1),
    ])
    db.commit()

    facts = FS.load_facts(db, "2026-01-01", "2026-01-31", PROPERTY)
    assert [f.business_date for f in facts] == ["2026-01-01"]

    excluded = FS.load_excluded(db, "2026-01-01", "2026-01-31", PROPERTY)
    assert len(excluded) == 3
    assert "負營收" in excluded[0]["reasons"]
    assert "無售出房晚" in excluded[1]["reasons"]
    assert "無可售房晚" in excluded[2]["reasons"]


def test_load_facts_不看非有效版本(db):
    db.add_all([
        OperaRevenueDaily(property_code=PROPERTY, record_type=RECORD_TYPE_HISTORY,
                          business_date="2026-01-01", revenue=100000, sold_rooms=40,
                          available_rooms=69, is_current=1),
        OperaRevenueDaily(property_code=PROPERTY, record_type=RECORD_TYPE_HISTORY,
                          business_date="2026-01-01", revenue=999999, sold_rooms=40,
                          available_rooms=69, is_current=0),   # 舊版本
        OperaRevenueDaily(property_code=PROPERTY, record_type="Forecast",
                          business_date="2026-01-01", revenue=888888, sold_rooms=40,
                          available_rooms=69, is_current=1),   # Forecast 不可混入
    ])
    db.commit()
    facts = FS.load_facts(db, "2026-01-01", "2026-01-31", PROPERTY)
    assert len(facts) == 1
    assert facts[0].revenue == 100000


# ══════════════════════════════════════════════════════════════════════════════
# 係數估算：能不能還原已知真值
# ══════════════════════════════════════════════════════════════════════════════

def test_fit_還原星期係數(db):
    _seed(db)
    coef = FS.fit_coefficients(db, PROPERTY)
    assert coef.is_usable

    mean_true = sum(TRUE_DOW_ADR) / 7
    for wd in range(7):
        expected = TRUE_DOW_ADR[wd] / mean_true      # 模型的係數是正規化過的
        got = coef.dow_adr[wd]
        assert abs(got - expected) / expected < 0.06, (
            f"{wd} 的星期係數還原誤差過大：估 {got:.3f} vs 真值 {expected:.3f}"
        )


def test_fit_還原月份係數(db):
    _seed(db)
    coef = FS.fit_coefficients(db, PROPERTY)
    mean_true = sum(TRUE_MONTH.values()) / 12
    errors = [
        abs(coef.month_adr[m] - TRUE_MONTH[m] / mean_true) / (TRUE_MONTH[m] / mean_true)
        for m in range(1, 13)
    ]
    assert sum(errors) / 12 < 0.05, f"月份係數平均誤差 {sum(errors) / 12:.2%} 過大"


def test_fit_還原年成長(db):
    _seed(db)
    coef = FS.fit_coefficients(db, PROPERTY)
    assert abs(coef.growth_adr - TRUE_GROWTH) < 0.05, (
        f"年成長還原誤差過大：估 {coef.growth_adr:.4f} vs 真值 {TRUE_GROWTH}"
    )


def test_fit_基準值錨定最近一年而非全期平均(db):
    """全期平均會低估（含較早的低價年份），若基準用全期又乘成長會重複計算。"""
    _seed(db)
    coef = FS.fit_coefficients(db, PROPERTY)
    all_facts = FS.load_facts(db, SYNTH_START.isoformat(), SYNTH_END.isoformat(), PROPERTY)
    overall = FS._weighted_adr(all_facts)
    assert coef.baseline_adr > overall, "基準值應該高於全期平均（因為錨定在最近一年）"
    assert coef.anchor_date == SYNTH_END.isoformat()


def test_fit_可售房晚用中位數(db):
    _seed(db)
    coef = FS.fit_coefficients(db, PROPERTY)
    assert coef.available_rooms == AVAILABLE


def test_fit_資料太少不可用(db):
    _seed(db, start=date(2026, 6, 1), end=date(2026, 7, 1))
    coef = FS.fit_coefficients(db, PROPERTY)
    assert not coef.is_usable
    assert any("不足以估算" in w for w in coef.warnings)


def test_fit_樣本不足的星期別退回1並提出警告(db):
    """只給 3 週資料 → 每個星期別只有 3 天，全部應退回 1.0 且發出警告。"""
    _seed(db, start=date(2026, 6, 1), end=date(2026, 8, 3))   # 64 天
    coef = FS.fit_coefficients(db, PROPERTY)
    # 64 天 > 60 → 可用，但月份樣本不足
    thin_months = [m for m in range(1, 13) if coef.month_days.get(m, 0) < FS.MIN_COEF_SAMPLE_DAYS]
    for m in thin_months:
        assert coef.month_adr[m] == 1.0
    assert any("樣本" in w for w in coef.warnings)


# ══════════════════════════════════════════════════════════════════════════════
# 預測
# ══════════════════════════════════════════════════════════════════════════════

def test_predict_day_係數相乘等於預測值(db):
    """畫面上攤開的拆解必須真的乘得回預測值，否則說明就是假的。"""
    _seed(db)
    coef = FS.fit_coefficients(db, PROPERTY)
    row = FS.predict_day(coef, "2026-09-12")
    b = row["breakdown"]
    recomputed = (b["baseline_adr"] * b["dow_adr"] * b["month_adr"]
                  * b["growth_adr"] * b["event_adr"])
    assert abs(recomputed - row["predicted_adr"]) / row["predicted_adr"] < 0.001


def test_predict_住房率不會超過100趴(db):
    _seed(db)
    coef = FS.fit_coefficients(db, PROPERTY)
    coef.baseline_occ = 0.95
    row = FS.predict_day(coef, "2026-09-12", [
        {"effective_adr_index": 1.0, "effective_occ_index": 3.0},
    ])
    assert row["predicted_occupancy"] <= 1.0
    assert row["occ_upper"] <= 1.0


def test_predict_區間必定包住預測值(db):
    _seed(db)
    coef = FS.fit_coefficients(db, PROPERTY)
    for iso in ("2026-09-01", "2026-12-25", "2027-02-14"):
        row = FS.predict_day(coef, iso)
        assert row["adr_lower"] <= row["predicted_adr"] <= row["adr_upper"]


def test_forecast_range_期間ADR用加權而非每日平均(db):
    _seed(db)
    coef = FS.fit_coefficients(db, PROPERTY)
    FS.save_coefficients(db, coef, PROPERTY)
    db.commit()

    res = FS.forecast_range(db, "2026-09-01", "2026-09-30", PROPERTY)
    assert res["ok"]
    total_rev = sum(i["predicted_revenue"] for i in res["items"])
    total_sold = sum(i["predicted_sold_rooms"] for i in res["items"])
    assert abs(res["summary"]["predicted_adr"] - total_rev / total_sold) < 0.5

    simple_mean = sum(i["predicted_adr"] for i in res["items"]) / len(res["items"])
    assert abs(res["summary"]["predicted_adr"] - simple_mean) > 0.01, (
        "加權 ADR 不應等於每日 ADR 的算術平均"
    )


def test_forecast_range_超過上限要擋(db):
    _seed(db)
    FS.save_coefficients(db, FS.fit_coefficients(db, PROPERTY), PROPERTY)
    db.commit()
    with pytest.raises(ValueError, match="最長"):
        FS.forecast_range(db, "2026-09-01", "2030-09-01", PROPERTY)


def test_forecast_range_未估算係數時回傳可讀原因(db):
    _seed(db)
    res = FS.forecast_range(db, "2026-09-01", "2026-09-10", PROPERTY)
    assert not res["ok"]
    assert "估算" in res["reason"]


def test_forecast_range_假設事件依倍數放大(db):
    _seed(db)
    FS.save_coefficients(db, FS.fit_coefficients(db, PROPERTY), PROPERTY)
    db.commit()

    base = FS.forecast_range(db, "2026-09-10", "2026-09-12", PROPERTY)
    with_ev = FS.forecast_range(db, "2026-09-10", "2026-09-12", PROPERTY, extra_events=[{
        "name": "假設展覽", "start_date": "2026-09-10", "end_date": "2026-09-12",
        "adr_index": 1.4, "occ_index": 1.15,
    }])
    ratio = with_ev["summary"]["predicted_adr"] / base["summary"]["predicted_adr"]
    assert abs(ratio - 1.4) < 0.01


def test_forecast_range_已有實績的日子會標記(db):
    _seed(db)
    FS.save_coefficients(db, FS.fit_coefficients(db, PROPERTY), PROPERTY)
    db.commit()
    res = FS.forecast_range(db, "2026-07-01", "2026-08-10", PROPERTY)
    assert res["history_days"] > 0
    assert any("實績" in w for w in res["warnings"])
    assert res["items"][0]["actual"] is not None


# ══════════════════════════════════════════════════════════════════════════════
# 樸素基準
# ══════════════════════════════════════════════════════════════════════════════

def test_naive_取364天前而非365天前(db):
    """−364 天剛好 52 週，星期必定相同；−365 會差一天，星期就對不上。"""
    _seed(db)
    actuals = FS._actual_map(db, SYNTH_START.isoformat(), SYNTH_END.isoformat(), PROPERTY)
    target = "2026-08-01"
    row = FS.predict_day_naive(actuals, target)
    assert row is not None
    ref = date.fromisoformat(row["reference_date"])
    assert ref.weekday() == date.fromisoformat(target).weekday()
    assert (date.fromisoformat(target) - ref).days == 364


def test_naive_找不到就往前再推一年(db):
    _seed(db, start=date(2023, 1, 1), end=date(2024, 12, 31))
    actuals = FS._actual_map(db, "2023-01-01", "2024-12-31", PROPERTY)
    # 2026 年往回 364 天是 2025 年（沒有資料），要能再往前推到 2024
    row = FS.predict_day_naive(actuals, "2026-06-15")
    assert row is not None
    assert row["reference_date"].startswith("2024")


# ══════════════════════════════════════════════════════════════════════════════
# 回測
# ══════════════════════════════════════════════════════════════════════════════

def test_backtest_嚴格切分不得資料洩漏(db):
    _seed(db)
    res = FS.backtest(db, PROPERTY, test_days=365)
    assert res["ok"]
    assert res["train"]["end"] < res["test"]["start"], "訓練期不可與測試期重疊"


def test_backtest_分解模型應勝過樸素基準(db):
    """合成資料的結構完全符合模型假設，若還輸給樸素基準就是估算有錯。"""
    _seed(db)
    res = FS.backtest(db, PROPERTY, test_days=365)
    decomp = next(m for m in res["models"] if m["model"] == "decomp")
    naive = next(m for m in res["models"] if m["model"] == "naive")
    assert decomp["adr"]["mape"] < naive["adr"]["mape"]
    assert res["beats_naive"] is True
    assert res["improvement"] > 0


def test_backtest_區間涵蓋率接近目標(db):
    _seed(db)
    res = FS.backtest(db, PROPERTY, test_days=365)
    # 目標 80%（p10~p90）；容許 ±15 個百分點的偏差
    assert abs(res["interval_coverage"] - res["interval_target"]) < 0.15


def test_backtest_資料不足時給可讀原因(db):
    _seed(db, start=date(2026, 1, 1), end=date(2026, 8, 3))
    res = FS.backtest(db, PROPERTY, test_days=365)
    assert not res["ok"]
    assert "天" in res["reason"]


def test_error_metrics_基本正確性():
    m = FS._error_metrics([(100.0, 110.0), (200.0, 180.0)])
    assert m["n"] == 2
    assert abs(m["mape"] - 0.10) < 1e-9          # (10/100 + 20/200) / 2
    assert abs(m["mae"] - 15.0) < 1e-9
    assert abs(m["bias"] - (-5.0)) < 1e-9        # (+10 −20) / 2
    assert FS._error_metrics([])["n"] == 0
    # 實際值為 0 的樣本要跳過，不可產生除以零
    assert FS._error_metrics([(0.0, 50.0)])["n"] == 0


def test_quantile():
    vals = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert FS._quantile(vals, 0.0) == 1.0
    assert FS._quantile(vals, 1.0) == 5.0
    assert FS._quantile(vals, 0.5) == 3.0
    assert FS._quantile([], 0.5) == 1.0


# ══════════════════════════════════════════════════════════════════════════════
# 係數存取與人工覆寫
# ══════════════════════════════════════════════════════════════════════════════

def test_save_load_係數往返一致(db):
    _seed(db)
    coef = FS.fit_coefficients(db, PROPERTY)
    FS.save_coefficients(db, coef, PROPERTY)
    db.commit()

    loaded = FS.load_coefficients(db, PROPERTY)
    assert loaded is not None
    assert abs(loaded.baseline_adr - coef.baseline_adr) < 0.01
    assert abs(loaded.growth_adr - coef.growth_adr) < 1e-6
    assert loaded.anchor_date == coef.anchor_date
    assert loaded.available_rooms == coef.available_rooms
    for wd in range(7):
        assert abs(loaded.dow_adr[wd] - coef.dow_adr[wd]) < 1e-6


def test_人工覆寫的係數重新估算時不被蓋掉(db):
    from app.models.opera_forecast import COEF_DOW, METRIC_ADR, OperaForecastCoefficient

    _seed(db)
    FS.save_coefficients(db, FS.fit_coefficients(db, PROPERTY), PROPERTY)
    db.commit()

    row = db.query(OperaForecastCoefficient).filter_by(
        property_code=PROPERTY, kind=COEF_DOW, coef_key="5", metric=METRIC_ADR).first()
    row.is_manual = 1
    row.value = 1.9
    db.commit()

    FS.save_coefficients(db, FS.fit_coefficients(db, PROPERTY), PROPERTY)
    db.commit()

    db.refresh(row)
    assert float(row.value) == 1.9, "人工覆寫值被自動估算蓋掉了"
    assert abs(float(row.fitted_value) - 1.9) > 0.1, "fitted_value 應更新為最新的自動估算值"

    loaded = FS.load_coefficients(db, PROPERTY)
    assert abs(loaded.dow_adr[5] - 1.9) < 1e-6, "預測應採用人工覆寫值"


def test_load_coefficients_未估算時回None(db):
    assert FS.load_coefficients(db, PROPERTY) is None


# ══════════════════════════════════════════════════════════════════════════════
# 事件係數學習（評估文件 §3.4）
# ══════════════════════════════════════════════════════════════════════════════

def _boost(db, start: str, end: str, factor: float) -> None:
    for r in db.query(OperaRevenueDaily).filter(
        OperaRevenueDaily.business_date >= start,
        OperaRevenueDaily.business_date <= end,
    ).all():
        r.revenue = float(r.revenue) * factor
    db.commit()


def test_learn_同名事件三次以上才可靠(db):
    _seed(db)
    FS.save_coefficients(db, FS.fit_coefficients(db, PROPERTY), PROPERTY)
    for y in (2024, 2025, 2026):
        db.add(OperaEvent(property_code=PROPERTY, name="國際電腦展", category="展覽",
                          start_date=f"{y}-06-03", end_date=f"{y}-06-07", is_active=1))
        _boost(db, f"{y}-06-03", f"{y}-06-07", 1.35)
    db.commit()

    res = FS.learn_event_coefficients(db, PROPERTY)
    assert res["ok"]
    item = next(i for i in res["items"] if i["name"] == "國際電腦展")
    assert item["occurrences"] == 3
    assert item["is_reliable"]
    # 學習值應該明顯大於 1（拉高了 35%），但不必剛好 1.35 ——
    # 因為係數估算時 6 月的月份係數已經吸收了一部分事件效果。
    assert 1.15 < item["learned_adr_index"] < 1.45


def test_learn_樣本不足時強制退回人工設定(db):
    _seed(db)
    FS.save_coefficients(db, FS.fit_coefficients(db, PROPERTY), PROPERTY)
    ev = OperaEvent(property_code=PROPERTY, name="只辦過一次", category="其他",
                    start_date="2025-03-05", end_date="2025-03-07",
                    is_active=1, source=EVENT_SOURCE_LEARNED)
    db.add(ev)
    db.commit()

    res = FS.learn_event_coefficients(db, PROPERTY)
    item = next(i for i in res["items"] if i["name"] == "只辦過一次")
    assert item["occurrences"] == 1
    assert not item["is_reliable"]
    assert str(MIN_EVENT_SAMPLES) in item["note"]

    db.refresh(ev)
    assert ev.source == EVENT_SOURCE_MANUAL, "樣本不足卻仍停留在 learned"
    assert ev.effective_adr_index == float(ev.expected_adr_index)


def test_learn_未估算係數時拒絕(db):
    _seed(db)
    res = FS.learn_event_coefficients(db, PROPERTY)
    assert not res["ok"]
    assert "係數" in res["reason"]


def test_event_effective_index_採用邏輯(db):
    ev = OperaEvent(property_code=PROPERTY, name="X", category="展覽",
                    start_date="2026-01-01", end_date="2026-01-03",
                    expected_adr_index=1.2, learned_adr_index=1.5,
                    sample_count=1, source=EVENT_SOURCE_MANUAL)
    assert ev.effective_adr_index == 1.2

    ev.source = EVENT_SOURCE_LEARNED
    assert ev.effective_adr_index == 1.2, "樣本不足時即使 source=learned 也不可採用學習值"

    ev.sample_count = MIN_EVENT_SAMPLES
    assert ev.effective_adr_index == 1.5


def test_event_days計算含頭尾(db):
    ev = OperaEvent(property_code=PROPERTY, name="X", category="展覽",
                    start_date="2026-06-03", end_date="2026-06-07")
    assert ev.days == 5


# ══════════════════════════════════════════════════════════════════════════════
# 預測快照與真實誤差
# ══════════════════════════════════════════════════════════════════════════════

def test_快照存檔後可回填實際值算真實誤差(db):
    _seed(db)
    FS.save_coefficients(db, FS.fit_coefficients(db, PROPERTY), PROPERTY)
    db.commit()

    # 預測一段**已經有實績**的期間，這樣才能立刻回填
    res = FS.forecast_range(db, "2026-07-01", "2026-07-31", PROPERTY)
    run_id = FS.save_forecast_run(db, res, PROPERTY, user_name="pytest")
    db.commit()
    assert run_id > 0

    cmp1 = FS.compare_runs_with_actual(db, PROPERTY)
    db.commit()
    assert cmp1["filled"] == 31
    assert cmp1["adr"]["n"] == 31
    assert cmp1["adr"]["mape"] is not None

    # 再跑一次不應重複回填（compared_at 已寫入）
    cmp2 = FS.compare_runs_with_actual(db, PROPERTY)
    assert cmp2["filled"] == 0
    assert cmp2["compared"] == 31


def test_years_from_anchor方向正確(db):
    coef = FS.Coefficients(anchor_date="2026-08-03")
    assert FS._years_from_anchor(coef, "2027-08-03") > 0.99
    assert FS._years_from_anchor(coef, "2025-08-03") < -0.99
    assert abs(FS._years_from_anchor(coef, "2026-08-03")) < 1e-9
