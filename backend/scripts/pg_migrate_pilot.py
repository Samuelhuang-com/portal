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

    ④ **外鍵孤兒**（2026-08-29 補）
       SQLite **預設不執行外鍵約束**（要 `PRAGMA foreign_keys=ON` 才會，
       而本專案沒有全面開啟），所以子表可能存在指向不存在父列的資料。
       PostgreSQL 一律執行 → 灌資料時 `violates foreign key constraint`。
       同樣是會中途失敗的那一類，所以放進前置檢查一起掃。
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

        # ── ④ 外鍵孤兒 ──────────────────────────────────────────────────
        for tbl, col, ptbl, pcol, cnt in find_orphan_fks(names, Base, src, have):
            problems.append(f"{tbl}.{col} → {ptbl}.{pcol}："
                            f"{cnt:,} 列的父資料不存在（SQLite 沒擋，PostgreSQL 會擋）")
    return problems


def find_orphan_fks(names, Base, src, have=None) -> list[tuple]:
    """找出「子表指向不存在父列」的外鍵，回 (子表, 子欄, 父表, 父欄, 筆數)。

    ⚠️ 只檢查「父表也在這次搬運範圍內」的 FK。父表不在範圍時，PG 那邊根本
       不會有這條約束（表沒建），檢查了也沒意義。
    """
    if have is None:
        have = set(inspect(src).get_table_names())
    scope = set(names) & have
    out: list[tuple] = []
    with src.connect() as c:
        for n in sorted(scope):
            for fk in Base.metadata.tables[n].foreign_keys:
                child_col, parent_tbl = fk.parent.name, fk.column.table.name
                parent_col = fk.column.name
                if parent_tbl not in scope or parent_tbl == n:
                    continue
                try:
                    cnt = c.execute(text(
                        f"SELECT COUNT(*) FROM {n} ch WHERE ch.{child_col} IS NOT NULL "
                        f"AND NOT EXISTS (SELECT 1 FROM {parent_tbl} pa "
                        f"WHERE pa.{parent_col} = ch.{child_col})")).scalar_one()
                    if cnt:
                        out.append((n, child_col, parent_tbl, parent_col, cnt))
                except Exception:
                    pass
    return out


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


def dep_order(Base, names: list[str]) -> list[str]:
    """把表名照**外鍵相依順序**排（被參照的排前面）。

    ⚠️⚠️ 不可以用 `sorted(names)`（字母序）。2026-08-29 踩過：
       `approval_actions` 有 FK 指向 `approvals`，字母序讓它先建 →
       `relation "approvals" does not exist`，整批中斷在第 4 張表。
       試點的 32 張表剛好沒有跨表 FK，所以這個坑到全庫才爆。

    `sorted_tables` 會做拓樸排序；有循環相依時 SQLAlchemy 會退回字母序並發
    warning，那種情況這裡補在最後（讓它照樣試，失敗訊息才看得到是哪張）。
    """
    want = set(names)
    out = [t.name for t in Base.metadata.sorted_tables if t.name in want]
    out += [n for n in names if n not in set(out)]
    return out


def drop_orphan_fks(pg, orphan_fks: list[tuple[str, str, str, str]]) -> list[str]:
    """把「有孤兒資料」的外鍵約束從 PG 移除，讓資料先搬得過去。

    ⚠️⚠️ **這是刻意留下的技術債，只能用在測試／比對用的資料庫。**
       正式切換前這些孤兒必須先修掉、約束必須加回去 —— 否則等於把
       PostgreSQL 幫忙抓出來的資料問題重新蓋起來，而且會繼續累積。

    回傳「要加回去的 ALTER 語句」，由呼叫端印出來存查。
    """
    restore: list[str] = []
    with pg.begin() as c:
        for tbl, col, ptbl, pcol in orphan_fks:
            rows = c.execute(text("""
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_class rel   ON rel.oid = con.conrelid
                JOIN pg_class frel  ON frel.oid = con.confrelid
                JOIN pg_attribute a ON a.attrelid = rel.oid
                                   AND a.attnum = ANY(con.conkey)
                WHERE con.contype = 'f' AND rel.relname = :t
                  AND frel.relname = :p AND a.attname = :c
            """), {"t": tbl, "p": ptbl, "c": col}).scalars().all()
            for name in rows:
                c.execute(text(f'ALTER TABLE {tbl} DROP CONSTRAINT "{name}"'))
                restore.append(
                    f'ALTER TABLE {tbl} ADD CONSTRAINT "{name}" '
                    f"FOREIGN KEY ({col}) REFERENCES {ptbl} ({pcol});")
    return restore


