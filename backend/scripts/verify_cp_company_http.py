"""週採多公司隔離：HTTP 層端到端測試（TestClient 呼叫真正的路由）

前置：
  - 主庫 DATABASE_URL 為「剛建好、空的」測試庫（本腳本會寫入 t_ 前綴的測試使用者）。
  - 週採庫 CYCLE_PURCHASE_DATABASE_URL 已升到 cpco3，且已依 batch1 seed、services/services2 寫入資料。
用法：
  DATABASE_URL=... CYCLE_PURCHASE_DATABASE_URL=... python scripts/verify_cp_company_http.py
"""
import os
import sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import verify_cp_company_scope as scope_setup  # noqa: E402
import app.dependencies as deps  # noqa: E402
import app.services.cycle_purchase_company_scope as scope_mod  # noqa: E402
from app.main import app  # noqa: E402
from app.core.database import get_db, SessionLocal  # noqa: E402
from app.core.cycle_purchase_database import get_cycle_purchase_db, CyclePurchaseSessionLocal  # noqa: E402

BASE = "/api/v1/cycle-purchase"
CP_PERMS = ["cycle_purchase_view", "cycle_purchase_admin", "cycle_purchase_buyer", "cycle_purchase_close",
            "cycle_purchase_finance", "cycle_purchase_receive", "cycle_purchase_report",
            "cycle_purchase_request", "cycle_purchase_vendor_backfill"]
FAILS = 0


def check(desc, cond, detail=""):
    global FAILS
    FAILS += 0 if cond else 1
    print("PASS" if cond else "FAIL", desc, detail)


def _gen_main():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _gen_cp():
    db = CyclePurchaseSessionLocal()
    try:
        yield db
    finally:
        db.close()


