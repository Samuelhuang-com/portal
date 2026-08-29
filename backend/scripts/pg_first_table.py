"""
Phase 1 試點：把第一張表搬到 PostgreSQL（`ohip_revenue_history`）

做什麼
────────────────────────────────────────────────────────────────────────────
1. 連上 `.env` 的 `POSTGRES_URL`
2. 在 PostgreSQL 建立 `ohip_revenue_history`（**只有這一張**，不是全部 163 張）
3. 把 SQLite 的資料整批複製過去
4. 逐項驗證兩邊一致：筆數、日期範圍、維度基數、金額總和
5. 印出可以在 pgAdmin 貼上直接看的 SQL

為什麼選這張表當試點
    · 與其他模組**零外鍵關聯**（雙向都查過），自成一區
    · 唯讀分析用，沒有審批流程，搞砸不影響業務資料
    · 資料可重建（OHIP 能回補），最壞情況就是重來
    · 19.7 萬列、每天約 266 列成長 —— 正是「未來會更龐大」的那一批

⚠️ **完全不動 SQLite。** 來源端全程唯讀，`DATABASE_URL` 不需要改。
   這一步做完 Portal 仍然只讀 SQLite，PG 那份純粹是給你看的副本。

⚠️ 可重複執行：每次會先 `DROP TABLE` 再重建，不會累積重複資料。

執行：
    cd backend
    python scripts\\pg_first_table.py
    python scripts\\pg_first_table.py --rows 5000     # 只搬前 5000 列試水溫
"""
from __future__ import annotations

import logging
import os
import re
import sys
import time

# ⚠️ 輸出強制 UTF-8（2026-08-29 踩過）
#    Windows 主控台是 UTF-8，但**把輸出導向檔案時 Python 會改用 cp950**，
#    腳本裡的 ⚠️ ✅ ❌ 一律編不進去 → UnicodeEncodeError 整支中斷。
#    `> cmp.txt` 這種存檔動作很常用，不能因此掛掉。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

from sqlalchemy import create_engine, func, inspect, select, text   # noqa: E402
from sqlalchemy.orm import Session                                  # noqa: E402

TABLE = "ohip_revenue_history"
BATCH = 5000


