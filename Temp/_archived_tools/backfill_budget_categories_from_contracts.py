"""
合約明細「預算大項」「預算細項」反寫回 budget_categories migration（2026-07-21）

用途：
  新增合約表單的「預算大項」/「預算細項」下拉選單資料來自 budget_categories 表，
  但過去有些合約使用的科目組合在 budget_categories 主檔裡並不存在（例如透過其他
  管道建立、或當初漏建主檔資料），導致這些科目之後在新增合約表單選不到。

  本腳本掃描 contracts 表所有已使用過的 (預算年度, 預算大項, 預算細項) 組合，把
  budget_categories 裡還沒有的組合補進去，讓這些科目未來在新增合約表單重新可被選取。

與 Samuel 確認的規則（AskUserQuestion，2026-07-21）：
  - dept 留空（不分部門）：避免「預算細項」下拉選單依 (年度, 大項, 細項) 組合出現
    重複顯示的細項名稱（前端下拉目前沒有依 dept 去重，且合約驗證邏輯本來就不比對
    dept）。判斷「是否已存在」時，只要 budget_categories 裡已有任何一筆
    (budget_year, category_l1, category_l2) 的組合（不論 dept 是什麼），就視為已
    涵蓋，不會重複建立。
  - effective_date（必填欄位）：用該組合中最早一筆合約的 start_date。
  - accounting_code：同樣取該組合中最早一筆合約的 accounting_code（同組合內若不同
    合約的會計科目不一致，以最早那筆為準，其餘可事後在「合約設定」頁面人工覆核）。
  - maintain_unit：留空字串，可事後在「合約管理→合約設定」頁面手動補上維護單位。
  - is_enabled：預設 True，讓補齊的科目立即可在新增合約表單選取。

這支腳本是「安全可重複執行」版本：
  - 只會新增 budget_categories 裡還沒有的 (budget_year, category_l1, category_l2) 組合
  - 不會修改或刪除任何既有 budget_categories 資料
  - 不會動 contracts 表任何資料

用法（在你自己的電腦上，開一個終端機視窗）：
    python backfill_budget_categories_from_contracts.py

或者直接雙擊同資料夾裡的 backfill_budget_categories_from_contracts.bat
"""

import sqlite3
import sys
from datetime import datetime

# 對齊 backend/.env 的 DATABASE_URL=sqlite:///C:/portal_data/portal.db
DB_PATH = r"C:\portal_data\portal.db"


def main():
    print(f"連線到：{DB_PATH}")
    try:
        con = sqlite3.connect(DB_PATH)
    except Exception as e:
        print(f"[錯誤] 無法開啟資料庫檔案：{e}")
        sys.exit(1)

    # 1. 掃描 contracts 表所有已使用過的 (budget_year, l1, l2) 組合，
    #    取該組合中最早一筆合約的 accounting_code / start_date
    try:
        rows = con.execute(
            """
            SELECT budget_year, budget_category_l1, budget_category_l2,
                   accounting_code, start_date, contract_id
            FROM contracts
            WHERE budget_category_l1 IS NOT NULL AND budget_category_l1 != ''
              AND budget_category_l2 IS NOT NULL AND budget_category_l2 != ''
            """
        ).fetchall()
    except Exception as e:
        print(f"[錯誤] 無法讀取 contracts 表：{e}")
        con.close()
        sys.exit(1)

    print(f"contracts 表共 {len(rows)} 筆有填預算大項/細項的合約")

    groups = {}
    for budget_year, l1, l2, accounting_code, start_date, contract_id in rows:
        key = (budget_year, l1, l2)
        cur_start = start_date or ""
        if key not in groups or cur_start < (groups[key]["start_date"] or ""):
            groups[key] = {
                "accounting_code": accounting_code or "",
                "start_date": start_date,
                "contract_id": contract_id,
            }

    print(f"去重後共 {len(groups)} 組不重複的 (預算年度, 預算大項, 預算細項) 組合")

    # 2. 查詢 budget_categories 已存在的組合（忽略 dept，任何 dept 都算已涵蓋）
    try:
        existing = {
            (row[0], row[1], row[2])
            for row in con.execute(
                "SELECT budget_year, category_l1, category_l2 FROM budget_categories"
            )
        }
    except Exception as e:
        print(f"[錯誤] 無法讀取 budget_categories 表：{e}")
        con.close()
        sys.exit(1)

    print(f"budget_categories 目前已有 {len(existing)} 組不重複的組合")

    # 3. 補齊缺少的組合
    to_insert = [(key, info) for key, info in groups.items() if key not in existing]
    print(f"需要補齊 {len(to_insert)} 組\n")

    if not to_insert:
        print("沒有需要補齊的組合，budget_categories 已完整涵蓋 contracts 用過的科目。")
        con.close()
        return

    now = datetime.now()
    inserted = 0
    for (budget_year, l1, l2), info in sorted(to_insert, key=lambda x: (x[0][0], x[0][1], x[0][2])):
        effective_date = info["start_date"] or f"{budget_year}-01-01"
        accounting_code = info["accounting_code"]
        try:
            con.execute(
                """
                INSERT INTO budget_categories
                    (budget_year, dept, category_l1, category_l2, accounting_code,
                     payment_code, is_enabled, effective_date, disabled_date,
                     maintain_unit, created_at, updated_at)
                VALUES (?, '', ?, ?, ?, NULL, 1, ?, NULL, '', ?, ?)
                """,
                (budget_year, l1, l2, accounting_code, effective_date, now, now),
            )
            print(
                f"[新增] {budget_year} / {l1} / {l2}"
                f"（會計科目：{accounting_code or '（空白）'}，生效日：{effective_date}，"
                f"來源合約：{info['contract_id']}）"
            )
            inserted += 1
        except Exception as e:
            print(f"[錯誤] 新增 {budget_year}/{l1}/{l2} 失敗：{e}")

    con.commit()
    con.close()

    print()
    print("=" * 60)
    print(f"✅ 完成！共新增 {inserted} 筆預算科目主檔資料。")
    print("   dept／maintain_unit 留空，如需依部門管理可到「合約管理→合約設定」頁面手動編輯補上。")


if __name__ == "__main__":
    main()
