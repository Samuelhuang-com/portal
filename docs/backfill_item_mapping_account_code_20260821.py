#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
週期採購 — 料號對照表「會計科目」回填腳本（2026-08-21）
==============================================================

依 2026-08-21 與 Samuel 確認的四點：

  1. 會計科目掛在 **cycle_purchase_item_mappings**（公司＋部門），不是料號主檔。
     因為《設料號明細表》的會科本來就填在「部門欄位」底下，且確實有跨部門
     不同科目的案例：`E0204002 公區照明-軌道燈` 工程部 621601 修繕費-維修／
     營業部 1142 用品盤存。
  2. 請購單移除會計科目欄，改由後端建立明細時自動從對照表帶入快照。
     `cycle_purchase_request_items.account_code_id` 欄位與付款分攤邏輯不變。
  3. 主檔（cycle_purchase_account_codes）查無附件裡的代碼時，**自動建立**。
  4. 比對鍵用 `cycle_purchase_item_mappings.original_code` ＋ `company='春大直'`
     （附件是純原始碼 E0101001，DB 的 items.item_code 已改成 `CH-` 前綴，
     見 models/cycle_purchase_item.py 2026-08-13）。

⚠️ 本腳本放在 docs/ 而不是 Temp/：正式區要靠 git pull 拿到它才跑得起來，
而 Temp/ 完全不進版控（CLAUDE.md §10 規則 4）。輸入來源
《20260716春大直設料號明細表-加代碼_20260818.xlsx》已在同目錄，
是 2026-08-18 align_chunda_items 那支腳本一併納入版控的同一份檔案。

────────────────────────────────────────────────────────────────
執行前提：後端必須先重啟過一次
────────────────────────────────────────────────────────────────
`account_code_id` 欄位由 `main.py` 的
`_migrate_cycle_purchase_item_mapping_account_code()` 在啟動時自動補上。
本腳本開頭會檢查欄位在不在，不在就直接中止並要你先重啟後端——沒有這一欄
時硬跑會噴 `no such column`，看起來像腳本壞了。

────────────────────────────────────────────────────────────────
使用方式
────────────────────────────────────────────────────────────────

  1) 盤點模式（預設，不寫入任何資料）：

       python backfill_item_mapping_account_code_20260821.py ^
           --excel-path "20260716春大直設料號明細表-加代碼_20260818.xlsx"

  2) 確認盤點報告沒問題後：

       python backfill_item_mapping_account_code_20260821.py ^
           --excel-path "20260716春大直設料號明細表-加代碼_20260818.xlsx" --execute

  預設 DB 路徑 C:\\portal_data\\cycle-purchase.db（同 backend/.env），
  要換用 --db-path。execute 模式會先備份（含 -wal/-shm）再動手，
  全程單一 transaction，任何一步失敗都 rollback。

  預設**只填空的**（account_code_id IS NULL）。已經有值但與附件不同的列會
  列在報告裡但不動；要一併覆蓋加 `--overwrite`。

────────────────────────────────────────────────────────────────
「一列多個部門會科」怎麼決定
────────────────────────────────────────────────────────────────
維修備品分頁有四組部門會科欄（管理部／客服停管部／營業部／工程部），
一列通常只填一組。但 2026-08-18 匯入時，該分頁的料號**一律掛在工程部**
（見 align_chunda_items_20260818.py 的 SHEET_SPEC），所以 DB 的部門
未必等於 Excel 上填會科的那個部門欄。取值規則：

  1. 對照表的部門名稱剛好等於某個 Excel 部門欄 → 用那一欄（E0204002 走這條，
     它的工程部欄是 621601，取 621601）
  2. 對不上，但整列只有一組會科 → 用那一組（絕大多數走這條）
  3. 對不上，且整列有多組會科 → **不猜、跳過並列進報告**由人工決定

規則 2 的語意是：會科代表「這個品項要記到哪個科目」，Excel 的部門欄只是
標示該筆支出算在誰頭上；Portal 對照表的部門則是「哪個部門的請購單看得到
這個料號」。兩者不是同一件事，所以部門對不上不代表會科用錯。
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("缺少 openpyxl，請先執行：pip install openpyxl", file=sys.stderr)
    sys.exit(1)


COMPANY = "春大直"
DEFAULT_DB = r"C:\portal_data\cycle-purchase.db"
TABLE = "cycle_purchase_item_mappings"
AC_TABLE = "cycle_purchase_account_codes"


def _norm(value) -> str:
    """Excel 欄位正規化。

    同一個會科代碼在不同分頁被存成不同型別：維修備品／文具分頁是數字
    （openpyxl 讀出來是 int 621601），清潔／營業分頁是字串 '6238'。
    數字欄位偶爾還會是 float（621601.0）。全部轉成去頭尾空白的字串，
    否則 '621601' 與 621601 會被當成兩個不同的科目各建一次。
    會科名稱也一樣要 strip——附件裡是 ' 修繕費-維修'，前面有一個空格。
    """
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value)).strip()
    return str(value).strip()


