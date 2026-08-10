"""
週期採購 migration 狀態「唯讀」檢查器（2026-08-07）

用途：
  只是「看一眼」cycle-purchase.db 目前的欄位狀態，回答一個問題——
  `apply_cycle_purchase_summary_migration.py` 到底跑過了沒有？

  這支腳本**完全不會寫入任何東西**（用 SQLite 的 file:...?mode=ro 唯讀模式
  開檔），所以就算在後端服務執行中、或不確定資料庫現況時，也可以安全執行。
  真正要補欄位請執行 apply_cycle_purchase_summary_migration.py（或 .bat）。

⚠️ 週採目前有**兩支**互相獨立的 migration，這裡兩支都會檢查：
     A. apply_cycle_purchase_summary_migration.py  → 補欄位（可重複執行）
     B. apply_cycle_purchase_po_unique_migration.py → 採購單唯一鍵整表重建
   跑過 A 不代表跑過 B。B 沒跑的症狀是「退回彙整單」可以按，但**重新轉單會撞
   UNIQUE constraint**。

檢查四件事：
  1. cycle_purchase_summary 的 6 個部門別／Ragic 拋轉欄位在不在
  2. cycle_purchase_requests 的 15 個欄位（已彙整＋關閉／重新開啟＋退回彙整）在不在
  2b. cycle_purchase_cycles 的 applicable_department_ids 在不在
  3. 舊資料一次性轉換（status='approved' -> is_closed=True）做過了沒有
  4. cycle_purchase_pos 的 partial unique index 在不在（← 這一項對應 B）

用法：
    python verify_cycle_purchase_migration.py

或者直接雙擊同資料夾裡的 verify_cycle_purchase_migration.bat
"""

import os
import sqlite3
import sys

from migration_db_path import resolve_db_path

# 2026-08-10：路徑不再寫死。優先序為 --db 參數 > backend/.env 的
# CYCLE_PURCHASE_DATABASE_URL > 下面這個預設值（見 migration_db_path.py 的說明）。
DEFAULT_DB_PATH = r"C:\portal_data\cycle-purchase.db"

# 一次性資料轉換用的識別批次號，必須與 apply_cycle_purchase_summary_migration.py
# 的 LEGACY_CONVERT_BATCH_NO 保持一致。
LEGACY_CONVERT_BATCH_NO = "LEGACY-CONVERT-20260717"

# 2026-08-09：採購單唯一鍵改成 partial unique index 後的索引名稱，必須與
# apply_cycle_purchase_po_unique_migration.py 及 models/cycle_purchase_po.py 一致。
PO_PARTIAL_INDEX_NAME = "uq_cp_po_active_cycle_period_company_vendor"

# (資料表名稱, 這次改版應該要有的欄位, 這批欄位是哪一次調整加的)
EXPECTED = [
    (
        "cycle_purchase_summary",
        [
            "department_id",
            "ragic_push_batch_no",
            "ragic_pushed",
            "ragic_record_id",
            "ragic_pushed_at",
            "ragic_push_error",
        ],
        "第一次調整：彙整單部門別＋Ragic 拋轉追蹤（CHANGELOG [1.80.51]）",
    ),
    (
        "cycle_purchase_requests",
        [
            "is_summarized",
            "summary_batch_no",
            "summarized_at",
        ],
        "第二次調整：彙整單改用勾選請購單產生（CHANGELOG [1.80.52]）",
    ),
    (
        "cycle_purchase_requests",
        [
            "is_closed",
            "closed_by_user_id",
            "closed_by_name",
            "closed_at",
            "close_batch_no",
            "reopened_by_user_id",
            "reopened_by_name",
            "reopened_at",
        ],
        "第三次調整：請購單拿掉送出／核准，改成關閉／重新開啟（CHANGELOG [1.80.53]）",
    ),
    (
        "cycle_purchase_cycles",
        [
            "applicable_department_ids",
        ],
        "第四次調整：週期設定的適用部門（CHANGELOG [1.90.23]）"
        "　⚠️ 這個欄位缺了會讓 GET /cycles 直接 500，"
        "Dashboard 三個統計卡片會因為 Promise.all 一起失敗而全部停在 0",
    ),
    (
        "cycle_purchase_requests",
        [
            "unsummarized_by_user_id",
            "unsummarized_by_name",
            "unsummarized_at",
            "unsummarize_reason",
        ],
        "第五次調整：彙整單退回請購單（CHANGELOG [1.90.24]）"
        "　⚠️ 這批欄位缺了會讓所有查請購單的端點 500（含 Dashboard 的「我的待辦」）",
    ),
]


