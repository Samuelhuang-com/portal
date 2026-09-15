"""
Excel（openpyxl）寫入工具 — 共用於各報表的 Excel 匯出
"""
import re
from typing import Any

# openpyxl 的 ILLEGAL_CHARACTERS_RE：XML 1.0 規格不允許出現在文件中的控制字元。
# 寫進儲存格會讓 openpyxl 丟 IllegalCharacterError，整支匯出 API 500。
# （\x09 tab、\x0a LF、\x0d CR 是合法的，不能清掉。）
_ILLEGAL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# Excel 單一儲存格字元數上限；超過同樣會讓 openpyxl 拒絕。
_MAX_CELL_LEN = 32767


def xlsx_safe(value: Any) -> Any:
    """
    把值清理成 openpyxl 一定收得下的形式。非字串原樣回傳。

    用途：Ragic 的自由輸入欄位（品名／說明／備註）可能夾帶看不見的控制字元
    —— 多半是從別的系統複製貼上帶進來的。畫面上完全看不出來，但匯出 Excel 時
    openpyxl 會丟 `IllegalCharacterError` → 500，且只有「剛好含到那筆資料」的
    篩選條件會失敗，非常難查。

    2026-09-15 實例：`樂工購20260700030` 的品名含 `\\x03`
    （「水管型溫度感測器(\\x03NTC 3K)異常」），導致工務部 2026-07、
    以及任何涵蓋該月的區間（含 2026年度、全部部門）匯出全部 500。

    Examples:
        >>> xlsx_safe("正常字串")
        '正常字串'
        >>> xlsx_safe("感測器(\\x03NTC 3K)")
        '感測器(NTC 3K)'
        >>> xlsx_safe(123)
        123
        >>> xlsx_safe(None) is None
        True
    """
    if not isinstance(value, str):
        return value
    cleaned = _ILLEGAL_CHARS_RE.sub("", value)
    if len(cleaned) > _MAX_CELL_LEN:
        cleaned = cleaned[:_MAX_CELL_LEN]
    return cleaned