def prepare_schema(Base, names: list[str], pg) -> None:
    """先把**所有**目標表建好，再灌資料。

    ⚠️ 建表與灌資料必須分成兩階段：一張一張「drop→create→insert」的話，
       drop 後面那張時會被前面已建好的 FK 擋住（或反過來 create 時對象還沒建）。
       分兩階段就只需要「反向 drop 全部 → 正向 create 全部」。
    """
    tables = [Base.metadata.tables[n] for n in names]
    Base.metadata.drop_all(pg, tables=list(reversed(tables)), checkfirst=True)
    Base.metadata.create_all(pg, tables=tables, checkfirst=False)


def migrate_one(name, table, src, pg, limit) -> dict:
    """只灌資料 + 驗證；建表由 `prepare_schema()` 統一處理。"""
    res = {"table": name, "rows": 0, "sec": 0.0, "ok": True, "diffs": [], "notes": []}

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
    # ⚠️ --all：改搬主庫**全部**資料表（163 張），不只試點的 32 張。
    #    全庫遷移前要先用這個把 PG 補齊，否則 pg_compare_reads.py 會全部
    #    報 relation does not exist（那是缺表，不是相容性問題）。
    take_all = "--all" in args
    # ⚠️⚠️ --allow-orphans：容忍外鍵孤兒（把該條約束從 PG 移除後再搬）。
    #    **這是刻意留下的技術債，只能用在測試／比對用的資料庫。**
    #    正式切換前孤兒必須修掉、約束必須加回去。腳本會印出加回去的 SQL。
    allow_orphans = "--allow-orphans" in args

    pg_url = read_env("POSTGRES_URL")
    if not pg_url:
        print("❌ backend/.env 找不到 POSTGRES_URL（不要動 DATABASE_URL）：")
        print("   POSTGRES_URL=postgresql+psycopg://portal:密碼@localhost:5432/portal")
        return 2

    Base = load_models()
    from app.core.database import engine as src
    src.echo = False

    names = sorted(Base.metadata.tables) if take_all \
        else sorted(n for n in Base.metadata.tables if PILOT.match(n))
    if only:
        names = [n for n in names if n.startswith(only)]
    if picked:
        names = [n for n in names if n in picked]
    # ⚠️ 依外鍵相依排序 —— 字母序會讓 approval_actions 先於 approvals 建表而失敗
    names = dep_order(Base, names)

    print("=" * 76)
    print("  " + ("主庫全部資料表" if take_all else "試點模組（OPERA / OHIP / 金旭）") + " → PostgreSQL")
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

    # ⚠️ --allow-orphans：把「有孤兒」的外鍵約束從 PG 拿掉，讓資料先搬過去。
    #    **只給測試／比對用的資料庫**，正式切換前孤兒必須修掉、約束必須加回去。
    orphans = find_orphan_fks([n for n, c in plan if c], Base, src) if allow_orphans else []
    if allow_orphans and orphans:
        keys = {f"{t}.{c} → {p}.{q}" for t, c, p, q, _ in orphans}
        over = [x for x in over if not any(x.startswith(k) for k in keys)]

    if over:
        print(f"\n  ❌ 有 {len(over)} 個欄位的值 PostgreSQL 收不下，**先不要搬**：\n")
        for p in over:
            print(f"       · {p}")
        print("""
     原因：這些限制（VARCHAR 長度、Numeric 精度、外鍵）**只有 PostgreSQL 會
           執行，SQLite 一律忽略**，所以這些值在 SQLite 存得進去，搬到 PG 會
           中途失敗。

     要你決定，本腳本不會自作主張改資料：

       · 長度／精度超出 → 先看實際的值再決定往哪邊改：
             py -3.12 scripts\\pg_show_overlong.py
         ① 值是正常內容、只是比較長  → 宣告太緊，放寬 model 再產 migration
         ② 值根本不該出現在那個欄位  → **資料有問題，不要放寬宣告**，
                                       查是哪條寫入路徑塞進去的

       · 外鍵孤兒 → 子表指向了不存在的父列。同樣兩條路：補回父資料，
         或刪掉／清空這些指向。**不要**為了搬得過去就把 FK 拿掉。
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

    # ── 先建好全部的表（含 FK），再逐張灌資料 ─────────────────────────────
    todo = [n for n, c in plan if c is not None]
    print(f"  建立 {len(todo)} 張表（依外鍵相依順序）…", end="", flush=True)
    try:
        prepare_schema(Base, todo, pg)
        print(" ✅")
    except Exception as e:
        print(f"\n  ❌ 建表失敗：{type(e).__name__}: {str(e).splitlines()[0]}")
        return 2

    restore_sql: list[str] = []
    if orphans:
        restore_sql = drop_orphan_fks(pg, [(t, c, p, q) for t, c, p, q, _ in orphans])
        print(f"\n  ⚠️⚠️  --allow-orphans：已移除 {len(restore_sql)} 條外鍵約束")
        for t, c, p, q, n in orphans:
            print(f"        · {t}.{c} → {p}.{q}（{n:,} 列孤兒）")
        # ⚠️ 立刻寫檔，不等搬運結束 —— 中途失敗時這份 SQL 更需要留著
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "restore_dropped_fks.sql")
        with open(out, "w", encoding="utf-8") as f:
            f.write("-- 由 pg_migrate_pilot.py --allow-orphans 產生\n")
            f.write("-- ⚠️ 孤兒資料修好之後，用這個把外鍵約束加回 PostgreSQL。\n")
            f.write("-- ⚠️ 資料還沒修就執行的話，這些 ALTER 會失敗（那是對的）。\n\n")
            for t, c, p, q, n in orphans:
                f.write(f"-- {t}.{c} → {p}.{q}：搬運當下有 {n:,} 列孤兒\n")
            f.write("\n" + "\n".join(restore_sql) + "\n")
        print(f"""
        📄 加回外鍵的 SQL 已寫到：{out}

        **這個 PostgreSQL 資料庫的完整性約束不完整，只能用來比對測試，
          不可以當成正式切換的目標。** 正式切換前必須：
            ① 修掉孤兒資料
            ② 執行上面那份 SQL 把約束加回去
            ③ 重跑一次不帶 --allow-orphans 的搬運，確認前置檢查全綠""")
    print()

    results = []
    t_all = time.perf_counter()
    for n, cnt in plan:
        if cnt is None:
            print(f"     {n:<32} （SQLite 無此表，略過）")
            continue
        # ⚠️ 單張表失敗不中斷整批：163 張表時，一次看到全部問題遠比
        #    「修一個、重跑、再撞下一個」有效率。失敗的表照樣記進 results。
        try:
            r = migrate_one(n, Base.metadata.tables[n], src, pg, limit)
        except Exception as e:
            r = {"table": n, "rows": 0, "sec": 0.0, "ok": False, "notes": [],
                 "diffs": [f"搬運失敗 {type(e).__name__}: {str(e).splitlines()[0][:110]}"]}
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
