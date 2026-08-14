"""
班表權限 key 轉換腳本（2026-08-14）

背景
────
班表模組於 2026-08-14 拆分為「飯店班表」與「商場班表」兩套獨立模組，
原本的 3 個權限 key 拆成 6 個：

    schedule_view    →  hotel_schedule_view   + mall_schedule_view
    schedule_manage  →  hotel_schedule_manage + mall_schedule_manage
    schedule_admin   →  hotel_schedule_admin  + mall_schedule_admin

⚠️ 部署順序（非常重要）
────────────────────
    1. 先執行本腳本（正式模式）
    2. 再部署新版程式碼

順序顛倒的話，所有非 system_admin 的使用者會有一段時間完全打不開班表頁面
（新程式碼查 hotel_schedule_view，但資料庫裡只有舊的 schedule_view）。

system_admin 持有萬用符 "*"，不受影響、也不需要轉換。

用法
────
    # 預覽（預設，不寫入任何資料）
    cd backend
    python ..\\docs\\migrate_schedule_permissions.py

    # 正式執行（會先自動備份資料庫）
    python ..\\docs\\migrate_schedule_permissions.py --apply

    # 指定資料庫路徑（預設讀 app.core.config 的設定）
    python ..\\docs\\migrate_schedule_permissions.py --apply --db C:\\Portal_Data\\portal.db

回復
────
腳本會在 --apply 前把資料庫複製一份到同目錄，檔名帶時間戳記，例如：
    portal.db.bak_schedule_perm_20260814_143022
要回復直接把備份檔複製回去即可（需先停掉後端服務）。
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime

# ── 轉換對照表 ────────────────────────────────────────────────────
MAPPING: dict[str, list[str]] = {
    "schedule_view":   ["hotel_schedule_view",   "mall_schedule_view"],
    "schedule_manage": ["hotel_schedule_manage", "mall_schedule_manage"],
    "schedule_admin":  ["hotel_schedule_admin",  "mall_schedule_admin"],
}

OLD_KEYS = list(MAPPING.keys())


def _resolve_db_path(explicit: str | None) -> str:
    """決定要操作的資料庫檔案路徑。"""
    if explicit:
        return explicit

    # 嘗試從專案設定讀取（需要在 backend/ 目錄下執行）
    try:
        sys.path.insert(0, os.getcwd())
        from app.core.config import settings  # type: ignore

        url = str(settings.DATABASE_URL)
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "", 1)
        raise SystemExit(
            f"[中止] 本腳本只支援 SQLite，但設定的是：{url}\n"
            f"       若已遷移到其他資料庫，請改用對應的 SQL 手動轉換。"
        )
    except ImportError:
        raise SystemExit(
            "[中止] 找不到 app.core.config。\n"
            "       請在 backend/ 目錄下執行，或用 --db 明確指定資料庫路徑。"
        )


def _backup(db_path: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{db_path}.bak_schedule_perm_{stamp}"
    shutil.copy2(db_path, dst)
    return dst


def main() -> int:
    ap = argparse.ArgumentParser(description="班表權限 key 轉換（schedule_* → hotel_/mall_schedule_*）")
    ap.add_argument("--apply", action="store_true", help="實際寫入。未加此參數時只做預覽。")
    ap.add_argument("--db", default=None, help="SQLite 資料庫路徑（預設讀 app.core.config）")
    args = ap.parse_args()

    db_path = _resolve_db_path(args.db)
    if not os.path.exists(db_path):
        print(f"[中止] 找不到資料庫：{db_path}")
        return 1

    print(f"資料庫：{db_path}")
    print(f"模式　：{'正式執行（會寫入）' if args.apply else '預覽（不寫入）'}")
    print("─" * 64)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── 1. 讀出所有持有舊 key 的角色 ──────────────────────────────
    placeholders = ",".join("?" * len(OLD_KEYS))
    cur.execute(
        f"""
        SELECT rp.id, rp.role_id, rp.permission_key, r.name AS role_name
        FROM role_permissions rp
        LEFT JOIN roles r ON r.id = rp.role_id
        WHERE rp.permission_key IN ({placeholders})
        ORDER BY r.name, rp.permission_key
        """,
        OLD_KEYS,
    )
    old_rows = cur.fetchall()

    if not old_rows:
        print("沒有任何角色持有舊的 schedule_* 權限，不需要轉換。")
        print("（若這是重跑，代表先前已經轉換完成。）")
        conn.close()
        return 0

    # ── 2. 讀出已存在的新 key，避免重複插入 ──────────────────────
    new_keys = [k for ks in MAPPING.values() for k in ks]
    cur.execute(
        f"SELECT role_id, permission_key FROM role_permissions "
        f"WHERE permission_key IN ({','.join('?' * len(new_keys))})",
        new_keys,
    )
    existing_new = {(r["role_id"], r["permission_key"]) for r in cur.fetchall()}

    # ── 3. 規劃動作 ──────────────────────────────────────────────
    to_insert: list[tuple[str, str, str]] = []   # (role_id, role_name, new_key)
    to_delete: list[str] = []                    # role_permissions.id
    skipped:   list[tuple[str, str]] = []        # (role_name, new_key) 已存在

    for row in old_rows:
        role_id   = row["role_id"]
        role_name = row["role_name"] or f"(未知角色 {role_id[:8]})"
        for new_key in MAPPING[row["permission_key"]]:
            if (role_id, new_key) in existing_new:
                skipped.append((role_name, new_key))
            else:
                to_insert.append((role_id, role_name, new_key))
                existing_new.add((role_id, new_key))
        to_delete.append(row["id"])

    # ── 4. 輸出計畫 ──────────────────────────────────────────────
    by_role: dict[str, list[str]] = {}
    for _, role_name, new_key in to_insert:
        by_role.setdefault(role_name, []).append(new_key)

    print(f"將新增 {len(to_insert)} 筆權限：")
    for role_name in sorted(by_role):
        print(f"  {role_name}")
        for k in sorted(by_role[role_name]):
            print(f"      + {k}")

    if skipped:
        print(f"\n已存在、略過 {len(skipped)} 筆：")
        for role_name, k in sorted(set(skipped)):
            print(f"      = {role_name} / {k}")

    print(f"\n將刪除 {len(to_delete)} 筆舊 key（{', '.join(OLD_KEYS)}）")

    # ── 5. 執行 ──────────────────────────────────────────────────
    if not args.apply:
        print("\n" + "─" * 64)
        print("以上為預覽，未寫入任何資料。")
        print("確認無誤後，加上 --apply 重跑即可實際執行。")
        conn.close()
        return 0

    backup_path = _backup(db_path)
    print(f"\n已備份：{backup_path}")

    try:
        cur.executemany(
            "INSERT INTO role_permissions (id, role_id, permission_key) VALUES (?, ?, ?)",
            [(str(uuid.uuid4()), role_id, key) for role_id, _, key in to_insert],
        )
        cur.executemany(
            "DELETE FROM role_permissions WHERE id = ?",
            [(rid,) for rid in to_delete],
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        conn.close()
        print(f"\n[失敗] 已回滾，資料庫未變更：{exc}")
        print(f"       備份檔仍保留在：{backup_path}")
        return 1

    # ── 6. 驗證 ──────────────────────────────────────────────────
    cur.execute(
        f"SELECT COUNT(*) FROM role_permissions WHERE permission_key IN ({placeholders})",
        OLD_KEYS,
    )
    remaining = cur.fetchone()[0]
    cur.execute(
        f"SELECT COUNT(*) FROM role_permissions "
        f"WHERE permission_key IN ({','.join('?' * len(new_keys))})",
        new_keys,
    )
    total_new = cur.fetchone()[0]
    conn.close()

    print("\n" + "─" * 64)
    print(f"完成。舊 key 殘留 {remaining} 筆（應為 0），新 key 共 {total_new} 筆。")
    if remaining:
        print("[警告] 舊 key 未清乾淨，請檢查。")
        return 1
    print("\n接下來才可以部署新版程式碼。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
