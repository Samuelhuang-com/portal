"""
KPO 稽核 — 業務邏輯層（種子、小計）

小計口徑（全部由系統計算，使用者不可手改）
    選定項數 = 該部門本期選定的項目數
    ★ 項數   = 其中 is_key 的項目數
    滿分     = 選定項目 score 合計（例：1★＋3 項＝10＋5×3＝25）
    符合 / 不符合 / 尚未查核 = 依各項 result（pass / fail / 空）計數
    得分     = result = pass 的項目 score 合計
    達成率   = 得分 / 滿分（滿分 0 → None）；尚未查核的項目不得分
    本期分數 = 得分 ÷ 滿分 × 100，四捨五入取整數，不呈現 %（2026-10-11；例 10÷40 → 25；滿分 0 → None）

層級（2026-10-11）：期別 → 公司別稽核單（audit_kpo_sheets）→ 受稽部門（audit_kpo_sheet_depts）→ 選定項目。
小計在「部門」「公司稽核單」「整期」三層都用同一個 subtotal()。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from sqlalchemy.orm import Session

from app.models.audit_kpo import (
    AuditKpoDept, AuditKpoItem, AuditKpoPeriod, AuditKpoPeriodItem, AuditKpoSheet,
)

SEED_FILE = Path(__file__).with_name("audit_kpo_seed.json")


def default_score(is_key: bool) -> int:
    """Excel 規則：★ 重點項 10 分，其餘 5 分（16 項合計 100）。"""
    return 10 if is_key else 5


def seed_kpo_master(db: Session) -> int:
    """
    依 Excel「財#1稽核系統建構-整合」植入 9 個部門與各部門稽核項目。
    冪等：只在 audit_kpo_departments 完全為空時植入，不覆寫使用者後續的任何修改。
    回傳新增的部門數。
    """
    if db.query(AuditKpoDept.id).first() is not None:
        return 0
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    # 用 Core 只寫原始欄位：kpoaud 遷移執行當下，後續遷移（kpoaud3）新增的欄位尚不存在，
    # 不能走 ORM（ORM 會 INSERT 全部欄位）。
    dt, it_t = AuditKpoDept.__table__, AuditKpoItem.__table__
    for d in data:
        dept_id = db.execute(
            dt.insert().values(
                name=d["name"], source_title=d.get("source_title"),
                sort_order=d["sort_order"], is_active=True,
            ).returning(dt.c.id)
        ).scalar_one()
        rows = [
            dict(department_id=dept_id, item_no=it["item_no"], is_key=it["is_key"],
                 name=it["name"], score=it["score"], method=it.get("method"),
                 sort_order=(idx + 1) * 10, is_active=True)
            for idx, it in enumerate(d["items"])
        ]
        if rows:
            db.execute(it_t.insert(), rows)
    db.commit()
    return len(data)


def subtotal(lines: Iterable[AuditKpoPeriodItem]) -> Dict[str, object]:
    item_count = key_count = full = passed = failed = pending = earned = 0
    for ln in lines:
        item_count += 1
        key_count += 1 if ln.is_key else 0
        sc = int(ln.score or 0)
        full += sc
        if ln.result == "pass":
            passed += 1
            earned += sc
        elif ln.result == "fail":
            failed += 1
        else:
            pending += 1
    return {
        "item_count": item_count, "key_count": key_count, "full_score": full,
        "pass_count": passed, "fail_count": failed, "pending_count": pending,
        "earned_score": earned,
        "rate": round(earned / full, 4) if full else None,
        # 本期分數：得分÷滿分×100 四捨五入取整數（2026-10-11 裁示，不呈現 %）。
        # 用整數運算避免浮點誤差（例 12.5 要進位成 13，不能被 round() 的銀行家捨入吃掉）。
        "score100": ((earned * 200 + full) // (2 * full)) if full else None,
    }


def _line_out(ln: AuditKpoPeriodItem) -> Dict[str, object]:
    return {
        "id": ln.id, "department_id": ln.department_id,
        "source_item_id": ln.source_item_id, "item_no": ln.item_no,
        "is_key": bool(ln.is_key), "name": ln.name, "score": int(ln.score or 0),
        "method": ln.method, "result": ln.result, "remark": ln.remark,
        "sort_order": ln.sort_order,
    }


def _ordered(lines: List[AuditKpoPeriodItem]) -> List[AuditKpoPeriodItem]:
    return sorted(lines, key=lambda x: (x.sort_order or 0, x.item_no or 0, x.id))


def _company_name(sheet: AuditKpoSheet) -> str:
    return sheet.company.name if sheet.company is not None else f"公司#{sheet.company_id}"


def build_sheet_block(sheet: AuditKpoSheet) -> Dict[str, object]:
    """一張公司稽核單：依「受稽部門」順序列出每個部門（沒選項目的部門也列出，才能按「選擇項目」）。"""
    by_dept: Dict[int, List[AuditKpoPeriodItem]] = {}
    for ln in sheet.lines:
        by_dept.setdefault(ln.department_id, []).append(ln)
    blocks = []
    for sd in sorted(sheet.departments, key=lambda x: (x.sort_order or 0, x.id)):
        lines = _ordered(by_dept.get(sd.department_id, []))
        blocks.append({
            "department_id": sd.department_id,
            "department_name": sd.department.display_name,
            "lines": [_line_out(x) for x in lines],
            "subtotal": subtotal(lines),
        })
    return {
        "id": sheet.id, "company_id": sheet.company_id, "company_name": _company_name(sheet),
        "departments": blocks, "total": subtotal(sheet.lines),
    }


def build_period_detail(db: Session, period: AuditKpoPeriod) -> Dict[str, object]:
    """期別明細：公司別稽核單（依建立順序）→ 受稽部門 → 稽核項目。"""
    return {
        "id": period.id, "period": period.period, "title": period.title,
        "note": period.note,
        "sheets": [build_sheet_block(sh) for sh in period.sheets],
        "total": subtotal(period.lines),
    }


def build_period_summary(period: AuditKpoPeriod) -> Dict[str, object]:
    return {
        "id": period.id, "period": period.period, "title": period.title,
        "note": period.note, "created_at": period.created_at,
        "sheets": [
            {"id": sh.id, "company_id": sh.company_id, "company_name": _company_name(sh),
             "dept_count": len(sh.departments)}
            for sh in period.sheets
        ],
        "dept_count": sum(len(sh.departments) for sh in period.sheets),
        "total": subtotal(period.lines),
    }


def dept_history(db: Session, period: AuditKpoPeriod, sheet: AuditKpoSheet, dept_id: int) -> Dict[str, object]:
    """同公司、同部門在其他期別的歷史（不含本期）。

    2026-10-11 裁示：
      - 範圍＝同公司 × 同部門；不含目前這一期
      - 期別數只算「該部門有選定項目」的期別
      - 分數＝各期「本期分數」(得分÷滿分×100) 加總；平均分數＝分數÷期別數
      - 項目標記＝該主檔項目曾被選定的期別＋判定（沒填判定＝未查核）
    """
    sheets = (
        db.query(AuditKpoSheet)
        .filter(AuditKpoSheet.company_id == sheet.company_id, AuditKpoSheet.period_id != period.id)
        .all()
    )
    rows = []
    items: Dict[int, List[Dict[str, object]]] = {}
    for sh in sheets:
        lines = [ln for ln in sh.lines if ln.department_id == dept_id]
        if not lines:
            continue
        per = sh.period_ref
        rows.append({"period_id": per.id, "period": per.period, "score100": subtotal(lines)["score100"]})
        for ln in lines:
            if ln.source_item_id is not None:
                items.setdefault(ln.source_item_id, []).append(
                    {"period_id": per.id, "period": per.period, "result": ln.result})
    rows.sort(key=lambda x: (x["period"], x["period_id"]))
    for marks in items.values():
        marks.sort(key=lambda x: (x["period"], x["period_id"]))
    total = sum(int(r["score100"] or 0) for r in rows)
    return {
        "periods": rows, "period_count": len(rows), "score_sum": total,
        "score_avg": round(total / len(rows), 1) if rows else None,
        "items": items,
    }


def dashboard(db: Session, year: int | None) -> Dict[str, object]:
    """年度 Dashboard：公司 × 部門 × 月份的本期分數。

    2026-10-11 裁示：
      - 同月多期 → 格子取該月各期「本期分數」的平均
      - 只列該公司年度內有稽核（有選定項目）的部門；沒稽核的部門不列（2026-10-11 改，畫面較乾淨）
      - 公司＝該年度有建立稽核單的公司；部門與公司別無連動，每家公司都列全部部門
      - 年度平均＝各期本期分數 ÷ 期別數（只算該部門有選定項目的期別）
    """
    all_periods = db.query(AuditKpoPeriod.period).distinct().all()
    years = sorted({int(p[0][:4]) for p in all_periods}, reverse=True)
    if year is None:
        from app.core.time import twnow
        year = years[0] if years else twnow().year
    depts = (
        db.query(AuditKpoDept).filter(AuditKpoDept.is_active.is_(True))
        .order_by(AuditKpoDept.sort_order, AuditKpoDept.id).all()
    )
    sheets = (
        db.query(AuditKpoSheet).join(AuditKpoPeriod, AuditKpoSheet.period_id == AuditKpoPeriod.id)
        .filter(AuditKpoPeriod.period.like(f"{year}-%")).all()
    )
    by_company: Dict[int, List[AuditKpoSheet]] = {}
    for sh in sheets:
        by_company.setdefault(sh.company_id, []).append(sh)
    companies = []
    for cid, shs in sorted(by_company.items(), key=lambda kv: (_company_name(kv[1][0]), kv[0])):
        rows = []
        for d in depts:
            months: Dict[int, List[Dict[str, object]]] = {}
            for sh in shs:
                lines = [ln for ln in sh.lines if ln.department_id == d.id]
                if not lines:
                    continue
                per = sh.period_ref
                months.setdefault(int(per.period[5:7]), []).append(
                    {"period_id": per.id, "period": per.period, "score100": subtotal(lines)["score100"]})
            month_out: Dict[int, Dict[str, object]] = {}
            total = count = 0
            for m, ps in months.items():
                ps.sort(key=lambda x: (x["period"], x["period_id"]))
                vals = [int(x["score100"]) for x in ps if x["score100"] is not None]
                total += sum(vals); count += len(vals)
                month_out[m] = {
                    "avg": round(sum(vals) / len(vals), 1) if vals else None,
                    "count": len(ps), "periods": ps,
                }
            if not months:
                continue  # 2026-10-11 改：只列年度內有稽核的部門
            rows.append({
                "department_id": d.id, "department_name": d.name, "months": month_out,
                "period_count": sum(len(v) for v in months.values()), "score_sum": total,
                "avg": round(total / count, 1) if count else None,
            })
        companies.append({"company_id": cid, "company_name": _company_name(shs[0]), "rows": rows})
    return {"year": year, "years": years or [year], "companies": companies}


# ════════════════════════════════════════════════════════════════════════════
# 分數統計（2026-10-13）— 比照系統建置稽核的「分數統計」
# ════════════════════════════════════════════════════════════════════════════
def _year_periods(db: Session, year: int) -> List[AuditKpoPeriod]:
    return (
        db.query(AuditKpoPeriod).filter(AuditKpoPeriod.period.like(f"{year}-%"))
        .order_by(AuditKpoPeriod.period, AuditKpoPeriod.id).all()
    )


def _stat_year(db: Session, year: int | None) -> int:
    if year is not None:
        return year
    ys = sorted({int(p[0][:4]) for p in db.query(AuditKpoPeriod.period).distinct().all()}, reverse=True)
    if ys:
        return ys[0]
    from app.core.time import twnow
    return twnow().year


def statistics(db: Session, year: int | None, company_id: int | None = None) -> Dict[str, object]:
    """年度分數統計：每家公司一個區塊，欄＝期別、列＝受稽部門。
    格子＝本期分數（score100）＋「N項符合 / M項選定」；最後一列「查核完成」＝已查核項數 / 選定項數。"""
    year = _stat_year(db, year)
    periods = _year_periods(db, year)
    seen: Dict[str, int] = {}
    col_label: Dict[int, str] = {}
    for p in periods:
        seen[p.period] = seen.get(p.period, 0) + 1
        col_label[p.id] = p.period if seen[p.period] == 1 else f"{p.period} ({seen[p.period]})"

    by_company: Dict[int, List[AuditKpoSheet]] = {}
    for per in periods:
        for sh in per.sheets:
            if company_id is not None and sh.company_id != company_id:
                continue
            by_company.setdefault(sh.company_id, []).append(sh)

    dept_rows = {d.id: d for d in db.query(AuditKpoDept).all()}
    blocks = []
    for cid, shs in sorted(by_company.items(), key=lambda kv: (_company_name(kv[1][0]), kv[0])):
        shs.sort(key=lambda sh: (sh.period_ref.period, sh.period_ref.id))
        labels = [col_label[sh.period_id] for sh in shs]
        dept_ids: Dict[int, None] = {}
        per_cell: Dict[int, Dict[str, Dict[str, object]]] = {}
        completion = []
        for sh, label in zip(shs, labels):
            by_dept: Dict[int, List[AuditKpoPeriodItem]] = {}
            for ln in sh.lines:
                by_dept.setdefault(ln.department_id, []).append(ln)
            for did, lines in by_dept.items():
                st = subtotal(lines)
                dept_ids[did] = None
                per_cell.setdefault(did, {})[label] = {
                    "period": label, "period_id": sh.period_id, "sheet_id": sh.id, "department_id": did,
                    "score": st["score100"], "pass_count": st["pass_count"], "fail_count": st["fail_count"],
                    "pending_count": st["pending_count"], "item_count": st["item_count"],
                    "label": f"{st['pass_count']}項符合 / {st['item_count']}項選定",
                }
            tot = subtotal(sh.lines)
            checked = tot["pass_count"] + tot["fail_count"]
            completion.append({
                "period": label, "period_id": sh.period_id, "sheet_id": sh.id, "department_id": None,
                "score": tot["score100"], "pass_count": tot["pass_count"], "fail_count": tot["fail_count"],
                "pending_count": tot["pending_count"], "item_count": tot["item_count"],
                "label": f"{checked}/{tot['item_count']}" if tot["item_count"] else "—",
            })
        order = sorted(dept_ids, key=lambda i: ((dept_rows[i].sort_order or 0) if i in dept_rows else 0, i))
        rows = [{
            "department_id": did,
            "name": dept_rows[did].display_name if did in dept_rows else f"#{did}",
            "cells": [per_cell[did].get(lb) or {
                "period": lb, "period_id": None, "sheet_id": None, "department_id": did, "score": None,
                "pass_count": 0, "fail_count": 0, "pending_count": 0, "item_count": 0, "label": "本月無",
            } for lb in labels],
        } for did in order]
        blocks.append({
            "company_id": cid, "company_name": _company_name(shs[0]),
            "periods": labels, "rows": rows, "completion": completion,
        })
    years = sorted({int(p[0][:4]) for p in db.query(AuditKpoPeriod.period).distinct().all()}, reverse=True)
    return {"year": year, "years": years or [year], "blocks": blocks}


def flagged(db: Session, year: int | None, include_pending: bool = False) -> List[Dict[str, object]]:
    """缺失與建議清單：不符合項（可選含未查核），附備註。"""
    year = _stat_year(db, year)
    out: List[Dict[str, object]] = []
    for per in _year_periods(db, year):
        for sh in per.sheets:
            for ln in _ordered(list(sh.lines)):
                if ln.result == "fail":
                    label = "不符合"
                elif include_pending and ln.result not in ("pass", "fail"):
                    label = "未查核"
                elif ln.result == "pass":
                    continue
                else:
                    continue
                out.append({
                    "period": per.period, "period_id": per.id, "sheet_id": sh.id,
                    "company_id": sh.company_id, "company_name": _company_name(sh),
                    "department_id": ln.department_id,
                    "department_name": ln.department.display_name if ln.department is not None else "",
                    "line_id": ln.id, "item_no": ln.item_no, "is_key": bool(ln.is_key),
                    "item_name": ln.name, "result": ln.result or "", "result_label": label,
                    "remark": ln.remark or "",
                })
    out.sort(key=lambda r: (r["period"], r["company_name"], r["department_name"], r["item_no"] or 0))
    return out
