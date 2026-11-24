#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
週期採購 — 台中（HO／智選）料號匯入：《20261123維春台中料號明細表(第二版)-FOR 金協理.xlsx》
================================================================================

做什麼
------
把 Excel 匯入「週期採購 → 料號主檔」（公司代碼 HO＝台中／智選），一次建立：
  1. 類別主檔（cycle_purchase_categories）   依 Excel〈編碼原則〉，缺的才建
  2. 會計科目（cycle_purchase_account_codes） 依 Excel 科目編號／科目名稱，缺的才建
  3. 料號（cycle_purchase_items）             item_code 一律加 HO- 前綴
  4. 料號對照（cycle_purchase_item_mappings） 每個料號 × 每個部門一筆，帶廠商、單價、會計科目

安全設計
--------
- 預設只「檢核＋預覽」，不寫入任何資料。確認報告無誤後加 --apply，並輸入 YES（或加 --yes）。
- 單一 transaction，任何一步失敗全部 rollback。
- 廠商：先比對台中既有廠商；對不到的，從 Ragic 台中廠商表（info/19）補建為本地廠商（代碼 HOV-NNNN，
  source_vendor_id 為 NULL）。Excel 廠商仍對不到的會擋下，列出清單。
- 已存在的料號（item_code 相同，或對照原始料號相同）預設完全不動；--update-existing 才更新。
- 品名、單位、類別不覆蓋既有資料。
- 單價空白的料號照常匯入（unit_price 為 NULL），報告會列出，之後再補。

執行
----
    cd D:\\portal\\backend
    py -3.11 scripts\\import_cp_items_tc_20261123.py --excel-only
        ^ 只檢核 Excel，完全不連資料庫

    py -3.11 scripts\\import_cp_items_tc_20261123.py
        ^ 檢核＋預覽（連資料庫，不寫入）

    py -3.11 scripts\\import_cp_items_tc_20261123.py --apply
        ^ 預覽正確後才加 --apply，輸入 YES 才會寫入（--yes 跳過確認）

分頁 → 部門（預設值，可用 --dept-map "分頁=部門[+部門]" 覆寫；* ＝台中全部啟用部門）
--------------------------------------------------------------------------
    A食品、B飲品、OE   → 餐飲部
    C清潔用品、R客房用品 → 房務部
    S營業用品           → 餐飲部
    E工程              → 工程部
    G文具              → *（全部 11 個部門）
    H印刷              → 無料號，不需指定（台中沒有「營業部」，如需指定請用 --dept-map）

