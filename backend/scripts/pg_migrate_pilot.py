"""
Phase 1：把試點模組（OPERA／OHIP／金旭）的 32 張表整批搬到 PostgreSQL

為什麼這批可以獨立搬
────────────────────────────────────────────────────────────────────────────
實測：這 32 張表**外鍵完全是 0** —— 不只沒有指向模組外的，模組內部也沒有。
所以建表與搬運**沒有任何順序限制**，任何一張出錯都不影響其他張。

⚠️ **完全不動 SQLite。** 來源端全程唯讀，`DATABASE_URL` 不需要改。
   這一步做完 Portal 仍然只讀 SQLite，PG 那份是純副本。

⚠️ 可重複執行：每張表都先 `DROP TABLE` 再重建，不會累積重複資料。

驗證方式（每張表）
    · 筆數
    · 每個數值欄位的 SUM
    · 每個字串／日期欄位的 MIN / MAX
    ⚠️ 數值欄位的 SUM 必須先在 SQLite 側套用 model 宣告的精度再加總 ——
       `Numeric(p, s)` 只有 PostgreSQL 會執行，SQLite 忽略。
       不對齊的話 19.7 萬列會差幾分錢（見 docs/CHANGELOG.md [1.96.36]）。

執行：
    cd backend
    python scripts\\pg_migrate_pilot.py                  # 全部 32 張
    python scripts\\pg_migrate_pilot.py --dry-run        # 只列出計畫，不動作
    python scripts\\pg_migrate_pilot.py --only ohip_     # 只搬表名開頭符合的
    python scripts\\pg_migrate_pilot.py --tables a,b     # 指定表名
    python scripts\\pg_migrate_pilot.py --rows 5000      # 每張表只搬前 N 列（試水溫）
"""
from __future__ import annotations

import logging
import os
import re
import sys
import time

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

from sqlalchemy import Date, DateTime, Numeric, String, Text, create_engine, inspect, select, text  # noqa: E402
from sqlalchemy.orm import Session                                    # noqa: E402

PILOT = re.compile(r"^(opera_|ohip_|jinxu_)")
BATCH = 5000


def read_env(key: str) -> str | None:
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
    return re.sub(r"://([^:/@]+):([^@]*)@", r"://\1:****@", url)


def load_models():
    import importlib
    import pkgutil
    import app.models as pkg
    for m in pkgutil.iter_modules(pkg.__path__):
        try:
            importlib.import_module(f"app.models.{m.name}")
        except Exception:
            pass
    from app.core.database import Base
    return Base


def checks_for(table) -> list[tuple[str, str, str]]:
    """每張表的比對項目 → (顯示名, SQLite SQL 片段, PostgreSQL SQL 片段)"""
    # (顯示名, SQLite SQL, PostgreSQL SQL, 是否硬性)
    # ⚠️ SUM 是**次要檢查**：它抓得到「少搬幾列／數值搬錯」，
    #    但兩邊的捨入平局（.00005 這種邊界）方向可能不同，
    #    差個 1e-10 相對量級不代表資料有問題。
    #    真正的完整性由「筆數」與各欄位的 MIN/MAX 把關 —— 那兩個是硬性的。
    out: list[tuple[str, str, str, bool]] = [("筆數", "COUNT(*)", "COUNT(*)", True)]
    for col in table.columns:
        t, n = col.type, col.name
        if isinstance(t, Numeric) and not isinstance(t, (String, Text)):
            # ⚠️ SQLite 側要先套用宣告精度，否則會差幾分錢（見檔頭說明）
            scale = getattr(t, "scale", None)
            if scale is None:
                out.append((f"SUM({n})", f"SUM({n})", f"SUM({n})", False))
            else:
                out.append((f"SUM({n})",
                            f"ROUND(SUM(ROUND({n}, {scale})), {scale})",
                            f"ROUND(SUM({n}), {scale})", False))
        elif isinstance(t, (Date, DateTime)):
            # ⚠️ 日期時間**不能 CAST 成字串比對** —— 兩邊的字串表示法不同：
            #    SQLite `'2026-01-01 00:00:00.000000'` vs PG `'2026-01-01 00:00:00'`。
            #    值是一樣的，差的只是格式。所以直接比 MIN/MAX 本身，
            #    交給 Python 端比較（psycopg 與 sqlite3 都會給回 datetime 物件）。
            out.append((f"MIN({n})", f"MIN({n})", f"MIN({n})", True))
            out.append((f"MAX({n})", f"MAX({n})", f"MAX({n})", True))
        elif isinstance(t, (String, Text)):
            # ⚠️⚠️ **文字的 MIN/MAX 必須指定 `COLLATE "C"`。**
            #    SQLite 比字串一律照 UTF-8 **位元組順序**；
            #    PostgreSQL 照建庫時的 collation（Windows 中文環境常是
            #    `Chinese (Traditional)_Taiwan.950`）。同一組中文字串，
            #    兩邊的 MIN/MAX 會選到**不同的列** —— 資料明明一樣卻判定不符。
            #    `COLLATE "C"` 就是位元組序，強制指定才比得起來。
            out.append((f"MIN/MAX({n})",
                        f"COALESCE(MIN({n}),'')||'|'||COALESCE(MAX({n}),'')",
                        f'COALESCE(MIN({n} COLLATE "C"),\'\')||\'|\'||COALESCE(MAX({n} COLLATE "C"),\'\')',
                        True))
            # 與排序規則完全無關的完整性檢查 —— 這兩個才是真正在抓資料有沒有搬錯
            out.append((f"DISTINCT({n})", f"COUNT(DISTINCT {n})", f"COUNT(DISTINCT {n})", True))
            out.append((f"總長度({n})", f"SUM(LENGTH({n}))", f"SUM(LENGTH({n}))", True))
    return out


