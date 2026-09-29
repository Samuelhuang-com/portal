# -*- coding: utf-8 -*-
"""
週期採購 — 手動「新增請購單」「複製上期請購單」必須符合週期的適用範圍（2026-09-29）

改版前 create_request()／copy_request() 只檢查週期與部門「存在」，可以建出
「只適用智選的週期 × 春大直部門」這種單。現在與「產生本期請購單」共用
resolve_applicable_departments()：適用公司 ∩ 適用部門 ∩ 品類下有啟用中料號。

DB 用記憶體 SQLite（純規則判斷，沒有併發／鎖），符合 CLAUDE.md §0。
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.cycle_purchase_database import CyclePurchaseBase          # noqa: E402
from app.models.cycle_purchase_request import CyclePurchaseRequest, CyclePurchaseRequestItem  # noqa: E402
from app.models.cycle_purchase_reference import CyclePurchaseDepartment  # noqa: E402
from app.models.cycle_purchase_item import CyclePurchaseItem, CyclePurchaseItemMapping  # noqa: E402
from app.models.cycle_purchase_cycle import CyclePurchaseCycle          # noqa: E402
import app.models.cycle_purchase_vendor      # noqa: F401,E402  （建表需要）
import app.models.cycle_purchase_category    # noqa: F401,E402
import app.models.cycle_purchase_summary     # noqa: F401,E402
import app.models.cycle_purchase_po          # noqa: F401,E402
import app.models.cycle_purchase_receiving   # noqa: F401,E402
import app.models.cycle_purchase_payment     # noqa: F401,E402
import app.models.cycle_purchase_audit       # noqa: F401,E402

from app.services import cycle_purchase_request_service as svc  # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    CyclePurchaseBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _dept(db, company, code, name, active=True):
    d = CyclePurchaseDepartment(company=company, dept_code=code, dept_name=name, is_active=active)
    db.add(d)
    db.flush()
    return d


def _item(db, code, category, dept):
    it = CyclePurchaseItem(item_code=code, item_name=f"品項{code}", category=category, is_active=True)
    db.add(it)
    db.flush()
    db.add(CyclePurchaseItemMapping(
        item_id=it.id, company=dept.company, department_id=dept.id,
        original_unit_price=Decimal("10"),
    ))
    db.flush()
    return it


def _cycle(db, code, scope=None, dept_ids=None, categories=None):
    c = CyclePurchaseCycle(
        cycle_code=code, cycle_name=f"週期{code}", frequency="monthly",
        applicable_scope=scope, applicable_department_ids=dept_ids,
        applicable_categories=categories, status="active",
    )
    db.add(c)
    db.flush()
    return c


@pytest.fixture()
def world(db):
    zx = _dept(db, "智選", "TC-01", "客務部")
    ch = _dept(db, "春大直", "CH-01", "營業部")
    ch_off = _dept(db, "春大直", "CH-02", "管理部", active=False)
    ch_noitem = _dept(db, "春大直", "CH-03", "行銷部")
    for d in (zx, ch, ch_off):
        _item(db, f"A{d.id}", "文具", d)
    return SimpleNamespace(zx=zx, ch=ch, ch_off=ch_off, ch_noitem=ch_noitem)


def _create(db, cycle, dept):
    return svc.create_request(db, SimpleNamespace(cycle_id=cycle.id, department_id=dept.id, cost_center_id=None))


def test_create_ok_when_department_in_scope(db, world):
    cyc = _cycle(db, "C1", scope="春大直")
    req = _create(db, cyc, world.ch)
    assert req.company == "春大直"


def test_create_rejects_company_outside_cycle_scope(db, world):
    """實際要防的情境：只適用智選的週期，選了春大直的部門。"""
    cyc = _cycle(db, "C2", scope="智選")
    with pytest.raises(svc.RequestServiceError, match="不屬於此週期的適用公司"):
        _create(db, cyc, world.ch)
    assert db.query(CyclePurchaseRequest).count() == 0


def test_create_rejects_department_not_ticked(db, world):
    cyc = _cycle(db, "C3", dept_ids=str(world.zx.id))
    with pytest.raises(svc.RequestServiceError, match="不在此週期勾選的適用部門"):
        _create(db, cyc, world.ch)


def test_create_rejects_inactive_department(db, world):
    cyc = _cycle(db, "C4", scope="春大直")
    with pytest.raises(svc.RequestServiceError, match="部門已停用"):
        _create(db, cyc, world.ch_off)


def test_create_rejects_department_without_items_in_category(db, world):
    cyc = _cycle(db, "C5", scope="春大直", categories="清潔用品")
    with pytest.raises(svc.RequestServiceError, match="沒有啟用中料號"):
        _create(db, cyc, world.ch)
    cyc2 = _cycle(db, "C6", scope="春大直")
    with pytest.raises(svc.RequestServiceError, match="沒有啟用中料號"):
        _create(db, cyc2, world.ch_noitem)


def test_copy_rechecks_scope_against_current_cycle_settings(db, world):
    """來源單建立後，週期被改成只適用智選 → 不能再複製成春大直的新單。"""
    cyc = _cycle(db, "C7", scope="春大直")
    src = _create(db, cyc, world.ch)
    it = db.query(CyclePurchaseItem).filter(CyclePurchaseItem.item_code == f"A{world.ch.id}").one()
    db.add(CyclePurchaseRequestItem(
        request_id=src.id, item_id=it.id, item_code=it.item_code, item_name=it.item_name,
        request_qty=1, unit_price=Decimal("10"), subtotal=Decimal("10"),
    ))
    db.flush()

    new_req, skipped = svc.copy_request(db, src.id, user=None)
    assert new_req.department_id == world.ch.id and not skipped

    cyc.applicable_scope = "智選"
    db.flush()
    with pytest.raises(svc.RequestServiceError, match="不屬於此週期的適用公司"):
        svc.copy_request(db, src.id, user=None)
