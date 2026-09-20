# -*- coding: utf-8 -*-
"""
週期採購 — 單號／批次號流水號不可以用 COUNT(*)+1（全部 7 處）

2026-09-20 實測抓到：`PR-2026-09-` 底下只剩 003～007（001、002 被刪過），
`COUNT(*)+1` 算出 006，正好撞上還活著的那張單。`request_no` 是 UNIQUE，
於是「新增請購單」整個月每次都 500 —— 不是偶發，是「刪過就永久壞掉」。

這支測試把「有洞的號碼序列」這個情境釘住 —— 對全部 7 個號碼產生器，
因為它們原本是同一個寫法，也應該一起被釘住：

  · 有 UNIQUE：request_no／po_no／receiving_no／payment_no → 撞號就是 500
  · 沒 UNIQUE：close_batch_no／summary_batch_no／ragic_push_batch_no
              → **不會報錯**，只是兩批不同的動作共用一個批次號，更難發現

DB 用記憶體 SQLite（純號碼計算，沒有併發／鎖），符合 CLAUDE.md §0。
"""
from __future__ import annotations

import os
import sys
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.cycle_purchase_database import CyclePurchaseBase          # noqa: E402
from app.models.cycle_purchase_request import CyclePurchaseRequest      # noqa: E402
import app.models.cycle_purchase_item        # noqa: F401,E402  （建表需要）
import app.models.cycle_purchase_reference   # noqa: F401,E402
import app.models.cycle_purchase_vendor      # noqa: F401,E402
import app.models.cycle_purchase_category    # noqa: F401,E402
import app.models.cycle_purchase_cycle       # noqa: F401,E402
import app.models.cycle_purchase_summary     # noqa: F401,E402
import app.models.cycle_purchase_po          # noqa: F401,E402
import app.models.cycle_purchase_receiving   # noqa: F401,E402
import app.models.cycle_purchase_payment     # noqa: F401,E402
import app.models.cycle_purchase_audit       # noqa: F401,E402

from app.services.cycle_purchase_request_service import _next_request_no   # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    CyclePurchaseBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _add(db, no: str):
    db.add(CyclePurchaseRequest(
        request_no=no, cycle_id=1, period_label="2026-09",
        department_id=1, company="春大直", status="draft", total_amount=0,
    ))
    db.flush()


ON = date(2026, 9, 20)


def test_first_number_of_the_month(db):
    assert _next_request_no(db, ON) == "PR-2026-09-001"


def test_counts_up_from_the_largest_not_the_count(db):
    for n in ("001", "002", "003"):
        _add(db, f"PR-2026-09-{n}")
    assert _next_request_no(db, ON) == "PR-2026-09-004"


def test_gap_in_the_sequence_does_not_reuse_a_live_number(db):
    """現場實況：001、002 被刪掉，只剩 003～007。

    COUNT(*)+1 會算出 006 —— 那張單還活著。這就是 500 的來源。
    """
    for n in ("003", "004", "005", "006", "007"):
        _add(db, f"PR-2026-09-{n}")
    nxt = _next_request_no(db, ON)
    assert nxt == "PR-2026-09-008"
    existing = {r.request_no for r in db.query(CyclePurchaseRequest).all()}
    assert nxt not in existing


def test_generated_number_actually_inserts(db):
    """把號碼真的寫下去 —— UNIQUE 撞號要在這裡就炸，不能等到正式區。"""
    for n in ("003", "004", "005", "006", "007"):
        _add(db, f"PR-2026-09-{n}")
    _add(db, _next_request_no(db, ON))          # 不該拋 IntegrityError
    assert db.query(CyclePurchaseRequest).count() == 6


def test_other_months_do_not_interfere(db):
    for n in ("001", "002", "003", "004", "005"):
        _add(db, f"PR-2026-08-{n}")
    assert _next_request_no(db, ON) == "PR-2026-09-001"


def test_malformed_numbers_are_ignored_not_crashed(db):
    """手工補過的怪號碼不該讓整支掛掉（也不該被算進流水號）。"""
    _add(db, "PR-2026-09-001")
    _add(db, "PR-2026-09-XXX")
    _add(db, "PR-2026-09-002")
    assert _next_request_no(db, ON) == "PR-2026-09-003"


# ═══════════════════════════════════════════════════════════════════════════
# 共用產生器本身（services/cycle_purchase_seq.py）
# ═══════════════════════════════════════════════════════════════════════════

from app.services import cycle_purchase_seq as seq                      # noqa: E402


def test_largest_suffix_ignores_gaps_and_junk():
    vals = ["PR-2026-09-003", "PR-2026-09-007", "PR-2026-09-XXX", None,
            "PR-2026-08-999", "", "PR-2026-09-004"]
    # 別的月份（PR-2026-08-999）不可以被算進來
    assert seq.largest_suffix(vals, "PR-2026-09-") == 7


def test_largest_suffix_of_nothing_is_zero():
    assert seq.largest_suffix([], "PR-2026-09-") == 0
    assert seq.largest_suffix([None, "", "其他-001"], "PR-2026-09-") == 0


