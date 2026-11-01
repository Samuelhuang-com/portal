"""週採多公司隔離 第二批（cpco2）唯一鍵驗證

前置：測試庫已依 verify_cp_company_batch1.py seed 寫入資料，並升到 cpco1 或 cpco2。
用法：
  python -m alembic -c alembic_cp.ini upgrade head
  python scripts/verify_cp_company_batch2.py
每項檢查都在獨立交易中執行，失敗的插入會被回滾，不影響其他檢查。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from verify_cp_company_batch1 import _conn, _fill_required  # noqa: E402

import psycopg2  # noqa: E402
from psycopg2.extras import RealDictCursor  # noqa: E402


def _try_insert(conn, table, values, expect_ok, desc):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    row = _fill_required(cur, table, values)
    cols = list(row)
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})"
    cur.execute("SAVEPOINT sp")
    try:
        cur.execute(sql, [row[c] for c in cols])
        ok = True
    except psycopg2.IntegrityError:
        ok = False
    cur.execute("ROLLBACK TO SAVEPOINT sp" if not ok else "RELEASE SAVEPOINT sp")
    passed = ok == expect_ok
    print(("PASS" if passed else "FAIL"), desc, f"inserted={ok} expect={expect_ok}")
    return 0 if passed else 1


def _id(cur, sql, args):
    cur.execute(sql, args)
    return list(cur.fetchone().values())[0]


def main() -> int:
    conn = _conn()
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SET session_replication_role = replica")  # 只驗唯一鍵，不驗外鍵
    fails = 0

    item_ch = _id(cur, "SELECT id FROM cycle_purchase_items WHERE item_code='CH-A'", ())
    d_ch = _id(cur, "SELECT id FROM cycle_purchase_departments WHERE dept_name='工務部'", ())
    d_ou = _id(cur, "SELECT id FROM cycle_purchase_departments WHERE dept_name='客服部'", ())
    vendor_ou = _id(cur, "SELECT id FROM cycle_purchase_vendors WHERE vendor_code='V-OU'", ())
    cycle_id = 1

    # 1. 料號對照：同公司同部門重複 → 擋；不同公司 → 允許
    # 種子資料中 CH-A 已有 (CH, d_ch)、(OU, d_ou)
    fails += _try_insert(conn, "cycle_purchase_item_mappings",
        {"item_id": item_ch, "company": "春大直", "company_code": "CH", "department_id": d_ch},
        False, "料號對照：同公司同部門重複被擋")
    fails += _try_insert(conn, "cycle_purchase_item_mappings",
        {"item_id": item_ch, "company": "台中", "company_code": "HO", "department_id": d_ch},
        True, "料號對照：不同公司代碼（HO）允許")

    # 2. 會計科目：同代碼跨公司允許，同公司重複擋
    fails += _try_insert(conn, "cycle_purchase_account_codes",
        {"code": "ACC-1", "name": "重複", "company_code": "CH"}, False, "會計科目：同公司同代碼被擋")
    fails += _try_insert(conn, "cycle_purchase_account_codes",
        {"code": "ACC-1", "name": "日曜版", "company_code": "OU"}, True, "會計科目：跨公司同代碼允許")

    # 3. 採購單部分唯一索引：已取消不擋重開，有效單仍擋重複
    cur.execute("""UPDATE cycle_purchase_pos SET status='open', cycle_id=%s, period_label='2026-10',
                   company_code='OU', vendor_id=%s WHERE po_no='PO-OU-1'""", (cycle_id, vendor_ou))
    fails += _try_insert(conn, "cycle_purchase_pos",
        {"cycle_id": cycle_id, "period_label": "2026-10", "company_code": "OU",
         "vendor_id": vendor_ou, "company": "日曜天地", "status": "cancelled"},
        True, "採購單：已取消的單不佔用唯一性（修正 PG 無條件索引）")
    fails += _try_insert(conn, "cycle_purchase_pos",
        {"cycle_id": cycle_id, "period_label": "2026-10", "company_code": "OU",
         "vendor_id": vendor_ou, "company": "日曜天地", "status": "open"},
        False, "採購單：同期別同廠商仍只允許一張有效單")

    conn.rollback()  # 全部檢查皆不保留
    print("RESULT:", "ALL PASS" if fails == 0 else f"{fails} FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(main())
