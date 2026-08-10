# -*- coding: utf-8 -*-
"""
週期採購 — 料號對照表 vendor_id 回填腳本

2026-07-11（第三期彙整單／採購單規劃時發現並修正，見
backend/app/models/cycle_purchase_item.py 開頭說明）：
cycle_purchase_item_mappings.original_vendor_name 原本只是文字欄位，沒有連到
cycle_purchase_vendors，7 筆兩公司 confirmed 合併的料號因此會分不出供應商
（CyclePurchaseItem.default_vendor_id 只記到先建檔那家公司）。

這支腳本是「非破壞性」的欄位補丁 + 資料回填，**不需要清空重建資料庫**（吸取
先前 department_id 那次「create_all() 不會 ALTER 既有表格」的教訓）：
  1. 檢查 cycle_purchase_item_mappings 是否已經有 vendor_id 欄位，沒有的話
     用 ALTER TABLE 新增（nullable，不影響既有資料列）。這一步冪等：欄位已
     存在就跳過。
  2. 回填：對每一筆 vendor_id 還是 NULL、但 original_vendor_name 有值的
     對照列，用「完全相同字串」比對 cycle_purchase_vendors.vendor_name，
     找到就回填 vendor_id。這個比對可靠是因為匯入時 get_or_create_vendor()
     本身就是用完全相同字串去重、且是兩公司匯入共用同一份記憶體字典，
     所以現在資料庫裡的 vendor_name 字串本來就是 original_vendor_name 去重
     後的結果，理論上應該 100% 對得起來。
  3. 任何回填不到的列（original_vendor_name 有值但比對不到 vendor_name，
     或 original_vendor_name 本身是空的）會被列出來，不會靜默略過——
     空的部分是原始資料本來就沒有廠商，不算異常；比對不到的部分請告訴我，
     不能自己猜。

使用方式（在 backend 資料夾底下，啟用虛擬環境後執行）：
    python backfill_item_mapping_vendor_id.py --dry-run   # 先預覽，不寫入
    python backfill_item_mapping_vendor_id.py              # 正式回填

可重複執行：已經有 vendor_id 的列不會被覆蓋，欄位已存在也不會重複 ALTER。
"""

import argparse
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("C:/portal_data/cycle-purchase.db")


def main():
    parser = argparse.ArgumentParser(description="回填週期採購料號對照表的 vendor_id")
    parser.add_argument("--dry-run", action="store_true", help="只預覽，不實際寫入資料庫")
    args = parser.parse_args()

    print("=" * 70)
    print("  週期採購 — 料號對照表 vendor_id 回填")
    print(f"  目標資料庫：{DB_PATH}")
    if args.dry_run:
        print("  [DRY-RUN 模式：不會實際寫入資料庫]")
    print("=" * 70)

    if not DB_PATH.exists():
        print(f"找不到資料庫檔案：{DB_PATH}")
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # ── 1. 確認表格存在 ──────────────────────────────────────────────────────
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='cycle_purchase_item_mappings'"
    )
    if not cur.fetchone():
        print("資料庫裡找不到 cycle_purchase_item_mappings 表，請確認後端已經啟動過（會自動建表）。")
        sys.exit(1)

    # ── 2. 檢查／新增 vendor_id 欄位（非破壞性）──────────────────────────────
    cur.execute("PRAGMA table_info(cycle_purchase_item_mappings)")
    existing_cols = {row["name"] for row in cur.fetchall()}
    if "vendor_id" in existing_cols:
        print("\nvendor_id 欄位已存在，跳過 ALTER TABLE。")
    else:
        print("\nvendor_id 欄位不存在，新增中...")
        if not args.dry_run:
            cur.execute(
                "ALTER TABLE cycle_purchase_item_mappings "
                "ADD COLUMN vendor_id INTEGER REFERENCES cycle_purchase_vendors(id)"
            )
            con.commit()
            print("  已新增 vendor_id 欄位（nullable，不影響既有資料列）")
        else:
            print("  [DRY-RUN] 會新增 vendor_id 欄位")

    # ── 3. 回填 ──────────────────────────────────────────────────────────────
    cur.execute("SELECT id, vendor_name FROM cycle_purchase_vendors")
    vendor_id_by_name = {row["vendor_name"]: row["id"] for row in cur.fetchall()}

    # 若剛新增欄位且是 dry-run，PRAGMA 仍看不到新欄位，這裡用 try 保護，
    # dry-run 模式下改用「模擬」方式跑一遍邏輯，不實際查詢 vendor_id 欄位。
    if "vendor_id" in existing_cols or not args.dry_run:
        cur.execute(
            "SELECT id, company, original_code, original_vendor_name, vendor_id "
            "FROM cycle_purchase_item_mappings"
        )
        rows = cur.fetchall()
    else:
        cur.execute(
            "SELECT id, company, original_code, original_vendor_name "
            "FROM cycle_purchase_item_mappings"
        )
        rows = cur.fetchall()

    to_backfill = []       # (mapping_id, vendor_id, vendor_name)
    already_set = 0
    empty_vendor_name = []  # original_vendor_name 本來就是空的（正常情況，不算異常）
    unmatched = []          # original_vendor_name 有值，但比對不到任何 vendor_name（需要人工看）

    for row in rows:
        current_vendor_id = row["vendor_id"] if "vendor_id" in row.keys() else None
        if current_vendor_id:
            already_set += 1
            continue

        name = row["original_vendor_name"]
        if not name or not name.strip():
            empty_vendor_name.append((row["company"], row["original_code"]))
            continue

        name = name.strip()
        vid = vendor_id_by_name.get(name)
        if vid is None:
            unmatched.append((row["company"], row["original_code"], name))
            continue

        to_backfill.append((row["id"], vid, name))

    print(f"\n對照表總筆數：{len(rows)}")
    print(f"  已經有 vendor_id（本次略過）：{already_set} 筆")
    print(f"  可回填（original_vendor_name 比對到供應商）：{len(to_backfill)} 筆")
    print(f"  原始廠商欄位本來就是空的（正常，不回填）：{len(empty_vendor_name)} 筆")
    print(f"  ⚠️ 比對不到供應商（需要人工確認，本次不會動）：{len(unmatched)} 筆")

    if unmatched:
        print("\n以下對照列的 original_vendor_name 比對不到任何供應商主檔，請人工確認"
              "（可能是供應商主檔那邊名稱打法不同，或這筆資料本身有問題）：")
        for company, code, name in unmatched[:50]:
            print(f"    - {company} / {code} / 廠商文字=「{name}」")
        if len(unmatched) > 50:
            print(f"    ...（其餘 {len(unmatched) - 50} 筆省略，請自行查詢資料庫）")

    if not args.dry_run and to_backfill:
        cur.executemany(
            "UPDATE cycle_purchase_item_mappings SET vendor_id = ? WHERE id = ?",
            [(vid, mapping_id) for mapping_id, vid, _ in to_backfill],
        )
        con.commit()
        print(f"\n已回填 {len(to_backfill)} 筆對照列的 vendor_id。")
    elif args.dry_run:
        print(f"\n[DRY-RUN] 會回填 {len(to_backfill)} 筆對照列的 vendor_id（未實際寫入）。")

    con.close()
    print("\n" + "=" * 70)
    print("  完成" + ("（DRY-RUN，未實際寫入）" if args.dry_run else ""))
    print("=" * 70)


if __name__ == "__main__":
    main()