離開碼：0＝完成（含預覽）；1＝有錯誤無法 --apply／使用者取消；2＝執行失敗。
"""
from __future__ import annotations

import argparse
import difflib
import logging
import os
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from decimal import Decimal, InvalidOperation

for _s_ in (sys.stdout, sys.stderr):
    try:
        _s_.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

COMPANY_CODE = "HO"
CODE_PREFIX = "HO-"
DEFAULT_EXCEL = r"C:\OneDrive\_Ragic\myDoc\統購\20261123維春台中料號明細表(第二版)-FOR 金協理.xlsx"
SOURCE_LABEL = "20261123維春台中料號明細表(第二版)-FOR 金協理.xlsx"
RULE_SHEET = "編碼原則"

ITEM_SHEETS = ["A食品", "B飲品", "C清潔用品", "E工程", "G文具", "H印刷", "R客房用品", "S營業用品", "OE"]

DEFAULT_SHEET_DEPTS = {
    "A食品": ["餐飲部"],
    "B飲品": ["餐飲部"],
    "OE": ["餐飲部"],
    "C清潔用品": ["房務部"],
    "R客房用品": ["房務部"],
    "S營業用品": ["餐飲部"],
    "E工程": ["工程部"],
    "G文具": ["*"],
    "H印刷": [],
}

# Excel 廠商名稱 → 廠商主檔名稱（筆誤或別名）。可用 --vendor-alias 補充。
VENDOR_NAME_FIXES: dict = {"零用金": "行政辦公室零用金"}   # 2026-11-24 Samuel：零用金 → 行政辦公室零用金
# Ragic 沒有、直接建立為台中廠商的名稱（Ragic 不需要有資料）
EXTRA_VENDORS = ["蝦皮", "友信廣告企業社", "友賓食品工業有限公司", "妙管家", "寶美廣告", "日榮", "發統企業股份有限公司", "綜神有限公司"]  # 2026-11-24 Samuel：Ragic 無資料者直接建立

# ── Ragic「台中廠商表」（https://ap12.ragic.com/soutlet001/info/19）──
RAGIC_VENDOR_SERVER = "ap12.ragic.com"
RAGIC_VENDOR_ACCOUNT = "soutlet001"
RAGIC_VENDOR_SHEET = "info/19"
VENDOR_CODE_PREFIX = "HOV-"
RAGIC_FIELD_CANDIDATES = {
    "name": ["名稱", "廠商名稱", "供應商名稱", "廠商全名", "公司名稱"],
    "tax_id": ["統一編號", "統編"],
    "contact": ["聯絡窗口", "聯絡人"],
    "phone": ["電話", "電話號碼", "聯絡電話"],
    "terms": ["付款條件", "付款方式"],
    "notes": ["備註"],
}


# ─────────────────────────────────────────────────────────────────────────────
# 解析 Excel
# ─────────────────────────────────────────────────────────────────────────────
def _s(v):
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = str(v).strip()
    return s or None


def _dec(v):
    """數字或數字字串 → Decimal；空白 → None；無法解析丟 ValueError。"""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        return Decimal(str(v).strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"不是數字：{v!r}")


def _norm(x):
    return "".join((x or "").split())


def parse_rules(wb):
    """〈編碼原則〉→ {(大分類碼, 中分類碼, 細分類碼): 名稱}、{大分類碼: 大分類名稱}。
    欄位：B=大分類名稱 C=大分類代碼 D=中分類名稱 E=中分類代碼 F=細分類代碼（中分類空白沿用上一列）。"""
    ws = wb[RULE_SHEET]
    rules: dict = {}
    major_name: dict = {}
    letter = None
    mid = None
    for r in ws.iter_rows(min_row=3, values_only=True):
        if r[1]:
            letter = _s(r[2]) or letter
            if letter:
                major_name[letter] = _s(r[1])
        if r[4] is not None:
            mid = str(_s(r[4])).zfill(2)
        name = _s(r[3])
        if name is None or letter is None or mid is None or r[5] is None:
            continue
        rules[(letter, mid, str(_s(r[5])).zfill(2))] = name
    return rules, major_name


def parse_items(wb):
    """依「標題列」取欄位（不依欄位位置）。標題列＝含「料號」的那一列。
    重複標題（科目編號／科目名稱在客房、餐飲兩組）：取第一個有值的。"""
    rows = []
    for sheet in ITEM_SHEETS:
        if sheet not in wb.sheetnames:
            raise SystemExit(f"Excel 缺少分頁「{sheet}」")
        ws = wb[sheet]
        allrows = list(ws.iter_rows(values_only=True))
        hi = next((i for i, r in enumerate(allrows) if r and any(_s(v) == "料號" for v in r)), None)
        if hi is None:
            raise SystemExit(f"分頁「{sheet}」找不到「料號」標題列")
        hdr = [_s(h) or "" for h in allrows[hi]]
        cols = defaultdict(list)
        for i, h in enumerate(hdr):
            if h:
                cols[h].append(i)
        for need in ("料號", "類別", "品名", "單位", "廠商", "單價"):
            if not cols.get(need):
                raise SystemExit(f"分頁「{sheet}」缺少欄位「{need}」")

        def pick(r, name):
            for i in cols.get(name, []):
                if i < len(r) and _s(r[i]) is not None:
                    return r[i]
            return None

        for xl_row, r in enumerate(allrows[hi + 1:], start=hi + 2):
            if not r or _s(pick(r, "料號")) is None:
                continue
            rows.append({
                "sheet": sheet, "row": xl_row,
                "code": _s(pick(r, "料號")),
                "category": _s(pick(r, "類別")),
                "location": _s(pick(r, "位置")),
                "name_raw": pick(r, "品名"),
                "name": _s(pick(r, "品名")),
                "unit": _s(pick(r, "單位")),
                "vendor": _s(pick(r, "廠商")),
                "price_raw": pick(r, "單價"),
                "max_raw": pick(r, "最大庫存量"),
                "min_raw": pick(r, "最小庫存量"),
                "moq_raw": pick(r, "mini order"),
                "remark": _s(pick(r, "備註")),
                "acc_code": _s(pick(r, "科目編號")),
                "acc_name": _s(pick(r, "科目名稱")),
            })
    return rows


def validate_excel(rows, rules):
    """純 Excel 檢核（不碰資料庫）。回傳 (errors, warns)。同類警告合併成一行。"""
    errors: list = []
    grp: dict = OrderedDict()

    def g(msg, code):
        grp.setdefault(msg, []).append(code)

    seen: dict = {}
    for d in rows:
        tag = f"[{d['sheet']}!R{d['row']}] {d['code']}"
        code = d["code"]
        if not re.fullmatch(r"[A-Z]\d{7}", code):
            errors.append(f"{tag} 料號格式不符（應為 1 個大寫英文＋7 位數字）")
        elif code[0] != d["sheet"][0] and d["sheet"] != "OE":
            errors.append(f"{tag} 料號首字母 {code[0]} 與分頁「{d['sheet']}」不符")
        if code in seen:
            errors.append(f"{tag} 料號重複（另見 {seen[code]}）")
        seen[code] = f"{d['sheet']}!R{d['row']}"
        if d["name"] and len(d["name"]) > 200:
            errors.append(f"{tag} 品名超過 200 字（資料庫上限）")
        if d["unit"] and len(d["unit"]) > 20:
            errors.append(f"{tag} 單位超過 20 字（資料庫上限）")
        for key, label in (("name", "品名"), ("unit", "單位"), ("category", "類別"), ("vendor", "廠商")):
            if not d[key]:
                errors.append(f"{tag} 缺「{label}」")
        for key, label in (("price_raw", "單價"), ("max_raw", "最大庫存量"),
                           ("min_raw", "最小庫存量"), ("moq_raw", "mini order")):
            try:
                v = _dec(d[key])
            except ValueError as e:
                errors.append(f"{tag} 「{label}」{e}")
                v = None
            if v is not None and v < 0:
                errors.append(f"{tag} 「{label}」為負數：{v}")
            d[key.replace("_raw", "")] = v
        mx, mn = d.get("max"), d.get("min")
        if mx is not None and mn is not None and mn > mx:
            errors.append(f"{tag} 最小庫存量 {mn} 大於最大庫存量 {mx}")

        # ── 警告（不擋 --apply）──
        if d["price"] is None:
            g("單價空白（料號仍會匯入，單價為 NULL，之後請補）", code)
        if isinstance(d["name_raw"], str) and d["name_raw"] != d["name_raw"].strip():
            g("品名前後有空白（匯入時自動去除）", code)
        if d["price"] is not None and d["price"] < 1:
            g(f"單價小於 1（{d['price']}），請確認是否正確", code)
        for key, label in (("max", "最大庫存量"), ("min", "最小庫存量"), ("moq", "mini order")):
            v = d.get(key)
            if v is not None and v != v.to_integral_value():
                g(f"「{label}」不是整數，匯入時會四捨五入", code)

        d["key"] = (code[0], code[1:3], code[3:5])
        rule_name = rules.get(d["key"])
        if rule_name is None:
            g(f"碼 {code[:5]} 不在〈編碼原則〉→ 依 Excel 類別「{d['category']}」另建類別", code)
        elif d["category"] and d["category"] != rule_name:
            g(f"碼 {code[:5]}：Excel 類別「{d['category']}」≠ 編碼原則「{rule_name}」→ 匯入後類別以編碼原則為準", code)

    # 流水碼不連續（僅提醒，不補號）
    by_prefix = defaultdict(list)
    for code in seen:
        by_prefix[code[:5]].append(int(code[5:]))
    gaps = [k for k, v in by_prefix.items() if sorted(v) != list(range(1, len(v) + 1))]
    if gaps:
        g(f"細分類內流水碼不連續（可能是已刪除的料號，請確認；不影響匯入）", sorted(gaps))

    # 同一類別名稱掛不同科目（僅提醒）
    cat_acc = defaultdict(set)
    for d in rows:
        if d["category"] and d["acc_code"]:
            cat_acc[d["category"]].add(d["acc_code"])
    for cat, accs in cat_acc.items():
        if len(accs) > 1:
            g(f"類別「{cat}」對到多個科目 {sorted(accs)}（沿用 Excel 原值，請確認）", [cat])

    # 同名品名（僅提醒）
    names = Counter(d["name"] for d in rows if d["name"])
    dup_names = [n for n, c in names.items() if c > 1]
    if dup_names:
        g("同品名不同料號（請確認是否為不同項目）", dup_names)

    warns = []
    for msg, codes in grp.items():
        if msg.startswith("細分類內流水碼") or msg.startswith("類別「") or msg.startswith("同品名"):
            warns.append(f"{msg}：{'、'.join(map(str, codes[:20]))}" + ("…" if len(codes) > 20 else ""))
        else:
            sample = "、".join(map(str, codes[:6])) + ("…" if len(codes) > 6 else "")
            warns.append(f"{msg}：{len(codes)} 筆（{sample}）")
    return errors, warns


# ─────────────────────────────────────────────────────────────────────────────
# 資料庫面
# ─────────────────────────────────────────────────────────────────────────────
def parse_dept_map(entries):
    out = {}
    for e in entries or []:
        if "=" not in e:
            raise SystemExit(f"--dept-map 格式應為 分頁=部門（多個用 +），收到：{e!r}")
        sheet, depts = e.split("=", 1)
        sheet = sheet.strip()
        if sheet not in ITEM_SHEETS:
            raise SystemExit(f"--dept-map 的分頁「{sheet}」不存在；可用：{ITEM_SHEETS}")
        out[sheet] = [x.strip() for x in depts.split("+") if x.strip()]
    return out


def _url(session) -> str:
    try:
        return session.get_bind().url.render_as_string(hide_password=True)
    except Exception as e:  # noqa: BLE001
        return f"（無法取得連線資訊：{e}）"


def fetch_ragic_rows():
    import asyncio
    from app.services.ragic_adapter import RagicAdapter
    ad = RagicAdapter(sheet_path=RAGIC_VENDOR_SHEET, server_url=RAGIC_VENDOR_SERVER,
                      account=RAGIC_VENDOR_ACCOUNT)
    return asyncio.run(ad.fetch_all())


def _pick_field(keys, wanted, candidates):
    if wanted:
        return wanted if wanted in keys else None
    for c in candidates:
        if c in keys:
            return c
    return None


def parse_ragic_vendors(raw, args):
    """回傳 (vendors, fieldmap, error)。vendors: [{ragic_id,name,tax_id,contact,phone,terms,notes,short}]"""
    keys = []
    for rec in raw.values():
        for k in rec:
            if k not in keys and not str(k).startswith("_"):
                keys.append(k)
    fm = {
        "name": _pick_field(keys, args.ragic_name_field, RAGIC_FIELD_CANDIDATES["name"]),
        "tax_id": _pick_field(keys, args.ragic_taxid_field, RAGIC_FIELD_CANDIDATES["tax_id"]),
        "contact": _pick_field(keys, None, RAGIC_FIELD_CANDIDATES["contact"]),
        "phone": _pick_field(keys, None, RAGIC_FIELD_CANDIDATES["phone"]),
        "terms": _pick_field(keys, None, RAGIC_FIELD_CANDIDATES["terms"]),
        "notes": _pick_field(keys, None, RAGIC_FIELD_CANDIDATES["notes"]),
    }
    if not fm["name"]:
        return [], fm, "Ragic 台中廠商表找不到「廠商名稱」欄位；請用 --dump-ragic-fields 看欄名，再以 --ragic-name-field 指定"

    def val(rec, key):
        if not key:
            return None
        v = rec.get(key)
        v = ("" if v is None else str(v)).strip()
        return None if v in ("", "N/A", "-") else v

    out, seen = [], set()
    for rid, rec in raw.items():
        name = val(rec, fm["name"])
        if not name:
            continue
        tax = val(rec, fm["tax_id"])
        k = (tax or "") or _norm(name)
        if k in seen:
            continue
        seen.add(k)
        code = val(rec, "廠商編號")
        note = val(rec, fm["notes"])
        note = (f"Ragic廠商編號 {code}" + (f"；{note}" if note else "")) if code else note
        out.append({"ragic_id": rid, "name": name, "tax_id": tax, "contact": val(rec, fm["contact"]),
                    "phone": val(rec, fm["phone"]), "terms": val(rec, fm["terms"]),
                    "notes": note, "short": val(rec, "簡稱")})
    return out, fm, None


def build_plan(db, rows, rules, major_name, sheet_depts, ragic_vendors=None):
    from app.models.cycle_purchase_category import CyclePurchaseCategory
    from app.models.cycle_purchase_company import CyclePurchaseCompany
    from app.models.cycle_purchase_item import CyclePurchaseItem, CyclePurchaseItemMapping
    from app.models.cycle_purchase_reference import CyclePurchaseAccountCode, CyclePurchaseDepartment
    from app.models.cycle_purchase_vendor import CyclePurchaseVendor

    plan = {"errors": [], "warns": [], "info": [], "errors_vendor": []}

    company = db.query(CyclePurchaseCompany).filter(CyclePurchaseCompany.code == COMPANY_CODE).first()
    if not company:
        plan["errors"].append(f"找不到公司代碼 {COMPANY_CODE}（cycle_purchase_companies）")
        return plan
    if not company.is_active:
        plan["errors"].append(f"公司 {COMPANY_CODE} 已停用")
    plan["company"] = company

    # ── 部門 ──
    depts = (db.query(CyclePurchaseDepartment)
             .filter(CyclePurchaseDepartment.company_code == COMPANY_CODE,
                     CyclePurchaseDepartment.is_active == True)  # noqa: E712
             .order_by(CyclePurchaseDepartment.id).all())
    by_name = {d.dept_name.strip(): d for d in depts}
    plan["info"].append("台中啟用部門：" + ("、".join(by_name) if by_name else "（沒有啟用部門）"))
    resolved: dict = {}
    for sheet in ITEM_SHEETS:
        names = sheet_depts.get(sheet) or []
        n_items = sum(1 for r in rows if r["sheet"] == sheet)
        if n_items == 0:
            resolved[sheet] = []
            continue
        if not names:
            plan["errors"].append(f"分頁「{sheet}」（{n_items} 筆）尚未指定部門，請加 --dept-map \"{sheet}=部門名稱\"")
            continue
        objs = []
        for n in names:
            if n == "*":
                objs.extend(depts)
            elif n in by_name:
                objs.append(by_name[n])
            else:
                plan["errors"].append(f"分頁「{sheet}」指定的部門「{n}」不在台中啟用部門內")
        resolved[sheet] = list({o.id: o for o in objs}.values())
    plan["sheet_depts"] = resolved

    # ── 廠商：台中既有主檔比對；對不到的由 Ragic 台中廠商表補建 ──
    vendors = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.company_code == COMPANY_CODE).all()
    v_by_name = {v.vendor_name.strip(): v for v in vendors}
    v_by_norm = {_norm(v.vendor_name): v for v in vendors}
    v_by_tax = {_norm(v.tax_id): v for v in vendors if v.tax_id}
    # 只建立台中料號實際用到的廠商（2026-11-24 Samuel 同意）
    used_names = {_norm(VENDOR_NAME_FIXES.get(r["vendor"], r["vendor"])) for r in rows if r["vendor"]}
    new_vendors = []
    for rv in (ragic_vendors or []):
        tax = _norm(rv["tax_id"])
        if (tax and tax in v_by_tax) or _norm(rv["name"]) in v_by_norm:
            continue
        if _norm(rv["name"]) not in used_names and _norm(rv.get("short") or "") not in used_names:
            continue
        new_vendors.append(rv)
    for name in EXTRA_VENDORS:
        key = _norm(name)
        if key in used_names and key not in v_by_norm and not any(_norm(x["name"]) == key for x in new_vendors):
            new_vendors.append({"ragic_id": None, "name": name, "tax_id": None, "contact": None,
                                "phone": None, "terms": None, "notes": "Excel 指定新增（Ragic 無此名稱）",
                                "short": None})
    plan["new_vendors"] = new_vendors
    new_by_norm = {}
    for rv in new_vendors:
        new_by_norm.setdefault(_norm(rv["name"]), rv)
        if rv.get("short"):
            new_by_norm.setdefault(_norm(rv["short"]), rv)
    vendor_of: dict = {}
    missing_vendors: dict = {}
    for name in sorted({r["vendor"] for r in rows if r["vendor"]}):
        fixed = VENDOR_NAME_FIXES.get(name, name)
        if fixed != name:
            plan["warns"].append(f"廠商名稱已修正：{name} → {fixed}")
        v = v_by_name.get(fixed) or v_by_norm.get(_norm(fixed))
        if v:
            vendor_of[name] = v
            if not v.is_active:
                plan["warns"].append(f"廠商「{fixed}」在台中週採為停用狀態")
        elif _norm(fixed) in new_by_norm:
            vendor_of[name] = new_by_norm[_norm(fixed)]   # dict ＝ 待從 Ragic 建立
        else:
            missing_vendors[name] = sum(1 for r in rows if r["vendor"] == name)
    plan["vendor_of"] = vendor_of
    plan["missing_vendors"] = missing_vendors
    for name, n in missing_vendors.items():
        near = difflib.get_close_matches(VENDOR_NAME_FIXES.get(name, name),
                                         list(v_by_name) + [rv["name"] for rv in (ragic_vendors or [])],
                                         n=3, cutoff=0.5)
        plan["errors_vendor"].append(
            f"廠商「{name}」（{n} 筆）在台中週採主檔與 Ragic 台中廠商表都找不到"
            + (f"；相近：{'、'.join(near)}" if near else "")
            + "（請補齊 Ragic 廠商資料，或用 --vendor-alias 指定對應名稱）")

    # ── 會計科目 ──
    acc_rows = db.query(CyclePurchaseAccountCode).filter(
        CyclePurchaseAccountCode.company_code == COMPANY_CODE).all()
    acc_by_code = {a.code.strip(): a for a in acc_rows}
    acc_new: dict = OrderedDict()
    for r in rows:
        c = r["acc_code"]
        if not c:
            continue
        if c.endswith(".0") and c[:-2].isdigit():
            c = c[:-2]
        r["acc_code"] = c
        a = acc_by_code.get(c)
        if a is None:
            acc_new.setdefault(c, r["acc_name"] or c)
        elif r["acc_name"] and _norm(a.name) != _norm(r["acc_name"]):
            plan["warns"].append(f"會計科目 {c} 名稱不同：台中「{a.name}」vs Excel「{r['acc_name']}」（沿用台中，不改名）")
    plan["acc_by_code"] = acc_by_code
    plan["acc_new"] = acc_new
    for c in {r["acc_code"] for r in rows if r["acc_code"]}:
        if c in acc_by_code and not acc_by_code[c].is_active:
            plan["warns"].append(f"會計科目 {c} 在台中為停用狀態")

    # ── 類別主檔 ──
    cats = db.query(CyclePurchaseCategory).filter(CyclePurchaseCategory.company_code == COMPANY_CODE).all()
    cat_by_key = {(c.major_code, c.mid_code, c.sub_code): c for c in cats}
    cat_new: dict = OrderedDict()
    mid_name_of = {}
    for (mj, md, sb), nm in rules.items():
        mid_name_of.setdefault((mj, md), nm.split("-", 1)[0])
    for r in sorted(rows, key=lambda x: x["code"]):
        k = r["key"]
        if k in cat_by_key or k in cat_new:
            continue
        mj, md, sb = k
        canon = rules.get(k) or r["category"]
        parts = canon.split("-", 1)
        cat_new[k] = {
            "major_code": mj, "major_name": major_name.get(mj, mj),
            "mid_code": md, "mid_name": mid_name_of.get((mj, md), parts[0]),
            "sub_code": sb, "sub_name": parts[1] if len(parts) > 1 else None,
            "category_name": canon, "sheet": r["sheet"],
        }
    plan["cat_by_key"] = cat_by_key
    plan["cat_new"] = cat_new
    for k, c in cat_by_key.items():
        if not c.is_active and any(r["key"] == k for r in rows):
            plan["warns"].append(f"類別 {''.join(k)}「{c.category_name}」在類別主檔為停用，匯入該類別料號會失敗")

    # ── 既有料號 ──
    items = db.query(CyclePurchaseItem).filter(CyclePurchaseItem.company_code == COMPANY_CODE).all()
    maps = db.query(CyclePurchaseItemMapping).filter(CyclePurchaseItemMapping.company_code == COMPANY_CODE).all()
    item_by_id = {i.id: i for i in items}
    orig_to_item: dict = {}
    for m in maps:
        if m.original_code and m.item_id in item_by_id:
            orig_to_item.setdefault(m.original_code.strip(), item_by_id[m.item_id])
    plan["existing_maps"] = defaultdict(set)
    plan["existing_map_rows"] = {}
    for m in maps:
        plan["existing_maps"][m.item_id].add(m.department_id)
        plan["existing_map_rows"][(m.item_id, m.department_id)] = m
    plan["info"].append(f"台中既有料號 {len(items)} 筆；本次新料號 item_code 採「{CODE_PREFIX}」前綴")

    # 其他公司已占用的 item_code
    wanted = set()
    for r in rows:
        wanted.add(r["code"])
        wanted.add(CODE_PREFIX + r["code"])
    other = (db.query(CyclePurchaseItem.item_code, CyclePurchaseItem.company_code)
             .filter(CyclePurchaseItem.item_code.in_(wanted),
                     CyclePurchaseItem.company_code != COMPANY_CODE).all())
    other_map = {c: co for c, co in other}

    actions = []   # (row, 'new'|'existing'|'conflict', item_or_None, item_code)
    for r in rows:
        bare, pref = r["code"], CODE_PREFIX + r["code"]
        existing = (next((i for i in items if i.item_code == pref), None)
                    or next((i for i in items if i.item_code == bare), None)
                    or orig_to_item.get(bare))
        if existing:
            actions.append((r, "existing", existing, existing.item_code))
        elif pref in other_map:
            actions.append((r, "conflict", None, pref))
            plan["errors"].append(f"[{r['sheet']}!R{r['row']}] item_code {pref} 已被公司 {other_map[pref]} 的料號占用，略過")
        else:
            actions.append((r, "new", None, pref))
    plan["actions"] = actions
    return plan


def diff_existing(r, item, vendor):
    out = []

    def n(v):
        return None if v is None else Decimal(str(v))
    if n(item.unit_price) != r["price"]:
        out.append(("price", f"單價：台中 {n(item.unit_price)} → Excel {r['price']}"))
    if item.max_stock != (None if r["max"] is None else int(r["max"])) \
            or item.min_stock != (None if r["min"] is None else int(r["min"])):
        out.append(("stock", f"庫存上下限：台中 {item.max_stock}/{item.min_stock} → Excel {r['max']}/{r['min']}"))
    if (item.moq or 0) != (0 if r["moq"] is None else int(r["moq"])):
        out.append(("moq", f"MOQ：台中 {item.moq} → Excel {r['moq']}"))
    if (item.item_name or "").strip() != (r["name"] or ""):
        out.append(("name_diff", f"品名不同：台中「{item.item_name}」vs Excel「{r['name']}」"))
    if (item.unit or "") != (r["unit"] or ""):
        out.append(("unit", f"單位：台中 {item.unit!r} → Excel {r['unit']!r}"))
    if vendor and item.default_vendor_id != vendor.id:
        out.append(("vendor", "預設廠商不同"))
    return out


def print_report(plan, rows):
    p = print
    p("=" * 78)
    p("台中（HO）週採料號匯入檢核報告")
    p("=" * 78)
    for line in plan["info"]:
        p("  ·", line)
    acts = plan["actions"]
    c = Counter(a[1] for a in acts)
    p(f"\n【料號】Excel {len(rows)} 筆：新增 {c['new']}、已存在 {c['existing']}、衝突略過 {c['conflict']}")
    p("  分頁筆數：" + "、".join(f"{s} {sum(1 for r in rows if r['sheet'] == s)}" for s in ITEM_SHEETS))
    p("  分頁 → 部門：")
    for s in ITEM_SHEETS:
        ds = plan["sheet_depts"].get(s)
        if not ds and sum(1 for r in rows if r["sheet"] == s) == 0:
            p(f"    {s:<10} → （無料號，略過）")
        else:
            p(f"    {s:<10} → " + ("、".join(d.dept_name for d in ds) if ds else "（未指定）"))
    n_map = sum(len(plan["sheet_depts"].get(a[0]["sheet"], [])) for a in acts if a[1] == "new")
    p(f"  預計新增對照 {n_map} 筆（新料號 × 部門）")

    p(f"\n【類別主檔】預計新增 {len(plan['cat_new'])} 個細分類（既有 {len(plan['cat_by_key'])} 個）")
    for k, v in plan["cat_new"].items():
        p(f"    {''.join(k)}  {v['major_name']} / {v['mid_name']} / {v['sub_name'] or '—'}   類別名稱：{v['category_name']}")

    p(f"\n【會計科目】預計新增 {len(plan['acc_new'])} 個")
    for c_, n_ in plan["acc_new"].items():
        p(f"    {c_}  {n_}")

    p(f"\n【廠商】Excel 共 {len({r['vendor'] for r in rows if r['vendor']})} 家，已對到 {len(plan['vendor_of'])} 家")
    nv = plan.get("new_vendors") or []
    if nv:
        p(f"  將從 Ragic 台中廠商表新增 {len(nv)} 家（代碼 {VENDOR_CODE_PREFIX}NNNN）：")
        for rv in nv[:20]:
            p(f"    + {rv['name']}　統編 {rv['tax_id'] or '—'}")
        if len(nv) > 20:
            p(f"    ……另有 {len(nv) - 20} 家")
    for line in plan["errors_vendor"]:
        p("   ✗", line)

    ex = [(a[0], a[2]) for a in acts if a[1] == "existing"]
    if ex:
        p(f"\n【已存在的料號】{len(ex)} 筆（預設完全不動）")
        kinds = defaultdict(list)
        for r, item in ex:
            vend = plan["vendor_of"].get(r["vendor"]) if r["vendor"] else None
            if isinstance(vend, dict):
                vend = None
            for k, text in diff_existing(r, item, vend):
                kinds[k].append((item.item_code, text))
        labels = {
            "name_diff": "品名不同（--update-existing 不會覆蓋品名）",
            "unit": "單位不同（不會覆蓋）",
            "price": "單價不同（--update-existing 會更新）",
            "stock": "庫存上下限不同（--update-existing 會更新）",
            "moq": "MOQ 不同（--update-existing 會更新）",
            "vendor": "預設廠商不同（--update-existing 會更新）",
        }
        for k in ("name_diff", "unit", "price", "stock", "moq", "vendor"):
            if kinds.get(k):
                p(f"  ▸ {labels[k]}：{len(kinds[k])} 筆")
                for code_, text in kinds[k][:10]:
                    p(f"       {code_}: {text}")
                if len(kinds[k]) > 10:
                    p(f"       ……另有 {len(kinds[k]) - 10} 筆")
        if not kinds:
            p("  所有既有料號與 Excel 一致")

    p(f"\n【警告】{len(plan['warns'])} 則（不擋 --apply）")
    for w in plan["warns"]:
        p("   ⚠", w)
    errs = plan["errors"] + plan["errors_vendor"]
    p(f"\n【錯誤】{len(errs)} 則（有錯誤不能 --apply）")
    for e in errs:
        p("   ✗", e)


def apply_plan(db, plan, rows, update_existing):
    from app.models.cycle_purchase_category import CyclePurchaseCategory
    from app.models.cycle_purchase_item import CyclePurchaseItem, CyclePurchaseItemMapping
    from app.models.cycle_purchase_reference import CyclePurchaseAccountCode
    from app.models.cycle_purchase_vendor import CyclePurchaseVendor

    company = plan["company"]
    stats = Counter()

    # 0) 廠商：Ragic 台中廠商 → 本地廠商（source_vendor_id 為 NULL）
    if plan.get("new_vendors"):
        used = {c for (c,) in db.query(CyclePurchaseVendor.vendor_code).all()}
        seq = max([int(c[len(VENDOR_CODE_PREFIX):]) for c in used
                   if c.startswith(VENDOR_CODE_PREFIX) and c[len(VENDOR_CODE_PREFIX):].isdigit()] or [0])
        made = {}
        for rv in plan["new_vendors"]:
            seq += 1
            v = CyclePurchaseVendor(
                company_code=COMPANY_CODE, vendor_code=f"{VENDOR_CODE_PREFIX}{seq:04d}",
                vendor_name=rv["name"], tax_id=rv["tax_id"], contact_name=rv["contact"],
                contact_phone=rv["phone"], payment_terms=rv["terms"],
                notes=rv["notes"], is_active=True)
            db.add(v)
            made[id(rv)] = v
            stats["廠商(新增)"] += 1
        db.flush()
        for name, cur in list(plan["vendor_of"].items()):
            if isinstance(cur, dict):
                plan["vendor_of"][name] = made[id(cur)]

    # 1) 會計科目
    acc_by_code = dict(plan["acc_by_code"])
    for code, name in plan["acc_new"].items():
        a = CyclePurchaseAccountCode(company_code=COMPANY_CODE, code=code, name=name, is_active=True)
        db.add(a)
        acc_by_code[code] = a
        stats["會計科目"] += 1
    db.flush()

    # 2) 類別主檔
    cat_by_key = dict(plan["cat_by_key"])
    for k, v in plan["cat_new"].items():
        depts = plan["sheet_depts"].get(v["sheet"], [])
        c = CyclePurchaseCategory(
            company_code=COMPANY_CODE, company=company.name,
            department_id=depts[0].id if len(depts) == 1 else None,
            major_code=v["major_code"], major_name=v["major_name"],
            mid_code=v["mid_code"], mid_name=v["mid_name"],
            sub_code=v["sub_code"], sub_name=v["sub_name"],
            category_name=v["category_name"], serial_width=3, is_active=True,
            notes=f"台中料號匯入（{SOURCE_LABEL}）",
        )
        db.add(c)
        cat_by_key[k] = c
        stats["類別"] += 1
    db.flush()

    def q(v):
        return None if v is None else int(v.to_integral_value())

    for r, kind, item, code in plan["actions"]:
        if kind == "conflict":
            stats["略過(衝突)"] += 1
            continue
        vendor = plan["vendor_of"].get(r["vendor"]) if r["vendor"] else None
        acc = acc_by_code.get(r["acc_code"]) if r["acc_code"] else None
        depts = plan["sheet_depts"][r["sheet"]]

        if kind == "new":
            cat = cat_by_key[r["key"]]
            notes = "；".join(x for x in (
                f"位置：{r['location']}" if r["location"] else None,
                f"備註：{r['remark']}" if r["remark"] else None,
                f"來源：{SOURCE_LABEL}／{r['sheet']}",
            ) if x)
            item = CyclePurchaseItem(
                company_code=COMPANY_CODE, item_code=code, item_name=r["name"],
                category=cat.category_name, category_id=cat.id, unit=r["unit"],
                default_qty=0, moq=q(r["moq"]) or 0,
                max_stock=q(r["max"]), min_stock=q(r["min"]),
                unit_price=r["price"], default_vendor_id=vendor.id if vendor else None,
                is_active=True, is_cycle_item=True, notes=notes,
            )
            db.add(item)
            db.flush()
            stats["料號(新增)"] += 1
            have = set()
        else:
            have = set(plan["existing_maps"].get(item.id, set()))
            if not update_existing:
                stats["料號(已存在,未動)"] += 1
                continue
            item.unit_price = r["price"]
            item.max_stock = q(r["max"])
            item.min_stock = q(r["min"])
            item.moq = q(r["moq"]) or 0
            if vendor:
                item.default_vendor_id = vendor.id
            stats["料號(更新)"] += 1

        for d in depts:
            if d.id in have:
                m = plan["existing_map_rows"].get((item.id, d.id))
                if m is not None:
                    if vendor and m.vendor_id is None:
                        m.vendor_id = vendor.id
                    if acc and m.account_code_id is None:
                        m.account_code_id = acc.id
                    m.original_unit_price = r["price"]
                    stats["對照(補值)"] += 1
                continue
            db.add(CyclePurchaseItemMapping(
                item_id=item.id, company_code=COMPANY_CODE, company=company.name,
                department_id=d.id, original_code=r["code"], original_name=r["name"],
                original_vendor_name=r["vendor"], vendor_id=vendor.id if vendor else None,
                original_unit_price=r["price"], account_code_id=acc.id if acc else None,
                is_confirmed=True,
                notes=f"台中料號匯入（{r['sheet']}）",
            ))
            stats["對照"] += 1
    db.flush()
    return stats


def main():
    ap = argparse.ArgumentParser(description="台中（HO）週期採購料號匯入（預設只檢核預覽）")
    ap.add_argument("--excel-path", default=DEFAULT_EXCEL)
    ap.add_argument("--excel-only", action="store_true", help="只檢核 Excel，不連資料庫")
    ap.add_argument("--dept-map", action="append", metavar="分頁=部門[+部門]",
                    help="覆寫分頁對應部門，可重複；* 代表台中全部啟用部門")
    ap.add_argument("--vendor-alias", action="append", default=[], metavar="Excel名=廠商主檔名",
                    help="Excel 廠商名稱與廠商主檔名稱不同時的對照，可重複指定")
    ap.add_argument("--no-ragic-vendors", action="store_true", help="不讀 Ragic 台中廠商表")
    ap.add_argument("--dump-ragic-fields", action="store_true", help="只列出 Ragic 台中廠商表欄位與前 3 筆後結束")
    ap.add_argument("--ragic-name-field", help="Ragic「廠商名稱」欄位名（自動判斷失敗時指定）")
    ap.add_argument("--ragic-taxid-field", help="Ragic「統一編號」欄位名")
    ap.add_argument("--update-existing", action="store_true",
                    help="已存在料號：更新單價／庫存／MOQ／預設廠商並補部門對照（品名、單位、類別不覆蓋）")
    ap.add_argument("--apply", action="store_true", help="真的寫入（需輸入 YES）")
    ap.add_argument("--yes", action="store_true", help="--apply 時不再詢問")
    args = ap.parse_args()

    import openpyxl
    if not os.path.exists(args.excel_path):
        print(f"找不到 Excel：{args.excel_path}")
        return 2
    wb = openpyxl.load_workbook(args.excel_path, data_only=True)
    rules, major_name = parse_rules(wb)
    rows = parse_items(wb)
    x_errors, x_warns = validate_excel(rows, rules)

    for a in args.vendor_alias:
        if "=" not in a:
            print(f"✗ --vendor-alias 格式應為「Excel名=主檔名」：{a}")
            return 2
        k, v = a.split("=", 1)
        VENDOR_NAME_FIXES[k.strip()] = v.strip()

    if args.excel_only:
        print(f"Excel：{args.excel_path}（{len(rows)} 筆料號、編碼原則 {len(rules)} 條）")
        print(f"【錯誤】{len(x_errors)} 則")
        for e in x_errors:
            print("   ✗", e)
        print(f"【警告】{len(x_warns)} 則")
        for w in x_warns:
            print("   ⚠", w)
        return 1 if x_errors else 0

    ragic_vendors = None
    if args.dump_ragic_fields or not args.no_ragic_vendors:
        try:
            raw = fetch_ragic_rows()
        except Exception as e:  # noqa: BLE001
            print(f"✗ 讀取 Ragic 台中廠商表失敗：{type(e).__name__}: {e}")
            return 2
        if args.dump_ragic_fields:
            for rid, rec in list(raw.items())[:3]:
                print(f"--- Ragic #{rid}")
                for k, v in rec.items():
                    print(f"  {k}: {v!r}")
            print(f"（共 {len(raw)} 筆）")
            return 0
        ragic_vendors, fm, err = parse_ragic_vendors(raw, args)
        if err:
            print("✗", err)
            return 2
        print(f"Ragic 台中廠商表（{RAGIC_VENDOR_SHEET}）：{len(raw)} 筆、可用 {len(ragic_vendors)} 家；欄位對應 {fm}")

    sheet_depts = dict(DEFAULT_SHEET_DEPTS)
    sheet_depts.update(parse_dept_map(args.dept_map))

    from app.core.cycle_purchase_database import CyclePurchaseSessionLocal
    from app.models import (cycle_purchase_category, cycle_purchase_company,  # noqa: F401
                            cycle_purchase_item, cycle_purchase_reference, cycle_purchase_vendor)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
    db = CyclePurchaseSessionLocal()
    try:
        try:
            db.get_bind().echo = False   # .env DEBUG=True 時 engine 會印出每句 SQL
        except Exception:
            pass
        print(f"連線目標：{_url(db)}")
        print(f"Excel：{args.excel_path}（{len(rows)} 筆料號、編碼原則 {len(rules)} 條）\n")
        plan = build_plan(db, rows, rules, major_name, sheet_depts, ragic_vendors)
        if "actions" not in plan:
            for e in plan["errors"]:
                print("✗", e)
            return 1
        plan["errors"] = x_errors + plan["errors"]
        plan["warns"] = x_warns + plan["warns"]
        print_report(plan, rows)

        blocking = plan["errors"] + plan["errors_vendor"]
        if not args.apply:
            print("\n（預覽模式，未寫入任何資料。確認無誤後加 --apply）")
            return 1 if blocking else 0
        if blocking:
            print(f"\n✗ 有 {len(blocking)} 個錯誤，不能 --apply，請先處理上面的錯誤。")
            return 1
        if not args.yes:
            ans = input("\n確認寫入上述資料？輸入 YES 繼續：").strip()
            if ans != "YES":
                print("已取消，未寫入。")
                return 1
        stats = apply_plan(db, plan, rows, args.update_existing)
        db.commit()
        print("\n✓ 已寫入：" + "、".join(f"{k} {v}" for k, v in stats.items()))
        return 0
    except Exception as e:  # noqa: BLE001
        db.rollback()
        print(f"\n✗ 執行失敗，已 rollback：{type(e).__name__}: {e}")
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
