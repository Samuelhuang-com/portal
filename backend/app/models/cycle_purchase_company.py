"""週採公司主檔（週採庫內）

與主庫 companies 以「公司代碼」對應（CH 春大直／OU 日曜天地／HO 台中）。
週採庫與主庫是不同資料庫，無法建立跨庫外鍵，因此本表為週採自有主檔。
"""
from sqlalchemy import Boolean, Column, DateTime, String, func

from app.core.cycle_purchase_database import CyclePurchaseBase


class CyclePurchaseCompany(CyclePurchaseBase):
    __tablename__ = "cycle_purchase_companies"

    code       = Column(String(10), primary_key=True, comment="公司代碼（CH／OU／HO）")
    name       = Column(String(100), nullable=False, unique=True, comment="公司名稱（週採慣用字串）")
    is_active  = Column(Boolean, nullable=False, default=True, comment="是否啟用")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
