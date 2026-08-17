"""
週期採購 — 部門／成本中心／會計科目主檔（獨立資料庫 cycle-purchase.db）

2026-07-10 決策（已於 2026-08-17 部分反轉，見下方）：週期採購自建獨立的
部門／成本中心／會計科目主檔，不與 Budget 模組（budget_system_v1.sqlite，
且該模組本身也沒有成本中心的概念）或 reference_data.py 的 Company/
RefDepartment（portal.db，供合約模組使用）關聯。

2026-08-17 決策（與 Samuel 確認跨模組整合範圍後，反轉上面「部門」的部分，
「成本中心」「會計科目」維持獨立不變）：週期採購連續發生多次「選錯公司/
部門的品類」事故後，確認公司/部門關聯要有全站唯一真實來源，改為：

    portal.db  Company/RefDepartment（reference_data.py，真實來源）
        └─ cycle_purchase_department_sync.py ──▶ cycle_purchase_departments（本檔，鏡像）

`CyclePurchaseDepartment` 保留自己的 Integer PK 與既有 FK（`cost_centers`
等三處都靠它），只新增 `source_department_id`（見下方欄位），比照
`cycle_purchase_vendor_sync.py` 的鏡像同步模式（廠商主檔），理由相同：
跨 SQLite 檔案不能建 FK，本專案也明訂不做 ATTACH DATABASE。

同步只覆蓋 `company`／`dept_name`（來源端的真實欄位）；`dept_code`（來源
端沒有代碼概念，新增時自動帶 `DEPT-{來源id}`，之後可手動改）、
`owner_user_id`、`is_active` 都是週期採購自己維護的欄位，同步不碰。
完整比對優先序與欄位權責見 `cycle_purchase_department_sync.py` 檔頭。

「成本中心」「會計科目」這兩張表**不在**這次整合範圍內，維持 2026-07-10
的原決策（週期採購自建、不與其他模組關聯）。
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
    # 2026-08-17 新增：跨庫對照鍵，指向 portal.db RefDepartment.id（存字串，
    # 比照 CyclePurchaseVendor.source_vendor_id 的既有模式）。NULL＝這筆是
    # 週採本地自建、還沒（或不會）連結到全站公司/部門主檔，同步不會動它。
    source_department_id = Column(String(30), nullable=True, unique=True,
                                   comment="跨庫對照鍵，對應 portal.db RefDepartment.id；"
                                            "NULL=本地自建，同步不覆蓋不刪除")

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
