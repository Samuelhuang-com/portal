"""
退件統計 API（規格 §6）。前綴 /api/v1/return-stats，全部需 return_reject_stats_view；
手動同步需 return_reject_stats_manage。
"""
import asyncio
import json
from datetime import date
from typing import Optional

import io
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_permission
from app.models.return_stats import ReturnStatsRecord, ReturnStatsSource, ReturnStatsStep
from app.core.excel_utils import xlsx_safe
from app.core.time import twnow
from app.services.ragic_adapter import RagicAdapter
from app.services.return_stats_parser import as_text, classify_approval, html_to_text, steps_from_approval
from app.services.return_stats_sync import RAGIC_ACCOUNT, RAGIC_SERVER, sync_return_stats, rejection_note_of, rejection_approver_of

router = APIRouter()

VIEW = "return_reject_stats_view"
MANAGE = "return_reject_stats_manage"
OUTCOMES = ["rejected", "withdrawn", "approved", "agreed", "pending", "unknown"]
OUTCOME_LABEL = {
    "rejected": "退件", "withdrawn": "退簽", "approved": "核准",
    "agreed": "同意（未完成）", "pending": "待審", "unknown": "未知",
}


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"日期格式錯誤：{s}（需 YYYY-MM-DD）")


def _filtered(
    q,
    company: Optional[list[str]], dept: Optional[list[str]],
    form_type: Optional[list[str]], form_name: Optional[list[str]],
    outcome: Optional[list[str]],
    start: Optional[str], end: Optional[str], date_field: str,
    approver: Optional[str], applicant: Optional[str], keyword: Optional[str],
    db: Session, rejection_approver: Optional[str] = None, ragic_rej: bool = False,
):
    q = q.filter(ReturnStatsRecord.is_deleted == False)  # noqa: E712
    if company:
        q = q.filter(ReturnStatsRecord.company.in_(company))
    if dept:
        q = q.filter(ReturnStatsRecord.dept_display.in_(dept))
    if form_type:
        q = q.filter(ReturnStatsRecord.form_type.in_(form_type))
    if form_name:
        q = q.filter(ReturnStatsRecord.form_name.in_(form_name))
    if outcome:
        q = q.filter(ReturnStatsRecord.outcome.in_(outcome))
    col = ReturnStatsRecord.last_sign_date if date_field == "last_sign" else ReturnStatsRecord.apply_date
    s, e = _parse_date(start), _parse_date(end)
    if s:
        q = q.filter(col >= s)
    if e:
        q = q.filter(col <= e)
    if applicant:
        q = q.filter(ReturnStatsRecord.applicant.like(f"%{applicant}%"))
    if approver:
        # 流程含簽核人：只看簽核步驟（與退件Dashboard 送件口徑一致；不含「下一位簽核人」）
        step_ids = db.query(ReturnStatsStep.record_id).filter(
            ReturnStatsStep.approver_text.like(f"%{approver}%"))
        q = q.filter(ReturnStatsRecord.id.in_(step_ids))
    if ragic_rej:
        # 簽核狀態＝REJ（退件，與 Ragic 直接統計口徑一致）
        q = q.filter(ReturnStatsRecord.ragic_status == "REJ")
    if rejection_approver:
        rej_ids = db.query(ReturnStatsStep.record_id).filter(
            ReturnStatsStep.response_code == "REJ",
            ReturnStatsStep.approver_text == rejection_approver)
        q = q.filter(ReturnStatsRecord.id.in_(rej_ids))
    if keyword:
        step_ids = db.query(ReturnStatsStep.record_id).filter(
            ReturnStatsStep.remark.like(f"%{keyword}%"))
        q = q.filter(or_(ReturnStatsRecord.purpose.like(f"%{keyword}%"),
                         ReturnStatsRecord.applicant.like(f"%{keyword}%"),
                         ReturnStatsRecord.id.in_(step_ids)))
    return q


def _filter_params(
    company: list[str] = Query(default=[]),
    dept: list[str] = Query(default=[]),
    form_type: list[str] = Query(default=[]),
    form_name: list[str] = Query(default=[]),
    outcome: list[str] = Query(default=[]),
    start: Optional[str] = None,
    end: Optional[str] = None,
    date_field: str = Query("apply", pattern="^(apply|last_sign)$"),
    approver: Optional[str] = None,
    applicant: Optional[str] = None,
    keyword: Optional[str] = None,
    rejection_approver: Optional[str] = None,
    ragic_rej: bool = Query(False),
):
    return dict(company=company, dept=dept, form_type=form_type, form_name=form_name,
                outcome=outcome, start=start, end=end, date_field=date_field,
                approver=approver, applicant=applicant, keyword=keyword,
                rejection_approver=rejection_approver, ragic_rej=ragic_rej)


