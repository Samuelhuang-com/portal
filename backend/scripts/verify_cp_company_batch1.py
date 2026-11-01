"""週採多公司隔離 第一批（cpco1）回填驗證腳本

用途：在「已升到 cpccdefault」的週採測試庫上，塞入含各種 company 字串的資料，
執行 `alembic -c alembic_cp.ini upgrade head` 之後，檢查 company_code 回填結果。

用法（PostgreSQL 測試區，不要對正式區執行）：
  set CYCLE_PURCHASE_DATABASE_URL=postgresql+psycopg2://user:pw@host/cp_test
  python -m alembic -c alembic_cp.ini upgrade cpccdefault
  python scripts/verify_cp_company_batch1.py seed
  python -m alembic -c alembic_cp.ini upgrade head
  python scripts/verify_cp_company_batch1.py check
"""
import os
import sys
import uuid

import psycopg2
from psycopg2.extras import RealDictCursor

URL = os.environ.get("CYCLE_PURCHASE_DATABASE_URL", "")


def _dsn(url: str) -> str:
    # postgresql+psycopg2://user:pw@host/db?host=/socket  →  libpq dsn
    from urllib.parse import urlparse, parse_qs, unquote
    u = urlparse(url.replace("postgresql+psycopg2://", "postgresql://"))
    q = parse_qs(u.query)
    parts = [f"dbname={u.path.lstrip('/')}"]
    if u.username: parts.append(f"user={unquote(u.username)}")
    if u.password: parts.append(f"password={unquote(u.password)}")
    host = q.get("host", [u.hostname or ""])[0]
    if host: parts.append(f"host={host}")
    if u.port: parts.append(f"port={u.port}")
    return " ".join(parts)


def _conn():
    if "postgresql" not in URL:
        sys.exit("請設定 CYCLE_PURCHASE_DATABASE_URL 為 PostgreSQL")
    return psycopg2.connect(_dsn(URL))


def _fill_required(cur, table: str, values: dict) -> dict:
    """補上所有 NOT NULL 且無預設值的欄位（測試用虛擬值）。"""
    cur.execute("""SELECT column_name, data_type, column_default, is_nullable
                   FROM information_schema.columns
                   WHERE table_name = %s AND table_schema = current_schema()""", (table,))
    out = dict(values)
    for col in cur.fetchall():
        name = col["column_name"]
        if name in out or col["is_nullable"] == "YES" or col["column_default"] is not None:
            continue
        dt = col["data_type"]
        if dt in ("character varying", "text", "character"):
            out[name] = "t" + uuid.uuid4().hex[:10]
        elif dt in ("integer", "bigint", "smallint", "numeric"):
            out[name] = 1
        elif dt == "boolean":
            out[name] = False
        elif dt.startswith("timestamp"):
            out[name] = "2026-10-31"
        elif dt == "date":
            out[name] = "2026-10-31"
        else:
            out[name] = "t"
    return out


def _insert(cur, table: str, values: dict) -> int:
    row = _fill_required(cur, table, values)
    cols = list(row)
    cur.execute(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) RETURNING id",
        [row[c] for c in cols],
    )
    return cur.fetchone()["id"]


