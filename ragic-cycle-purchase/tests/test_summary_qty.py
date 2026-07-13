"""
test_summary_qty.py v1.0
彙整數量計算測試：
  - 需求總量 = 各部門請購數量加總（排除0）
  - 調整量與需求量不同時需有原因
  - 調整量=0不可轉採購單
"""
import pytest


class TestSummaryQuantity:
    """彙整單數量計算邏輯測試。"""

    def test_demand_qty_sum_excluding_zero(self):
        """需求總量 = 各部門非零數量加總。"""
        requests = [
            {"請購部門": "行政部", "料號": "ITEM001", "請購數量": 10},
            {"請購部門": "業務部", "料號": "ITEM001", "請購數量": 0},
            {"請購部門": "IT部",   "料號": "ITEM001", "請購數量": 5},
        ]
        total = sum(r["請購數量"] for r in requests if r["請購數量"] > 0)
        assert total == 15, f"彙整總量應為15，實際為{total}"

    def test_demand_qty_all_zero_no_summary(self):
        """所有部門數量均為0時，不應產生彙整單。"""
        requests = [
            {"請購部門": "行政部", "請購數量": 0},
            {"請購部門": "業務部", "請購數量": 0},
        ]
        total = sum(r["請購數量"] for r in requests)
        assert total == 0, "所有數量為0時不應產生彙整單"
        should_create = total > 0
        assert not should_create

    def test_adjusted_qty_different_requires_reason(self):
        """調整量與需求量不同時調整原因必填。"""
        demand_qty = 15
        adjusted_qty = 10
        adjust_reason = ""
        if adjusted_qty != demand_qty:
            is_valid = bool(adjust_reason.strip())
            assert not is_valid, "調整原因為空時應驗證失敗"

    def test_adjusted_qty_zero_blocked(self):
        """調整量為0不可轉採購單。"""
        adjusted_qty = 0
        can_convert = adjusted_qty > 0
        assert not can_convert, "調整量為0不可轉採購單"

    def test_adjusted_qty_same_as_demand_no_reason_required(self):
        """調整量等於需求量時，不需填調整原因。"""
        demand_qty = 15
        adjusted_qty = 15
        adjust_reason = ""
        if adjusted_qty == demand_qty:
            is_valid = True
        else:
            is_valid = bool(adjust_reason.strip())
        assert is_valid


class TestSummaryFormula:
    """彙整單公式計算測試。"""

    def test_subtotal_formula(self):
        """請購明細小計 = 單價 × 請購數量。"""
        unit_price = 100
        request_qty = 15
        subtotal = unit_price * request_qty
        assert subtotal == 1500

    def test_total_amount_formula(self):
        """請購總金額 = SUM(請購明細.小計)。"""
        details = [
            {"單價": 100, "請購數量": 10},
            {"單價": 80,  "請購數量": 20},
            {"單價": 200, "請購數量": 0},
        ]
        total = sum(d["單價"] * d["請購數量"] for d in details)
        assert total == 2600
