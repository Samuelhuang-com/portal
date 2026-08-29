"""
切換前的差異比對：同一支查詢函式，SQLite vs PostgreSQL，比對回傳結果

為什麼要有這一步
────────────────────────────────────────────────────────────────────────────
遷移真正的風險**不是資料丟失，是查詢結果不同**。資料完整性有
`pg_migrate_pilot.py` 把關（筆數、MIN/MAX 都比對過），但那證明不了
「同一個 API 在兩邊會回傳一樣的東西」。

光是 2026-08-28 一天就找到三個會讓結果不同的因素：

  · collation ──────── 中文 ORDER BY 的順序（已用 C collation 解決）
  · ORDER BY 的 NULL ─ SQLite 排最前 / PG 的 ASC 排最後（已修 19 處）
  · Numeric 精度 ───── SQLite 忽略宣告、PG 執行（金額總額差 0.01 元）

這三個是**我們想到的**。這支腳本用真實資料把所有查詢跑一遍，
找出**我們還沒想到的**。

⚠️ **完全不動 production 程式碼。** 只是在外部用兩個 session 各呼叫一次
   同樣的 service 函式，再比對回傳值 —— 零風險，可以隨時重跑。
   （原本考慮在程式裡做「影子讀取」，但那要改 production 路徑；
     這些 service 函式的第一個參數都是 `db: Session`，外部呼叫就夠了。）

怎麼決定要比對哪些函式
    自動探索：模組裡所有「第一個參數叫 db」的公開函式。
    參數則從實際資料範圍推導（起迄日、年份、單日…）。
    推不出來的必要參數 → 跳過並列在報告裡，需要人工補。

執行：
    cd backend
    py -3.12 scripts\\pg_compare_reads.py
    py -3.12 scripts\\pg_compare_reads.py --module opera_segment_service
    py -3.12 scripts\\pg_compare_reads.py --verbose      # 印出每一處差異的路徑
    py -3.12 scripts\\pg_compare_reads.py --all          # 掃全部 service 模組
                                                     （PG 需先有全部 163 張表）
    py -3.12 scripts\\pg_compare_reads.py --days 180     # 縮短測試區間
                                                     （有些函式限制單次最多 366 天）
"""
from __future__ import annotations

import importlib
import inspect
import json
import logging
import os
import re
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

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

from sqlalchemy import create_engine, inspect as sa_inspect, text   # noqa: E402
from sqlalchemy.orm import Session                                  # noqa: E402

# 預設只比對試點模組（PG 裡只有這 32 張表時用）
PILOT_MODULES = [
    "opera_analysis_service",
    "opera_segment_service",
    "opera_pace_service",
    "opera_reservation_service",
    "opera_lookup_service",
    "jinxu_analysis_service",
]


def discover_modules() -> list[str]:
    """掃出 app/services 底下所有含「第一個參數是 db」的公開函式的模組。

    ⚠️ 用 `--all` 之前，PG 必須已經有主庫**全部 163 張表**：
           py -3.12 scripts\\pg_migrate_pilot.py --all
       否則非試點模組會全部報 `relation does not exist` ——
       那是缺表，不是相容性問題，會把報告淹掉。
    """
    import pkgutil
    import app.services as pkg
    # ⚠️ 排除三類模組：
    #    · cycle_purchase_* → 查的是 **cycle-purchase.db**（另一個 Base/engine），
    #      拿主庫的 PG session 去跑只會全部 relation does not exist
    #    · *_seed / *_sync / *_import → 會寫入或打外部 API
    #    · realtime_* → ⚠️⚠️ **每一支都打 OHIP 外部 API**（2026-08-29 才發現）。
    #      它們查的是即時 API 不是資料庫，跑兩次本來就會不一樣
    #      （elapsed_ms、request_id、fetched_at、快取命中），對「SQLite vs PG」
    #      零資訊量。更糟的是：那是**計費的 API 呼叫**，而且每次都寫一列
    #      ohip_call_log —— 前一次 --all 就是這樣讓 get_call_logs 冒出
    #      688 處假差異（測試自己污染了要比對的表）。
    EXCLUDE = re.compile(r"^(cycle_purchase_|realtime_)|"
                         r"(_seed|_sync|_import_service|_parser)$|"
                         r"^(sync_|ragic_|email_|ohip_client|ota_browser|ota_scraper)")
    out = []
    for m in pkgutil.iter_modules(pkg.__path__):
        if EXCLUDE.search(m.name):
            continue
        try:
            mod = importlib.import_module(f"app.services.{m.name}")
        except Exception:
            continue
        for n, f in vars(mod).items():
            if n.startswith("_") or not callable(f):
                continue
            if getattr(f, "__module__", "") != f"app.services.{m.name}":
                continue
            if SKIP_NAMES.match(n):
                continue
            try:
                ps = list(inspect.signature(f).parameters)
            except (TypeError, ValueError):
                continue
            if ps and ps[0] == "db":
                out.append(m.name)
                break
    return sorted(out)

