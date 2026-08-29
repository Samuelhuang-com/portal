"""
查這兩組孤兒「還原得回來嗎」（唯讀）

`pg_show_orphans.py` 已經告訴我們一件關鍵的事：**兩組孤兒各自只有一個值。**

  · `contracts.vendor_id` 的 20 列全都是 `''`（空字串）
  · `user_roles.granted_by` 的 11 列全都是同一個 UUID

這代表它們**不是**「父資料被刪掉」那種零星孤兒，而是各有單一成因：

  · `''` → 那 20 張合約**從來沒有連上廠商主檔**。欄位是 `nullable=False`
    且預設 `""`，所以「沒填」被存成空字串而不是 NULL。
    ⚠️ 這是設計上的問題：外鍵欄位的「沒有值」應該是 NULL，不是 `''`。
       PostgreSQL 拒絕它是對的 —— `vendors` 裡沒有 `vendor_id = ''` 這筆。
    ⚠️ 順帶影響（跟遷移無關、現在就在發生）：這 20 張合約的
       `Contract.vendor` relationship 一定是 None，凡是從廠商主檔取值的
       畫面（統編、聯絡人、電話）對這 20 張都是空的。36 張裡佔 20 張。

  · 單一 UUID → 某個帳號被刪掉了，它授權過的 11 筆角色指派留了下來。

本腳本回答兩個問題，用來決定怎麼修：
  ① 那 20 張合約的 `vendor_name`，在 `vendors` 主檔裡找得到嗎？
     找得到 → 可以把真正的 vendor_id 補回去（**修好一個現存的功能缺陷**）
     找不到 → 只能讓欄位可為 NULL
  ② 那個被刪掉的 UUID，還有沒有其他線索（audit_logs）？

⚠️ 唯讀，不修改任何資料。

執行：
    cd backend
    py -3.12 scripts\\check_orphan_recoverable.py
"""
from __future__ import annotations

import logging
import os
import sys

# ⚠️ 輸出強制 UTF-8（2026-08-29 踩過）
#    Windows 主控台是 UTF-8，但**把輸出導向檔案時 Python 會改用 cp950**，
#    腳本裡的 ⚠️ ✅ ❌ 一律編不進去 → UnicodeEncodeError 整支中斷。
#    `> cmp.txt` 這種存檔動作很常用，不能因此掛掉。
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


def main() -> int:
    from app.core.database import engine
    engine.echo = False

    print("=" * 78)
    print("  孤兒還原可能性檢查（唯讀）")
    print("=" * 78)
    print(f"  {engine.url}\n")

    with engine.connect() as c:
        # ── ① contracts.vendor_id = '' 的 20 列，靠 vendor_name 對得回去嗎 ──
        print("-" * 78)
        print("  ① contracts.vendor_id = '' 的 20 列 —— 用 vendor_name 對回主檔")
        print("-" * 78)
        rows = c.execute(text(
            "SELECT ct.contract_name, ct.vendor_name, "
            "       (SELECT v.vendor_id FROM vendors v "
            "        WHERE TRIM(v.vendor_name) = TRIM(ct.vendor_name)) AS matched, "
            "       (SELECT COUNT(*) FROM vendors v "
            "        WHERE TRIM(v.vendor_name) = TRIM(ct.vendor_name)) AS n_match "
            "FROM contracts ct WHERE ct.vendor_id = '' "
            "ORDER BY ct.vendor_name")).all()

        hit = [r for r in rows if r.n_match == 1]
        dup = [r for r in rows if r.n_match > 1]
        miss = [r for r in rows if r.n_match == 0]

        for r in rows:
            if r.n_match == 1:
                mark, note = "✅", f"→ {r.matched}"
            elif r.n_match == 0:
                mark, note = "❌", "→ 主檔查無此廠商"
            else:
                mark, note = "⚠️ ", f"→ 主檔有 {r.n_match} 筆同名，無法確定"
            print(f"    {mark} {(r.vendor_name or '（空白）')[:26]:<28} {note}")
            print(f"          {r.contract_name}")

        print(f"\n    可自動補回 {len(hit)} 張 ｜ 同名多筆 {len(dup)} 張 ｜ 主檔沒有 {len(miss)} 張")

        # ── ② 被刪掉的授權者 ────────────────────────────────────────────
        print("\n" + "-" * 78)
        print("  ② user_roles.granted_by 指向的已刪除帳號")
        print("-" * 78)
        missing = c.execute(text(
            "SELECT DISTINCT ur.granted_by FROM user_roles ur "
            "WHERE ur.granted_by IS NOT NULL AND ur.granted_by <> '' "
            "AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id = ur.granted_by)"
        )).scalars().all()

        for uid in missing:
            n = c.execute(text("SELECT COUNT(*) FROM user_roles WHERE granted_by = :u"),
                          {"u": uid}).scalar_one()
            print(f"    {uid}  → 授權過 {n} 筆角色指派")
            try:
                # audit_logs 沒有 email 欄位，能查到的線索是 action / ip / extra
                trace = c.execute(text(
                    "SELECT created_at, action, ip_address, extra FROM audit_logs "
                    "WHERE user_id = :u ORDER BY created_at DESC LIMIT 3"),
                    {"u": uid}).all()
                if trace:
                    print("        稽核日誌還查得到這個 id（登入紀錄可看出是誰）：")
                    for t in trace:
                        print(f"          {t[0]} ｜ {t[1]} ｜ {t[2]} ｜ {str(t[3])[:40]}")
                else:
                    print("        ⚠️ 稽核日誌查不到 —— 這個帳號沒有留下任何線索")
            except Exception as e:
                print(f"        （稽核日誌查詢失敗：{type(e).__name__}）")

            # 受影響的是哪些人的哪些角色
            who = c.execute(text(
                "SELECT u.email, r.name FROM user_roles ur "
                "JOIN users u ON u.id = ur.user_id "
                "LEFT JOIN roles r ON r.id = ur.role_id "
                "WHERE ur.granted_by = :u LIMIT 12"), {"u": uid}).all()
            if who:
                print("        受影響的角色指派（授權紀錄會變空白，指派本身不動）：")
                for w in who:
                    print(f"          {w[0]} ｜ {w[1]}")

    print("\n" + "=" * 78)
    print("""  這支腳本只做判斷，不改資料。看完上面的結果再決定怎麼修。
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
