"""
週期採購「彙整單／請購單」欄位補齊 migration（2026-07-16／2026-07-17，累計三次調整）

用途：
  幫 cycle-purchase.db 補上這幾次改版新增的欄位，涵蓋兩張表：

  1) cycle_purchase_summary（部門別＋Ragic 拋轉追蹤，第一次調整）：
       department_id, ragic_push_batch_no, ragic_pushed,
       ragic_record_id, ragic_pushed_at, ragic_push_error

  2) cycle_purchase_requests（彙整單產生方式改版，第二次調整——用「勾選
     請購單」取代舊版「輸入週期＋期別字串」的產生方式）：
       is_summarized, summary_batch_no, summarized_at

  3) cycle_purchase_requests（請購單流程大改版，第三次調整——拿掉送出／核准，
     改成「關閉／重新開啟」）：
       is_closed, closed_by_user_id, closed_by_name, closed_at, close_batch_no,
       reopened_by_user_id, reopened_by_name, reopened_at

  另外，第三次調整還需要「一次性資料轉換」：改版前用 status=='approved'
  代表「這張單的內容已經定案」，改版後這個角色改由 is_closed=True 扮演，
  所以要把舊資料的 approved 狀態轉換成 is_closed=True（連帶把 closed_* 欄位
  用舊的 approved_* 欄位回填），否則舊資料會全部「卡住」，永遠出現不了在
  彙整單的可勾選清單裡。這個轉換只會挑「還沒被這支腳本轉換過」的列（用
  close_batch_no IS NULL 判斷，見下方 LEGACY_CONVERT_BATCH_NO），重複執行
  這支腳本不會覆蓋掉之後使用者手動關閉／重新開啟的結果。

這支腳本是「安全可重複執行」版本：
  - 執行前會先用 PRAGMA table_info 檢查每個欄位是否已經存在
  - 只會補「還沒加過」的欄位，已經加過的會直接跳過，不會報錯中斷
  - 一次性資料轉換也只會處理還沒轉換過的列，不會覆蓋既有資料
  - 不會刪除任何既有資料

用法（在你自己的電腦上，開一個終端機視窗）：
    python apply_cycle_purchase_summary_migration.py

或者直接雙擊同資料夾裡的 apply_cycle_purchase_summary_migration.bat
"""

import sqlite3
import sys

DB_PATH = r"C:\portal_data\cycle-purchase.db"

# 一次性資料轉換用的識別批次號，跟正常的關閉批次號（CPCLOSE-YYYYMM-NNN）格式
# 明顯不同，方便日後在資料庫裡分辨「這筆是舊資料轉換來的，不是使用者手動關的」。
LEGACY_CONVERT_BATCH_NO = "LEGACY-CONVERT-20260717"

# (資料表名稱, [(欄位名稱, 完整的 ADD COLUMN 語法), ...])
TABLES_TO_MIGRATE = [
    (
        "cycle_purchase_summary",
        [
            ("department_id", "ALTER TABLE cycle_purchase_summary ADD COLUMN department_id INTEGER"),
            ("ragic_push_batch_no", "ALTER TABLE cycle_purchase_summary ADD COLUMN ragic_push_batch_no VARCHAR(40)"),
            ("ragic_pushed", "ALTER TABLE cycle_purchase_summary ADD COLUMN ragic_pushed BOOLEAN NOT NULL DEFAULT 0"),
            ("ragic_record_id", "ALTER TABLE cycle_purchase_summary ADD COLUMN ragic_record_id VARCHAR(60)"),
            ("ragic_pushed_at", "ALTER TABLE cycle_purchase_summary ADD COLUMN ragic_pushed_at DATETIME"),
            ("ragic_push_error", "ALTER TABLE cycle_purchase_summary ADD COLUMN ragic_push_error TEXT"),
        ],
    ),
    (
        "cycle_purchase_requests",
        [
            ("is_summarized", "ALTER TABLE cycle_purchase_requests ADD COLUMN is_summarized BOOLEAN NOT NULL DEFAULT 0"),
            ("summary_batch_no", "ALTER TABLE cycle_purchase_requests ADD COLUMN summary_batch_no VARCHAR(40)"),
            ("summarized_at", "ALTER TABLE cycle_purchase_requests ADD COLUMN summarized_at DATETIME"),
            ("is_closed", "ALTER TABLE cycle_purchase_requests ADD COLUMN is_closed BOOLEAN NOT NULL DEFAULT 0"),
            ("closed_by_user_id", "ALTER TABLE cycle_purchase_requests ADD COLUMN closed_by_user_id VARCHAR(36)"),
            ("closed_by_name", "ALTER TABLE cycle_purchase_requests ADD COLUMN closed_by_name VARCHAR(100)"),
            ("closed_at", "ALTER TABLE cycle_purchase_requests ADD COLUMN closed_at DATETIME"),
            ("close_batch_no", "ALTER TABLE cycle_purchase_requests ADD COLUMN close_batch_no VARCHAR(40)"),
            ("reopened_by_user_id", "ALTER TABLE cycle_purchase_requests ADD COLUMN reopened_by_user_id VARCHAR(36)"),
            ("reopened_by_name", "ALTER TABLE cycle_purchase_requests ADD COLUMN reopened_by_name VARCHAR(100)"),
            ("reopened_at", "ALTER TABLE cycle_purchase_requests ADD COLUMN reopened_at DATETIME"),
        ],
    ),
]


