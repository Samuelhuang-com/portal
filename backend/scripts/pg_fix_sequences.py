"""
修復 PostgreSQL 遷移遺漏的 sequence 起始值

問題是什麼
────────────────────────────────────────────────────────────────────────────
從 SQLite 搬資料進 PG 時，id 是**明確帶值**寫進去的（INSERT ... (id, ...)）。
這種寫法**不會**推進該欄位的 sequence —— sequence 只有在 `nextval()` 被呼叫
（也就是 INSERT 沒指定 id）時才會前進。

於是搬完之後：
    表裡已經有 id = 1..12345
    sequence 卻還停在 1

下一次程式正常 INSERT（不帶 id）就會拿到 1，撞上既有列：

    duplicate key value violates unique constraint "xxx_pkey"
    DETAIL:  Key (id)=(3) already exists.

⚠️⚠️ **這不是某一張表的問題，是所有搬過來的表的共通問題。**
   2026-08-30 由 `ota_sync_logs` first 爆出來，純粹是因為它每次同步都寫一列
   log，最先把前幾個 id 用完。其他表只是還沒被寫到 —— 尤其那些「只讀不寫」
   或「一個月才新增一筆」的表，可能要等好幾週才會炸，而且是炸在使用者面前。

   `pg_migrate_pilot.py` / `pg_cutover.py` 從頭到尾沒有任何一處 `setval`，
   這一步從來沒做過。

做了什麼
────────────────────────────────────────────────────────────────────────────
掃描兩個資料庫（主庫 + 週期採購）public schema 下所有 BASE TABLE 的
identity / serial 欄位，對每一個：

    ① 找出它的 sequence（`pg_get_serial_sequence`）
    ② 問 sequence 下一次會發出什麼號碼
    ③ 問資料表該欄位目前的 MAX()
    ④ 下一個號碼 <= MAX ＝ 有風險，會撞

修復方式是 `setval(seq, MAX(col) + 1, false)` —— 下一次 nextval 直接回
MAX+1。空表則設成下一次回 1。

⚠️ **預設是唯讀的 dry-run**，只印報告不改東西。確認報告內容後才加 `--apply`。

⚠️ **執行前請先停掉會寫入的程式**（後端服務、sync_tool.py）。
   setval 與並行 INSERT 之間沒有鎖，一邊改一邊寫等於白改。

執行：
    cd backend

    # 測試區（本機，Python 來自 C:\\anaconda3，沒有 py launcher 的 3.11）
    python scripts\\pg_fix_sequences.py                # 只看報告（唯讀）
    python scripts\\pg_fix_sequences.py --apply        # 實際修正

    # 正式區（D:\\portal / C:\\portal）
    py -3.11 scripts\\pg_fix_sequences.py
    py -3.11 scripts\\pg_fix_sequences.py --apply

⚠️ 兩區的直譯器不一樣，指令不能互抄：測試區跑 `py -3.11` 會得到
   "No suitable Python runtime found"；正式區跑 `python` 則可能抓到別的環境。
   不確定時先 `python -c "import sys; print(sys.executable)"` 確認，
   套件裝 A 版程式跑 B 版是這個專案踩過的坑。

離開碼：
    0 = 全部檢查成功且沒有問題，或已成功修正
    1 = 偵測到有風險的 sequence 但沒有 --apply（提醒你要修）
    2 = 執行過程出錯，**或有任何欄位沒有檢查成功**

⚠️⚠️ 最後一項是刻意的：「一個都沒查成功」與「查過都沒問題」在數字上
   都是 at_risk == 0，意義卻完全相反。只要有一欄檢查失敗就不回報綠燈，
   離開碼一律非 0 —— 檢查工具最危險的失效方式是回報「沒問題」，
   而不是報錯。
"""
from __future__ import annotations

import argparse
import os
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

from sqlalchemy import text                                       # noqa: E402


def _cmd_hint() -> str:
    """回傳「用**目前這個**直譯器」的指令字串。

    ⚠️ 不要寫死 `python` 或 `py -3.11` —— 測試區是 anaconda 的 python、
       正式區是 py -3.11，寫死一定有一區的人照抄會失敗
       （測試區抄 py -3.11 會得到 No suitable Python runtime found）。
       直接回報使用者剛剛實際用來跑這支腳本的那一個。
    """
    exe = sys.executable or "python"
    return f'"{exe}"' if " " in exe else exe


# 找出 public schema 下所有 BASE TABLE 的 identity / serial 欄位。
#
# ⚠️ 兩種寫法都要涵蓋：
#     · is_identity = 'YES'          → GENERATED ... AS IDENTITY（PG 10+ 標準寫法）
#     · column_default LIKE 'nextval(%' → SERIAL / BIGSERIAL（舊寫法）
#   SQLAlchemy 建表時用哪一種取決於版本與方言設定，只查一種會漏。
#
# ⚠️ 限定 table_type='BASE TABLE'：VIEW 不會有 sequence，查了只是白噴錯。
_SQL_COLUMNS = """
SELECT c.table_name,
       c.column_name,
       pg_get_serial_sequence(
           quote_ident(c.table_schema) || '.' || quote_ident(c.table_name),
           c.column_name
       ) AS seq_name
  FROM information_schema.columns c
  JOIN information_schema.tables t
    ON t.table_schema = c.table_schema
   AND t.table_name   = c.table_name
 WHERE c.table_schema = 'public'
   AND t.table_type   = 'BASE TABLE'
   AND (c.is_identity = 'YES' OR c.column_default LIKE 'nextval(%')
 ORDER BY c.table_name, c.column_name
"""


