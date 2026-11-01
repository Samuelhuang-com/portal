"""週採多公司隔離：使用者可見公司與 co 參數權限測試（真的 PostgreSQL）

每次執行前請重建主庫測試庫（本腳本會提交測試資料）。
前置：
  - 主庫（DATABASE_URL）已升到 head；週採庫（CYCLE_PURCHASE_DATABASE_URL）已升到 cpco3 且有 CH/OU/HO 三筆公司。
  - 本腳本只寫入測試用資料（前綴 t_），不要對正式區執行。
用法：
  DATABASE_URL=postgresql+psycopg2://... CYCLE_PURCHASE_DATABASE_URL=postgresql+psycopg2://... \
  python scripts/verify_cp_company_scope.py
"""
import os
import sys
import uuid
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2  # noqa: E402
from psycopg2.extras import RealDictCursor  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from verify_cp_company_batch1 import _dsn  # noqa: E402
import app.services.cycle_purchase_company_scope as scope  # noqa: E402
from app.core.cycle_purchase_database import CyclePurchaseSessionLocal  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402

FAILS = 0


def check(desc, cond, detail=""):
    global FAILS
    FAILS += 0 if cond else 1
    print("PASS" if cond else "FAIL", desc, detail)


def _fill(cur, table, values):
    cur.execute("""SELECT column_name, data_type, column_default, is_nullable
                   FROM information_schema.columns WHERE table_name=%s AND table_schema=current_schema()""", (table,))
    out = dict(values)
    for col in cur.fetchall():
        n = col["column_name"]
        if n in out or col["is_nullable"] == "YES" or col["column_default"] is not None:
            continue
        dt = col["data_type"]
        if dt in ("character varying", "text", "character"):
            out[n] = "t_" + uuid.uuid4().hex[:8]
        elif dt in ("integer", "bigint", "smallint", "numeric"):
            out[n] = 1
        elif dt == "boolean":
            out[n] = False
        elif dt.startswith("timestamp") or dt == "date":
            out[n] = "2026-10-31"
        else:
            out[n] = "t"
    cols = list(out)
    cur.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s']*len(cols))}) RETURNING id",
                [out[c] for c in cols])
    return cur.fetchone()["id"]


def setup_main():
    conn = psycopg2.connect(_dsn(os.environ["DATABASE_URL"]))
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SET session_replication_role = replica")
    tenant_id = str(uuid.uuid4())
    tid = _fill(cur, "tenants", {"id": tenant_id, "source_company_id": None})
    comp_ch = _fill(cur, "companies", {"name": "春大直"})
    comp_ou = _fill(cur, "companies", {"name": "日曜天地"})
    comp_ho = _fill(cur, "companies", {"name": "台中"})
    dep_ch = _fill(cur, "departments", {"name": "t_工務部", "company_id": comp_ch})
    dep_ou = _fill(cur, "departments", {"name": "t_客服部", "company_id": comp_ou})
    def user(name, tenant):
        uid = str(uuid.uuid4())
        _fill(cur, "users", {"id": uid, "tenant_id": tenant, "email": f"{name}@t.local", "full_name": name})
        return uid
    u_ch = user("t_u_ch", tid)
    u_ou = user("t_u_ou", tid)
    u_none = user("t_u_none", tid)
    # u_mix 使用獨立租戶：無部門，主要公司別為台中（不影響其他使用者）
    tid_mix = _fill(cur, "tenants", {"id": str(uuid.uuid4()), "source_company_id": str(comp_ho)})
    u_mix = user("t_u_mix", tid_mix)
    _fill(cur, "user_departments", {"user_id": u_ch, "department_id": dep_ch})
    _fill(cur, "user_departments", {"user_id": u_ou, "department_id": dep_ou})
    conn.commit()
    return {"u_ch": u_ch, "u_ou": u_ou, "u_none": u_none, "u_mix": u_mix, "tenant": tid, "tenant_mix": tid_mix}


