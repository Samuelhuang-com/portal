"""
把 `user_roles.granted_by` 指向已刪除帳號的值清成 NULL

背景（2026-08-29，PostgreSQL 遷移的前置檢查抓到）
────────────────────────────────────────────────────────────────────────────
`user_roles.granted_by → users.id` 有 11 列孤兒，**全部指向同一個 UUID**
（`2d81795a-5ee7-4038-872c-6fc22b11871b`），那個帳號已經不存在，
連 `audit_logs` 都查不到任何線索。

⚠️ **主庫 `portal.db` 沒有開 `PRAGMA foreign_keys`**（週採的
`cycle-purchase.db` 才有），所以外鍵宣告形同虛設，孤兒可以長年累積。
PostgreSQL 一律執行 → 灌資料時 `violates foreign key constraint`。

為什麼設 NULL 是安全的
    · `granted_by` 是**稽核性欄位** —— 記的是「當時是誰授權的」。
      父資料被刪（帳號被移除）本來就會發生，欄位本身也宣告 `nullable=True`。
    · ⚠️ **角色指派本身完全不受影響** —— 這裡只清「誰授權的」這個註記，
      `user_id` 與 `role_id` 一個都不動，沒有人的權限會改變。
    · 那個 UUID 已經沒有任何線索可以還原，留著只是一個指不到東西的指標。

⚠️ 與 `contracts.vendor_id` 的差別（那個**不能**這樣處理）：
    | | `granted_by` | `contracts.vendor_id` |
    |---|---|---|
    | 性質 | 稽核註記 | 業務關聯 |
    | nullable | ✅ 是 | ❌ 否 |
    | 設 NULL 的損失 | 無（人都不在了） | **弄丟合約屬於哪家廠商** |

⚠️ 預設唯讀。要實際修改必須加 `--fix`。
⚠️ 動手前請先複製一份 `C:\\portal_data\\portal.db`。

執行：
    cd backend
    py -3.12 scripts\\fix_orphan_granted_by.py          # 只看不改
    py -3.12 scripts\\fix_orphan_granted_by.py --fix    # 實際清除
"""
from __future__ import annotations

import logging
import os
import sys

# ⚠️ 輸出強制 UTF-8：導向檔案時 Python 會改用 cp950，emoji 編不進去會整支中斷。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

from sqlalchemy import text                                       # noqa: E402

ORPHAN = ("ur.granted_by IS NOT NULL AND ur.granted_by <> '' "
          "AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id = ur.granted_by)")


def main() -> int:
    do_fix = "--fix" in sys.argv
    from app.core.database import engine
    engine.echo = False

    print("=" * 78)
    print("  清除 user_roles.granted_by 指向已刪除帳號的值")
    print("=" * 78)
    print(f"  {engine.url}\n")

    with engine.connect() as c:
        missing = c.execute(text(
            f"SELECT DISTINCT ur.granted_by FROM user_roles ur WHERE {ORPHAN}"
        )).scalars().all()
        if not missing:
            print("  ✅ 沒有孤兒，不需要處理。\n")
            return 0

        total = c.execute(text("SELECT COUNT(*) FROM user_roles")).scalar_one()
        n = c.execute(text(f"SELECT COUNT(*) FROM user_roles ur WHERE {ORPHAN}")).scalar_one()

        print(f"  {n} 列 / 全表 {total} 列，指向 {len(missing)} 個已刪除的帳號：\n")
        for uid in missing:
            cnt = c.execute(text(
                "SELECT COUNT(*) FROM user_roles WHERE granted_by = :u"), {"u": uid}).scalar_one()
            print(f"    {uid}  →  授權過 {cnt} 筆")
            # ⚠️ 把受影響的指派列出來，讓人看見「動的只是註記、不是權限」
            rows = c.execute(text(
                "SELECT u.email, COALESCE(r.name, '(角色已刪除)') FROM user_roles ur "
                "JOIN users u ON u.id = ur.user_id "
                "LEFT JOIN roles r ON r.id = ur.role_id "
                "WHERE ur.granted_by = :u ORDER BY u.email, r.name"), {"u": uid}).all()
            for email, role in rows:
                print(f"        {email:<34} {role}")

    print(f"""
  ⚠️ 只把「授權者」這個註記清成 NULL —— **user_id 與 role_id 一個都不動**，
     上面這些人的權限完全不受影響。""")

    if not do_fix:
        print("""
  （唯讀模式，未修改任何資料）
  ⚠️ 先複製一份 C:\\portal_data\\portal.db 當備份，再加 --fix 執行。
""")
        return 1

    with engine.connect() as c:
        n_done = c.execute(text(
            f"UPDATE user_roles SET granted_by = NULL WHERE {ORPHAN.replace('ur.', '')}"
        ).bindparams()).rowcount
        c.commit()
        left = c.execute(text(
            f"SELECT COUNT(*) FROM user_roles ur WHERE {ORPHAN}")).scalar_one()
        still = c.execute(text("SELECT COUNT(*) FROM user_roles")).scalar_one()

    print(f"\n  ✅ 已清除 {n_done} 列的授權者註記")
    print(f"  ✅ 剩餘孤兒 {left} 列；user_roles 總數 {still} 列（應與清除前相同）")
    print("""
  接著：
    py -3.12 scripts\\pg_show_orphans.py            ← 應只剩 contracts.vendor_id
    py -3.12 scripts\\pg_migrate_pilot.py --all     ← 若合約那組也處理完，
                                                     就不再需要 --allow-orphans
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
