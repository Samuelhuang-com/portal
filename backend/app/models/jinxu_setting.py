"""
金旭 PMS 分析 — 分析門檻設定

規格書：docs/SPEC_jinxu_analytics.md §7.9

門檻集中管理，禁止散落在程式碼各處。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow

# ── 預設門檻（首次啟動 seed 用）──────────────────────────────────────────────

DEFAULT_SETTINGS: list[tuple[str, str, str, str]] = [
    # (key, value, value_type, 說明)
    ("net_amount_mode",           "NET",    "str",   "統計口徑：NET（淨額）/ GROSS"),
    ("deposit_alert_days",        "90",     "int",   "預收訂金未沖銷天數警示門檻"),
    ("revenue_anomaly_multiplier", "2.0",   "float", "單日營收異常倍數（vs 期間中位數）"),
    ("large_amount_threshold",    "100000", "int",   "大額交易標記門檻"),
    ("rate_gap_alert_pct",        "10.0",   "float", "訂價 vs 實收落差警示百分比"),
    ("long_stay_nights",          "7",      "int",   "長住訂房門檻（晚）"),
]

MODE_NET = "NET"
MODE_GROSS = "GROSS"


class JinxuAnalysisSetting(Base):
    """分析門檻設定（規格書 §7.9）"""

    __tablename__ = "jinxu_analysis_setting"

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_code: Mapped[str] = mapped_column(String(20), default="", index=True)
    setting_key:   Mapped[str] = mapped_column(String(50), default="", index=True)
    setting_value: Mapped[str] = mapped_column(String(200), default="")
    value_type:    Mapped[str] = mapped_column(String(10), default="str")
    description:   Mapped[str] = mapped_column(String(200), default="")

    updated_at:         Mapped[datetime] = mapped_column(DateTime, default=twnow)
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
