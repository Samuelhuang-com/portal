# -*- coding: utf-8 -*-
"""
週期採購 — 料號對照表「一個料號 ＝ 一個公司 ＋ 多個部門 ＋ 多個科目」的防呆測試

2026-09-20（0919 會議 N1）：料號主檔改成可以在同一個畫面編多列對照，
「公司＋部門」撞號從罕見變成日常操作，所以 service 層要先明確擋下來。

⚠️ 唯一鍵刻意是「公司＋部門」，**不含會計科目**（Samuel 裁示）：
請購單建立明細時是用 (公司, 部門) 去抓這筆對照來帶科目與單價
（request_service.add_request_item 的 .first()），同一個部門若能掛兩個科目，
那裡就會隨機挑一筆。這幾項測試就是把這個約束釘住。

DB 用記憶體 SQLite —— 測的是查詢條件與防呆分支（功能正確性），沒有併發／鎖，
符合 CLAUDE.md §0 對「什麼可以跑 SQLite」的規定。
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.cycle_purchase_database import CyclePurchaseBase           # noqa: E402
from app.models.cycle_purchase_item import (                             # noqa: E402
    CyclePurchaseItem, CyclePurchaseItemMapping,
)
from app.models.cycle_purchase_reference import (                        # noqa: E402
    CyclePurchaseAccountCode, CyclePurchaseDepartment,
)
import app.models.cycle_purchase_vendor      # noqa: F401,E402  （建表需要）
import app.models.cycle_purchase_category    # noqa: F401,E402
import app.models.cycle_purchase_cycle       # noqa: F401,E402
import app.models.cycle_purchase_request     # noqa: F401,E402
import app.models.cycle_purchase_summary     # noqa: F401,E402
import app.models.cycle_purchase_po          # noqa: F401,E402
import app.models.cycle_purchase_receiving   # noqa: F401,E402
import app.models.cycle_purchase_payment     # noqa: F401,E402
import app.models.cycle_purchase_audit       # noqa: F401,E402

from app.schemas.cycle_purchase_item import (                            # noqa: E402
    ItemMappingCreate, ItemMappingUpdate,
)
from app.services import cycle_purchase_service as svc                   # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    CyclePurchaseBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def fixtures(db):
    """一個料號、一家公司的兩個部門、兩個會計科目 —— 0919 會議舉的那個例子。"""
    item = CyclePurchaseItem(item_code="CH-0105054", item_name="五月花大捲筒衛生紙")
    d_admin = CyclePurchaseDepartment(company="春大直", dept_code="ADM", dept_name="管理部")
    d_mkt = CyclePurchaseDepartment(company="春大直", dept_code="MKT", dept_name="行銷部")
    a_clean = CyclePurchaseAccountCode(code="6238", name="清潔費")
    a_misc = CyclePurchaseAccountCode(code="6241", name="雜項支出")
    db.add_all([item, d_admin, d_mkt, a_clean, a_misc])
    db.flush()
    return {
        "item": item, "admin": d_admin, "mkt": d_mkt,
        "clean": a_clean, "misc": a_misc,
    }


def _create(db, item_id, company, dept_id, account_id=None, price=None):
    return svc.create_item_mapping(
        db, item_id,
        ItemMappingCreate(
            company=company, department_id=dept_id,
            account_code_id=account_id, original_unit_price=price,
        ),
    )


# ── 這是 N1 要的行為：同一料號、同一公司、不同部門、不同科目 ────────────────

def test_same_item_same_company_different_departments_is_allowed(db, fixtures):
    f = fixtures
    m1 = _create(db, f["item"].id, "春大直", f["admin"].id, f["clean"].id, Decimal("120"))
    m2 = _create(db, f["item"].id, "春大直", f["mkt"].id, f["misc"].id, Decimal("120"))
    assert m1.id != m2.id
    rows = svc.list_item_mappings(db, f["item"].id)
    assert len(rows) == 2
    assert {r.account_code_label for r in rows} == {"6238 清潔費", "6241 雜項支出"}


# ── 撞號要被擋下，而且訊息要講得出是哪一組 ─────────────────────────────────

def test_create_duplicate_company_department_is_rejected(db, fixtures):
    f = fixtures
    _create(db, f["item"].id, "春大直", f["admin"].id, f["clean"].id)
    with pytest.raises(svc.ItemMappingConflict) as e:
        _create(db, f["item"].id, "春大直", f["admin"].id, f["misc"].id)
    # 訊息要指名道姓，不能只說「重複」
    assert "春大直" in str(e.value) and "管理部" in str(e.value)


def test_create_duplicate_is_rejected_even_with_a_different_account(db, fixtures):
    """唯一鍵不含會計科目 —— 換一個科目不會讓它變成「不同的一筆」。

    這一條是刻意釘住的：請購單是用 (公司, 部門) .first() 抓對照，
    同一個部門掛兩個科目會讓那裡隨機挑一筆。
    """
    f = fixtures
    _create(db, f["item"].id, "春大直", f["admin"].id, f["clean"].id)
    with pytest.raises(svc.ItemMappingConflict):
        _create(db, f["item"].id, "春大直", f["admin"].id, f["misc"].id)


def test_update_into_an_existing_company_department_is_rejected(db, fixtures):
    """0920 之前這條路徑完全沒防，撞到會是一個沒人看得懂的 500。"""
    f = fixtures
    _create(db, f["item"].id, "春大直", f["admin"].id, f["clean"].id)
    m2 = _create(db, f["item"].id, "春大直", f["mkt"].id, f["misc"].id)
    with pytest.raises(svc.ItemMappingConflict) as e:
        svc.update_item_mapping(
            db, f["item"].id, m2.id,
            ItemMappingUpdate(department_id=f["admin"].id),
        )
    assert "管理部" in str(e.value)


def test_update_keeping_its_own_company_department_is_fine(db, fixtures):
    """只改科目／單價不算撞到自己 —— exclude_unset 的比較基準要拿現有值補齊。"""
    f = fixtures
    m = _create(db, f["item"].id, "春大直", f["admin"].id, f["clean"].id, Decimal("100"))
    out = svc.update_item_mapping(
        db, f["item"].id, m.id,
        ItemMappingUpdate(account_code_id=f["misc"].id, original_unit_price=Decimal("135.5")),
    )
    assert out.account_code_label == "6241 雜項支出"
    assert Decimal(str(out.original_unit_price)) == Decimal("135.5")
    assert out.department_id == f["admin"].id


def test_update_can_move_to_a_free_department(db, fixtures):
    f = fixtures
    m = _create(db, f["item"].id, "春大直", f["admin"].id, f["clean"].id)
    out = svc.update_item_mapping(
        db, f["item"].id, m.id, ItemMappingUpdate(department_id=f["mkt"].id),
    )
    assert out.department_id == f["mkt"].id
    assert out.department_name == "行銷部"


def test_same_company_department_on_a_different_item_is_allowed(db, fixtures):
    """唯一鍵的第一段是料號 —— 別的料號當然可以用同一組公司＋部門。"""
    f = fixtures
    other = CyclePurchaseItem(item_code="CH-0105055", item_name="擦手紙")
    db.add(other); db.flush()
    _create(db, f["item"].id, "春大直", f["admin"].id, f["clean"].id)
    m = _create(db, other.id, "春大直", f["admin"].id, f["clean"].id)
    assert m.id is not None


def test_account_code_can_be_cleared_back_to_none(db, fixtures):
    """畫面上清空科目要真的清掉（送 null，不是 undefined）。"""
    f = fixtures
    m = _create(db, f["item"].id, "春大直", f["admin"].id, f["clean"].id)
    out = svc.update_item_mapping(
        db, f["item"].id, m.id, ItemMappingUpdate(account_code_id=None),
    )
    assert out.account_code_id is None
    assert out.account_code_label is None


def test_create_on_a_missing_item_returns_none(db, fixtures):
    assert _create(db, 99999, "春大直", fixtures["admin"].id) is None
