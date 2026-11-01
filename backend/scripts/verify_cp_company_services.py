"""週採多公司隔離：服務層列表過濾與跨公司建立防護（真的 PostgreSQL）

前置：週採庫已升到 cpco3，並依 verify_cp_company_batch1.py seed 寫入資料
（PO-OU-1 屬 OU；PO-X-1 屬 CH，因 batch3 測試補值為 CH）。
用法：CYCLE_PURCHASE_DATABASE_URL=... python scripts/verify_cp_company_services.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402
from app.core.cycle_purchase_database import CyclePurchaseSessionLocal  # noqa: E402
from app.services import cycle_purchase_service as svc  # noqa: E402
from app.services import cycle_purchase_po_service as po_svc  # noqa: E402

FAILS = 0


def check(desc, cond, detail=""):
    global FAILS
    FAILS += 0 if cond else 1
    print("PASS" if cond else "FAIL", desc, detail)


class P:
    """模擬 pydantic payload：只需要 model_dump()"""
    def __init__(self, **kw):
        self._d = kw
    def model_dump(self):
        return dict(self._d)
    def __getattr__(self, k):
        try:
            return self._d[k]
        except KeyError:
            raise AttributeError(k)


def main() -> int:
    db = CyclePurchaseSessionLocal()
    try:
        ou_pos = {r.po_no for r in po_svc.list_pos(db, company="OU")}
        ch_pos = {r.po_no for r in po_svc.list_pos(db, company="CH")}
        check("採購單列表 OU 只含 OU 的單", "PO-OU-1" in ou_pos and "PO-X-1" not in ou_pos, f"OU={sorted(ou_pos)}")
        check("採購單列表 CH 只含 CH 的單", "PO-X-1" in ch_pos and "PO-OU-1" not in ch_pos, f"CH={sorted(ch_pos)}")

        dept_ou = db.execute(text("SELECT id FROM cycle_purchase_departments WHERE dept_name='客服部'")).scalar()
        dept_ch = db.execute(text("SELECT id FROM cycle_purchase_departments WHERE dept_name='工務部'")).scalar()

        try:
            svc.create_department(db, P(company="日曜天地", dept_code="X-1", dept_name="跨公司",
                                        is_active=True, owner_user_id=None), "CH")
            check("建立部門：payload 公司與目前公司不一致應拒絕", False)
        except ValueError as e:
            check("建立部門：payload 公司與目前公司不一致應拒絕", True, f"({e})")
        db.rollback()

        try:
            svc.create_cost_center(db, P(department_id=dept_ou, cc_code="CC-X", cc_name="跨公司",
                                         is_default=False, is_active=True), "CH")
            check("建立成本中心：部門屬於另一公司應拒絕", False)
        except ValueError as e:
            check("建立成本中心：部門屬於另一公司應拒絕", True, f"({e})")
        db.rollback()

        cat_ch = db.execute(text("SELECT id FROM cycle_purchase_categories LIMIT 1")).scalar()
        db.execute(text("UPDATE cycle_purchase_categories SET is_active=true WHERE id=:i"), {"i": cat_ch})
        db.commit()  # 測試用：確保分類啟用，讓檢查真正走到公司比對
        try:
            svc.create_item(db, P(item_code="X-ITEM-1", item_name="跨公司", category_id=cat_ch,
                                  is_active=True, is_cycle_item=False), "OU")
            check("建立料號：分類屬於另一公司應拒絕（分類為 CH，料號指定 OU）", False)
        except ValueError as e:
            check("建立料號：分類屬於另一公司應拒絕", "不屬於此公司別" in str(e), f"({e})")
        db.rollback()
    finally:
        db.close()
    print("RESULT:", "ALL PASS" if FAILS == 0 else f"{FAILS} FAILED")
    return FAILS


if __name__ == "__main__":
    sys.exit(main())
