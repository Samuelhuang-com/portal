"""角色授權端到端測試：盤點 → 確認 → 寫入 role_permissions → 真實權限查詢得到正確可見公司

前置：主庫（DATABASE_URL）為「剛建好、空的」測試庫（已 alembic upgrade head）；週採庫已升到 cpco4。
本測試不替換 get_user_permissions，走真實的角色權限查詢。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import psycopg2  # noqa: E402
from psycopg2.extras import RealDictCursor  # noqa: E402

import verify_cp_company_scope as setup_mod  # noqa: E402
import cp_company_grants_plan as plan  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.cycle_purchase_database import CyclePurchaseSessionLocal  # noqa: E402
from app.services import cycle_purchase_company_scope as scope  # noqa: E402
from app.models.role_permission import RolePermission  # noqa: E402

FAILS = 0


def check(desc, cond, detail=""):
    global FAILS
    FAILS += 0 if cond else 1
    print("PASS" if cond else "FAIL", desc, detail)


def main() -> int:
    ids = setup_mod.setup_main()  # t_u_ch（工務部→CH）、t_u_ou（客服部→OU）、t_u_none、t_u_mix（主要公司別→HO）
    conn = psycopg2.connect(setup_mod._dsn(os.environ["DATABASE_URL"]))
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SET session_replication_role = replica")
    role_ch = setup_mod._fill(cur, "roles", {"name": "週採-春大直"})
    role_ou = setup_mod._fill(cur, "roles", {"name": "週採-日曜"})
    setup_mod._fill(cur, "user_roles", {"user_id": ids["u_ch"], "role_id": role_ch, "tenant_id": ids["tenant"]})
    setup_mod._fill(cur, "user_roles", {"user_id": ids["u_ou"], "role_id": role_ou, "tenant_id": ids["tenant"]})
    conn.commit(); conn.close()

    # 1. 盤點（依改版前的部門規則）
    main_db = SessionLocal(); cp_db = CyclePurchaseSessionLocal()
    try:
        from app.models.user import User
        cur_ch = main_db.query(User).filter(User.id == ids["u_ch"]).first()
        check("盤點：春大直角色成員的舊規則可見 CH", plan.legacy_codes_for_user(main_db, cp_db, cur_ch) == {"CH"})
    finally:
        main_db.close(); cp_db.close()
    check("盤點報表寫入", plan.report() == 0)
    with open(plan.PROPOSAL_FILE, encoding="utf-8") as f:
        proposal = json.load(f)["roles"]
    check("建議：週採-春大直 → CH", proposal["週採-春大直"]["suggested_codes"] == ["CH"], str(proposal["週採-春大直"]))
    check("建議：週採-日曜 → OU", proposal["週採-日曜"]["suggested_codes"] == ["OU"], str(proposal["週採-日曜"]))

    # 2. 確認（管理員確認後的版本）→ 乾跑不寫入
    confirmed = "cp_company_grants_confirmed.json"
    with open(confirmed, "w", encoding="utf-8") as f:
        json.dump({"roles": {"週採-春大直": ["CH"], "週採-日曜": ["OU"]}}, f, ensure_ascii=False)
    check("乾跑 apply 回傳 0", plan.apply(confirmed, write=False) == 0)
    main_db = SessionLocal()
    check("乾跑後尚未寫入任何授權",
          main_db.query(RolePermission).filter(RolePermission.permission_key.like("cycle_purchase_company_%")).count() == 0)
    main_db.close()

    # 3. 寫入
    check("正式 apply（--yes）回傳 0", plan.apply(confirmed, write=True) == 0)
    main_db = SessionLocal(); cp_db = CyclePurchaseSessionLocal()
    try:
        keys = {(rp.role_id, rp.permission_key) for rp in main_db.query(RolePermission)
                .filter(RolePermission.permission_key.like("cycle_purchase_company_%")).all()}
        check("寫入：春大直角色有 cycle_purchase_company_ch", (role_ch, "cycle_purchase_company_ch") in keys)
        check("寫入：日曜角色有 cycle_purchase_company_ou", (role_ou, "cycle_purchase_company_ou") in keys)

        # 4. 真實權限查詢（不替換 get_user_permissions）
        from app.models.user import User
        def U(uid): return main_db.query(User).filter(User.id == uid).first()
        check("真實查詢：春大直成員可見 CH", scope.visible_codes_for_user(main_db, cp_db, U(ids["u_ch"])) == {"CH"})
        check("真實查詢：日曜成員可見 OU", scope.visible_codes_for_user(main_db, cp_db, U(ids["u_ou"])) == {"OU"})
        check("真實查詢：無角色者（有主要公司別 HO）不可見任何公司（改由角色決定）",
              scope.visible_codes_for_user(main_db, cp_db, U(ids["u_mix"])) == frozenset())
        check("名稱：日曜公司顯示為「日曜」",
              cp_db.execute(__import__("sqlalchemy").text("SELECT name FROM cycle_purchase_companies WHERE code='OU'")).scalar() == "日曜")
    finally:
        main_db.close(); cp_db.close()

    # 5. 重跑 apply 應為冪等（沒有新增或移除）
    check("重跑 apply 冪等（回傳 0）", plan.apply(confirmed, write=True) == 0)
    main_db = SessionLocal()
    n = main_db.query(RolePermission).filter(RolePermission.permission_key.like("cycle_purchase_company_%")).count()
    main_db.close()
    check("重跑後授權筆數仍為 2", n == 2, f"n={n}")

    print("RESULT:", "ALL PASS" if FAILS == 0 else f"{FAILS} FAILED")
    return FAILS


if __name__ == "__main__":
    sys.exit(main())
