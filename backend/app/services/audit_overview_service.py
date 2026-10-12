"""
稽核總覽 Dashboard（2026-10-12）— 把「財#3 系統建置稽核」與「財#1 現場營運稽核」放進同一張矩陣。

裁示（2026-10-12 使用者）：
  - 兩種稽核的分數「並列」（每個部門兩行），不算綜合分
  - 獨立頁、選單新增「Dashboard」
分數口徑（各自沿用原模組，這裡只彙整，不重算）：
  - 財#3：達標率 × 100（audit_check_service.build_statistics 的 score ×100）
  - 財#1：本期分數 score100（audit_kpo_service.dashboard）
  - 同月多期 → 取各期分數平均（與 KPO Dashboard 一致）
列的對應鍵＝公司別 ＋ 部門名稱（兩邊部門主檔不同，以名稱對應；對不上的部門自成一列、另一行留白）。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.audit_check import AuditPeriod, AuditSheet
from app.models.audit_kpo import AuditKpoDept, AuditKpoPeriod
from app.services import audit_check_service as f3svc
from app.services import audit_kpo_service as f1svc
from app.services.audit_check_html import html_to_text


def _avg(vals: List[float]) -> Optional[float]:
    return round(sum(vals) / len(vals), 1) if vals else None


def _month_of(label: str) -> int:
    return int(label[5:7])


def _empty_line() -> dict:
    return {"months": {}, "avg": None, "count": 0}


def _finish(line: dict) -> None:
    allv: List[float] = []
    cnt = 0
    for m in line["months"].values():
        vals = m.pop("_vals")
        allv += vals
        cnt += len(m["items"])
        m["avg"] = _avg(vals)
        m["count"] = len(m["items"])
    line["avg"] = _avg(allv)
    line["count"] = cnt


def _put(line: dict, month: int, ref_id: int, label: str, score: Optional[float]) -> None:
    m = line["months"].setdefault(month, {"avg": None, "count": 0, "items": [], "_vals": []})
    m["items"].append({"id": ref_id, "label": label, "score": score})
    if score is not None:
        m["_vals"].append(score)


def build_overview(db: Session, year: Optional[int], f3_flagged: List[dict]) -> dict:
    # ── 年度清單（兩邊聯集）──
    years = {int(p[0][:4]) for p in db.query(AuditPeriod.period).distinct().all()}
    years |= {int(p[0][:4]) for p in db.query(AuditKpoPeriod.period).distinct().all()}
    years_sorted = sorted(years, reverse=True)
    if year is None:
        from app.core.time import twnow
        year = years_sorted[0] if years_sorted else twnow().year
    if year not in years_sorted:
        years_sorted = sorted(set(years_sorted) | {year}, reverse=True)

    rows: Dict[tuple, dict] = {}
    company_names: Dict[int, str] = {}

    def row_for(cid: int, cname: str, dept: str) -> dict:
        company_names[cid] = cname
        return rows.setdefault((cid, dept), {
            "company_id": cid, "company_name": cname, "department_name": dept,
            "f3": _empty_line(), "f1": _empty_line(),
        })

    # ── 財#3 ──
    stats = f3svc.build_statistics(db, year)
    periods = (
        db.query(AuditPeriod).filter(AuditPeriod.period.like(f"{year}-%"))
        .order_by(AuditPeriod.period, AuditPeriod.id).all()
    )
    label_to_pid: Dict[str, int] = {}
    seen: Dict[str, int] = {}
    for p in periods:   # 與 build_statistics 相同的欄位標籤規則
        seen[p.period] = seen.get(p.period, 0) + 1
        label_to_pid[p.period if seen[p.period] == 1 else f"{p.period} ({seen[p.period]})"] = p.id
    sheet_id: Dict[tuple, int] = {}
    if periods:
        for s in db.query(AuditSheet).filter(AuditSheet.period_id.in_([p.id for p in periods])).all():
            sheet_id[(s.company_id, s.period_id)] = s.id
    f3_periods = set()
    for blk in stats.get("blocks", []):
        cid = blk["company_id"]
        for r in blk["rows"]:
            line = row_for(cid, blk["company_name"], r["name"])["f3"]
            for c in r["cells"]:
                if c["score"] is None:
                    continue
                pid = label_to_pid.get(c["period"])
                sid = sheet_id.get((cid, pid))
                if sid is None:
                    continue
                f3_periods.add(pid)
                _put(line, _month_of(c["period"]), sid, c["period"], round(c["score"] * 100, 1))

    # ── 財#1 ──
    dash = f1svc.dashboard(db, year)
    f1_periods = set()
    for co in dash["companies"]:
        for r in co["rows"]:
            line = row_for(co["company_id"], co["company_name"], r["department_name"])["f1"]
            for m, mm in r["months"].items():
                for p in mm["periods"]:
                    if p["score100"] is None:
                        continue
                    f1_periods.add(p["period_id"])
                    _put(line, int(m), p["period_id"], p["period"], float(p["score100"]))

    out_rows = list(rows.values())
    for r in out_rows:
        _finish(r["f3"]); _finish(r["f1"])
        r["f3"]["months"] = {str(k): v for k, v in r["f3"]["months"].items()}
        r["f1"]["months"] = {str(k): v for k, v in r["f1"]["months"].items()}
    out_rows.sort(key=lambda r: (r["company_name"], r["department_name"]))

    # ── 摘要／趨勢／最低分 ──
    def summary(key: str, period_cnt: int) -> dict:
        audited = [r for r in out_rows if r[key]["avg"] is not None]
        low = min(audited, key=lambda r: r[key]["avg"]) if audited else None
        allv = [m_["avg"] for r in audited for m_ in r[key]["months"].values() if m_["avg"] is not None]
        return {
            "period_count": period_cnt, "dept_count": len(audited), "avg": _avg(allv),
            "lowest": None if low is None else {
                "company_name": low["company_name"], "department_name": low["department_name"], "avg": low[key]["avg"]},
        }

    def trend(key: str) -> List[Optional[float]]:
        out = []
        for m in range(1, 13):
            vals = [r[key]["months"][str(m)]["avg"] for r in out_rows
                    if str(m) in r[key]["months"] and r[key]["months"][str(m)]["avg"] is not None]
            out.append(_avg(vals))
        return out

    def lowest5(key: str) -> List[dict]:
        aud = sorted((r for r in out_rows if r[key]["avg"] is not None), key=lambda r: r[key]["avg"])[:5]
        return [{"company_name": r["company_name"], "department_name": r["department_name"], "avg": r[key]["avg"]}
                for r in aud]

    # ── 待改善清單 ──
    improvements: List[dict] = []
    for f in f3_flagged:
        if str(f.get("period", ""))[:4] != str(year):
            continue
        improvements.append({
            "type": "f3", "period": f["period"], "company_name": f["company_name"],
            "department_name": f["department_name"],
            "item": f"{f.get('display_no') or ''} {f.get('item_name') or ''}".strip(),
            "content": f.get("comment") or "", "result": f.get("result_label") or "",
            "sheet_id": f.get("sheet_id"), "sheet_item_id": f.get("sheet_item_id"),
            "sheet_department_id": f.get("sheet_department_id"),
        })
    dept_names = {d.id: d.name for d in db.query(AuditKpoDept).all()}
    for per in db.query(AuditKpoPeriod).filter(AuditKpoPeriod.period.like(f"{year}-%")).all():
        for sh in per.sheets:
            for ln in sh.lines:
                if ln.result != "fail":
                    continue
                no = "" if ln.item_no is None else str(ln.item_no)
                improvements.append({
                    "type": "f1", "period": per.period, "company_name": f1svc._company_name(sh),
                    "department_name": dept_names.get(ln.department_id, ""),
                    "item": f"{'★' if ln.is_key else ''}{no} {ln.name}".strip(),
                    "content": html_to_text(ln.remark) or "", "result": "不符合",
                    "period_id": per.id, "line_id": ln.id,
                })
    improvements.sort(key=lambda x: (x["period"], x["company_name"], x["department_name"], x["type"]))

    return {
        "year": year, "years": years_sorted,
        "companies": [{"company_id": k, "company_name": v} for k, v in sorted(company_names.items(), key=lambda kv: kv[1])],
        "rows": out_rows,
        "summary": {"f3": summary("f3", len(f3_periods)), "f1": summary("f1", len(f1_periods)),
                    "improvement_count": len(improvements)},
        "trend": {"f3": trend("f3"), "f1": trend("f1")},
        "lowest": {"f3": lowest5("f3"), "f1": lowest5("f1")},
        "improvements": improvements,
    }