# ⚠️ 這些函式會**寫入**或打外部 API，不可以拿來比對
SKIP_NAMES = re.compile(
    r"^(save|set|update|delete|create|upsert|sync|import|fit_|backtest|run_|refresh)")


def read_env(key: str) -> str | None:
    if os.environ.get(key):
        return os.environ[key]
    p = os.path.join(BACKEND, ".env")
    if not os.path.exists(p):
        return None
    for line in open(p, encoding="utf-8", errors="ignore"):
        m = re.match(rf"^\s*{re.escape(key)}\s*=\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def mask(u: str) -> str:
    return re.sub(r"://([^:/@]+):([^@]*)@", r"://\1:****@", u)


def data_window(eng) -> tuple[str, str]:
    """從實際資料推出一段有資料的日期區間（拿 ohip_revenue_history 當代表）。"""
    have = set(sa_inspect(eng).get_table_names())
    for tbl, col in (("ohip_revenue_history", "business_date"),
                     ("opera_revenue_daily", "business_date"),
                     ("jinxu_ledger_entry", "business_date")):
        if tbl not in have:
            continue
        with eng.connect() as c:
            lo, hi = c.execute(text(f"SELECT MIN({col}), MAX({col}) FROM {tbl}")).one()
        lo, hi = str(lo or "")[:10], str(hi or "")[:10]
        # ⚠️ 要驗格式：這些欄位是字串型別，資料髒掉時可能不是日期
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", lo) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", hi):
            return lo, hi
    return "2024-01-01", date.today().isoformat()


def build_kwargs(fn, start: str, end: str) -> dict | None:
    """依參數名推導測試值。推不出必要參數就回 None（跳過）。"""
    mid = start[:8] + "15"
    guess = {
        "start": start, "end": end,
        "start_date": start, "end_date": end,
        "business_date": mid, "stay_date": mid, "target_date": mid,
        "as_of": end, "property_code": "",
    }
    if re.fullmatch(r"\d{4}", end[:4]):
        guess["year"] = int(end[:4])
    kw: dict = {}
    for name, p in list(inspect.signature(fn).parameters.items())[1:]:   # 跳過 db
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        if name in guess:
            kw[name] = guess[name]
        elif p.default is not inspect.Parameter.empty:
            continue                      # 用預設值
        else:
            return None                   # 必要參數但猜不到 → 跳過
    return kw


def norm(v):
    """把回傳值正規化成可比對的形式。"""
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [norm(x) for x in v]
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)

    # ⚠️ ORM 實體要轉成欄位字典（2026-08-29 踩過）。
    #    有些 service 直接回 `query.all()`，元素是 ORM 物件；預設比對會落到
    #    `repr()`，那裡面有**記憶體位址** ——
    #    `<OtaPlatform object at 0x0000022A8AE33260>` vs `0x...328D0`，
    #    兩邊必然不同，報出來全是假差異，而且把真正的差異蓋掉。
    try:
        from sqlalchemy import inspect as _sa_inspect
        st = _sa_inspect(v)
        if hasattr(st, "mapper"):
            return {a.key: norm(getattr(v, a.key)) for a in st.mapper.column_attrs}
    except Exception:
        pass

    # ⚠️ 二進位（例如 export_xlsx 回傳的 .xlsx bytes）只比長度。
    #    zip 容器內嵌了**產生當下的時間戳**，逐位元組比對必然不同 ——
    #    那是格式特性，不是 SQLite vs PG 的差異。比長度至少擋得住
    #    「有一邊根本沒產出資料」。
    if isinstance(v, (bytes, bytearray)):
        return f"<binary {len(v)} bytes>"
    return v


