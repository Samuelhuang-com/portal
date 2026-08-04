"""
OPERA 營運分析 — History and Forecast 原始層、每日營收事實表、分析門檻設定

規格書：docs/SPEC_opera_analytics.md §5.4 / §5.6 / §5.7

⚠️ 實測重點（規格書 §3.4、§3.6）
  1. 可售房晚一律用 CF_CALC_INV_ROOMS（= INVENTORY_ROOMS − CF_OOO_ROOMS），
     直接用 INVENTORY_ROOMS 會低估住房率。
  2. 前 24 個 SUM*PERREC_TYPE 欄位是「同 REC_TYPE 全期合計」的重複值，
     只寫入 raw 層，不進 fact 表（REC_TYPE / REC_TYPE_DESC 除外）。
  3. ADR / 住房率 / RevPAR 不落地，一律查詢時以加權公式計算。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow

# ── History and Forecast TXT 表頭（固定 55 欄，順序即位置索引）──────────────────
HF_COLUMNS: list[str] = [
    "GPAGEID", "REC_TYPE", "REC_TYPE_DESC", "SUMNO_ROOMSPERREC_TYPE",
    "SUMCALC_OCCROOMSPERREC_TYPE", "SUMCALC_INVROOMSPERREC_TYPE",
    "SUMARRIVAL_ROOMSPERREC_TYPE", "SUMCOMPLIMENTARY_ROOMSPERREC_T",
    "SUMHOUSE_USE_ROOMSPERREC_TYPE", "SUMDAY_USE_ROOMSPERREC_TYPE",
    "SUMNO_SHOW_ROOMSPERREC_TYPE", "SUMIND_DEDUCT_ROOMSPERREC_TYPE",
    "SUMIND_NON_DEDUCT_ROOMSPERREC_", "SUMGRP_DEDUCT_ROOMSPERREC_TYPE",
    "SUMGRP_NON_DEDUCT_ROOMSPERREC_", "SUMDEPARTURE_ROOMSPERREC_TYPE",
    "SUMOOO_ROOMSPERREC_TYPE", "SUMNO_PERSONSPERREC_TYPE",
    "SUMINVENTORY_ROOMSPERREC_TYPE", "SUMREVENUEPERREC_TYPE",
    "SUMOWNER_ROOMSPERREC_TYPE", "SUMFF_ROOMSPERREC_TYPE",
    "CF_AVERAGE_ROOM_RATE_REC_TYPE", "CF_OCCUPANCY_REC_TYPE", "REVENUE",
    "NO_ROOMS", "IND_DEDUCT_ROOMS", "IND_NON_DEDUCT_ROOMS", "GRP_DEDUCT_ROOMS",
    "GRP_NON_DEDUCT_ROOMS", "NO_PERSONS", "ARRIVAL_ROOMS", "DEPARTURE_ROOMS",
    "COMPLIMENTARY_ROOMS", "HOUSE_USE_ROOMS", "DAY_USE_ROOMS", "NO_SHOW_ROOMS",
    "INVENTORY_ROOMS", "CONSIDERED_DATE", "CHAR_CONSIDERED_DATE",
    "IND_DEDUCT_REVENUE", "IND_NON_DEDUCT_REVENUE", "GRP_NON_DEDUCT_REVENUE",
    "GRP_DEDUCT_REVENUE", "OWNER_ROOMS", "FF_ROOMS", "CF_OOO_ROOMS",
    "CF_CALC_OCC_ROOMS", "CF_CALC_INV_ROOMS", "CF_AVERAGE_ROOM_RATE",
    "CF_OCCUPANCY", "CF_IND_DED_REV", "CF_IND_NON_DED_REV",
    "CF_BLK_DED_REV", "CF_BLK_NON_DED_REV",
]

HF_WIDTH = 55

RECORD_TYPE_HISTORY = "History"
RECORD_TYPE_FORECAST = "Forecast"
HF_VALID_RECORD_TYPES = (RECORD_TYPE_HISTORY, RECORD_TYPE_FORECAST)

# History and Forecast footer 兩行結構的欄名（規格書 §3.3，實測 21 欄）
HF_FOOTER_KEYS = [
    "SUMNO_ROOMSPERREPORT", "SUMARRIVAL_ROOMSPERREPORT",
    "SUMCOMPLIMENTARY_ROOMSPERREPOR", "SUMHOUSE_USE_ROOMSPERREPORT",
    "SUMIND_DEDUCT_ROOMSPERREPORT", "SUMIND_NON_DEDUCT_ROOMSPERREPO",
    "SUMGRP_DEDUCT_ROOMSPERREPORT", "SUMGRP_NON_DEDUCT_ROOMSPERREPO",
    "SUMDEPARTURE_ROOMSPERREPORT", "SUMOOO_ROOMSPERREPORT",
    "SUMNO_PERSONSPERREPORT", "SUMREVENUEPERREPORT",
    "SUMINVENTORY_ROOMSPERREPORT", "CF_AVERAGE_ROOM_RATE_REPORT",
    "CF_OCCUPANCY_REPORT", "SUMOWNER_ROOMSPERREPORT", "SUMFF_ROOMSPERREPORT",
    "SUMCALC_OCCROOMSPERREPORT", "SUMCALC_INVROOMSPERREPORT",
    "SUMDAY_USE_ROOMSPERREPORT", "SUMNO_SHOW_ROOMSPERREPORT",
]


def _col_attr(name: str) -> str:
    """來源欄名 → ORM 屬性名（小寫；重複底線結尾保留）"""
    return name.lower()


class OperaHistoryForecastRaw(Base):
    """History and Forecast 原始層 — 所有來源欄位一律 TEXT（規格書 §5.4）"""

    __tablename__ = "opera_history_forecast_raw"

    id:            Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id:      Mapped[int]      = mapped_column(Integer, index=True, default=0)
    source_row_no: Mapped[int]      = mapped_column(Integer, default=0)
    row_hash:      Mapped[str]      = mapped_column(String(64),  default="", index=True)
    record_key:    Mapped[str]      = mapped_column(String(200), default="", index=True)
    imported_at:   Mapped[datetime] = mapped_column(DateTime, default=twnow)

    gpageid:                        Mapped[str] = mapped_column(Text, default="")
    rec_type:                       Mapped[str] = mapped_column(Text, default="")
    rec_type_desc:                  Mapped[str] = mapped_column(Text, default="")
    sumno_roomsperrec_type:         Mapped[str] = mapped_column(Text, default="")
    sumcalc_occroomsperrec_type:    Mapped[str] = mapped_column(Text, default="")
    sumcalc_invroomsperrec_type:    Mapped[str] = mapped_column(Text, default="")
    sumarrival_roomsperrec_type:    Mapped[str] = mapped_column(Text, default="")
    sumcomplimentary_roomsperrec_t: Mapped[str] = mapped_column(Text, default="")
    sumhouse_use_roomsperrec_type:  Mapped[str] = mapped_column(Text, default="")
    sumday_use_roomsperrec_type:    Mapped[str] = mapped_column(Text, default="")
    sumno_show_roomsperrec_type:    Mapped[str] = mapped_column(Text, default="")
    sumind_deduct_roomsperrec_type: Mapped[str] = mapped_column(Text, default="")
    sumind_non_deduct_roomsperrec_: Mapped[str] = mapped_column(Text, default="")
    sumgrp_deduct_roomsperrec_type: Mapped[str] = mapped_column(Text, default="")
    sumgrp_non_deduct_roomsperrec_: Mapped[str] = mapped_column(Text, default="")
    sumdeparture_roomsperrec_type:  Mapped[str] = mapped_column(Text, default="")
    sumooo_roomsperrec_type:        Mapped[str] = mapped_column(Text, default="")
    sumno_personsperrec_type:       Mapped[str] = mapped_column(Text, default="")
    suminventory_roomsperrec_type:  Mapped[str] = mapped_column(Text, default="")
    sumrevenueperrec_type:          Mapped[str] = mapped_column(Text, default="")
    sumowner_roomsperrec_type:      Mapped[str] = mapped_column(Text, default="")
    sumff_roomsperrec_type:         Mapped[str] = mapped_column(Text, default="")
    cf_average_room_rate_rec_type:  Mapped[str] = mapped_column(Text, default="")
    cf_occupancy_rec_type:          Mapped[str] = mapped_column(Text, default="")
    revenue:                        Mapped[str] = mapped_column(Text, default="")
    no_rooms:                       Mapped[str] = mapped_column(Text, default="")
    ind_deduct_rooms:               Mapped[str] = mapped_column(Text, default="")
    ind_non_deduct_rooms:           Mapped[str] = mapped_column(Text, default="")
    grp_deduct_rooms:               Mapped[str] = mapped_column(Text, default="")
    grp_non_deduct_rooms:           Mapped[str] = mapped_column(Text, default="")
    no_persons:                     Mapped[str] = mapped_column(Text, default="")
    arrival_rooms:                  Mapped[str] = mapped_column(Text, default="")
    departure_rooms:                Mapped[str] = mapped_column(Text, default="")
    complimentary_rooms:            Mapped[str] = mapped_column(Text, default="")
    house_use_rooms:                Mapped[str] = mapped_column(Text, default="")
    day_use_rooms:                  Mapped[str] = mapped_column(Text, default="")
    no_show_rooms:                  Mapped[str] = mapped_column(Text, default="")
    inventory_rooms:                Mapped[str] = mapped_column(Text, default="")
    considered_date:                Mapped[str] = mapped_column(Text, default="")
    char_considered_date:           Mapped[str] = mapped_column(Text, default="")
    ind_deduct_revenue:             Mapped[str] = mapped_column(Text, default="")
    ind_non_deduct_revenue:         Mapped[str] = mapped_column(Text, default="")
    grp_non_deduct_revenue:         Mapped[str] = mapped_column(Text, default="")
    grp_deduct_revenue:             Mapped[str] = mapped_column(Text, default="")
    owner_rooms:                    Mapped[str] = mapped_column(Text, default="")
    ff_rooms:                       Mapped[str] = mapped_column(Text, default="")
    cf_ooo_rooms:                   Mapped[str] = mapped_column(Text, default="")
    cf_calc_occ_rooms:              Mapped[str] = mapped_column(Text, default="")
    cf_calc_inv_rooms:              Mapped[str] = mapped_column(Text, default="")
    cf_average_room_rate:           Mapped[str] = mapped_column(Text, default="")
    cf_occupancy:                   Mapped[str] = mapped_column(Text, default="")
    cf_ind_ded_rev:                 Mapped[str] = mapped_column(Text, default="")
    cf_ind_non_ded_rev:             Mapped[str] = mapped_column(Text, default="")
    cf_blk_ded_rev:                 Mapped[str] = mapped_column(Text, default="")
    cf_blk_non_ded_rev:             Mapped[str] = mapped_column(Text, default="")

    def to_source_dict(self) -> dict:
        return {col: getattr(self, _col_attr(col), "") or "" for col in HF_COLUMNS}


class OperaRevenueDaily(Base):
    """每日營收事實表（規格書 §5.6）

    唯一業務鍵：property_code + record_type + business_date（is_current=1）
    """

    __tablename__ = "opera_revenue_daily"

    id:       Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(Integer, index=True, default=0)
    raw_id:   Mapped[int] = mapped_column(Integer, default=0)

    property_code: Mapped[str] = mapped_column(String(20), default="", index=True)
    record_type:   Mapped[str] = mapped_column(String(10), default="", index=True)
    business_date: Mapped[str] = mapped_column(String(10), default="", index=True)

    revenue:         Mapped[float] = mapped_column(Numeric(16, 4), default=0)
    sold_rooms:      Mapped[int]   = mapped_column(Integer, default=0)
    inventory_rooms: Mapped[int]   = mapped_column(Integer, default=0)
    ooo_rooms:       Mapped[int]   = mapped_column(Integer, default=0)
    available_rooms: Mapped[int]   = mapped_column(Integer, default=0)   # CF_CALC_INV_ROOMS

    individual_deduct_rooms:     Mapped[int] = mapped_column(Integer, default=0)
    individual_non_deduct_rooms: Mapped[int] = mapped_column(Integer, default=0)
    group_deduct_rooms:          Mapped[int] = mapped_column(Integer, default=0)
    group_non_deduct_rooms:      Mapped[int] = mapped_column(Integer, default=0)

    individual_deduct_revenue:     Mapped[float] = mapped_column(Numeric(16, 4), default=0)
    individual_non_deduct_revenue: Mapped[float] = mapped_column(Numeric(16, 4), default=0)
    group_deduct_revenue:          Mapped[float] = mapped_column(Numeric(16, 4), default=0)
    group_non_deduct_revenue:      Mapped[float] = mapped_column(Numeric(16, 4), default=0)

    arrival_rooms:       Mapped[int] = mapped_column(Integer, default=0)
    departure_rooms:     Mapped[int] = mapped_column(Integer, default=0)
    complimentary_rooms: Mapped[int] = mapped_column(Integer, default=0)
    house_use_rooms:     Mapped[int] = mapped_column(Integer, default=0)
    day_use_rooms:       Mapped[int] = mapped_column(Integer, default=0)
    no_show_rooms:       Mapped[int] = mapped_column(Integer, default=0)
    no_persons:          Mapped[int] = mapped_column(Integer, default=0)

    row_hash:   Mapped[str] = mapped_column(String(64), default="")
    is_current: Mapped[int] = mapped_column(Integer, default=1, index=True)

    imported_at: Mapped[datetime] = mapped_column(DateTime, default=twnow)

    # ── 衍生（不落地，查詢時計算；此處僅供單筆 Drawer 顯示）────────────────
    @property
    def adr(self) -> float:
        return float(self.revenue) / self.sold_rooms if self.sold_rooms else 0.0

    @property
    def occupancy(self) -> float:
        return self.sold_rooms / self.available_rooms if self.available_rooms else 0.0

    @property
    def revpar(self) -> float:
        return float(self.revenue) / self.available_rooms if self.available_rooms else 0.0

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "raw_id":          self.raw_id,
            "batch_id":        self.batch_id,
            "record_type":     self.record_type,
            "business_date":   self.business_date,
            "revenue":         float(self.revenue),
            "sold_rooms":      self.sold_rooms,
            "available_rooms": self.available_rooms,
            "inventory_rooms": self.inventory_rooms,
            "ooo_rooms":       self.ooo_rooms,
            "adr":             round(self.adr, 2),
            "occupancy":       round(self.occupancy, 6),
            "revpar":          round(self.revpar, 2),
            "individual_rooms": self.individual_deduct_rooms + self.individual_non_deduct_rooms,
            "group_rooms":      self.group_deduct_rooms + self.group_non_deduct_rooms,
            "individual_revenue": float(self.individual_deduct_revenue) + float(self.individual_non_deduct_revenue),
            "group_revenue":      float(self.group_deduct_revenue) + float(self.group_non_deduct_revenue),
            "arrival_rooms":   self.arrival_rooms,
            "departure_rooms": self.departure_rooms,
            "no_persons":      self.no_persons,
            "detail": {
                "資料類型":         self.record_type,
                "房間營收":         f"{float(self.revenue):,.0f}",
                "已售房晚":         f"{self.sold_rooms:,}",
                "可售房晚":         f"{self.available_rooms:,}",
                "實體房數":         f"{self.inventory_rooms:,}",
                "OOO 房數":         f"{self.ooo_rooms:,}",
                "ADR":              f"{self.adr:,.0f}",
                "住房率":           f"{self.occupancy * 100:.1f}%",
                "RevPAR":           f"{self.revpar:,.0f}",
                "散客確定房數":     f"{self.individual_deduct_rooms:,}",
                "散客非確定房數":   f"{self.individual_non_deduct_rooms:,}",
                "團體確定房數":     f"{self.group_deduct_rooms:,}",
                "團體非確定房數":   f"{self.group_non_deduct_rooms:,}",
                "散客確定營收":     f"{float(self.individual_deduct_revenue):,.0f}",
                "散客非確定營收":   f"{float(self.individual_non_deduct_revenue):,.0f}",
                "團體確定營收":     f"{float(self.group_deduct_revenue):,.0f}",
                "團體非確定營收":   f"{float(self.group_non_deduct_revenue):,.0f}",
                "抵達房數":         f"{self.arrival_rooms:,}",
                "退房房數":         f"{self.departure_rooms:,}",
                "招待房":           f"{self.complimentary_rooms:,}",
                "自用房":           f"{self.house_use_rooms:,}",
                "日用房":           f"{self.day_use_rooms:,}",
                "No-show 房數":     f"{self.no_show_rooms:,}",
                "人數":             f"{self.no_persons:,}",
                "批次編號":         str(self.batch_id),
            },
        }


# ── 分析門檻設定（規格書 §5.7）────────────────────────────────────────────────

DEFAULT_ANALYSIS_SETTINGS: dict[str, tuple[float, str, str]] = {
    # key: (預設值, value_type, 說明)
    "high_occupancy_threshold":        (0.95, "float", "高住房率固定門檻"),
    "opportunity_occupancy_threshold": (0.90, "float", "高住房率低 ADR 機會門檻"),
    "adr_low_multiplier":              (0.50, "float", "ADR 偏低倍數"),
    "adr_high_multiplier":             (1.50, "float", "ADR 偏高倍數"),
    "annual_occupancy_diff_pp":        (0.10, "float", "與年度住房率差異門檻（10 個百分點）"),
    "long_stay_nights":                (7,    "int",   "長住客門檻（晚）"),
}


class OperaAnalysisSetting(Base):
    """分析門檻設定 — 集中管理，禁止散落程式碼（規格書 §5.7）"""

    __tablename__ = "opera_analysis_setting"

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_code: Mapped[str] = mapped_column(String(20), default="", index=True)
    setting_key:   Mapped[str] = mapped_column(String(50), default="", index=True)
    setting_value: Mapped[str] = mapped_column(String(50), default="")
    value_type:    Mapped[str] = mapped_column(String(10), default="float")
    description:   Mapped[str] = mapped_column(String(200), default="")

    updated_at:         Mapped[datetime]   = mapped_column(DateTime, default=twnow, onupdate=twnow)
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    updated_by_name:    Mapped[str]        = mapped_column(String(100), default="")

    def typed_value(self) -> float | int:
        try:
            return int(self.setting_value) if self.value_type == "int" else float(self.setting_value)
        except (TypeError, ValueError):
            fallback = DEFAULT_ANALYSIS_SETTINGS.get(self.setting_key)
            return fallback[0] if fallback else 0

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "property_code":   self.property_code,
            "setting_key":     self.setting_key,
            "setting_value":   self.typed_value(),
            "value_type":      self.value_type,
            "description":     self.description,
            "updated_at":      self.updated_at.strftime("%Y/%m/%d %H:%M") if self.updated_at else "",
            "updated_by_name": self.updated_by_name,
        }