def open_readonly(path):
    """用唯讀模式開啟資料庫，確保這支腳本不可能改到任何資料。"""
    if not os.path.exists(path):
        print(f"[錯誤] 找不到資料庫檔案：{path}")
        print("       請確認路徑是否正確（可對照 backend/.env 的 CYCLE_PURCHASE_DATABASE_URL）。")
        print("       也可以直接指定：--db <路徑>")
        return None
    # 2026-08-10：0 bytes 空檔要當成錯誤，不能只是「每張表都找不到」。
    # 空殼檔的檢查結果與「真的還沒跑 migration」長得一模一樣，正式區就是在這裡
    # 被誤導了一輪——結論會叫人去跑 apply，而 apply 又會在同一個空檔上「成功」。
    if os.path.getsize(path) == 0:
        print(f"[錯誤] 這個檔案是 0 bytes 的空檔：{path}")
        print("       多半是先前某次腳本誤建出來的空殼，不是真正的資料庫。")
        print("       請用 --db 指定正確路徑，並把這個空檔刪掉。")
        return None
    uri = "file:{}?mode=ro".format(path.replace("\\", "/"))
    try:
        return sqlite3.connect(uri, uri=True)
    except sqlite3.Error as e:
        print(f"[錯誤] 無法以唯讀模式開啟資料庫：{e}")
        return None


def table_columns(con, table_name):
    """回傳這張表目前實際有的欄位集合；表不存在回傳 None。"""
    try:
        rows = con.execute(f"PRAGMA table_info({table_name})").fetchall()
    except sqlite3.Error as e:
        print(f"[錯誤] 無法讀取 {table_name} 的欄位資訊：{e}")
        return None
    if not rows:
        return None
    return {r[1] for r in rows}


def check_columns(con):
    """逐批檢查欄位，回傳 (全部都在嗎, 缺少的欄位清單)。"""
    all_ok = True
    missing_all = []

    for table_name, expected_cols, note in EXPECTED:
        print(f"--- {table_name} ---")
        print(f"    {note}")

        existing = table_columns(con, table_name)
        if existing is None:
            print(f"    [錯誤] 找不到資料表 {table_name}（PRAGMA 回傳空清單）。")
            print("           請確認後端至少正常啟動過一次（啟動時會 create_all 建表）。")
            all_ok = False
            missing_all.extend(expected_cols)
            print()
            continue

        missing = [c for c in expected_cols if c not in existing]
        present = [c for c in expected_cols if c in existing]

        if present:
            print(f"    ✅ 已存在（{len(present)}/{len(expected_cols)}）：{present}")
        if missing:
            print(f"    ❌ 還缺少（{len(missing)}）：{missing}")
            all_ok = False
            missing_all.extend(missing)
        print()

    return all_ok, missing_all


def check_legacy_conversion(con):
    """檢查舊資料 approved -> is_closed 的一次性轉換做過了沒有。"""
    print("--- 舊資料一次性轉換（status='approved' -> is_closed=True）---")

    cols = table_columns(con, "cycle_purchase_requests")
    if cols is None:
        print("    [略過] 找不到 cycle_purchase_requests，無法檢查。")
        print()
        return None
    if "is_closed" not in cols or "close_batch_no" not in cols:
        print("    [略過] is_closed／close_batch_no 欄位還沒補上，轉換一定還沒做。")
        print("           請先執行 apply_cycle_purchase_summary_migration.py。")
        print()
        return False

    try:
        converted = con.execute(
            "SELECT COUNT(*) FROM cycle_purchase_requests WHERE close_batch_no = ?",
            (LEGACY_CONVERT_BATCH_NO,),
        ).fetchone()[0]
        pending = con.execute(
            "SELECT COUNT(*) FROM cycle_purchase_requests "
            "WHERE status = 'approved' AND close_batch_no IS NULL"
        ).fetchone()[0]
        total = con.execute("SELECT COUNT(*) FROM cycle_purchase_requests").fetchone()[0]
        closed_now = con.execute(
            "SELECT COUNT(*) FROM cycle_purchase_requests WHERE is_closed = 1"
        ).fetchone()[0]
    except sqlite3.Error as e:
        print(f"    [錯誤] 查詢失敗：{e}")
        print()
        return None

    print(f"    請購單總筆數：{total}　／　目前 is_closed=True：{closed_now}")
    print(f"    已被本腳本轉換過（批次號 {LEGACY_CONVERT_BATCH_NO}）：{converted} 筆")
    print(f"    仍待轉換（status='approved' 且 close_batch_no IS NULL）：{pending} 筆")

    if pending > 0:
        print("    ❌ 還有舊資料沒轉換 —— 這些單會卡住，永遠不會出現在彙整單的可勾選清單。")
        print()
        return False

    if converted > 0:
        print("    ✅ 轉換已完成。")
    else:
        print("    ✅ 沒有需要轉換的舊資料（這個資料庫本來就沒有 approved 狀態的單）。")
    print()
    return True