def make_user(uid, tenant):
    return SimpleNamespace(id=uid, tenant_id=tenant)


def main() -> int:
    ids = setup_main()
    main_db = SessionLocal()
    cp_db = CyclePurchaseSessionLocal()
    try:
        ch = make_user(ids["u_ch"], ids["tenant"])
        ou = make_user(ids["u_ou"], ids["tenant"])
        none = make_user(ids["u_none"], ids["tenant"])
        mix = make_user(ids["u_mix"], ids["tenant_mix"])

        perms_by_id = {ids["u_ch"]: ["cycle_purchase_company_ch"],
                       ids["u_ou"]: ["cycle_purchase_company_ou"],
                       ids["u_none"]: [],
                       ids["u_mix"]: ["cycle_purchase_company_ho", "cycle_purchase_company_ch"]}
        scope.get_user_permissions = lambda uid, db: perms_by_id.get(uid, [])
        check("角色給春大直者可見 CH", scope.visible_codes_for_user(main_db, cp_db, ch) == {"CH"})
        check("角色給日曜者可見 OU（不含 CH）", scope.visible_codes_for_user(main_db, cp_db, ou) == {"OU"})
        check("沒有公司權限者不可見任何公司", scope.visible_codes_for_user(main_db, cp_db, none) == frozenset())
        check("多角色取聯集（HO＋CH）", scope.visible_codes_for_user(main_db, cp_db, mix) == {"HO", "CH"})

        check("名稱別名 日曜 → OU", scope.resolve_company_code(cp_db, "日曜") == "OU")
        check("代碼大小寫不敏感 ou → OU", scope.resolve_company_code(cp_db, "ou") == "OU")
        check("未知公司回 None", scope.resolve_company_code(cp_db, "不存在") is None)

        ctx = scope.company_context(co=None, current_user=ou, main_db=main_db, cp_db=cp_db)
        check("未帶 co 時，只能看到 OU 的使用者預設為 OU", ctx.code == "OU")

        try:
            scope.company_context(co="OU", current_user=ch, main_db=main_db, cp_db=cp_db)
            check("春大直使用者指定 co=OU 應回 403", False)
        except HTTPException as e:
            check("春大直使用者指定 co=OU 回 403", e.status_code == 403, f"status={e.status_code}")

        try:
            scope.company_context(co="CH", current_user=none, main_db=main_db, cp_db=cp_db)
            check("無公司者應回 403", False)
        except HTTPException as e:
            check("無公司者回 403", e.status_code == 403)

        ctx = scope.company_context(co="ch", current_user=ch, main_db=main_db, cp_db=cp_db)
        check("co=ch（小寫）解析為 CH", ctx.code == "CH")

        # 系統管理員：全部啟用公司
        orig = scope.get_user_permissions
        scope.get_user_permissions = lambda uid, db: ["*"]
        try:
            ctx = scope.company_context(co="HO", current_user=ou, main_db=main_db, cp_db=cp_db)
            check("系統管理員可指定任一公司（HO）", ctx.code == "HO" and ctx.is_admin)
            check("系統管理員可見全部三間公司", ctx.codes == {"CH", "OU", "HO"}, f"codes={sorted(ctx.codes)}")
        finally:
            scope.get_user_permissions = orig

        # 單筆資料可見性
        ctx = scope.company_context(co=None, current_user=ch, main_db=main_db, cp_db=cp_db)
        try:
            scope.assert_visible(ctx, "OU")
            check("跨公司單筆應回 404", False)
        except HTTPException as e:
            check("跨公司單筆回 404（不洩漏存在）", e.status_code == 404)
        scope.assert_visible(ctx, "CH")
        check("同公司單筆通過", True)
    finally:
        main_db.rollback()
        main_db.close()
        cp_db.close()
    print("RESULT:", "ALL PASS" if FAILS == 0 else f"{FAILS} FAILED")
    return FAILS


if __name__ == "__main__":
    sys.exit(main())
