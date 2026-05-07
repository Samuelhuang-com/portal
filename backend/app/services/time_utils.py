"""
time_utils.py — 時間解析共用工具

集中管理跨模組共用的時間計算函式，避免在各 router 中重複定義。
"""
import re
from typing import Optional


def parse_minutes(start: str, end: str) -> int:
    """
    解析 HH:MM 格式開始/結束時間，回傳分鐘數差值；格式無效回傳 0。

    支援跨日情形：若 end < start（diff < 0），視為跨越午夜，
    自動加上 24 × 60 分鐘修正。

    Args:
        start: 開始時間字串，格式 "HH:MM"（可含前後空白）。
        end:   結束時間字串，格式 "HH:MM"（可含前後空白）。

    Returns:
        整數分鐘數差值（≥ 0）；任一參數格式無效則回傳 0。

    Examples:
        >>> parse_minutes("09:00", "10:30")
        90
        >>> parse_minutes("23:30", "00:15")
        45
        >>> parse_minutes("", "10:00")
        0
    """
    def to_min(t: str) -> Optional[int]:
        m = re.match(r"^(\d{1,2}):(\d{2})$", (t or "").strip())
        return int(m.group(1)) * 60 + int(m.group(2)) if m else None

    s, e = to_min(start), to_min(end)
    if s is None or e is None:
        return 0
    diff = e - s
    return diff + 24 * 60 if diff < 0 else diff
