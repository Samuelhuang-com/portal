"""
檢核：週採部門是否都已接回「公司/部門管理」全站主檔

為什麼要查
────────────────────────────────────────────────────────────────────────────
2026-09-01 起，週採請購單的編輯權限改走「部門成員」鏈：

    請購單.department_id → cycle_purchase_departments.source_department_id
        → portal.db departments.id → user_departments（使用者↔部門）

`source_department_id IS NULL` 的週採部門（＝本地自建、沒接回主檔）**走不了
這條鏈** —— 只剩 owner_user_id 備援通道（一位承辦人）與 cycle_purchase_view /
system_admin 能操作它的請購單。上線「部門成員可編輯」之前應該把這些部門
接回主檔，否則「同部門的人都能編」對這些部門不生效，而且不會有任何錯誤訊息。

本腳本做什麼（**純唯讀**，不改任何資料）
────────────────────────────────────────────────────────────────────────────
  ① 列出所有 source_department_id IS NULL 的週採部門，附：
     - 該部門底下有幾張請購單（受影響範圍）
     - owner_user_id 是誰（現在唯一能編它的人；NULL 就是沒人能編）
     - 主檔裡有沒有「公司+名稱」完全相同的部門（有＝跑一次「週期採購部門」
       同步就會自動收編，不用手動處理）
  ② 列出孤兒（source_department_id 指向的主檔部門已被刪除）
  ③ 順帶列出主檔端「啟用中但週採還沒有鏡像」的部門（下次同步會新增，僅供參考）

怎麼修（2026-09-01 更新：company 改週採自行輸入，比對規則跟著變）
────────────────────────────────────────────────────────────────────────────
  - **部門名稱**在週採未連結列中唯一、且主檔有同名部門 → 跑一次同步即可
    （sync_tool.py「週期採購部門」，或等排程），會自動收編
  - 部門名稱重複（跨公司同名）→ 同步刻意不自動連結，請到
    週期採購 → 部門主檔 → 編輯 → 「連結主檔部門」下拉手動連結
  - 主檔還沒有這個部門 → 先到「系統設定 → 公司/部門管理」建部門
    （⚠️ 公司名稱**不需要**跟週採的公司字串一致——週採的 company 是自行
    輸入的業務字串，兩邊本來就可以不同），再同步或手動連結
  - 真的不要接回主檔的部門 → 維持現狀，但要知道它只剩承辦人通道

執行
────────────────────────────────────────────────────────────────────────────
    cd backend
    python scripts\\check_cp_departments_linked.py      # 測試區
    py -3.11 scripts\\check_cp_departments_linked.py    # 正式區

離開碼：0＝全部已連結；1＝有未連結或孤兒（上面有清單）；2＝檢查失敗。
⚠️ 查不出來（連線失敗等）回 2，不回 0 —— 「沒查成功」不等於「查過沒問題」。
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


def main() -> int:
    from app.core.database import SessionLocal
    from app.core.cycle_purchase_database import CyclePurchaseSessionLocal
    from app.models.reference_data import Company, RefDepartment
    from app.models.user import User
    from app.models.cycle_purchase_reference import CyclePurchaseDepartment
    from app.models.cycle_purchase_request import CyclePurchaseRequest

    portal_db = SessionLocal()
    cp_db = CyclePurchaseSessionLocal()
    try:
        # 主檔：portal.db（公司+名稱 → RefDepartment）
        ref_rows = (
            portal_db.query(RefDepartment, Company)
            .join(Company, RefDepartment.company_id == Company.id)
            .all()
        )
        # 2026-09-01 起自動收編只看**部門名稱唯一命中**（company 是週採自行輸入，
        # 不參與比對）。這裡照同一套規則預判哪些跑同步就會自動連上。
        ref_name_count: dict = {}
        for d, _ in ref_rows:
            ref_name_count[d.name] = ref_name_count.get(d.name, 0) + 1
        ref_ids = {str(d.id) for d, _ in ref_rows}
        users_by_id = {u.id: u for u in portal_db.query(User).all()}

        cp_depts = cp_db.query(CyclePurchaseDepartment).all()

        print("=" * 76)
        print("  週採部門 ↔ 公司/部門管理主檔 連結檢核（唯讀）")
        print("=" * 76)
        print(f"  週採部門共 {len(cp_depts)} 筆；主檔部門共 {len(ref_rows)} 筆")

        # ── ① 未連結（本地自建）──────────────────────────────────────────
        unlinked = [d for d in cp_depts if not d.source_department_id]
        # 週採端同名未連結部門也會讓自動收編卻步（不知道收編哪一筆）
        cp_unlinked_name_count: dict = {}
        for d in unlinked:
            cp_unlinked_name_count[d.dept_name] = cp_unlinked_name_count.get(d.dept_name, 0) + 1
        print(f"\n【① 未連結主檔（source_department_id IS NULL）】{len(unlinked)} 筆")
        if unlinked:
            print("    這些部門的請購單只剩「承辦人」通道，「同部門可編輯」不生效：")
        for d in unlinked:
            n_req = (
                cp_db.query(CyclePurchaseRequest)
                .filter(CyclePurchaseRequest.department_id == d.id)
                .count()
            )
            owner = users_by_id.get(d.owner_user_id)
            owner_txt = (
                f"承辦人：{owner.full_name}（{owner.email}）" if owner
                else "⚠️ 沒有承辦人 —— 一般填單人**沒有任何人**能編它的單"
            )
            n_ref = ref_name_count.get(d.dept_name, 0)
            if n_ref == 1 and cp_unlinked_name_count.get(d.dept_name, 0) == 1:
                auto = "✓ 部門名稱唯一命中，跑一次「週期採購部門」同步即自動收編"
            elif n_ref == 0:
                auto = ("✗ 主檔沒有同名部門 —— 到「公司/部門管理」建部門後再同步或手動連結"
                        "（公司名稱不需要跟週採的公司字串一致）")
            else:
                auto = ("✗ 部門名稱重複（主檔或週採端有多筆同名）—— 同步不會自動連結，"
                        "請到 週期採購 → 部門主檔 → 編輯 →「連結主檔部門」手動連結")
            state = "啟用" if d.is_active else "停用"
            print(f"    - [{state}] {d.company}／{d.dept_name}（id={d.id}, code={d.dept_code}）")
            print(f"        請購單 {n_req} 張 · {owner_txt}")
            print(f"        {auto}")

        # ── ② 孤兒 ────────────────────────────────────────────────────────
        orphans = [
            d for d in cp_depts
            if d.source_department_id and d.source_department_id not in ref_ids
        ]
        print(f"\n【② 孤兒（指向的主檔部門已被刪除）】{len(orphans)} 筆")
        for d in orphans:
            print(f"    - {d.company}／{d.dept_name}（id={d.id}, "
                  f"source_department_id={d.source_department_id}）")

        # ── ③ 主檔有、週採還沒有（僅供參考）──────────────────────────────
        # 排除「會被名稱唯一命中自動收編」的（那些下次同步是收編既有列，不是新增）
        cp_src_ids = {d.source_department_id for d in cp_depts if d.source_department_id}
        missing = [
            (c, d) for d, c in ref_rows
            if d.is_active and str(d.id) not in cp_src_ids
            and cp_unlinked_name_count.get(d.name, 0) == 0
        ]
        print(f"\n【③ 主檔啟用中、週採尚無鏡像】{len(missing)} 筆（下次「週期採購部門」同步會新增，"
              f"company 帶主檔公司名當初始值、之後可自行改）")
        for c, d in missing:
            print(f"    - {c.name}／{d.name}（主檔 id={d.id}）")

        print("\n" + "=" * 76)
        if unlinked or orphans:
            print("  ⚠️ 有未連結或孤兒項目，處理方式見本檔檔頭「怎麼修」。")
            return 1
        print("  ✅ 所有週採部門都已連結主檔，「部門成員可編輯」全面生效。")
        return 0

    except Exception as exc:
        print(f"✗ 檢查失敗：{exc}")
        import traceback
        traceback.print_exc()
        return 2
    finally:
        portal_db.close()
        cp_db.close()


if __name__ == "__main__":
    sys.exit(main())
