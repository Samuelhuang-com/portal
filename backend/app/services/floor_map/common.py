"""
樓層巡檢圖 — 共用小工具（DEV_SPEC §5）

狀態語意固定四種（§5.2）：
  no_record ：當日該資料來源沒有任何場次
  abnormal  ：任一判定列異常／待處理
  unchecked ：有場次但有判定列未填
  normal    ：其餘（量測／填數字列有值即算正常）
kind = separate（另作表單）／unmapped（Ragic 無此欄位）的列不列入判定。
"""
from __future__ import annotations

import re
from typing import Any, Iterable

RAGIC_BASE = "https://ap12.ragic.com/soutlet001"

_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")
_DATE_RE = re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})")

JUDGED_KINDS = ("status", "reading")


def normalize_date(raw: str) -> str:
    """'2026-09-15' / '2026/9/15' → '2026/09/15'；解析不出來回空字串。"""
    m = _DATE_RE.search(raw or "")
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"{y}/{int(mo):02d}/{int(d):02d}"


def hhmm(raw: str) -> str:
    """取字串中最後一個 HH:MM（'2026/9/1 09:26' → '09:26'）。"""
    found = _TIME_RE.findall(raw or "")
    if not found:
        return ""
    h, m = found[-1]
    return f"{int(h):02d}:{m}"


def minutes_between(start: str, end: str) -> int:
    s, e = hhmm(start), hhmm(end)
    if not s or not e:
        return 0
    diff = (int(e[:2]) * 60 + int(e[3:])) - (int(s[:2]) * 60 + int(s[3:]))
    return diff + 24 * 60 if diff < 0 else diff


def ragic_record_url(sheet_path: str, row_id: str) -> str:
    if not sheet_path or not row_id:
        return ""
    return f"{RAGIC_BASE}/{sheet_path}/{row_id}"


def merge_group_status(rows: Iterable[dict[str, Any]], has_record: bool) -> str:
    if not has_record:
        return "no_record"
    judged = [r for r in rows if r.get("kind") in JUDGED_KINDS]
    if any(r.get("abnormal") for r in judged):
        return "abnormal"
    if any(r.get("status") == "unchecked" for r in judged):
        return "unchecked"
    return "normal"


def batch_out(sheet_path: str, row_id: str, b: Any) -> dict[str, Any]:
    """共用 Batch 格式（§5.1）。b 需有 inspector_name／start_time／end_time。"""
    return {
        "ragic_id":       b.ragic_id,
        "ragic_url":      ragic_record_url(sheet_path, row_id),
        "inspector":      (b.inspector_name or "").strip(),
        "start_hhmm":     hhmm(b.start_time or ""),
        "end_hhmm":       hhmm(b.end_time or ""),
        "actual_minutes": minutes_between(b.start_time or "", b.end_time or ""),
    }
