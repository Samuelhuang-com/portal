"""
庫存管理 Phase 3：進貨匯入服務 — docs/SPEC_stock_management.md §6（2026-11-17）

流程：Ragic 已同步的採購單／請款單（主庫，只讀）→ refresh_candidates() 產生待匯入清單（週採庫快照）
      → 人工確認（料號、實收量、單位換算、入庫倉）→ confirm_receipt() 產生進貨單並過帳
      → void_receipt() 作廢（反向異動、回補可匯入量）

串接規則（SPEC §4.4、§5.1，Phase 0 實測）：
  - 請款單「採購編號」含「採」字且等於某張採購單編號 → 已對應採購單（linked_po，不進待匯入，D15）
  - 台中／日曜：9 碼日期流水號（YYYYMMNNN）等於採購單編號的數字部分 → 已對應
  - 樂群 5 碼數字是請款單自身流水號，不當連結
  - 其他請款單用內容比對找「疑似同一筆採購」（強＝金額＋受款者／說明…≥5 分），匯入前須確認（§6.5）
"""
import hashlib
import json
import re
import unicodedata
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.claim_request import ApprovedClaimRequest, ApprovedClaimRequestItem
from app.models.cycle_purchase_item import CyclePurchaseItem
from app.models.nichiyo_claim_request import NichiyoClaimRequest, NichiyoClaimRequestItem
from app.models.ragic_purchase_order import RagicPurchaseOrder, RagicPurchaseOrderItem
from app.models.stock import (
    StockImportLine, StockItemAlias, StockItemSetting, StockMove, StockReceipt, StockReceiptItem, StockWarehouse,
)
from app.models.taichung_claim_request import TaichungClaimRequest, TaichungClaimRequestItem
from app.services.stock_service import StockError, post_move

RAGIC_BASE = "https://ap12.ragic.com/soutlet001"
COMPANY_MAIN = {"CH": "樂群", "OU": "日曜", "HO": "台中"}       # 週採公司代碼 → 主庫同步表 company 字串
CLAIM_MODELS = {
    "CH": (ApprovedClaimRequest, ApprovedClaimRequestItem, "claim_id"),
    "OU": (NichiyoClaimRequest, NichiyoClaimRequestItem, "order_id"),
    "HO": (TaichungClaimRequest, TaichungClaimRequestItem, "claim_id"),
}
DATE_SERIAL_RE = re.compile(r"^\d{9}$")          # 台中／日曜採購單去前綴後的 YYYYMMNNN
OPEN_STATUSES = ("pending", "partial")
Q4 = Decimal("0.0001")


# ── 小工具 ────────────────────────────────────────────────────────────────────

