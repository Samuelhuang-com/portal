"""
稽核檢查統計（合併計分）— 2026-11-02 裁示

- 稽核檢查（audit_check）與 KPO 稽核（audit_kpo）各模組的計算「不變」，本服務直接沿用：
  * 稽核檢查：compute_scores() 的 sub_count（子項數）與 pass_count（達標項數）
  * KPO：subtotal() 的 item_count（選定項數）與 pass_count（符合項數）
- 合併達標率（2026-11-12 裁示：方案 A）：
  * 直接讀模組既有的月分數（與模組頁面相同的計分函式，不另行計算）：
    系統檢查月分數 = compute_scores() 的 score（達標項 ÷ 子項）；現場稽核月分數 = subtotal() 的 score100 ÷ 100
  * 年度分數 = 各月模組分數的平均（每月等權）
  * 合併達標率 = (系統檢查年度分數 + 現場稽核年度分數) ÷ 2；某一模組無資料時，只取另一模組的年度分數
  * 不再把「項」與「點」直接相加
- 年度 = 期別年份（YYYY-MM）。某部門某月沒有資料（子項數／選定項數為 0）→ 排除不計。
- 部門比對：公司 + 部門名稱。KPO「客服停管部」對應到「客服部」（2026-11-02 裁示）。
"""
from collections import defaultdict
from typing import Dict, Tuple

from sqlalchemy.orm import Session

from app.models.audit_check import AuditPeriod, AuditSheet
from app.models.audit_kpo import AuditKpoDept
from app.models.reference_data import Company, RefDepartment
from app.services import audit_kpo_service as kpo
from app.services.audit_check_service import compute_scores

DEPT_ALIAS = {"客服停管部": "客服部"}  # 2026-11-02 裁示


def _norm_dept(name: str) -> str:
    n = (name or "").strip()
    return DEPT_ALIAS.get(n, n)


def build_score(db: Session, year: int) -> dict:
    companies = {c.id: c.name for c in db.query(Company).all()}
    ref_names = {d.id: d.name for d in db.query(RefDepartment).all()}
    kpo_names = {d.id: (d.display_name or d.name) for d in db.query(AuditKpoDept).all()}

    # (company_id, 部門名稱) → 累計
    acc: Dict[Tuple[int, str], Dict[str, object]] = defaultdict(
        lambda: {"a_sub": 0, "a_pass": 0, "k_sub": 0, "k_pass": 0, "a_scores": [], "k_scores": [],
                 "a_months": 0, "k_months": 0, "monthly": []})

    # 稽核檢查
    pids = [p.id for p in db.query(AuditPeriod).filter(AuditPeriod.period.like(f"{year}-%")).all()]
    if pids:
        for sh in db.query(AuditSheet).filter(AuditSheet.period_id.in_(pids)).all():
            period = sh.period_ref.period if sh.period_ref else ""
            for row in compute_scores(db, sh):
                if not row["sub_count"]:
                    continue  # 本月無 → 排除
                name = _norm_dept(ref_names.get(row["department_id"], row["name"]))
                cell = acc[(sh.company_id, name)]
                cell["a_sub"] += row["sub_count"]
                cell["a_pass"] += row["pass_count"]
                cell["a_months"] += 1
                if row["score"] is not None:
                    cell["a_scores"].append(row["score"])
                cell["monthly"].append({
                    "period": period, "source": "稽核檢查", "source_sheet_id": sh.id,
                    "sub": row["sub_count"], "pass": row["pass_count"],
                    "module_score": row["score"],            # 原模組：達標項數 ÷ 子項數（0~1）
                    "module_label": row["score_label"],      # 原模組畫面文字
                })

    # KPO
    for per in kpo._year_periods(db, year):
        for sh in per.sheets:
            by_dept: Dict[int, list] = {}
            for ln in sh.lines:
                by_dept.setdefault(ln.department_id, []).append(ln)
            period = per.period
            for did, lines in by_dept.items():
                st = kpo.subtotal(lines)
                if not st["item_count"]:
                    continue  # 本月無 → 排除
                name = _norm_dept(kpo_names.get(did, f"#{did}"))
                cell = acc[(sh.company_id, name)]
                cell["k_sub"] += int(st["item_count"])
                cell["k_pass"] += int(st["pass_count"])
                if st["score100"] is not None:
                    cell["k_scores"].append(st["score100"] / 100)
                cell["k_months"] += 1
                cell["monthly"].append({
                    "period": period, "source": "KPO", "source_sheet_id": sh.id,
                    "sub": int(st["item_count"]), "pass": int(st["pass_count"]),
                    "module_score": st["score100"],          # 原模組：0~100 分
                    "module_label": f"{st['pass_count']}項符合 / {st['item_count']}項選定",
                })

    blocks = []
    for cid in sorted({k[0] for k in acc}, key=lambda c: (companies.get(c, ""), c)):
        rows = []
        for (c, name), v in sorted(((k, v) for k, v in acc.items() if k[0] == cid), key=lambda kv: kv[0][1]):
            total_sub = v["a_sub"] + v["k_sub"]
            total_pass = v["a_pass"] + v["k_pass"]
            # 年度分數 = 各月模組分數平均（每月等權）；兩模組各佔一半，無資料的模組不參與
            a_score = (sum(v["a_scores"]) / len(v["a_scores"])) if v["a_scores"] else None
            k_score = (sum(v["k_scores"]) / len(v["k_scores"])) if v["k_scores"] else None
            parts = [x for x in (a_score, k_score) if x is not None]
            rate = (sum(parts) / len(parts)) if parts else None
            rows.append({
                "department": name,
                "audit_sub": v["a_sub"], "audit_pass": v["a_pass"],
                "kpo_sub": v["k_sub"], "kpo_pass": v["k_pass"],
                "total_sub": total_sub, "total_pass": total_pass,
                "rate": rate,
                "audit_score": a_score, "kpo_score": k_score,
                "audit_months": v["a_months"], "kpo_months": v["k_months"],
                "monthly": sorted(v["monthly"], key=lambda m: (m["period"], m["source"])),
            })
        blocks.append({"company_id": cid, "company_name": companies.get(cid, f"#{cid}"), "rows": rows})
    return {"year": year, "blocks": blocks}