def _next_value(conn, seq_name: str) -> int:
    """問 sequence「下一次 nextval 會發出什麼號碼」。

    ⚠️ 直接讀 sequence relation 本身（`SELECT last_value, is_called FROM 該序列`）。
       **不要用 `pg_sequences` view —— 它沒有 `is_called` 欄位**，只有
       last_value／start_value／increment_by 等。2026-08-30 初版就是誤用它，
       第一欄就 UndefinedColumn。

    ⚠️ last_value 要配 is_called 一起看：
        is_called = true  → 這個號碼已經發出去了，下一個是 last_value + 1
        is_called = false → 還沒發過，下一個就是 last_value 本身
                            （剛建立、或被 setval(..., false) 設定過）
       只看 last_value 會差一號。

    ⚠️ 也不能用 nextval() 去試 —— 那會真的消耗一個號碼，唯讀模式就不唯讀了。
    """
    # seq_name 來自 pg_get_serial_sequence，已是安全的 quoted 識別字
    row = conn.execute(text(
        f"SELECT last_value, is_called FROM {seq_name}"
    )).first()
    if row is None:
        raise RuntimeError(f"讀不到 sequence：{seq_name}")
    last_value, is_called = row[0], row[1]
    if last_value is None:
        return 1
    return int(last_value) + 1 if is_called else int(last_value)


