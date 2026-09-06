"""
立刻執行一次「公司 → 據點」鏡像同步，並診斷為什麼下拉還沒變

要解決什麼
────────────────────────────────────────────────────────────────────────────
2026-09-01：改完之後「人員管理 → 新增使用者 → 所屬據點」下拉仍然是舊的六個
據點（Default Tenant／商場A／商場B／總公司／飯店A／飯店B），公司/部門管理裡的
台中／春大直／樂群／自由完全沒出現。

⚠️⚠️ **根因：測試區 `.env` 是 `SCHEDULER_ENABLED=false`。**
`main.py` 的 APScheduler 完全不啟動 → `_auto_sync()` 從來不會跑 →
`tenant_company_sync` 一次都沒執行過。這與 CHANGELOG [1.96.46]「5 個排程模組
在正式區從未執行」是**同一個坑**：把同步掛進 `_auto_sync` 不等於它會被執行，
還要看那台機器有沒有開排程。

在這種環境下，鏡像同步只有兩條路會被觸發：
  ① `sync_tool.py` 手動同步「使用者據點」
  ② 在「公司/部門管理」新增／改名／停用任一家公司（`_mirror_tenants` write-through）

本腳本是第三條路：不必開 GUI，直接跑一次並把前後對照印出來。

做什麼
────────────────────────────────────────────────────────────────────────────
  ① 檢查前置條件：`tenants.source_company_id` 欄位存在嗎（＝ migration 跑過沒）
  ② 印出目前的 companies 與 tenants 兩份清單，讓差異一眼可見
  ③ `--apply` 才實際執行 `sync_companies_to_tenants()`，並印出同步後的結果

⚠️ 本腳本只做鏡像同步（新增／改名／啟停用鏡像據點）。**不會**停用舊據點、
   **不會**改任何使用者的所屬據點 —— 那是 `migrate_tenants_to_companies.py`
   的工作，是一次性的業務決策，兩件事刻意分開。

執行
────────────────────────────────────────────────────────────────────────────
    cd backend

    # 測試區（本機 anaconda 的 python）
    python scripts\\sync_tenants_now.py            # 唯讀診斷
    python scripts\\sync_tenants_now.py --apply    # 實際同步

    # 正式區（D:\\portal / C:\\portal）
    py -3.11 scripts\\sync_tenants_now.py
    py -3.11 scripts\\sync_tenants_now.py --apply

⚠️ 兩區直譯器不同，指令不能互抄。

離開碼
    0 = 診斷通過且無待同步項目，或已成功同步
    1 = 有待同步的內容但沒有加 --apply
    2 = 前置條件不滿足（多半是 migration 還沒跑）或執行出錯
"""
from __future__ import annotations

import argparse
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


def _cmd_hint() -> str:
    exe = sys.executable or "python"
    return f'"{exe}"' if " " in exe else exe


def _dump(db, Company, Tenant) -> tuple[list, list]:
    companies = db.query(Company).order_by(Company.name).all()
    tenants = db.query(Tenant).order_by(Tenant.name).all()

    print(f"\n【公司/部門管理 → 公司別】{len(companies)} 家")
    for c in companies:
        print(f"    {'啟用' if c.is_active else '停用'}  id={c.id:<4} {c.name}")

    print(f"\n【據點 tenants】{len(tenants)} 筆"
          f"（人員管理下拉只會顯示「啟用」且會看到的那幾筆）")
    for t in tenants:
        src = f"← 公司 id={t.source_company_id}" if t.source_company_id else "本地自建（同步不碰）"
        print(f"    {'啟用' if t.is_active else '停用'}  code={t.code:<14} {t.name:<16} {src}")

    return companies, tenants


