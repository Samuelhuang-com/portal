"""退件Dashboard API（/api/v1/return-dashboard）— 權限沿用 return_reject_stats_view"""
import calendar
import io
from datetime import date
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.excel_utils import xlsx_safe
from app.core.time import twnow
from app.dependencies import require_permission
from app.models.return_stats import ReturnStatsRecord
from app.routers.return_stats import EXPORT_MAX_ROWS, OUTCOME_LABEL, _ragic_url
from app.services.return_dashboard_service import RETURNED, build_matrix
from app.services.return_stats_parser import html_to_text
from app.services.return_stats_sync import rejection_approver_of, rejection_note_of

router = APIRouter()
VIEW = "return_reject_stats_view"
FORM_LABEL = {"purchase": "請購", "claim": "請款", "seal": "用印"}
DETAIL_LIMIT = 2000


@router.get("/matrix", summary="公司 × 部門 × 月份的送件數與退件數")
def get_matrix(
    year: int = Query(..., ge=2000, le=2100),
    form_type: Optional[str] = Query(None, pattern="^(purchase|claim|seal)$"),
    company: list[str] = Query(default=[]),
    rejection_approver: Optional[str] = Query(None, description="退件簽核人（只限縮退件數）"),
    db: Session = Depends(get_db),
    _=Depends(require_permission(VIEW)),
):
    return build_matrix(db, year, form_type, company or None, rejection_approver or None)


@router.get("/detail", summary="單一格子（月份 × 部門 × 送件／退件）的明細")
def get_detail(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    kind: str = Query("sent", pattern="^(sent|returned)$"),
    company: list[str] = Query(default=[]),
    dept: list[str] = Query(default=[]),
    form_type: Optional[str] = Query(None, pattern="^(purchase|claim|seal)$"),
    db: Session = Depends(get_db),
    _=Depends(require_permission(VIEW)),
):
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    q = db.query(ReturnStatsRecord).filter(
        ReturnStatsRecord.is_deleted == False,  # noqa: E712
        ReturnStatsRecord.apply_date >= first,
        ReturnStatsRecord.apply_date <= last,
    )
    if company:
        q = q.filter(ReturnStatsRecord.company.in_(company))
    if dept:
        q = q.filter(ReturnStatsRecord.dept_display.in_(dept))
    if form_type:
        q = q.filter(ReturnStatsRecord.form_type == form_type)
    if kind == "returned":
        q = q.filter(ReturnStatsRecord.outcome.in_(RETURNED))
    total = q.count()
    recs = (q.order_by(ReturnStatsRecord.company, ReturnStatsRecord.dept_display,
                       ReturnStatsRecord.apply_date, ReturnStatsRecord.id)
            .limit(DETAIL_LIMIT).all())
    items = [{
        "id": r.id, "company": r.company, "form_type": r.form_type,
        "dept": r.dept_display, "form_name": r.form_name,
        "ragic_record_id": r.ragic_record_id, "ragic_url": _ragic_url(r),
        "applicant": r.applicant,
        "apply_date": r.apply_date.isoformat() if r.apply_date else None,
        "amount": r.amount, "outcome": r.outcome,
        "outcome_label": OUTCOME_LABEL.get(r.outcome, r.outcome),
        "rejection_note": rejection_note_of(db, r),
        "rejection_approver": rejection_approver_of(db, r),
        "next_approver": r.next_approver,
        "ragic_status": r.ragic_status,
    } for r in recs]
    return {"total": total, "truncated": total > DETAIL_LIMIT, "items": items}


MATRIX_HEADERS_TAIL = ["全年送件", "全年退件", "退件率"]
DETAIL_HEADERS = ["公司", "部門", "表單", "表單名稱", "記錄編號", "申請人", "申請日期", "月份",
                  "金額", "狀態", "退件簽核人", "退件原因", "下一位簽核人", "Ragic 連結"]


