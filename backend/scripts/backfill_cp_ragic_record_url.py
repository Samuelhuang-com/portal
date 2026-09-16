"""
回補週採彙整列的 `ragic_record_url`（讓已拋轉的單號可以點開 Ragic）

背景（2026-09-16）
────────────────────────────────────────────────────────────────────────────
2026-09-15 完成 Ragic 正式串接時，先推了幾張單（樂管週採00003／00004／00005），
**之後**才加上 `cycle_purchase_summary.ragic_record_url` 這個欄位
（alembic_cp revision `cpragicurl`）。所以那幾張單的網址是 NULL，畫面上只顯示
單號、不能點。本腳本把它們補起來。

⚠️ 為什麼不能用算的
   Ragic 單筆網址要的是**內部 `_ragicId`**（`.../57/2`），而我們存的
   `ragic_record_id` 是**給人看的採購編號**（`樂管週採00003`）。兩者沒有任何
   可推導的關係 —— 目前這張表剛好「編號減 1 等於內部 id」，純粹是因為還沒刪過
   任何一筆記錄；只要有人在 Ragic 刪掉一張，之後全部對不起來。
   所以一定要**跟 Ragic 要一份對照表**，不能自己算。

做法
   1. 打 `GET <sheet>?api&v=3`（唯讀）拿回整張表
   2. 建立「採購編號 → _ragicId」對照
   3. 逐列比對並回填 `ragic_record_url`

⚠️ 不會碰的列
   · `ragic_pushed = false`（沒推過，本來就不該有網址）
   · `ragic_record_url` 已經有值（不覆蓋，冪等）
   · `ragic_record_id` 是 `STUB-*`（2026-09-15 之前的假資料，Ragic 上沒有對應
     單據，補不了也不該補）
   · 在 Ragic 上找不到對應採購編號的（會列出來讓你判斷，可能是 Ragic 端被刪了）

⚠️ 預設唯讀，要實際寫入必須加 `--fix`。

執行：
    cd backend
    py -3.12 scripts\\backfill_cp_ragic_record_url.py          # 只看不改
    py -3.12 scripts\\backfill_cp_ragic_record_url.py --fix    # 實際回填
"""
from __future__ import annotations

import logging
import os
import sys

# ⚠️ 輸出強制 UTF-8：導向檔案時 Python 會改用 cp950，中文與 emoji 編不進去會整支中斷。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

import httpx                                                      # noqa: E402
from sqlalchemy import text                                       # noqa: E402


