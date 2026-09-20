# -*- coding: utf-8 -*-
"""
週期採購 — 合併供應商

2026-09-20 實測發現：週採 204 家供應商裡有 32 家是匯入料號時直接用**簡稱**建的
孤兒，其中 **15 家在週採裡已經另外有一筆正確的全稱**（「北金」 vs
「北金文具印刷有限公司」）。這種情況**不能用「對照合約廠商」解決** —— 目標已被
正本佔走會撞號；要的是把孤兒身上的參照搬到正本。

Ragic 主表「廠商(一)」是連結欄位、只認廠商資料表的全名，所以料號對照只要還指著
簡稱那一筆，拋轉出去的單廠商欄就是空的（而且 Ragic 照樣回 SUCCESS）。

DB 用記憶體 SQLite（測的是搬移筆數與防呆分支），符合 CLAUDE.md §0。
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
from app.models.cycle_purchase_vendor import CyclePurchaseVendor        # noqa: E402
from app.models.cycle_purchase_item import (                            # noqa: E402
    CyclePurchaseItem, CyclePurchaseItemMapping,
)
from app.models.cycle_purchase_reference import CyclePurchaseDepartment  # noqa: E402
from app.models.cycle_purchase_summary import CyclePurchaseSummary      # noqa: E402
from app.models.cycle_purchase_po import CyclePurchasePO                # noqa: E402
import app.models.cycle_purchase_category    # noqa: F401,E402
import app.models.cycle_purchase_cycle       # noqa: F401,E402
import app.models.cycle_purchase_request     # noqa: F401,E402
import app.models.cycle_purchase_receiving   # noqa: F401,E402
import app.models.cycle_purchase_payment     # noqa: F401,E402
import app.models.cycle_purchase_audit       # noqa: F401,E402

from app.services import cycle_purchase_service as svc                  # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    CyclePurchaseBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def pair(db):
    """孤兒「北金」(簡稱) 與正本「北金文具印刷有限公司」(已對照合約主檔)。"""
    orphan = CyclePurchaseVendor(id=33, vendor_code="CPV-0033", vendor_name="北金")
    proper = CyclePurchaseVendor(id=120, vendor_code="V-00047",
                                 vendor_name="北金文具印刷有限公司",
                                 source_vendor_id="V-00047")
    item = CyclePurchaseItem(id=1, item_code="CH-G0201001", item_name="A3影印紙",
                             default_vendor_id=33)
    dept = CyclePurchaseDepartment(id=6, company="春大直", dept_code="ADM", dept_name="管理部")
    db.add_all([orphan, proper, item, dept])
    db.flush()
    db.add_all([
        CyclePurchaseItemMapping(item_id=1, company="春大直", department_id=6, vendor_id=33),
        CyclePurchaseSummary(id=1, cycle_id=1, period_label="2026-09", company="春大直",
                             item_id=1, item_code="CH-G0201001", item_name="A3影印紙",
                             unit="包", demand_qty=1, adjusted_qty=1,
                             unit_price=Decimal("160"), status="draft", vendor_id=33),
    ])
    db.flush()
    return {"orphan": orphan, "proper": proper}


def test_dry_run_reports_what_would_move_without_writing(db, pair):
    out = svc.preview_vendor_merge(db, 33, 120)
    assert out["applied"] is False
    assert out["moved"]["料號對照"] == 1
    assert out["moved"]["彙整列"] == 1
    assert out["moved"]["料號主檔的預設供應商"] == 1
    assert out["total_moved"] == 3
    # 什麼都沒動
    assert db.query(CyclePurchaseItemMapping).filter_by(vendor_id=33).count() == 1
    assert pair["orphan"].is_active is True


def test_merge_repoints_every_reference(db, pair):
    out = svc.merge_vendor(db, 33, 120)
    assert out["applied"] is True
    assert out["total_moved"] == 3
    assert db.query(CyclePurchaseItemMapping).filter_by(vendor_id=33).count() == 0
    assert db.query(CyclePurchaseItemMapping).filter_by(vendor_id=120).count() == 1
    assert db.query(CyclePurchaseSummary).filter_by(vendor_id=120).count() == 1
    assert db.query(CyclePurchaseItem).filter_by(default_vendor_id=120).count() == 1


def test_source_is_deactivated_not_deleted(db, pair):
    """⚠️ 停用不是刪除：採購單外鍵是 RESTRICT，而且停用可逆、稽核查得到。"""
    svc.merge_vendor(db, 33, 120)
    still = db.query(CyclePurchaseVendor).filter_by(id=33).first()
    assert still is not None
    assert still.is_active is False
    assert "合併" in (still.notes or "")
    assert "北金文具印刷有限公司" in (still.notes or "")


def test_merging_into_itself_is_rejected(db, pair):
    with pytest.raises(svc.VendorMergeError) as e:
        svc.merge_vendor(db, 33, 33)
    assert "同一筆" in str(e.value)


def test_missing_vendor_returns_empty(db, pair):
    assert svc.merge_vendor(db, 33, 99999) == {}
    assert svc.merge_vendor(db, 99999, 120) == {}


def test_clashing_active_pos_are_refused_with_a_readable_message(db, pair):
    """兩邊在同一組週期＋期別＋公司底下都有有效採購單 → 搬過去會撞 partial unique index。

    與其讓它拋一個看不懂的 IntegrityError，先查出來講清楚哪兩張單相撞。
    """
    db.add_all([
        CyclePurchasePO(po_no="PO-202609-0001", cycle_id=1, period_label="2026-09",
                        company="春大直", vendor_id=33, status="draft"),
        CyclePurchasePO(po_no="PO-202609-0002", cycle_id=1, period_label="2026-09",
                        company="春大直", vendor_id=120, status="draft"),
    ])
    db.flush()
    with pytest.raises(svc.VendorMergeError) as e:
        svc.merge_vendor(db, 33, 120)
    msg = str(e.value)
    assert "PO-202609-0001" in msg and "PO-202609-0002" in msg
    assert "取消" in msg          # 要告訴他怎麼辦
    # 撞號時什麼都不該被搬走
    assert db.query(CyclePurchaseItemMapping).filter_by(vendor_id=33).count() == 1


def test_cancelled_pos_do_not_block_the_merge(db, pair):
    """已取消的採購單不參與唯一性檢查（partial index 的條件），不該擋住合併。"""
    db.add_all([
        CyclePurchasePO(po_no="PO-202609-0003", cycle_id=1, period_label="2026-09",
                        company="春大直", vendor_id=33, status="cancelled"),
        CyclePurchasePO(po_no="PO-202609-0004", cycle_id=1, period_label="2026-09",
                        company="春大直", vendor_id=120, status="draft"),
    ])
    db.flush()
    out = svc.merge_vendor(db, 33, 120)
    assert out["applied"] is True
    assert out["moved"]["採購單"] == 1


def test_reference_list_covers_every_table_with_a_vendor_column():
    """⚠️ 新增會參照供應商的資料表時，一定要補進 _VENDOR_REFERENCES。

    漏一個就會留下指向已停用供應商的孤兒參照，而且**不會有任何錯誤訊息**。
    這一條把目前已知的四處釘住，將來加表時這個測試會提醒你。
    """
    covered = {(t, c) for t, c, _ in svc._VENDOR_REFERENCES}
    assert covered == {
        ("cycle_purchase_item_mappings", "vendor_id"),
        ("cycle_purchase_summary", "vendor_id"),
        ("cycle_purchase_pos", "vendor_id"),
        ("cycle_purchase_items", "default_vendor_id"),
    }