def check_po_unique_index(con):
    """檢查採購單的唯一鍵是不是已經換成 partial unique index（2026-08-09，
    對應 apply_cycle_purchase_po_unique_migration.py）。

    這是**另一支** migration。欄位那支（apply_cycle_purchase_summary_migration.py）
    跑過並不代表這支跑過——兩支互相獨立，輸出也長得不一樣。沒跑的話症狀是：
    採購單「退回彙整單」可以用，但**重新轉單會撞 UNIQUE constraint**。"""
    print("--- 採購單唯一鍵（cycle_purchase_pos）---")
    print("    對應 apply_cycle_purchase_po_unique_migration.py（**與欄位那支是不同的腳本**）")

    try:
        rows = con.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='index' AND tbl_name='cycle_purchase_pos'"
        ).fetchall()
    except sqlite3.Error as e:
        print(f"    [錯誤] 無法讀取索引資訊：{e}")
        print()
        return None

    if not rows:
        print("    [錯誤] 找不到 cycle_purchase_pos 的任何索引，資料表可能不存在。")
        print()
        return None

    target = [r for r in rows if r[0] == PO_PARTIAL_INDEX_NAME]
    if target:
        sql = (target[0][1] or "").replace("\n", " ")
        print(f"    ✅ 已存在：{PO_PARTIAL_INDEX_NAME}")
        print(f"       {sql}")
        if "cancelled" not in sql:
            print("    ⚠️ 但這個索引的條件裡沒有 cancelled，請確認是不是被人手動改過。")
            print()
            return False
        print()
        return True

    print(f"    ❌ 找不到 {PO_PARTIAL_INDEX_NAME}")
    print(f"       目前的索引：{[r[0] for r in rows]}")
    print("       症狀：「退回彙整單」可以按，但**退回後重新轉單會失敗**，訊息是")
    print("             UNIQUE constraint failed: cycle_purchase_pos.cycle_id, ...")
    print()
    return False


def main():
    print("=" * 64)
    print("  週期採購 migration 狀態檢查（唯讀，不會修改任何資料）")
    print("=" * 64)
    db_path, source = resolve_db_path(DEFAULT_DB_PATH)
    print(f"資料庫：{db_path}")
    print(f"　來源：{source}")
    print()

    con = open_readonly(db_path)
    if con is None:
        return 1

    try:
        cols_ok, missing = check_columns(con)
        legacy_ok = check_legacy_conversion(con)
        po_index_ok = check_po_unique_index(con)
    finally:
        con.close()

    print("=" * 64)
    if cols_ok and legacy_ok and po_index_ok:
        print("✅ 結論：兩支 migration 都跑過了，欄位齊全、舊資料轉換完成、")
        print("   採購單唯一鍵也已改成 partial unique index。")
        return 0

    print("⚠️ 結論：還有沒完成的項目。")
    if missing:
        print(f"   ① 缺少 {len(missing)} 個欄位：{missing}")
    if legacy_ok is False:
        print("   ② 舊資料一次性轉換還沒做完。")
    if missing or legacy_ok is False:
        print("      → 執行 apply_cycle_purchase_summary_migration.py")
        print("        （安全可重複執行，只補缺少的部分，不會刪任何資料）")
    if po_index_ok is False:
        print("   ③ 採購單唯一鍵還沒換成 partial unique index。")
        print("      → 執行 apply_cycle_purchase_po_unique_migration.py")
        print("        ⚠️ 這支會**整表重建**，請先停掉後端服務再跑（會自動備份）")
    print("=" * 64)
    return 1


if __name__ == "__main__":
    sys.exit(main())
