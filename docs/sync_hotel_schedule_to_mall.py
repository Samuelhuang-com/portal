"""
班表資料同步：飯店 → 商場（一次性作業，2026-08-14）

用途
────
把飯店班表既有的資料整份複製到商場班表。適用情境是「原本只有一份班表，
資料都在飯店那邊，拆分後要讓商場也有一份起始資料」。

⚠️ 這是**一次性搬運工具**，不是常態同步機制。
   拆分後的設計是兩邊各自匯入、互不干涉（見 docs/SCHEDULE_VENUE_SPLIT_PLAN.md），
   跑完這支腳本之後，兩邊就應該各走各的，不要再定期互相覆蓋。

同步範圍
────────
    schedule_departments   → mall_schedule_departments     （依「部門名稱」比對）
    schedule_shift_types   → mall_schedule_shift_types     （依「班別代碼」比對）
    schedule_staff_members → mall_schedule_staff_members   （依「Excel 原始姓名」比對）
    schedules              → mall_schedules                （依「年、月」比對）
    schedule_details       → mall_schedule_details         （整份重建）

**不同步** `schedule_import_logs` —— 那是「誰在什麼時候匯入了哪個檔案」的稽核紀錄，
複製過去會變成商場端從來沒發生過的假紀錄。

衝突處理：來源端覆蓋目標端
──────────────────────────
商場端已存在的同名部門／同代碼班別／同姓名人員／同年月班表，欄位一律以飯店端為準覆蓋。
被覆蓋的班表，其明細會先整批刪除再重建，確保不會留下舊資料的殘渣。

⚠️ 商場端只有自己有、飯店端沒有的資料（例如商場自行建立的人員）**不會被刪除**，
   只是不會被更新。

ID 對照的處理（這支腳本最容易做錯的地方）
────────────────────────────────────────
兩邊的主鍵都是各自產生的 UUID。商場的班別與部門在後端首次啟動時已由 seed 建立，
代碼雖然相同（N1、Y、E6…）但 **ID 與飯店端不同**。

因此不能直接把飯店的 `schedule_details` 整列搬過去 —— 裡面的
`shift_type_id`、`staff_id`、`schedule_id` 都是飯店端的 ID，搬過去會指向不存在的資料。
本腳本會先建立三張對照表，寫入明細時逐一換成商場端對應的 ID。

新增資料時會盡量沿用飯店端的 UUID（方便日後追溯兩邊的對應關係），
只有在該 UUID 已被商場端佔用時才另外產生新的。

用法
────
    # 預覽（預設，不寫入任何資料）
    cd backend
    python ..\\docs\\sync_hotel_schedule_to_mall.py

    # 正式執行（會先自動備份）
    python ..\\docs\\sync_hotel_schedule_to_mall.py --apply

    # 只同步特定年月（不指定則同步全部）
    python ..\\docs\\sync_hotel_schedule_to_mall.py --apply --year 2026 --month 8

    # 指定資料庫路徑
    python ..\\docs\\sync_hotel_schedule_to_mall.py --apply --db C:\\Portal_Data\\portal.db

前置條件
────────
必須先執行 `docs/migrate_schedule_venue_split.py`（飯店表要有 venue_flag 欄位），
且後端至少啟動過一次（商場的 6 張表由 create_all 建立）。
兩者未完成時本腳本會直接中止並說明原因。

回復
────
`--apply` 前會自動備份，檔名帶時間戳記：
    portal.db.bak_sync_h2m_20260814_143022
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

MALL_VENUE_FLAG = "商"

# ── 來源表 → 目標表 ───────────────────────────────────────────────
PAIRS = [
    ("schedule_departments",   "mall_schedule_departments"),
    ("schedule_shift_types",   "mall_schedule_shift_types"),
    ("schedule_staff_members", "mall_schedule_staff_members"),
    ("schedules",              "mall_schedules"),
    ("schedule_details",       "mall_schedule_details"),
]


# ─────────────────────────────────────────────────────────────────
# 基礎工具
# ─────────────────────────────────────────────────────────────────

def _resolve_db_path(explicit: str | None) -> str:
    if explicit:
        return explicit
    try:
        sys.path.insert(0, os.getcwd())
        from app.core.config import settings  # type: ignore

        url = str(settings.DATABASE_URL)
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "", 1)
        raise SystemExit(f"[中止] 本腳本只支援 SQLite，但設定的是：{url}")
    except ImportError:
        raise SystemExit(
            "[中止] 找不到 app.core.config。\n"
            "       請在 backend/ 目錄下執行，或用 --db 明確指定資料庫路徑。"
        )


def _backup(db_path: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{db_path}.bak_sync_h2m_{stamp}"
    shutil.copy2(db_path, dst)
    return dst


def _table_exists(cur: sqlite3.Cursor, t: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,))
    return cur.fetchone() is not None


def _has_column(cur: sqlite3.Cursor, t: str, c: str) -> bool:
    cur.execute(f"PRAGMA table_info({t})")
    return any(r[1] == c for r in cur.fetchall())


def _preflight(cur: sqlite3.Cursor) -> None:
    """前置條件檢查，任何一項不過就中止。"""
    missing = [t for pair in PAIRS for t in pair if not _table_exists(cur, t)]
    if missing:
        hint = ""
        if any(m.startswith("mall_") for m in missing):
            hint = ("\n       商場的表由 SQLAlchemy create_all 在後端啟動時建立，"
                    "請先啟動一次後端再重跑本腳本。")
        raise SystemExit(f"[中止] 找不到資料表：{', '.join(missing)}{hint}")

    if not _has_column(cur, "schedule_staff_members", "venue_flag"):
        raise SystemExit(
            "[中止] schedule_staff_members 沒有 venue_flag 欄位。\n"
            "       請先執行 docs/migrate_schedule_venue_split.py --apply"
        )


def _cols(cur: sqlite3.Cursor, t: str) -> list[str]:
    cur.execute(f"PRAGMA table_info({t})")
    return [r[1] for r in cur.fetchall()]


def _pick_id(cur: sqlite3.Cursor, table: str, preferred: str, taken: set[str]) -> str:
    """盡量沿用來源端的 UUID，被佔用時才產生新的。"""
    if preferred not in taken:
        cur.execute(f"SELECT 1 FROM {table} WHERE id = ?", (preferred,))
        if cur.fetchone() is None:
            taken.add(preferred)
            return preferred
    new = str(uuid.uuid4())
    taken.add(new)
    return new


# ─────────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="班表資料同步：飯店 → 商場（一次性，來源覆蓋目標）")
    ap.add_argument("--apply", action="store_true", help="實際寫入。未加此參數時只做預覽。")
    ap.add_argument("--db", default=None, help="SQLite 資料庫路徑（預設讀 app.core.config）")
    ap.add_argument("--year", type=int, default=None, help="只同步指定年份的班表")
    ap.add_argument("--month", type=int, default=None, help="只同步指定月份的班表")
    args = ap.parse_args()

    if (args.year is None) != (args.month is None):
        raise SystemExit("[中止] --year 與 --month 必須成對指定，或兩者都不指定（＝全部）。")

    db_path = _resolve_db_path(args.db)
    if not os.path.exists(db_path):
        print(f"[中止] 找不到資料庫：{db_path}")
        return 1

    scope = f"{args.year} 年 {args.month} 月" if args.year else "全部年月"
    print("班表資料同步：飯店 → 商場")
    print(f"資料庫：{db_path}")
    print(f"範圍　：{scope}")
    print(f"模式　：{'正式執行（會寫入）' if args.apply else '預覽（不寫入）'}")
    print("─" * 68)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    _preflight(cur)

    # 備份必須在任何寫入之前
    backup_path = None
    if args.apply:
        backup_path = _backup(db_path)
        print(f"已備份：{backup_path}\n")

    stats: dict[str, dict[str, int]] = {}
    taken_ids: dict[str, set[str]] = {dst: set() for _, dst in PAIRS}

    def bump(table: str, key: str) -> None:
        stats.setdefault(table, {"新增": 0, "覆蓋": 0, "刪除明細": 0})[key] += 1

    try:
        # ── 1. 部門（依名稱比對）────────────────────────────────────
        dept_map: dict[str, str] = {}
        src_cols = [c for c in _cols(cur, "schedule_departments") if c != "id"]
        cur.execute("SELECT * FROM schedule_departments WHERE is_deleted = 0")
        for row in cur.fetchall():
            cur.execute(
                "SELECT id FROM mall_schedule_departments WHERE name = ?", (row["name"],))
            hit = cur.fetchone()
            if hit:
                dept_map[row["id"]] = hit["id"]
                if args.apply:
                    cur.execute(
                        f"UPDATE mall_schedule_departments SET "
                        f"{', '.join(f'{c} = ?' for c in src_cols)} WHERE id = ?",
                        [row[c] for c in src_cols] + [hit["id"]])
                bump("部門", "覆蓋")
            else:
                new_id = _pick_id(cur, "mall_schedule_departments", row["id"],
                                  taken_ids["mall_schedule_departments"])
                dept_map[row["id"]] = new_id
                if args.apply:
                    cur.execute(
                        f"INSERT INTO mall_schedule_departments "
                        f"(id, {', '.join(src_cols)}) VALUES (?{', ?' * len(src_cols)})",
                        [new_id] + [row[c] for c in src_cols])
                bump("部門", "新增")

        # ── 2. 班別（依代碼比對）────────────────────────────────────
        shift_map: dict[str, str] = {}
        src_cols = [c for c in _cols(cur, "schedule_shift_types") if c != "id"]
        cur.execute("SELECT * FROM schedule_shift_types WHERE is_deleted = 0")
        for row in cur.fetchall():
            cur.execute(
                "SELECT id FROM mall_schedule_shift_types WHERE code = ?", (row["code"],))
            hit = cur.fetchone()
            if hit:
                shift_map[row["id"]] = hit["id"]
                if args.apply:
                    cur.execute(
                        f"UPDATE mall_schedule_shift_types SET "
                        f"{', '.join(f'{c} = ?' for c in src_cols)} WHERE id = ?",
                        [row[c] for c in src_cols] + [hit["id"]])
                bump("班別", "覆蓋")
            else:
                new_id = _pick_id(cur, "mall_schedule_shift_types", row["id"],
                                  taken_ids["mall_schedule_shift_types"])
                shift_map[row["id"]] = new_id
                if args.apply:
                    cur.execute(
                        f"INSERT INTO mall_schedule_shift_types "
                        f"(id, {', '.join(src_cols)}) VALUES (?{', ?' * len(src_cols)})",
                        [new_id] + [row[c] for c in src_cols])
                bump("班別", "新增")

        # ── 3. 人員（依 Excel 原始姓名比對；venue_flag 改「商」）────
        staff_map: dict[str, str] = {}
        src_cols = [c for c in _cols(cur, "schedule_staff_members") if c != "id"]
        cur.execute("SELECT * FROM schedule_staff_members WHERE is_deleted = 0")
        for row in cur.fetchall():
            vals = []
            for c in src_cols:
                if c == "venue_flag":
                    vals.append(MALL_VENUE_FLAG)          # 場域標記必須翻面
                elif c == "department_id":
                    vals.append(dept_map.get(row[c]))      # 部門 ID 換成商場端的
                else:
                    vals.append(row[c])

            cur.execute(
                "SELECT id FROM mall_schedule_staff_members WHERE source_name = ?",
                (row["source_name"],))
            hit = cur.fetchone()
            if hit:
                staff_map[row["id"]] = hit["id"]
                if args.apply:
                    cur.execute(
                        f"UPDATE mall_schedule_staff_members SET "
                        f"{', '.join(f'{c} = ?' for c in src_cols)} WHERE id = ?",
                        vals + [hit["id"]])
                bump("人員", "覆蓋")
            else:
                new_id = _pick_id(cur, "mall_schedule_staff_members", row["id"],
                                  taken_ids["mall_schedule_staff_members"])
                staff_map[row["id"]] = new_id
                if args.apply:
                    cur.execute(
                        f"INSERT INTO mall_schedule_staff_members "
                        f"(id, {', '.join(src_cols)}) VALUES (?{', ?' * len(src_cols)})",
                        [new_id] + vals)
                bump("人員", "新增")

        # ── 4. 班表主檔（依年月比對）────────────────────────────────
        sched_map: dict[str, str] = {}
        src_cols = [c for c in _cols(cur, "schedules") if c != "id"]
        where = "WHERE is_deleted = 0"
        params: list = []
        if args.year:
            where += " AND schedule_year = ? AND schedule_month = ?"
            params = [args.year, args.month]
        cur.execute(f"SELECT * FROM schedules {where}", params)
        for row in cur.fetchall():
            cur.execute(
                "SELECT id FROM mall_schedules "
                "WHERE schedule_year = ? AND schedule_month = ? AND is_deleted = 0",
                (row["schedule_year"], row["schedule_month"]))
            hit = cur.fetchone()
            if hit:
                sched_map[row["id"]] = hit["id"]
                if args.apply:
                    cur.execute(
                        f"UPDATE mall_schedules SET "
                        f"{', '.join(f'{c} = ?' for c in src_cols)} WHERE id = ?",
                        [row[c] for c in src_cols] + [hit["id"]])
                    # 覆蓋語意：舊明細整批清掉再重建，避免殘留
                    cur.execute(
                        "DELETE FROM mall_schedule_details WHERE schedule_id = ?", (hit["id"],))
                    for _ in range(cur.rowcount if cur.rowcount > 0 else 0):
                        bump("班表明細", "刪除明細")
                else:
                    cur.execute(
                        "SELECT COUNT(*) c FROM mall_schedule_details WHERE schedule_id = ?",
                        (hit["id"],))
                    for _ in range(cur.fetchone()["c"]):
                        bump("班表明細", "刪除明細")
                bump("班表主檔", "覆蓋")
            else:
                new_id = _pick_id(cur, "mall_schedules", row["id"], taken_ids["mall_schedules"])
                sched_map[row["id"]] = new_id
                if args.apply:
                    cur.execute(
                        f"INSERT INTO mall_schedules "
                        f"(id, {', '.join(src_cols)}) VALUES (?{', ?' * len(src_cols)})",
                        [new_id] + [row[c] for c in src_cols])
                bump("班表主檔", "新增")

        # ── 5. 班表明細（三個外鍵全部重映射）────────────────────────
        src_cols = [c for c in _cols(cur, "schedule_details") if c != "id"]
        orphan_shift = 0
        orphan_staff = 0
        if sched_map:
            qs = ",".join("?" * len(sched_map))
            cur.execute(
                f"SELECT * FROM schedule_details "
                f"WHERE is_deleted = 0 AND schedule_id IN ({qs})", list(sched_map))
            for row in cur.fetchall():
                vals = []
                for c in src_cols:
                    if c == "schedule_id":
                        vals.append(sched_map[row[c]])
                    elif c == "staff_id":
                        if row[c] and row[c] not in staff_map:
                            orphan_staff += 1
                        vals.append(staff_map.get(row[c]) if row[c] else None)
                    elif c == "shift_type_id":
                        if row[c] and row[c] not in shift_map:
                            orphan_shift += 1
                        vals.append(shift_map.get(row[c]) if row[c] else None)
                    else:
                        vals.append(row[c])
                new_id = _pick_id(cur, "mall_schedule_details", row["id"],
                                  taken_ids["mall_schedule_details"])
                if args.apply:
                    cur.execute(
                        f"INSERT INTO mall_schedule_details "
                        f"(id, {', '.join(src_cols)}) VALUES (?{', ?' * len(src_cols)})",
                        [new_id] + vals)
                bump("班表明細", "新增")

        # ── 輸出計畫／結果 ──────────────────────────────────────────
        print(f"{'項目':<10}{'新增':>8}{'覆蓋':>8}{'清除舊明細':>12}")
        print("─" * 68)
        for t in ["部門", "班別", "人員", "班表主檔", "班表明細"]:
            s = stats.get(t, {"新增": 0, "覆蓋": 0, "刪除明細": 0})
            print(f"{t:<10}{s['新增']:>8}{s['覆蓋']:>8}{s['刪除明細']:>12}")

        if orphan_shift or orphan_staff:
            print()
            if orphan_shift:
                print(f"[提醒] {orphan_shift} 筆明細的班別在飯店端已被刪除，"
                      f"商場端的 shift_type_id 會是空值（班別代碼文字仍保留）。")
            if orphan_staff:
                print(f"[提醒] {orphan_staff} 筆明細的人員在飯店端已被刪除，"
                      f"商場端的 staff_id 會是空值（姓名文字仍保留）。")

        if not args.apply:
            conn.rollback()
            conn.close()
            print("\n" + "─" * 68)
            print("以上為預覽，未寫入任何資料。")
            print("確認無誤後，加上 --apply 重跑即可實際執行。")
            return 0

        conn.commit()

    except Exception as exc:
        conn.rollback()
        conn.close()
        print(f"\n[失敗] 已回滾，資料庫未變更：{exc}")
        if backup_path:
            print(f"       備份檔仍保留在：{backup_path}")
        return 1

    # ── 驗證 ────────────────────────────────────────────────────────
    print("\n" + "─" * 68)
    print("驗證：")
    ok = True

    cur.execute("SELECT COUNT(*) c FROM mall_schedule_staff_members WHERE venue_flag != ?",
                (MALL_VENUE_FLAG,))
    bad_flag = cur.fetchone()["c"]
    print(f"  場域標記非「{MALL_VENUE_FLAG}」的商場人員：{bad_flag} 筆" +
          ("" if bad_flag == 0 else "   ← 異常"))
    ok &= bad_flag == 0

    cur.execute("""
        SELECT COUNT(*) c FROM mall_schedule_details d
        LEFT JOIN mall_schedules s ON s.id = d.schedule_id WHERE s.id IS NULL""")
    orphan1 = cur.fetchone()["c"]
    cur.execute("""
        SELECT COUNT(*) c FROM mall_schedule_details d
        LEFT JOIN mall_schedule_staff_members m ON m.id = d.staff_id
        WHERE d.staff_id IS NOT NULL AND m.id IS NULL""")
    orphan2 = cur.fetchone()["c"]
    cur.execute("""
        SELECT COUNT(*) c FROM mall_schedule_details d
        LEFT JOIN mall_schedule_shift_types t ON t.id = d.shift_type_id
        WHERE d.shift_type_id IS NOT NULL AND t.id IS NULL""")
    orphan3 = cur.fetchone()["c"]
    print(f"  外鍵指向不存在的資料：班表 {orphan1}、人員 {orphan2}、班別 {orphan3}" +
          ("" if orphan1 + orphan2 + orphan3 == 0 else "   ← 異常"))
    ok &= (orphan1 + orphan2 + orphan3) == 0

    print("\n  兩邊資料筆數對照：")
    for src, dst in PAIRS:
        cur.execute(f"SELECT COUNT(*) c FROM {src} WHERE is_deleted = 0")
        a = cur.fetchone()["c"]
        cur.execute(f"SELECT COUNT(*) c FROM {dst} WHERE is_deleted = 0")
        b = cur.fetchone()["c"]
        print(f"    {src:<24} {a:>6}   →   {dst:<28} {b:>6}")

    conn.close()

    print("\n" + "─" * 68)
    if not ok:
        print("[警告] 驗證未全數通過，請檢查上方標示「異常」的項目。")
        print(f"       備份檔：{backup_path}")
        return 1

    print("同步完成。")
    print("\n提醒：這是一次性搬運，跑完之後兩邊就各走各的。")
    print("      請到「商場管理 → 商場班表」確認資料，並依商場實際情況調整班別時段。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
