"""
KPO 稽核 — 業務邏輯層（種子、小計）

小計口徑（全部由系統計算，使用者不可手改）
    選定項數 = 該部門本期選定的項目數
    ★ 項數   = 其中 is_key 的項目數
    滿分     = 選定項目 score 合計（例：1★＋3 項＝10＋5×3＝25）
    符合 / 不符合 / 尚未查核 = 依各項 result（pass / fail / 空）計數
    得分     = result = pass 的項目 score 合計
    達成率   = 得分 / 滿分（滿分 0 → None）；尚未查核的項目不得分
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from sqlalchemy.orm import Session

from app.models.audit_kpo import (
    AuditKpoDept, AuditKpoItem, AuditKpoPeriod, AuditKpoPeriodItem,
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


def parse_dept_order(period: AuditKpoPeriod) -> List[int]:
    out: List[int] = []
    for t in (period.dept_order or "").split(","):
        t = t.strip()
        if t.isdigit() and int(t) not in out:
            out.append(int(t))
    return out


def build_period_detail(db: Session, period: AuditKpoPeriod) -> Dict[str, object]:
    """只列出「本期有選定項目」的部門，依部門 sort_order 排列。"""
    depts = {
        d.id: d for d in db.query(AuditKpoDept).all()
    }
    by_dept: Dict[int, List[AuditKpoPeriodItem]] = {}
    for ln in period.lines:
        by_dept.setdefault(ln.department_id, []).append(ln)
    blocks = []
    order = parse_dept_order(period)
    pos = {d: i for i, d in enumerate(order)}
    # 有自訂順序的依自訂順序；其餘（之後才加入的部門）接在後面，依主檔順序
    for dept_id in sorted(by_dept, key=lambda i: (pos.get(i, 10**6), depts[i].sort_order, i)):
        lines = _ordered(by_dept[dept_id])
        blocks.append({
            "department_id": dept_id,
            "department_name": depts[dept_id].display_name,
            "lines": [_line_out(x) for x in lines],
            "subtotal": subtotal(lines),
        })
    return {
        "id": period.id, "period": period.period, "title": period.title,
        "note": period.note, "dept_order": order, "departments": blocks,
        "total": subtotal(period.lines),
    }


def build_period_summary(period: AuditKpoPeriod) -> Dict[str, object]:
    return {
        "id": period.id, "period": period.period, "title": period.title,
        "note": period.note, "created_at": period.created_at,
        "dept_count": len({ln.department_id for ln in period.lines}),
        "total": subtotal(period.lines),
    }