# ═══════════════════════════════════════════════════════════════════════════
# 另外 6 個產生器：一樣不可以因為序列有洞而撞號
# ═══════════════════════════════════════════════════════════════════════════

def test_close_batch_no_counts_up_from_largest(db):
    """close_batch_no 沒有 UNIQUE —— 撞號不會報錯，只會靜默地把兩批混成一批。

    「重新開啟」會把 close_batch_no 清成 NULL，所以計數必定退回，
    這不是理論風險。
    """
    from app.services.cycle_purchase_request_service import _next_close_batch_no
    for i, no in enumerate(("CPCLOSE-202609-003", "CPCLOSE-202609-004", None)):
        db.add(CyclePurchaseRequest(
            request_no=f"PR-2026-09-{i + 1:03d}", cycle_id=1, period_label="2026-09",
            department_id=1, company="春大直", status="draft", total_amount=0,
            close_batch_no=no,
        ))
    db.flush()
    assert _next_close_batch_no(db, "2026-09") == "CPCLOSE-202609-005"


def test_summary_generate_batch_no_counts_up_from_largest(db):
    """退回請購單會把 summary_batch_no 清成 NULL，計數會退回。"""
    from app.services.cycle_purchase_summary_service import _next_summary_generate_batch_no
    for i, no in enumerate(("CPGEN-202609-春大直-002", None, "CPGEN-202609-春大直-005")):
        db.add(CyclePurchaseRequest(
            request_no=f"PR-2026-09-{i + 1:03d}", cycle_id=1, period_label="2026-09",
            department_id=1, company="春大直", status="draft", total_amount=0,
            summary_batch_no=no,
        ))
    db.flush()
    assert _next_summary_generate_batch_no(db, 1, "春大直", "2026-09") == "CPGEN-202609-春大直-006"


def test_summary_generate_batch_no_is_per_company(db):
    """批次號前綴含公司別 —— 別家公司的號碼不可以推高這一家的流水號。"""
    from app.services.cycle_purchase_summary_service import _next_summary_generate_batch_no
    db.add(CyclePurchaseRequest(
        request_no="PR-2026-09-001", cycle_id=1, period_label="2026-09",
        department_id=1, company="日曜天地", status="draft", total_amount=0,
        summary_batch_no="CPGEN-202609-日曜天地-009",
    ))
    db.flush()
    assert _next_summary_generate_batch_no(db, 1, "春大直", "2026-09") == "CPGEN-202609-春大直-001"


def test_po_no_counts_up_from_largest(db):
    from app.models.cycle_purchase_po import CyclePurchasePO
    from app.services.cycle_purchase_summary_service import _next_po_no
    # 採購單另有 (cycle, period, company, vendor) 的唯一鍵，所以每筆換一家廠商
    for i, no in enumerate(("PO-202609-0003", "PO-202609-0004", "PO-202609-0005")):
        db.add(CyclePurchasePO(po_no=no, cycle_id=1, period_label="2026-09",
                               company="春大直", vendor_id=i + 1))
    db.flush()
    assert _next_po_no(db, ON) == "PO-202609-0006"


def test_receiving_no_counts_up_from_largest(db):
    from app.models.cycle_purchase_receiving import CyclePurchaseReceiving
    from app.services.cycle_purchase_receiving_service import _next_receiving_no
    for no in ("RC-202609-0002", "RC-202609-0007"):
        db.add(CyclePurchaseReceiving(receiving_no=no, po_id=1, received_date=ON))
    db.flush()
    assert _next_receiving_no(db, ON) == "RC-202609-0008"


def test_payment_no_counts_up_from_largest(db):
    from app.models.cycle_purchase_payment import CyclePurchasePayment
    from app.services.cycle_purchase_payment_service import _next_payment_no
    for no in ("PAY-202609-0002", "PAY-202609-0009"):
        db.add(CyclePurchasePayment(payment_no=no, po_id=1, invoice_no="INV-1",
                                    invoice_date=ON, invoice_amount=100))
    db.flush()
    assert _next_payment_no(db, ON) == "PAY-202609-0010"


def test_ragic_push_batch_no_counts_up_from_largest(db):
    """拋轉批次號取「稽核紀錄」與「彙整表現用號碼」兩邊的最大值。

    2026-08-09 已經因為「取消拋轉把欄位清成 NULL → 計數退回 → 重推拿到一樣的
    批次號」修過一次，但當時只換了計數來源，沒改掉「用數量當號碼」。
    """
    from app.models.cycle_purchase_audit import CyclePurchaseAuditLog
    from app.services.cycle_purchase_summary_service import _next_ragic_push_batch_no
    prefix = "CPSUM-202609-春大直-"
    def audit(no, event):
        return CyclePurchaseAuditLog(
            document_type="summary", document_id=1, document_no=no,
            event_type=event, description="test")
    db.add(audit(f"{prefix}0003", "ragic_push"))
    db.add(audit(f"{prefix}0007", "ragic_push"))
    # 不同事件類型的號碼不可以被算進來
    db.add(audit(f"{prefix}0099", "other"))
    db.flush()
    assert _next_ragic_push_batch_no(db, "春大直", "2026-09") == f"{prefix}0008"
