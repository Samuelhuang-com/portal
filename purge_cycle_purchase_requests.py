"""
週期採購 — 清空「請購單 + 彙整單」資料（2026-08-09，與 Samuel 確認）

用途：
    測試期間累積的請購單／彙整單資料已經很亂，需要整批清掉重來。
    這支腳本**只刪交易資料，不動任何主檔**。

【會刪的（3 張表 + 1 類日誌）】
    cycle_purchase_request_items   請購明細
    cycle_purchase_requests        請購單
    cycle_purchase_summary         彙整單
    cycle_purchase_audit_logs      只刪 document_type='request' 的列

【絕對不會動的】
    cycle_purchase_cycles          週期設定
    cycle_purchase_departments     部門主檔
    cycle_purchase_cost_centers    成本中心主檔
    cycle_purchase_account_codes   會計科目主檔
    cycle_purchase_items           料號主檔
    cycle_purchase_item_mappings   料號對照表
    cycle_purchase_vendors         供應商主檔
    cycle_purchase_pos / po_items          採購單
    cycle_purchase_receiving / receiving_items   驗收
    cycle_purchase_payments / ...          付款

────────────────────────────────────────────────────────────────────────────
⚠️ 執行前必讀
────────────────────────────────────────────────────────────────────────────

1) **有採購單引用彙整列時，腳本會直接中止，不會刪任何東西。**
   `cycle_purchase_po_items.summary_id` 的外鍵是 `ondelete="RESTRICT"`，
   而這個資料庫 `PRAGMA foreign_keys=ON`（見 core/cycle_purchase_database.py）。
   硬刪會被資料庫擋下來，或（若關掉 FK）留下指向不存在彙整列的採購明細。
   遇到這個情況，腳本會列出是哪幾張採購單，由你決定：
     - 那些採購單也不要了 → 先手動清掉採購／驗收／付款，再跑這支
     - 那些採購單要保留   → 改用 `--requests-only`，只刪請購單、保留彙整單
                            （⚠️ 見下方第 3 點的批次號撞號問題）

2) **請先停掉後端服務再執行。** WAL 模式下邊跑邊刪不會壞資料，但服務記憶體裡
   可能還握著已被刪掉的資料，畫面會出現看不懂的錯誤。

3) ⚠️ **彙整批次號會從 001 重新起算。**
   `_next_summary_generate_batch_no()` 的流水號是去數「請購單上的
   summary_batch_no」，請購單清空後計數歸零。
     - 預設模式（請購單 + 彙整單一起清）：兩邊都空了，不會撞號。
     - `--requests-only` 模式：既有彙整列還在，但計數基準沒了，
       下次產生彙整會產出與既有彙整列**重複的批次號**。

4) **稽核日誌實測上大概不會有東西可刪。** 目前程式碼裡只有 receiving／payment
   兩處會寫稽核日誌（`document_type='receiving'`／`'payment'`），
   沒有任何地方寫 `'request'`。這一步是為了保險，不是因為預期有資料。

────────────────────────────────────────────────────────────────────────────
用法
────────────────────────────────────────────────────────────────────────────

    # 測試區（預設路徑），會先顯示筆數並要你打字確認
    python purge_cycle_purchase_requests.py

    # 指定資料庫（正式區在另一台機器，把路徑帶進來）
    python purge_cycle_purchase_requests.py --db "D:\\portal_data\\cycle-purchase.db"

    # 只刪請購單、保留彙整單（請先讀上面第 1、3 點）
    python purge_cycle_purchase_requests.py --requests-only

    # 順便把 id 流水號歸零
    # （多數情況不需要：這些表用的是一般 rowid 主鍵，清空後 id 本來就從 1 開始）
    python purge_cycle_purchase_requests.py --reset-ids

    # 跳過互動確認（自動化用；仍然會備份）
    python purge_cycle_purchase_requests.py --yes

備份：執行前一定會用 SQLite 官方 backup API 產生一份完整快照
      （`cycle-purchase.db.backup-YYYYMMDD-HHMMSS`），放在原資料庫旁邊。
      這比直接複製檔案可靠——WAL 模式下光複製 .db 會漏掉還沒 checkpoint 的
      交易。要還原就是把備份檔改回原檔名（先停服務）。
      `--no-backup` 可以跳過，但沒有理由這樣做。
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime

DEFAULT_DB_PATH = r"C:\portal_data\cycle-purchase.db"

# 會被清空的表（順序就是實際刪除順序：先子表再父表，
# 雖然 request_items 有 ON DELETE CASCADE，還是明確刪一次，
# 這樣事後的筆數報告才對得起來）
TABLES_FULL = [
    ("cycle_purchase_request_items", "請購明細"),
    ("cycle_purchase_requests", "請購單"),
    ("cycle_purchase_summary", "彙整單"),
]
TABLES_REQUESTS_ONLY = [
    ("cycle_purchase_request_items", "請購明細"),
    ("cycle_purchase_requests", "請購單"),
]

# 只看不動，用來讓使用者確認「主檔沒被碰到」
TABLES_UNTOUCHED = [
    ("cycle_purchase_cycles", "週期設定"),
    ("cycle_purchase_departments", "部門主檔"),
    ("cycle_purchase_items", "料號主檔"),
    ("cycle_purchase_item_mappings", "料號對照表"),
    ("cycle_purchase_vendors", "供應商主檔"),
    ("cycle_purchase_pos", "採購單"),
    ("cycle_purchase_receiving", "驗收單"),
    ("cycle_purchase_payments", "付款單"),
]


def count_of(con, table):
    """表不存在時回傳 None，而不是讓整支腳本炸掉。"""
    try:
        return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.OperationalError:
        return None


def fmt(n):
    return "（表不存在）" if n is None else f"{n:,} 筆"


def check_po_blocking(con):
    """
    找出「被採購單引用、因此不能刪」的彙整列。

    回傳 (blocked_summary_count, [(po_no, 引用列數), ...])。
    這個檢查要在刪除前做完，不是等資料庫丟 FK 錯誤才處理——
    刪到一半才失敗的話，request 已經刪了、summary 沒刪，狀態比原本更糟。
    """
    try:
        rows = con.execute(
            """
            SELECT p.po_no, COUNT(DISTINCT pi.summary_id)
            FROM cycle_purchase_po_items pi
            JOIN cycle_purchase_pos p ON p.id = pi.po_id
            GROUP BY p.po_no
            ORDER BY p.po_no
            """
        ).fetchall()
    except sqlite3.OperationalError:
        return 0, []

    total = con.execute(
        "SELECT COUNT(DISTINCT summary_id) FROM cycle_purchase_po_items"
    ).fetchone()[0]
    return total, rows


def make_backup(db_path):
    """用 SQLite 官方 backup API 產生一致的快照（WAL 模式下直接複製檔案會漏交易）。"""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest_path = f"{db_path}.backup-{stamp}"
    src = sqlite3.connect(db_path)
    dest = sqlite3.connect(dest_path)
    try:
        with dest:
            src.backup(dest)
    finally:
        dest.close()
        src.close()
    size_mb = os.path.getsize(dest_path) / 1024 / 1024
    print(f"[備份] 已建立：{dest_path}（{size_mb:.1f} MB）")
    return dest_path


def main():
    parser = argparse.ArgumentParser(
        description="清空週期採購的請購單／彙整單資料（不動任何主檔）"
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help=f"資料庫路徑（預設 {DEFAULT_DB_PATH}）")
    parser.add_argument("--requests-only", action="store_true",
                        help="只刪請購單，保留彙整單（⚠️ 會造成彙整批次號撞號，見檔頭第 3 點）")
    parser.add_argument("--reset-ids", action="store_true",
                        help="把被清空的表的 AUTOINCREMENT 流水號歸零（多數情況不需要，"
                             "這些表用的是一般 rowid 主鍵，清空後 id 本來就從 1 開始）")
    parser.add_argument("--keep-audit", action="store_true",
                        help="保留 document_type='request' 的稽核日誌")
    parser.add_argument("--no-backup", action="store_true", help="跳過備份（不建議）")
    parser.add_argument("--yes", action="store_true", help="跳過互動確認")
    args = parser.parse_args()

    db_path = args.db
    print("=" * 72)
    print("週期採購 — 清空請購單／彙整單")
    print("=" * 72)
    print(f"資料庫：{db_path}")

    if not os.path.exists(db_path):
        print(f"\n[錯誤] 找不到資料庫檔案：{db_path}")
        print("       請用 --db 指定正確路徑，例如：")
        print('       python purge_cycle_purchase_requests.py --db "D:\\portal_data\\cycle-purchase.db"')
        sys.exit(1)

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA busy_timeout=60000")
    con.execute("PRAGMA foreign_keys=ON")   # 與後端行為一致，不偷偷關掉

    targets = TABLES_REQUESTS_ONLY if args.requests_only else TABLES_FULL

    # ── 1. 現況 ────────────────────────────────────────────────────────────
    print("\n【會被清空的資料】")
    before = {}
    for table, label in targets:
        before[table] = count_of(con, table)
        print(f"  {label:<10} {table:<32} {fmt(before[table])}")

    audit_count = 0
    if not args.keep_audit:
        try:
            audit_count = con.execute(
                "SELECT COUNT(*) FROM cycle_purchase_audit_logs WHERE document_type = 'request'"
            ).fetchone()[0]
        except sqlite3.OperationalError:
            audit_count = 0
        print(f"  {'稽核日誌':<10} {'audit_logs (document_type=request)':<32} {audit_count:,} 筆")

    print("\n【不會被動到的資料】")
    for table, label in TABLES_UNTOUCHED:
        print(f"  {label:<10} {table:<32} {fmt(count_of(con, table))}")

    total_to_delete = sum(v for v in before.values() if v) + audit_count
    if total_to_delete == 0:
        print("\n沒有任何資料需要清除，結束。")
        con.close()
        return

    # ── 2. 擋路檢查：採購單引用彙整列 ──────────────────────────────────────
    if not args.requests_only:
        blocked, po_rows = check_po_blocking(con)
        if blocked > 0:
            print("\n" + "!" * 72)
            print("[中止] 有採購單正在引用彙整列，不能刪除彙整單 —— 沒有刪除任何資料。")
            print("!" * 72)
            print(f"\n  被引用的彙整列：{blocked} 列，來自以下採購單：")
            for po_no, cnt in po_rows:
                print(f"    · {po_no}（引用 {cnt} 列彙整）")
            print("\n  原因：cycle_purchase_po_items.summary_id 的外鍵是 ondelete=RESTRICT，")
            print("        且本資料庫 PRAGMA foreign_keys=ON。硬刪會被資料庫擋下，")
            print("        或留下指向不存在彙整列的採購明細。")
            print("\n  你可以選一條路：")
            print("    (A) 那些採購單也不要了 → 先清掉採購／驗收／付款資料，再重跑這支腳本")
            print("    (B) 那些採購單要保留   → 改用 --requests-only（只刪請購單）")
            print("        ⚠️ 但請先讀腳本開頭第 3 點：彙整批次號會撞號")
            con.close()
            sys.exit(2)

    # ── 3. 確認 ────────────────────────────────────────────────────────────
    print("\n" + "-" * 72)
    print(f"總共將刪除 {total_to_delete:,} 筆資料。**這個動作不可復原**（備份除外）。")
    if args.requests_only:
        print("⚠️ --requests-only：彙整單會保留，但下次產生彙整的批次號會與既有的重複。")
    print("-" * 72)

    if not args.yes:
        answer = input('\n確定要執行嗎？請輸入 DELETE（大寫）後按 Enter，其他任何輸入都會取消：')
        if answer.strip() != "DELETE":
            print("已取消，沒有刪除任何資料。")
            con.close()
            return

    # ── 4. 備份 ────────────────────────────────────────────────────────────
    if not args.no_backup:
        try:
            make_backup(db_path)
        except Exception as e:
            print(f"\n[錯誤] 備份失敗，為了安全起見中止：{e}")
            print("       如果你確定不需要備份，可以加 --no-backup 重跑（自負風險）。")
            con.close()
            sys.exit(1)
    else:
        print("[備份] 已依 --no-backup 跳過")

    # ── 5. 刪除（單一交易，全成功或全回復）────────────────────────────────
    print("\n【開始刪除】")
    try:
        with con:   # with block 正常結束會 commit，丟例外會 rollback
            for table, label in targets:
                if before[table] is None:
                    print(f"  [略過] {label}（{table} 不存在）")
                    continue
                cur = con.execute(f"DELETE FROM {table}")
                print(f"  [完成] {label:<10} 刪除 {cur.rowcount:,} 筆")

            if not args.keep_audit and audit_count > 0:
                cur = con.execute(
                    "DELETE FROM cycle_purchase_audit_logs WHERE document_type = 'request'"
                )
                print(f"  [完成] {'稽核日誌':<10} 刪除 {cur.rowcount:,} 筆")

            if args.reset_ids:
                # ⚠️ sqlite_sequence 只有在「真的用了 AUTOINCREMENT 關鍵字」的資料庫才存在。
                # SQLAlchemy 的 Column(Integer, primary_key=True, autoincrement=True) 產生的是
                # 普通的 INTEGER PRIMARY KEY（rowid），**不會**建立 sqlite_sequence。
                # 沒有這張表時直接查會噴 "no such table: sqlite_sequence" 讓整批刪除回復，
                # 所以先確認存在再動它。
                has_seq = con.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
                ).fetchone()
                if has_seq:
                    for table, label in targets:
                        if before[table] is None:
                            continue
                        con.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
                    print("  [完成] AUTOINCREMENT 流水號已歸零")
                else:
                    print("  [略過] 這個資料庫沒有 sqlite_sequence（表用的是一般 rowid 主鍵）；")
                    print("         清空後 id 本來就會從 1 重新開始，--reset-ids 不需要做任何事")
    except Exception as e:
        print(f"\n[錯誤] 刪除失敗，已全部回復（沒有刪掉任何東西）：{e}")
        con.close()
        sys.exit(1)

    # ── 6. 驗證 ────────────────────────────────────────────────────────────
    print("\n【刪除後確認】")
    all_clear = True
    for table, label in targets:
        if before[table] is None:
            continue
        after = count_of(con, table)
        ok = after == 0
        all_clear = all_clear and ok
        print(f"  {label:<10} {table:<32} {fmt(after)} {'✅' if ok else '⚠️ 沒有清乾淨'}")

    print("\n【主檔確認（應與執行前完全相同）】")
    for table, label in TABLES_UNTOUCHED:
        print(f"  {label:<10} {table:<32} {fmt(count_of(con, table))}")

    con.execute("VACUUM")   # 把刪掉的空間還給檔案系統
    con.close()

    print("\n" + "=" * 72)
    if all_clear:
        print("✅ 完成。請重新啟動後端服務，再重新整理「週期採購」頁面。")
        print("   下一張請購單會是 PR-YYYY-MM-001（單號流水號本來就是依當月筆數計算）。")
    else:
        print("⚠️ 有表沒有清乾淨，請看上面的訊息。備份檔還在，必要時可以還原。")
    print("=" * 72)


if __name__ == "__main__":
    main()
