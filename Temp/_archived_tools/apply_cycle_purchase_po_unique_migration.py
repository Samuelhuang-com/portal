"""
週期採購「採購單唯一鍵」整表重建 migration（2026-08-09）

做什麼：
  把 cycle_purchase_pos 的唯一鍵從

      UNIQUE (cycle_id, period_label, company, vendor_id)          ← 不分狀態

  改成

      CREATE UNIQUE INDEX uq_cp_po_active_cycle_period_company_vendor
        ON cycle_purchase_pos (cycle_id, period_label, company, vendor_id)
        WHERE status != 'cancelled'                                 ← 排除已取消

為什麼要改：
  2026-08-09 新增「採購單退回彙整單」。退回時採購單保留為 cancelled 當軌跡，
  但買家調整完之後要能對**同一組週期＋期別＋公司＋供應商**再轉出一張新的
  採購單。原本的唯一鍵不分狀態，會直接擋掉：

      UNIQUE constraint failed: cycle_purchase_pos.cycle_id,
      cycle_purchase_pos.period_label, cycle_purchase_pos.company,
      cycle_purchase_pos.vendor_id

  改成 partial index 後，已取消的單不參與唯一性檢查，但**仍然保證「同一組
  同時只會有一張有效（未取消）的採購單」**——不是把約束拿掉。

為什麼要整表重建：
  SQLite 不支援 `ALTER TABLE ... DROP CONSTRAINT`。table-level 的 UNIQUE 會變成
  一個隱含的 sqlite_autoindex，沒辦法單獨刪掉，只能「建新表 → 搬資料 →
  刪舊表 → 改名」。

安全性：
  - 執行前會**自動備份整個資料庫檔案**到 cycle-purchase.db.bak-YYYYmmdd-HHMMSS
  - 全程在單一 transaction 內，中途出錯會整個 rollback，不會留下半殘狀態
  - 搬完資料會**比對前後筆數**，不一致就 rollback 並中止
  - 可重複執行：偵測到新索引已存在就直接跳過

⚠️ 執行前請先把後端服務停掉（整表重建期間有其他連線寫入會失敗）。

用法（在你自己的電腦上，開一個終端機視窗）：
    python apply_cycle_purchase_po_unique_migration.py
"""

import os
import shutil
import sqlite3
import sys
from datetime import datetime

from migration_db_path import require_existing_db, resolve_db_path

# 2026-08-10：路徑不再寫死。優先序為 --db 參數 > backend/.env 的
# CYCLE_PURCHASE_DATABASE_URL > 下面這個預設值（見 migration_db_path.py 的說明）。
DEFAULT_DB_PATH = r"C:\portal_data\cycle-purchase.db"

NEW_INDEX_NAME = "uq_cp_po_active_cycle_period_company_vendor"

# 新表定義：欄位與舊表完全一致，只是**沒有** table-level 的 UNIQUE(cycle_id,
# period_label, company, vendor_id)。po_no 的 UNIQUE 保留。
CREATE_NEW_TABLE = """
CREATE TABLE cycle_purchase_pos__new (
    id            INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    po_no         VARCHAR(30) NOT NULL UNIQUE,
    cycle_id      INTEGER NOT NULL REFERENCES cycle_purchase_cycles(id) ON DELETE RESTRICT,
    period_label  VARCHAR(30) NOT NULL,
    company       VARCHAR(50) NOT NULL,
    vendor_id     INTEGER NOT NULL REFERENCES cycle_purchase_vendors(id) ON DELETE RESTRICT,
    buyer_user_id VARCHAR(36),
    buyer_name    VARCHAR(100),
    expected_date DATE,
    total_amount  NUMERIC(14, 2) NOT NULL DEFAULT 0,
    status        VARCHAR(20) NOT NULL DEFAULT 'draft',
    notes         TEXT,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

COPY_COLUMNS = [
    "id", "po_no", "cycle_id", "period_label", "company", "vendor_id",
    "buyer_user_id", "buyer_name", "expected_date", "total_amount",
    "status", "notes", "created_at", "updated_at",
]

CREATE_NEW_INDEX = f"""
CREATE UNIQUE INDEX {NEW_INDEX_NAME}
    ON cycle_purchase_pos (cycle_id, period_label, company, vendor_id)
    WHERE status != 'cancelled'
