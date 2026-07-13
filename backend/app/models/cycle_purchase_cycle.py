"""
週期採購 — 週期設定（獨立資料庫 cycle-purchase.db）

第一層設計：定義請購規則、頻率、開放天數、截止日、適用品類與適用單位。

2026-07-11：原本第二層「週期採購批次」已拿掉（見 cycle_purchase_request.py
開頭說明），請購單改成直接掛在這裡的 cycle_id + 期別標籤（period_label）。
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, func

from app.core.cycle_purchase_database import CyclePurchaseBase


class CyclePurchaseCycle(CyclePurchaseBase):
    """週期採購週期設定（第一層：規則）"""
    __tablename__ = "cycle_purchase_cycles"

    id                     = Column(Integer, primary_key=True, autoincrement=True)
    cycle_code             = Column(String(30),  nullable=False, unique=True, comment="週期代碼")
    cycle_name             = Column(String(100), nullable=False, comment="週期名稱")
    frequency              = Column(String(20),  nullable=False,
                                     comment="頻率：monthly | biweekly | bimonthly | custom")
    open_rule              = Column(String(200), nullable=True,  comment="開放規則說明（如：每月第幾日）")
    close_rule             = Column(String(200), nullable=True,  comment="截止規則說明（如：開放後 N 天）")
    applicable_categories  = Column(Text, nullable=True, comment="適用品類（逗號分隔）")
    applicable_scope       = Column(Text, nullable=True, comment="適用公司／部門（逗號分隔，或 all）")
    auto_generate          = Column(Boolean, nullable=False, default=False,
                                     comment="是否自動產生本期請購單（第一版預設人工按鈕觸發，日後可接排程）")
    reminder_rule          = Column(Text, nullable=True, comment="提醒規則說明")
    status                 = Column(String(20), nullable=False, default="active",
                                     comment="狀態：active | inactive | paused")
    notes                  = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CyclePurchaseCycle id={self.id} code={self.cycle_code} name={self.cycle_name}>"
