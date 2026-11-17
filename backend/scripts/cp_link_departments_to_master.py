"""
一次性：把週採部門（cycle_purchase_departments）連結到「公司/部門管理」主檔

背景（2026-11-17）
──────────────────────────────────────────────────
2026-09-22 週採部門改為本地自建、停用同步後，source_department_id 全部為 NULL，
「部門成員可編輯請購單」這條權限鏈（user_departments → source_department_id）
從此是斷的。本腳本用「公司代碼＋部門名稱」比對主檔，補回 source_department_id。

比對規則（與 2026-09-01 舊同步只比部門名稱不同）
──────────────────────────────────────────────────
  週採部門.company_code（CH／OU／HO）＝ 主檔公司名稱經 resolve_company_code()
  （含別名：樂群＝春大直、自由＝日曜天地、智選＝台中）解析出的代碼，
  且 部門名稱（去前後空白）完全相同、主檔部門與公司皆啟用。
  → 跨公司同名（例：春大直／管理部 vs 日曜／管理部）不會混在一起。

分類
──────────────────────────────────────────────────
  LINK          唯一命中，--apply 時才寫入 source_department_id
  NO_MASTER     主檔沒有對應部門（不會被連結；列出身上有多少資料，供決定刪除與否）
  AMBIGUOUS     主檔同公司同名有多筆，不猜，需人工處理
  INACTIVE_ONLY 只有停用的主檔部門對得上，不連
  CONFLICT      該主檔部門已被其他週採部門連結，或同一次有兩筆要連同一個主檔部門

本腳本**只改 source_department_id**；不新增、不刪除、不改名稱／公司別／代碼／承辦人。

執行（預設只預覽，不寫入）
──────────────────────────────────────────────────
    cd backend
    py -3.11 scripts\\cp_link_departments_to_master.py            # 預覽
    py -3.11 scripts\\cp_link_departments_to_master.py --apply    # 預覽後輸入 YES 才寫入
    py -3.11 scripts\\cp_link_departments_to_master.py --apply --yes   # 不問，直接寫（排程／批次用）

⚠️ 一律先看第一行印出的「連線目標」確認連到的是要處理的資料庫（測試區／正式區），
   再看預覽。測試區與正式區的部門 id、主檔 id 不同，結果不可互相套用。

離開碼：0＝完成（含預覽）；1＝--apply 被取消；2＝執行失敗。
"""
from __future__ import annotations

import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import logging                                                    # noqa: E402
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

# 依 department_id 綁住的資料表（表名只來自這裡的常數，不接受外部輸入）
DEPENDENT_TABLES = [
    ("料號對照", "cycle_purchase_item_mappings"),
    ("請購單", "cycle_purchase_requests"),
    ("彙整單列", "cycle_purchase_summary"),
    ("請款分攤", "cycle_purchase_payment_allocations"),
    ("類別主檔", "cycle_purchase_categories"),
    ("成本中心", "cycle_purchase_cost_centers"),
]


def _url(session) -> str:
    try:
        return session.get_bind().url.render_as_string(hide_password=True)
    except Exception as e:  # noqa: BLE001
        return f"（無法取得連線資訊：{e}）"


def _dependent_counts(cp_db, dept_id: int) -> list[tuple[str, object]]:
    from sqlalchemy import text
    out: list[tuple[str, object]] = []
    for label, table in DEPENDENT_TABLES:
        try:
            n = cp_db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE department_id = :d"), {"d": dept_id}
            ).scalar()
        except Exception:  # noqa: BLE001
            cp_db.rollback()
            n = "?"
        out.append((label, n))
    return out


