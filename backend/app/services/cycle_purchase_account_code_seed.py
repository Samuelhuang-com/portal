"""
週期採購 — 會計科目主檔 預設值 seed

2026-07-16 與 Samuel 確認：會計科目代碼／名稱先用預設值頂著上線，不用等
協理提供正式完整清單才能開工；之後協理提供正式清單時，直接到「會計科目
主檔」頁面（既有選單項目，見 frontend/src/pages/CyclePurchase/Masters/
AccountCodes.tsx）修改代碼／名稱即可，不影響已送出單據的歷史金額
（cycle_purchase_request_items 是逐行快照單價，不是即時關聯）。

預設 4 筆對應 0715 會議記錄確認的四大類別＋部門對應：
  工程備品 → 工程部　清潔用品 → 管理部　文具用品 → 全部門　營業用品 → 管理部/營業部
代碼採用暫定的 CPAC-xxx 格式，之後協理提供正式會計科目代碼時可直接覆蓋
（code 欄位有 unique 限制，改代碼前建議先確認沒有請購明細正在使用中）。
"""
from sqlalchemy.orm import Session

from app.models.cycle_purchase_reference import CyclePurchaseAccountCode

DEFAULT_ACCOUNT_CODES = [
    {"code": "CPAC-001", "name": "工程備品"},
    {"code": "CPAC-002", "name": "清潔用品"},
    {"code": "CPAC-003", "name": "文具用品"},
    {"code": "CPAC-004", "name": "營業用品"},
]


def seed_default_account_codes(db: Session) -> int:
    """若 cycle_purchase_account_codes 表為空，塞入預設的 4 筆會計科目。
    冪等：表裡只要已經有任何資料（不論是不是這 4 筆）就不會再動作，
    避免蓋掉協理之後手動維護的正式資料。回傳實際新增的筆數。
    """
    existing_count = db.query(CyclePurchaseAccountCode).count()
    if existing_count > 0:
        return 0

    for row in DEFAULT_ACCOUNT_CODES:
        db.add(CyclePurchaseAccountCode(code=row["code"], name=row["name"], is_active=True))
    db.commit()
    return len(DEFAULT_ACCOUNT_CODES)