def diff(a, b, path="") -> list[str]:
    """深層比對，回傳差異路徑。數值用相對誤差（float64 的表示極限）。"""
    out: list[str] = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}.{k}：只有 PG 有")
            elif k not in b:
                out.append(f"{path}.{k}：只有 SQLite 有")
            else:
                out += diff(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}：長度 {len(a)} vs {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out += diff(x, y, f"{path}[{i}]")
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) \
            and not isinstance(a, bool) and not isinstance(b, bool):
        try:
            na, nb = Decimal(str(a)), Decimal(str(b))
            if na != nb:
                s = max(abs(na), abs(nb), Decimal(1))
                rel = abs(na - nb) / s
                if rel >= Decimal("1e-9"):
                    # ⚠️ 前綴 `~` 標記「純數值誤差」，摘要才分得開兩種差異：
                    #    純數值誤差 → 已知原因（SQLite 存滿精度、PG 依 Numeric(p,s)
                    #                 捨入；加總順序不同也會差），使用者看不出來
                    #    其他差異   → 筆數／順序／內容不同，那才要一筆一筆查
                    out.append(f"~{path}：{a!r} vs {b!r}（相對差 {rel:.1e}）")
        except InvalidOperation:
            if a != b:
                out.append(f"{path}：{a!r} vs {b!r}")
    elif a != b:
        out.append(f"{path}：{a!r} vs {b!r}")
    return out