def main() -> int:
    do_fix = "--fix" in sys.argv

    from app.core.config import settings
    from app.core.cycle_purchase_database import cycle_purchase_engine as engine
    engine.echo = False

    sheet_url = (
        f"https://{settings.RAGIC_CP_SUMMARY_SERVER_URL}"
        f"/{settings.RAGIC_CP_SUMMARY_ACCOUNT}"
        f"/{settings.RAGIC_CP_SUMMARY_PATH}"
    )
    doc_no_fid = settings.RAGIC_CP_F_DOC_NO

    print("=" * 78)
    print("  週採：回補 ragic_record_url（已拋轉單號 → Ragic 單筆網址）")
    print("=" * 78)
    print(f"  DB    : {engine.url}")
    print(f"  Ragic : {sheet_url}")
    print(f"  模式  : {'實際寫入 (--fix)' if do_fix else '唯讀預覽（要寫入請加 --fix）'}\n")

    # ── 1. 找出需要回補的列 ────────────────────────────────────────────────
    sql_need = text(
        "SELECT id, ragic_record_id, ragic_push_batch_no, company, period_label "
        "FROM cycle_purchase_summary "
        "WHERE ragic_pushed = TRUE "
        "  AND ragic_record_url IS NULL "
        "  AND ragic_record_id IS NOT NULL "
        "  AND ragic_record_id NOT LIKE 'STUB-%' "
        "ORDER BY ragic_record_id, id"
    )
    with engine.connect() as c:
        need = c.execute(sql_need).all()
        n_stub = c.execute(text(
            "SELECT COUNT(*) FROM cycle_purchase_summary "
            "WHERE ragic_pushed = TRUE AND ragic_record_id LIKE 'STUB-%'"
        )).scalar_one()
        n_done = c.execute(text(
            "SELECT COUNT(*) FROM cycle_purchase_summary "
            "WHERE ragic_pushed = TRUE AND ragic_record_url IS NOT NULL"
        )).scalar_one()

    print(f"  需要回補 : {len(need)} 列")
    print(f"  已有網址 : {n_done} 列（跳過，不覆蓋）")
    print(f"  stub 假料: {n_stub} 列（跳過，Ragic 上沒有對應單據）\n")
    if not need:
        print("  ✅ 沒有需要回補的列。\n")
        return 0

    # ── 2. 跟 Ragic 要「採購編號 → 內部 id」對照表 ─────────────────────────
    if not settings.RAGIC_API_KEY:
        print("  ❌ RAGIC_API_KEY 是空的，無法查詢 Ragic。中止。\n")
        return 1

    print("  → 讀取 Ragic 表單…")
    try:
        resp = httpx.get(
            sheet_url,
            headers={"Authorization": f"Basic {settings.RAGIC_API_KEY}"},
            params={"api": "", "v": "3"},
            timeout=settings.RAGIC_CP_SUMMARY_TIMEOUT,
            verify=settings.RAGIC_VERIFY_SSL,
        )
        resp.raise_for_status()
        raw = resp.json()
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ 讀取 Ragic 失敗：{exc}\n")
        return 1

    if not isinstance(raw, dict):
        print(f"  ❌ Ragic 回傳格式不是預期的物件：{str(raw)[:200]}\n")
        return 1

    # key 是內部 _ragicId（字串），值裡面的 doc_no_fid 是採購編號。
    # ⚠️ 用 `rec.get("_ragicId", key)` 而不是只信 key —— 兩者理論上相同，
    #    但真正拿來組網址的是 _ragicId，以它為準比較保險。
    no2id: dict[str, str] = {}
    for key, rec in raw.items():
        if not isinstance(rec, dict):
            continue
        doc_no = str(rec.get(doc_no_fid) or rec.get("採購編號") or "").strip()
        if not doc_no:
            continue
        rid = rec.get("_ragicId")
        no2id[doc_no] = str(key if rid is None else rid)

    print(f"  → Ragic 上共 {len(no2id)} 張單\n")

    # ── 3. 比對並回填 ──────────────────────────────────────────────────────
    updates: list[tuple[int, str]] = []
    missing: list[tuple[int, str]] = []
    for row_id, doc_no, batch, company, period in need:
        rid = no2id.get(str(doc_no).strip())
        if rid is None:
            missing.append((row_id, doc_no))
            continue
        updates.append((row_id, f"{sheet_url}/{rid}"))

    by_doc: dict[str, int] = {}
    for row_id, doc_no, *_ in need:
        by_doc[doc_no] = by_doc.get(doc_no, 0) + 1
    print("  對照結果（依採購編號）：")
    for doc_no, cnt in sorted(by_doc.items()):
        rid = no2id.get(doc_no.strip())
        mark = f"→ {sheet_url}/{rid}" if rid is not None else "→ ⚠️ Ragic 上找不到"
        print(f"    {doc_no}  {cnt} 列  {mark}")
    print()

    if missing:
        print(f"  ⚠️ {len(missing)} 列在 Ragic 上找不到對應採購編號，**不會**被回補：")
        for row_id, doc_no in missing:
            print(f"     summary_id={row_id}  {doc_no}")
        print("     可能是那張單在 Ragic 端被刪了；請自行確認要不要「取消拋轉」重推。\n")

    if not do_fix:
        print(f"  ℹ️ 唯讀模式，未寫入。加 --fix 會回填 {len(updates)} 列。\n")
        return 0

    with engine.begin() as c:
        for row_id, url in updates:
            c.execute(
                text("UPDATE cycle_purchase_summary SET ragic_record_url = :u WHERE id = :i"),
                {"u": url, "i": row_id},
            )
    print(f"  ✅ 已回填 {len(updates)} 列。\n")

    with engine.connect() as c:
        left = c.execute(sql_need).all()
    print(f"  驗證：仍需回補 {len(left)} 列"
          f"{'（都是 Ragic 上找不到的那幾列）' if left else '，全部完成'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