def parse_excel(path: Path) -> tuple[dict[str, dict[str, tuple[str, str]]], list[str]]:
    """回傳 (原始料號 → {Excel部門欄名: (會科代碼, 會科名稱)}, 警告清單)。"""
    wb = openpyxl.load_workbook(path, data_only=True)
    result: dict[str, dict[str, tuple[str, str]]] = {}
    warnings: list[str] = []

    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 3:
            continue
        header1, header2 = rows[0], rows[1]

        # 「料號」欄的位置＝部門會科區塊的右界。各分頁部門組數不同
        # （維修備品 4 組、其餘 1 組），所以不能寫死欄號。
        code_col = next(
            (i for i, v in enumerate(header1) if _norm(v) == "料號"),
            None,
        )
        if code_col is None:
            warnings.append(f"分頁「{ws.title}」找不到「料號」欄，整頁略過")
            continue

        # 部門欄名在第一列（合併儲存格 → 只有左邊那格有值），
        # 第二列是「會科代碼／會科」（營業分頁寫的是「會科代號」，兩種都吃）。
        dept_cols: list[tuple[int, str]] = []
        for i in range(0, code_col - 1, 2):
            name = _norm(header1[i]) or _norm(header1[i - 1] if i else "")
            sub = _norm(header2[i])
            if name and sub in ("會科代碼", "會科代號"):
                dept_cols.append((i, name))
        if not dept_cols:
            warnings.append(f"分頁「{ws.title}」找不到會科欄，整頁略過")
            continue

        for row in rows[2:]:
            item_code = _norm(row[code_col])
            if not item_code:
                continue
            pairs: dict[str, tuple[str, str]] = {}
            for i, dept_name in dept_cols:
                ac_code, ac_name = _norm(row[i]), _norm(row[i + 1])
                if ac_code:
                    pairs[dept_name] = (ac_code, ac_name or ac_code)
            if not pairs:
                warnings.append(f"料號 {item_code}（{ws.title}）整列沒有會科，略過")
                continue
            if item_code in result and result[item_code] != pairs:
                warnings.append(f"料號 {item_code} 在多個分頁出現且會科不一致，後者略過")
                continue
            result[item_code] = pairs

    return result, warnings


def pick_account_code(
    dept_name: str | None,
    pairs: dict[str, tuple[str, str]],
) -> tuple[tuple[str, str] | None, str]:
    """依檔頭「一列多個部門會科怎麼決定」的三條規則取值。回傳 (會科, 理由)。"""
    if dept_name and dept_name in pairs:
        return pairs[dept_name], f"部門欄相符（{dept_name}）"
    if len(pairs) == 1:
        only_dept, only_pair = next(iter(pairs.items()))
        return only_pair, f"整列只有一組會科（Excel 標在{only_dept}）"
    return None, f"整列有 {len(pairs)} 組會科（{'／'.join(pairs)}）且與部門「{dept_name or '未設定'}」都對不上"