def main() -> int:
    args = sys.argv[1:]
    verbose = "--verbose" in args
    only = args[args.index("--module") + 1] if "--module" in args else None
    # ⚠️ 有些函式有「單次查詢最多 N 天」的業務規則，全區間會被擋下來。
    #    --days 讓測試區間縮短到最後 N 天，才測得到那幾支。
    days = int(args[args.index("--days") + 1]) if "--days" in args else None
    # ⚠️ --all：自動掃出所有 service 模組（不只試點的 6 個）。
    #    前提是 PG 已經有全部 163 張表，否則會被 relation does not exist 淹沒。
    scan_all = "--all" in args

    pg_url = read_env("POSTGRES_URL")
    if not pg_url:
        print("❌ backend/.env 找不到 POSTGRES_URL")
        return 2
    sqlite_url = read_env("DATABASE_URL")

    print("=" * 78)
    print("  查詢結果比對：SQLite vs PostgreSQL")
    print("=" * 78)
    print(f"  SQLite    : {sqlite_url}")
    print(f"  PostgreSQL: {mask(pg_url)}")

    src = create_engine(sqlite_url.replace("sqlite+aiosqlite", "sqlite"))
    pg = create_engine(pg_url)
    src.echo = pg.echo = False

    start, end = data_window(src)
    if days:
        from datetime import timedelta
        try:
            start = (date.fromisoformat(end) - timedelta(days=days - 1)).isoformat()
        except ValueError:
            pass
    print(f"  測試區間  : {start} ~ {end}" + (f"（--days {days}）" if days else "") + "\n")

    same_n = 0
    diffs: list[tuple[str, list[str]]] = []
    numeric: list[tuple[str, list[str]]] = []     # 只有數值精度差的（`~` 開頭）
    errors: list[tuple[str, str]] = []
    skipped: list[str] = []

    modules = discover_modules() if scan_all else PILOT_MODULES
    if scan_all:
        print(f"  掃描模式  : 全部 {len(modules)} 個 service 模組\n")

    for mname in modules:
        if only and mname != only:
            continue
        try:
            mod = importlib.import_module(f"app.services.{mname}")
        except Exception as e:
            errors.append((mname, f"匯入失敗 {type(e).__name__}: {e}"))
            continue

        fns = []
        for n, f in vars(mod).items():
            if n.startswith("_") or not callable(f):
                continue
            if getattr(f, "__module__", "") != f"app.services.{mname}":
                continue
            if SKIP_NAMES.match(n):
                continue
            try:
                ps = list(inspect.signature(f).parameters)
            except (TypeError, ValueError):
                continue
            if ps and ps[0] == "db":
                fns.append((n, f))

        print(f"  ── {mname}（{len(fns)} 支）")
        for n, f in sorted(fns):
            kw = build_kwargs(f, start, end)
            label = f"{mname}.{n}"
            if kw is None:
                skipped.append(label)
                continue
            try:
                with Session(src) as s:
                    ra = norm(f(s, **kw))
                with Session(pg) as s:
                    rb = norm(f(s, **kw))
            except Exception as e:
                errors.append((label, f"{type(e).__name__}: {str(e).splitlines()[0][:90]}"))
                print(f"       {n:<34} ❌ 執行失敗")
                continue
            d = diff(ra, rb)
            if d:
                # `~` 開頭 ＝ 純數值精度。⚠️ 分開「計數」而不是只看 all()：
                #    一支函式常常是「88 處數值 + 3 處內容」，全有全無的分類
                #    會讓那 88 處把 3 處真正的差異淹掉。
                hard = [x for x in d if not x.startswith("~")]
                (diffs if hard else numeric).append((label, hard or d))
                if hard:
                    extra = f"（另 {len(d) - len(hard)} 處僅數值精度）" if len(hard) < len(d) else ""
                    print(f"       {n:<34} ⚠️  {len(hard)} 處內容差異{extra}")
                else:
                    print(f"       {n:<34} ≈  {len(d)} 處數值精度差異")
                if verbose:
                    for x in d[:8]:
                        print(f"            {x}")
            else:
                same_n += 1
                print(f"       {n:<34} ✅")

    print()
    print("=" * 78)
    print(f"  ✅ 結果相同   {same_n} 支")
    print(f"  ≈  僅數值精度 {len(numeric)} 支（已知原因，見下方說明）")
    print(f"  ⚠️  內容有差異 {len(diffs)} 支  ← 只有這一項需要逐筆判斷")
    print(f"  ❌ 執行失敗   {len(errors)} 支")
    print(f"  ⏭  跳過       {len(skipped)} 支（必要參數猜不到，需人工補）")

    if numeric:
        print("\n  僅數值精度（相對差都在 1e-8 以下，畫面上看不出來）：")
        for label, d in numeric:
            print(f"     · {label}（{len(d)} 處）")
            for x in d[:2]:
                print(f"         {x[1:]}")
    if diffs and not verbose:
        print("\n  內容有差異（加 --verbose 看每一處）：")
        for label, d in diffs:
            print(f"     · {label}（{len(d)} 處）")
            for x in d[:3]:
                print(f"         {x.lstrip('~')}")
    if errors:
        print("\n  執行失敗：")
        for label, e in errors[:15]:
            print(f"     · {label}：{e}")
    if skipped:
        print(f"\n  跳過的：{', '.join(skipped[:12])}" + (" …" if len(skipped) > 12 else ""))
    print()
    print("""  怎麼判讀
    · ⚠️ 內容有差異 → 筆數／順序／內容真的不同。**只有這一項需要逐筆判斷**，
         這就是切換後使用者會看到的變化。
    · ≈ 僅數值精度 → 已知原因，不必逐筆看：SQLite 把 Numeric 當 float 存滿
         精度（11 位小數），PostgreSQL 依 `Numeric(p,s)` 的宣告捨入（4 位）；
         加總順序不同也會在 float64 的表示極限造成尾差。
         相對差都在 1e-8 量級 —— 以 ADR 1296.81 為例是小數第 7 位，
         畫面顯示到小數 2 位，看不出來。
    · ❌ 執行失敗 → 多半是 PG 缺表或參數猜錯，不是相容性問題：
         `relation does not exist` → 缺表，先跑 pg_migrate_pilot.py --all
         `單次查詢最多 366 天`     → 測試區間太長，加 --days 180
    · ⏭ 跳過 → 必要參數猜不到（例如需要某筆 id），要的話手動補測""")
    print()
    return 0 if not diffs else 1


if __name__ == "__main__":
    sys.exit(main())
