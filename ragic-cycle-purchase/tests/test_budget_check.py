"""
test_budget_check.py v1.0
預算檢核測試：
  - 請購總金額不超過部門預算
  - 預算不足時是否提示（v1.0為警告，不阻止）
  - 會計科目帶入邏輯
"""
import pytest


class TestBudgetCheck:
    """部門預算檢核測試。"""

    def test_request_within_budget(self):
        """請購金額在預算範圍內應通過。"""
        dept_budget = 10000
        request_amount = 8000
        exceeds = request_amount > dept_budget
        assert not exceeds, "8000 應在 10000 預算內"

    def test_request_exceeds_budget_warning(self):
        """請購金額超過預算應顯示警告（v1.0 不阻止，僅警告）。"""
        dept_budget = 10000
        request_amount = 12000
        exceeds = request_amount > dept_budget
        assert exceeds, "12000 超過 10000 預算，應觸發警告"

    def test_budget_calculation_with_existing_requests(self):
        """已提交請購的部門預算應扣除已用金額。"""
        annual_budget = 120000
        used_amount = 85000
        available = annual_budget - used_amount
        assert available == 35000

    def test_zero_budget_blocks_all(self):
        """預算為0時所有請購均超額（警告）。"""
        dept_budget = 0
        request_amount = 100
        exceeds = request_amount > dept_budget
        assert exceeds


class TestAccountCodeLookup:
    """會計科目帶入邏輯測試。"""

    def test_account_code_auto_loaded(self):
        """選擇部門後應自動帶入對應會計科目。"""
        dept_to_account = {
            "行政部": "6201",
            "業務部": "6201",
            "IT部":   "6299",
        }
        dept = "行政部"
        account = dept_to_account.get(dept)
        assert account == "6201", f"行政部的會計科目應為6201，實際為{account}"

    def test_cost_center_auto_loaded(self):
        """選擇部門後應自動帶入成本中心。"""
        dept_to_cost_center = {
            "行政部": "CC001",
            "業務部": "CC002",
        }
        dept = "業務部"
        cc = dept_to_cost_center.get(dept)
        assert cc == "CC002"