def migrate_table(con, table_name, columns_to_add):
    print(f"=== {table_name} ===")
    try:
        existing = {row[1] for row in con.execute(f"PRAGMA table_info({table_name})")}
    except Exception as e:
        print(f"[錯誤] 無法讀取 {table_name} 的欄位資訊：{e}")
        return False

    if not existing:
        print(f"[錯誤] 找不到資料表 {table_name}（PRAGMA 回傳空清單），請確認後端至少啟動過一次。")
        return False

    print(f"目前已有欄位：{sorted(existing)}")

    added = []
    skipped = []
    for col_name, ddl in columns_to_add:
        if col_name in existing:
            print(f"[略過] {col_name} 已存在，不需要補")
            skipped.append(col_name)
            continue
        try:
            con.execute(ddl)
            print(f"[完成] 已新增欄位：{col_name}")
            added.append(col_name)
        except Exception as e:
            print(f"[錯誤] 新增欄位 {col_name} 失敗：{e}")

    con.commit()
    final = {row[1] for row in con.execute(f"PRAGMA table_info({table_name})")}
    required = {c for c, _ in columns_to_add}
    ok = required.issubset(final)
    print(f"新增了 {len(added)} 個欄位：{added}；略過了 {len(skipped)} 個（已存在）：{skipped}")
    print("✅ 這張表沒問題了" if ok else f"⚠️ 還缺少欄位：{required - final}")
    print()
    return ok


def convert_legacy_approved_to_closed(con):
    """一次性資料轉換：把舊資料裡 status=='approved' 的請購單轉成 is_closed=True，
    closed_* 欄位從既有的 approved_* 欄位回填（見本檔開頭第三次調整說明）。
    只挑 close_batch_no IS NULL 的列（代表這支腳本還沒轉換過、也還沒被使用者
    手動關閉過），重複執行這支腳本不會覆蓋掉之後使用者手動關閉／重新開啟的
    結果——這也是為什麼用「is NULL」而不是「is_closed=0」判斷：如果之後有人
    把轉換過的單重新開啟（is_closed 會變回 0，但 close_batch_no 保留不清），
    再跑一次這支腳本也不會誤把它重新標記為關閉。"""
    print("=== 一次性資料轉換：舊資料 approved -> is_closed=True ===")
    try:
        cur = con.execute(
            """
            SELECT COUNT(*) FROM cycle_purchase_requests
            WHERE status = 'approved' AND close_batch_no IS NULL
            """
        )
        candidate_count = cur.fetchone()[0]
    except Exception as e:
        print(f"[錯誤] 無法查詢待轉換的請購單：{e}")
        return False

    if candidate_count == 0:
        print("[略過] 沒有需要轉換的舊資料（可能是還沒轉換過，但也沒有 approved 資料；或已經轉換過了）")
        print()
        return True

    print(f"找到 {candidate_count} 筆 status='approved' 且尚未轉換過的請購單，開始轉換...")
    try:
        con.execute(
            """
            UPDATE cycle_purchase_requests
            SET is_closed = 1,
                closed_by_user_id = approved_by_user_id,
                closed_by_name = approved_by_name,
                closed_at = approved_at,
                close_batch_no = ?
            WHERE status = 'approved' AND close_batch_no IS NULL
            """,
            (LEGACY_CONVERT_BATCH_NO,),
        )
        con.commit()
    except Exception as e:
        print(f"[錯誤] 轉換失敗：{e}")
        return False

    print(f"[完成] 已將 {candidate_count} 筆舊資料轉換為 is_closed=True（批次號：{LEGACY_CONVERT_BATCH_NO}）")
    print()
    return True


def main():
    print(f"連線到：{DB_PATH}")
    try:
        con = sqlite3.connect(DB_PATH)
    except Exception as e:
        print(f"[錯誤] 無法開啟資料庫檔案：{e}")
        sys.exit(1)

    all_ok = True
    for table_name, columns in TABLES_TO_MIGRATE:
        ok = migrate_table(con, table_name, columns)
        all_ok = all_ok and ok

    # 欄位補齊之後才能做資料轉換（is_closed／close_batch_no 等欄位要先存在）。
    if all_ok:
        all_ok = convert_legacy_approved_to_closed(con) and all_ok

    con.close()

    if all_ok:
        print("=" * 60)
        print("✅ 成功！所有必要欄位都已存在、舊資料也轉換完成，現在可以重新整理「週期採購」頁面了。")
    else:
        print("=" * 60)
        print("⚠️ 注意：有些欄位還沒補上或資料轉換失敗，請把上面的錯誤訊息回報給我。")


if __name__ == "__main__":
    main()