def _s(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return ",".join(_s(x) for x in v)
    return str(v).strip()


def _num(v: Any) -> Optional[Decimal]:
    t = re.sub(r"[^\d.\-]", "", _s(v))
    if not t or t in ("-", ".", "-."):
        return None
    try:
        return Decimal(t)
    except InvalidOperation:
        return None


def _first(d: dict, *keys: str) -> str:
    for k in keys:
        v = _s(d.get(k))
        if v:
            return v
    return ""


def normalize_name(name: Optional[str]) -> str:
    t = unicodedata.normalize("NFKC", name or "").lower()
    return re.sub(r"[\s\-_/\\,.;:、，。；：()（）\[\]【】{}<>《》\"'“”‘’*#+~]", "", t)[:300]


def _digits(v: Optional[str]) -> str:
    m = re.findall(r"\d+", v or "")
    return m[-1] if m else ""


def _vendor_norm(v: Optional[str]) -> str:
    return re.sub(r"[\s()（）]|有限公司|股份有限公司|公司", "", unicodedata.normalize("NFKC", v or ""))


def _sim(a: Optional[str], b: Optional[str]) -> float:
    a, b = normalize_name(a), normalize_name(b)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def _hash(*parts: Any) -> str:
    return hashlib.sha256(json.dumps([_s(p) for p in parts], ensure_ascii=False).encode()).hexdigest()


def ragic_url(line: StockImportLine) -> str:
    return f"{RAGIC_BASE}/{line.ragic_sheet_path}/{line.ragic_record_id}"


def recompute_status(line: StockImportLine) -> None:
    if line.status not in OPEN_STATUSES + ("done",):
        return
    imp = Decimal(str(line.imported_qty or 0))
    if line.qty is not None and imp >= Decimal(str(line.qty)) and imp > 0:
        line.status = "done"
    elif imp > 0:
        line.status = "partial"
    else:
        line.status = "pending"


# ── 來源解析 ──────────────────────────────────────────────────────────────────

def _claim_header(c, code: str) -> dict:
    raw = {}
    try:
        raw = json.loads(c.raw_data_json or "{}")
    except Exception:
        pass
    if code == "OU":
        doc_no, d, po_raw = c.claim_no, c.request_date, _s(raw.get("採購編號"))
    else:
        doc_no, d, po_raw = c.request_no, c.apply_date, _s(c.purchase_no) or _s(raw.get("採購編號"))
    return {"doc_no": doc_no, "date": d, "po_raw": po_raw, "raw": raw,
            "non_purchase": _s(raw.get("非採購需求")) == "Yes",
            "tax_included": _s(raw.get("項目金額為(含稅)")) == "Yes"}


def _claim_rows(c, h: dict, item_model, fk: str, db: Session) -> list[dict]:
    """優先用 raw_data_json 的子表（有穩定的 _ragicId）；沒有才退回 Portal 品項表（seq）。"""
    out = []
    for k, v in (h["raw"] or {}).items():
        if not (k.startswith("_subtable_") and isinstance(v, dict)):
            continue
        for rid, row in v.items():
            if not isinstance(row, dict):
                continue
            name = _first(row, "產品名稱", "品名", "品項名稱", "名稱", "項目", "品項")
            untaxed = _num(_first(row, "擬定廠商金額(未稅)", "金額(未稅)"))
            amt = untaxed
            if amt is None:
                amt = _num(_first(row, "擬定廠商金額", "金額", "請款金額", "小計"))
                if amt is not None and h["tax_included"]:
                    amt = (amt / Decimal("1.05")).quantize(Decimal("0.01"), ROUND_HALF_UP)
            out.append({"row_id": _s(row.get("_ragicId")) or _s(rid), "name": name,
                        "qty_raw": _s(row.get("數量")), "unit": _first(row, "單位"),
                        "price": _num(_first(row, "單價(未稅)", "擬定廠商單價", "單價")), "amount": amt})
    if out:
        return out
    for it in db.query(item_model).filter(getattr(item_model, fk) == c.id).order_by(item_model.seq).all():
        if item_model is NichiyoClaimRequestItem:
            out.append({"row_id": f"seq{it.seq}", "name": it.product_name, "qty_raw": _s(it.qty), "unit": it.unit,
                        "price": _num(it.unit_price), "amount": _num(it.amount)})
        else:
            out.append({"row_id": f"seq{it.seq}", "name": it.item_name, "qty_raw": _s(it.quantity), "unit": it.unit,
                        "price": None, "amount": _num(it.proposed_vendor_amount)})
    return out


def _unit_price(price: Optional[Decimal], amount: Optional[Decimal], qty: Optional[Decimal]) -> Optional[Decimal]:
    if price is not None:
        return price
    if amount is not None and qty:
        return (amount / qty).quantize(Q4, ROUND_HALF_UP)
    return None


# ── 產生／更新待匯入清單 ─────────────────────────────────────────────────────

def refresh_candidates(main: Session, cp: Session, code: str) -> dict:
    company = COMPANY_MAIN.get(code)
    if not company:
        raise StockError(f"不支援的公司：{code}")
    now = twnow()
    aliases_ns = {a.normalized_name for a in cp.query(StockItemAlias)
                  .filter(StockItemAlias.company_code == code, StockItemAlias.is_non_stock.is_(True)).all()}

    # 1) 採購單
    pos = main.query(RagicPurchaseOrder).filter(RagicPurchaseOrder.company == company).all()
    po_by_no = {p.po_no: p for p in pos if p.po_no and not p.is_ragic_deleted}
    po_by_digits: dict[str, list[str]] = {}
    for no in po_by_no:
        d = _digits(no)
        if DATE_SERIAL_RE.match(d):
            po_by_digits.setdefault(d, []).append(no)
    items_by_po: dict[int, list] = {}
    for it in main.query(RagicPurchaseOrderItem).filter(RagicPurchaseOrderItem.order_id.in_([p.id for p in pos] or [0])).all():
        items_by_po.setdefault(it.order_id, []).append(it)

    snap: dict[tuple, dict] = {}
    missing_reason: dict[tuple, str] = {}
    for p in pos:
        for it in items_by_po.get(p.id, []):
            key = ("ragic_po", p.ragic_sheet_path, p.ragic_record_id, it.ragic_row_id)
            if p.is_ragic_deleted:
                missing_reason[key] = "deleted"
                continue
            qty = it.qty
            snap[key] = dict(
                source_db_id=p.id, doc_no=p.po_no, po_no=p.po_no, suspected_po_no=None, department=p.department_display,
                doc_date=p.apply_date or p.arrival_date, vendor_name=p.vendor_name, item_code=it.item_code,
                product_name=it.product_name, qty=qty, qty_raw=it.qty_raw, unit=it.unit,
                unit_price=_unit_price(it.unit_price, it.amount, qty), amount=it.amount,
                _linked=None, _non_purchase=False)

    # 2) 請款單（只取已核准 F）
    hdr_model, item_model, fk = CLAIM_MODELS[code]
    po_headers = [p for p in pos if not p.is_ragic_deleted]
    po_names = {p.id: {normalize_name(i.product_name) for i in items_by_po.get(p.id, [])} for p in po_headers}
    for c in main.query(hdr_model).filter(hdr_model.company == company).all():
        h = _claim_header(c, code)
        rows = _claim_rows(c, h, item_model, fk, main)
        keys = [("ragic_claim", c.ragic_sheet_path, c.ragic_record_id, r["row_id"]) for r in rows]
        if c.status != "F":
            for k in keys:
                missing_reason[k] = "rejected" if c.status == "REJ" else "deleted"
            continue
        linked = None
        raw_po = h["po_raw"]
        if raw_po:
            if "採" in raw_po and raw_po in po_by_no:
                linked = raw_po
            elif code in ("HO", "OU") and DATE_SERIAL_RE.match(_digits(raw_po)) and len(po_by_digits.get(_digits(raw_po), [])) == 1:
                linked = po_by_digits[_digits(raw_po)][0]
        suspect = None
        if not linked:
            suspect = _suspect_po(c, h, rows, po_headers, po_names)
        for r, key in zip(rows, keys):
            if not r["name"] and r["amount"] in (None, 0):
                continue
            qty = _num(r["qty_raw"])
            snap[key] = dict(
                source_db_id=c.id, doc_no=h["doc_no"], po_no=linked, suspected_po_no=suspect,
                department=c.department_display, doc_date=h["date"], vendor_name=c.payee, item_code=None,
                product_name=r["name"], qty=qty, qty_raw=r["qty_raw"][:50] or None, unit=(r["unit"] or "")[:50] or None,
                unit_price=_unit_price(r["price"], r["amount"], qty), amount=r["amount"],
                _linked=linked, _non_purchase=h["non_purchase"])

    # 3) 寫入（upsert）
    existing = {(l.source_type, l.ragic_sheet_path, l.ragic_record_id, l.ragic_row_id): l
                for l in cp.query(StockImportLine).filter(StockImportLine.company_code == code).all()}
    stats = {"inserted": 0, "updated": 0, "changed_after_import": 0, "missing": 0, "total_source_lines": len(snap)}
    for key, f in snap.items():
        linked, non_purchase = f.pop("_linked"), f.pop("_non_purchase")
        hsh = _hash(f["doc_no"], f["product_name"], f["qty_raw"], f["unit"], f["unit_price"], f["amount"], f["vendor_name"], f["po_no"])
        line = existing.get(key)
        if line is None:
            line = StockImportLine(company_code=code, source_type=key[0], ragic_sheet_path=key[1], ragic_record_id=key[2],
                                   ragic_row_id=key[3], source_hash=hsh, imported_qty=0, refreshed_at=now, **f)
            if linked:
                line.status, line.status_reason = "linked_po", f"已對應採購單 {linked}（以採購單入庫，D15）"
            elif non_purchase:
                line.status, line.status_reason = "non_stock", "Ragic「非採購需求」＝Yes"
            elif normalize_name(f["product_name"]) in aliases_ns:
                line.status, line.status_reason = "non_stock", "品名對照：不入庫"
            else:
                line.status = "pending"
            cp.add(line)
            stats["inserted"] += 1
            continue
        line.refreshed_at = now
        imported = Decimal(str(line.imported_qty or 0)) > 0
        if line.source_hash != hsh:
            for k, v in f.items():
                setattr(line, k, v)
            line.source_hash = hsh
            stats["updated"] += 1
            if imported:
                line.source_changed, line.source_status = True, "changed"
                stats["changed_after_import"] += 1
        if line.source_status in ("deleted", "rejected") and not imported:
            line.source_status = "ok"
        if not imported and line.status in ("pending", "linked_po"):
            if linked:
                line.status, line.status_reason = "linked_po", f"已對應採購單 {linked}（以採購單入庫，D15）"
            elif line.status == "linked_po":
                line.status, line.status_reason = "pending", None
        if not imported:
            recompute_status(line)
    for key, line in existing.items():
        if key in snap:
            continue
        reason = missing_reason.get(key, "deleted")
        if line.source_status != reason:
            line.source_status = reason
            if Decimal(str(line.imported_qty or 0)) > 0:
                line.source_changed = True
            stats["missing"] += 1
    cp.flush()
    return stats


def _suspect_po(c, h: dict, rows: list[dict], po_headers: list, po_names: dict) -> Optional[str]:
    """樂群／日曜等沒有可靠串接欄位的請款單：內容比對找「強」的疑似採購單（Phase 0 規則，台中驗證準確率約 97%）。"""
    cd = h["date"]
    amts = {a for a in (_num(c.subtotal), _num(c.total)) if a is not None}
    payee = _vendor_norm(c.payee)
    names = {normalize_name(r["name"]) for r in rows if r["name"]}
    best, best_score = None, 0
    for p in po_headers:
        pd = p.apply_date or p.arrival_date
        if cd and pd and not (0 <= (cd - pd).days <= 180):
            continue
        sc = 0
        if amts & {a for a in (p.subtotal, p.total) if a is not None}:
            sc += 3
        if payee and _vendor_norm(p.vendor_name) == payee:
            sc += 2
        if sc == 0:
            continue
        if _sim(c.purpose_description, p.purpose) >= 0.6:
            sc += 2
        if names & po_names.get(p.id, set()):
            sc += 1
        if sc > best_score:
            best, best_score = p.po_no, sc
    return best if best_score >= 5 else None


# ── 料號建議 ──────────────────────────────────────────────────────────────────

def suggest_items(cp: Session, code: str, line: StockImportLine, limit: int = 5) -> list[dict]:
    items = (cp.query(CyclePurchaseItem, StockItemSetting)
             .outerjoin(StockItemSetting, StockItemSetting.item_id == CyclePurchaseItem.id)
             .filter(CyclePurchaseItem.company_code == code, CyclePurchaseItem.is_active.is_(True)).all())
    items = [(i, s) for i, s in items if s is None or s.is_stock_item]
    out: list[dict] = []
    seen = set()

    def add(i, s, score, why):
        if i.id in seen:
            return
        seen.add(i.id)
        out.append({"item_id": i.id, "item_code": i.item_code, "item_name": i.item_name, "spec": i.spec, "unit": i.unit,
                    "unit_price": float(i.unit_price) if i.unit_price is not None else None,
                    "purchase_unit": s.purchase_unit if s else None, "unit_ratio": float(s.unit_ratio) if s else 1.0,
                    "score": round(score, 3), "reason": why})

    by_id = {i.id: (i, s) for i, s in items}
    if line.item_code:
        for i, s in items:
            if i.item_code == line.item_code:
                add(i, s, 1.0, "Ragic 料號相同")
    norm = normalize_name(line.product_name)
    alias = cp.query(StockItemAlias).filter(StockItemAlias.company_code == code, StockItemAlias.normalized_name == norm).first()
    if alias and alias.item_id in by_id:
        add(*by_id[alias.item_id], 1.0, f"品名對照（已確認 {alias.hit_count} 次）")
    scored = sorted(((SequenceMatcher(None, norm, normalize_name(i.item_name)).ratio(), i, s) for i, s in items),
                    key=lambda x: -x[0])
    for sc, i, s in scored:
        if len(out) >= limit:
            break
        if sc >= 0.3:
            add(i, s, sc, "品名相似")
    return out


# ── 確認入庫／作廢 ────────────────────────────────────────────────────────────

def _next_no(cp: Session, prefix: str) -> str:
    last = (cp.query(StockReceipt.receipt_no).filter(StockReceipt.receipt_no.like(prefix + "%"))
            .order_by(StockReceipt.receipt_no.desc()).first())
    return f"{prefix}{(int(last[0][-3:]) + 1) if last else 1:03d}"


def _po_already_imported_by_claim(cp: Session, code: str, po_no: str) -> Optional[str]:
    """採購單匯入前：同一筆採購是否已由請款單入庫。
    已對應（po_no 相同）的請款單一律算；「疑似」的請款單只有在入庫時沒填理由（未確認是不同批貨）才算。"""
    base = cp.query(StockImportLine.id, StockImportLine.doc_no).filter(
        StockImportLine.company_code == code, StockImportLine.source_type == "ragic_claim", StockImportLine.imported_qty > 0)
    hit = base.filter(StockImportLine.po_no == po_no).first()
    if hit:
        return hit[1]
    for lid, doc_no in base.filter(StockImportLine.suspected_po_no == po_no).all():
        confirmed_diff = cp.query(StockReceiptItem.id).join(StockReceipt, StockReceipt.id == StockReceiptItem.receipt_id).filter(
            StockReceiptItem.import_line_id == lid, StockReceipt.status == "posted",
            StockReceiptItem.override_reason.isnot(None)).first()
        if not confirmed_diff:
            return doc_no
    return None


def _claim_suspect_imported(cp: Session, code: str, po_no: str) -> bool:
    return cp.query(StockImportLine.id).filter(StockImportLine.company_code == code, StockImportLine.source_type == "ragic_po",
                                               StockImportLine.po_no == po_no, StockImportLine.imported_qty > 0).first() is not None


def confirm_receipt(cp: Session, *, code: str, warehouse: StockWarehouse, receipt_date: date, note: Optional[str],
                    lines: list[dict], user_name: str) -> StockReceipt:
    """lines：[{import_line_id, item_id, purchase_qty, unit_ratio, unit_price(採購單位未稅, 可 None), override_reason,
                remember_alias(bool), remember_ratio(bool)}]"""
    if not lines:
        raise StockError("至少要有一筆品項")
    if warehouse.company_code != code:
        raise StockError("倉庫不屬於這家公司")
    ids = [l["import_line_id"] for l in lines]
    if len(set(ids)) != len(ids):
        raise StockError("同一張進貨單不可重複選同一筆待匯入品項")
    src = {l.id: l for l in cp.query(StockImportLine).filter(StockImportLine.id.in_(ids)).with_for_update().all()}
    items = {i.id: i for i in cp.query(CyclePurchaseItem).filter(CyclePurchaseItem.id.in_([l["item_id"] for l in lines])).all()}
    settings = {s.item_id: s for s in cp.query(StockItemSetting).filter(StockItemSetting.item_id.in_(list(items) or [0])).all()}
    receipt = StockReceipt(receipt_no=_next_no(cp, f"RCV-{code}-{receipt_date.strftime('%Y%m')}-"), company_code=code,
                           warehouse_id=warehouse.id, receipt_date=receipt_date, status="posted", note=note,
                           created_by=user_name, line_count=len(lines), total_amount=0)
    cp.add(receipt)
    cp.flush()
    total = Decimal(0)
    for l in lines:
        line = src.get(l["import_line_id"])
        if not line or line.company_code != code:
            raise StockError(f"找不到待匯入品項 id={l['import_line_id']}")
        label = f"{line.doc_no or ''} {line.product_name or ''}".strip()
        if line.status not in OPEN_STATUSES:
            raise StockError(f"「{label}」狀態為 {line.status}，不能入庫")
        if line.source_status != "ok":
            raise StockError(f"「{label}」Ragic 來源已異動／退回／刪除，請先處理")
        it = items.get(l["item_id"])
        if not it or it.company_code != code or not it.is_active:
            raise StockError(f"「{label}」選的料號不存在或已停用")
        st = settings.get(it.id)
        if st is not None and not st.is_stock_item:
            raise StockError(f"料號 {it.item_code} 設定為不納入庫存")
        pq = Decimal(str(l["purchase_qty"]))
        ratio = Decimal(str(l.get("unit_ratio") or 1))
        if pq <= 0 or ratio <= 0:
            raise StockError(f"「{label}」數量與換算比例必須大於 0")
        if line.qty is not None:
            remain = Decimal(str(line.qty)) - Decimal(str(line.imported_qty or 0))
            if pq > remain:
                raise StockError(f"「{label}」實收 {pq.normalize():f} 超過剩餘可匯入量 {remain.normalize():f}")
        # 防重複入庫（§6.5）
        if line.source_type == "ragic_po":
            dup = _po_already_imported_by_claim(cp, code, line.po_no)
            if dup:
                raise StockError(f"採購單 {line.po_no} 已由請款單 {dup} 入庫，不能再用採購單匯入")
        elif line.suspected_po_no and _claim_suspect_imported(cp, code, line.suspected_po_no):
            if not (l.get("override_reason") or "").strip():
                raise StockError(f"「{label}」疑似已由採購單 {line.suspected_po_no} 入庫；確認不是同一批貨請填寫理由")
        price = l.get("unit_price")
        estimated = False
        if price is None:
            price = line.unit_price
        if price is None:
            if it.unit_price is None:
                raise StockError(f"「{label}」沒有單價，請輸入")
            unit_cost, estimated = Decimal(str(it.unit_price)), True
        else:
            unit_cost = (Decimal(str(price)) / ratio).quantize(Q4, ROUND_HALF_UP)
        stock_qty = (pq * ratio).quantize(Q4, ROUND_HALF_UP)
        m = post_move(cp, warehouse=warehouse, item=it, qty=stock_qty, unit_cost=unit_cost, move_type="receipt",
                      source_type="receipt", source_id=receipt.id, source_no=receipt.receipt_no, moved_at=receipt_date,
                      note=f"{line.doc_no or ''} {line.product_name or ''}".strip()[:200], user_name=user_name)
        cp.add(StockReceiptItem(receipt_id=receipt.id, import_line_id=line.id, item_id=it.id, purchase_qty=pq,
                                purchase_unit=line.unit, unit_ratio=ratio, stock_qty=stock_qty, unit_cost=unit_cost,
                                amount=m.amount, is_estimated_cost=estimated,
                                override_reason=(l.get("override_reason") or "").strip() or None))
        total += Decimal(str(m.amount))
        line.imported_qty = Decimal(str(line.imported_qty or 0)) + pq
        if line.qty is None:
            line.status = "done"      # 數量無法解析的列，一次確認即視為完成
        else:
            recompute_status(line)
        if l.get("remember_alias", True) and line.product_name:
            _remember_alias(cp, code, line.product_name, it.id, user_name)
        if l.get("remember_ratio") and line.unit and ratio != 1:
            if st is None:
                st = StockItemSetting(item_id=it.id, is_stock_item=True)
                cp.add(st)
                settings[it.id] = st
            st.purchase_unit, st.unit_ratio, st.updated_by = line.unit[:20], ratio, user_name
    receipt.total_amount = total
    return receipt


def _remember_alias(cp: Session, code: str, raw_name: str, item_id: Optional[int], user: str, non_stock: bool = False) -> None:
    norm = normalize_name(raw_name)
    if not norm:
        return
    a = cp.query(StockItemAlias).filter(StockItemAlias.company_code == code, StockItemAlias.normalized_name == norm).first()
    if a is None:
        cp.add(StockItemAlias(company_code=code, normalized_name=norm, raw_name=raw_name, item_id=item_id,
                              is_non_stock=non_stock, confirmed_by=user, confirmed_at=twnow(), hit_count=1))
    else:
        a.item_id, a.is_non_stock, a.confirmed_by, a.confirmed_at = item_id, non_stock, user, twnow()
        a.hit_count = (a.hit_count or 0) + 1


def void_receipt(cp: Session, *, receipt: StockReceipt, warehouse: StockWarehouse, reason: str, user_name: str) -> None:
    if receipt.status != "posted":
        raise StockError("這張進貨單已作廢")
    ris = cp.query(StockReceiptItem).filter(StockReceiptItem.receipt_id == receipt.id).all()
    items = {i.id: i for i in cp.query(CyclePurchaseItem).filter(CyclePurchaseItem.id.in_([r.item_id for r in ris] or [0])).all()}
    lines = {l.id: l for l in cp.query(StockImportLine).filter(StockImportLine.id.in_([r.import_line_id for r in ris] or [0]))
             .with_for_update().all()}
    for r in ris:
        post_move(cp, warehouse=warehouse, item=items[r.item_id], qty=-Decimal(str(r.stock_qty)), move_type="receipt_void",
                  source_type="receipt", source_id=receipt.id, source_no=receipt.receipt_no, moved_at=receipt.receipt_date,
                  note=f"作廢：{reason}"[:200], user_name=user_name)
        line = lines.get(r.import_line_id)
        if line:
            line.imported_qty = max(Decimal(0), Decimal(str(line.imported_qty or 0)) - Decimal(str(r.purchase_qty)))
            if line.status == "done" and line.qty is None:
                line.status = "pending"
            recompute_status(line)
    receipt.status, receipt.voided_by, receipt.voided_at, receipt.void_reason = "voided", user_name, twnow(), reason


# ── 標記 ──────────────────────────────────────────────────────────────────────

def mark_lines(cp: Session, *, code: str, line_ids: list[int], status: str, reason: Optional[str], user_name: str,
               remember_non_stock: bool = False) -> dict:
    if status not in ("non_stock", "pre_opening", "pending"):
        raise StockError("不支援的狀態")
    done, skipped = 0, []
    for l in cp.query(StockImportLine).filter(StockImportLine.company_code == code, StockImportLine.id.in_(line_ids)).all():
        if Decimal(str(l.imported_qty or 0)) > 0 or l.status in ("done", "linked_po"):
            skipped.append(l.doc_no or str(l.id))
            continue
        l.status, l.status_reason, l.marked_by = status, (reason or None) if status != "pending" else None, user_name
        if status == "non_stock" and remember_non_stock and l.product_name:
            _remember_alias(cp, code, l.product_name, None, user_name, non_stock=True)
        done += 1
    return {"updated": done, "skipped": skipped}


def mark_before(cp: Session, *, code: str, before: date, user_name: str) -> int:
    """D19：開帳前的舊單據整批標「開帳前，不入庫」（只動待確認、未匯入的列）。"""
    q = cp.query(StockImportLine).filter(StockImportLine.company_code == code, StockImportLine.status == "pending",
                                         StockImportLine.imported_qty == 0, StockImportLine.doc_date < before)
    n = 0
    for l in q.all():
        l.status, l.status_reason, l.marked_by = "pre_opening", f"開帳前（{before.isoformat()} 之前）不入庫", user_name
        n += 1
    return n