def scan(engine, label: str, apply: bool) -> tuple[int, int, int, int]:
    """回傳 (成功檢查數, 有風險數, 已修正數, 檢查失敗數)。"""
    print("=" * 78)
    print(f"  {label}")
    print(f"  連線目標：{engine.url}")
    print("=" * 78)

    if engine.dialect.name != "postgresql":
        print(f"  ⏭  這個庫是 {engine.dialect.name}，不是 PostgreSQL —— 沒有 sequence，跳過。\n")
        return (0, 0, 0, 0)

    ok_count = at_risk = fixed = failed = 0
    rows: list[tuple] = []

    # ⚠️⚠️ 必須用 AUTOCOMMIT。在一般 transaction 裡只要有**一句** SQL 失敗，
    #      PG 會把整個 transaction 標成 aborted，後面每一句都回
    #      "current transaction is aborted" —— 一欄查不到就會連鎖成全部查不到，
    #      而那看起來像「檢查過了」。AUTOCOMMIT 下每句各自獨立，互不影響。
    #      （2026-08-30 初版就是踩這個，105 欄連鎖失敗還回報「全部正常」。）
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        cols = conn.execute(text(_SQL_COLUMNS)).fetchall()
        print(f"  找到 {len(cols)} 個 identity / serial 欄位\n")

        for table_name, column_name, seq_name in cols:
            if not seq_name:
                # identity 欄位理論上一定有 sequence；查不到就是有別的問題，
                # 明確印出來而不是靜默跳過（「查不出來」≠「查過沒問題」）。
                print(f"  ❌ {table_name}.{column_name} 找不到對應 sequence —— 請人工確認")
                failed += 1
                continue

            try:
                nxt = _next_value(conn, seq_name)
                # 表名／欄名一律加雙引號：本專案雖然全是小寫底線命名，
                # 但沒加引號的識別字碰到保留字或大小寫混合就會炸。
                max_id = conn.execute(text(
                    f'SELECT COALESCE(MAX("{column_name}"), 0) FROM "{table_name}"'
                )).scalar_one()
            except Exception as exc:
                # 每一欄各自 try/except，一欄壞掉不影響其他欄，且獨立計入 failed。
                # ⚠️ 絕不能把失敗當成「沒問題」——那是最危險的一種綠燈。
                failed += 1
                print(f"  ❌ {table_name}.{column_name} 檢查失敗："
                      f"{type(exc).__name__}: {str(exc).splitlines()[0][:70]}")
                continue

            ok_count += 1
            risky = nxt <= int(max_id)
            if risky:
                at_risk += 1
            rows.append((table_name, column_name, seq_name, nxt, int(max_id), risky))

        # ── 報告 ──────────────────────────────────────────────────────────
        print()
        # ⚠️ 欄寬 14 不是 10：部分表的 id 到 2 千萬級（Ragic 帶過來的原始 id），
        #    10 格放不下，兩個數字會黏成一團看不出斷點。
        print(f"  {'表 . 欄位':<40}{'下一號':>14}{'MAX':>16}   狀態")
        print("  " + "-" * 76)
        shown = 0
        for table_name, column_name, _seq, nxt, max_id, risky in rows:
            ident = f"{table_name}.{column_name}"
            if risky or max_id > 0:
                print(f"  {ident:<40}{nxt:>14,}{max_id:>16,}   "
                      f"{'❌ 會撞' if risky else '✅'}")
                shown += 1
        if shown == 0:
            print("  （沒有任何有資料的表，全部是空表）")

        print()
        print(f"  檢查成功 {ok_count} 個　有風險 {at_risk} 個　檢查失敗 {failed} 個")
        if failed:
            print(f"  ⚠️ 有 {failed} 個欄位**沒有檢查成功**——這不代表它們沒問題，"
                  f"代表不知道。請先排除上面的錯誤。")
        print()

        if at_risk == 0:
            if failed == 0:
                print(f"  ✅ {ok_count} 個 sequence 全部正常，沒有會撞的。\n")
            return (ok_count, 0, 0, failed)

        print(f"  ❌ {at_risk} 個 sequence 落後於資料，下次 INSERT 會 duplicate key。\n")

        if not apply:
            print("  ⚠️ 這是唯讀的 dry-run，沒有改任何東西。")
            print("     確認上面清單無誤後，加 --apply 實際修正。\n")
            return (ok_count, at_risk, 0, failed)

        # ── 修正（同一條 AUTOCOMMIT 連線，每句各自生效）────────────────
        print("  開始修正…\n")
        for table_name, column_name, seq_name, nxt, max_id, risky in rows:
            if not risky:
                continue
            try:
                # setval(seq, MAX+1, false) → 下一次 nextval 直接回 MAX+1。
                # 第三個參數 false 代表「這個號碼還沒發出去」，所以不會跳號。
                new_val = int(max_id) + 1
                conn.execute(text("SELECT setval(:seq, :val, false)"),
                             {"seq": seq_name, "val": new_val})
                fixed += 1
                print(f"  ✅ {table_name}.{column_name:<28} {nxt:,} → {new_val:,}")
            except Exception as exc:
                print(f"  ❌ {table_name}.{column_name} 修正失敗："
                      f"{type(exc).__name__}: {str(exc).splitlines()[0][:70]}")

    print(f"\n  已修正 {fixed} / {at_risk} 個。\n")
    return (ok_count, at_risk, fixed, failed)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="修復 PG 遷移遺漏的 sequence 起始值（預設唯讀 dry-run）")
    ap.add_argument("--apply", action="store_true",
                    help="實際執行 setval（不加就只印報告，不改任何東西）")
    args = ap.parse_args()

    print()
    print("=" * 78)
    print("  PostgreSQL sequence 對齊檢查" + ("（--apply：會修改資料庫）" if args.apply
                                              else "（dry-run：唯讀）"))
    print("=" * 78)
    if args.apply:
        print("  ⚠️ 執行前請確認後端服務與 sync_tool.py 都已停止。")
        print("     setval 與並行 INSERT 之間沒有鎖，一邊改一邊寫等於白改。")
    print()

    try:
        from app.core.database import engine
        from app.core.cycle_purchase_database import cycle_purchase_engine
        engine.echo = cycle_purchase_engine.echo = False
    except Exception as exc:
        print(f"  ❌ 無法建立資料庫連線：{type(exc).__name__}: {exc}")
        return 2

    total_ok = total_risk = total_fixed = total_failed = 0
    for eng, label in ((engine, "主庫（app.core.database.engine）"),
                       (cycle_purchase_engine, "週期採購（cycle_purchase_engine）")):
        try:
            c, r, f, bad = scan(eng, label, args.apply)
        except Exception as exc:
            print(f"  ❌ {label} 掃描失敗：{type(exc).__name__}: {exc}\n")
            return 2
        total_ok += c
        total_risk += r
        total_fixed += f
        total_failed += bad

    print("=" * 78)
    print(f"  合計：檢查成功 {total_ok} 個　有風險 {total_risk} 個　"
          f"已修正 {total_fixed} 個　檢查失敗 {total_failed} 個")
    print("=" * 78)

    # ⚠️⚠️ 檢查失敗優先於「沒有風險」。
    #      「一個都沒查成功」與「查過都沒問題」在數字上都是 at_risk == 0，
    #      但意義完全相反。回報綠燈之前必須先確認真的查成功了。
    if total_failed:
        print(f"  ❌ 有 {total_failed} 個欄位沒有檢查成功 —— **無法斷定資料庫沒問題**。")
        print("     請先排除上面的錯誤訊息，再重跑一次。\n")
        return 2

    if total_risk == 0:
        print(f"  ✅ {total_ok} 個 sequence 全部檢查成功且正常。\n")
        return 0
    if not args.apply:
        print("  ⚠️ 尚未修正。確認報告後，**先停掉後端服務與 sync_tool.py**，再執行：")
        print(f"       {_cmd_hint()} scripts\\pg_fix_sequences.py --apply\n")
        return 1
    if total_fixed == total_risk:
        print("  ✅ 已全部修正。建議再跑一次 dry-run 確認：")
        print(f"       {_cmd_hint()} scripts\\pg_fix_sequences.py\n")
        return 0
    print(f"  ❌ 有 {total_risk - total_fixed} 個沒修成功，請看上面的錯誤訊息。\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