def backup_db(db_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = db_path.with_name(f"{db_path.stem}.backup_{stamp}{db_path.suffix}")
    shutil.copy2(db_path, dest)
    # WAL 模式下 -wal/-shm 也要一起備份，只複製主檔還原後會少掉尚未 checkpoint
    # 的交易（與 align_chunda_items_20260818.py 同樣的處理）。
    for suffix in ("-wal", "-shm"):
        side = Path(str(db_path) + suffix)
        if side.exists():
            shutil.copy2(side, Path(str(dest) + suffix))
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description="週期採購 — 料號對照表會計科目回填（2026-08-21）")
    ap.add_argument("--excel-path", required=True, help="《設料號明細表》.xlsx 路徑")
    ap.add_argument("--db-path", default=DEFAULT_DB, help=f"cycle-purchase.db 路徑（預設 {DEFAULT_DB}）")
    ap.add_argument("--company", default=COMPANY, help=f"公司別（預設 {COMPANY}）")
    ap.add_argument("--execute", action="store_true", help="真的寫入（預設只盤點）")
    ap.add_argument("--overwrite", action="store_true", help="連同已有值但與附件不同的列一起覆蓋")
    args = ap.parse_args()

    excel_path, db_path = Path(args.excel_path), Path(args.db_path)
    if not excel_path.exists():
        print(f"✗ 找不到 Excel：{excel_path}", file=sys.stderr)
        return 1
    if not db_path.exists():
        print(f"✗ 找不到資料庫：{db_path}", file=sys.stderr)
        return 1

    excel_map, excel_warnings = parse_excel(excel_path)
    print(f"【Excel】{excel_path.name}：讀到 {len(excel_map)} 個料號的會科")
    for w in excel_warnings:
        print(f"  ⚠ {w}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({TABLE})")}
        if not cols:
            print(f"✗ 資料表 {TABLE} 不存在，確認 --db-path 指到 cycle-purchase.db", file=sys.stderr)
            return 1
        if "account_code_id" not in cols:
            print(
                f"✗ {TABLE} 還沒有 account_code_id 欄位。\n"
                f"  這一欄由後端啟動時的 _migrate_cycle_purchase_item_mapping_account_code() 自動補，\n"
                f"  請先**重啟後端服務**再跑本腳本。",
                file=sys.stderr,
            )
            return 1

        # ── 1. 會計科目主檔：對齊 Excel 出現過的所有代碼 ─────────────────────
        master = {r["code"]: r for r in conn.execute(f"SELECT id, code, name FROM {AC_TABLE}")}
        needed: dict[str, str] = {}
        for pairs in excel_map.values():
            for code, name in pairs.values():
                needed.setdefault(code, name)

        missing = {c: n for c, n in needed.items() if c not in master}
        renamed = [
            (c, master[c]["name"], n)
            for c, n in needed.items()
            if c in master and master[c]["name"] != n
        ]
        print(f"\n【會計科目主檔】附件用到 {len(needed)} 個代碼，主檔已有 {len(needed) - len(missing)} 個")
        for c, n in sorted(missing.items()):
            print(f"  ＋ 將新增：{c} {n}")
        for c, old, new in sorted(renamed):
            # 只提醒不改名：主檔名稱可能是協理正式清單的用字，附件是工作用簡稱。
            print(f"  ⚠ 名稱不同（不動主檔）：{c} 主檔「{old}」／附件「{new}」")

        # ── 2. 逐筆對照決定科目 ───────────────────────────────────────────────
        mappings = list(conn.execute(
            f"""
            SELECT m.id, m.item_id, m.original_code, m.account_code_id,
                   i.item_code, i.item_name, d.dept_name
            FROM {TABLE} m
            JOIN cycle_purchase_items i ON i.id = m.item_id
            LEFT JOIN cycle_purchase_departments d ON d.id = m.department_id
            WHERE m.company = ?
            ORDER BY i.item_code, d.dept_name
            """,
            (args.company,),
        ))
        print(f"\n【料號對照表】公司「{args.company}」共 {len(mappings)} 筆對照")

        to_fill: list[tuple[int, str]] = []   # (mapping_id, account_code)
        to_overwrite: list[tuple[int, str, str, str]] = []
        unchanged = 0
        no_excel: list[str] = []
        ambiguous: list[str] = []

        code_to_name = {r["code"]: r["name"] for r in master.values()}
        code_to_name.update(missing)

        for m in mappings:
            original = _norm(m["original_code"])
            pairs = excel_map.get(original)
            if not pairs:
                no_excel.append(f"{m['item_code']} {m['item_name']}（原始料號「{original or '空白'}」）")
                continue
            picked, reason = pick_account_code(m["dept_name"], pairs)
            if picked is None:
                ambiguous.append(f"{m['item_code']} {m['item_name']}／{m['dept_name'] or '未設定'}：{reason}")
                continue
            new_code = picked[0]
            current_id = m["account_code_id"]
            if current_id is None:
                to_fill.append((m["id"], new_code))
            else:
                current_code = next(
                    (r["code"] for r in master.values() if r["id"] == current_id), None
                )
                if current_code == new_code:
                    unchanged += 1
                else:
                    to_overwrite.append((
                        m["id"], new_code,
                        f"{m['item_code']} {m['item_name']}／{m['dept_name'] or '未設定'}",
                        f"{current_code or f'id={current_id}'} → {new_code}",
                    ))

        print(f"  ＋ 待填（目前空白）      ：{len(to_fill)} 筆")
        print(f"  ＝ 已相符不需動          ：{unchanged} 筆")
        print(f"  ! 已有值但與附件不同     ：{len(to_overwrite)} 筆"
              f"{'（--overwrite 會一併覆蓋）' if args.overwrite else '（不動；要改請加 --overwrite）'}")
        for _, _, label, change in to_overwrite:
            print(f"      {label}：{change}")
        print(f"  ? 附件查無此原始料號     ：{len(no_excel)} 筆")
        for line in no_excel:
            print(f"      {line}")
        print(f"  ? 多組會科無法判定       ：{len(ambiguous)} 筆")
        for line in ambiguous:
            print(f"      {line}")

        if not args.execute:
            print("\n（盤點模式，未寫入任何資料。確認無誤後加 --execute 再跑一次。）")
            return 0

        # ── 3. 寫入 ───────────────────────────────────────────────────────────
        backup = backup_db(db_path)
        print(f"\n【備份】{backup}")

        conn.execute("BEGIN")
        try:
            for code in sorted(missing):
                conn.execute(
                    f"INSERT INTO {AC_TABLE} (code, name, is_active) VALUES (?, ?, 1)",
                    (code, missing[code]),
                )
            code_to_id = {
                r["code"]: r["id"] for r in conn.execute(f"SELECT id, code FROM {AC_TABLE}")
            }

            targets = list(to_fill)
            if args.overwrite:
                targets += [(mid, code) for mid, code, _, _ in to_overwrite]
            for mapping_id, code in targets:
                conn.execute(
                    f"UPDATE {TABLE} SET account_code_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (code_to_id[code], mapping_id),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        print(f"✓ 已新增 {len(missing)} 個會計科目、回填 {len(targets)} 筆對照的科目。")
        print("  請重新整理「週期採購 → 料號主檔」頁面確認「會計科目」欄。")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
