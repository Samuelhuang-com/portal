"""
三單比對（Phase 6）規則數字驗證 —— 唯讀，不寫任何資料（2026-11-17）

依 Samuel 2026-11-03 裁示「凡要對 Ragic 做數字統計，先出唯讀 Python、確認數字後才寫 Portal 程式」，
在把三單比對規則加進 purchase-report「資料異常稽核」（SPEC D22）之前，先用這支看各規則會抓出幾筆、抓得對不對。

資料來源：Portal 主庫已同步的 Ragic 資料（請購、Ragic採購單、請款），串接規則與「進貨匯入」相同：
  - 台中：請款「採購編號」去前綴取 9 碼對採購單；採購單「來源請購單號」對請購單
  - 樂群／日曜：請款「採購編號」含「採」字且有這張採購單才算連結；否則用內容比對（金額＋受款者＋說明＋品名，≥5 分）列「疑似」
  - 只看已核准（F）；Ragic「非採購需求」＝Yes 的請款單排除

候選規則：
  R09 請款對不到採購單（沒有連結、也沒有疑似）
  R10 請款金額超過採購單（同一張採購單底下所有請款單未稅金額加總 > 採購單未稅小計 + 1 元）
  R11 請購已核准超過 N 天還沒有採購單（只有台中能判斷：採購單有「來源請購單號」）
  R12 採購單超過 N 天還沒有請款單（放在稽核新增的「採購單」來源）

用法（在 backend 目錄）：
  python scripts/check_stock_three_way.py                 # 預設近 6 個月、逾期 30 天
  python scripts/check_stock_three_way.py --months 12 --days 45
輸出：畫面摘要＋ myDoc/three_way_check_<日期>/ 底下每條規則一個 CSV（可用 Excel 開），請挑幾筆到 Ragic 對看。
"""
import argparse
import csv
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal  # noqa: E402
from app.models.ragic_purchase_order import RagicPurchaseOrder, RagicPurchaseOrderItem  # noqa: E402
from app.models.taichung_purchase_request import TaichungPurchaseRequest  # noqa: E402
from app.services import stock_import_service as imp  # noqa: E402

RAGIC = "https://ap12.ragic.com/soutlet001"


def _amt(c) -> Decimal:
    """請款單未稅金額：subtotal；沒有就用 total ÷ 1.05。"""
    if c.subtotal is not None:
        return Decimal(str(c.subtotal))
    if c.total is not None:
        return (Decimal(str(c.total)) / Decimal("1.05")).quantize(Decimal("1"))
    return Decimal(0)