def main() -> int:
    parser = argparse.ArgumentParser(
        description="立刻執行一次公司→據點鏡像同步（預設唯讀診斷）",
    )
    parser.add_argument("--apply", action="store_true", help="實際執行同步（預設只診斷）")
    args = parser.parse_args()

    from app.core.database import SessionLocal
    from app.models.reference_data import Company
    from app.models.tenant import Tenant

    db = SessionLocal()
    try:
        # ── 前置條件：migration 跑過沒 ────────────────────────────────────
        try:
            db.query(Tenant.source_company_id).limit(1).all()
        except Exception as exc:
            db.rollback()
            print("✗ tenants.source_company_id 不存在 —— migration 還沒跑。")
            print("  ⚠️ PG 庫若從沒 stamp 過，要先跑 stamp 再 upgrade：")
            print(f"      cd backend")
            print(f"      {_cmd_hint()} scripts/alembic_stamp_current.py --apply")
            print(f"      {_cmd_hint()} -m alembic upgrade head")
            print(f"  （原始錯誤：{exc}）")
            return 2

        print("=" * 76)
        print("  公司 → 據點 鏡像同步 · 同步前")
        print("=" * 76)
        companies, tenants_before = _dump(db, Company, Tenant)

        if not companies:
            print("\n✗ 公司清單是空的。請先到「系統設定 → 公司/部門管理」建立公司。")
            return 2

        # 預估會有哪些變化（只是給人看的，實際判定仍由 sync 自己做）
        tenant_names = {t.name for t in tenants_before}
        missing = [c.name for c in companies if c.name not in tenant_names]
        if missing:
            print(f"\n→ 下列 {len(missing)} 家公司在據點清單裡還沒有對應："
                  + "、".join(missing))
        else:
            print("\n→ 每一家公司都已經有同名的據點（同步會把它們收編成鏡像）")

        if not args.apply:
            print("\n" + "-" * 76)
            print("這是唯讀診斷，什麼都沒有改。確認後加 --apply 實際同步：")
            print(f"    {_cmd_hint()} scripts/sync_tenants_now.py --apply")
            return 1

        # ── 執行同步 ──────────────────────────────────────────────────────
        from app.services.tenant_company_sync import sync_companies_to_tenants
        result = sync_companies_to_tenants(db)

        print("\n" + "=" * 76)
        print("  同步結果")
        print("=" * 76)
        print(f"    來源公司 {result['fetched']} 家 → "
              f"新增 {result['created']}、更新 {result['updated']}、"
              f"無異動 {result['unchanged']}、略過 {result['skipped']}、"
              f"孤兒 {result['orphans']}")
        for w in result["warnings"]:
            print(f"    ⚠ {w}")
        for e in result["errors"]:
            print(f"    ✗ {e}")

        print("\n" + "=" * 76)
        print("  同步後")
        print("=" * 76)
        _dump(db, Company, Tenant)

        print("\n" + "-" * 76)
        if result["errors"]:
            print("⚠️ 有錯誤，請看上面的訊息。")
            return 2

        print("✓ 鏡像同步完成。重新整理「人員管理 → 新增使用者」確認下拉。")
        print()
        print("  ⚠️ 舊據點（上面標「本地自建」那幾筆）**還在下拉裡**，這是預期的：")
        print("     停用舊據點、把既有使用者改掛「總公司」是一次性的業務決策，")
        print("     要另外跑（預設唯讀預覽）：")
        print(f"         {_cmd_hint()} scripts/migrate_tenants_to_companies.py")
        print(f"         {_cmd_hint()} scripts/migrate_tenants_to_companies.py --apply")
        print()
        print("  ⚠️ 本機 .env 是 SCHEDULER_ENABLED=false，往後公司清單有異動時：")
        print("     · 在「公司/部門管理」新增／改名／停用 → 會自動即時鏡像（write-through）")
        print("     · 直接改資料庫或想手動補跑 → 用 sync_tool.py 同步「使用者據點」，")
        print("       或再跑一次這支腳本")
        return 0

    except Exception as exc:
        db.rollback()
        print(f"✗ 執行失敗：{exc}")
        import traceback
        traceback.print_exc()
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
