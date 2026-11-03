"""
退件Dashboard：各公司 → 各部門 → 每月（1～12）的送件數與退件數，以及當年度合計。
- 月份依 apply_date（申請日期）。
- 退件數 = outcome in (rejected, withdrawn)。
- 送件數 = 該期間所有未刪除紀錄。
"""
from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.return_stats import ReturnStatsRecord

RETURNED = ("rejected", "withdrawn")


def _with_rate(c: dict) -> dict:
    """月退件率 ＝ 退件 ÷ 送件；送件為 0 → None（顯示「—」，不計入全年）。"""
    c["rate"] = (c["returned"] / c["sent"]) if c["sent"] else None
    return c


def _avg_rate(cells: list) -> Optional[float]:
    """全年退件率 ＝ 有送件月份的月退件率算術平均（2026-11-03 裁示：件數為 0 的月份排除，不算 0%）。"""
    rates = [c["rate"] for c in cells if c["rate"] is not None]
    return (sum(rates) / len(rates)) if rates else None


def build_matrix(db: Session, year: int, form_type: Optional[str] = None,
                 companies: Optional[list[str]] = None) -> dict:
    q = db.query(ReturnStatsRecord).filter(
        ReturnStatsRecord.is_deleted == False,  # noqa: E712
        ReturnStatsRecord.apply_date.isnot(None),
        ReturnStatsRecord.apply_date >= date(year, 1, 1),
        ReturnStatsRecord.apply_date <= date(year, 12, 31),
    )
    if form_type:
        q = q.filter(ReturnStatsRecord.form_type == form_type)
    if companies:
        q = q.filter(ReturnStatsRecord.company.in_(companies))

    # (company, dept) → month → [sent, returned]
    cell = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    month_total = defaultdict(lambda: [0, 0])
    for r in q.all():
        m = r.apply_date.month
        c = cell[(r.company, r.dept_display)][m]
        c[0] += 1
        if r.outcome in RETURNED:
            c[1] += 1
        t = month_total[m]
        t[0] += 1
        if r.outcome in RETURNED:
            t[1] += 1

    companies_map = defaultdict(list)
    for (comp, dept), months in cell.items():
        cells = [_with_rate({"month": m, "sent": months[m][0], "returned": months[m][1]}) for m in range(1, 13)]
        sent_y = sum(c["sent"] for c in cells)
        ret_y = sum(c["returned"] for c in cells)
        companies_map[comp].append({
            "department": dept, "cells": cells,
            "year_sent": sent_y, "year_returned": ret_y,
            "year_rate": _avg_rate(cells),
        })

    order = {"樂群": 1, "日曜": 2, "台中": 3}
    blocks = []
    for comp in sorted(companies_map, key=lambda c: (order.get(c, 9), c)):
        rows = sorted(companies_map[comp], key=lambda r: r["department"])
        months_tot = [_with_rate({"month": m,
                       "sent": sum(r["cells"][m - 1]["sent"] for r in rows),
                       "returned": sum(r["cells"][m - 1]["returned"] for r in rows)}) for m in range(1, 13)]
        sent_y = sum(r["year_sent"] for r in rows)
        ret_y = sum(r["year_returned"] for r in rows)
        blocks.append({
            "company": comp, "rows": rows, "months": months_tot,
            "year_sent": sent_y, "year_returned": ret_y,
            "year_rate": _avg_rate(months_tot),
        })

    grand_sent = sum(b["year_sent"] for b in blocks)
    grand_ret = sum(b["year_returned"] for b in blocks)
    grand_months = [_with_rate({"month": m, "sent": month_total[m][0], "returned": month_total[m][1]})
                    for m in range(1, 13)]
    return {
        "year": year,
        "form_type": form_type or "",
        "companies": list(companies or []),
        "blocks": blocks,
        "months": grand_months,
        "year_sent": grand_sent,
        "year_returned": grand_ret,
        "year_rate": _avg_rate(grand_months),
    }