def main() -> int:
    ids = scope_setup.setup_main()   # 建立 t_u_ch（CH）、t_u_ou（OU）、t_u_none、t_u_mix
    cur_user = {"u": None}

    perms = {"list": CP_PERMS}
    company_perms = {ids["u_ch"]: ["cycle_purchase_company_ch"], ids["u_ou"]: ["cycle_purchase_company_ou"]}
    deps.get_user_permissions = lambda uid, db: ["*"] if cur_user.get("admin") else list(perms["list"]) + company_perms.get(uid, [])
    scope_mod.get_user_permissions = deps.get_user_permissions

    app.dependency_overrides[get_db] = _gen_main
    app.dependency_overrides[get_cycle_purchase_db] = _gen_cp
    app.dependency_overrides[deps.get_current_user] = lambda: cur_user["u"]

    cp = CyclePurchaseSessionLocal()
    po_ou = cp.execute(text("SELECT id FROM cycle_purchase_pos WHERE po_no='PO-OU-1'")).scalar()
    po_ch = cp.execute(text("SELECT id FROM cycle_purchase_pos WHERE po_no='PO-X-1'")).scalar()
    item_ou = cp.execute(text("SELECT id FROM cycle_purchase_items WHERE item_code='OU-X1'")).scalar()
    item_ch = cp.execute(text("SELECT id FROM cycle_purchase_items WHERE item_code='CH-A'")).scalar()
    dept_ou = cp.execute(text("SELECT id FROM cycle_purchase_departments WHERE dept_name='客服部'")).scalar()
    cp.close()
    assert po_ou and po_ch and item_ou and item_ch and dept_ou, "請先執行 batch1 seed 與 services 測試"
    # 日曜請購單（測試資料）：用於驗證聚合端點不會把它顯示給春大直使用者
    from verify_cp_company_batch1 import _conn, _insert  # noqa: E402
    from psycopg2.extras import RealDictCursor  # noqa: E402
    _c = _conn(); _c.autocommit = False; _cur = _c.cursor(cursor_factory=RealDictCursor)
    _cur.execute("SET session_replication_role = replica")
    _cur.execute("SELECT 1 FROM cycle_purchase_requests WHERE request_no='RQ-OU-TEST'")
    if _cur.fetchone() is None:
        _insert(_cur, "cycle_purchase_requests", {"request_no": "RQ-OU-TEST", "cycle_id": 1, "period_label": "2026-10",
                "department_id": dept_ou, "company": "日曜天地", "company_code": "OU", "status": "open",
                "is_closed": False, "is_summarized": False})
    _c.commit(); _c.close()
    _c = _conn(); _c.autocommit = False; _cur = _c.cursor(cursor_factory=RealDictCursor)
    _cur.execute("SET session_replication_role = replica")
    _cur.execute("SELECT 1 FROM cycle_purchase_cycles WHERE id=1")
    if _cur.fetchone() is None:
        _insert(_cur, "cycle_purchase_cycles", {"id": 1, "cycle_code": "CY-HTTP-TEST", "cycle_name": "HTTP 測試週期"})
    _c.commit(); _c.close()
    cp = CyclePurchaseSessionLocal()
    req_ou = cp.execute(text("SELECT id FROM cycle_purchase_requests WHERE request_no='RQ-OU-TEST'")).scalar()

    client = TestClient(app)
    ch = SimpleNamespace(id=ids["u_ch"], tenant_id=ids["tenant"], full_name="CH 使用者")
    ou = SimpleNamespace(id=ids["u_ou"], tenant_id=ids["tenant"], full_name="OU 使用者")

    # ── 春大直（CH）使用者 ──
    cur_user["u"] = ch
    r = client.get(f"{BASE}/pos")
    check("CH 採購單列表 200", r.status_code == 200, f"status={r.status_code}")
    check("CH 採購單列表不含日曜單 PO-OU-1", "PO-OU-1" not in r.text, "")
    check("CH 指定 co=OU → 403", client.get(f"{BASE}/pos", params={"co": "OU"}).status_code == 403)
    check("CH 讀取日曜採購單 /pos/{id} → 404", client.get(f"{BASE}/pos/{po_ou}").status_code == 404)
    check("CH 讀取自家採購單 /pos/{id} → 200", client.get(f"{BASE}/pos/{po_ch}").status_code == 200)
    check("CH 料號列表不含 OU-X1", "OU-X1" not in client.get(f"{BASE}/items", params={"per_page": 200}).text)
    check("CH 讀取日曜料號 /items/{id} → 404", client.get(f"{BASE}/items/{item_ou}").status_code == 404)
    dep_text = client.get(f"{BASE}/masters/departments").text
    check("CH 部門主檔不含日曜部門（客服部）", "客服部" not in dep_text, f"status={client.get(f'{BASE}/masters/departments').status_code}")
    r = client.post(f"{BASE}/receiving", json={"po_id": po_ou, "received_date": "2026-10-31"})
    check("CH 對日曜採購單建立驗收 → 404", r.status_code == 404, f"status={r.status_code}")
    r = client.post(f"{BASE}/requests", json={"cycle_id": 1, "period_label": "2026-10", "department_id": dept_ou})
    check("CH 對日曜部門建立請購單 → 404（不得寫入）", r.status_code == 404, f"status={r.status_code}")

    # ── 日曜（OU）使用者 ──
    cur_user["u"] = ou
    check("OU 料號列表含 OU-X1", "OU-X1" in client.get(f"{BASE}/items", params={"per_page": 200}).text)
    check("OU 料號列表不含 CH-A", "CH-A" not in client.get(f"{BASE}/items", params={"per_page": 200}).text)
    check("OU 讀取春大直料號 /items/{id} → 404", client.get(f"{BASE}/items/{item_ch}").status_code == 404)
    check("OU 讀取日曜採購單 /pos/{id} → 200", client.get(f"{BASE}/pos/{po_ou}").status_code == 200)
    check("OU 讀取春大直採購單 /pos/{id} → 404", client.get(f"{BASE}/pos/{po_ch}").status_code == 404)
    check("OU 適用公司選項不含春大直", "春大直" not in client.get(f"{BASE}/cycles/options").text)
    check("OU 稽核列表 200", client.get(f"{BASE}/audit-log").status_code == 200)

    # ── 聚合端點：春大直使用者看不到日曜的資料 ──
    cur_user["u"] = ch
    for path in ["/requests/todos", "/requests/my-period", "/requests/generate-status", "/requests",
                 "/summary/pending-requests", "/summary/ragic-pushed/date-range"]:
        rr = client.get(f"{BASE}{path}")
        check(f"CH {path} 200 且不含日曜請購單", rr.status_code == 200 and "RQ-OU-TEST" not in rr.text,
              f"status={rr.status_code}")
    rr = client.get(f"{BASE}/requests/generate-preview", params={"cycle_id": 1})
    check("CH 產生預覽不含日曜部門（客服部）", rr.status_code == 200 and "客服部" not in rr.text, f"status={rr.status_code} {rr.text[:120]}")
    check("CH 複製候選：日曜部門 → 404", client.get(f"{BASE}/requests/copy-candidates",
          params={"cycle_id": 1, "department_id": dept_ou}).status_code == 404)
    check("CH 讀取日曜請購單 /requests/{id} → 404", client.get(f"{BASE}/requests/{req_ou}").status_code == 404)
    cur_user["u"] = ou
    rr = client.get(f"{BASE}/requests")
    check("OU 請購單列表含日曜請購單", rr.status_code == 200 and "RQ-OU-TEST" in rr.text, f"status={rr.status_code}")

    # ── 第四輪：部門連結選項、週期設定 ──
    cur_user["u"] = ch
    from sqlalchemy import create_engine  # noqa: E402
    main_url = os.environ["DATABASE_URL"]
    eng = create_engine(main_url)
    with eng.begin() as mc:
        mc.execute(text("UPDATE departments SET is_active = true WHERE name IN ('t_客服部','t_工務部')"))
    eng.dispose()
    lo = client.get(f"{BASE}/masters/departments/link-options")
    check("CH 部門連結選項 200", lo.status_code == 200, f"status={lo.status_code}")
    check("CH 部門連結選項不含日曜部門（t_客服部）", "t_客服部" not in lo.text, "")
    check("CH 部門連結選項含春大直部門（t_工務部）", "t_工務部" in lo.text, "")
    base_cycle = {"cycle_code": "CY-T1", "cycle_name": "測試", "frequency": "monthly"}
    r = client.post(f"{BASE}/cycles", json={**base_cycle, "applicable_department_ids": str(dept_ou)})
    check("CH 週期設定選日曜部門 → 404（不得寫入）", r.status_code == 404, f"status={r.status_code}")
    r = client.post(f"{BASE}/cycles", json={**base_cycle, "cycle_code": "CY-T2", "applicable_scope": "日曜天地"})
    check("CH 週期設定適用公司選日曜 → 403", r.status_code == 403, f"status={r.status_code}")
    cur_user["u"] = ou
    lo2 = client.get(f"{BASE}/masters/departments/link-options")
    check("OU 部門連結選項含日曜部門", "t_客服部" in lo2.text, f"status={lo2.status_code}")
    check("OU 部門連結選項不含春大直部門", "t_工務部" not in lo2.text, "")

    # ── 公司切換器用的可見公司清單 ──
    cur_user["u"] = ch
    cc = client.get(f"{BASE}/companies")
    check("CH 可見公司清單只含春大直", cc.status_code == 200 and [c["code"] for c in cc.json()["companies"]] == ["CH"]
          and cc.json()["current"] == "CH", f"{cc.status_code} {cc.text[:120]}")
    cur_user["u"] = ou
    cc2 = client.get(f"{BASE}/companies")
    check("OU 可見公司清單只含日曜", cc2.status_code == 200 and [c["code"] for c in cc2.json()["companies"]] == ["OU"],
          f"{cc2.status_code} {cc2.text[:120]}")

    # ── 系統管理員 ──
    cur_user["u"] = ch; cur_user["admin"] = True
    check("管理員指定 co=OU 可讀日曜採購單", client.get(f"{BASE}/pos", params={"co": "OU"}).status_code == 200
          and "PO-OU-1" in client.get(f"{BASE}/pos", params={"co": "OU"}).text)
    cur_user["admin"] = False

    app.dependency_overrides.clear()
    print("RESULT:", "ALL PASS" if FAILS == 0 else f"{FAILS} FAILED")
    return FAILS


if __name__ == "__main__":
    sys.exit(main())
