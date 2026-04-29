"""
診斷腳本：查詢「狀態判定完成但無時間戳記」的案件
執行方式：
    cd portal/backend
    python scripts/check_status_only_cases.py

說明：
    目前 is_completed_flag = (completed_at IS NOT NULL) OR is_completed
    「結案時間」和「驗收時間」在同步時都合併到 completed_at 欄位。
    因此：
        completed_at IS NULL AND is_completed = 1
        → 狀態欄為「已結案/結案/已辦驗...」但 Ragic 無任何時間欄位的案件
        → 這些在新定義下會從「已完成」變成「未完成」
"""

import sqlite3
from collections import defaultdict

DB_PATH = "./portal.db"

def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── 1. 總計：樂群 ──────────────────────────────────────────────────────────
    cur.execute("""
        SELECT COUNT(*) as cnt
        FROM luqun_repair_case
        WHERE completed_at IS NULL
          AND is_completed = 1
          AND status NOT IN ('取消')
    """)
    luqun_total = cur.fetchone()["cnt"]

    # ── 2. 明細：樂群 ──────────────────────────────────────────────────────────
    cur.execute("""
        SELECT ragic_id, case_no, title, status, occurred_at,
               occ_year, occ_month, year, month
        FROM luqun_repair_case
        WHERE completed_at IS NULL
          AND is_completed = 1
          AND status NOT IN ('取消')
        ORDER BY occurred_at DESC
    """)
    luqun_rows = cur.fetchall()

    # ── 3. 各月統計：新舊定義對比（樂群）─────────────────────────────────────
    # 舊定義（current）: completed_at IS NOT NULL OR is_completed=1
    # 新定義（new）    : completed_at IS NOT NULL
    cur.execute("""
        SELECT
            occ_year, occ_month,
            COUNT(*) as total,
            SUM(CASE WHEN completed_at IS NOT NULL OR is_completed=1 THEN 1 ELSE 0 END) as completed_old,
            SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END) as completed_new,
            SUM(CASE WHEN NOT (completed_at IS NOT NULL OR is_completed=1) THEN 1 ELSE 0 END) as uncompleted_old,
            SUM(CASE WHEN completed_at IS NULL THEN 1 ELSE 0 END) as uncompleted_new
        FROM luqun_repair_case
        WHERE status NOT IN ('取消')
          AND occ_year IS NOT NULL
          AND occ_month IS NOT NULL
        GROUP BY occ_year, occ_month
        ORDER BY occ_year, occ_month
    """)
    luqun_monthly = cur.fetchall()

    # ── 4. 總計：大直 ──────────────────────────────────────────────────────────
    cur.execute("""
        SELECT COUNT(*) as cnt
        FROM dazhi_repair_case
        WHERE completed_at IS NULL
          AND is_completed = 1
          AND status NOT IN ('取消')
    """)
    dazhi_total = cur.fetchone()["cnt"]

    cur.execute("""
        SELECT
            year, month,
            COUNT(*) as total,
            SUM(CASE WHEN completed_at IS NOT NULL OR is_completed=1 THEN 1 ELSE 0 END) as completed_old,
            SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END) as completed_new,
            SUM(CASE WHEN NOT (completed_at IS NOT NULL OR is_completed=1) THEN 1 ELSE 0 END) as uncompleted_old,
            SUM(CASE WHEN completed_at IS NULL THEN 1 ELSE 0 END) as uncompleted_new
        FROM dazhi_repair_case
        WHERE status NOT IN ('取消')
          AND year IS NOT NULL
          AND month IS NOT NULL
        GROUP BY year, month
        ORDER BY year, month
    """)
    dazhi_monthly = cur.fetchall()

    conn.close()

    # ── 輸出 ───────────────────────────────────────────────────────────────────
    print("=" * 70)
    print("【樂群】狀態判定完成 但無時間戳記的案件（新定義下會翻轉為未完成）")
    print(f"  總計：{luqun_total} 筆")
    print("-" * 70)
    if luqun_rows:
        print(f"{'報修編號':<20} {'狀態':<12} {'報修日期':<22} {'統計月'}")
        for r in luqun_rows:
            stat_m = f"{r['year']}/{r['month']:02d}" if r['year'] else f"occ {r['occ_year']}/{r['occ_month']:02d}" if r['occ_year'] else "?"
            print(f"{r['case_no'] or r['ragic_id']:<20} {r['status']:<12} {str(r['occurred_at'] or ''):<22} {stat_m}")
    else:
        print("  （無）")

    print()
    print("=" * 70)
    print("【樂群】各月 已完成/未完成 舊 vs 新定義對比（以報修月 occ_year/month 為基準）")
    print(f"{'年月':<8} {'總計':>5} | {'已完(舊)':>8} {'已完(新)':>8} {'差異':>6} | {'未完(舊)':>8} {'未完(新)':>8} {'差異':>6}")
    print("-" * 70)
    for r in luqun_monthly:
        ym = f"{r['occ_year']}/{r['occ_month']:02d}"
        diff_c = r['completed_new'] - r['completed_old']
        diff_u = r['uncompleted_new'] - r['uncompleted_old']
        flag = " ← 有差異" if diff_c != 0 else ""
        print(f"{ym:<8} {r['total']:>5} | {r['completed_old']:>8} {r['completed_new']:>8} {diff_c:>+6} | "
              f"{r['uncompleted_old']:>8} {r['uncompleted_new']:>8} {diff_u:>+6}{flag}")

    print()
    print("=" * 70)
    print(f"【大直】狀態判定完成 但無時間戳記：{dazhi_total} 筆")
    print()
    print("【大直】各月 已完成/未完成 舊 vs 新定義對比（以 year/month 為基準）")
    print(f"{'年月':<8} {'總計':>5} | {'已完(舊)':>8} {'已完(新)':>8} {'差異':>6} | {'未完(舊)':>8} {'未完(新)':>8} {'差異':>6}")
    print("-" * 70)
    for r in dazhi_monthly:
        ym = f"{r['year']}/{r['month']:02d}"
        diff_c = r['completed_new'] - r['completed_old']
        diff_u = r['uncompleted_new'] - r['uncompleted_old']
        flag = " ← 有差異" if diff_c != 0 else ""
        print(f"{ym:<8} {r['total']:>5} | {r['completed_old']:>8} {r['completed_new']:>8} {diff_c:>+6} | "
              f"{r['uncompleted_old']:>8} {r['uncompleted_new']:>8} {diff_u:>+6}{flag}")

    print("=" * 70)

if __name__ == "__main__":
    run()
