# -*- coding: utf-8 -*-
"""
唯讀診斷：一張 Ragic 採購單為什麼沒進「進貨匯入」（/stock/receipts）待匯入清單（2026-11-17）

依資料流逐關檢查，第一個沒過的就是原因：
  ① Ragic 單筆 API：紀錄存在？子表有品項？
  ② Ragic 清單 API（同步實際用的）：這筆有沒有出現？清單版本有沒有帶子表？
  ③ 主庫 ragic_purchase_orders：同步進來了沒？品項幾筆？這張表最後同步時間？
  ④ 週採庫 stock_import_lines：待匯入清單有沒有這筆？狀態？清單最後重新整理時間？

只做 GET 與 SELECT，不寫任何資料。

用法（在 backend 資料夾）：
    python scripts/check_stock_po_record.py new-tab/11/13
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx  # noqa: E402
from sqlalchemy import func  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.cycle_purchase_database import CyclePurchaseSessionLocal, cycle_purchase_engine  # noqa: E402
from app.core.database import SessionLocal, engine  # noqa: E402
from app.models.module_sync_log import ModuleSyncLog  # noqa: E402
from app.models.ragic_sheet_config import RagicSheetConfig  # noqa: E402
from app.models.ragic_purchase_order import RagicPurchaseOrder, RagicPurchaseOrderItem  # noqa: E402
from app.models.stock import StockImportLine  # noqa: E402
from app.services.ragic_adapter import RagicAdapter  # noqa: E402
from app.services.ragic_po_sync import RAGIC_ACCOUNT, RAGIC_SERVER, _first, _subtable_rows  # noqa: E402

OK, NG = "✅", "❌"

# 關掉 SQL echo（DEV .env 可能開著，輸出會被 SQL 淹沒）
engine.echo = False
cycle_purchase_engine.echo = False
for _n in ("sqlalchemy.engine", "sqlalchemy.engine.Engine"):
    __import__("logging").getLogger(_n).setLevel(__import__("logging").WARNING)


def _overall(db) -> None:
    """③ 失敗時：分辨「整個 Ragic採購單 沒跑過」還是「跑了但讀不到採購單表單設定」。"""
    print("\n--- 整體檢查（判斷是沒跑過，還是跑了卻沒抓）---")
    rows = (db.query(RagicSheetConfig.module, RagicSheetConfig.display_name, RagicSheetConfig.list_path,
                     RagicSheetConfig.is_active)
            .filter(RagicSheetConfig.module.in_(("purchase_po", "nichiyo_po", "taichung_po")))
            .order_by(RagicSheetConfig.module, RagicSheetConfig.sort_order).all())
    active = [r for r in rows if r.is_active]
    mark = OK if active else NG
    print(f"{mark} ragic_sheet_config 採購單表單設定：{len(rows)} 筆（啟用 {len(active)}）"
          + ("" if active else " → 同步讀不到任何採購單表單，會「成功但 0 筆」。重啟一次後端即可寫入設定"))
    for r in rows:
        print(f"      {r.module:12s} {r.display_name:10s} {r.list_path:40s} {'啟用' if r.is_active else '停用'}")
    by_mod = (db.query(RagicPurchaseOrder.sheet_module, func.count(RagicPurchaseOrder.id),
                       func.max(RagicPurchaseOrder.sync_at))
              .group_by(RagicPurchaseOrder.sheet_module).all())
    total = sum(n for _, n, _ in by_mod)
    print(f"{OK if total else NG} ragic_purchase_orders 全部：{total} 張"
          + ("" if total else " → 「Ragic採購單」在這個資料庫從來沒有成功抓到資料"))
    for m, n, t in by_mod:
        print(f"      {m:12s} {n:5d} 張　最後同步 {t}")
    try:
        logs = (db.query(ModuleSyncLog).filter(ModuleSyncLog.module_name == "Ragic採購單")
                .order_by(ModuleSyncLog.started_at.desc()).limit(5).all())
        print(f"    module_sync_log「Ragic採購單」最近 {len(logs)} 次（sync_tool 不一定會寫這張表，僅供參考）：")
        for g in logs:
            print(f"      {g.started_at}　{g.status}　fetched {g.fetched}　upserted {g.upserted}　{(g.error_msg or '')[:120]}")
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"    （讀 module_sync_log 失敗：{exc}）")


def _params() -> dict:
    return {"api": "", "version": settings.RAGIC_API_VERSION, "naming": settings.RAGIC_NAMING}


def _summary(data: dict) -> None:
    print(f"    採購編號：{_first(data, '採購編號', '採購單號', '編號') or '（空白）'}")
    print(f"    申請日期：{_first(data, '申請日期') or '（空白）'}　到貨日期：{_first(data, '到貨日期') or '（空白）'}")
    print(f"    擬定廠商：{_first(data, '擬定廠商', '25擬定廠商名稱') or '（空白）'}")
    sub_keys = [k for k in data if k.startswith("_subtable_")]
    rows = _subtable_rows(data)
    print(f"    子表欄位：{sub_keys or '（沒有任何 _subtable_ 欄位）'}　品項列數：{len(rows)}")
    for r in rows[:10]:
        print(f"      - {_first(r, '產品名稱', '品名', '品項名稱') or '（無品名）'}　數量 {_first(r, '數量') or '—'}　"
              f"{_first(r, '單位')}　_ragicId={r.get('_ragicId')}")


async def main(sheet: str, rid: str) -> None:
    print(f"\n=== 檢查 {sheet}/{rid} ===\n")

    # ① 單筆 API
    url = f"https://{RAGIC_SERVER}/{RAGIC_ACCOUNT}/{sheet}/{rid}"
    async with httpx.AsyncClient(timeout=60, verify=settings.RAGIC_VERIFY_SSL) as c:
        r = await c.get(url, params=_params(), headers={"Authorization": f"Basic {settings.RAGIC_API_KEY}"})
    r.raise_for_status()
    body = r.json()
    one = body.get(rid) if isinstance(body, dict) and rid in body else body
    if not isinstance(one, dict) or not one:
        print(f"{NG} ① Ragic 單筆 API 讀不到這筆（可能已刪除或沒有權限）")
        return
    print(f"{OK} ① Ragic 單筆 API 有這筆")
    _summary(one)

    # ② 清單 API（同步用的就是這個）
    records = await RagicAdapter(sheet_path=sheet, server_url=RAGIC_SERVER, account=RAGIC_ACCOUNT).fetch_all()
    lst = records.get(rid)
    if lst is None:
        print(f"\n{NG} ② 清單 API 共 {len(records)} 筆，**沒有**這筆 → 同步永遠抓不到"
              "（常見原因：清單 API 預設篩選／這筆被隱藏、或 API 帳號看不到）")
    else:
        n = len(_subtable_rows(lst))
        mark = OK if n else NG
        print(f"\n{mark} ② 清單 API 共 {len(records)} 筆，有這筆；清單版本的品項列數 {n}"
              + ("" if n else " → 清單 API 沒帶子表，同步進來會是 0 個品項"))

    # ③ 主庫
    db = SessionLocal()
    try:
        last_sync = db.query(func.max(RagicPurchaseOrder.sync_at)).filter(RagicPurchaseOrder.ragic_sheet_path == sheet).scalar()
        cnt = db.query(func.count(RagicPurchaseOrder.id)).filter(RagicPurchaseOrder.ragic_sheet_path == sheet).scalar()
        print(f"\n    主庫這張表：{cnt} 張採購單，最後同步 {last_sync or '（從未同步）'}")
        po = (db.query(RagicPurchaseOrder)
              .filter(RagicPurchaseOrder.ragic_sheet_path == sheet, RagicPurchaseOrder.ragic_record_id == rid).first())
        if not po:
            print(f"{NG} ③ 主庫 ragic_purchase_orders 沒有這筆 → 需要在 sync_tool 執行「Ragic採購單」同步")
            _overall(db)
            return
        items = db.query(RagicPurchaseOrderItem).filter(RagicPurchaseOrderItem.order_id == po.id).count()
        mark = OK if items and not po.is_ragic_deleted else NG
        print(f"{mark} ③ 主庫有這筆：公司 {po.company}、部門 {po.department_display}、採購編號 {po.po_no or '（空白）'}、"
              f"品項 {items} 筆、同步於 {po.sync_at}、已刪除標記 {po.is_ragic_deleted}")
        company = po.company
    finally:
        db.close()

    # ④ 週採庫：待匯入清單
    code = {"樂群": "CH", "日曜": "OU", "台中": "HO"}.get(company)
    cp = CyclePurchaseSessionLocal()
    try:
        refreshed = (cp.query(func.max(StockImportLine.refreshed_at))
                     .filter(StockImportLine.company_code == code).scalar())
        print(f"\n    待匯入清單（{company}）最後重新整理：{refreshed or '（從未）'}")
        lines = (cp.query(StockImportLine)
                 .filter(StockImportLine.source_type == "ragic_po", StockImportLine.ragic_sheet_path == sheet,
                         StockImportLine.ragic_record_id == rid).all())
        if not lines:
            print(f"{NG} ④ 待匯入清單沒有這筆 → 請在「進貨匯入」按「從 Ragic 資料重新整理」"
                  f"（主庫同步於 {po.sync_at}，清單最後重新整理於 {refreshed or '從未'}）")
            return
        print(f"{OK} ④ 待匯入清單有 {len(lines)} 列：")
        for l in lines:
            print(f"      - {l.product_name}　狀態 {l.status}　{l.status_reason or ''}")
        print("    → 資料都在。若畫面上看不到，請確認公司別下拉、狀態篩選（例如在「不入庫」分頁）、或日期區間。")
    finally:
        cp.close()


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1].strip("/").count("/") < 2:
        print("用法：python scripts/check_stock_po_record.py new-tab/11/13")
        sys.exit(1)
    parts = sys.argv[1].strip("/").split("?")[0].split("/")
    asyncio.run(main("/".join(parts[:-1]), parts[-1]))