"""


def backup(path):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = f"{path}.bak-{stamp}"
    shutil.copy2(path, dst)
    print(f"[備份] 已複製一份到：{dst}")
    return dst


def index_exists(con, name):
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (name,)
    ).fetchone()
    return row is not None


def check_duplicate_active(con):
    """重建前先確認：排除 cancelled 之後，有沒有同一組出現兩張以上的單？
    如果有（理論上不可能，因為舊約束更嚴），新的 partial unique index 會建不起來，
    要先講清楚是哪幾筆，而不是讓使用者看到一句沒頭沒尾的 IntegrityError。"""
    rows = con.execute(
        """
        SELECT cycle_id, period_label, company, vendor_id, COUNT(*) AS n,
               GROUP_CONCAT(po_no, '、') AS po_nos
        FROM cycle_purchase_pos
        WHERE status != 'cancelled'
        GROUP BY cycle_id, period_label, company, vendor_id
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    return rows


def main():
    print("=" * 64)
    print("  週期採購 — 採購單唯一鍵改為 partial unique index（整表重建）")
    print("=" * 64)
    db_path, source = resolve_db_path(DEFAULT_DB_PATH)
    require_existing_db(db_path, source)

    con = sqlite3.connect(db_path)
    try:
        if index_exists(con, NEW_INDEX_NAME):
            print(f"[略過] 索引 {NEW_INDEX_NAME} 已經存在，這支腳本先前跑過了，不需要再跑一次。")
            print()
            print("=" * 64)
            print("✅ 已是最新狀態。")
            return 0

        dups = check_duplicate_active(con)
        if dups:
            print("[錯誤] 資料裡有「同一組週期＋期別＋公司＋供應商」出現多張未取消的採購單，")
            print("       新的唯一索引建不起來。請先人工處理以下這幾組：")
            for row in dups:
                print(f"         cycle_id={row[0]} 期別={row[1]} 公司={row[2]} "
                      f"vendor_id={row[3]} → {row[4]} 張：{row[5]}")
            return 1

        before = con.execute("SELECT COUNT(*) FROM cycle_purchase_pos").fetchone()[0]
        print(f"[檢查] 目前採購單筆數：{before}")

        backup(db_path)

        # 整表重建期間必須關掉 FK 檢查，否則 DROP 舊表時會被子表
        # （cycle_purchase_po_items / receiving / payment）的外鍵擋住。
        # PRAGMA foreign_keys 不能在 transaction 內切換，所以放在 BEGIN 之前。
        con.execute("PRAGMA foreign_keys=OFF")
        con.execute("BEGIN")
        try:
            con.execute(CREATE_NEW_TABLE)
            cols = ", ".join(COPY_COLUMNS)
            con.execute(
                f"INSERT INTO cycle_purchase_pos__new ({cols}) "
                f"SELECT {cols} FROM cycle_purchase_pos"
            )
            moved = con.execute("SELECT COUNT(*) FROM cycle_purchase_pos__new").fetchone()[0]
            if moved != before:
                raise RuntimeError(f"搬移筆數不一致：原本 {before}、搬過去 {moved}")

            con.execute("DROP TABLE cycle_purchase_pos")
            con.execute("ALTER TABLE cycle_purchase_pos__new RENAME TO cycle_purchase_pos")
            con.execute(CREATE_NEW_INDEX)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        finally:
            con.execute("PRAGMA foreign_keys=ON")

        after = con.execute("SELECT COUNT(*) FROM cycle_purchase_pos").fetchone()[0]
        print(f"[完成] 重建後採購單筆數：{after}")

        # 重建後檢查外鍵有沒有被搞壞（子表指向的 po_id 是否都還在）
        violations = con.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            print(f"[警告] foreign_key_check 回報 {len(violations)} 筆問題，請檢查：")
            for v in violations[:10]:
                print("        ", v)
        else:
            print("[檢查] foreign_key_check 沒有問題。")

        print()
        print("=" * 64)
        if after == before and not violations:
            print("✅ 成功！現在同一組週期＋期別＋公司＋供應商可以有多張『已取消』的採購單，")
            print("   但同時只會有一張有效（未取消）的採購單。")
            print("   請重新啟動後端服務。")
            return 0
        print("⚠️ 完成但有需要確認的項目，請看上面的訊息。備份檔在資料庫同一個資料夾。")
        return 1

    except Exception as e:
        print(f"\n[錯誤] 執行失敗，資料庫未被修改（已 rollback）：{e}")
        print("       備份檔在資料庫同一個資料夾，必要時可以直接還原。")
        return 1
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
