#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
週期採購 — 日曜（OU）料號匯入：《20261002 日曜料號明細表-製作物.xlsx》
================================================================================

做什麼
------
把 Excel 的料號匯入「週期採購 → 料號主檔」（公司＝日曜／OU），一次建立：
  1. 類別主檔（cycle_purchase_categories）  依 Excel〈編碼原則〉分頁，缺的才建
  2. 會計科目（cycle_purchase_account_codes） 依 Excel 的「科目編號／科目名稱」，缺的才建
  3. 料號（cycle_purchase_items）            item_code、品名、單位、單價、庫存上下限、MOQ、預設廠商
  4. 料號對照（cycle_purchase_item_mappings）每個料號 × 每個部門一筆，帶廠商、單價、會計科目

預設只「檢核＋預覽」，不寫入任何資料。確認報告沒問題後加 --apply。

執行（正式區主機；先停止請購單作業更保險）
--------------------------------------------------------------------------
    cd D:\\portal\\backend
    py -3.11 scripts\\import_cp_items_ou_20261002.py --excel-path "<xlsx路徑>"
        ^ 檢核＋預覽（不寫入）。分頁部門未決定的會在報告最前面列出。

    py -3.11 scripts\\import_cp_items_ou_20261002.py --excel-path "<xlsx路徑>" ^
        --dept-map "工務用=管理部" --dept-map "製作物=行銷部" --apply
        ^ 預覽正確後才加 --apply，輸入 YES 才會寫入（--yes 跳過確認）

分頁 → 部門（--dept-map "分頁=部門名稱"；多個部門用 + 連接；* ＝日曜全部啟用部門）
--------------------------------------------------------------------------
    文具&印刷  預設 *            （比照春大直：文具開放全部門）
    清潔用品   預設 管理部       （比照春大直）
    營業用品   預設 營業部       （比照春大直）
    工務用     無預設，必須指定  （日曜目前沒有工程部／工務部）
    製作物     無預設，必須指定  （D 系列，科目 621702 廣告費-促銷）
    指定的部門名稱必須已存在於週採部門（日曜、啟用）。沒指定完 --apply 會被擋下。

寫入規則（刻意保守）
--------------------------------------------------------------------------
- 單一 transaction，任何一步失敗全部 rollback；寫入前先印連線目標（遮蔽密碼）。
- 不新增廠商：廠商主檔的唯一來源是合約模組（鏡像同步）。Excel 的廠商名稱對不到
  週採廠商時，--apply 會被擋下並列出清單，請先到合約模組／廠商資料補齊並同步，
  或修正 Excel 的名稱。（--allow-missing-vendors 可強制放行，該列對照的 vendor_id
  會是 NULL，彙整單依廠商分單時會歸不到廠商——不建議。）
- 已存在的日曜料號（item_code 或對照原始碼相同）預設完全不動，只在報告列出差異；
  加 --update-existing 才會更新單價／庫存／MOQ／預設廠商，並補上缺少的部門對照。
  品名、單位、類別一律不覆蓋（避免蓋掉人工修正）。
- item_code 格式：偵測日曜既有料號是「純原始碼」還是「OU-前綴」，沿用同一種；
  日曜沒有任何料號時用 OU- 前綴（同春大直的 CH-）。可用 --code-style 強制指定。
  對照表 original_code 永遠存純原始碼（不含前綴）。
- item_code 若撞到其他公司的料號，該筆跳過並列在報告（不會覆蓋別家資料）。
- 類別一律以〈編碼原則〉的名稱為準寫進類別主檔，料號 category 由主檔帶入
  （與 service._apply_item_category 一致）；Excel 的「類別」字串與編碼原則不同者列為警告。

