"""全棟保養：2026/10 起新編號正規化（棟週保202610-006）"""
from app.services.full_building_maintenance_sync import _normalize_journal_no


def test_new_format_is_normalized():
    assert _normalize_journal_no("2026/10棟週保-006") == "棟週保202610-006"


def test_orphan_star_variant_is_normalized():
    assert _normalize_journal_no("2026/10*棟週保-001") == "棟週保202610-001"


def test_surrounding_whitespace_is_tolerated():
    assert _normalize_journal_no("  2026/11棟週保-012 ") == "棟週保202611-012"


def test_old_format_is_unchanged():
    assert _normalize_journal_no("棟週保202609-001") == "棟週保202609-001"
    assert _normalize_journal_no("棟週保202608-001") == "棟週保202608-001"


def test_unparseable_and_empty_pass_through():
    assert _normalize_journal_no("") == ""
    assert _normalize_journal_no("隨便寫的") == "隨便寫的"
