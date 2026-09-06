"""
一次性遷移：把舊「據點」按對照表收斂成「公司/部門管理」的公司

要解決什麼
────────────────────────────────────────────────────────────────────────────
2026-09-01 使用者裁示：人員管理「新增使用者 → 所屬據點」的下拉，必須等於
「系統設定 → 公司/部門管理」維護的公司名稱。

`services/tenant_company_sync.py` 已負責把 Company 鏡像成 Tenant，但依
CLAUDE.md §9 規則 2，**同步不會去動 `source_company_id IS NULL` 的列**
（＝本地自建的 6 個舊據點）。把舊據點收斂掉是一次性的業務決策，刻意不放進
每輪都會跑的同步裡 —— 否則同步每一輪都在改業務資料，而且從此再也不能手動
新增任何據點。

對照表（使用者 2026-09-01 指定）
────────────────────────────────────────────────────────────────────────────
    舊據點 code   舊名稱            →  公司
    ───────────────────────────────────────────
    HQ            總公司            →  總公司
    MALL_A        商場A             →  春大直
    MALL_B        商場B             →  台中
    HOTEL_A       飯店A             →  樂群
    HOTEL_B       飯店B             →  自由
    default       Default Tenant    →  總公司

⚠️⚠️ **這個作法比「全部倒進總公司」好得多**：每個舊據點各自對應一家公司，
   既有使用者留在有意義的公司底下，**幾乎不需要重新指派任何人**
   （只有 `default` 底下的使用者要搬，因為 `總公司` 已經被 `HQ` 佔用）。

兩種處理模式
────────────────────────────────────────────────────────────────────────────
① **收編**（rename）：目標公司還沒有鏡像據點 → 直接把舊據點**改名**成公司名稱、
   回填 `source_company_id`。`tenants.id` 不變，**所有使用者、角色、Ragic 連線
   設定原封不動**，這是最安全的作法。舊 code（HQ／MALL_A…）保留不動 —— 它比
   同步自動產生的 `CMP-{id}` 有意義，而且 code 已經不再顯示在畫面上。

② **合併**（merge）：目標公司已經有鏡像據點（例如 `default` → 總公司，而總公司
   已被 `HQ` 收編）→ 把舊據點的 `users` 與 `user_roles` 改掛過去，舊據點停用。

⚠️ **執行順序**：本腳本會**先做完所有收編、再做合併**。顛倒的話 `default`
   會找不到總公司的鏡像而誤判成要收編，兩筆都想拿 `總公司` 這個
   `source_company_id`，撞 unique。

⚠️ **建議在 `sync_tenants_now.py --apply` 之前跑這一支。** 先跑同步的話，
   春大直／台中／樂群／自由會被建成 4 筆全新的 `CMP-{id}` 據點，舊據點仍在，
   變成一家公司兩筆據點。真的先跑了也沒關係：本腳本會偵測到已存在的鏡像，
   自動改走「合併」模式，只是使用者要多搬一次。

刻意不做的事
────────────────────────────────────────────────────────────────────────────
⚠️ **不刪除任何一筆 tenant。** `users.tenant_id`／`user_roles.tenant_id`／
   `ragic_connections.tenant_id` 都是 NOT NULL 外鍵，只要還有一列指著就
   DELETE 不掉；`audit_logs.tenant_id` 還留著歷史稽核紀錄。而
   `GET /api/v1/tenants` 只回 `is_active`，停用就足以讓它從下拉消失。

⚠️ **`default` 更是絕對不能刪。** `main.py` 開機時會用
   `SELECT id FROM tenants WHERE code = 'default'` 檢查，刪掉會被原地重建
   （停用則不會 —— 它只認 code 存不存在）。

⚠️ **不動 `ragic_connections`。** 那是各 Ragic 模組的連線設定，跟著舊據點走。
   收編模式下 id 不變，它們自動就對；合併模式下改指到別的據點不會讓任何事
   變好，卻可能讓同步找不到設定。腳本只印出它們指著誰，供你判斷。

⚠️ **不動 `audit_logs`。** 稽核日誌是歷史事實，改寫等於竄改紀錄。

⚠️ `user_roles` 有 `UniqueConstraint(user_id, role_id, tenant_id)`。合併時
   如果目標據點下已有同一組 `(user_id, role_id)`，會撞唯一鍵 —— 腳本會先偵測、
   **保留一筆、刪掉多餘的**，並把刪掉的內容印出來。

執行方式
────────────────────────────────────────────────────────────────────────────
    cd backend

    # 測試區（本機 anaconda 的 python）
    python scripts\\migrate_tenants_to_companies.py            # 唯讀預覽
    python scripts\\migrate_tenants_to_companies.py --apply    # 實際執行

    # 正式區（D:\\portal / C:\\portal）
    py -3.11 scripts\\migrate_tenants_to_companies.py
    py -3.11 scripts\\migrate_tenants_to_companies.py --apply

⚠️ 兩區直譯器不同，指令不能互抄（同 pg_fix_sequences.py 的說明）。

要改對照表就用 --map（可重複），不必改程式：
    python scripts\\migrate_tenants_to_companies.py --map MALL_A=台中 --map MALL_B=春大直

⚠️ **前置條件**：先跑完 alembic migration `tncomp`（`tenants.source_company_id`
   才存在）。PG 庫若從沒 stamp 過，要先 `alembic_stamp_current.py --apply`
   再 `alembic upgrade head`。腳本會自己檢查，缺前置條件會擋下來並說明缺什麼。

⚠️ **執行前請停掉會寫入的程式**（後端服務、sync_tool.py），並先備份
   （`python scripts\\pg_backup.py`）。

離開碼
────────────────────────────────────────────────────────────────────────────
    0 = 沒有東西要改，或已成功套用
    1 = 偵測到要改的內容但沒有 --apply（提醒你加上）
    2 = 前置條件不滿足或執行出錯

⚠️ 離開碼 0 只在「確實查成功且沒事」時才回。前置條件查不到就是 2，不會因為
   「找不到東西要改」而回綠燈 —— 檢查工具最危險的失效方式是回報「沒問題」，
   而不是報錯（見 CHANGELOG [1.96.39]）。
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


# 舊據點 code → 公司名稱（使用者 2026-09-01 指定）
# ⚠️ 用 code 當 key 不用名稱：code 是 unique 且不會被同步改動，名稱會。
DEFAULT_MAP: dict[str, str] = {
    "HQ":       "總公司",
    "MALL_A":   "春大直",
    "MALL_B":   "台中",
    "HOTEL_A":  "樂群",
    "HOTEL_B":  "自由",
    "default":  "總公司",     # 總公司已被 HQ 收編 → 這筆會走「合併」模式
}


def _cmd_hint() -> str:
    exe = sys.executable or "python"
    return f'"{exe}"' if " " in exe else exe


def main() -> int:
    parser = argparse.ArgumentParser(
        description="把舊據點按對照表收斂成公司/部門管理的公司（預設唯讀預覽）",
    )
    parser.add_argument("--apply", action="store_true", help="實際寫入（預設只預覽）")
    parser.add_argument(
        "--map", action="append", default=[], metavar="CODE=公司名",
        help="覆寫對照表的一項（可重複）。例：--map MALL_A=台中",
    )
    args = parser.parse_args()

    mapping = dict(DEFAULT_MAP)
    for item in args.map:
        if "=" not in item:
            print(f"✗ --map 格式錯誤：{item!r}，應為 CODE=公司名")
            return 2
        code, _, cname = item.partition("=")
        mapping[code.strip()] = cname.strip()

    from app.core.database import SessionLocal
    from app.models.reference_data import Company
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.models.user_role import UserRole
    from app.models.ragic_connection import RagicConnection

    db = SessionLocal()
    try:
        # ── 前置條件：source_company_id 欄位存在嗎 ─────────────────────────
        try:
            db.query(Tenant.source_company_id).limit(1).all()
        except Exception as exc:
            db.rollback()
            print("✗ tenants.source_company_id 不存在 —— migration 還沒跑。")
            print("  ⚠️ PG 庫若從沒 stamp 過，要先 stamp 再 upgrade：")
            print(f"      cd backend")
            print(f"      {_cmd_hint()} scripts/alembic_stamp_current.py --apply")
            print(f"      {_cmd_hint()} -m alembic upgrade head")
            print(f"  （原始錯誤：{exc}）")
            return 2

        companies = {c.name: c for c in db.query(Company).all()}
        tenants_by_code = {t.code: t for t in db.query(Tenant).all()}
        mirrors = {
            t.source_company_id: t
            for t in db.query(Tenant).filter(Tenant.source_company_id.isnot(None)).all()
        }

        # ── 驗證對照表：公司必須存在且啟用 ────────────────────────────────
        problems: list[str] = []
        for code, cname in mapping.items():
            if code not in tenants_by_code:
                problems.append(f"據點 code={code} 不存在（對照表寫著 → {cname}）")
                continue
            c = companies.get(cname)
            if c is None:
                problems.append(f"公司「{cname}」不存在（對照表：{code} → {cname}）")
            elif not c.is_active:
                problems.append(f"公司「{cname}」目前是停用狀態（對照表：{code} → {cname}）"
                                "；停用的據點不會出現在下拉，請先啟用")
        if problems:
            print("✗ 對照表驗證失敗，什麼都沒有做：")
            for p in problems:
                print(f"    · {p}")
            print("\n  目前公司/部門管理裡的公司：")
            for name, c in sorted(companies.items()):
                print(f"    {'啟用' if c.is_active else '停用'}  {name}")
            print("\n  目前的據點：")
            for code, t in sorted(tenants_by_code.items()):
                print(f"    {'啟用' if t.is_active else '停用'}  code={code:<14} {t.name}")
            print("\n  → 修好上面的問題，或用 --map CODE=公司名 覆寫對照表。")
            return 2

        # ── 分類：收編（rename）vs 合併（merge）───────────────────────────
        # ⚠️ 順序相依：先把「目標公司還沒有鏡像」的收編掉，剩下的才是合併。
        #    在這個迴圈裡就要把新收編的登記進 planned_mirrors，否則
        #    HQ→總公司 與 default→總公司 會雙雙判成收編、撞 unique。
        planned_mirrors = dict(mirrors)
        to_rename: list[tuple[Tenant, Company]] = []
        to_merge: list[tuple[Tenant, Tenant]] = []      # (舊據點, 目標據點)
        already_ok: list[Tenant] = []

        for code, cname in mapping.items():
            t = tenants_by_code[code]
            c = companies[cname]
            cid = str(c.id)

            if t.source_company_id == cid:
                already_ok.append(t)                    # 這一筆已經處理過了
                continue

            target = planned_mirrors.get(cid)
            if target is None:
                to_rename.append((t, c))
                planned_mirrors[cid] = t
            elif target.id == t.id:
                already_ok.append(t)
            else:
                to_merge.append((t, target))

        # 對照表沒涵蓋到的本地自建據點
        uncovered = [
            t for t in db.query(Tenant).filter(Tenant.source_company_id.is_(None)).all()
            if t.code not in mapping
        ]

        # ── 印出計畫 ──────────────────────────────────────────────────────
        print("=" * 76)
        print("  舊據點 → 公司 收斂計畫")
        print("=" * 76)

        if already_ok:
            print(f"\n【已完成，不再處理】{len(already_ok)} 筆")
            for t in already_ok:
                print(f"    code={t.code:<14} {t.name}")

        print(f"\n【① 收編（改名 + 回填對照鍵，id 不變 → 使用者原封不動）】{len(to_rename)} 筆")
        for t, c in to_rename:
            n_users = db.query(User).filter(User.tenant_id == t.id).count()
            print(f"    code={t.code:<14} 「{t.name}」→「{c.name}」"
                  f"（company_id={c.id}）· 底下 {n_users} 人不受影響")

        print(f"\n【② 合併（使用者改掛目標據點，舊據點停用）】{len(to_merge)} 筆")
        merge_users: list = []
        merge_moves: list = []
        merge_dels: list = []
        for t, target in to_merge:
            us = db.query(User).filter(User.tenant_id == t.id).all()
            merge_users.extend((u, target) for u in us)
            print(f"    code={t.code:<14} 「{t.name}」→ 併入「{target.name}」"
                  f"（code={target.code}）· 要搬 {len(us)} 人")
            for u in us:
                print(f"        - {u.full_name or ''}（{u.email}）")

            # user_roles：UniqueConstraint(user_id, role_id, tenant_id) 去重
            existing = {
                (r.user_id, r.role_id)
                for r in db.query(UserRole).filter(UserRole.tenant_id == target.id).all()
            }
            for r in db.query(UserRole).filter(UserRole.tenant_id == t.id).all():
                key = (r.user_id, r.role_id)
                if key in existing:
                    merge_dels.append(r)
                else:
                    existing.add(key)
                    merge_moves.append((r, target))

        if to_merge:
            print(f"\n    user_roles：改掛 {len(merge_moves)} 筆、刪除重複 {len(merge_dels)} 筆")
            for r in merge_dels:
                print(f"        - 重複而刪除：user_id={r.user_id} role_id={r.role_id}")

        if uncovered:
            print(f"\n⚠ 對照表沒涵蓋到的本地自建據點 {len(uncovered)} 筆 —— **本腳本不動它們**：")
            for t in uncovered:
                n_users = db.query(User).filter(User.tenant_id == t.id).count()
                print(f"    code={t.code:<14} {t.name}（{n_users} 人）")
            print("  → 它們會繼續出現在下拉。要處理請用 --map 補進對照表。")

        # 只示警、不處理
        all_touched = [t for t, _ in to_rename] + [t for t, _ in to_merge]
        n_conns = (
            db.query(RagicConnection)
            .filter(RagicConnection.tenant_id.in_([t.id for t in all_touched]))
            .count()
            if all_touched else 0
        )
        if n_conns:
            print(f"\n⚠ ragic_connections 有 {n_conns} 筆指向這些據點 —— **本腳本不動**。")
            print("  收編模式下 tenant id 不變，它們自動仍然正確；")
            print("  合併模式下改指到別的據點不會讓任何事變好，停用據點也不影響它們運作。")

        if not to_rename and not to_merge:
            print("\n✓ 沒有東西要改。")
            return 0

        if not args.apply:
            print("\n" + "-" * 76)
            print("這是唯讀預覽，什麼都沒有改。確認以上內容後，加上 --apply 實際執行：")
            print(f"    {_cmd_hint()} scripts/migrate_tenants_to_companies.py --apply")
            return 1

        # ── 實際套用 ──────────────────────────────────────────────────────
        # ⚠️ 順序：先收編（拿走 source_company_id），再合併。反過來的話合併的
        #    目標據點可能還沒有對照鍵。
        for t, c in to_rename:
            t.name = c.name
            t.source_company_id = str(c.id)
            t.is_active = c.is_active
            # code／type 刻意不改：舊 code 比自動產生的 CMP-{id} 有意義，
            # 而且 code 已不再顯示在畫面上。
        db.flush()

        for u, target in merge_users:
            u.tenant_id = target.id
        for r in merge_dels:
            db.delete(r)
        db.flush()                # 先讓刪除落地，再改剩下的，避免撞唯一鍵
        for r, target in merge_moves:
            r.tenant_id = target.id
        for t, _ in to_merge:
            t.is_active = False   # ⚠️ 停用不刪除，理由見檔頭（default 尤其不能刪）
        db.commit()

        print("\n" + "=" * 76)
        print(f"✓ 完成：收編 {len(to_rename)} 筆、合併 {len(to_merge)} 筆"
              f"（搬 {len(merge_users)} 人、user_roles 改掛 {len(merge_moves)}／"
              f"刪重複 {len(merge_dels)}）")
        print("=" * 76)
        print("\n目前的據點清單：")
        for t in db.query(Tenant).order_by(Tenant.name).all():
            src = f"← 公司 id={t.source_company_id}" if t.source_company_id else "本地自建"
            print(f"    {'啟用' if t.is_active else '停用'}  code={t.code:<14} "
                  f"{t.name:<16} {src}")
        print("\n請重新整理「人員管理 → 新增使用者」確認下拉。")
        print(f"建議接著跑一次 {_cmd_hint()} scripts/sync_tenants_now.py --apply，")
        print("確認同步端與現況一致（應該是全部『無異動』）。")
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