離開碼：0＝完成（含預覽）；1＝有錯誤無法 --apply／使用者取消；2＝執行失敗。
"""
from __future__ import annotations

import argparse
import difflib
import os
import sys
from collections import Counter, OrderedDict, defaultdict
from decimal import Decimal, InvalidOperation

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import logging  # noqa: E402
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.getcwd())

COMPANY_CODE = "OU"
CODE_PREFIX = "OU-"
DEFAULT_EXCEL = r"C:\OneDrive\_Ragic\myDoc\統購\20261002 日曜料號明細表-製作物.xlsx"
SOURCE_LABEL = "20261002 日曜料號明細表-製作物.xlsx"

# 料號分頁（標題在第 2 列、資料從第 3 列）。〈編碼原則〉另外解析。
ITEM_SHEETS = ["製作物", "文具&印刷", "清潔用品", "營業用品", "工務用"]
RULE_SHEET = "編碼原則"

# 分頁 → 部門。None ＝ 必須由 --dept-map 指定；"*" ＝ 日曜全部啟用部門
DEFAULT_SHEET_DEPTS = {
    "製作物": ["行銷部"],      # 2026-11-17 Samuel 確認
    "文具&印刷": ["*"],
    "清潔用品": ["管理部"],
    "營業用品": ["營業部"],
    "工務用": ["管理部"],      # 2026-11-17 Samuel 確認（日曜無工務部）
}

# 大分類代碼 → 名稱：編碼原則分頁的 B 欄為準；編碼原則沒有的 D 系列在此補上
EXTRA_MAJOR_NAME = {"D": "製作物"}

# Excel 廠商名稱的已知筆誤 → 正確名稱（比對前先套用，並在報告列出）
VENDOR_NAME_FIXES = {
    "藍格印刷國際企業有限公思": "藍格印刷國際企業有限公司",
}


# ─────────────────────────────────────────────────────────────────────────────
# 解析 Excel
# ─────────────────────────────────────────────────────────────────────────────
def _s(v):
    if v is None:
        return None
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


def parse_rules(wb):
    """〈編碼原則〉→ {(大分類碼, 中分類碼, 細分類碼): 名稱}、{大分類碼: 大分類名稱}"""
    ws = wb[RULE_SHEET]
    rules: dict = {}
    major_name: dict = {}
    letter = None
    mid = None
    for r in ws.iter_rows(min_row=3, values_only=True):
        if r[1]:
            letter = _s(r[2])
            if letter:
                major_name[letter] = _s(r[1])
        if r[4] is not None:
            mid = str(r[4]).strip().zfill(2)
        name = _s(r[3])
        if name is None or letter is None or mid is None or r[5] is None:
            continue
        rules[(letter, mid, str(r[5]).strip().zfill(2))] = name
    for k, v in EXTRA_MAJOR_NAME.items():
        major_name.setdefault(k, v)
    return rules, major_name


def parse_items(wb):
    rows = []
    for sheet in ITEM_SHEETS:
        if sheet not in wb.sheetnames:
            raise SystemExit(f"Excel 缺少分頁「{sheet}」")
        ws = wb[sheet]
        header = next(ws.iter_rows(min_row=2, max_row=2, values_only=True))
        cols = {str(h).strip(): i for i, h in enumerate(header) if h}
        for need in ("料號", "類別", "品名", "單位", "廠商", "單價", "科目編號", "科目名稱"):
            if need not in cols:
                raise SystemExit(f"分頁「{sheet}」缺少欄位「{need}」")

        def g(r, name):
            i = cols.get(name)
            return r[i] if i is not None and i < len(r) else None

        for xl_row, r in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
            if not _s(g(r, "料號")):
                continue
            rows.append({
                "sheet": sheet, "row": xl_row,
                "code": _s(g(r, "料號")),
                "category": _s(g(r, "類別")),
                "location": _s(g(r, "位置")),
                "name_raw": g(r, "品名"),
                "name": _s(g(r, "品名")),
                "unit": _s(g(r, "單位")),
                "vendor": _s(g(r, "廠商")),
                "price_raw": g(r, "單價"),
                "max_raw": g(r, "最大庫存量"),
                "min_raw": g(r, "最小庫存量"),
                "moq_raw": g(r, "mini order"),
                "remark": _s(g(r, "備註")),
                "acc_code": _s(g(r, "科目編號")),
                "acc_name": _s(g(r, "科目名稱")),
                "terms": _s(g(r, "月結")),
            })
    return rows


def validate_excel(rows, rules):
    """純 Excel 檢核（不碰資料庫）。回傳 (errors, warnings)，皆為 list[str]。"""
    import re
    errors: list = []
    warns: list = []
    grp: dict = OrderedDict()   # 同類警告合併成一行：訊息 → [料號...]

    def g(msg, code):
        grp.setdefault(msg, []).append(code)

    seen: dict = {}
    name2keys = defaultdict(list)
    for k, n in rules.items():
        name2keys[n].append(k)

    for d in rows:
        tag = f"[{d['sheet']}!R{d['row']}] {d['code']}"
        code = d["code"]
        # ── 錯誤（會擋 --apply）──
        if not re.fullmatch(r"[A-Z]\d{7}", d["code"]):
            errors.append(f"{tag} 料號格式不符（應為 1 個大寫英文＋7 位數字）")
        if d["code"] in seen:
            errors.append(f"{tag} 料號重複（另見 {seen[d['code']]}）")
        seen[d["code"]] = f"{d['sheet']}!R{d['row']}"
        if d["name"] and len(d["name"]) > 200:
            errors.append(f"{tag} 品名超過 200 字（資料庫上限）")
        if d["unit"] and len(d["unit"]) > 20:
            errors.append(f"{tag} 單位超過 20 字（資料庫上限）")
        for key, label in (("name", "品名"), ("unit", "單位"), ("category", "類別"),
                           ("vendor", "廠商"), ("acc_code", "科目編號"), ("acc_name", "科目名稱")):
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

        # ── 警告 ──
        if d["price"] is None:
            g("單價空白（料號仍會匯入，單價為 NULL，之後請補）", code)
        if isinstance(d["name_raw"], str) and d["name_raw"] != d["name_raw"].strip():
            g("品名前後有空白（匯入時自動去除）", code)
        if isinstance(d["price_raw"], str) and d["price"] is not None:
            g("單價在 Excel 是文字格式（匯入時自動轉成數字）", code)
        for key, label in (("max", "最大庫存量"), ("min", "最小庫存量"), ("moq", "mini order")):
            v = d.get(key)
            if v is not None and v != v.to_integral_value():
                g(f"「{label}」不是整數，匯入時會四捨五入", code)

        key = (code[0], code[1:3], code[3:5])
        d["key"] = key
        rule_name = rules.get(key)
        if rule_name is None:
            g(f"碼 {code[:5]} 不在〈編碼原則〉→ 依 Excel 類別「{d['category']}」另建類別", code)
        elif d["category"] and d["category"] != rule_name:
            other = name2keys.get(d["category"])
            if other:
                g(f"❗碼 {code[:5]} 的編碼原則名稱是「{rule_name}」，Excel 類別卻寫「{d['category']}」"
                  f"（那是 {''.join(other[0])} 的名稱）→ 疑似料號編錯碼，請先確認", code)
            elif d["category"].split("-", 1)[0] != rule_name.split("-", 1)[0]:
                g(f"❗碼 {code[:5]} 的編碼原則是「{rule_name}」，Excel 類別卻是「{d['category']}」"
                  f"（中分類完全不同）→ 疑似料號編錯碼，請先確認", code)
            else:
                g(f"碼 {code[:5]}：Excel 類別「{d['category']}」≠ 編碼原則「{rule_name}」→ 匯入後類別以編碼原則為準", code)

    for msg, codes in grp.items():
        sample = "、".join(codes[:6]) + ("…" if len(codes) > 6 else "")
        warns.append(f"{msg}：{len(codes)} 筆（{sample}）")

    # 同一類別名稱掛在不同碼（例：斷路器 E0301／E0302、紙）
    by_cat = defaultdict(set)
    for d in rows:
        by_cat[d["category"]].add(d["code"][:5])
    for cat, prefixes in sorted(by_cat.items(), key=lambda x: str(x[0])):
        if len(prefixes) > 1:
            warns.append(f"類別字串「{cat}」同時用在多個碼 {sorted(prefixes)}")

    # 廠商月結不一致
    terms = defaultdict(set)
    for d in rows:
        if d["vendor"] and d["terms"]:
            terms[d["vendor"]].add(d["terms"])
    for v, t in terms.items():
        if len(t) > 1:
            warns.append(f"廠商「{v}」的月結在不同列不一致：{sorted(t)}")
    return errors, warns


# ─────────────────────────────────────────────────────────────────────────────
# 資料庫面
# ─────────────────────────────────────────────────────────────────────────────
def _url(session) -> str:
    try:
        return session.get_bind().url.render_as_string(hide_password=True)
    except Exception as e:  # noqa: BLE001
        return f"（無法取得連線資訊：{e}）"


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



# ── Ragic「廠商資料表-管理部」（日曜廠商來源，freed-management-division/20）──
RAGIC_VENDOR_SERVER = "ap12.ragic.com"
RAGIC_VENDOR_ACCOUNT = "soutlet001"
RAGIC_VENDOR_SHEET = "freed-management-division/20"
VENDOR_CODE_PREFIX = "OUV-"
# 欄位名稱候選（Ragic 回傳中文欄名；實際欄名可用 --dump-ragic-fields 確認，或以 --ragic-*-field 覆寫）
RAGIC_FIELD_CANDIDATES = {
    "name": ["名稱", "廠商名稱", "供應商名稱", "廠商全名", "公司名稱"],
    "tax_id": ["統一編號", "統編"],
    "contact": ["聯絡窗口", "聯絡人"],
    "phone": ["電話", "電話號碼", "聯絡電話"],
    "terms": ["付款條件", "付款方式"],
    "notes": ["備註"],
}


def fetch_ragic_rows():
    import asyncio
    from app.services.ragic_adapter import RagicAdapter
    ad = RagicAdapter(sheet_path=RAGIC_VENDOR_SHEET, server_url=RAGIC_VENDOR_SERVER,
                      account=RAGIC_VENDOR_ACCOUNT)
    return asyncio.run(ad.fetch_all())


def _pick_field(keys, wanted, candidates):
    if wanted:
        return wanted if wanted in keys else None
    for c in candidates:                      # 先完全相等，再「包含」
        if c in keys:
            return c
    return None


def parse_ragic_vendors(raw, args):
    """回傳 (vendors, fieldmap, error)。vendors: [{ragic_id,name,tax_id,contact,phone,terms,notes}]"""
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
        return [], fm, "Ragic 廠商表找不到「廠商名稱」欄位；請用 --dump-ragic-fields 看欄名，再以 --ragic-name-field 指定"

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
        k = (tax or "") or "".join(name.split())
        if k in seen:
            continue
        seen.add(k)
        code = val(rec, "廠商編號")
        note = val(rec, fm["notes"])
        note = f"Ragic廠商編號 {code}" + (f"；{note}" if note else "") if code else note
        out.append({"ragic_id": rid, "name": name, "tax_id": tax, "contact": val(rec, fm["contact"]),
                    "phone": val(rec, fm["phone"]), "terms": val(rec, fm["terms"]),
                    "notes": note, "short": val(rec, "簡稱")})
    return out, fm, None


def build_plan(db, rows, rules, major_name, sheet_depts, code_style_arg, ragic_vendors=None):
    from app.models.cycle_purchase_category import CyclePurchaseCategory
    from app.models.cycle_purchase_company import CyclePurchaseCompany
    from app.models.cycle_purchase_item import CyclePurchaseItem, CyclePurchaseItemMapping
    from app.models.cycle_purchase_reference import CyclePurchaseAccountCode, CyclePurchaseDepartment
    from app.models.cycle_purchase_vendor import CyclePurchaseVendor

    plan = {"errors": [], "warns": [], "info": []}

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
    plan["info"].append("日曜啟用部門：" + "、".join(by_name) if by_name else "日曜沒有啟用部門")
    resolved: dict = {}
    for sheet in ITEM_SHEETS:
        names = sheet_depts.get(sheet)
        n_items = sum(1 for r in rows if r["sheet"] == sheet)
        if not names:
            plan["errors"].append(
                f"分頁「{sheet}」（{n_items} 筆）尚未指定部門，請加 --dept-map \"{sheet}=部門名稱\""
            )
            continue
        objs = []
        for n in names:
            if n == "*":
                objs.extend(depts)
            elif n in by_name:
                objs.append(by_name[n])
            else:
                plan["errors"].append(f"分頁「{sheet}」指定的部門「{n}」不在日曜啟用部門內")
        resolved[sheet] = list({o.id: o for o in objs}.values())
    plan["sheet_depts"] = resolved

    # ── 廠商（只比對，不新增）──
    vendors = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.company_code == COMPANY_CODE).all()
    v_by_name = {v.vendor_name.strip(): v for v in vendors}
    v_by_norm = {"".join(v.vendor_name.split()): v for v in vendors}
    # Ragic 廠商：日曜主檔尚未有者（統編相同或名稱相同視為已有）→ 預定新增為本地自建廠商
    new_vendors = []
    if ragic_vendors:
        v_by_tax = {"".join((v.tax_id or "").split()): v for v in vendors if v.tax_id}
        for rv in ragic_vendors:
            tax = "".join((rv["tax_id"] or "").split())
            if (tax and tax in v_by_tax) or "".join(rv["name"].split()) in v_by_norm:
                continue
            new_vendors.append(rv)
        # 其他公司已有同統編廠商（僅供報告：同廠商多公司別）
        other = (db.query(CyclePurchaseVendor.tax_id, CyclePurchaseVendor.company_code)
                 .filter(CyclePurchaseVendor.company_code != COMPANY_CODE,
                         CyclePurchaseVendor.tax_id.isnot(None)).all())
        tax_cos = defaultdict(set)
        for t_, c_ in other:
            tax_cos["".join((t_ or "").split())].add(c_)
        for rv in new_vendors:
            rv["also_in"] = sorted(tax_cos.get("".join((rv["tax_id"] or "").split()), []))
    plan["new_vendors"] = new_vendors
    new_by_norm = {"".join(rv["name"].split()): rv for rv in new_vendors}
    for rv in new_vendors:                       # 簡稱也可比對（名稱優先）
        if rv.get("short"):
            new_by_norm.setdefault("".join(rv["short"].split()), rv)
    ragic_names = [rv["name"] for rv in (ragic_vendors or [])]
    vendor_of: dict = {}
    missing_vendors: dict = defaultdict(int)
    for name in sorted({r["vendor"] for r in rows if r["vendor"]}):
        fixed = VENDOR_NAME_FIXES.get(name, name)
        if fixed != name:
            plan["warns"].append(f"廠商名稱筆誤已修正：{name} → {fixed}")
        v = v_by_name.get(fixed) or v_by_norm.get("".join(fixed.split()))
        if not v and "".join(fixed.split()) in new_by_norm:
            vendor_of[name] = new_by_norm["".join(fixed.split())]   # 預定新增（apply 時換成實體）
            continue
        if v:
            vendor_of[name] = v
            if not v.is_active:
                plan["warns"].append(f"廠商「{fixed}」在週採為停用狀態")
        else:
            missing_vendors[name] = sum(1 for r in rows if r["vendor"] == name)
    plan["vendor_of"] = vendor_of
    plan["missing_vendors"] = dict(missing_vendors)
    for name, n in missing_vendors.items():
        near = difflib.get_close_matches(VENDOR_NAME_FIXES.get(name, name),
                                         list(v_by_name) + ragic_names, n=3, cutoff=0.5)
        plan["errors_vendor"] = plan.get("errors_vendor", [])
        plan["errors_vendor"].append(
            f"廠商「{name}」（{n} 筆）在日曜週採廠商主檔找不到" + (f"；相近：{'、'.join(near)}" if near else "")
        )

    # ── 會計科目 ──
    acc_rows = db.query(CyclePurchaseAccountCode).filter(
        CyclePurchaseAccountCode.company_code == COMPANY_CODE).all()
    acc_by_code = {a.code.strip(): a for a in acc_rows}
    acc_new: dict = OrderedDict()
    for r in rows:
        c = r["acc_code"]
        if not c:
            continue
        # Excel 科目編號是數字格式，可能被讀成 621601.0
        c = c[:-2] if c.endswith(".0") and c[:-2].isdigit() else c
        r["acc_code"] = c
        a = acc_by_code.get(c)
        if a is None:
            acc_new.setdefault(c, r["acc_name"])
        elif r["acc_name"] and a.name.strip() != r["acc_name"]:
            plan["warns"].append(
                f"會計科目 {c} 名稱不同：週採「{a.name}」vs Excel「{r['acc_name']}」（沿用週採，不改名）")
    plan["acc_by_code"] = acc_by_code
    plan["acc_new"] = acc_new
    inactive_acc = [c for c in {r["acc_code"] for r in rows} if c in acc_by_code and not acc_by_code[c].is_active]
    for c in inactive_acc:
        plan["warns"].append(f"會計科目 {c} 在週採為停用狀態")

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
    # 新類別同名警告
    names = Counter(v["category_name"] for v in cat_new.values())
    for k, v in cat_new.items():
        if names[v["category_name"]] > 1 or any(
                c.category_name == v["category_name"] for c in cat_by_key.values()):
            plan["warns"].append(
                f"新類別 {''.join(k)} 的名稱「{v['category_name']}」與其他類別重名，"
                f"下拉選單會出現兩個同名項目，建議之後在類別主檔補上細分類名稱")

    # ── 既有料號 ──
    items = db.query(CyclePurchaseItem).filter(CyclePurchaseItem.company_code == COMPANY_CODE).all()
    maps = (db.query(CyclePurchaseItemMapping)
            .filter(CyclePurchaseItemMapping.company_code == COMPANY_CODE).all())
    orig_to_item: dict = {}
    item_by_id = {i.id: i for i in items}
    for m in maps:
        if m.original_code and m.item_id in item_by_id:
            orig_to_item.setdefault(m.original_code.strip(), item_by_id[m.item_id])
    bare = sum(1 for i in items if not i.item_code.startswith(CODE_PREFIX))
    pref = sum(1 for i in items if i.item_code.startswith(CODE_PREFIX))
    if code_style_arg:
        style = code_style_arg
    elif items:
        style = "prefixed" if pref > bare else "bare"
    else:
        style = "prefixed"
    plan["code_style"] = style
    plan["info"].append(
        f"日曜既有料號 {len(items)} 筆（純原始碼 {bare}／{CODE_PREFIX}前綴 {pref}），"
        f"本次新料號 item_code 採「{'OU-前綴' if style == 'prefixed' else '純原始碼'}」")
    plan["existing_maps"] = defaultdict(set)
    plan["existing_map_rows"] = {}
    for m in maps:
        plan["existing_maps"][m.item_id].add(m.department_id)
        plan["existing_map_rows"][(m.item_id, m.department_id)] = m
    plan["map_stats"] = {
        "total": len(maps),
        "no_vendor": sum(1 for m in maps if m.vendor_id is None),
        "no_account": sum(1 for m in maps if m.account_code_id is None),
    }
    # 廠商診斷：日曜廠商主檔現況，以及 Excel 廠商名稱是否出現在別家公司的廠商主檔
    other_v = (db.query(CyclePurchaseVendor.vendor_name, CyclePurchaseVendor.company_code)
               .filter(CyclePurchaseVendor.company_code != COMPANY_CODE).all())
    other_by_name = defaultdict(set)
    for n_, c_ in other_v:
        other_by_name["".join((n_ or "").split())].add(c_)
    plan["vendor_diag"] = {
        "ou_total": len(vendors),
        "ou_sample": [v.vendor_name for v in vendors[:8]],
        "elsewhere": {name: sorted(other_by_name.get("".join(VENDOR_NAME_FIXES.get(name, name).split()), []))
                      for name in plan["missing_vendors"]
                      if other_by_name.get("".join(VENDOR_NAME_FIXES.get(name, name).split()))},
    }

    # 其他公司已占用的 item_code
    wanted = set()
    for r in rows:
        wanted.add(r["code"])
        wanted.add(CODE_PREFIX + r["code"])
    other = (db.query(CyclePurchaseItem.item_code, CyclePurchaseItem.company_code)
             .filter(CyclePurchaseItem.item_code.in_(wanted),
                     CyclePurchaseItem.company_code != COMPANY_CODE).all())
    other_map = {c: co for c, co in other}

    actions = []   # (row, 'new'|'existing'|'conflict', item_or_none, item_code)
    for r in rows:
        bare_code, pref_code = r["code"], CODE_PREFIX + r["code"]
        existing = (next((i for i in items if i.item_code == bare_code), None)
                    or next((i for i in items if i.item_code == pref_code), None)
                    or orig_to_item.get(bare_code))
        new_code = pref_code if style == "prefixed" else bare_code
        if existing:
            actions.append((r, "existing", existing, existing.item_code))
        elif new_code in other_map:
            actions.append((r, "conflict", None, new_code))
            plan["errors"].append(
                f"[{r['sheet']}!R{r['row']}] item_code {new_code} 已被公司 {other_map[new_code]} 的料號占用，略過")
        else:
            actions.append((r, "new", None, new_code))
    plan["actions"] = actions
    return plan


def _norm(x):
    return "".join((x or "").split())


def diff_existing(r, item, vendor):
    """回傳 [(類別, 說明)]。品名比對用「品名＋規格」：舊匯入會在第一個空白把 Excel 品名切成
    品名／規格兩欄，單看 item_name 會誤判成不同。"""
    out = []
    def n(v):
        return None if v is None else Decimal(str(v))
    if n(item.unit_price) != r["price"]:
        out.append(("price", f"單價：週採 {n(item.unit_price)} → Excel {r['price']}"))
    if item.max_stock != (None if r["max"] is None else int(r["max"])) \
            or item.min_stock != (None if r["min"] is None else int(r["min"])):
        out.append(("stock", f"庫存上下限：週採 {item.max_stock}/{item.min_stock} → Excel {r['max']}/{r['min']}"))
    if (item.moq or 0) != (0 if r["moq"] is None else int(r["moq"])):
        out.append(("moq", f"MOQ：週採 {item.moq} → Excel {r['moq']}"))
    if (item.item_name or "").strip() != (r["name"] or ""):
        full = f"{item.item_name or ''} {item.spec or ''}"
        if _norm(full) == _norm(r["name"]):
            out.append(("name_split", f"品名被切成「{item.item_name}」＋規格「{item.spec}」（合起來與 Excel 相同）"))
        else:
            out.append(("name_diff", f"品名不同：週採「{item.item_name}｜{item.spec or ''}」vs Excel「{r['name']}」"))
    if (item.unit or "") != (r["unit"] or ""):
        out.append(("unit", f"單位：週採 {item.unit!r} → Excel {r['unit']!r}"))
    if vendor and not isinstance(vendor, dict) and item.default_vendor_id != vendor.id:
        out.append(("vendor", "預設廠商不同"))
    return out


def print_report(plan, rows, rules, args):
    p = print
    p("=" * 78)
    p("日曜料號匯入檢核報告")
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
        p(f"    {s:<8} → " + ("、".join(d.dept_name for d in ds) if ds else "（未指定）"))
    n_map = sum(len(plan["sheet_depts"].get(a[0]["sheet"], [])) for a in acts if a[1] == "new")
    p(f"  預計新增對照 {n_map} 筆（新料號 × 部門）")

    p(f"\n【類別主檔】預計新增 {len(plan['cat_new'])} 個細分類（既有 {len(plan['cat_by_key'])} 個）")
    for k, v in plan["cat_new"].items():
        p(f"    {''.join(k)}  {v['major_name']} / {v['mid_name']} / {v['sub_name'] or '—'}   類別名稱：{v['category_name']}")

    p(f"\n【會計科目】預計新增 {len(plan['acc_new'])} 個")
    for c_, n_ in plan["acc_new"].items():
        p(f"    {c_}  {n_}")

    p("\n【廠商】Excel 共 %d 家，已對到 %d 家" % (
        len({r['vendor'] for r in rows if r['vendor']}), len(plan["vendor_of"])))
    for line in plan.get("errors_vendor", []):
        p("   ✗", line)

    ex = [(a[0], a[2]) for a in acts if a[1] == "existing"]
    if ex:
        p(f"\n【已存在的日曜料號】{len(ex)} 筆（預設完全不動；見下方旗標說明）")
        ms = plan["map_stats"]
        p(f"  既有日曜對照 {ms['total']} 筆：未填廠商 {ms['no_vendor']}、未填會計科目 {ms['no_account']}")
        kinds = defaultdict(list)
        missing_by_sheet = Counter()
        for r, item in ex:
            vend = plan["vendor_of"].get(r["vendor"])
            for k, text in diff_existing(r, item, vend):
                kinds[k].append((item.item_code, text))
            miss = [x.dept_name for x in plan["sheet_depts"].get(r["sheet"], [])
                    if x.id not in plan["existing_maps"].get(item.id, set())]
            if miss:
                missing_by_sheet[r["sheet"]] += 1
                kinds["no_dept_map"].append((item.item_code, f"缺部門對照 {miss}"))
        labels = {
            "name_split": "品名被切成 品名＋規格（--fix-names 可合併回完整品名）",
            "name_diff": "品名真的不同（--fix-names 會改成 Excel 的品名）",
            "unit": "單位不同（不會覆蓋）",
            "price": "單價不同（--update-existing 會更新）",
            "stock": "庫存上下限不同（--update-existing 會更新）",
            "moq": "MOQ 不同（--update-existing 會更新）",
            "vendor": "預設廠商不同（--update-existing 會更新）",
            "no_dept_map": "缺部門對照（--update-existing 會補）",
        }
        for k in ("no_dept_map", "name_split", "name_diff", "unit", "price", "stock", "moq", "vendor"):
            if kinds.get(k):
                p(f"  ▸ {labels[k]}：{len(kinds[k])} 筆")
                limit = 30 if k == "name_diff" else 4
                for code_, text in kinds[k][:limit]:
                    p(f"       {code_}: {text}")
                if len(kinds[k]) > limit:
                    p(f"       ……另有 {len(kinds[k]) - limit} 筆")
        if missing_by_sheet:
            p("  缺部門對照依分頁：" + "、".join(f"{k} {v}" for k, v in missing_by_sheet.items()))
        if not kinds:
            p("  所有既有料號與 Excel 一致")

    nv = plan.get("new_vendors") or []
    if nv:
        p(f"\n【廠商主檔】自 Ragic 廠商表將新增 {len(nv)} 家日曜廠商（本地自建，代碼 {VENDOR_CODE_PREFIX}NNNN）")
        for rv in nv[:15]:
            extra = f"　同統編也在：{'、'.join(rv['also_in'])}" if rv.get("also_in") else ""
            p(f"  + {rv['name']}　統編 {rv['tax_id'] or '—'}{extra}")
        if len(nv) > 15:
            p(f"  ……另有 {len(nv) - 15} 家")
    vd = plan["vendor_diag"]
    if plan["missing_vendors"]:
        p(f"\n【廠商診斷】日曜週採廠商主檔共 {vd['ou_total']} 家" + (f"，例：{'、'.join(vd['ou_sample'])}" if vd["ou_sample"] else "（空的）"))
        if vd["elsewhere"]:
            p("  下列 Excel 廠商在別家公司的廠商主檔有，但日曜沒有：")
            for name, cos in vd["elsewhere"].items():
                p(f"    {name} → 存在於 {cos}")

    p(f"\n【警告】{len(plan['warns'])} 則")
    for w in plan["warns"]:
        p("   ⚠", w)
    p(f"\n【錯誤】{len(plan['errors']) + len(plan.get('errors_vendor', []))} 則（有錯誤不能 --apply）")
    for e in plan["errors"]:
        p("   ✗", e)


def apply_plan(db, plan, rows, args):
    from app.models.cycle_purchase_category import CyclePurchaseCategory
    from app.models.cycle_purchase_item import CyclePurchaseItem, CyclePurchaseItemMapping
    from app.models.cycle_purchase_reference import CyclePurchaseAccountCode

    from app.models.cycle_purchase_vendor import CyclePurchaseVendor

    company = plan["company"]
    stats = Counter()

    # 0) 廠商主檔：Ragic 廠商 → 日曜本地自建廠商（source_vendor_id=NULL，不會被合約同步覆蓋或刪除）
    if plan.get("new_vendors"):
        used = {c for (c,) in db.query(CyclePurchaseVendor.vendor_code).all()}
        seq = 0
        for c in used:
            if c.startswith(VENDOR_CODE_PREFIX) and c[len(VENDOR_CODE_PREFIX):].isdigit():
                seq = max(seq, int(c[len(VENDOR_CODE_PREFIX):]))
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
            notes=f"2026-10-02 日曜料號匯入（{SOURCE_LABEL}）",
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
        vendor = plan["vendor_of"].get(r["vendor"])
        acc = acc_by_code.get(r["acc_code"])
        depts = plan["sheet_depts"][r["sheet"]]

        if kind == "new":
            cat = cat_by_key[r["key"]]
            notes = "；".join(x for x in (
                f"位置：{r['location']}" if r["location"] else None,
                f"月結：{r['terms']}" if r["terms"] else None,
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
            if args.fix_names and (item.item_name or "").strip() != r["name"]:
                # 品名＋規格相同＝舊匯入切割；不同者（例：印尼→印泥錯字）以 Excel 為準（2026-11-17 Samuel 指示）
                same = _norm(f"{item.item_name or ''} {item.spec or ''}") == _norm(r["name"])
                item.item_name = r["name"]
                item.spec = None
                stats["品名合併(去除規格切割)" if same else "品名改為Excel(錯字)"] += 1
            if args.update_existing:
                item.unit_price = r["price"]
                item.max_stock = q(r["max"])
                item.min_stock = q(r["min"])
                item.moq = q(r["moq"]) or 0
                if vendor:
                    item.default_vendor_id = vendor.id
                stats["料號(更新)"] += 1
            else:
                stats["料號(已存在,未動)"] += 1
                continue

        for d in depts:
            if d.id in have:
                # 既有對照：只補空值，價格同步為 Excel（--update-existing 才會走到這裡）
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
                notes=f"2026-10-02 日曜料號匯入（{r['sheet']}）",
            ))
            stats["對照"] += 1
    db.flush()
    return stats


def main():
    ap = argparse.ArgumentParser(description="日曜（OU）週期採購料號匯入（預設只檢核預覽）")
    ap.add_argument("--excel-path", default=DEFAULT_EXCEL)
    ap.add_argument("--dept-map", action="append", metavar="分頁=部門[+部門]",
                    help="分頁對應部門，可重複；* 代表日曜全部啟用部門")
    ap.add_argument("--code-style", choices=["bare", "prefixed"], help="新料號 item_code 格式（預設自動偵測）")
    ap.add_argument("--update-existing", action="store_true", help="已存在料號：更新單價／庫存／MOQ／廠商並補部門對照")
    ap.add_argument("--no-ragic-vendors", action="store_true",
                    help="不讀 Ragic 廠商表（預設會讀 freed-management-division/20 並補建日曜缺的廠商）")
    ap.add_argument("--dump-ragic-fields", action="store_true", help="只列出 Ragic 廠商表欄位與前 3 筆內容後結束")
    ap.add_argument("--ragic-name-field", help="Ragic 廠商表「廠商名稱」欄位名（自動判斷失敗時指定）")
    ap.add_argument("--ragic-taxid-field", help="Ragic 廠商表「統一編號」欄位名")
    ap.add_argument("--vendor-alias", action="append", default=[], metavar="Excel名=廠商主檔名",
                    help="Excel 廠商名稱與廠商主檔（Ragic）名稱不同時的對照，可重複指定")
    ap.add_argument("--fix-names", action="store_true",
                    help="既有料號：品名＋規格合起來與 Excel 相同（舊匯入在第一個空白切開）者，合併回完整品名並清空規格")
    ap.add_argument("--allow-missing-vendors", action="store_true", help="廠商對不到也放行（不建議）")
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
    ragic_vendors = None
    if args.dump_ragic_fields or not args.no_ragic_vendors:
        try:
            raw = fetch_ragic_rows()
        except Exception as e:  # noqa: BLE001
            print(f"✗ 讀取 Ragic 廠商表失敗：{type(e).__name__}: {e}")
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
        print(f"Ragic 廠商表：{len(raw)} 筆、可用 {len(ragic_vendors)} 家；欄位對應 {fm}")

    sheet_depts = dict(DEFAULT_SHEET_DEPTS)
    sheet_depts.update(parse_dept_map(args.dept_map))

    from app.core.cycle_purchase_database import CyclePurchaseSessionLocal
    from app.models import (cycle_purchase_category, cycle_purchase_company,  # noqa: F401
                            cycle_purchase_item, cycle_purchase_reference, cycle_purchase_vendor)
    db = CyclePurchaseSessionLocal()
    try:
        try:
            db.get_bind().echo = False          # .env DEBUG=True 時 engine 會把每句 SQL 印出來
        except Exception:
            pass
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        print(f"連線目標：{_url(db)}")
        print(f"Excel：{args.excel_path}（{len(rows)} 筆料號、編碼原則 {len(rules)} 條）\n")
        plan = build_plan(db, rows, rules, major_name, sheet_depts, args.code_style, ragic_vendors)
        if "actions" not in plan:
            for e in plan["errors"]:
                print("✗", e)
            return 1
        plan["errors"] = x_errors + plan["errors"]
        plan["warns"] = x_warns + plan["warns"]
        print_report(plan, rows, rules, args)

        blocking = list(plan["errors"])
        if plan.get("errors_vendor") and not args.allow_missing_vendors:
            blocking += plan["errors_vendor"]
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
        stats = apply_plan(db, plan, rows, args)
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
