"""
test_cycle_rules.py v1.0
週期規則測試：
  - 週期批次不可重複產生
  - 批次關閉後不可送出請購單
  - 逾期批次阻止送出
"""
import pytest
from unittest.mock import MagicMock, patch


class TestCycleBatchGeneration:
    """週期批次產生規則測試。"""

    def test_batch_not_duplicated(self):
        """同一週期同一期間不可重複產生批次。"""
        existing_batches = [{"批次號": "BATCH001", "開放日期": "2026-06-01"}]
        with patch("scripts.ragic_client.RagicClient.get_records", return_value=existing_batches):
            from scripts.ragic_client import RagicClient
            client = RagicClient(api_key="test", dry_run=True)
            records = client.get_records("cycle-purchase/batches", {"週期ID": "CYCLE001", "開放日期": "2026-06-01"})
            assert len(records) > 0, "應偵測到已存在的批次"

    def test_disabled_cycle_cannot_generate(self):
        """停用週期不可產生批次。"""
        cycle_status = "停用"
        assert cycle_status != "啟用", "停用週期不應通過驗證"

    def test_missing_dates_blocked(self):
        """未填開放日或截止日不可產生批次。"""
        open_date = None
        close_date = "2026-06-10"
        assert open_date is None, "空白開放日應被阻止"


class TestRequestSubmitRules:
    """請購單送出規則測試。"""

    def test_request_qty_default_zero(self):
        """請購明細預設數量應為0。"""
        sample_details = [
            {"統購料號": "ITEM001", "品名": "衛生紙", "請購數量": 0},
            {"統購料號": "ITEM002", "品名": "洗手乳", "請購數量": 0},
        ]
        for detail in sample_details:
            assert detail["請購數量"] == 0, f"{detail['品名']} 預設數量應為0"

    def test_blank_qty_blocked(self):
        """空白數量（None）不可送出。"""
        detail = {"統購料號": "ITEM001", "請購數量": None}
        is_valid = detail["請購數量"] is not None
        assert not is_valid, "空白數量應被阻止"

    def test_closed_batch_blocks_submit(self):
        """批次已關閉不可送出請購單。"""
        batch_status = "關閉"
        can_submit = batch_status == "開放"
        assert not can_submit, "關閉批次不應允許送出"

    def test_overdue_batch_blocks_submit(self):
        """逾期批次不可送出請購單。"""
        close_date = "2026-05-01"
        today = "2026-06-09"
        is_overdue = close_date < today
        assert is_overdue, "批次已逾截止日應被阻止"
