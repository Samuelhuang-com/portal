"""
週期採購 — 類別主檔（三層編碼，獨立資料庫 cycle-purchase.db）

2026-08-18 新增（依 Samuel 指示：「增加『類別主檔』設定，先按上述建立，
未來直接連結」）。

────────────────────────────────────────────────────────────────
為什麼要有這張表
────────────────────────────────────────────────────────────────
在此之前，「類別」只是 `cycle_purchase_items.category` 上的一個自由文字欄位，
沒有主檔。實際帶來三個問題：

  1. 週期設定的「適用品類」下拉是靠 `distinct(category)` 現算的
     （見 cycle_purchase_service.get_cycle_options），字串打錯一個字
     就變成一個新品類，而且沒有任何地方看得出來錯在哪。
  2. 類別跟部門的關係只能從「料號 → 對照表 → 部門」繞著推導，
     2026-08-17 才被迫在下拉選項標籤上臨時附加部門名稱來救急。
  3. 料號編碼規則（大分類英文 + 中分類 2 碼 + 細分類 2 碼 + 流水 3 碼，
     見春大直《設料號明細表》的「編碼原則」分頁）只存在於 Excel 裡，
     Portal 完全不知道，新增料號時只能人工翻 Excel 查下一個流水號。

────────────────────────────────────────────────────────────────
三層結構怎麼存
────────────────────────────────────────────────────────────────
本表**一列 = 一個細分類（葉節點）**，大分類／中分類以反正規化欄位存在同一列，
不另外開兩張表。理由：

  - 料號的碼位本來就是固定寬度的三段（`E` + `01` + `01` + `001`），
    層級數不會再長出第四層，父子表帶來的 join 成本換不到彈性。
  - 未來 `cycle_purchase_items` 要接的是**葉節點**（category_id），
    父層只是顯示與分群用，不需要有自己的 id 被外鍵綁住。
  - 中分類／大分類名稱要改時只是同一支 UPDATE 多帶幾列，
    週期採購的類別總數是百位數，不是效能敏感的規模。

`category_name` 是「目前 `cycle_purchase_items.category` 實際存的那個字串」，
是本表與既有資料唯一的對照鍵。⚠️ 建表時**刻意不去改動 items.category 的內容**
（例如不會因為補了細分類名稱就把「文具-整理」改寫成「文具-整理-膠水」）——
週期設定的 `applicable_categories` 存的是類別字串，一改就會讓既有週期設定
篩不到料號，那是 2026-07-16 彙整單期別字串對不上的同一種病灶。補上來的細分類
名稱先存在 `sub_name`，等 items 接上 `category_id` 之後才有條件討論要不要
改顯示字串。

────────────────────────────────────────────────────────────────
department_id 為什麼可以是 NULL
────────────────────────────────────────────────────────────────
NULL ＝「不限部門（全公司共用）」。春大直的文具用品（G 系列）在
《設料號明細表》裡的分頁就叫「文具用品-所有部門需求」，本來就是各部門都會領用，
不屬於任何單一部門。對應到料號那邊的做法是「一個料號對每個部門各建一筆
mapping」（見 cycle_purchase_item.py 2026-08-18 段落），但類別主檔沒有必要
跟著複製四份——同一個類別複製四份反而會讓「適用品類」下拉出現四筆同名項目，
正是這張表要解決的問題。

E／C／S 三系列則有明確的單一部門歸屬，department_id 填實際部門。
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime,
    ForeignKey, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from app.core.cycle_purchase_database import CyclePurchaseBase


class CyclePurchaseCategory(CyclePurchaseBase):
    """週期採購類別主檔（一列 = 一個細分類葉節點）"""
    __tablename__ = "cycle_purchase_categories"
    __table_args__ = (
        # 同一家公司內，三段碼組合唯一。sub_code 為 NOT NULL（每個料號碼位本來
        # 就一定有細分類那兩碼），所以不會踩到 SQLite「NULL 彼此不相等、
        # UNIQUE 擋不住重複 NULL」的坑。
        UniqueConstraint(
            "company", "major_code", "mid_code", "sub_code",
            name="uq_cp_category_company_codes",
        ),
    )

    id            = Column(Integer, primary_key=True, autoincrement=True)
    company       = Column(String(50), nullable=False, comment="公司別（如：春大直／日曜天地）")
    department_id = Column(
        Integer,
        ForeignKey("cycle_purchase_departments.id", ondelete="RESTRICT"),
        nullable=True,
        comment="歸屬部門；NULL＝不限部門（全公司共用，如文具用品）",
    )

    major_code = Column(String(5),   nullable=False, comment="大分類代碼（E 工程／C 清潔／G 文具／S 營業用品）")
    major_name = Column(String(50),  nullable=False, comment="大分類名稱")
    mid_code   = Column(String(2),   nullable=False, comment="中分類代碼（2 碼）")
    mid_name   = Column(String(100), nullable=False, comment="中分類名稱")
    sub_code   = Column(String(2),   nullable=False, comment="細分類代碼（2 碼）")
    sub_name   = Column(String(100), nullable=True,
                         comment="細分類名稱；NULL＝來源 Excel 未命名（類別字串只到中分類）")

    category_name = Column(
        String(200), nullable=False,
        comment="類別顯示字串，等同 cycle_purchase_items.category 現存的值，"
                "是本表與既有料號資料的對照鍵（見檔頭說明，不隨 sub_name 改寫）",
    )

    serial_width = Column(
        Integer, nullable=False, default=3,
        comment="流水碼位數（春大直全系列皆為 3 碼），供「取下一個料號」計算用",
    )

    is_active  = Column(Boolean, nullable=False, default=True)
    notes      = Column(Text, nullable=True, comment="備註（含來源資料疑義說明）")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    department = relationship("CyclePurchaseDepartment")

    @property
    def code_prefix(self) -> str:
        """料號前綴（不含流水碼），如 `E0101`。"""
        return f"{self.major_code}{self.mid_code}{self.sub_code}"

    def __repr__(self):
        return (
            f"<CyclePurchaseCategory id={self.id} {self.company}/"
            f"{self.code_prefix} {self.category_name}>"
        )