@router.get("/filters", summary="篩選下拉選項")
def get_filters(db: Session = Depends(get_db), _=Depends(require_permission(VIEW))):
    sources = (db.query(ReturnStatsSource)
               .filter(ReturnStatsSource.is_active == True)  # noqa: E712
               .order_by(ReturnStatsSource.sort_order).all())
    companies = sorted({s.company for s in sources})
    depts = []
    for s in sources:
        pair = {"company": s.company, "dept": s.dept_display}
        if pair not in depts:
            depts.append(pair)
    form_names = sorted({s.form_name for s in sources})
    max_apply = db.query(func.max(ReturnStatsRecord.apply_date)).scalar()
    rej_names = sorted({n for (n,) in db.query(ReturnStatsStep.approver_text)
                        .filter(ReturnStatsStep.response_code == "REJ").distinct()
                        if n and n != "（簽名圖）"})
    return {
        "companies": companies,
        "departments": depts,
        "form_types": sorted({s.form_type for s in sources}),
        "form_names": form_names,
        "outcomes": [{"value": o, "label": OUTCOME_LABEL[o]} for o in OUTCOMES],
        "rejection_approvers": rej_names,
        "data_end": max_apply.isoformat() if max_apply else None,
    }


@router.get("/summary", summary="統計卡與依部門彙總")
def get_summary(f: dict = Depends(_filter_params), db: Session = Depends(get_db),
                _=Depends(require_permission(VIEW))):
    base = _filtered(db.query(ReturnStatsRecord), db=db, **f)
    rows = base.with_entities(ReturnStatsRecord.outcome, func.count(ReturnStatsRecord.id)).group_by(
        ReturnStatsRecord.outcome).all()
    counts = {o: 0 for o in OUTCOMES}
    for o, n in rows:
        counts[o] = n
    total = sum(counts.values())
    by_dept_rows = base.with_entities(
        ReturnStatsRecord.company, ReturnStatsRecord.dept_display,
        ReturnStatsRecord.outcome, func.count(ReturnStatsRecord.id)
    ).group_by(ReturnStatsRecord.company, ReturnStatsRecord.dept_display,
               ReturnStatsRecord.outcome).all()
    by_dept: dict = {}
    for comp, dept, o, n in by_dept_rows:
        item = by_dept.setdefault((comp, dept), {"company": comp, "dept": dept,
                                                 **{k: 0 for k in OUTCOMES}, "total": 0})
        item[o] = n
        item["total"] += n
    # 上次同步時間：每次同步都會寫入 synced_at（台北時間），取最大值即最後一次寫入
    last = db.query(func.max(ReturnStatsRecord.synced_at)).scalar()
    return {
        "total": total,
        "counts": counts,
        "by_dept": sorted(by_dept.values(), key=lambda x: (x["company"], -x["total"])),
        "last_synced_at": last.strftime("%Y-%m-%d %H:%M") if last else None,
    }


@router.get("/records", summary="清單（分頁）")
def list_records(
    f: dict = Depends(_filter_params),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_permission(VIEW)),
):
    q = _filtered(db.query(ReturnStatsRecord), db=db, **f)
    total = q.count()
    recs = (q.order_by(ReturnStatsRecord.apply_date.desc().nullslast(), ReturnStatsRecord.id.desc())
            .offset((page - 1) * page_size).limit(page_size).all())
    items = []
    for r in recs:
        items.append({
            "id": r.id, "company": r.company, "form_type": r.form_type,
            "dept": r.dept_display, "form_name": r.form_name,
            "ragic_record_id": r.ragic_record_id,
            "doc_no": _doc_no(r),
            "ragic_url": _ragic_url(r),
            "applicant": r.applicant, "apply_date": r.apply_date.isoformat() if r.apply_date else None,
            "amount": r.amount, "purpose": html_to_text(r.purpose),
            "ragic_status": r.ragic_status, "outcome": r.outcome,
            "outcome_label": OUTCOME_LABEL.get(r.outcome, r.outcome),
            "outcome_reason": r.outcome_reason,
            "rejection_note": rejection_note_of(db, r),
            "rejection_approver": rejection_approver_of(db, r),
            "next_approver": r.next_approver,
            "last_sign_date": r.last_sign_date.isoformat() if r.last_sign_date else None,
        })
    return {"total": total, "page": page, "page_size": page_size, "items": items}


# 各表單的原始單號欄位（依優先順序）。請款的「付款編號」未填時改用「專請編號」。
DOC_NO_KEYS = {
    "purchase": ["編號"],
    "claim": ["付款編號", "工請編號", "專請編號", "編號"],
    "seal": ["印鑑編號", "編號"],
}
# 其他含「編號」的欄位若要當作單號，需排除這些（採購編號是 ERP 採購單號，不是表單單號）
DOC_NO_EXCLUDE = {"採購編號", "傳票號碼"}


