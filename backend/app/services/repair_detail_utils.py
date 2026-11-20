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


# ── 零件子表（2026-11-20）：工務零件／專櫃零件 ─────────────────────────────────
# 工務零件：零件／料號／數量／參考單價（無項次、無列小計；父層「零件金額」為合計）
# 專櫃零件：項次／零件／料號／數量／參考單價／領料日期／小計成本（父層「零件費用」為合計）
# 專櫃簽名、預估工時 為專櫃零件區的父層欄位。

def _to_float(v) -> float:
    """Ragic 金額可能是 "$710"、"1,200" 或數字；無法解析 → 0.0。"""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def _to_date(v):
    """領料日期（例如 2026/11/20）→ date；無法解析 → None。"""
    dt = parse_subtable_datetime(v)
    return dt.date() if dt else None


def extract_part_records(raw: dict) -> tuple[list[dict], list[dict]]:
    """
    從 Ragic raw row 解析零件子表。回傳 (工務零件 list, 專櫃零件 list)。

    判定：子表任一列同時含「零件」與「參考單價」即為零件子表；
          含「領料日期」或「小計成本」者為專櫃零件，其餘為工務零件。
    找不到 → ([], [])。
    """
    site: list[dict] = []
    counter: list[dict] = []
    if not isinstance(raw, dict):
        return site, counter

    for key, val in raw.items():
        if not str(key).startswith("_subtable_") or not isinstance(val, dict):
            continue
        rows = [r for r in val.values() if isinstance(r, dict)]
        if not any("零件" in r and "參考單價" in r for r in rows):
            continue
        is_counter = any(("領料日期" in r) or ("小計成本" in r) for r in rows)
        bucket = counter if is_counter else site

        for rid, row in val.items():
            if not isinstance(row, dict):
                continue
            name = str(row.get("零件", "") or "").strip()
            part_no = str(row.get("料號", "") or "").strip()
            qty = str(row.get("數量", "") or "").strip()
            price = _to_float(row.get("參考單價"))
            # 全空列（Ragic 偶有空白尾列）→ 略過
            if not (name or part_no or qty or price):
                continue
            rec = {
                "ragic_id":   str(row.get("_ragicId", rid)),
                "part_name":  name,
                "part_no":    part_no,
                "qty":        qty,
                "unit_price": price,
            }
            if is_counter:
                seq = str(row.get("項次", "") or "").strip() or str(len(counter) + 1)
                rec["seq"] = seq
                rec["issue_date"] = _to_date(row.get("領料日期"))
                rec["subtotal"] = _to_float(row.get("小計成本"))
                counter.append(rec)
            else:
                rec["seq"] = str(len(site) + 1)
                site.append(rec)

    return site, counter


def extract_parent_fields(raw: dict) -> dict:
    """父層零件合計與專櫃區欄位（Ragic 原欄位名稱）。"""
    if not isinstance(raw, dict):
        raw = {}
    return {
        "site_parts_fee":    _to_float(raw.get("零件金額")),
        "counter_parts_fee": _to_float(raw.get("零件費用")),
        "counter_sign":      str(raw.get("專櫃簽名", "") or "").strip(),
        "counter_est_hours": str(raw.get("預估工時", "") or "").strip(),
    }
