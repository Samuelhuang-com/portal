"""
清掉 `approved_purchase_requests.applicant` 裡誤存的圖檔 base64

背景（2026-08-29，PostgreSQL 遷移的前置檢查抓到）
────────────────────────────────────────────────────────────────────────────
Ragic 的「申請人／請購人」是**圖檔欄位（簽名圖）**，API 回傳
`data:image/png;base64,iVBORw0KG...`。`purchase_request_sync.py` 原本直接把它
寫進 `applicant`，導致 **87 筆存了 17,474 字的 base64**，
畫面上的申請人欄位顯示成一長串亂碼。

這是既有的顯示問題，**不是遷移造成的** —— 只是遷移的
`VARCHAR(50)` 長度檢查把它照出來（SQLite 不執行長度限制，所以一直沒人發現）。

處理方式（已與使用者確認）
    · 同步端：`_person_name()` 攔掉 `data:` 開頭的值，回 None 不回截斷字串
      （截斷會留下看似合理的垃圾，比空值更難發現）
    · 資料端：本腳本把既有的髒值清成 NULL
    · 欄位維持 `VARCHAR(50)` —— **不放寬**，放寬等於把錯誤永久合法化

⚠️ 只把 `data:` 開頭的值改成 NULL，其他一律不動。
⚠️ 執行前會先列出受影響筆數並要求確認。

執行：
    cd backend
    py -3.12 scripts\\fix_applicant_data_uri.py           # 會先問你
    py -3.12 scripts\\fix_applicant_data_uri.py --yes     # 不問直接執行
    py -3.12 scripts\\fix_applicant_data_uri.py --check   # 只檢查不修改
"""
from __future__ import annotations

import logging
import os
import sys

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

from sqlalchemy import inspect, text                              # noqa: E402

TABLE = "approved_purchase_requests"
COLUMN = "applicant"


def main() -> int:
    auto_yes = "--yes" in sys.argv or "-y" in sys.argv
    check_only = "--check" in sys.argv

    from app.core.database import engine
    engine.echo = False

    print("=" * 74)
    print(f"  清理 {TABLE}.{COLUMN} 裡的圖檔 base64")
    print("=" * 74)
    print(f"  {engine.url}\n")

    if TABLE not in set(inspect(engine).get_table_names()):
        print(f"  ⚠️  找不到資料表 {TABLE}，略過。")
        return 0

    where = f"{COLUMN} LIKE 'data:%'"
    with engine.connect() as c:
        n, mx = c.execute(text(
            f"SELECT COUNT(*), COALESCE(MAX(LENGTH({COLUMN})), 0) "
            f"FROM {TABLE} WHERE {where}")).one()
        # 順便看看有沒有「不是 data: 開頭但仍超長」的（那要另外判斷，本腳本不碰）
        other, = c.execute(text(
            f"SELECT COUNT(*) FROM {TABLE} "
            f"WHERE LENGTH({COLUMN}) > 50 AND {COLUMN} NOT LIKE 'data:%'")).one()

    if not n:
        print("  ✅ 沒有 data: 開頭的值，不需要處理。")
    else:
        print(f"  找到 {n:,} 筆 `data:` 開頭的值（最長 {mx:,} 字）")
        print(f"  → 這些會被改成 NULL（欄位維持 VARCHAR(50)，不放寬）")

    if other:
        print(f"\n  ⚠️  另有 {other:,} 筆超過 50 字但**不是** data: 開頭 ——")
        print("     本腳本刻意不碰，那些要先看內容才知道該截斷還是放寬：")
        print("         py -3.12 scripts\\pg_show_overlong.py")

    if not n:
        return 0
    if check_only:
        print("\n  （--check 模式，未修改）")
        return 1

    if not auto_yes:
        try:
            ans = input(f"\n  要把這 {n:,} 筆改成 NULL 嗎？輸入 y 執行： ").strip().lower()
        except EOFError:
            ans = ""
        if ans not in ("y", "yes"):
            print("  已取消，未修改任何資料。")
            return 2

    with engine.connect() as c:
        c.execute(text(f"UPDATE {TABLE} SET {COLUMN} = NULL WHERE {where}"))
        c.commit()
        left, = c.execute(text(f"SELECT COUNT(*) FROM {TABLE} WHERE {where}")).one()

    print(f"\n  ✅ 已清除 {n:,} 筆，剩餘 {left} 筆")
    print("""
  ⚠️ 下次同步不會再被污染 —— purchase_request_sync.py 的 _person_name()
     會攔掉 data: 開頭的值。但那 87 筆的申請人**就此空白**，
     Ragic 端沒有文字姓名可以補回來（該欄位本身就是圖檔）。
     若之後 Ragic 新增文字欄位，把欄位名加進
     LIST_FIELD_CANDIDATES["applicant"] 再重跑同步即可。
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
