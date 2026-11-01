"""週採多公司隔離（第二輪）：料號列表、適用公司選項、排除料號候選、稽核列表（真的 PostgreSQL）

前置：週採庫已升到 cpco3，並已執行 verify_cp_company_batch1.py seed 與 verify_cp_company_services.py。
會新增一筆 OU 料號（測試資料，代碼 OU-X1）。
用法：CYCLE_PURCHASE_DATABASE_URL=... python scripts/verify_cp_company_services2.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402
from app.core.cycle_purchase_database import CyclePurchaseSessionLocal  # noqa: E402
from app.services import cycle_purchase_service as svc  # noqa: E402
from app.services import cycle_purchase_audit_service as audit_svc  # noqa: E402

FAILS = 0


def check(desc, cond, detail=""):
    global FAILS
    FAILS += 0 if cond else 1
    print("PASS" if cond else "FAIL", desc, detail)


def main() -> int:
    db = CyclePurchaseSessionLocal()
    try:
        exists = db.execute(text("SELECT 1 FROM cycle_purchase_items WHERE item_code='OU-X1'")).scalar()
        if not exists:
            from verify_cp_company_batch1 import _conn, _insert  # noqa: E402
            from psycopg2.extras import RealDictCursor  # noqa: E402
            conn = _conn(); conn.autocommit = False
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SET session_replication_role = replica")
            _insert(cur, "cycle_purchase_items", {"item_code": "OU-X1", "item_name": "日曜測試料號",
                                                  "company_code": "OU", "is_active": True})
            conn.commit(); conn.close()

        ch_codes = {i.item_code for i in svc.list_items(db, company_code="CH", per_page=200)[0]}
        ou_codes = {i.item_code for i in svc.list_items(db, company_code="OU", per_page=200)[0]}
        check("料號列表 CH 不含日曜料號 OU-X1", "OU-X1" not in ch_codes and "CH-A" in ch_codes, f"CH={sorted(ch_codes)}")
        check("料號列表 OU 只含日曜料號", "OU-X1" in ou_codes and "CH-A" not in ou_codes, f"OU={sorted(ou_codes)}")

        db.execute(text("UPDATE cycle_purchase_departments SET is_active=true WHERE dept_name IN ('客服部','工務部')"))
        db.commit()  # 測試用：適用公司只列啟用中的部門
        opts_none = svc.get_cycle_options(db, companies_filter=[])
        check("適用公司：沒有任何可見公司時回傳空清單", opts_none["companies"] == [], f"{opts_none['companies']}")

        opts_ou = svc.get_cycle_options(db, companies_filter=["OU"])
        check("適用公司：OU 使用者只看到日曜天地（不含春大直）", opts_ou["companies"] == ["日曜天地"], f"{opts_ou['companies']}")

        check("排除料號候選：空公司清單回傳空（不再視為不篩選）",
              svc.list_exclude_item_candidates(db, [], []) == [])

        ch_audit = audit_svc.list_audit_log(db, company_code="CH")
        ou_audit = audit_svc.list_audit_log(db, company_code="OU")
        check("稽核列表：CH 使用者看得到 CH 的稽核紀錄", len(ch_audit) >= 1, f"n={len(ch_audit)}")
        check("稽核列表：OU 使用者看不到 CH 的稽核紀錄", all(r.company_code == "OU" for r in ou_audit),
              f"n={len(ou_audit)}")
        db.rollback()
    finally:
        db.close()
    print("RESULT:", "ALL PASS" if FAILS == 0 else f"{FAILS} FAILED")
    return FAILS


if __name__ == "__main__":
    sys.exit(main())