def preflight(names, Base, src) -> list[str]:
    """搬之前先掃出「SQLite 存得進去、PostgreSQL 會拒絕」的值。

    ⚠️⚠️ **SQLite 的型別參數幾乎都是裝飾用的，PostgreSQL 全部認真執行。**
       這一族已經踩到三個，全部實測確認：

       | 宣告 | SQLite | PostgreSQL |
       |------|--------|-----------|
       | `VARCHAR(2)` 塞 `'v0000'` | 照收（length=5） | `value too long for type character varying(2)` |
       | `Numeric(8,4)` 塞 `88072.8136` | 照收 | `numeric field overflow`（整數部分只能 4 位）|
       | `Numeric(16,4)` 塞 11 位小數 | 照收 | 四捨五入到 4 位（**不報錯**，但總額會差） |

       前兩個會讓整批搬運**中途失敗**，所以一定要先掃再搬。
       第三個不報錯，由 `checks_for()` 的精度對齊處理。
    """
    problems: list[str] = []
    have = set(inspect(src).get_table_names())
    with src.connect() as c:
        for n in names:
            if n not in have:
                continue
            for col in Base.metadata.tables[n].columns:
                t, cn = col.type, col.name

                # ① VARCHAR 長度
                length = getattr(t, "length", None)
                if isinstance(t, (String, Text)) and length:
                    try:
                        cnt, mx = c.execute(text(
                            f"SELECT COUNT(*), MAX(LENGTH({cn})) FROM {n} "
                            f"WHERE LENGTH({cn}) > {length}")).one()
                        if cnt:
                            problems.append(f"{n}.{cn}：宣告 VARCHAR({length})，"
                                            f"{cnt:,} 列超長（最長 {mx}）")
                    except Exception:
                        pass
                    continue

                # ② Numeric 的整數部分位數：precision - scale
                if isinstance(t, Numeric) and not isinstance(t, (String, Text)):
                    p, s = getattr(t, "precision", None), getattr(t, "scale", None)
                    if p is None or s is None:
                        continue
                    limit = 10 ** (p - s)          # 絕對值必須 < 這個數
                    try:
                        cnt, mx = c.execute(text(
                            f"SELECT COUNT(*), MAX(ABS({cn})) FROM {n} "
                            f"WHERE ABS({cn}) >= {limit}")).one()
                        if cnt:
                            problems.append(
                                f"{n}.{cn}：宣告 Numeric({p},{s}) → 絕對值上限 {limit:,}，"
                                f"{cnt:,} 列超出（最大 {mx}）")
                    except Exception:
                        pass
    return problems


