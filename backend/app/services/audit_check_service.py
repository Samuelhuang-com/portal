"""
稽核檢查 — 業務邏輯層（分數、完成率、缺失彙整、覆核帶入、統計）

⚠️ 口徑硬規則（docs/SPEC_audit_check.md §4，已用 Excel 202608/202609 實際數字回算驗證）
────────────────────────────────────────────────────────────────────────────
各部門分數
    子項數   = 該部門欄中「評語非空」的 2 階子項格子數（1 階大項列不計分）
               ＋ 覆核區（待補正項目／結果）有填時算 1 項
                 —— 期別開關 review_counts_in_score 控制，預設 True
    達標項數 = 上述格子中，判定類型 counts_as_pass = True 的數量
               （覆核區只要任一格判定為不達標，該項即不達標）
    分數     = 達標項數 / 子項數；子項數 = 0 → None（畫面顯示「本月無」）

⚠️ 為什麼覆核要算一項（2026-09-20 用 Excel 實測反推）
    Excel 的「稽核子項數／達標項數」是人工填的，用「只算子項」的規則回算，
    17 個部門欄只有 7 欄對得上；把覆核算成一項之後變成 13 欄對得上
    （春大直 管理 8/8、資訊 4/4、工程 6/5、客服停管 3/0 全部命中）。
    剩下 4 欄對不上的，來源是 Excel 本身的人工計數與字色不一致
    （例如同樣是「架構無」，春大直財務有算、日曜財務沒算），無法用任何
    單一規則重現 —— 這正是改成系統自動計算要解決的問題。
    若使用者認為覆核不該計分，把期別的 review_counts_in_score 關掉即可。

稽核完成率
    分母 = 該稽核單勾選的 1 階大項數 × 期別 goal_minor（預設 3）＋ completion_adjust
    分子 = 實際「至少有一個部門填了評語」的 2 階子項數
    完成率 = 分子 / 分母

    completion_adjust 調整的是**分子（已完成數）**，不是分母 —— 比照 Excel 的寫法
    「3*3-1=8     8/9=88.9%」：應完成 9 項、其中 1 項本期沒做到 → 完成 8 項、分母仍是 9。
    2026-08 日曜就是這個情況：9 個子項在表上全都有評語，但稽核人員判定其中一項本期
    沒做到。這種判斷無法從資料推導（格子看起來是滿的），只能讓稽核人員自己填 -1。

回算驗證（2026-09）
    春大直 工程 6 項 / 5 項達標 = 0.8333…  管理 8/8 = 1  客服停管 3/0 = 0
    兩店完成率皆 3*3=9、9/9 = 100%
    日曜 2026-08 為 3*3-1=8 → 8/9 = 0.889
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.audit_check import (
    AuditCell, AuditItem, AuditItemTarget, AuditPeriod, AuditResultType,
    AuditReview, AuditSheet, AuditSheetDepartment, AuditSheetItem,
)
from app.models.reference_data import Company, RefDepartment


# ── 判定類型 ───────────────────────────────────────────────────────────────
DEFAULT_RESULT_TYPES = [
    # code,     label,  color,      counts_as_pass, include_in_summary, is_default
    ("ok",     "達標", "#262626", True,  False, True),
    ("deduct", "扣分", "#cf1322", False, True,  False),
    ("advice", "建議", "#1677ff", True,  True,  False),
]


def seed_result_types(db: Session) -> None:
    """首次使用時植入三筆系統內建判定類型（冪等）。"""
    existing = {r.code for r in db.query(AuditResultType).all()}
    changed = False
    for idx, (code, label, color, is_pass, in_summary, is_default) in enumerate(DEFAULT_RESULT_TYPES):
        if code in existing:
            continue
        db.add(AuditResultType(
            code=code, label=label, color=color,
            counts_as_pass=is_pass, include_in_summary=in_summary,
            is_default=is_default, is_system=True,
            sort_order=idx * 10, is_active=True,
        ))
        changed = True
    if changed:
        db.commit()


def get_result_types(db: Session) -> List[AuditResultType]:
    seed_result_types(db)
    return (
        db.query(AuditResultType)
        .order_by(AuditResultType.sort_order, AuditResultType.id)
        .all()
    )


def result_type_maps(db: Session) -> Tuple[Dict[str, AuditResultType], str]:
    """回傳 (code -> 判定類型, 預設 code)。"""
    types = get_result_types(db)
    by_code = {t.code: t for t in types}
    default_code = next((t.code for t in types if t.is_default and t.is_active), None)
    if default_code is None:
        default_code = types[0].code if types else "ok"
    return by_code, default_code


# ── 小工具 ─────────────────────────────────────────────────────────────────
def _filled(text: Optional[str]) -> bool:
    return bool(text and text.strip())


def sheet_item_name(si: AuditSheetItem) -> str:
    """
    稽核單某一列的顯示名稱：一律以本期快照 item_name 為準。
    快照為空（理論上 migration audchkn 已補齊）才退回主檔目前名稱。
    """
    if si.item_name:
        return si.item_name
    return si.item.name if si.item else ""


def item_in_use(db: Session, item_id: int) -> bool:
    """檢查項是否已被任一期稽核單引用（被引用者刪除時改為軟刪除；改名不受限）。"""
    return db.query(AuditSheetItem.id).filter(AuditSheetItem.item_id == item_id).first() is not None


def items_in_use(db: Session) -> set:
    return {row[0] for row in db.query(AuditSheetItem.item_id).distinct().all()}


def department_label(sd: AuditSheetDepartment) -> str:
    if sd.column_label:
        return sd.column_label
    return sd.department.name if sd.department else f"#{sd.department_id}"


def audited_label(sheet: AuditSheet) -> str:
    """還原 Excel 的「2026.09.07下午資料查核」字樣。"""
    if not sheet.audited_on:
        return ""
    base = sheet.audited_on.strftime("%Y.%m.%d")
    return f"{base}{sheet.audited_session or ''}資料查核"


# ── 分數 ───────────────────────────────────────────────────────────────────
def compute_scores(
    db: Session,
    sheet: AuditSheet,
    cells: Optional[Sequence[AuditCell]] = None,
) -> List[dict]:
    by_code, _ = result_type_maps(db)
    if cells is None:
        cells = db.query(AuditCell).filter(AuditCell.sheet_id == sheet.id).all()

    # 只有 2 階子項計分
    minor_ids = {si.id for si in sheet.items if si.parent_sheet_item_id is not None}

    sub: Dict[int, int] = {}
    passed: Dict[int, int] = {}
    for c in cells:
        if c.sheet_item_id not in minor_ids or not _filled(c.comment):
            continue
        sub[c.sheet_department_id] = sub.get(c.sheet_department_id, 0) + 1
        rt = by_code.get(c.result_code)
        if rt is None or rt.counts_as_pass:
            passed[c.sheet_department_id] = passed.get(c.sheet_department_id, 0) + 1

    # 覆核區算一項（可由期別開關關閉）
    if sheet.period_ref is None or sheet.period_ref.review_counts_in_score:
        for rv in sheet.reviews:
            texts = [(rv.pending_text, rv.pending_result), (rv.result_text, rv.result_status)]
            filled_parts = [(t, code) for t, code in texts if _filled(t)]
            if not filled_parts:
                continue
            sub[rv.sheet_department_id] = sub.get(rv.sheet_department_id, 0) + 1
            ok = all(
                (by_code.get(code) is None or by_code[code].counts_as_pass)
                for _t, code in filled_parts
            )
            if ok:
                passed[rv.sheet_department_id] = passed.get(rv.sheet_department_id, 0) + 1

    out: List[dict] = []
    for sd in sorted(sheet.departments, key=lambda d: (d.sort_order, d.id)):
        n = sub.get(sd.id, 0)
        p = passed.get(sd.id, 0)
        if n == 0:
            out.append({
                "sheet_department_id": sd.id,
                "department_id": sd.department_id,
                "name": department_label(sd),
                "sub_count": 0,
                "pass_count": 0,
                "score": None,
                "score_label": "本月無",
            })
        else:
            out.append({
                "sheet_department_id": sd.id,
                "department_id": sd.department_id,
                "name": department_label(sd),
                "sub_count": n,
                "pass_count": p,
                "score": p / n,
                "score_label": f"{n}項 / {p}項達標",
            })
    return out


# ── 完成率 ─────────────────────────────────────────────────────────────────
def compute_completion(
    db: Session,
    sheet: AuditSheet,
    cells: Optional[Sequence[AuditCell]] = None,
) -> Tuple[Optional[float], str]:
    if cells is None:
        cells = db.query(AuditCell).filter(AuditCell.sheet_id == sheet.id).all()

    goal_minor = sheet.period_ref.goal_minor if sheet.period_ref else 3
    major_count = len([si for si in sheet.items if si.parent_sheet_item_id is None])
    denominator = major_count * goal_minor          # 本期「應完成」的子項數
    if denominator <= 0:
        return None, ""

    filled_items = {c.sheet_item_id for c in cells if _filled(c.comment)}
    minor_ids = {si.id for si in sheet.items if si.parent_sheet_item_id is not None}
    adjust = sheet.completion_adjust or 0
    # adjust 調整的是「已完成數」（分子），分母仍是 3*3 —— 比照 Excel「3*3-1=8  8/9=88.9%」
    numerator = max(0, min(len(filled_items & minor_ids) + adjust, denominator))

    rate = numerator / denominator
    pct = round(rate * 1000) / 10
    pct_txt = f"{pct:.1f}".rstrip("0").rstrip(".")
    formula = f"{major_count}*{goal_minor}"
    if adjust:
        formula += f"{adjust:+d}"
    label = f"{formula}={numerator}　{numerator}/{denominator} = {pct_txt}%"
    return rate, label


# ── 缺失自動彙整 ───────────────────────────────────────────────────────────
def compute_deficiencies(
    db: Session,
    sheet: AuditSheet,
    cells: Optional[Sequence[AuditCell]] = None,
    kind: str = "deficiency",
) -> Dict[int, str]:
    """
    回傳 {sheet_department_id: 彙整文字}（僅自動彙整，不含人工覆寫）。

    2026-10-01 使用者要求「缺失下面多一列＝建議」，同一批「列入彙整」的判定拆成兩列：
      kind="deficiency"：不算達標者（如扣分）→「缺失」列
      kind="suggestion"：算達標者（如建議）  →「建議」列
    """
    by_code, _ = result_type_maps(db)
    if cells is None:
        cells = db.query(AuditCell).filter(AuditCell.sheet_id == sheet.id).all()

    order = {si.id: (si.sort_order, si.id) for si in sheet.items}
    buckets: Dict[int, List[Tuple[Tuple[int, int], int, str]]] = {}
    for c in cells:
        if not _filled(c.comment):
            continue
        rt = by_code.get(c.result_code)
        if rt is None or not rt.include_in_summary:
            continue
        if (kind == "suggestion") != bool(rt.counts_as_pass):
            continue
        rank = 0
        buckets.setdefault(c.sheet_department_id, []).append(
            (order.get(c.sheet_item_id, (9999, 0)), rank, c.comment.strip())
        )

    result: Dict[int, str] = {}
    for dept_id, rows in buckets.items():
        rows.sort(key=lambda r: (r[1], r[0]))
        result[dept_id] = "\n".join(r[2] for r in rows)
    return result


# ── 稽核單完整內容 ─────────────────────────────────────────────────────────
def build_sheet_detail(db: Session, sheet: AuditSheet) -> dict:
    cells = db.query(AuditCell).filter(AuditCell.sheet_id == sheet.id).all()
    auto_def = compute_deficiencies(db, sheet, cells)
    auto_sug = compute_deficiencies(db, sheet, cells, kind="suggestion")

    departments = []
    for sd in sorted(sheet.departments, key=lambda d: (d.sort_order, d.id)):
        departments.append({
            "id": sd.id,
            "department_id": sd.department_id,
            "name": department_label(sd),
            "sort_order": sd.sort_order,
            "deficiency_override": sd.deficiency_override,
            "deficiency": sd.deficiency_override if _filled(sd.deficiency_override) else auto_def.get(sd.id, ""),
            "suggestion_override": sd.suggestion_override,
            "suggestion": sd.suggestion_override if _filled(sd.suggestion_override) else auto_sug.get(sd.id, ""),
        })

    targets: Dict[int, List[int]] = {}
    for t in db.query(AuditItemTarget).join(
        AuditSheetItem, AuditSheetItem.id == AuditItemTarget.sheet_item_id
    ).filter(AuditSheetItem.sheet_id == sheet.id).all():
        targets.setdefault(t.sheet_item_id, []).append(t.department_id)

    items = []
    for si in sorted(sheet.items, key=lambda i: (i.sort_order, i.id)):
        items.append({
            "id": si.id,
            "item_id": si.item_id,
            "parent_sheet_item_id": si.parent_sheet_item_id,
            "level": 2 if si.parent_sheet_item_id is not None else 1,
            "display_no": si.display_no,
            "name": sheet_item_name(si),
            "master_name": si.item.name if (si.item and si.item.deleted_at is None) else None,
            "scope_note": si.scope_note,
            "target_department_ids": targets.get(si.id, []),
            "sort_order": si.sort_order,
        })

    rate, rate_label = compute_completion(db, sheet, cells)
    company = db.query(Company).filter(Company.id == sheet.company_id).first()

    return {
        "id": sheet.id,
        "period_id": sheet.period_id,
        "period": sheet.period_ref.period if sheet.period_ref else "",
        "title": sheet.period_ref.title if sheet.period_ref else "",
        "goal_major": sheet.period_ref.goal_major if sheet.period_ref else 3,
        "goal_minor": sheet.period_ref.goal_minor if sheet.period_ref else 3,
        "review_counts_in_score": sheet.period_ref.review_counts_in_score if sheet.period_ref else True,
        "company_id": sheet.company_id,
        "company_name": company.name if company else "",
        "audited_on": sheet.audited_on,
        "audited_session": sheet.audited_session,
        "audited_label": audited_label(sheet),
        "executor_label": sheet.executor_label,
        "completion_adjust": sheet.completion_adjust or 0,
        "remark": sheet.remark,
        "status": sheet.status,
        "departments": departments,
        "items": items,
        "cells": [
            {
                "sheet_item_id": c.sheet_item_id,
                "sheet_department_id": c.sheet_department_id,
                "comment": c.comment,
                "result_code": c.result_code,
                "updated_at": c.updated_at,
            }
            for c in cells
        ],
        "scores": compute_scores(db, sheet, cells),
        "reviews": [
            {
                "sheet_department_id": r.sheet_department_id,
                "source_period": r.source_period,
                "pending_text": r.pending_text,
                "pending_result": r.pending_result,
                "result_text": r.result_text,
                "result_status": r.result_status,
            }
            for r in sheet.reviews
        ],
        "completion_rate": rate,
        "completion_label": rate_label,
        "result_types": get_result_types(db),
    }


# ── 稽核單建立 / 版面調整 ──────────────────────────────────────────────────
def apply_layout(
    db: Session,
    sheet: AuditSheet,
    department_ids: Sequence[int],
    item_specs: Sequence,
) -> None:
    """
    建立或調整稽核單的部門欄與檢查項列。

    item_specs 只需要給 2 階子項或 1 階大項的 item_id；1 階大項會依主檔的
    parent_id 自動補齊並排在子項之前，display_no 也一併重算。
    移除的列／欄，其格子會被 ON DELETE CASCADE 一併刪除。
    """
    # ── 部門欄 ────────────────────────────────────────────────────────────
    existing_depts = {sd.department_id: sd for sd in sheet.departments}
    keep_depts = set(department_ids)
    for dept_id, sd in list(existing_depts.items()):
        if dept_id not in keep_depts:
            db.delete(sd)
    for idx, dept_id in enumerate(department_ids):
        sd = existing_depts.get(dept_id)
        if sd is None:
            sd = AuditSheetDepartment(sheet_id=sheet.id, department_id=dept_id, sort_order=idx * 10)
            db.add(sd)
        else:
            sd.sort_order = idx * 10
    db.flush()

    # ── 檢查項列（先算出「大項 → 子項」的完整結構）────────────────────────
    spec_by_item = {s.item_id: s for s in item_specs}
    all_items = {i.id: i for i in db.query(AuditItem).filter(AuditItem.id.in_(spec_by_item.keys())).all()}
    # 已從主檔刪除（軟刪除）的項目：本張原本就有的列照舊保留；不允許新加入
    _already = {si.item_id for si in sheet.items}
    all_items = {
        iid: it for iid, it in all_items.items()
        if it.deleted_at is None or iid in _already
    }

    majors: List[int] = []
    minors_by_major: Dict[int, List[int]] = {}
    for item_id in spec_by_item.keys():
        it = all_items.get(item_id)
        if it is None:
            continue
        if it.parent_id is None:
            if item_id not in majors:
                majors.append(item_id)
        else:
            if it.parent_id not in majors:
                majors.append(it.parent_id)
            minors_by_major.setdefault(it.parent_id, []).append(item_id)

    # 排序：本張既有的列保留目前順序（含使用者在稽核單上拖曳調整過的，2026-10-01）；
    #       新加入的列依主檔 sort_order 排在既有列之後
    parents = {i.id: i for i in db.query(AuditItem).filter(AuditItem.id.in_(majors)).all()}
    prev_order = {si.item_id: si.sort_order for si in sheet.items}

    def _master_name(iid: int) -> Optional[str]:
        it = all_items.get(iid) or parents.get(iid)
        return it.name if it else None
    def _key(iid: int, src: dict) -> tuple:
        if iid in prev_order:
            return (0, prev_order[iid], 0, iid)
        return (1, 0, src[iid].sort_order if iid in src else 9999, iid)
    majors.sort(key=lambda mid: _key(mid, parents))
    for mid, lst in minors_by_major.items():
        lst.sort(key=lambda iid: _key(iid, all_items))

    existing_rows = {si.item_id: si for si in sheet.items}
    wanted = set(majors) | {i for lst in minors_by_major.values() for i in lst}
    for item_id, si in list(existing_rows.items()):
        if item_id not in wanted:
            db.delete(si)
    db.flush()

    order = 0
    major_rows: Dict[int, AuditSheetItem] = {}
    for m_idx, mid in enumerate(majors, start=1):
        row = existing_rows.get(mid)
        if row is None:
            # 新加入的列：拍下主檔當下名稱；既有列保留原快照（含使用者改過的本期名稱）
            row = AuditSheetItem(sheet_id=sheet.id, item_id=mid, item_name=_master_name(mid))
            db.add(row)
            db.flush()
        row.parent_sheet_item_id = None
        row.display_no = str(m_idx)
        row.sort_order = order
        spec = spec_by_item.get(mid)
        if spec is not None:
            row.scope_note = spec.scope_note
        order += 10
        major_rows[mid] = row

        for s_idx, iid in enumerate(minors_by_major.get(mid, []), start=1):
            child = existing_rows.get(iid)
            if child is None:
                child = AuditSheetItem(sheet_id=sheet.id, item_id=iid, item_name=_master_name(iid))
                db.add(child)
                db.flush()
            child.parent_sheet_item_id = row.id
            child.display_no = f"{m_idx}.{s_idx}"
            child.sort_order = order
            spec = spec_by_item.get(iid)
            child.scope_note = spec.scope_note if spec else None
            order += 10

            db.query(AuditItemTarget).filter(AuditItemTarget.sheet_item_id == child.id).delete()
            for dept_id in (spec.target_department_ids if spec else []):
                db.add(AuditItemTarget(sheet_item_id=child.id, department_id=dept_id))
    db.flush()


def reorder_items(db: Session, sheet: AuditSheet, sheet_item_ids: Sequence[int]) -> None:
    """
    依使用者在稽核單上拖曳後的順序重排檢查項列（2026-10-01）。

    規則：大項之間可互換（子項跟著大項走）；子項只能在同一個大項底下換位置。
    sheet_item_ids 為畫面由上到下的順序；沒列到的列維持原相對順序排在最後。
    display_no（1 / 1.1）一併重算。
    """
    rows = {si.id: si for si in sheet.items}
    pos = {sid: idx for idx, sid in enumerate(sheet_item_ids)}

    def _k(si: AuditSheetItem) -> tuple:
        return (0, pos[si.id]) if si.id in pos else (1, si.sort_order, si.id)

    majors = sorted((si for si in rows.values() if si.parent_sheet_item_id is None), key=_k)
    order = 0
    for m_idx, major in enumerate(majors, start=1):
        major.display_no = str(m_idx)
        major.sort_order = order
        order += 10
        children = sorted(
            (si for si in rows.values() if si.parent_sheet_item_id == major.id), key=_k,
        )
        for s_idx, child in enumerate(children, start=1):
            child.display_no = f"{m_idx}.{s_idx}"
            child.sort_order = order
            order += 10
    db.flush()


def carry_over_reviews(db: Session, sheet: AuditSheet) -> None:
    """
    把上一期同公司的未達標項目彙整成本期「待補正項目」預設值。
    產生後即為獨立資料，之後上一期再改也不會連動。
    """
    period = sheet.period_ref
    if period is None:
        return
    # 2026-09-29：同一個月份可以有多期 → 「上一期」＝同公司、排在本期之前的最近一張稽核單
    # （先比月份、同月再比期別 id），不再假設一個月只有一期。
    from sqlalchemy import and_, or_
    row = (
        db.query(AuditSheet, AuditPeriod)
        .join(AuditPeriod, AuditPeriod.id == AuditSheet.period_id)
        .filter(
            AuditSheet.company_id == sheet.company_id,
            AuditSheet.id != sheet.id,
            or_(
                AuditPeriod.period < period.period,
                and_(AuditPeriod.period == period.period, AuditPeriod.id < period.id),
            ),
        )
        .order_by(AuditPeriod.period.desc(), AuditPeriod.id.desc())
        .first()
    )
    if row is None:
        return
    prev_sheet, prev = row

    by_code, _ = result_type_maps(db)
    prev_cells = db.query(AuditCell).filter(AuditCell.sheet_id == prev_sheet.id).all()
    prev_dept_map = {sd.id: sd.department_id for sd in prev_sheet.departments}

    texts: Dict[int, List[str]] = {}
    for c in prev_cells:
        if not _filled(c.comment):
            continue
        rt = by_code.get(c.result_code)
        if rt is None or rt.counts_as_pass:
            continue
        dept_id = prev_dept_map.get(c.sheet_department_id)
        if dept_id is None:
            continue
        texts.setdefault(dept_id, []).append(c.comment.strip())

    for sd in sheet.departments:
        pending = texts.get(sd.department_id)
        if not pending:
            continue
        exists = (
            db.query(AuditReview)
            .filter(AuditReview.sheet_id == sheet.id, AuditReview.sheet_department_id == sd.id)
            .first()
        )
        if exists is not None:
            continue
        db.add(AuditReview(
            sheet_id=sheet.id,
            sheet_department_id=sd.id,
            source_period=prev.period,
            pending_text="\n".join(pending),
            pending_result="ok",
            result_status="ok",
            updated_at=twnow(),
        ))
    db.flush()


# ── 跨月統計（對應 Excel「分數統計」Sheet）─────────────────────────────────
def build_statistics(db: Session, year: int, company_id: Optional[int] = None) -> dict:
    periods = (
        db.query(AuditPeriod)
        .filter(AuditPeriod.period.like(f"{year}-%"))
        .order_by(AuditPeriod.period, AuditPeriod.id)
        .all()
    )
    period_ids = [p.id for p in periods]
    # 2026-09-29：同月可多期 → 欄位以期別 id 區分；同月第 2 期起標示「YYYY-MM (2)」
    col_label: Dict[int, str] = {}
    _seen: Dict[str, int] = {}
    for p in periods:
        _seen[p.period] = _seen.get(p.period, 0) + 1
        col_label[p.id] = p.period if _seen[p.period] == 1 else f"{p.period} ({_seen[p.period]})"
    if not period_ids:
        return {"year": year, "note": None, "blocks": []}

    q = db.query(AuditSheet).filter(AuditSheet.period_id.in_(period_ids))
    if company_id is not None:
        q = q.filter(AuditSheet.company_id == company_id)
    sheets = q.all()

    companies = {c.id: c for c in db.query(Company).all()}
    dept_names = {d.id: d.name for d in db.query(RefDepartment).all()}

    by_company: Dict[int, Dict[str, AuditSheet]] = {}
    for s in sheets:
        if s.period_id not in col_label:
            continue
        by_company.setdefault(s.company_id, {})[col_label[s.period_id]] = s

    blocks = []
    for cid, per_map in sorted(by_company.items()):
        period_list = [col_label[p.id] for p in periods if col_label[p.id] in per_map]
        audited_labels, major_items, completion = [], [], []
        dept_cells: Dict[int, Dict[str, dict]] = {}

        for period in period_list:
            sheet = per_map[period]
            audited_labels.append(audited_label(sheet))
            major_items.append([
                sheet_item_name(si) + (si.scope_note or "")
                for si in sorted(sheet.items, key=lambda i: (i.sort_order, i.id))
                if si.parent_sheet_item_id is None
            ])
            rate, label = compute_completion(db, sheet)
            completion.append({"period": period, "score": rate, "label": label})

            for row in compute_scores(db, sheet):
                dept_cells.setdefault(row["department_id"], {})[period] = {
                    "period": period,
                    "score": row["score"],
                    "label": row["score_label"],
                }

        rows = []
        for dept_id, per_cell in dept_cells.items():
            rows.append({
                "department_id": dept_id,
                "name": dept_names.get(dept_id, f"#{dept_id}"),
                "cells": [
                    per_cell.get(p, {"period": p, "score": None, "label": "本月無"})
                    for p in period_list
                ],
            })
        rows.sort(key=lambda r: r["name"])

        blocks.append({
            "company_id": cid,
            "company_name": companies[cid].name if cid in companies else f"#{cid}",
            "periods": period_list,
            "audited_labels": audited_labels,
            "major_items": major_items,
            "rows": rows,
            "completion": completion,
        })

    note = next((p.note for p in reversed(periods) if p.note), None)
    return {"year": year, "note": note, "blocks": blocks}