def build_plan(portal_db, cp_db):
    from app.models.reference_data import Company, RefDepartment
    from app.models.cycle_purchase_reference import CyclePurchaseDepartment
    from app.models.cycle_purchase_cycle import CyclePurchaseCycle
    from app.services.cycle_purchase_company_scope import resolve_company_code

    # 主檔公司 → 週採公司代碼
    companies = portal_db.query(Company).order_by(Company.id).all()
    company_code = {c.id: resolve_company_code(cp_db, c.name) for c in companies}

    ref_rows = portal_db.query(RefDepartment).all()
    # (公司代碼, 名稱) → [RefDepartment...]
    idx: dict = {}
    for d in ref_rows:
        code = company_code.get(d.company_id)
        if not code:
            continue
        idx.setdefault((code, (d.name or "").strip()), []).append(d)
    company_active = {c.id: bool(c.is_active) for c in companies}

    cp_depts = cp_db.query(CyclePurchaseDepartment).order_by(
        CyclePurchaseDepartment.company_code, CyclePurchaseDepartment.id).all()
    already_linked_to = {
        int(d.source_department_id): d for d in cp_depts
        if d.source_department_id and str(d.source_department_id).isdigit()
    }

    plan = {"LINK": [], "NO_MASTER": [], "AMBIGUOUS": [], "INACTIVE_ONLY": [], "CONFLICT": []}
    taken: dict = {}   # 本次已規劃連結的主檔部門 id → 週採部門
    for d in cp_depts:
        if d.source_department_id:
            continue
        key = (d.company_code, (d.dept_name or "").strip())
        cands = idx.get(key, [])
        active = [c for c in cands if c.is_active and company_active.get(c.company_id)]
        if not cands:
            plan["NO_MASTER"].append((d, None))
        elif not active:
            plan["INACTIVE_ONLY"].append((d, cands))
        elif len(active) > 1:
            plan["AMBIGUOUS"].append((d, active))
        else:
            ref = active[0]
            if ref.id in already_linked_to:
                plan["CONFLICT"].append((d, ref, f"主檔部門已被週採部門 id={already_linked_to[ref.id].id} 連結"))
            elif ref.id in taken:
                plan["CONFLICT"].append((d, ref, f"與週採部門 id={taken[ref.id].id} 都對到同一個主檔部門"))
            else:
                taken[ref.id] = d
                plan["LINK"].append((d, ref))

    # 主檔端：啟用中、對得到週採公司、但週採沒有任何對應部門（僅供參考）
    cp_keys = {(d.company_code, (d.dept_name or "").strip()) for d in cp_depts}
    cp_linked_ids = {int(d.source_department_id) for d in cp_depts
                     if d.source_department_id and str(d.source_department_id).isdigit()}
    master_only = []
    for (code, name), refs in sorted(idx.items()):
        for r in refs:
            if r.is_active and company_active.get(r.company_id) \
                    and (code, name) not in cp_keys and r.id not in cp_linked_ids:
                master_only.append((code, r))

    # 週期設定裡引用到的部門 id（刪除前要知道）
    cycle_refs: dict = {}
    for c in cp_db.query(CyclePurchaseCycle).all():
        for tok in (c.applicable_department_ids or "").split(","):
            tok = tok.strip()
            if tok.isdigit():
                cycle_refs.setdefault(int(tok), []).append(c.cycle_name)
    return companies, company_code, plan, master_only, cycle_refs