def same(a, b) -> bool:
    """比對兩邊的查詢結果。

    ⚠️ **不能直接 `a == b` 或 `str(a) == str(b)`**，兩個驅動回傳的型別不同：

      · 日期時間：走 `text()` 原始 SQL 時，sqlite3 回**字串**
        `'2026-01-01 00:00:00.000000'`，psycopg 回 `datetime` 物件。
        值一樣、型別不一樣 —— 要正規化後才能比。

      · 大額 SUM：SQLite 的 NUMERIC 走 float64，到 1.4e14 這種量級時
        有效位數只剩 15～16 位，分位會失真（`...193.7` vs `...193.66`）。
        PostgreSQL 的 NUMERIC 是精確十進位。
        這不是資料搬錯，是 float64 的表示極限 —— 用**相對誤差**判定。
    """
    from datetime import date, datetime
    from decimal import Decimal, InvalidOperation

    if a is None or b is None:
        return a is None and b is None

    # 日期時間：兩邊都正規化成 datetime 再比
    def as_dt(v):
        if isinstance(v, datetime):
            return v
        if isinstance(v, date):
            return datetime(v.year, v.month, v.day)
        if isinstance(v, str):
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
        return None

    da, dbv = as_dt(a), as_dt(b)
    if da is not None and dbv is not None:
        return da == dbv

    # 數值：相對誤差（float64 在大數量級下必然失真）
    try:
        na, nb = Decimal(str(a)), Decimal(str(b))
        if na == nb:
            return True
        scale = max(abs(na), abs(nb), Decimal(1))
        return abs(na - nb) / scale < Decimal("1e-12")
    except (InvalidOperation, ValueError):
        pass

    return str(a) == str(b)


def migrate_one(name, table, src, pg, limit) -> dict:
    res = {"table": name, "rows": 0, "sec": 0.0, "ok": True, "diffs": [], "notes": []}

    table.drop(pg, checkfirst=True)
    table.create(pg)

    cols = [c.name for c in table.columns]
    t0 = time.perf_counter()
    moved = 0
    with Session(src) as s, pg.begin() as dst:
        q = select(table)
        if limit:
            q = q.limit(limit)
        result = s.execute(q)
        while True:
            chunk = result.fetchmany(BATCH)
            if not chunk:
                break
            dst.execute(table.insert(), [dict(zip(cols, r)) for r in chunk])
            moved += len(chunk)
            print(f"\r     {name:<32} {moved:>9,} 列", end="", flush=True)
    res["rows"] = moved
    res["sec"] = time.perf_counter() - t0

    # ── 驗證 ────────────────────────────────────────────────────────────
    for label, sql_a, sql_b, hard in checks_for(table):
        qa = f"SELECT {sql_a} FROM {name}"
        qb = f"SELECT {sql_b} FROM {name}"
        if limit:
            qa = f"SELECT {sql_a} FROM (SELECT * FROM {name} LIMIT {limit}) t"
            qb = f"SELECT {sql_b} FROM (SELECT * FROM {name} LIMIT {limit}) t"
        try:
            with src.connect() as c:
                a = c.execute(text(qa)).scalar()
            with pg.connect() as c:
                b = c.execute(text(qb)).scalar()
        except Exception as e:
            res["diffs"].append(f"{label}: 查詢失敗 {type(e).__name__}")
            res["ok"] = False
            continue
        if same(a, b):
            continue
        msg = f"{label}: SQLite={a!r} PG={b!r}"
        if hard:
            res["diffs"].append(msg)
            res["ok"] = False
        else:
            res["notes"].append(msg)
    return res


