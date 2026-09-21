# -*- coding: utf-8 -*-
"""
週期採購 — 請款單分攤建議不可以因為請購單 status 而全部落到「未歸屬」

2026-09-21 盤點抓到：`_compute_suggested_allocation()` 仍篩
`CyclePurchaseRequest.status == "approved"`。2026-07-17 請購單拿掉送出／核准之後，
新資料的 status 固定是 draft，永遠查不到 → 每一筆採購明細都走「找不回原始請購資料」
的防呆，整張請款單的分攤建議全部歸到 department_id=None（未歸屬）。

修正後的口徑與 unsummarize_request() 重算相同：
同週期＋期別＋公司＋部門、且 is_summarized=True 的請購單。
2026-07-16 以前沒有部門別的歷史彙整列維持舊規則（status == "approved"）。

DB 用記憶體 SQLite（純查詢邏輯，沒有併發／鎖），符合 CLAUDE.md §0。
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.cycle_purchase_database import CyclePurchaseBase          # noqa: E402
from app.models.cycle_purchase_request import (                          # noqa: E402
    CyclePurchaseRequest, CyclePurchaseRequestItem,
)
from app.models.cycle_purchase_summary import CyclePurchaseSummary      # noqa: E402
from app.models.cycle_purchase_po import CyclePurchasePO, CyclePurchasePOItem  # noqa: E402
import app.models.cycle_purchase_item        # noqa: F401,E402  （建表需要）
import app.models.cycle_purchase_reference   # noqa: F401,E402
import app.models.cycle_purchase_vendor      # noqa: F401,E402
import app.models.cycle_purchase_category    # noqa: F401,E402
import app.models.cycle_purchase_cycle       # noqa: F401,E402
import app.models.cycle_purchase_receiving   # noqa: F401,E402
import app.models.cycle_purchase_payment     # noqa: F401,E402
import app.models.cycle_purchase_audit       # noqa: F401,E402

from app.services.cycle_purchase_payment_service import _compute_suggested_allocation  # noqa: E402

CYCLE, PERIOD, COMPANY, ITEM = 1, "2026-09", "春大直", 10
_seq = {"n": 0}


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    CyclePurchaseBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _request(db, dept, qty, *, status="draft", summarized=True, closed=True,
             cost_center=None, account=None, item=ITEM):
    _seq["n"] += 1
    req = CyclePurchaseRequest(
        request_no=f"PR-2026-09-{_seq['n']:03d}", cycle_id=CYCLE, period_label=PERIOD,
        department_id=dept, company=COMPANY, status=status, total_amount=0,
        is_summarized=summarized, is_closed=closed, cost_center_id=cost_center,
    )
    db.add(req)
    db.flush()
    db.add(CyclePurchaseRequestItem(
        request_id=req.id, item_id=item, item_code="A001", item_name="影印紙",
        request_qty=qty, subtotal=0, account_code_id=account,
    ))
    db.flush()
    return req


def _po_line(db, dept, subtotal, *, item=ITEM):
    s = CyclePurchaseSummary(
        cycle_id=CYCLE, period_label=PERIOD, company=COMPANY, item_id=item,
        department_id=dept, item_code="A001", item_name="影印紙",
        demand_qty=1, adjusted_qty=1, status="converted",
    )
    db.add(s)
    db.flush()
    po = db.query(CyclePurchasePO).first()
    if not po:
        po = CyclePurchasePO(po_no="PO-TEST-0001", cycle_id=CYCLE, period_label=PERIOD,
                             company=COMPANY, vendor_id=1, total_amount=0, status="issued")
        db.add(po)
        db.flush()
    db.add(CyclePurchasePOItem(
        po_id=po.id, summary_id=s.id, item_id=item, item_code="A001", item_name="影印紙",
        ordered_qty=1, subtotal=Decimal(subtotal),
    ))
    db.flush()
    return po


def test_new_flow_draft_request_is_allocated_to_its_department(db):
    """現場實況：新流程的請購單 status=draft、is_summarized=True。修正前全部落到未歸屬。"""
    _request(db, dept=5, qty=3, cost_center=7, account=9)
    po = _po_line(db, dept=5, subtotal="300.00")

    buckets = _compute_suggested_allocation(db, po)

    assert dict(buckets) == {(5, 7, 9): Decimal("300.00")}
    assert (None, None, None) not in buckets


def test_other_department_does_not_take_a_share(db):
    """彙整列是分部門的：A 部門那一行的金額不能拆給 B 部門。"""
    _request(db, dept=5, qty=1)
    _request(db, dept=6, qty=3)   # 同料號、別的部門
    po = _po_line(db, dept=5, subtotal="100.00")

    assert dict(_compute_suggested_allocation(db, po)) == {(5, None, None): Decimal("100.00")}


def test_unsummarized_request_is_excluded(db):
    """被「退回請購單」的單（is_summarized=False）不應再參與分攤。"""
    _request(db, dept=5, qty=2, cost_center=1)
    _request(db, dept=5, qty=8, cost_center=2, summarized=False)
    po = _po_line(db, dept=5, subtotal="50.00")

    assert dict(_compute_suggested_allocation(db, po)) == {(5, 1, None): Decimal("50.00")}


def test_same_department_split_by_cost_center_and_account(db):
    """同部門多張單（不同成本中心／會科）依數量占比拆，尾差由最後一組吸收。"""
    _request(db, dept=5, qty=1, cost_center=1, account=1)
    _request(db, dept=5, qty=2, cost_center=2, account=1)
    po = _po_line(db, dept=5, subtotal="100.00")

    buckets = _compute_suggested_allocation(db, po)
    assert buckets[(5, 1, 1)] == Decimal("33.33")
    assert buckets[(5, 2, 1)] == Decimal("66.67")
    assert sum(buckets.values()) == Decimal("100.00")


def test_legacy_summary_without_department_keeps_old_rule(db):
    """2026-07-16 以前的歷史彙整列（department_id=None）維持跨部門、依 approved 單拆。"""
    _request(db, dept=5, qty=1, status="approved", summarized=False)
    _request(db, dept=6, qty=3, status="approved", summarized=False)
    _request(db, dept=7, qty=9, status="draft", summarized=True)   # 舊規則不看這張
    po = _po_line(db, dept=None, subtotal="100.00")

    assert dict(_compute_suggested_allocation(db, po)) == {
        (5, None, None): Decimal("25.00"),
        (6, None, None): Decimal("75.00"),
    }


def test_no_source_request_still_falls_back_to_unassigned(db):
    """防呆行為不變：真的找不回請購資料時才歸到未歸屬。"""
    po = _po_line(db, dept=5, subtotal="80.00")
    assert dict(_compute_suggested_allocation(db, po)) == {(None, None, None): Decimal("80.00")}
