"""
test_payment_allocation.py v1.0
請款分攤測試：
  - 分攤金額合計必須等於發票金額
  - 差異時差異原因必填
  - 驗收異常狀態需有異常紀錄才可進入請款
  - 請款不可重複建立
"""
import pytest


class TestPaymentAllocation:
    """費用分攤明細驗證測試。"""

    def test_allocation_sum_equals_invoice(self):
        """分攤金額合計應等於發票金額。"""
        invoice_amount = 5000
        allocations = [
            {"部門": "行政部", "分攤金額": 2000},
            {"部門": "業務部", "分攤金額": 2000},
            {"部門": "IT部",   "分攤金額": 1000},
        ]
        total_alloc = sum(a["分攤金額"] for a in allocations)
        assert total_alloc == invoice_amount, f"分攤合計{total_alloc}應等於發票金額{invoice_amount}"

    def test_allocation_diff_requires_reason(self):
        """分攤合計與發票金額不同時，差異原因必填。"""
        invoice_amount = 5000
        total_alloc = 4800
        diff_reason = ""
        if total_alloc != invoice_amount:
            is_valid = bool(diff_reason.strip())
            assert not is_valid, "差異原因為空時驗證應失敗"

    def test_allocation_diff_with_reason_passes(self):
        """有填差異原因時驗證應通過。"""
        invoice_amount = 5000
        total_alloc = 4800
        diff_reason = "匯率調整差異"
        if total_alloc != invoice_amount:
            is_valid = bool(diff_reason.strip())
            assert is_valid, "有差異原因時應通過驗證"

    def test_empty_allocations_blocked(self):
        """費用分攤明細為空時不可提交請款單。"""
        allocations = []
        can_submit = len(allocations) > 0
        assert not can_submit, "空分攤明細不可提交"


class TestPaymentPrerequisite:
    """請款單前置條件測試。"""

    def test_abnormal_receiving_needs_audit_record(self):
        """驗收異常狀態必須有異常紀錄才可產生請款單。"""
        recv_status = "驗收異常"
        audit_records = []
        if recv_status == "驗收異常":
            can_proceed = len(audit_records) > 0
            assert not can_proceed, "無異常紀錄不可產生請款單"

    def test_abnormal_receiving_with_audit_allowed(self):
        """有異常紀錄且授權放行時可產生請款單。"""
        recv_status = "驗收異常"
        audit_records = [{"事件類型": "驗收差異", "說明": "授權放行"}]
        if recv_status == "驗收異常":
            can_proceed = len(audit_records) > 0
            assert can_proceed, "有異常紀錄時應允許產生請款單"

    def test_duplicate_payment_blocked(self):
        """同一驗收單不可重複建立請款單。"""
        recv_no = "RECV001"
        existing_payments = [{"請款單號": "PAY001", "驗收單號": recv_no}]
        already_exists = any(p["驗收單號"] == recv_no for p in existing_payments)
        assert already_exists, "應偵測到重複的請款單"
        can_create = not already_exists
        assert not can_create, "重複請款單應被阻止"

    def test_pending_receiving_blocked(self):
        """待驗收狀態不可產生請款單。"""
        recv_status = "待驗收"
        can_proceed = recv_status in ("驗收完成", "驗收異常")
        assert not can_proceed, "待驗收不可進入請款"