def _doc_no(r: ReturnStatsRecord) -> str:
    """Ragic 原始單號（例如 樂專購20260500004、樂專印20260900001）；取不到時退回 Ragic 紀錄編號。"""
    try:
        raw = json.loads(r.raw_json or "{}")
    except (TypeError, ValueError):
        raw = {}
    for key in DOC_NO_KEYS.get(r.form_type, ["編號"]):
        v = as_text(raw.get(key)).strip()
        if v:
            return v
    # 後備：任何含「編號」且非空的欄位（排除 DOC_NO_EXCLUDE）
    for key, val in raw.items():
        if "編號" in key and key not in DOC_NO_EXCLUDE:
            v = as_text(val).strip()
            if v:
                return v
    return r.ragic_record_id


def _ragic_url(r: ReturnStatsRecord) -> str:
    src = r.source_key.split("|")
    path = src[2] if len(src) == 3 else ""
    return f"https://ap12.ragic.com/soutlet001/{path}/{r.ragic_record_id}" if path else ""


def _detail_fields(raw_json: str) -> dict:
    """明細 detail dict：中文欄位名稱，排除系統欄位、簽名圖、子表格。"""
    try:
        raw = json.loads(raw_json or "{}")
    except (TypeError, ValueError):
        return {}
    out = {}
    for k, v in raw.items():
        if k.startswith("_") or k.startswith("wf") or k == "簽核":
            continue
        if isinstance(v, (dict, list)):
            continue
        text = as_text(v)
        if text == "（簽名圖）" or text == "":
            continue
        out[k] = text
    return out


@router.get("/records/{record_id}", summary="明細（含所有簽核步驟與備註）")
def get_record(record_id: int, db: Session = Depends(get_db), _=Depends(require_permission(VIEW))):
    r = db.query(ReturnStatsRecord).filter_by(id=record_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail="找不到紀錄")
    steps = (db.query(ReturnStatsStep).filter_by(record_id=r.id)
             .order_by(ReturnStatsStep.step_no).all())
    return {
        "id": r.id, "company": r.company, "form_type": r.form_type, "dept": r.dept_display,
        "form_name": r.form_name, "ragic_record_id": r.ragic_record_id, "ragic_url": _ragic_url(r),
        "applicant": r.applicant, "apply_date": r.apply_date.isoformat() if r.apply_date else None,
        "amount": r.amount, "purpose": html_to_text(r.purpose), "ragic_status": r.ragic_status,
        "submitter": r.submitter, "next_approver": r.next_approver,
        "outcome": r.outcome, "outcome_label": OUTCOME_LABEL.get(r.outcome, r.outcome),
        "outcome_reason": r.outcome_reason,
        "rejection_approver": rejection_approver_of(db, r),
        "last_sign_date": r.last_sign_date.isoformat() if r.last_sign_date else None,
        "steps": [{
            "step_no": s.step_no, "role_field": s.role_field, "approver": s.approver_text,
            "sign_date": s.sign_date.isoformat() if s.sign_date else None,
            "remark": s.remark or "", "inferred_last": s.is_inferred_last,
            "response_code": s.response_code,
        } for s in steps],
        "detail": _detail_fields(r.raw_json),
    }


EXPORT_MAX_ROWS = 20000

RECORD_HEADERS = [
    "公司", "部門", "表單", "記錄編號", "Ragic 連結", "申請人", "申請日期", "金額", "事由",
    "狀態", "狀態說明", "退件簽核人", "退件／退簽原因", "下一位簽核人", "最後簽署日期", "Ragic 狀態",
]
STEP_HEADERS = [
    "公司", "部門", "表單", "記錄編號", "步驟", "角色", "簽核人", "簽署日期", "代碼", "回應／備註",
]