def print_plan(portal_db, cp_db, companies, company_code, plan, master_only, cycle_refs):
    print("  【主檔公司 → 週採公司代碼】")
    for c in companies:
        code = company_code.get(c.id)
        flag = "" if c.is_active else "（停用）"
        print(f"    - {c.name}{flag} → {code if code else '✗ 無法對應（此公司的部門不會被連結）'}")

    print(f"\n  【LINK 唯一命中，--apply 才會寫入】{len(plan['LINK'])} 筆")
    for d, ref in plan["LINK"]:
        print(f"    ✓ {d.company}／{d.dept_name}（週採 id={d.id}, {d.company_code}） → 主檔 id={ref.id}「{ref.name}」")

    print(f"\n  【NO_MASTER 主檔沒有對應部門】{len(plan['NO_MASTER'])} 筆（不會連結；若要在週採端刪除，影響如下）")
    for d, _ in plan["NO_MASTER"]:
        deps = _dependent_counts(cp_db, d.id)
        cyc = cycle_refs.get(d.id, [])
        dep_txt = "、".join(f"{k} {v}" for k, v in deps)
        print(f"    ✗ {d.company}／{d.dept_name}（週採 id={d.id}, {d.company_code}）")
        print(f"        綁住的資料：{dep_txt}；週期設定引用：{('、'.join(cyc)) if cyc else '無'}")

    for title, key in (("AMBIGUOUS 主檔同公司同名有多筆，不猜", "AMBIGUOUS"),
                       ("INACTIVE_ONLY 只有停用的主檔部門對得上，不連", "INACTIVE_ONLY")):
        print(f"\n  【{title}】{len(plan[key])} 筆")
        for d, refs in plan[key]:
            ids = "、".join(f"{r.id}" for r in refs)
            print(f"    ? {d.company}／{d.dept_name}（週採 id={d.id}） 候選主檔 id：{ids}")

    print(f"\n  【CONFLICT】{len(plan['CONFLICT'])} 筆")
    for d, ref, why in plan["CONFLICT"]:
        print(f"    ! {d.company}／{d.dept_name}（週採 id={d.id}） → 主檔 id={ref.id}：{why}")

    print(f"\n  【參考：主檔啟用中、週採沒有對應部門】{len(master_only)} 筆（本腳本不會新增）")
    for code, r in master_only:
        print(f"    - {code}／{r.name}（主檔 id={r.id}）")


def main() -> int:
    apply = "--apply" in sys.argv
    assume_yes = "--yes" in sys.argv

    from app.core.database import SessionLocal
    from app.core.cycle_purchase_database import CyclePurchaseSessionLocal

    portal_db = SessionLocal()
    cp_db = CyclePurchaseSessionLocal()
    try:
        print("=" * 76)
        print("  週採部門 → 公司/部門管理主檔 連結（" + ("寫入模式" if apply else "預覽，不寫入") + "）")
        print("=" * 76)
        print(f"  連線目標 portal : {_url(portal_db)}")
        print(f"  連線目標 週採庫 : {_url(cp_db)}\n")

        companies, company_code, plan, master_only, cycle_refs = build_plan(portal_db, cp_db)
        print_plan(portal_db, cp_db, companies, company_code, plan, master_only, cycle_refs)

        n = len(plan["LINK"])
        print("\n" + "=" * 76)
        print(f"  預計連結 {n} 筆；不處理：NO_MASTER {len(plan['NO_MASTER'])}、"
              f"AMBIGUOUS {len(plan['AMBIGUOUS'])}、INACTIVE_ONLY {len(plan['INACTIVE_ONLY'])}、"
              f"CONFLICT {len(plan['CONFLICT'])}")
        if not apply:
            print("  （預覽模式，未寫入任何資料。確認無誤後加 --apply）")
            return 0
        if n == 0:
            print("  沒有可連結的項目。")
            return 0
        if not assume_yes:
            ans = input(f"  確定把以上 {n} 筆寫入「{_url(cp_db)}」？輸入 YES 繼續：").strip()
            if ans != "YES":
                print("  已取消，未寫入。")
                return 1

        for d, ref in plan["LINK"]:
            d.source_department_id = str(ref.id)
        cp_db.commit()

        # 寫入後回查（不信任「沒報錯」）
        from app.models.cycle_purchase_reference import CyclePurchaseDepartment
        ok = 0
        for d, ref in plan["LINK"]:
            row = cp_db.query(CyclePurchaseDepartment).filter(CyclePurchaseDepartment.id == d.id).first()
            if row and row.source_department_id == str(ref.id):
                ok += 1
        print(f"  ✅ 已寫入並回查確認 {ok}/{n} 筆。")
        return 0 if ok == n else 2
    except Exception as e:  # noqa: BLE001
        cp_db.rollback()
        print(f"  ✗ 執行失敗：{type(e).__name__}: {e}")
        return 2
    finally:
        portal_db.close()
        cp_db.close()


if __name__ == "__main__":
    sys.exit(main())
