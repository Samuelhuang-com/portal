"""
OPERA 營運分析 — 房價預測（事件月曆／係數／預測執行／逐日預測）

評估文件：docs/EVAL_opera_rate_forecasting.md
規格書：  docs/SPEC_opera_rate_forecast.md

設計原則（來自評估文件的實測結論，不可便宜行事）
────────────────────────────────────────────────────────────────────────────
1. **可解釋優先**。預測用乘法分解模型，畫面必須能攤開每一項係數：
       預測 ADR = 基準 × 星期 × 月份 × 年成長 × 事件
   黑箱模型給不出理由，收益經理不敢用，也無法除錯。

2. **一律附帶預測區間**。實測樸素基準（去年同期同星期）ADR MAPE 已達 14.6%，
   只給單一數字會讓使用者誤以為那是確定值。

3. **樸素基準必須保留並同時顯示**。任何模型若沒有明顯低於 14.6%，
   就代表沒學到日曆以外的東西，不值得取代規則。

4. **事件係數樣本不足時不可自動學習**。同類事件少於 `MIN_EVENT_SAMPLES` 次時，
   一律標示為人工設定，不能拿單一樣本當結論。

5. **每次預測都要存快照**（`OperaForecastRun` + `OperaForecastDaily`），
   否則日後無法回頭算真實 MAPE，只能講理論值。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow

# ── 模型版本（改動係數定義或公式時必須進版，回測才比得出差異）──────────────────
MODEL_VERSION = "decomp-1.0"
MODEL_LABEL = "乘法分解模型 v1.0"

MODEL_NAIVE = "naive"          # 去年同期同星期（基準線）
MODEL_DECOMP = "decomp"        # 乘法分解
MODEL_LABELS = {
    MODEL_NAIVE:  "樸素基準（去年同期同星期）",
    MODEL_DECOMP: MODEL_LABEL,
}

# ── 事件 ─────────────────────────────────────────────────────────────────────
EVENT_CATEGORIES: list[str] = [
    "展覽",       # 國際電腦展、旅展等
    "連假",       # 連續假期
    "國定假日",   # 單日
    "春節",       # 農曆，跨年度日期會飄移，單獨一類
    "大型團體",   # 已知的大型團體入住
    "在地活動",   # 演唱會、賽事、廟會
    "其他",
]

EVENT_SOURCE_MANUAL = "manual"
EVENT_SOURCE_LEARNED = "learned"
EVENT_SOURCE_LABELS = {
    EVENT_SOURCE_MANUAL:  "人工設定",
    EVENT_SOURCE_LEARNED: "資料學習",
}

# 少於這個樣本數就不可自動學習係數（評估文件 §3.4）
MIN_EVENT_SAMPLES = 3

# ── 係數 ─────────────────────────────────────────────────────────────────────
COEF_BASELINE = "baseline"   # coef_key = "-"      基準值（ADR 金額／住房率比例）
COEF_DOW = "dow"             # coef_key = "0".."6" 0 = 星期一
COEF_MONTH = "month"         # coef_key = "1".."12"
COEF_GROWTH = "growth"       # coef_key = "-"      年成長率（1.093 = +9.3%）
COEF_HOLIDAY = "holiday"     # coef_key = 事件類別
COEF_INTERVAL = "interval"   # coef_key = "p10" / "p90"  殘差分位數（預測區間用）
COEF_ANCHOR = "anchor"       # coef_key = "date" / "available_rooms" / "fit_days"

COEF_KINDS = (COEF_BASELINE, COEF_DOW, COEF_MONTH, COEF_GROWTH,
              COEF_HOLIDAY, COEF_INTERVAL, COEF_ANCHOR)
COEF_KIND_LABELS = {
    COEF_BASELINE: "基準值",
    COEF_DOW:      "星期係數",
    COEF_MONTH:    "月份係數",
    COEF_GROWTH:   "年成長係數",
    COEF_HOLIDAY:  "事件類別係數",
    COEF_INTERVAL: "預測區間分位數",
    COEF_ANCHOR:   "基準錨點",
}

# 使用者可以人工覆寫的係數種類（錨點與區間是算出來的事實，改了會讓模型自相矛盾）
COEF_EDITABLE_KINDS = (COEF_BASELINE, COEF_DOW, COEF_MONTH, COEF_GROWTH)

METRIC_ADR = "adr"
METRIC_OCC = "occupancy"
METRIC_LABELS = {METRIC_ADR: "ADR", METRIC_OCC: "住房率"}

# 係數估算時每一格至少要有幾天樣本，否則退回 1.0（不套用）
MIN_COEF_SAMPLE_DAYS = 8


class OperaEvent(Base):
    """事件月曆（評估文件 §3.4、§9.1）

    `expected_*` 是人工填的預期倍數，`learned_*` 是從歷史資料學出來的。
    `source` 決定預測實際採用哪一組 —— 樣本不足時強制留在 manual。
    """

    __tablename__ = "opera_event"

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_code: Mapped[str] = mapped_column(String(20), default="", index=True)

    name:       Mapped[str] = mapped_column(String(120), default="", index=True)
    category:   Mapped[str] = mapped_column(String(20), default="其他", index=True)
    start_date: Mapped[str] = mapped_column(String(10), default="", index=True)
    end_date:   Mapped[str] = mapped_column(String(10), default="", index=True)

    # 人工預期倍數（1.0 = 無影響）
    expected_adr_index: Mapped[float] = mapped_column(Numeric(8, 4), default=1.0)
    expected_occ_index: Mapped[float] = mapped_column(Numeric(8, 4), default=1.0)

    # 自動學習倍數（尚未學習時為 NULL，不可用 0 代表「沒有」）
    learned_adr_index: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True, default=None)
    learned_occ_index: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True, default=None)
    sample_count:      Mapped[int]          = mapped_column(Integer, default=0)
    learned_at:        Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)

    source:    Mapped[str] = mapped_column(String(10), default=EVENT_SOURCE_MANUAL)
    is_active: Mapped[int] = mapped_column(Integer, default=1, index=True)
    note:      Mapped[str] = mapped_column(String(500), default="")

    created_at:         Mapped[datetime]   = mapped_column(DateTime, default=twnow)
    updated_at:         Mapped[datetime]   = mapped_column(DateTime, default=twnow, onupdate=twnow)
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    updated_by_name:    Mapped[str]        = mapped_column(String(100), default="")

    # ── 衍生 ────────────────────────────────────────────────────────────────
    @property
    def days(self) -> int:
        from app.services.opera_period_service import to_date
        if not self.start_date or not self.end_date:
            return 0
        return (to_date(self.end_date) - to_date(self.start_date)).days + 1

    @property
    def is_learnable(self) -> bool:
        """樣本數足夠才允許採用學習係數（評估文件 §3.4）。"""
        return self.sample_count >= MIN_EVENT_SAMPLES

    @property
    def effective_adr_index(self) -> float:
        if self.source == EVENT_SOURCE_LEARNED and self.is_learnable and self.learned_adr_index:
            return float(self.learned_adr_index)
        return float(self.expected_adr_index or 1.0)

    @property
    def effective_occ_index(self) -> float:
        if self.source == EVENT_SOURCE_LEARNED and self.is_learnable and self.learned_occ_index:
            return float(self.learned_occ_index)
        return float(self.expected_occ_index or 1.0)

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "property_code": self.property_code,
            "name":          self.name,
            "category":      self.category,
            "start_date":    self.start_date,
            "end_date":      self.end_date,
            "days":          self.days,
            "expected_adr_index": float(self.expected_adr_index or 1.0),
            "expected_occ_index": float(self.expected_occ_index or 1.0),
            "learned_adr_index":  float(self.learned_adr_index) if self.learned_adr_index is not None else None,
            "learned_occ_index":  float(self.learned_occ_index) if self.learned_occ_index is not None else None,
            "sample_count":       self.sample_count,
            "is_learnable":       self.is_learnable,
            "learned_at":    self.learned_at.strftime("%Y/%m/%d %H:%M") if self.learned_at else "",
            "source":        self.source,
            "source_label":  EVENT_SOURCE_LABELS.get(self.source, self.source),
            "effective_adr_index": round(self.effective_adr_index, 4),
            "effective_occ_index": round(self.effective_occ_index, 4),
            "is_active":     bool(self.is_active),
            "note":          self.note,
            "updated_at":    self.updated_at.strftime("%Y/%m/%d %H:%M") if self.updated_at else "",
            "updated_by_name": self.updated_by_name,
            "detail": {
                "事件名稱":     self.name,
                "類別":         self.category,
                "起始日":       self.start_date,
                "結束日":       self.end_date,
                "天數":         f"{self.days} 天",
                "人工 ADR 倍數":  f"{float(self.expected_adr_index or 1.0):.2f}",
                "人工住房率倍數": f"{float(self.expected_occ_index or 1.0):.2f}",
                "學習 ADR 倍數":  f"{float(self.learned_adr_index):.2f}" if self.learned_adr_index is not None else "—",
                "學習住房率倍數": f"{float(self.learned_occ_index):.2f}" if self.learned_occ_index is not None else "—",
                "學習樣本數":   f"{self.sample_count} 次"
                                + ("" if self.is_learnable else f"（少於 {MIN_EVENT_SAMPLES} 次，不可靠）"),
                "採用來源":     EVENT_SOURCE_LABELS.get(self.source, self.source),
                "啟用":         "是" if self.is_active else "否",
                "備註":         self.note or "—",
                "最後更新":     self.updated_at.strftime("%Y/%m/%d %H:%M") if self.updated_at else "—",
            },
        }


class OperaForecastCoefficient(Base):
    """預測係數 — 自動估算，允許人工覆寫（評估文件 §9.1）

    唯一業務鍵：property_code + kind + coef_key + metric
    """

    __tablename__ = "opera_forecast_coefficient"

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_code: Mapped[str] = mapped_column(String(20), default="", index=True)

    kind:     Mapped[str] = mapped_column(String(20), default="", index=True)
    coef_key: Mapped[str] = mapped_column(String(30), default="", index=True)
    metric:   Mapped[str] = mapped_column(String(20), default=METRIC_ADR, index=True)

    value:       Mapped[float] = mapped_column(Numeric(14, 6), default=1.0)
    fitted_value: Mapped[float] = mapped_column(Numeric(14, 6), default=1.0)   # 自動估算值（人工覆寫後仍保留）
    sample_days: Mapped[int]   = mapped_column(Integer, default=0)

    is_manual: Mapped[int] = mapped_column(Integer, default=0)
    fit_start: Mapped[str] = mapped_column(String(10), default="")
    fit_end:   Mapped[str] = mapped_column(String(10), default="")

    fitted_at:          Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    updated_at:         Mapped[datetime]        = mapped_column(DateTime, default=twnow, onupdate=twnow)
    updated_by_user_id: Mapped[str | None]      = mapped_column(String(36), nullable=True, default=None)
    updated_by_name:    Mapped[str]             = mapped_column(String(100), default="")

    @property
    def is_reliable(self) -> bool:
        """樣本太少的係數要標示出來，避免使用者以為每一格都同樣可信。"""
        if self.kind in (COEF_BASELINE, COEF_GROWTH, COEF_INTERVAL, COEF_ANCHOR):
            return True
        return self.sample_days >= MIN_COEF_SAMPLE_DAYS

    @property
    def is_editable(self) -> bool:
        return self.kind in COEF_EDITABLE_KINDS

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "property_code": self.property_code,
            "kind":          self.kind,
            "kind_label":    COEF_KIND_LABELS.get(self.kind, self.kind),
            "coef_key":      self.coef_key,
            "metric":        self.metric,
            "metric_label":  METRIC_LABELS.get(self.metric, self.metric),
            "value":         float(self.value),
            "fitted_value":  float(self.fitted_value),
            "sample_days":   self.sample_days,
            "is_reliable":   self.is_reliable,
            "is_editable":   self.is_editable,
            "is_manual":     bool(self.is_manual),
            "fit_start":     self.fit_start,
            "fit_end":       self.fit_end,
            "fitted_at":     self.fitted_at.strftime("%Y/%m/%d %H:%M") if self.fitted_at else "",
            "updated_at":    self.updated_at.strftime("%Y/%m/%d %H:%M") if self.updated_at else "",
            "updated_by_name": self.updated_by_name,
        }


class OperaForecastRun(Base):
    """每一次預測的執行紀錄（評估文件 §9.1）

    存下來才有辦法日後回頭比對實際值、算出**真實** MAPE。
    """

    __tablename__ = "opera_forecast_run"

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_code: Mapped[str] = mapped_column(String(20), default="", index=True)

    run_at:        Mapped[datetime] = mapped_column(DateTime, default=twnow, index=True)
    horizon_start: Mapped[str]      = mapped_column(String(10), default="", index=True)
    horizon_end:   Mapped[str]      = mapped_column(String(10), default="", index=True)

    model:         Mapped[str] = mapped_column(String(20), default=MODEL_DECOMP)
    model_version: Mapped[str] = mapped_column(String(20), default=MODEL_VERSION)
    params_json:   Mapped[str] = mapped_column(Text, default="{}")

    days:            Mapped[int]   = mapped_column(Integer, default=0)
    predicted_adr:   Mapped[float] = mapped_column(Numeric(14, 4), default=0)   # 期間加權
    predicted_occ:   Mapped[float] = mapped_column(Numeric(10, 6), default=0)
    predicted_revenue: Mapped[float] = mapped_column(Numeric(16, 4), default=0)

    created_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    created_by_name:    Mapped[str]        = mapped_column(String(100), default="")
    note:               Mapped[str]        = mapped_column(String(300), default="")

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "property_code": self.property_code,
            "run_at":        self.run_at.strftime("%Y/%m/%d %H:%M") if self.run_at else "",
            "horizon_start": self.horizon_start,
            "horizon_end":   self.horizon_end,
            "model":         self.model,
            "model_label":   MODEL_LABELS.get(self.model, self.model),
            "model_version": self.model_version,
            "days":          self.days,
            "predicted_adr":     float(self.predicted_adr),
            "predicted_occ":     float(self.predicted_occ),
            "predicted_revenue": float(self.predicted_revenue),
            "created_by_name":   self.created_by_name,
            "note":              self.note,
        }


class OperaForecastDaily(Base):
    """逐日預測結果（評估文件 §9.1）

    `actual_*` 欄位在該日期的實績進來後才回填，用於算真實 MAPE。
    """

    __tablename__ = "opera_forecast_daily"

    id:     Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, default=0, index=True)

    property_code: Mapped[str] = mapped_column(String(20), default="", index=True)
    business_date: Mapped[str] = mapped_column(String(10), default="", index=True)

    predicted_adr:        Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    predicted_occupancy:  Mapped[float] = mapped_column(Numeric(10, 6), default=0)
    predicted_sold_rooms: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    predicted_revenue:    Mapped[float] = mapped_column(Numeric(16, 4), default=0)

    adr_lower: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    adr_upper: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    occ_lower: Mapped[float] = mapped_column(Numeric(10, 6), default=0)
    occ_upper: Mapped[float] = mapped_column(Numeric(10, 6), default=0)

    breakdown_json: Mapped[str] = mapped_column(Text, default="{}")

    actual_adr:       Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True, default=None)
    actual_occupancy: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True, default=None)
    actual_revenue:   Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True, default=None)
    compared_at:      Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)

    def to_dict(self) -> dict:
        import json
        try:
            breakdown = json.loads(self.breakdown_json or "{}")
        except (TypeError, ValueError):
            breakdown = {}
        return {
            "id":            self.id,
            "run_id":        self.run_id,
            "business_date": self.business_date,
            "predicted_adr":        float(self.predicted_adr),
            "predicted_occupancy":  float(self.predicted_occupancy),
            "predicted_sold_rooms": float(self.predicted_sold_rooms),
            "predicted_revenue":    float(self.predicted_revenue),
            "adr_lower": float(self.adr_lower),
            "adr_upper": float(self.adr_upper),
            "occ_lower": float(self.occ_lower),
            "occ_upper": float(self.occ_upper),
            "breakdown": breakdown,
            "actual_adr":       float(self.actual_adr) if self.actual_adr is not None else None,
            "actual_occupancy": float(self.actual_occupancy) if self.actual_occupancy is not None else None,
            "actual_revenue":   float(self.actual_revenue) if self.actual_revenue is not None else None,
        }
