# -*- coding: utf-8 -*-
"""
週期採購 — 彙整單拋轉 Ragic「★週期請購單」(sheet 58) 的單元測試

涵蓋 2026-09-18 ~ 09-20 三次改版後的行為。測的都是「錯了之後 Ragic 照樣回
SUCCESS／畫面照樣有東西」那一類，肉眼很難發現：

1. `build_payload()` 欄位對應 —— 尤其「廠商要送三個地方」與「金額/項次一律不送」。
   少送子表『擬定廠商』時 Ragic 不會報錯，只是主表「全案小計／全案總計」整片空白。
2. 0920 改版：**部門與會計課目逐列帶在子表**，拆單回到只依廠商。
   表頭的部門/會科是 config 固定值，設成空字串就不送。
3. `list_ragic_pushed_documents()` 的分組鍵 —— 拆單粒度變過兩次，分組鍵少一段就會
   把不同的 Ragic 單併成一列（單號與連結靜默消失），或把舊的跨部門單據錯誤拆開。
4. 缺欄位（migration 沒跑）要翻成看得懂的 503，而不是一句 PG 的 UndefinedColumn。

DB 用記憶體 SQLite —— 這裡測的是欄位對應與分組（功能正確性），沒有併發／鎖／
原子性，符合 CLAUDE.md §0 對「什麼可以跑 SQLite」的規定。
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings                                     # noqa: E402
from app.core.cycle_purchase_database import CyclePurchaseBase           # noqa: E402
from app.models.cycle_purchase_cycle import CyclePurchaseCycle           # noqa: E402
from app.models.cycle_purchase_item import CyclePurchaseItemMapping      # noqa: E402
from app.models.cycle_purchase_reference import (                        # noqa: E402
    CyclePurchaseAccountCode, CyclePurchaseDepartment,
)
from app.models.cycle_purchase_summary import CyclePurchaseSummary       # noqa: E402
from app.models.cycle_purchase_vendor import CyclePurchaseVendor         # noqa: E402
import app.models.cycle_purchase_po          # noqa: F401,E402  （建表需要）
import app.models.cycle_purchase_request     # noqa: F401,E402
import app.models.cycle_purchase_audit       # noqa: F401,E402
import app.models.cycle_purchase_category    # noqa: F401,E402
import app.models.cycle_purchase_receiving   # noqa: F401,E402
import app.models.cycle_purchase_payment     # noqa: F401,E402

from app.services import cycle_purchase_summary_service as svc           # noqa: E402
from app.services.cycle_purchase_ragic_push import build_payload         # noqa: E402


# ───────────────────────────────────────────────────────────────────────────
# fixtures
# ───────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    CyclePurchaseBase.metadata.create_all(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield s
    finally:
        s.close()


def _seed(db):
    """一個週期、三個部門、兩家廠商、兩個會計科目、四筆料號對照。

    料號 1 在工務部掛「6238 清潔費」、在管理部掛「6241 雜項支出」——
    正是 0919 會議舉的「同一個料號依部門掛不同會科」的例子。
    """
    db.add(CyclePurchaseCycle(id=1, cycle_code="CP-ENG", cycle_name="工程備品週採",
                              frequency="weekly"))
    db.add_all([
        CyclePurchaseDepartment(id=11, company="春大直", dept_code="D-ENG",
                                dept_name="工務部", owner_user_id="u-1"),
        CyclePurchaseDepartment(id=12, company="春大直", dept_code="D-ADM",
                                dept_name="管理部", owner_user_id="u-2"),
        CyclePurchaseDepartment(id=13, company="春大直", dept_code="D-MKT",
                                dept_name="行銷部"),
    ])
    db.add_all([
        CyclePurchaseVendor(id=21, vendor_code="V-001", vendor_name="茂忠"),
        CyclePurchaseVendor(id=22, vendor_code="V-002", vendor_name="Acer商城"),
    ])
    db.add_all([
        CyclePurchaseAccountCode(id=31, code="6238", name="清潔費"),
        CyclePurchaseAccountCode(id=32, code="6241", name="雜項支出"),
    ])
    db.add_all([
        CyclePurchaseItemMapping(id=41, item_id=1, company="春大直",
                                 department_id=11, account_code_id=31),
        CyclePurchaseItemMapping(id=42, item_id=1, company="春大直",
                                 department_id=12, account_code_id=32),
        CyclePurchaseItemMapping(id=43, item_id=2, company="春大直",
                                 department_id=11, account_code_id=31),
        # 刻意留一筆沒有會科的對照，驗證「查不到就送空字串、不要爆」
        CyclePurchaseItemMapping(id=44, item_id=3, company="春大直",
                                 department_id=11, account_code_id=None),
    ])
    db.flush()


def _summary(**kw):
    base = dict(
        cycle_id=1, period_label="2026-09", company="春大直",
        item_id=1, unit="個", demand_qty=1, adjusted_qty=1,
        unit_price=Decimal("100"), status="draft",
    )
    base.update(kw)
    return CyclePurchaseSummary(**base)


# ───────────────────────────────────────────────────────────────────────────
# 1. build_payload：欄位對應
# ───────────────────────────────────────────────────────────────────────────

def _doc(**over):
    d = {
        "batch_no": "CPSUM-202609-春大直-0001",
        "cycle_name": "工程備品週採",
        "period_label": "2026-09",
        "company": "春大直",
        "vendor_id": 21, "vendor_name": "茂忠",
        "department_names": ["工務部", "管理部"],
        "header_dept": "管理",
        "account_code": "雜項購置",
        "requester": "劉佳佳",
        "purpose": "2026-09 工程備品週採 匯總請購（春大直／茂忠）",
        "applicant": "Samuel",
        "apply_date": "2026/09/20",
        "pushed_at": "2026/09/20 21:30:00",
        "portal_note": "由 Portal 週期採購模組自動產生，明細請勿手動修改",
        "lines": [
            {"item_code": "CH-E0301001", "item_name": "LED燈管",
             "department_name": "工務部", "account_name": "6238 清潔費",
             "qty": 12, "unit": "支", "note": "",
             "unit_price": Decimal("290.0000"), "amount": Decimal("3480"),
             "summary_id": 137},
            {"item_code": "CH-E0301002", "item_name": "水龍頭",
             "department_name": "管理部", "account_name": "6241 雜項支出",
             "qty": 2, "unit": "個", "note": "調整量與需求量不同",
             "unit_price": Decimal("885.5000"), "amount": Decimal("1771"),
             "summary_id": 138},
        ],
    }
    d.update(over)
    return d


def _rows(payload):
    return payload[f"_subtable_{settings.RAGIC_CP_SUBTABLE}"]


def test_payload_main_fields():
    p = build_payload(_doc())
    assert p[settings.RAGIC_CP_F_DEPT] == "管理"            # 表頭固定值，不是真部門
    assert p[settings.RAGIC_CP_F_ACCOUNT] == "雜項購置"      # 表頭固定值
    assert p[settings.RAGIC_CP_F_APPLY_DATE] == "2026/09/20"
    assert p[settings.RAGIC_CP_F_REQUESTER] == "劉佳佳"      # 必填
    assert p[settings.RAGIC_CP_F_APPLICANT] == "Samuel"
    assert p[settings.RAGIC_CP_F_VENDOR] == "茂忠"           # 主表 廠商(一)
    assert p[settings.RAGIC_CP_F_COMPANY] == "春大直"
    assert p[settings.RAGIC_CP_F_BATCH] == "CPSUM-202609-春大直-0001"
    assert p[settings.RAGIC_CP_F_PUSHED_AT] == "2026/09/20 21:30:00"


def test_payload_header_dept_and_account_can_be_switched_off():
    """Ragic 端若把表頭那兩欄的「必填」取消掉，設定改空字串就不送——
    這是**不用改程式**就能切換的設計，所以要有測試釘住。"""
    p = build_payload(_doc(header_dept="", account_code=""))
    assert settings.RAGIC_CP_F_DEPT not in p
    assert settings.RAGIC_CP_F_ACCOUNT not in p


def test_payload_never_sends_formula_or_autogen_fields():
    """小計／稅／總計／項次／編號一律不送——它們是 Ragic 的公式與自動編號，
    Portal 送死值會在 Ragic 端有人改過之後變成錯的（見 push 檔頭）。

    ⚠️ 2026-09-20 起「金額」**不在這個名單裡了**：Ragic 端的 D5*G5 公式已經拿掉
    （公式欄寫不進值，部門小計列的金額就放不進去），改由 Portal 逐列送。
    """
    p = build_payload(_doc())
    for fid in (settings.RAGIC_CP_F_DOC_NO, settings.RAGIC_CP_F_SUBTOTAL,
                settings.RAGIC_CP_F_TAX, settings.RAGIC_CP_F_TOTAL,
                settings.RAGIC_CP_F_GRAND_SUB, settings.RAGIC_CP_F_GRAND_TOTAL):
        assert fid not in p
    for row in _rows(p).values():
        assert settings.RAGIC_CP_SF_SEQ not in row        # 項次是 $SEQ
        # 本月預算／上月累計預算是人工填的，Portal 不碰
        assert settings.RAGIC_CP_SF_BUDGET_M not in row
        assert settings.RAGIC_CP_SF_BUDGET_ACC not in row


def test_payload_sends_amount_per_line():
    """金額改由 Portal 算並逐列送（Ragic 的 D5*G5 公式已拿掉）。"""
    doc = _doc()
    doc["lines"][0]["qty"] = 12
    doc["lines"][0]["unit_price"] = Decimal("35")
    doc["lines"][0]["amount"] = Decimal("420")
    p = build_payload(doc)
    first = _rows(p)[max(_rows(p), key=lambda k: abs(int(k)))]
    assert first[settings.RAGIC_CP_SF_AMOUNT] == "420"


def test_payload_vendor_is_sent_to_all_three_places():
    """主表廠商(一) ＋ 子表擬定廠商 ＋ 子表勾選=Yes。
    少了子表那兩欄，Ragic 的「單價(選定)/金額(選定)」比對不到廠商，
    主表「全案小計／全案總計」會是空的，而 API 照樣回 SUCCESS。"""
    p = build_payload(_doc())
    assert p[settings.RAGIC_CP_F_VENDOR] == "茂忠"
    for row in _rows(p).values():
        assert row[settings.RAGIC_CP_SF_VENDOR] == "茂忠"
        assert row[settings.RAGIC_CP_SF_CHOSEN] == "Yes"


def test_payload_carries_per_line_department_and_account():
    """0920 改版的核心：部門與會計課目**逐列**帶在子表上，
    一張單因此可以橫跨多個部門，不必再依部門拆單。"""
    p = build_payload(_doc())
    rows = _rows(p)
    assert rows["-2"][settings.RAGIC_CP_SF_DEPT] == "工務部"
    assert rows["-2"][settings.RAGIC_CP_SF_ACCOUNT] == "6238 清潔費"
    assert rows["-1"][settings.RAGIC_CP_SF_DEPT] == "管理部"
    assert rows["-1"][settings.RAGIC_CP_SF_ACCOUNT] == "6241 雜項支出"


def test_payload_subtable_keys_are_reverse_ordered():
    """Ragic 是「負數 key 絕對值大的排前面」，第一列要拿到最大的絕對值，
    否則明細在 Ragic 上整個反序。"""
    p = build_payload(_doc())
    rows = _rows(p)
    assert set(rows.keys()) == {"-2", "-1"}
    assert rows["-2"][settings.RAGIC_CP_SF_ITEM_NAME] == "LED燈管"   # 第一列
    assert rows["-1"][settings.RAGIC_CP_SF_ITEM_NAME] == "水龍頭"    # 第二列


def test_payload_carries_item_code_and_summary_id():
    """料號與 Portal 彙整列 ID 是 Ragic 端新增的追蹤欄位，對帳靠它們。"""
    p = build_payload(_doc())
    rows = _rows(p)
    assert rows["-2"][settings.RAGIC_CP_SF_ITEM_CODE] == "CH-E0301001"
    assert rows["-2"][settings.RAGIC_CP_SF_SUMMARY_ID] == "137"


def test_payload_decimal_is_not_zero_padded():
    """Decimal('290.0000') 直接 str() 會變成 '290.0000'，Ragic 顯示會帶一串零。"""
    p = build_payload(_doc())
    rows = _rows(p)
    assert rows["-2"][settings.RAGIC_CP_SF_PRICE] == "290"
    assert rows["-1"][settings.RAGIC_CP_SF_PRICE] == "885.5"


# ───────────────────────────────────────────────────────────────────────────
# 2. 會計課目的來源：料號對照表（公司＋部門＋料號）
# ───────────────────────────────────────────────────────────────────────────

def test_account_name_follows_company_department_item(db):
    """0919 會議的核心裁示：同一個料號在不同部門掛不同會科。
    來源是 `cycle_purchase_item_mappings`（唯一鍵含 department_id），
    彙整當下已經把用到的那一列存進 item_mapping_id，這裡跟著走。"""
    _seed(db)
    eng = _summary(id=101, item_id=1, vendor_id=21, department_id=11,
                   item_mapping_id=41, item_code="A-1", item_name="捲筒衛生紙")
    adm = _summary(id=102, item_id=1, vendor_id=21, department_id=12,
                   item_mapping_id=42, item_code="A-1", item_name="捲筒衛生紙")
    none_acct = _summary(id=103, item_id=3, vendor_id=21, department_id=11,
                         item_mapping_id=44, item_code="A-3", item_name="沒設會科的料號")
    db.add_all([eng, adm, none_acct])
    db.flush()

    for r in (eng, adm, none_acct):
        svc._attach_summary_display_fields(db, r)

    assert eng.account_name == "6238 清潔費"
    assert adm.account_name == "6241 雜項支出"
    # 對照上沒設會科 → None，build_payload 會送空字串，不該爆
    assert none_acct.account_name is None


# ───────────────────────────────────────────────────────────────────────────
# 3. _build_vendor_documents：只依廠商拆單（0920 改回）
# ───────────────────────────────────────────────────────────────────────────

def _row(vendor_id, vendor_name, dept_id, dept_name, item_code, owner=None, acct=None):
    r = _summary(vendor_id=vendor_id, department_id=dept_id,
                 item_code=item_code, item_name=item_code)
    r.vendor_name = vendor_name
    r.department_name = dept_name
    r.dept_owner_user_id = owner
    r.account_name = acct
    r.id = abs(hash((vendor_id, dept_id, item_code))) % 100000
    return r


def _build(rows, owner_names=None):
    return svc._build_vendor_documents(
        rows, batch_no="B-1", cycle_name="工程備品週採", period_label="2026-09",
        company="春大直", pushed_at_text="2026/09/20 21:30:00",
        apply_date_text="2026/09/20", owner_names=owner_names or {},
    )


def test_documents_split_by_vendor_only():
    """⚠️ 2026-09-18~19 曾經是「廠商＋部門」拆單（被 Ragic 主表部門必填逼出來的），
    0920 部門下放到子表之後改回只依廠商——同一家廠商跨兩個部門要合成**一張單**。"""
    rows = [
        _row(21, "茂忠", 11, "工務部", "A-1", owner="u-1", acct="6238 清潔費"),
        _row(21, "茂忠", 12, "管理部", "A-2", owner="u-2", acct="6241 雜項支出"),
        _row(22, "Acer商城", 11, "工務部", "A-3", owner="u-1"),
    ]
    docs = _build(rows, {"u-1": "劉佳佳", "u-2": "王小明"})

    assert len(docs) == 2                       # 兩家廠商 → 兩張單，不是三張
    by_vendor = {d["vendor_id"]: d for d in docs}
    # 0920 起每個部門後面會多一列小計，所以這裡要把明細列與小計列分開看
    detail = [l for l in by_vendor[21]["lines"] if not l.get("is_subtotal")]
    assert len(detail) == 2                     # 茂忠那張含兩個部門的明細
    assert by_vendor[21]["department_names"] == ["工務部", "管理部"]
    assert [l["department_name"] for l in detail] == ["工務部", "管理部"]
    assert [l["account_name"] for l in detail] == ["6238 清潔費", "6241 雜項支出"]
    # 表頭一律是 config 的固定值
    for d in docs:
        assert d["header_dept"] == settings.RAGIC_CP_SUMMARY_HEADER_DEPT
        assert d["account_code"] == settings.RAGIC_CP_SUMMARY_ACCOUNT_CODE


def test_requester_single_department_uses_owner():
    rows = [_row(21, "茂忠", 11, "工務部", "A-1", owner="u-1")]
    assert _build(rows, {"u-1": "劉佳佳"})[0]["requester"] == "劉佳佳"


def test_requester_falls_back_when_document_spans_departments():
    """跨部門時沒有單一承辦人可言，硬挑一個會讓其他部門的人以為單子是別人開的，
    所以退回申請人。"""
    rows = [
        _row(21, "茂忠", 11, "工務部", "A-1", owner="u-1"),
        _row(21, "茂忠", 12, "管理部", "A-2", owner="u-2"),
    ]
    docs = _build(rows, {"u-1": "劉佳佳", "u-2": "王小明"})
    assert docs[0]["requester"] == settings.RAGIC_CP_SUMMARY_APPLICANT


def test_requester_falls_back_when_department_has_no_owner():
    rows = [_row(21, "茂忠", 13, "行銷部", "A-1", owner=None)]
    assert _build(rows)[0]["requester"] == settings.RAGIC_CP_SUMMARY_APPLICANT


# ───────────────────────────────────────────────────────────────────────────
# 4. list_ragic_pushed_documents：「已彙整 Ragic 請購單」TAB 的分組
# ───────────────────────────────────────────────────────────────────────────

def test_pushed_docs_split_by_ragic_record_id(db):
    """分組鍵是 (批次號, 廠商, Ragic 單號)。同批次同廠商若真的是兩張 Ragic 單，
    少了 ragic_record_id 就會併成一列，其中一張的單號與連結靜默消失。"""
    _seed(db)
    now = datetime(2026, 9, 20, 21, 30)
    db.add_all([
        _summary(id=201, item_id=1, vendor_id=21, department_id=11, item_code="A-1",
                 item_name="A-1", ragic_pushed=True, ragic_push_batch_no="B-1",
                 ragic_pushed_at=now, ragic_record_id="樂管購20260900001",
                 ragic_record_url="https://ap12.ragic.com/x/58/0"),
        _summary(id=202, item_id=1, vendor_id=21, department_id=12, item_code="A-2",
                 item_name="A-2", ragic_pushed=True, ragic_push_batch_no="B-1",
                 ragic_pushed_at=now, ragic_record_id="樂管購20260900002",
                 ragic_record_url="https://ap12.ragic.com/x/58/1"),
    ])
    db.flush()
    docs = svc.list_ragic_pushed_documents(db)
    assert len(docs) == 2
    assert {d["ragic_record_id"] for d in docs} == {"樂管購20260900001", "樂管購20260900002"}


def test_pushed_docs_one_record_across_departments_stays_one_row(db):
    """0920 之後這是**常態**（一張單橫跨多部門），0920 之前的 sheet 57 舊資料也是。
    分組鍵刻意不用 department_id，就是為了不把這種單據錯誤拆成好幾列。"""
    _seed(db)
    now = datetime(2026, 9, 20, 10, 0)
    db.add_all([
        _summary(id=211, item_id=1, vendor_id=21, department_id=11, item_code="A-1",
                 item_name="A-1", ragic_pushed=True, ragic_push_batch_no="B-0",
                 ragic_pushed_at=now, ragic_record_id="樂管購20260900003",
                 ragic_record_url="https://ap12.ragic.com/x/58/2"),
        _summary(id=212, item_id=1, vendor_id=21, department_id=12, item_code="A-2",
                 item_name="A-2", ragic_pushed=True, ragic_push_batch_no="B-0",
                 ragic_pushed_at=now, ragic_record_id="樂管購20260900003",
                 ragic_record_url="https://ap12.ragic.com/x/58/2"),
    ])
    db.flush()
    docs = svc.list_ragic_pushed_documents(db)
    assert len(docs) == 1
    assert docs[0]["item_count"] == 2
    assert sorted(docs[0]["department_names"]) == ["工務部", "管理部"]


def test_pushed_docs_ignore_unpushed_rows(db):
    _seed(db)
    db.add(_summary(id=301, vendor_id=21, department_id=11, item_code="A-1", item_name="A-1"))
    db.flush()
    assert svc.list_ragic_pushed_documents(db) == []


# ───────────────────────────────────────────────────────────────────────────
# 5. push_summary_to_ragic 整條（mock 掉真正的 HTTP）
# ───────────────────────────────────────────────────────────────────────────

def test_push_blocks_unpushable_rows_and_sends_the_rest(db):
    _seed(db)
    db.add_all([
        _summary(id=401, item_id=1, vendor_id=21, department_id=11, item_mapping_id=41,
                 item_code="A-1", item_name="A-1"),
        _summary(id=402, item_id=2, vendor_id=21, department_id=12, item_mapping_id=42,
                 item_code="A-2", item_name="A-2"),
        _summary(id=403, item_id=3, vendor_id=None, department_id=11,
                 item_code="A-3", item_name="A-3"),                      # 缺供應商
        _summary(id=404, item_id=4, vendor_id=21, department_id=11,
                 item_code="A-4", item_name="A-4", unit_price=None),     # 缺單價
        _summary(id=405, item_id=5, vendor_id=21, department_id=None,
                 item_code="A-5", item_name="A-5"),                      # 歷史列沒部門
    ])
    db.flush()

    captured = []

    def fake_push(document):
        captured.append(document)
        return {"ragic_record_id": "0", "ragic_no": "樂管購20260900001",
                "ragic_record_url": "https://ap12.ragic.com/x/58/0",
                "is_stub": False, "message": "ok"}

    original = svc.cycle_purchase_ragic_push.push_summary_document
    svc.cycle_purchase_ragic_push.push_summary_document = fake_push
    try:
        result = svc.push_summary_to_ragic(db, 1, "2026-09", "春大直")
    finally:
        svc.cycle_purchase_ragic_push.push_summary_document = original

    reasons = {r["item_code"]: r["reason"] for r in result["not_pushed"]}
    assert set(reasons) == {"A-3", "A-4", "A-5"}
    assert "供應商" in reasons["A-3"]
    assert "單價" in reasons["A-4"]
    assert "部門別" in reasons["A-5"]

    # 兩筆可推的都是同一家廠商 → **一張單、兩列明細**（0920 起不再依部門拆）
    assert len(captured) == 1
    doc = captured[0]
    detail = [l for l in doc["lines"] if not l.get("is_subtotal")]
    assert len(detail) == 2
    assert result["pushed_count"] == 2
    assert sorted(l["department_name"] for l in detail) == ["工務部", "管理部"]
    # 會科逐列，來自料號對照表（公司＋部門＋料號）
    assert sorted(l["account_name"] for l in detail) == ["6238 清潔費", "6241 雜項支出"]
    # 回傳給前端的那一列要看得出涵蓋哪些部門
    assert result["documents"][0]["department_name"] == "工務部、管理部"


# ───────────────────────────────────────────────────────────────────────────
# 6. 回傳結構真的帶得到單號與連結（schema 漏一欄畫面就永遠空白，API 不報錯）
# ───────────────────────────────────────────────────────────────────────────

def test_response_schemas_carry_ragic_no_and_url(db):
    from app.schemas.cycle_purchase_summary import RagicPushedDocOut, SummaryOut

    _seed(db)
    now = datetime(2026, 9, 20, 21, 30)
    db.add(_summary(id=501, item_id=1, vendor_id=21, department_id=11, item_mapping_id=41,
                    item_code="A-1", item_name="A-1",
                    ragic_pushed=True, ragic_push_batch_no="B-1", ragic_pushed_at=now,
                    ragic_record_id="樂管購20260900001",
                    ragic_record_url="https://ap12.ragic.com/x/58/0"))
    db.flush()

    doc = RagicPushedDocOut(**svc.list_ragic_pushed_documents(db)[0])
    assert doc.ragic_record_id == "樂管購20260900001"
    assert doc.ragic_record_url == "https://ap12.ragic.com/x/58/0"

    row = svc.list_summary(db, cycle_id=1, period_label="2026-09", company="春大直")[0]
    out = SummaryOut.model_validate(row)
    assert out.ragic_record_id == "樂管購20260900001"
    assert out.ragic_record_url == "https://ap12.ragic.com/x/58/0"
    assert out.ragic_pushed_at == now


# ───────────────────────────────────────────────────────────────────────────
# 7. migration 沒跑時要講人話
# ───────────────────────────────────────────────────────────────────────────

def test_schema_guard_turns_missing_column_into_actionable_503():
    from fastapi import HTTPException
    from app.routers import cycle_purchase_summary as router_mod

    def boom():
        raise RuntimeError(
            '(psycopg.errors.UndefinedColumn) column '
            'cycle_purchase_summary.ragic_record_url does not exist'
        )

    with pytest.raises(HTTPException) as ei:
        router_mod._handle(boom)
    assert ei.value.status_code == 503          # 不是 422：使用者換輸入也沒用
    detail = ei.value.detail
    assert "cycle_purchase_summary.ragic_record_url" in detail
    assert "cpragicurl" in detail               # 要說是哪一支 migration
    assert "重啟後端" in detail                   # 順序反過來照樣壞
    assert "不是操作問題" in detail                # feedback_stale_backend_symptom


def test_schema_guard_does_not_swallow_other_errors():
    from app.routers import cycle_purchase_summary as router_mod

    def boom():
        raise ValueError("完全無關的錯")

    with pytest.raises(ValueError):
        router_mod._handle(boom)


def test_service_error_still_becomes_422():
    from fastapi import HTTPException
    from app.routers import cycle_purchase_summary as router_mod

    def boom():
        raise svc.SummaryServiceError("這個週期＋期別＋公司範圍內沒有彙整列")

    with pytest.raises(HTTPException) as ei:
        router_mod._handle(boom)
    assert ei.value.status_code == 422


# ───────────────────────────────────────────────────────────────────────────
# 5. 部門小計列（2026-09-20 新增）
#
# 版型（Samuel 指定）：同一個部門的品項連在一起，最後一筆下面插一列小計。
#     1  CH-G0201001  A3影印紙   2 包  160   320   管理部
#     2  CH-G0201002  A4影印紙   5 包   78   390   管理部
#     3  CH-G0202001  阿波羅紙   3 包   60   180   管理部
#     4                                    890   管理部 小計
#
# ⚠️ 前提是**排序**。改版前 lines 照彙整列查出來的順序 append，同部門的品項不
#    保證連在一起，小計列就會插在莫名其妙的位置。
# ───────────────────────────────────────────────────────────────────────────

def _priced_row(vendor_id, vendor_name, dept_id, dept_name, item_code, qty, price, acct=None):
    r = _row(vendor_id, vendor_name, dept_id, dept_name, item_code, acct=acct)
    r.adjusted_qty = qty
    r.unit_price = Decimal(str(price))
    return r


def test_lines_are_sorted_by_department_then_item_code():
    """小計列要插得對，前提是同部門的明細連在一起。

    刻意把輸入順序打散（管理部、工務部、管理部、工務部），輸出必須重新排好。
    """
    rows = [
        _priced_row(21, "茂忠", 12, "管理部", "B-2", 1, 10),
        _priced_row(21, "茂忠", 11, "工務部", "A-2", 1, 10),
        _priced_row(21, "茂忠", 12, "管理部", "B-1", 1, 10),
        _priced_row(21, "茂忠", 11, "工務部", "A-1", 1, 10),
    ]
    lines = _build(rows)[0]["lines"]
    detail = [(l["department_name"], l["item_code"]) for l in lines if not l.get("is_subtotal")]
    assert detail == [("工務部", "A-1"), ("工務部", "A-2"), ("管理部", "B-1"), ("管理部", "B-2")]


def test_one_subtotal_row_per_department_with_the_right_total():
    """三個料號同一個部門 → 三列明細 ＋ 一列小計，金額是該部門的總和。"""
    rows = [
        _priced_row(21, "茂忠", 12, "管理部", "G-1", 2, 160),   # 320
        _priced_row(21, "茂忠", 12, "管理部", "G-2", 5, 78),    # 390
        _priced_row(21, "茂忠", 12, "管理部", "G-3", 3, 60),    # 180
    ]
    lines = _build(rows)[0]["lines"]
    assert len(lines) == 4
    assert [l.get("is_subtotal", False) for l in lines] == [False, False, False, True]
    sub = lines[-1]
    assert sub["department_name"] == "管理部 小計"
    assert sub["amount"] == Decimal("890")
    # 小計列不可以帶品項欄位——它不是一個品項
    for key in ("item_code", "item_name", "qty", "unit", "unit_price", "account_name", "summary_id"):
        assert key not in sub


def test_each_department_gets_its_own_subtotal():
    rows = [
        _priced_row(21, "茂忠", 11, "工務部", "A-1", 2, 50),    # 100
        _priced_row(21, "茂忠", 11, "工務部", "A-2", 1, 25),    # 25
        _priced_row(21, "茂忠", 12, "管理部", "B-1", 3, 10),    # 30
    ]
    lines = _build(rows)[0]["lines"]
    subs = [(l["department_name"], l["amount"]) for l in lines if l.get("is_subtotal")]
    assert subs == [("工務部 小計", Decimal("125")), ("管理部 小計", Decimal("30"))]
    # 小計列的位置：各自跟在自己部門最後一筆的後面
    assert [l.get("is_subtotal", False) for l in lines] == [False, False, True, False, True]


def test_rows_without_a_department_get_no_subtotal():
    """歷史資料的 department_name 可能是空的。

    幫一群「未分部門」的列算小計沒有意義，反而會讓人以為那是某個部門的數字。
    """
    rows = [
        _priced_row(21, "茂忠", 12, "管理部", "B-1", 1, 100),
        _priced_row(21, "茂忠", None, "", "X-1", 1, 100),
    ]
    lines = _build(rows)[0]["lines"]
    subs = [l["department_name"] for l in lines if l.get("is_subtotal")]
    assert subs == ["管理部 小計"]          # 只有一列，不含未分部門的
    assert lines[-1]["item_code"] == "X-1"  # 未分部門的排最後，後面沒有小計列


def test_subtotal_row_payload_only_carries_department_and_amount():
    """小計列在 Ragic 只填部門與金額（Samuel 裁示）。

    ⚠️ 其他欄位一定要留空 —— Ragic 端是靠「這一列的料號是空的」把小計列排除在
    小計／全案小計的加總之外，送了料號就會被重複加總。
    """
    doc = _doc()
    doc["lines"] = [
        {"item_code": "G-1", "item_name": "A3影印紙", "department_name": "管理部",
         "account_name": "621202 文具用品-用品", "qty": 2, "unit": "包", "note": "",
         "unit_price": Decimal("160"), "amount": Decimal("320"), "summary_id": 1},
        {"is_subtotal": True, "department_name": "管理部 小計", "amount": Decimal("320")},
    ]
    rows = _rows(build_payload(doc))
    sub = rows[min(rows, key=lambda k: abs(int(k)))]      # 絕對值最小的＝最後一列
    assert sub == {
        settings.RAGIC_CP_SF_DEPT: "管理部 小計",
        settings.RAGIC_CP_SF_AMOUNT: "320",
    }
    assert settings.RAGIC_CP_SF_ITEM_CODE not in sub      # 料號是 Ragic 排除小計列的依據
    assert settings.RAGIC_CP_SF_CHOSEN not in sub
    assert settings.RAGIC_CP_SF_VENDOR not in sub


def test_subtotal_rows_do_not_inflate_the_pushed_count():
    """回傳的 line_count／pushed_count 是「彙整列筆數」，不含小計列。

    算進去的話畫面上的筆數會比實際彙整列多，也跟 TAB 的 item_count 對不起來。
    """
    rows = [
        _priced_row(21, "茂忠", 12, "管理部", "G-1", 2, 160),
        _priced_row(21, "茂忠", 12, "管理部", "G-2", 5, 78),
        _priced_row(21, "茂忠", 11, "工務部", "A-1", 1, 10),
    ]
    doc = _build(rows)[0]
    assert len(doc["lines"]) == 5                                    # 3 明細 ＋ 2 小計
    detail = [l for l in doc["lines"] if not l.get("is_subtotal")]
    assert len(detail) == 3


# ───────────────────────────────────────────────────────────────────────────
# 6. 廠商防呆：拋轉前先跟 Ragic 核對廠商名稱（2026-09-20 新增）
#
# ⚠️ 實測踩到：主表「廠商(一)」是連結到「廠商資料表」的 L 型欄位，只認**完全
#    相符**的既有名稱。Portal 送「北金」而 Ragic 只認「北金文具印刷有限公司」，
#    Ragic **靜默丟掉那一欄、照樣回 SUCCESS**，從 API 回應完全看不出來。
# ───────────────────────────────────────────────────────────────────────────

from app.services import cycle_purchase_ragic_push as push_mod       # noqa: E402


def test_vendor_rejection_reason_accepts_an_exact_match():
    assert push_mod.vendor_rejection_reason("北金文具印刷有限公司",
                                            {"北金文具印刷有限公司"}) is None


def test_vendor_rejection_reason_hints_at_the_full_name():
    """簡稱對不上時要指出 Ragic 那邊的寫法，不然使用者不知道要改成什麼。"""
    reason = push_mod.vendor_rejection_reason("北金", {"北金文具印刷有限公司", "巨沅實業有限公司"})
    assert reason is not None
    assert "北金文具印刷有限公司" in reason
    assert "供應商主檔" in reason        # 要告訴他去哪裡修


def test_vendor_rejection_reason_when_ragic_has_nothing_like_it():
    reason = push_mod.vendor_rejection_reason("碩維", {"北金文具印刷有限公司"})
    assert reason is not None
    assert "完全找不到" in reason
    assert "Ragic 廠商資料表建檔" in reason


def test_vendor_check_is_skipped_when_the_list_cannot_be_fetched():
    """⚠️ 取不到清單（None）≠ 沒有任何廠商（空集合）。

    兩者混為一談的話，Ragic 一時連不上就會把**每一家**都判成對不上，
    整批拋轉全滅 —— 比原本的行為更糟。這是刻意的 fail open。
    """
    assert push_mod.vendor_rejection_reason("北金", None) is None
    # 對照組：空集合代表「真的查到了，而且一家都沒有」→ 要擋
    assert push_mod.vendor_rejection_reason("北金", set()) is not None


def test_empty_vendor_name_is_rejected():
    assert push_mod.vendor_rejection_reason("", {"北金文具印刷有限公司"}) == "缺供應商"
    assert push_mod.vendor_rejection_reason(None, {"北金文具印刷有限公司"}) == "缺供應商"


def test_push_puts_unknown_vendors_into_not_pushed_instead_of_sending_them(db):
    """對不上的廠商整張單擋下來列進 not_pushed，認得的照常送。"""
    _seed(db)
    db.add(CyclePurchaseVendor(id=23, vendor_code="V-23", vendor_name="碩維"))
    db.add_all([
        _summary(id=501, item_id=1, vendor_id=21, department_id=11, item_mapping_id=41,
                 item_code="OK-1", item_name="OK-1"),
        _summary(id=502, item_id=2, vendor_id=23, department_id=11, item_mapping_id=41,
                 item_code="NG-1", item_name="NG-1"),
    ])
    db.flush()

    captured = []

    def fake_push(document):
        captured.append(document)
        return {"ragic_record_id": "0", "ragic_no": "樂管購20260900001",
                "ragic_record_url": "https://ap12.ragic.com/x/58/0",
                "is_stub": False, "message": "ok"}

    orig_push = svc.cycle_purchase_ragic_push.push_summary_document
    orig_fetch = svc.cycle_purchase_ragic_push.fetch_accepted_vendor_names
    svc.cycle_purchase_ragic_push.push_summary_document = fake_push
    # Ragic 只認得「茂忠」，不認得「碩維」
    svc.cycle_purchase_ragic_push.fetch_accepted_vendor_names = lambda *a, **k: {"茂忠"}
    try:
        result = svc.push_summary_to_ragic(db, 1, "2026-09", "春大直")
    finally:
        svc.cycle_purchase_ragic_push.push_summary_document = orig_push
        svc.cycle_purchase_ragic_push.fetch_accepted_vendor_names = orig_fetch

    # 認得的那家有送出去，不認得的那家一列都沒送
    assert len(captured) == 1
    assert captured[0]["vendor_name"] == "茂忠"
    blocked = {r["item_code"]: r["reason"] for r in result["not_pushed"]}
    assert "NG-1" in blocked
    assert "碩維" in blocked["NG-1"]
    assert "OK-1" not in blocked
    assert result["pushed_count"] == 1


def test_push_raises_when_no_vendor_is_recognised(db):
    """全部對不上時要講清楚怎麼修，不是丟一句「沒有可拋轉的列」。"""
    _seed(db)
    db.add(_summary(id=511, item_id=1, vendor_id=21, department_id=11,
                    item_mapping_id=41, item_code="NG-9", item_name="NG-9"))
    db.flush()

    orig_fetch = svc.cycle_purchase_ragic_push.fetch_accepted_vendor_names
    svc.cycle_purchase_ragic_push.fetch_accepted_vendor_names = lambda *a, **k: {"別家公司"}
    try:
        with pytest.raises(svc.SummaryServiceError) as e:
            svc.push_summary_to_ragic(db, 1, "2026-09", "春大直")
    finally:
        svc.cycle_purchase_ragic_push.fetch_accepted_vendor_names = orig_fetch
    assert "對應合約廠商" in str(e.value)


# ───────────────────────────────────────────────────────────────────────────
# 7. 空殼防呆看的是「全案小計」，不是殘留的「小計」（2026-09-20）
#
# ⚠️ 這個防呆壞掉過兩次，而且兩次都是**靜默**的：
#    1. 舊的「小計 1020838」被刪掉後，程式還指著它 → record.get() 永遠 None
#       → **每推一張單都誤報**「小計是空的」。
#    2. 若改指到還掛在表單上的殘留「小計 1020840」（公式 `L5`，恆為 "0"），
#       "0" 是 truthy → **永遠不會示警**，防呆等於失效。
#    所以錨點必須是全案小計（1020810 = O5），它才真的反映推上去的金額。
# ───────────────────────────────────────────────────────────────────────────

class _FakeResp:
    status_code = 200

    def __init__(self, record):
        self._record = record

    def json(self):
        return {"status": "SUCCESS", "ragicId": 7, "data": self._record}


def _push_with_record(monkeypatch, caplog, record):
    monkeypatch.setattr(settings, "RAGIC_CP_SUMMARY_ENABLED", True)
    monkeypatch.setattr(push_mod.httpx, "post", lambda *a, **k: _FakeResp(record))
    with caplog.at_level("WARNING"):
        out = push_mod.push_summary_document(_doc())
    return out, caplog.text


def test_stale_subtotal_zero_does_not_silence_the_empty_shell_check(monkeypatch, caplog):
    """殘留的「小計」回 "0"、而全案小計是空的 → 必須示警。

    這一條就是「看錯欄位會被 "0" 騙過去」的回歸測試。
    """
    _, log = _push_with_record(monkeypatch, caplog, {
        settings.RAGIC_CP_F_DOC_NO: "樂管購20260900009",
        settings.RAGIC_CP_F_SUBTOTAL: "0",       # 殘留欄位，恆為 0
        settings.RAGIC_CP_F_GRAND_SUB: "",       # 真正該看的：空的
        settings.RAGIC_CP_F_GRAND_TOTAL: "",
    })
    assert "全案小計" in log
    assert "擬定廠商" in log        # 要指出最常見的原因


def test_no_warning_when_grand_sub_has_a_value(monkeypatch, caplog):
    """全案小計有值就不該示警 —— 即使殘留的「小計」是 0。

    沒有這一條的話，防呆會在一切正常時每張單都叫，很快就沒有人理它。
    """
    _, log = _push_with_record(monkeypatch, caplog, {
        settings.RAGIC_CP_F_DOC_NO: "樂管購20260900010",
        settings.RAGIC_CP_F_SUBTOTAL: "0",
        settings.RAGIC_CP_F_GRAND_SUB: "1020",
        settings.RAGIC_CP_F_GRAND_TOTAL: "1071",
    })
    assert "⚠️" not in log


def test_warns_when_grand_total_is_missing_but_sub_is_there(monkeypatch, caplog):
    _, log = _push_with_record(monkeypatch, caplog, {
        settings.RAGIC_CP_F_DOC_NO: "樂管購20260900011",
        settings.RAGIC_CP_F_GRAND_SUB: "1020",
        settings.RAGIC_CP_F_GRAND_TOTAL: "",
    })
    assert "全案總計" in log


def test_config_points_at_fields_that_still_exist_in_ragic():
    """2026-09-20 Ragic 整理金額區後的欄位代號，釘住避免又指到被刪掉的欄位。"""
    assert settings.RAGIC_CP_F_GRAND_SUB == "1020810"     # 全案小計 = O5
    assert settings.RAGIC_CP_F_TAX == "1020846"           # 營業稅
    assert settings.RAGIC_CP_F_GRAND_TOTAL == "1020852"   # 全案總計
    # 舊的那一組已經在 Ragic 被刪除，不可以再出現
    for dead in ("1020838", "1020843", "1020849"):
        assert settings.RAGIC_CP_F_GRAND_SUB != dead
        assert settings.RAGIC_CP_F_TAX != dead
        assert settings.RAGIC_CP_F_GRAND_TOTAL != dead
        assert settings.RAGIC_CP_F_SUBTOTAL != dead
