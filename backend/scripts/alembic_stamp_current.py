"""
把「已經是最新結構、但沒有 alembic_version」的資料庫 stamp 到正確的版本

要解決什麼
────────────────────────────────────────────────────────────────────────────
2026-09-01 在測試區跑 `python -m alembic upgrade head` 直接炸掉：

    psycopg.errors.DuplicateTable: relation "ai_conversation_log" already exists
    ...
    alembic/versions/20260828_baseline_main_baseline.py, line 23, in upgrade
        op.create_table('ai_conversation_log', ...)

**這不是 migration 寫錯，是資料庫沒有 `alembic_version` 表。**
沒有版本號 → Alembic 認為這是一個空庫 → 從 `baseline_main` 開始整串跑 →
第一個 `CREATE TABLE` 就撞上早就存在的表。

根因：2026-08-29 切到 PostgreSQL 時，`pg_cutover.py` 是用 `create_all()`
建結構的，**從頭到尾沒有做 stamp 這一步**（跟 `pg_fix_sequences.py` 修的
「沒做 setval」是同一類遺漏：搬遷腳本只搬了看得見的東西）。

為什麼不能直接用 alembic_stamp_baseline.py
────────────────────────────────────────────────────────────────────────────
那支的 drift 檢查是「Model 有、DB 沒有 ＝ 拒絕 stamp」。現在 Model 已經含有
`tenants.source_company_id`（migration `tncomp` 要加的欄位），DB 還沒有，
於是它會判定 drift 而擋下來 —— 但那個差異**正是我們接下來要用 migration
補上的東西**，不是需要修的 drift。

而且那支只會 stamp 到 `baseline_main`。這個庫的結構其實已經包含 `widen7`
與 `ctvnull` 的效果（切換時的 `create_all` 是照當時的 Model 建的），
stamp 成 baseline 之後跑 upgrade，那兩支會重跑一次。`widen7` 重跑無害
（把已經是 Text 的欄位再改成 Text），`ctvnull` 重跑也無害（已經 nullable
再設一次 nullable），但**「版本號說的話與資料庫的實情不符」本身就是隱患**，
下一支 migration 就不一定這麼幸運了。

這支腳本做什麼
────────────────────────────────────────────────────────────────────────────
① 逐支檢查**每一個 revision 的實際證據**是否已經存在於資料庫裡
   （不是問 alembic，是直接去看欄位型別／nullable／欄位在不在）
② 依證據推出「這個庫實際上停在哪一版」
③ 做一次 drift 檢查，但**排除掉尚未套用的 migration 會補上的欄位**
④ `--apply` 才實際 `alembic stamp <推出來的版本>`

stamp 完之後再跑 `alembic upgrade head`，就只會跑真正還沒套用的那幾支。

⚠️⚠️ 本腳本**只寫 `alembic_version` 一列版本號**，不建表、不改欄位、不動資料。

⚠️ 「證據查不出來」與「證據不存在」是兩件完全不同的事。任何一項檢查失敗
   （查詢出錯、表不存在）一律回離開碼 2，**不會**因為「看起來沒問題」就放行
   —— 檢查工具最危險的失效方式是回報「沒問題」（見 CHANGELOG [1.96.39]）。

執行
────────────────────────────────────────────────────────────────────────────
    cd backend

    # 測試區（本機 anaconda 的 python）
    python scripts\\alembic_stamp_current.py              # 唯讀診斷
    python scripts\\alembic_stamp_current.py --apply      # 實際 stamp

    # 正式區（D:\\portal / C:\\portal）
    py -3.11 scripts\\alembic_stamp_current.py
    py -3.11 scripts\\alembic_stamp_current.py --apply

⚠️ 兩區直譯器不同，指令不能互抄（同 pg_fix_sequences.py）。
⚠️ 執行前請先停掉會寫入的程式（後端服務、sync_tool.py），並先備份
   （`python scripts\\pg_backup.py`）。

離開碼
    0 = 已經 stamp 正確，或已成功 stamp
    1 = 診斷出需要 stamp，但沒有加 --apply
    2 = 檢查失敗、狀態與預期不符，或執行出錯
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import logging                                                    # noqa: E402
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

from sqlalchemy import inspect, text                              # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# 主庫 revision 鏈的「實際證據」
#
# ⚠️ 這裡問的是**資料庫的實情**，不是 alembic 的說法：直接看欄位型別、
#    nullable、欄位在不在。alembic_version 不可信（就是它不見了才要跑這支）。
#
# 每一項：(revision, 說明, 檢查函式, 這支 migration 會新增的欄位)
#   檢查函式回傳 True=證據存在／False=證據不存在／拋例外=查不出來（→ 離開碼 2）
#   最後那個「會新增的欄位」是給 drift 檢查排除用的：尚未套用的 migration
#   要補的欄位，本來就該是 Model 有、DB 沒有，不算 drift。
#
# ⚠️⚠️ 【維護規則】每新增一支 migration，就要在下面的 MAIN_CHAIN／CP_CHAIN
#       補一項，否則這支腳本會把「其實更新的資料庫」判成停在舊版本，
#       stamp 下去等於把版本號**倒退**，接著 upgrade head 會重跑中間那幾支
#       而撞 DuplicateTable。
#       2026-09-21 實際發生過：MAIN_CHAIN 停在 usrdept（漏了 compset／tcpurch／
#       audchk）、CP_CHAIN 只有 baseline_cp（漏了 cpragicurl／cpragicdept），
#       導致週採庫的 cpragicdept 被誤報成「與證據推出的 baseline_cp 不符」。
# ═══════════════════════════════════════════════════════════════════════════

def _col(insp, table: str, col: str) -> dict:
    """取欄位資訊；表或欄位不存在就拋例外（＝查不出來，不是「沒問題」）。"""
    cols = {c["name"]: c for c in insp.get_columns(table)}
    if col not in cols:
        raise LookupError(f"{table}.{col} 不存在")
    return cols[col]


def _chk_baseline(insp) -> bool:
    # baseline 的證據＝那些表存在。挑一張 baseline 建的表當代表即可
    # （就是報錯訊息裡的那一張）。
    return "ai_conversation_log" in set(insp.get_table_names())


def _chk_widen7(insp) -> bool:
    # widen7 把 4 張巡檢表的 result_raw 從 VARCHAR(50) 放寬成 TEXT。
    # PG 上 TEXT 的 length 是 None，VARCHAR(50) 是 50。
    return _col(insp, "b1f_inspection_item", "result_raw")["type"].length is None


def _chk_ctvnull(insp) -> bool:
    return bool(_col(insp, "contracts", "vendor_id")["nullable"])


def _chk_tncomp(insp) -> bool:
    try:
        _col(insp, "tenants", "source_company_id")
        return True
    except LookupError:
        return False        # 尚未套用是正常狀態


def _chk_usrdept(insp) -> bool:
    return "user_departments" in set(insp.get_table_names())


def _chk_compset(insp) -> bool:
    """競品分析 7 張表（compset_*）。

    ⚠️ 這支的證據**刻意不是「表在不在」**。2026-09-11 競品分析已隨五組營收模組
       獨立成新專案，Portal 端的 model 全部移除（見 project_split_revenue_suite），
       所以 compset_* 在現在的 Portal 可能因為三種完全不同的原因而不存在：
         (a) 這支 migration 從來沒跑過
         (b) 跑過，但之後用 docs/drop_split_module_tables.sql 刪掉了
         (c) 模組移除後 create_all() 本來就不會建它們
       單看資料庫分不出這三者。

       但真正重要的是：**這支對今日 Portal 的結構已經沒有任何影響**。
       Base.metadata 裡沒有 compset_*，所以 upgrade 過去不會建出 model 需要的
       任何東西，跳過它也不會缺任何東西。因此只要 model 端已經沒有 compset_*，
       就一律視為「已套用」，讓版本號能繼續往後推。

       若日後 compset 重新回到 Portal，下面的 fallback 會自動改回查表。
    """
    from app.core.database import Base
    model_has_compset = any(t.startswith("compset_") for t in Base.metadata.tables)
    if not model_has_compset:
        return True
    return "compset_subscribers" in set(insp.get_table_names())


def _chk_tcpurch(insp) -> bool:
    # 台中核准請購單／請款單 4 張表，挑第一張當代表
    return "taichung_purchase_requests" in set(insp.get_table_names())


def _chk_audchk(insp) -> bool:
    """稽核檢查 9 張表，挑交叉格（資料主體）當代表。

    ⚠️ 2026-09-21 測試區踩過：這 9 張表可能是 create_all() 先建出來的，
       形狀（欄位）**未必**與 migration 一致 —— create_all 補表不補欄位。
       這裡只負責判斷「這支有沒有套用過」，欄位層面的差異由下面的 _drift()
       負責抓（當時就是 drift 擋下來的，見 Temp/fix_audit_tables.py）。
    """
    return "audit_cells" in set(insp.get_table_names())


def _chk_cpragicurl(insp) -> bool:
    try:
        _col(insp, "cycle_purchase_summary", "ragic_record_url")
        return True
    except LookupError:
        return False


def _chk_cpragicdept(insp) -> bool:
    try:
        _col(insp, "cycle_purchase_departments", "ragic_dept")
        return True
    except LookupError:
        return False


def _chk_cpitemcat(insp) -> bool:
    try:
        _col(insp, "cycle_purchase_items", "category_id")
        return True
    except LookupError:
        return False


MAIN_CHAIN = [
    ("baseline_main", "建立全部資料表",                    _chk_baseline, []),
    ("widen7",        "4 張巡檢表 result_raw 放寬為 TEXT", _chk_widen7,   []),
    ("ctvnull",       "contracts.vendor_id 改為可 NULL",   _chk_ctvnull,  []),
    ("tncomp",        "tenants.source_company_id",         _chk_tncomp,
     [("tenants", "source_company_id")]),
    # ⚠️ 整張新表用 (table, None) 表示：_drift() 會把整張表列入排除，
    #    否則「Model 有整張表、DB 沒有」會被誤判成 drift 而擋下 stamp ——
    #    但那正是接下來 upgrade 要建的表，不是要修的 drift。
    ("usrdept",       "user_departments 關聯表",           _chk_usrdept,
     [("user_departments", None)]),
    ("compset",       "競品分析 7 張表（模組已移出 Portal）", _chk_compset, []),
    ("tcpurch",       "台中請購／請款 4 張表",             _chk_tcpurch,
     [("taichung_purchase_requests", None), ("taichung_purchase_request_items", None),
      ("taichung_claim_requests", None), ("taichung_claim_request_items", None)]),
    ("audchk",        "稽核檢查 9 張表",                   _chk_audchk,
     [("audit_result_types", None), ("audit_items", None), ("audit_periods", None),
      ("audit_sheets", None), ("audit_sheet_departments", None),
      ("audit_sheet_items", None), ("audit_item_targets", None),
      ("audit_cells", None), ("audit_reviews", None)]),
]

CP_CHAIN = [
    ("baseline_cp", "建立週採全部資料表",
     lambda insp: "cycle_purchase_departments" in set(insp.get_table_names()), []),
    ("cpragicurl",  "cycle_purchase_summary.ragic_record_url", _chk_cpragicurl,
     [("cycle_purchase_summary", "ragic_record_url")]),
    ("cpragicdept", "cycle_purchase_departments.ragic_dept",   _chk_cpragicdept,
     [("cycle_purchase_departments", "ragic_dept")]),
    ("cpitemcat",   "cycle_purchase_items.category_id",        _chk_cpitemcat,
     [("cycle_purchase_items", "category_id")]),
]


def _cmd_hint() -> str:
    exe = sys.executable or "python"
    return f'"{exe}"' if " " in exe else exe


def _current_version(eng) -> str | None:
    insp = inspect(eng)
    if "alembic_version" not in insp.get_table_names():
        return None
    with eng.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    return row[0] if row else None


def _check_chain_covers_versions(ini: str, chain: list) -> tuple[list[str], list[str]]:
    """檢查 versions/ 目錄裡的每一支 migration 都有登錄在 chain 裡。

    ⚠️ 2026-09-21 加上這道自檢。在此之前 MAIN_CHAIN 停在 usrdept、CP_CHAIN 只有
       baseline_cp，漏了後面好幾支，而腳本**完全不會察覺**——它只會安靜地推出一個
       偏舊的版本號。stamp 下去等於把版本號倒退，接著 upgrade head 重跑中間那幾支
       就撞 DuplicateTable。漏登錄是可以自動發現的，不該靠人記得。

    ini 檔名與 script_location 同名（alembic.ini → alembic/，
    alembic_cp.ini → alembic_cp/），沿用專案既有慣例。

    回傳 `(清單落差, 掃描失敗)`。兩者一定要分開報：「讀不到檔案」跟「清單過時」
    是完全不同的問題，混在同一個訊息裡會把人引去改 MAIN_CHAIN，而真正的原因
    在別處（2026-09-21 就是這樣：這裡誤用了沒 import 的 io.open，卻報成清單過時）。
    """
    vdir = os.path.join(BACKEND, ini[:-4] if ini.endswith(".ini") else ini, "versions")
    if not os.path.isdir(vdir):
        return [], [f"找不到 versions 目錄：{vdir}"]

    on_disk: dict[str, str] = {}
    errors: list[str] = []
    pat = re.compile(r"""^revision(?::\s*str)?\s*=\s*["']([^"']+)["']""", re.M)
    for fn in sorted(os.listdir(vdir)):
        if not fn.endswith(".py") or fn.startswith("__"):
            continue
        try:
            with open(os.path.join(vdir, fn), encoding="utf-8") as fh:
                text_ = fh.read()
        except Exception as exc:
            errors.append(f"{fn} 讀不到：{exc}")
            continue
        m = pat.search(text_)
        if m:
            on_disk[m.group(1)] = fn
        else:
            errors.append(f"{fn} 找不到 revision = 的宣告")
    if errors:
        return [], errors

    in_chain = {rev for rev, *_ in chain}
    problems = []
    for rev, fn in on_disk.items():
        if rev not in in_chain:
            problems.append(f"migration '{rev}'（{fn}）沒有登錄在本腳本的 chain 裡")
    for rev in in_chain:
        if rev not in on_disk:
            problems.append(f"chain 裡的 '{rev}' 在 versions/ 找不到對應檔案")
    return problems, []


def _check_ini_ascii(ini: str) -> list[str]:
    """.ini 必須純 ASCII —— Alembic 用 encoding="locale" 讀，Windows 繁中是
    cp950，一個中文字就會在 Alembic 啟動前拋 UnicodeDecodeError
    （2026-08-28 踩過，見 alembic_stamp_baseline.py 的同名函式）。"""
    path = os.path.join(BACKEND, ini)
    if not os.path.exists(path):
        return [f"{ini} 不存在"]
    with open(path, "rb") as f:
        raw = f.read()
    bad = []
    for lineno, line in enumerate(raw.split(b"\n"), start=1):
        try:
            line.decode("ascii")
        except UnicodeDecodeError:
            bad.append(f"{ini} 第 {lineno} 行含非 ASCII 字元")
    return bad


def _drift(base, eng, ignore: set[tuple[str, str]]) -> list[str]:
    """Model 有、DB 沒有的表／欄位；`ignore` 裡的不算（尚未套用的 migration 會補）。

    ignore 的元素兩種形式：(table, column) 排除單一欄位；(table, None) 排除整張表
    （待套用 migration 建立的新表）。
    """
    ignore_tables = {t for t, c in ignore if c is None}
    insp = inspect(eng)
    db_tables = set(insp.get_table_names())
    problems: list[str] = []
    for tname, table in base.metadata.tables.items():
        if tname not in db_tables:
            if tname not in ignore_tables:
                problems.append(f"缺少資料表 {tname}")
            continue
        db_cols = {c["name"] for c in insp.get_columns(tname)}
        for col in table.columns:
            if col.name not in db_cols and (tname, col.name) not in ignore:
                problems.append(f"缺少欄位 {tname}.{col.name}")
    return problems


def diagnose(label: str, ini: str, chain: list, base, eng, apply: bool) -> int:
    """回傳離開碼（0/1/2）。"""
    print()
    print("=" * 76)
    print(f"  {label}")
    print(f"  {eng.url}")
    print("=" * 76)

    enc = _check_ini_ascii(ini)
    if enc:
        print(f"❌ {ini} 編碼問題，Alembic 會在啟動前就失敗：")
        for e in enc:
            print(f"     · {e}")
        return 2

    gaps, scan_errors = _check_chain_covers_versions(ini, chain)
    if scan_errors:
        print(f"\n❌ 掃不完 {ini[:-4]}/versions/，無法確認 migration 清單，拒絕判斷：")
        for e in scan_errors:
            print(f"     · {e}")
        print("   → 這是**讀取／解析**的問題，不是 chain 過時，別去改 MAIN_CHAIN。")
        return 2
    if gaps:
        print("\n❌ 本腳本的 migration 清單與 versions/ 目錄對不起來，拒絕判斷：")
        for g in gaps:
            print(f"     · {g}")
        print("   → 請先在 alembic_stamp_current.py 的 MAIN_CHAIN／CP_CHAIN 補上")
        print("     對應項目（含證據檢查函式）。清單過時會讓這支推出偏舊的版本號，")
        print("     stamp 下去等於把版本號倒退。")
        return 2

    insp = inspect(eng)

    # ── ① 逐支查證據 ──────────────────────────────────────────────────────
    print("\n逐支檢查 migration 的實際證據（直接看資料庫，不問 alembic）：")
    applied: list[str] = []
    pending: list[str] = []
    pending_cols: set[tuple[str, str]] = set()
    seen_missing = False

    for rev, desc, fn, adds in chain:
        try:
            ok = fn(insp)
        except Exception as exc:
            print(f"  ✗ {rev:<14} {desc}")
            print(f"      查不出來：{exc}")
            print("      ⚠️ 「查不出來」不等於「沒問題」，中止。")
            return 2

        if ok:
            if seen_missing:
                # 前面某一支的證據不在、這一支卻在 → 鏈是斷的，不能用線性版本號描述
                print(f"  ⚠ {rev:<14} {desc} — 證據存在，但前面有支不存在")
                print("      ⚠️ 這個庫的結構無法用單一版本號如實描述，**不要**自行 stamp。")
                print("      請把整份輸出貼出來再處理。")
                return 2
            applied.append(rev)
            print(f"  ✓ {rev:<14} {desc}")
        else:
            seen_missing = True
            pending.append(rev)
            pending_cols.update(adds)
            print(f"  · {rev:<14} {desc} — 尚未套用")

    if not applied:
        print("\n❌ 連 baseline 的證據都不存在 —— 這看起來是個空庫。")
        print("   空庫請直接 `alembic upgrade head`，不要 stamp。")
        return 2

    target = applied[-1]

    # ── ② drift 檢查（排除待套用 migration 會補的欄位）────────────────────
    problems = _drift(base, eng, ignore=pending_cols)
    if problems:
        print(f"\n❌ 偵測到 {len(problems)} 項 schema drift（已排除待套用 migration 的欄位），拒絕 stamp：")
        for p in problems[:20]:
            print(f"     · {p}")
        print("   → 先修好 drift（見 check_schema_drift.py）再回來。")
        return 2
    if pending_cols:
        items = sorted(
            (f"{t}.{c}" if c is not None else f"{t}（整張表）") for t, c in pending_cols
        )
        print(f"\n✅ schema 與 Model 一致（已排除待套用的 {len(pending_cols)} 項："
              + "、".join(items) + "）")
    else:
        print("\n✅ schema 與 Model 完全一致")

    # ── ③ 決定並執行 stamp ────────────────────────────────────────────────
    cur = _current_version(eng)
    print(f"\nalembic_version 現況：{cur!r}")
    print(f"依證據推出的版本  ：{target!r}")
    if pending:
        print(f"stamp 後 upgrade head 會跑：{'、'.join(pending)}")
    else:
        print("stamp 後 upgrade head 不會有任何 migration 要跑（已是最新）")

    if cur == target:
        print("\n✅ 版本號已經正確，不需要 stamp。")
        return 0
    if cur is not None:
        print(f"\n⚠️  alembic_version 已存在且是 {cur}，與證據推出的 {target} 不符。")
        print("   → 這個環境的狀態跟預期不同，先不要動，把整份輸出貼出來。")
        return 2

    if not apply:
        print("\n" + "-" * 76)
        print("這是唯讀診斷，什麼都沒有改。確認以上內容後加 --apply 實際 stamp：")
        print(f"    {_cmd_hint()} scripts/alembic_stamp_current.py --apply")
        return 1

    print(f"\n執行：alembic -c {ini} stamp {target}")
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", ini, "stamp", target],
        cwd=BACKEND, capture_output=True, text=True,
    )
    if r.returncode != 0:
        print("❌ 失敗：")
        print((r.stdout + r.stderr)[-1500:])
        return 2

    after = _current_version(eng)
    if after != target:
        print(f"❌ 執行後版本是 {after!r}，與預期 {target!r} 不符")
        return 2
    print(f"✅ 完成，alembic_version = {after}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="把已是最新結構但缺 alembic_version 的資料庫 stamp 到正確版本（預設唯讀診斷）",
    )
    parser.add_argument("--apply", action="store_true", help="實際寫入版本號（預設只診斷）")
    args = parser.parse_args()

    # 讓 Base.metadata 收齊所有 model（drift 檢查需要）
    import importlib
    import pkgutil
    import app.models as pkg
    bad = []
    for m in pkgutil.iter_modules(pkg.__path__):
        try:
            importlib.import_module(f"app.models.{m.name}")
        except Exception as exc:
            bad.append(f"{m.name}: {exc}")
    if bad:
        print("❌ model import 失敗，中止：\n  " + "\n  ".join(bad))
        return 2

    from app.core.database import Base, engine
    from app.core.cycle_purchase_database import CyclePurchaseBase, cycle_purchase_engine
    engine.echo = False
    cycle_purchase_engine.echo = False

    print("Alembic stamp 診斷（只寫版本號，不建表、不改欄位、不動資料）")

    rc1 = diagnose("主庫 portal", "alembic.ini", MAIN_CHAIN, Base, engine, args.apply)
    rc2 = diagnose("週期採購 cycle_purchase", "alembic_cp.ini", CP_CHAIN,
                   CyclePurchaseBase, cycle_purchase_engine, args.apply)

    print()
    print("=" * 76)
    rc = max(rc1, rc2)
    if rc == 0:
        print("  ✅ 兩個庫的版本號都正確了。接著跑：")
        print("       cd backend")
        print(f"       {_cmd_hint()} -m alembic upgrade head")
        print("     （週採庫若有待跑的 migration：加 -c alembic_cp.ini）")
    elif rc == 1:
        print("  ⚠️  診斷完成，尚未寫入。確認上面的內容後加 --apply。")
    else:
        print("  ❌ 有項目需要處理，請看上面的訊息。**先不要跑 upgrade。**")
    print()
    return rc


if __name__ == "__main__":
    sys.exit(main())