@router.get("/export", summary="匯出 Excel（月份矩陣＋年度明細）")
def export_matrix(
    year: int = Query(..., ge=2000, le=2100),
    form_type: Optional[str] = Query(None, pattern="^(purchase|claim|seal)$"),
    company: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
    _=Depends(require_permission(VIEW)),
):
    data = build_matrix(db, year, form_type, company or None)

    q = db.query(ReturnStatsRecord).filter(
        ReturnStatsRecord.is_deleted == False,  # noqa: E712
        ReturnStatsRecord.apply_date >= date(year, 1, 1),
        ReturnStatsRecord.apply_date <= date(year, 12, 31),
    )
    if form_type:
        q = q.filter(ReturnStatsRecord.form_type == form_type)
    if company:
        q = q.filter(ReturnStatsRecord.company.in_(company))
    total = q.count()
    if total > EXPORT_MAX_ROWS:
        raise HTTPException(status_code=400, detail=f"筆數 {total} 超過匯出上限 {EXPORT_MAX_ROWS}，請縮小篩選範圍")
    recs = q.order_by(ReturnStatsRecord.company, ReturnStatsRecord.dept_display,
                      ReturnStatsRecord.apply_date, ReturnStatsRecord.id).all()

    header_fill = PatternFill("solid", fgColor="1B3A5C")
    header_font = Font(bold=True, color="FFFFFF")
    block_fill = PatternFill("solid", fgColor="E6EEF6")

    def write_header(sheet, headers):
        sheet.append(headers)
        for c in sheet[1]:
            c.font, c.fill = header_font, header_fill
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        sheet.freeze_panes = "C2"

    def pct(v):
        return v if v is not None else ""

    wb = Workbook()
    ws = wb.active
    ws.title = "月份矩陣"
    headers = ["公司", "部門"]
    for m in range(1, 13):
        headers += [f"{m}月送件", f"{m}月退件", f"{m}月退件率"]
    headers += MATRIX_HEADERS_TAIL
    write_header(ws, headers)

    def line(label_company, label_dept, months, year_sent, year_returned, year_rate):
        vals = [label_company, label_dept]
        for c in months:
            # 月退件率（2026-11-03）：送件為 0 → 「—」，與網頁一致
            vals += [c["sent"], c["returned"], c["rate"] if c["rate"] is not None else "—"]
        vals += [year_sent, year_returned, pct(year_rate)]
        return vals

    for b in data["blocks"]:
        ws.append([xlsx_safe(v) for v in line(b["company"], "小計", b["months"],
                                              b["year_sent"], b["year_returned"], b["year_rate"])])
        for c in ws[ws.max_row]:
            c.font = Font(bold=True)
            c.fill = block_fill
        for r in b["rows"]:
            ws.append([xlsx_safe(v) for v in line(b["company"], r["department"], r["cells"],
                                                  r["year_sent"], r["year_returned"], r["year_rate"])])
    ws.append([xlsx_safe(v) for v in line("合計", "", data["months"],
                                          data["year_sent"], data["year_returned"], data["year_rate"])])
    for c in ws[ws.max_row]:
        c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 14
    for i in range(3, len(headers) + 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = 9
    for row in ws.iter_rows(min_row=2, min_col=len(headers), max_col=len(headers)):
        for c in row:
            c.number_format = "0.0%"
    for m in range(1, 13):
        rate_col = 5 + 3 * (m - 1)   # A=公司、B=部門；每月 送件／退件／退件率 三欄
        for r_idx in range(2, ws.max_row + 1):
            ws.cell(row=r_idx, column=rate_col).number_format = "0.0%"

    ws2 = wb.create_sheet("明細")
    write_header(ws2, DETAIL_HEADERS)
    for r in recs:
        ws2.append([xlsx_safe(v) for v in [
            r.company, r.dept_display, FORM_LABEL.get(r.form_type, r.form_type), r.form_name,
            r.ragic_record_id, r.applicant or "",
            r.apply_date.isoformat() if r.apply_date else "", r.apply_date.month if r.apply_date else "",
            r.amount, OUTCOME_LABEL.get(r.outcome, r.outcome),
            rejection_approver_of(db, r), rejection_note_of(db, r), r.next_approver or "",
            _ragic_url(r),
        ]])
    for col, width in zip("ABCDEFGHIJKLMN", [8, 12, 8, 16, 12, 12, 12, 8, 12, 10, 14, 50, 16, 40]):
        ws2.column_dimensions[col].width = width

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    stamp = twnow().strftime("%Y%m%d")
    cn_name = f"退件Dashboard_{year}_{stamp}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": (
            f'attachment; filename="return_dashboard_{year}_{stamp}.xlsx"; '
            f"filename*=UTF-8''{quote(cn_name, safe='')}")},
    )