def read_env(key: str) -> str | None:
    """從 backend/.env 讀一個值（不覆寫 os.environ，也不印出內容）。"""
    if os.environ.get(key):
        return os.environ[key]
    path = os.path.join(BACKEND, ".env")
    if not os.path.exists(path):
        return None
    for line in open(path, encoding="utf-8", errors="ignore"):
        m = re.match(rf"^\s*{re.escape(key)}\s*=\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def mask(url: str) -> str:
    """把連線字串裡的密碼遮掉再印出來。"""
    return re.sub(r"://([^:/@]+):([^@]*)@", r"://\1:****@", url)


def main() -> int:
    limit = None
    if "--rows" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--rows") + 1])

    pg_url = read_env("POSTGRES_URL")
    if not pg_url:
        print("❌ backend/.env 找不到 POSTGRES_URL。請新增一行（不要動 DATABASE_URL）：")
        print("   POSTGRES_URL=postgresql+psycopg://postgres:你的密碼@localhost:5432/portal")
        return 2

    print("=" * 70)
    print("  Phase 1 試點：把 ohip_revenue_history 搬到 PostgreSQL")
    print("=" * 70)

    # ── 來源：SQLite（全程唯讀）──────────────────────────────────────────
    from app.core.database import engine as sqlite_engine
    sqlite_engine.echo = False
    print(f"  來源 SQLite : {sqlite_engine.url}")
    print(f"  目標 Postgres: {mask(pg_url)}")

    try:
        pg = create_engine(pg_url)
        with pg.connect() as c:
            ver = c.execute(text("SELECT version()")).scalar_one()
        print(f"  已連上 → {ver.split(',')[0]}")
    except Exception as e:
        print(f"\n❌ 連不上 PostgreSQL：{type(e).__name__}: {str(e).splitlines()[0]}")
        print("   · 密碼是否正確？· portal 這個資料庫建好了嗎？")
        print("   · 先跑 python scripts\\pg_discover.py 確認")
        return 2

    # ── 取出 model 定義（只要這一張表）──────────────────────────────────
    import importlib
    import pkgutil
    import app.models as pkg
    for m in pkgutil.iter_modules(pkg.__path__):
        try:
            importlib.import_module(f"app.models.{m.name}")
        except Exception:
            pass
    from app.core.database import Base
    table = Base.metadata.tables.get(TABLE)
    if table is None:
        print(f"❌ Model 裡找不到 {TABLE}")
        return 1

    src_n = 0
    with sqlite_engine.connect() as c:
        if TABLE not in inspect(sqlite_engine).get_table_names():
            print(f"❌ SQLite 沒有 {TABLE}")
            return 1
        src_n = c.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar_one()
    print(f"\n  SQLite 來源筆數：{src_n:,}" + (f"（本次只搬前 {limit:,} 列）" if limit else ""))

    # ── 建表（只建這一張）───────────────────────────────────────────────
    print(f"\n  ① 在 PostgreSQL 重建資料表 {TABLE} …")
    table.drop(pg, checkfirst=True)
    table.create(pg)
    with pg.connect() as c:
        cols = len(inspect(pg).get_columns(TABLE))
        idxs = len(inspect(pg).get_indexes(TABLE))
    print(f"     ✅ 已建立：{cols} 個欄位、{idxs} 個索引")

    # ── 搬資料 ──────────────────────────────────────────────────────────
    print(f"\n  ② 複製資料（每批 {BATCH:,} 列）…")
    t0 = time.perf_counter()
    moved = 0
    col_names = [c.name for c in table.columns]
    with Session(sqlite_engine) as src, pg.begin() as dst:
        q = select(table)
        if limit:
            q = q.limit(limit)
        result = src.execute(q)
        while True:
            chunk = result.fetchmany(BATCH)
            if not chunk:
                break
            dst.execute(table.insert(), [dict(zip(col_names, row)) for row in chunk])
            moved += len(chunk)
            print(f"\r     已複製 {moved:,} / {limit or src_n:,} 列", end="", flush=True)
    el = time.perf_counter() - t0
    print(f"\n     ✅ 完成 {moved:,} 列，耗時 {el:.1f} 秒（約 {moved/max(el,0.01):,.0f} 列/秒）")

    # ── 驗證 ────────────────────────────────────────────────────────────
    print("\n  ③ 兩邊逐項比對…")
    # ⚠️⚠️ 金額欄位兩邊**不能直接比 SUM**，會差幾分錢，原因不是搬運出錯：
    #    model 宣告 `Numeric(16, 4)`，**PostgreSQL 會執行這個精度、SQLite 不會**。
    #    實測：同一筆值 SQLite 存成 25906.62118665299（完整 float、11 位小數），
    #    PostgreSQL 存成 25906.6212（依宣告四捨五入到 4 位）。
    #    196,840 列累積下來就差約 0.01 元。
    #    → 讓 SQLite 那邊也先套用宣告精度（ROUND(v, 4)）再加總，才是同一個口徑。
    #    這個現象會出現在專案全部 100 個 Numeric 欄位上。
    MONEY_SCALE = 4
    checks = [
        # (顯示名稱, SQLite 用的 SQL, PostgreSQL 用的 SQL)
        ("筆數",        f"SELECT COUNT(*) FROM {TABLE}", None),
        ("最早日期",    f"SELECT MIN(business_date) FROM {TABLE}", None),
        ("最晚日期",    f"SELECT MAX(business_date) FROM {TABLE}", None),
        ("market 基數", f"SELECT COUNT(DISTINCT market_code) FROM {TABLE}", None),
        ("房型基數",    f"SELECT COUNT(DISTINCT room_type) FROM {TABLE}", None),
        ("售出房晚合計", f"SELECT SUM(rooms_sold) FROM {TABLE}", None),
        ("房租營收合計",
         f"SELECT ROUND(SUM(ROUND(room_revenue, {MONEY_SCALE})), 2) FROM {TABLE}",
         f"SELECT ROUND(SUM(room_revenue), 2) FROM {TABLE}"),
        ("總營收合計",
         f"SELECT ROUND(SUM(ROUND(total_revenue, {MONEY_SCALE})), 2) FROM {TABLE}",
         f"SELECT ROUND(SUM(total_revenue), 2) FROM {TABLE}"),
    ]
    allok = True
    print(f"     {'項目':<16}{'SQLite':>22}{'PostgreSQL':>22}")
    print("     " + "-" * 64)
    for label, sql_a, sql_b in checks:
        sql_b = sql_b or sql_a
        if limit:
            sub = f"FROM (SELECT * FROM {TABLE} LIMIT {limit}) t"
            sql_a = sql_a.replace(f"FROM {TABLE}", sub)
            sql_b = sql_b.replace(f"FROM {TABLE}", sub)
        with sqlite_engine.connect() as c:
            a = c.execute(text(sql_a)).scalar()
        with pg.connect() as c:
            b = c.execute(text(sql_b)).scalar()
        ok = str(a) == str(b) or (
            isinstance(a, (int, float)) and isinstance(b, (int, float))
            and abs(float(a) - float(b)) < 1e-9
        )
        allok &= ok
        print(f"     {label:<16}{str(a):>22}{str(b):>22}  {'✅' if ok else '❌'}")
    print()
    print(f"     註：金額欄位的 SQLite 側已先套用宣告精度 ROUND(v, {MONEY_SCALE}) 再加總 ——")
    print("         Numeric(16,4) 只有 PostgreSQL 會執行，不對齊就會差幾分錢。")

    print()
    print("=" * 70)
    if allok:
        print("  ✅ 兩邊完全一致。第一張表已經在你的 PostgreSQL 裡了。")
    else:
        print("  ❌ 有項目對不上，請把上面的表格貼出來。")
    print("=" * 70)
    print(f"""
  用 pgAdmin 看：左側 portal → Schemas → public → Tables → {TABLE}
  右鍵 → View/Edit Data → First 100 Rows

  或在 Query Tool 貼這段（跟 Portal 畫面上的市場區隔分析同一個口徑）：

    SELECT market_code,
           SUM(rooms_sold)                    AS 售出房晚,
           ROUND(SUM(room_revenue), 0)        AS 房租營收,
           ROUND(SUM(room_revenue) / NULLIF(SUM(rooms_sold), 0), 0) AS ADR
    FROM {TABLE}
    WHERE hotel_id = 'SUMMER'
    GROUP BY market_code
    ORDER BY 房租營收 DESC;

  ⚠️ SQLite 完全沒有被改動，Portal 仍然只讀 SQLite。
     PG 這份目前純粹是副本，還沒有任何程式碼會去讀它。
""")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
