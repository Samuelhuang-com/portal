"""
工單明細子表（維修記錄）共用解析工具

供 dazhi_repair_sync / luqun_repair_sync 使用：
  從 Ragic raw row 中找出「維修記錄」子表（key 為 _subtable_*），
  解析為標準化 dict list，供寫入 *_repair_record 表。

子表欄位（飯店 _subtable_1004878 / 商場 _subtable_1013290）：
  項次 / 狀態（商場無）/ 維修記錄 / 時間開始 / 時間結束 / 維修人員

注意：時間需保留「秒」精度（子表常有數秒的短列，工時計算用）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

# 判定為「維修記錄子表」所需欄位（任一列含其中之一即視為目標子表）
_DETAIL_MARKER_KEYS = ("維修記錄", "時間開始")

_DT_FORMATS = (
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
)


def parse_subtable_datetime(val) -> Optional[datetime]:
    """解析子表時間字串（保留秒）。解析失敗或空值 → None。"""
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def extract_detail_records(raw: dict) -> list[dict]:
    """
    從 Ragic raw row 解析維修記錄子表。

    回傳 list[dict]，每筆：
      { "ragic_id": str, "seq": str, "status": str, "record": str,
        "start_at": datetime|None, "end_at": datetime|None, "person": str }
    依 start_at 排序（None 排最後）。找不到子表 → []。
    """
    if not isinstance(raw, dict):
        return []

    sub: dict | None = None
    for key, val in raw.items():
        if not str(key).startswith("_subtable_") or not isinstance(val, dict):
            continue
        # 確認是維修記錄子表（檢查任一列的欄位）
        for row in val.values():
            if isinstance(row, dict) and any(k in row for k in _DETAIL_MARKER_KEYS):
                sub = val
                break
        if sub is not None:
            break

    if not sub:
        return []

    records: list[dict] = []
    for rid, row in sub.items():
        if not isinstance(row, dict):
            continue
        rec = {
            "ragic_id": str(row.get("_ragicId", rid)),
            "seq":      str(row.get("項次", "") or "").strip(),
            "status":   str(row.get("狀態", "") or "").strip(),
            "record":   str(row.get("維修記錄", "") or "").strip(),
            "start_at": parse_subtable_datetime(row.get("時間開始")),
            "end_at":   parse_subtable_datetime(row.get("時間結束")),
            "person":   str(row.get("維修人員", "") or "").strip(),
        }
        # 全空列（Ragic 偶有空白尾列）→ 略過
        if not any([rec["seq"], rec["record"], rec["start_at"], rec["end_at"], rec["person"]]):
            continue
        records.append(rec)

    records.sort(key=lambda r: (r["start_at"] is None, r["start_at"] or datetime.min))
    return records