@router.post("/records/{record_id}/refresh-approval", summary="重新抓取此紀錄的 Ragic 簽核步驟（單筆）")
def refresh_approval(record_id: int, db: Session = Depends(get_db), _=Depends(require_permission(MANAGE))):
    """
    直接以單筆 approval=true 查詢 Ragic，寫入簽核步驟並重算退件判定。
    失敗時回傳 Ragic 的錯誤原文，方便定位（2026-11-03）。
    """
    r = db.query(ReturnStatsRecord).filter_by(id=record_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail="找不到紀錄")
    src = db.query(ReturnStatsSource).filter_by(source_key=r.source_key).first()
    if src is None or not src.ragic_path:
        raise HTTPException(status_code=400, detail="此來源沒有 Ragic 路徑，無法抓取簽核資料")
    adapter = RagicAdapter(sheet_path=src.ragic_path, server_url=RAGIC_SERVER, account=RAGIC_ACCOUNT)
    try:
        one = asyncio.run(adapter.fetch_one(r.ragic_record_id, extra_params={"approval": "true"}))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Ragic 查詢失敗：{type(exc).__name__} {str(exc)[:200]}")
    single = (one.get(r.ragic_record_id) or {}) if isinstance(one, dict) else {}
    raw_steps = single.get("_approval_steps") or []
    if not raw_steps:
        raise HTTPException(status_code=404, detail="Ragic 回傳沒有簽核步驟（此紀錄可能未送簽）")
    steps = steps_from_approval(raw_steps)
    outcome, reason = classify_approval(steps)
    db.query(ReturnStatsStep).filter_by(record_id=r.id).delete()
    for st in steps:
        db.add(ReturnStatsStep(
            record_id=r.id, step_no=st["step_no"], role_field=st["role_field"],
            approver_text=st["approver_text"], sign_date=st["sign_date"], remark=st["remark"],
            is_inferred_last=False, response_code=st.get("code") or None))
    r.outcome, r.outcome_reason = outcome, reason
    db.commit()
    return {"ok": True, "steps": len(steps), "outcome": outcome, "outcome_reason": reason}


@router.get("/export", summary="匯出 Excel（與清單同篩選條件，不分頁）")
def export_records(
    f: dict = Depends(_filter_params),
    db: Session = Depends(get_db),
    _=Depends(require_permission(VIEW)),
):
    q = _filtered(db.query(ReturnStatsRecord), db=db, **f)
    total = q.count()
    if total > EXPORT_MAX_ROWS:
        raise HTTPException(status_code=400, detail=f"筆數 {total} 超過匯出上限 {EXPORT_MAX_ROWS}，請縮小篩選範圍")
    recs = q.order_by(ReturnStatsRecord.company, ReturnStatsRecord.dept_display,
                      ReturnStatsRecord.apply_date.desc().nullslast(), ReturnStatsRecord.id.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "退件統計"
    header_fill = PatternFill("solid", fgColor="1B3A5C")
    header_font = Font(bold=True, color="FFFFFF")

    def write_header(sheet, headers):
        sheet.append(headers)
        for c in sheet[1]:
            c.font, c.fill = header_font, header_fill
            c.alignment = Alignment(vertical="center", wrap_text=True)
        sheet.freeze_panes = "A2"

    write_header(ws, RECORD_HEADERS)
    for r in recs:
        ws.append([xlsx_safe(v) for v in [
            r.company, r.dept_display, r.form_name, _doc_no(r), _ragic_url(r),
            r.applicant or "", r.apply_date.isoformat() if r.apply_date else "",
            r.amount, html_to_text(r.purpose), OUTCOME_LABEL.get(r.outcome, r.outcome), r.outcome_reason,
            rejection_approver_of(db, r), rejection_note_of(db, r), r.next_approver or "",
            r.last_sign_date.isoformat() if r.last_sign_date else "", r.ragic_status or "",
        ]])
    for col, width in zip("ABCDEFGHIJKLMNOP", [8, 12, 16, 12, 40, 12, 12, 12, 40, 12, 28, 14, 50, 16, 14, 12]):
        ws.column_dimensions[col].width = width

    ws2 = wb.create_sheet("簽核步驟")
    write_header(ws2, STEP_HEADERS)
    ids = [r.id for r in recs]
    meta = {r.id: r for r in recs}
    if ids:
        steps = (db.query(ReturnStatsStep).filter(ReturnStatsStep.record_id.in_(ids))
                 .order_by(ReturnStatsStep.record_id, ReturnStatsStep.step_no).all())
        for s in steps:
            r = meta[s.record_id]
            ws2.append([xlsx_safe(v) for v in [
                r.company, r.dept_display, r.form_name, r.ragic_record_id, s.step_no, s.role_field,
                s.approver_text, s.sign_date.isoformat() if s.sign_date else "", s.response_code or "",
                s.remark or "",
            ]])
    for col, width in zip("ABCDEFGHIJ", [8, 12, 16, 12, 6, 12, 12, 12, 8, 60]):
        ws2.column_dimensions[col].width = width

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    stamp = twnow().strftime("%Y%m%d")
    cn_name = f"退件統計_{stamp}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": (
            f'attachment; filename="return_reject_stats_{stamp}.xlsx"; '
            f"filename*=UTF-8''{quote(cn_name, safe='')}")},
    )


@router.post("/sync", summary="手動同步退件統計")
async def manual_sync(_=Depends(require_permission(MANAGE))):
    return await sync_return_stats()
