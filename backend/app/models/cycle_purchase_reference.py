"""
週期採購 — 部門／成本中心／會計科目主檔（獨立資料庫 cycle-purchase.db）

2026-07-10 決策：週期採購自建獨立的部門／成本中心／會計科目主檔，
不與 Budget 模組（budget_system_v1.sqlite，且該模組本身也沒有成本中心
的概念）或 reference_data.py 的 Company/RefDepartment（portal.db，供
合約模組使用）關聯。三套主檔目前彼此獨立、不同步；若日後要整合，
需要另外規劃資料對照，不在本次範圍內。
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.cycle_purchase_database import CyclePurchaseBase


class CyclePurchaseDepartment(CyclePurchaseBase):
    """週期採購部門主檔（週期採購自建，不等於 Budget／Contract 模組的部門主檔）"""
    __tablename__ = "cycle_purchase_departments"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    company        = Column(String(50),  nullable=False, comment="公司別")
    dept_code      = Column(String(30),  nullable=False, comment="部門代碼")
    dept_name      = Column(String(100), nullable=False, comment="部門名稱")
    owner_user_id  = Column(String(36),  nullable=True,
                             comment="承辦人（portal.db users.id，軟關聯）—— 2026-07-11 新增，"
                                      "供「待辦提醒」判斷登入者屬於哪個週採部門用")
    is_active      = Column(Boolean,     nullable=False, default=True)
    created_at     = Column(DateTime,    nullable=False, server_default=func.now())

    cost_centers = relationship(
        "CyclePurchaseCostCenter",
        back_populates="department",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<CyclePurchaseDepartment id={self.id} {self.company}/{self.dept_name}>"


class CyclePurchaseCostCenter(CyclePurchaseBase):
    """週期採購成本中心主檔"""
    __tablename__ = "cycle_purchase_cost_centers"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(
        Integer,
        ForeignKey("cycle_purchase_departments.id", ondelete="CASCADE"),
        nullable=False,
    )
    cc_code    = Column(String(30),  nullable=False, comment="成本中心代碼")
    cc_name    = Column(String(100), nullable=False, comment="成本中心名稱")
    is_active  = Column(Boolean,     nullable=False, default=True)
    created_at = Column(DateTime,    nullable=False, server_default=func.now())

    department = relationship("CyclePurchaseDepartment", back_populates="cost_centers")

    def __repr__(self):
        return f"<CyclePurchaseCostCenter id={self.id} {self.cc_name}>"


class CyclePurchaseAccountCode(CyclePurchaseBase):
    """週期採購會計科目主檔"""
    __tablename__ = "cycle_purchase_account_codes"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    code       = Column(String(30),  nullable=False, unique=True, comment="會計科目代碼")
    name       = Column(String(100), nullable=False, comment="會計科目名稱")
    is_active  = Column(Boolean,     nullable=False, default=True)
    created_at = Column(DateTime,    nullable=False, server_default=func.now())

    def __repr__(self):
        return f"<CyclePurchaseAccountCode id={self.id} {self.code}/{self.name}>"