def run(months: int, days: int) -> None:
    today = date.today()
    since = today - timedelta(days=months * 31)
    overdue = today - timedelta(days=days)
    outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          "myDoc", f"three_way_check_{today.strftime('%Y%m%d')}")
    os.makedirs(outdir, exist_ok=True)
    db = SessionLocal()
    out = {k: [] for k in ("R09", "R10", "R11", "R12")}
    summary = []
    try:
        for code, company in imp.COMPANY_MAIN.items():
            hdr_model, item_model, fk = imp.CLAIM_MODELS[code]
            pos = [p for p in db.query(RagicPurchaseOrder).filter(RagicPurchaseOrder.company == company).all()
                   if not p.is_ragic_deleted]
            po_by_no = {p.po_no: p for p in pos if p.po_no}
            po_by_digits = defaultdict(list)
            for no in po_by_no:
                d = imp._digits(no)
                if imp.DATE_SERIAL_RE.match(d):
                    po_by_digits[d].append(no)
            items = defaultdict(list)
            for it in db.query(RagicPurchaseOrderItem).filter(RagicPurchaseOrderItem.order_id.in_([p.id for p in pos] or [0])).all():
                items[it.order_id].append(it)
            po_names = {p.id: {imp.normalize_name(i.product_name) for i in items[p.id]} for p in pos}

            claims = db.query(hdr_model).filter(hdr_model.company == company, hdr_model.status == "F").all()
            n_total = n_np = n_link = n_susp = n_none = 0
            claims_of_po = defaultdict(list)          # po_no → [(claim, 連結方式)]
            for c in claims:
                h = imp._claim_header(c, code)
                in_window = (c.approved_date or h["date"] or today) >= since
                link, how = None, ""
                raw = h["po_raw"]
                if raw:
                    if "採" in raw and raw in po_by_no:
                        link, how = raw, "連結"
                    elif code in ("HO", "OU") and imp.DATE_SERIAL_RE.match(imp._digits(raw)) and len(po_by_digits.get(imp._digits(raw), [])) == 1:
                        link, how = po_by_digits[imp._digits(raw)][0], "連結"
                if not link and not h["non_purchase"]:
                    rows = imp._claim_rows(c, h, item_model, fk, db)
                    s = imp._suspect_po(c, h, rows, pos, po_names)
                    if s:
                        link, how = s, "疑似"
                if link:
                    claims_of_po[link].append((c, how, h))
                if not in_window:
                    continue
                n_total += 1
                if h["non_purchase"]:
                    n_np += 1
                    continue
                if how == "連結":
                    n_link += 1
                elif how == "疑似":
                    n_susp += 1
                else:
                    n_none += 1
                    out["R09"].append({"公司": company, "請款單號": h["doc_no"], "部門": c.department_display,
                                       "核准日": c.approved_date, "受款者": c.payee, "未稅金額": _amt(c),
                                       "Ragic採購編號欄": raw, "說明": (c.purpose_description or "")[:60],
                                       "Ragic": f"{RAGIC}/{c.ragic_sheet_path}/{c.ragic_record_id}"})
            # R10 請款超過採購
            n_r10 = 0
            for no, lst in claims_of_po.items():
                p = po_by_no.get(no)
                if p is None or p.subtotal is None:
                    continue
                total = sum((_amt(c) for c, _, _ in lst), Decimal(0))
                if total > Decimal(str(p.subtotal)) + 1 and any((c.approved_date or today) >= since for c, _, _ in lst):
                    n_r10 += 1
                    out["R10"].append({"公司": company, "採購編號": no, "採購未稅小計": p.subtotal, "請款未稅合計": total,
                                       "超出": total - Decimal(str(p.subtotal)), "請款單": "、".join(h["doc_no"] for _, _, h in lst),
                                       "連結方式": "、".join(sorted({how for _, how, _ in lst})),
                                       "Ragic": f"{RAGIC}/{p.ragic_sheet_path}/{p.ragic_record_id}"})
            # R12 採購單逾期沒有請款
            n_r12 = 0
            for p in pos:
                d = p.apply_date or p.arrival_date
                if not d or d < since or d > overdue or p.po_no in claims_of_po:
                    continue
                n_r12 += 1
                out["R12"].append({"公司": company, "採購編號": p.po_no, "部門": p.department_display, "申請日": d,
                                   "擬定廠商": p.vendor_name, "未稅小計": p.subtotal, "說明": (p.purpose or "")[:60],
                                   "Ragic": f"{RAGIC}/{p.ragic_sheet_path}/{p.ragic_record_id}"})
            # R11 台中請購逾期沒有採購單
            n_r11 = None
            if code == "HO":
                linked_pr = {p.source_pr_no.strip() for p in pos if p.source_pr_no}
                n_r11 = 0
                for r in db.query(TaichungPurchaseRequest).filter(TaichungPurchaseRequest.status == "F").all():
                    d = r.approved_date or r.request_date
                    if not d or d < since or d > overdue or (r.purchase_no or "").strip() in linked_pr:
                        continue
                    n_r11 += 1
                    out["R11"].append({"公司": company, "請購單號": r.purchase_no, "部門": getattr(r, "department_display", ""),
                                       "核准日": r.approved_date, "Ragic": f"{RAGIC}/{r.ragic_sheet_path}/{r.ragic_record_id}"})
            summary.append((company, len(pos), n_total, n_np, n_link, n_susp, n_none, n_r10, n_r11, n_r12))
    finally:
        db.rollback()
        db.close()

    print(f"\n三單比對規則驗證（近 {months} 個月，逾期門檻 {days} 天，{today}）\n")
    print(f"{'公司':<4}{'採購單':>7}{'請款(期間)':>10}{'非採購需求':>10}{'連結':>6}{'疑似':>6}"
          f"{'R09對不到':>10}{'R10超額':>8}{'R11請購未採購':>13}{'R12採購未請款':>13}")
    for co, npo, nt, nnp, nl, ns, nn, r10, r11, r12 in summary:
        print(f"{co:<4}{npo:>8}{nt:>11}{nnp:>11}{nl:>7}{ns:>7}{nn:>11}{r10:>9}{('—' if r11 is None else r11):>14}{r12:>14}")
    for rule, rows in out.items():
        path = os.path.join(outdir, f"{rule}.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            if rows:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
            else:
                f.write("（沒有符合的資料）\n")
    print(f"\n明細 CSV：{outdir}")
    print("請各挑 5～10 筆到 Ragic 對看，確認「抓得對」再決定是否上線成稽核規則。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="三單比對規則數字驗證（唯讀）")
    ap.add_argument("--months", type=int, default=6, help="看近幾個月（預設 6）")
    ap.add_argument("--days", type=int, default=30, help="逾期門檻天數（預設 30）")
    a = ap.parse_args()
    run(a.months, a.days)