def seed() -> None:
    conn = _conn(); conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)
    # 測試資料允許違反外鍵（只為驗證回填邏輯）
    cur.execute("SET session_replication_role = replica")
    cat = _insert(cur, "cycle_purchase_categories", {"company": "春大直", "major_code": "M1",
                                                     "mid_code": "M1", "sub_code": "S1"})
    d_ch = _insert(cur, "cycle_purchase_departments", {"company": "春大直", "dept_name": "工務部"})
    d_ou = _insert(cur, "cycle_purchase_departments", {"company": "日曜天地", "dept_name": "客服部"})
    d_lq = _insert(cur, "cycle_purchase_departments", {"company": "樂群", "dept_name": "行政部"})
    d_x  = _insert(cur, "cycle_purchase_departments", {"company": "不存在公司", "dept_name": "神秘部"})
    cc_x = _insert(cur, "cycle_purchase_cost_centers", {"department_id": d_x, "cc_code": "CCX", "cc_name": "X"})
    cc_ou = _insert(cur, "cycle_purchase_cost_centers", {"department_id": d_ou, "cc_code": "CCO", "cc_name": "O"})
    vendor_ou = _insert(cur, "cycle_purchase_vendors", {"vendor_code": "V-OU", "vendor_name": "OU廠"})
    vendor_none = _insert(cur, "cycle_purchase_vendors", {"vendor_code": "V-NONE", "vendor_name": "無單"})
    item_ch = _insert(cur, "cycle_purchase_items", {"item_code": "CH-A", "item_name": "A", "category_id": cat})
    item_free = _insert(cur, "cycle_purchase_items", {"item_code": "FREE-B", "item_name": "B", "category_id": cat})
    _insert(cur, "cycle_purchase_item_mappings", {"item_id": item_ch, "company": "春大直", "department_id": d_ch})
    _insert(cur, "cycle_purchase_item_mappings", {"item_id": item_ch, "company": "日曜天地", "department_id": d_ou})
    po_ou = _insert(cur, "cycle_purchase_pos", {"company": "日曜天地", "vendor_id": vendor_ou, "po_no": "PO-OU-1"})
    po_x = _insert(cur, "cycle_purchase_pos", {"company": "不存在公司", "vendor_id": vendor_none, "po_no": "PO-X-1"})
    _insert(cur, "cycle_purchase_receiving", {"po_id": po_ou, "receiving_no": "RC-OU-1"})
    _insert(cur, "cycle_purchase_payments", {"po_id": po_ou, "payment_no": "PAY-OU-1"})
    _insert(cur, "cycle_purchase_receiving", {"po_id": po_x, "receiving_no": "RC-X-1"})
    _insert(cur, "cycle_purchase_account_codes", {"code": "ACC-1", "name": "科目"})
    _insert(cur, "cycle_purchase_audit_logs", {"event_type": "seed", "document_type": "seed"})
    # 供 check 使用的固定 id 記在環境外：以 po_no／代碼查詢即可
    cur.execute("SET session_replication_role = origin")
    conn.commit()
    print("seed OK")


EXPECT = [
    # (說明, SQL, 期望值)
    ("料號有春大直對照 → CH", "SELECT company_code FROM cycle_purchase_items WHERE item_code='CH-A'", "CH"),
    ("料號無對照 → 預設 CH", "SELECT company_code FROM cycle_purchase_items WHERE item_code='FREE-B'", "CH"),
    ("部門 日曜天地 → OU", "SELECT company_code FROM cycle_purchase_departments WHERE dept_name='客服部'", "OU"),
    ("部門 樂群（別名）→ CH", "SELECT company_code FROM cycle_purchase_departments WHERE dept_name='行政部'", "CH"),
    ("部門 無法對照 → NULL（第三批會擋）", "SELECT company_code FROM cycle_purchase_departments WHERE dept_name='神秘部'", None),
    ("成本中心跟隨部門 → OU", "SELECT company_code FROM cycle_purchase_cost_centers WHERE cc_code='CCO'", "OU"),
    ("成本中心部門無法對照 → NULL", "SELECT company_code FROM cycle_purchase_cost_centers WHERE cc_code='CCX'", None),
    ("廠商跟隨最近採購單 → OU", "SELECT company_code FROM cycle_purchase_vendors WHERE vendor_code='V-OU'", "OU"),
    ("廠商無採購單 → 預設 CH", "SELECT company_code FROM cycle_purchase_vendors WHERE vendor_code='V-NONE'", "CH"),
    ("採購單 日曜天地 → OU", "SELECT company_code FROM cycle_purchase_pos WHERE po_no='PO-OU-1'", "OU"),
    ("採購單 無法對照 → NULL", "SELECT company_code FROM cycle_purchase_pos WHERE po_no='PO-X-1'", None),
    ("驗收單跟隨採購單 → OU", "SELECT company_code FROM cycle_purchase_receiving WHERE receiving_no='RC-OU-1'", "OU"),
    ("付款跟隨採購單 → OU", "SELECT company_code FROM cycle_purchase_payments WHERE payment_no='PAY-OU-1'", "OU"),
    ("會計科目預設 CH", "SELECT company_code FROM cycle_purchase_account_codes WHERE code='ACC-1'", "CH"),
    ("公司主檔含三筆種子", "SELECT COUNT(*)::text AS c FROM cycle_purchase_companies", "3"),
]


def check() -> int:
    conn = _conn()
    cur = conn.cursor()
    failed = 0
    for desc, sql, expect in EXPECT:
        cur.execute(sql)
        row = cur.fetchone()
        got = row[0] if row else None
        ok = (got == expect)
        failed += 0 if ok else 1
        print(("PASS" if ok else "FAIL"), desc, f"got={got!r} expect={expect!r}")
    print("RESULT:", "ALL PASS" if failed == 0 else f"{failed} FAILED")
    return failed


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "seed":
        seed()
    else:
        sys.exit(check())
