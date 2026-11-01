"""週採多公司隔離 第三批（cpco3）驗證

前置：測試庫已升到 cpco2，且已依 batch1 的 seed 寫入資料（含無法對照的 NULL 列）。
流程：
  1. upgrade head 必須被擋下，且錯誤訊息列出 NULL 的表（驗證「不猜測」）。
  2. 測試用：把 NULL 補為 CH（模擬人工確認歸屬；正式區須人工判斷，不可照抄）。
  3. upgrade head 必須成功。
  4. 14 張表的 company_code 皆為 NOT NULL。
  5. 缺 company_code 的插入必須失敗。
用法：CYCLE_PURCHASE_DATABASE_URL=... python scripts/verify_cp_company_batch3.py
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from verify_cp_company_batch1 import _conn  # noqa: E402

import psycopg2  # noqa: E402
from psycopg2.extras import RealDictCursor  # noqa: E402

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = [
    "cycle_purchase_categories", "cycle_purchase_item_mappings", "cycle_purchase_payment_allocations",
    "cycle_purchase_pos", "cycle_purchase_departments", "cycle_purchase_requests", "cycle_purchase_summary",
    "cycle_purchase_items", "cycle_purchase_cost_centers", "cycle_purchase_account_codes",
    "cycle_purchase_vendors", "cycle_purchase_receiving", "cycle_purchase_payments", "cycle_purchase_audit_logs",
]


def _alembic_upgrade():
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic_cp.ini", "upgrade", "head"],
        cwd=BACKEND, capture_output=True, text=True,
    )


def main() -> int:
    fails = 0

    r = _alembic_upgrade()
    out = (r.stdout or "") + (r.stderr or "")
    ok = r.returncode != 0 and "[cpco3]" in out
    fails += 0 if ok else 1
    print("PASS" if ok else "FAIL", "有 NULL 時第三批被擋下並列出表名", f"exit={r.returncode}")

    conn = _conn(); conn.autocommit = True
    cur = conn.cursor(cursor_factory=RealDictCursor)
    for t in TABLES:  # 測試用補值
        cur.execute(f"UPDATE {t} SET company_code='CH' WHERE company_code IS NULL")
    print("（測試用）已將 NULL 補為 CH")

    r = _alembic_upgrade()
    ok = r.returncode == 0
    fails += 0 if ok else 1
    print("PASS" if ok else "FAIL", "補值後 upgrade head 成功", f"exit={r.returncode}")
    if not ok:
        print((r.stdout or "") + (r.stderr or ""))
        return fails

    cur.execute("""SELECT table_name, is_nullable FROM information_schema.columns
                   WHERE column_name='company_code' AND table_name = ANY(%s)""", (TABLES,))
    rows = {r["table_name"]: r["is_nullable"] for r in cur.fetchall()}
    bad = [t for t in TABLES if rows.get(t) != "NO"]
    fails += 0 if not bad else 1
    print("PASS" if not bad else "FAIL", "14 張表 company_code 皆為 NOT NULL", f"不符={bad}")

    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SET session_replication_role = replica")
    cur.execute("SAVEPOINT sp")
    try:
        cur.execute("INSERT INTO cycle_purchase_departments (company, dept_code, dept_name, is_active, created_at) "
                    "VALUES ('測試', 'NOCODE-1', '無代碼', true, now())")
        inserted = True
    except psycopg2.IntegrityError:
        inserted = False
    cur.execute("ROLLBACK TO SAVEPOINT sp")
    conn.rollback()
    ok = not inserted
    fails += 0 if ok else 1
    print("PASS" if ok else "FAIL", "缺 company_code 的插入被拒絕", f"inserted={inserted}")

    print("RESULT:", "ALL PASS" if fails == 0 else f"{fails} FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(main())