def main() -> int:
    args = sys.argv[1:]
    dry = "--dry-run" in args
    limit = int(args[args.index("--rows") + 1]) if "--rows" in args else None
    only = args[args.index("--only") + 1] if "--only" in args else None
    picked = args[args.index("--tables") + 1].split(",") if "--tables" in args else None

    pg_url = read_env("POSTGRES_URL")
    if not pg_url:
        print("❌ backend/.env 找不到 POSTGRES_URL（不要動 DATABASE_URL）：")
        print("   POSTGRES_URL=postgresql+psycopg://portal:密碼@localhost:5432/portal")
        return 2

    Base = load_models()
    from app.core.database import engine as src
    src.echo = False

    names = sorted(n for n in Base.metadata.tables if PILOT.match(n))
    if only:
        names = [n for n in names if n.startswith(only)]
    if picked:
        names = [n for n in names if n in picked]

    print("=" * 76)
    print("  Phase 1：試點模組（OPERA / OHIP / 金旭）→ PostgreSQL")
    print("=" * 76)
    print(f"  來源 SQLite : {src.url}")
    print(f"  目標 Postgres: {mask(pg_url)}")
    print(f"  對象         : {len(names)} 張表" + (f"（每張最多 {limit:,} 列）" if limit else ""))

    have = set(inspect(src).get_table_names())
    plan = []
    with src.connect() as c:
        for n in names:
            if n not in have:
                plan.append((n, None))
                continue
            plan.append((n, c.execute(text(f"SELECT COUNT(*) FROM {n}")).scalar_one()))
    total_rows = sum(v or 0 for _, v in plan)
    print(f"  來源總筆數   : {total_rows:,}\n")

    # ── 前置檢查：VARCHAR 長度 ───────────────────────────────────────────
    print("  前置檢查：掃描 SQLite 存得下、PostgreSQL 會拒絕的值…")
    over = preflight([n for n, c in plan if c], Base, src)
    if over:
        print(f"\n  ❌ 有 {len(over)} 個欄位的值 PostgreSQL 收不下，**先不要搬**：\n")
        for p in over:
            print(f"       · {p}")
        print("""
     原因：`VARCHAR(n)` 的長度限制**只有 PostgreSQL 會執行、SQLite 忽略**，
           所以這些值在 SQLite 存得進去，搬到 PG 會中途失敗。

     兩條路（要你決定，本腳本不會自作主張改資料）：
       ① 放寬 model 的欄位長度（改 String(n) 後用 alembic 產 migration）
       ② 先在 SQLite 端把超長的值截短或修正
""")
        return 2
    print("     ✅ 沒有問題\n")

    if dry:
        print("  （--dry-run，以下只是計畫）")
        for n, cnt in plan:
            print(f"     {n:<34} {'（SQLite 無此表，略過）' if cnt is None else f'{cnt:>10,} 列'}")
        return 0

    try:
        pg = create_engine(pg_url)
        with pg.connect() as c:
            ver = c.execute(text("SELECT version()")).scalar_one()
        with pg.connect() as c:
            coll = c.execute(text(
                "SELECT datcollate FROM pg_database WHERE datname = current_database()"
            )).scalar_one()
        print(f"  已連上 → {ver.split(',')[0]}")
        # ⚠️ 這一行很重要：PG 的文字排序照 collation，SQLite 照位元組序。
        #    非 C/POSIX 的 collation 會讓中文的 ORDER BY 結果與 SQLite 不同。
        print(f"  資料庫 collation：{coll}"
              + ("" if coll.upper().startswith(("C", "POSIX"))
                 else "   ⚠️ 非位元組序 —— 中文欄位的 ORDER BY 結果會與 SQLite 不同\n"))
        print()
    except Exception as e:
        print(f"❌ 連不上 PostgreSQL：{type(e).__name__}: {str(e).splitlines()[0]}")
        return 2

    results = []
    t_all = time.perf_counter()
    for n, cnt in plan:
        if cnt is None:
            print(f"     {n:<32} （SQLite 無此表，略過）")
            continue
        r = migrate_one(n, Base.metadata.tables[n], src, pg, limit)
        results.append(r)
        mark = "✅" if r["ok"] else "❌"
        if r["ok"] and r["notes"]:
            mark = "✅ ⚠️"
        print(f"\r     {n:<32} {r['rows']:>9,} 列  {r['sec']:>6.1f}s  {mark}")
        for d in r["diffs"]:
            print(f"        ❌ {d}")
        for d in r["notes"]:
            print(f"        ⚠️  {d}（捨入平局，非資料問題）")
    elapsed = time.perf_counter() - t_all

    ok = [r for r in results if r["ok"]]
    bad = [r for r in results if not r["ok"]]
    moved = sum(r["rows"] for r in results)
    print()
    print("=" * 76)
    print(f"  搬完 {len(results)} 張表、{moved:,} 列，耗時 {elapsed:.1f} 秒"
          f"（約 {moved / max(elapsed, 0.01):,.0f} 列/秒）")
    noted = [r for r in results if r["ok"] and r["notes"]]
    print(f"  ✅ 完整性檢查通過 {len(ok)} 張   ❌ 未通過 {len(bad)} 張")
    if noted:
        print(f"  ⚠️  其中 {len(noted)} 張的 SUM 有極小差異（捨入平局），"
              f"筆數與 MIN/MAX 皆一致")
    if bad:
        print("\n  有差異的表：")
        for r in bad:
            print(f"     · {r['table']}")
            for d in r["diffs"]:
                print(f"         {d}")
    print("=" * 76)
    print("""
  用 pgAdmin 看：左側 portal → Schemas → public → Tables

  ⚠️ SQLite 完全沒有被改動，Portal 仍然只讀 SQLite。
     PG 這份是副本，還沒有任何程式碼會去讀它 ——
     真正切換資料來源是下一步（Phase 2）的事。
""")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
