"""
週期採購 — 週期設定（獨立資料庫 cycle-purchase.db）

第一層設計：定義請購規則、頻率、開放天數、截止日、適用品類與適用單位。

2026-07-11：原本第二層「週期採購批次」已拿掉（見 cycle_purchase_request.py
開頭說明），請購單改成直接掛在這裡的 cycle_id + 期別標籤（period_label）。

2026-08-09（與 Samuel 確認，「部門範圍」+「品類接線」——規格見
docs/SPEC_cycle_purchase_dept_scope.md）：
  - **問題**：「產生本期請購單」會對範圍內公司的每一個啟用中部門各建一張空白單，
    造成「週期數 × 公司數 × 部門數」全展開。但實際上有些週採只屬於特定單位才用得到。
  - **調查發現三件事**（實際讀程式碼確認，不是推測）：
    (1) `applicable_scope` 的標籤寫「適用公司／部門」，但
        `cycle_purchase_request_service._applicable_departments()` 實際只做
        `CyclePurchaseDepartment.company.in_(...)` —— 填部門名稱會篩出 0 筆並拋錯。
        **不是「沒做」，是標籤一直在騙人。**
    (2) `applicable_categories` 從建檔以來**沒有任何 service 讀過**，純裝飾欄位。
    (3) `cycle_purchase_request_service.get_available_items()` 只按
        「公司＋部門」篩料號、**不看週期**，同一部門開幾個週期都拿到同一份料號
        清單。這是既有 bug，一併修掉。
  - **選定方案 B + D 併用**（兩者是交集，不是二選一）：
    * B —— 新增 `applicable_department_ids`，在週期設定上**明確勾選**部門。
    * D —— 再用「該公司＋該部門在此週期品類下有沒有啟用中料號」自動過濾。
      D 是**過濾器不是來源**：使用者勾了但沒料號的部門不產生，且必須在回傳訊息
      明講原因，不可靜默跳過（靜默跳過會讓買家以為系統壞了）。
  - `applicable_scope` 欄位與既有資料保留，但語意收斂為**只放公司**，前端標籤
    從「適用公司／部門」改成「適用公司」。
  - ⚠️ `applicable_scope`／`applicable_categories` 都是跟主檔做字串比對，與彙整單
    2026-07-16 踩過的「期別字串打不一致 → 查到 0 筆 → 誤以為沒資料」是同一種病灶。
    因此前端一律改成從主檔 distinct 值取選項的 multi-select，**不讓使用者手打**
    （選項 API：GET /cycle-purchase/options/companies、/options/categories）。

2026-08-16（新增 `excluded_item_ids`，與 Samuel 確認「品類底下要能排除個別料號」
的三個方案 A/B/C，選了 B）：
  - `applicable_categories` 是「整包」語意：選了一個品類＝底下全部啟用中料號都算，
    以後這個品類新增料號會自動涵蓋，行為與改版前一致。
  - `excluded_item_ids` 是**例外排除清單**，不是白名單：只用來手動排除品類整包
    裡少數幾筆不想要的料號，不影響「品類新增料號自動涵蓋」這個既有行為。
  - 三處比對邏輯（`resolve_applicable_departments()`／`_has_available_items()`／
    `get_available_items()`）都要在品類過濾之後，再排除掉這裡列出的 item id，
    否則「D 層判斷會不會產生空白單」跟「請購單可選料號清單」會兜不起來
    （這條一致性要求本來就是既有規範，見 `_has_available_items()` docstring）。
  - 前端候選清單（排除料號下拉的選項）另開端點
    `GET /cycles/exclude-item-candidates?companies=&categories=`，依「適用公司」
    ＋「適用品類」現算，不是固定清單——避免使用者排除了一筆料號，之後改了
    適用品類，排除清單裡卻殘留一筆已經不相干公司/品類的料號 id。
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
    applicable_categories  = Column(Text, nullable=True,
                                     comment="適用品類（逗號分隔，對應 cycle_purchase_items.category；"
                                              "空值＝不限品類。2026-08-09 起真正被程式使用，"
                                              "見 request_service 的部門解析與可選料號篩選）")
    applicable_scope       = Column(Text, nullable=True,
                                     comment="適用公司（逗號分隔，或 all／空值＝不限）。"
                                              "2026-08-09 語意收斂：這欄只放公司，部門改用 "
                                              "applicable_department_ids；改版前標籤誤植為"
                                              "「適用公司／部門」，但程式從來只比對公司")
    applicable_department_ids = Column(Text, nullable=True,
                                        comment="適用部門（逗號分隔的 cycle_purchase_departments.id）；"
                                                 "**空值＝適用公司底下的全部啟用中部門**（舊資料自動相容）。"
                                                 "2026-08-09 新增，見上方 class 註解方案 B")
    excluded_item_ids      = Column(Text, nullable=True,
                                     comment="從適用品類整包中手動排除的料號（逗號分隔的 "
                                              "cycle_purchase_items.id）；空值＝不排除任何料號。"
                                              "2026-08-16 新增，是例外排除清單不是白名單，"
                                              "見上方 class 註解")
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
