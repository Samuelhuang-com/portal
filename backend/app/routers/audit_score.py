"""
稽核檢查統計（合併計分）API — 規格見 services/audit_score_service.py
權限：audit_check_score_view（查看＋匯出）
"""
import io
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.excel_utils import xlsx_safe
from app.core.time import twnow
from app.dependencies import require_permission
from app.services.audit_score_service import build_score

router = APIRouter()
VIEW = "audit_check_score_view"

HEADER_FILL = PatternFill("solid", fgColor="1B3A5C")
HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT_ALIGN = Alignment(horizontal="left", vertical="center", wrap_text=True)
CENTER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
SOURCE_LABEL = {"稽核檢查": "系統檢查", "KPO": "現場稽核"}  # 與畫面 SOURCE_LABEL 一致


def _pts(v):
    """0~1 的比例 → 0~100 分，四捨五入取整數（與畫面 Math.round 一致）"""
    return int(v * 100 + 0.5)


def _pts_text(v):
    """合併分數：與畫面 pts() 相同，無資料顯示「本年無」"""
    return "本年無" if v is None else f"{_pts(v)} 分"


def _month_cell_text(items):
    """月份格：與畫面 monthCell() 相同，每個來源一行「來源 達標/子項（分數）」；整月無資料顯示「—」"""
    if not items:
        return "—"
    lines = []
    for m in items:
        label = SOURCE_LABEL.get(m["source"], m["source"])
        score = m["module_score"]
        if score is None:
            tail = "（本月無）"
        elif m["source"] == "稽核檢查":
            tail = f"（{_pts(score)} 分）"
        else:
            tail = f"（{int(score) if float(score).is_integer() else score} 分）"
        lines.append(f"{label} {m['pass']}/{m['sub']}{tail}")
    return "\n".join(lines)


@router.get("", summary="稽核檢查統計（合併分數，公司 → 部門）")
def get_score(
    year: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db),
    _=Depends(require_permission(VIEW)),
):
    return build_score(db, year)


@router.get("/export", summary="匯出 Excel")
def export_score(
    year: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db),
    _=Depends(require_permission(VIEW)),
):
    data = build_score(db, year)
    wb = Workbook()

    # ── Sheet 1：與畫面「稽核檢查統計」相同版面（公司區塊 → 部門列，1～12 月欄） ──
    ws = wb.active
    ws.title = f"{year}年稽核統計"
    month_keys = [f"{year}-{i:02d}" for i in range(1, 13)]
    LAST_COL = 22  # A～V
    # 欄位：1 部門｜2～13 一～十二月｜14～16 系統建置稽核（子項數、達標數、系統平均分）｜17～19 現場營運稽核（選定項數、符合項數、現場平均分）｜20 合計項數｜21 合計達標數｜22 合併分數
    ws.column_dimensions["A"].width = 14
    for col in range(2, 14):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = 18
    for col in range(14, LAST_COL + 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = 13

    row = 1
    for blk in data["blocks"]:
        # 公司標題列
        title = ws.cell(row=row, column=1, value=xlsx_safe(blk["company_name"]))
        title.font = Font(bold=True, size=12, color="1B3A5C")
        title.alignment = LEFT_ALIGN
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=LAST_COL)
        row += 1

        h1, h2 = row, row + 1
        # 單欄標題（跨兩列合併）
        single_headers = {1: "部門", 20: "合計項數", 21: "合計達標數", 22: "合併分數"}
        for i, mk in enumerate(month_keys):
            single_headers[2 + i] = f"{i + 1}月"
        for col in range(1, LAST_COL + 1):
            for r_ in (h1, h2):
                c = ws.cell(row=r_, column=col)
                c.fill = HEADER_FILL
                c.font = HEADER_FONT
                c.alignment = HEADER_ALIGN
        for col, text in single_headers.items():
            ws.cell(row=h1, column=col, value=text)
        # 群組標題（橫跨兩欄）
        ws.cell(row=h1, column=14, value="系統建置稽核")
        ws.cell(row=h1, column=17, value="現場營運稽核")
        for col, text in {14: "系統檢查子項數", 15: "系統檢查達標數", 16: "系統平均分", 17: "現場稽核選定項數", 18: "現場稽核符合項數", 19: "現場平均分"}.items():
            ws.cell(row=h2, column=col, value=text)
        for col in list(single_headers.keys()):
            ws.merge_cells(start_row=h1, start_column=col, end_row=h2, end_column=col)
        ws.merge_cells(start_row=h1, start_column=14, end_row=h1, end_column=16)
        ws.merge_cells(start_row=h1, start_column=17, end_row=h1, end_column=19)
        row = h2 + 1

        for r in blk["rows"]:
            by_month = {mk: [] for mk in month_keys}
            for m in r["monthly"]:
                if m["period"][:7] in by_month:
                    by_month[m["period"][:7]].append(m)
            month_texts = [_month_cell_text(by_month[mk]) for mk in month_keys]
            values = (
                [xlsx_safe(r["department"])]
                + [xlsx_safe(t) for t in month_texts]
                + [r["audit_sub"], r["audit_pass"], _pts_text(r["audit_score"]),
                   r["kpo_sub"], r["kpo_pass"], _pts_text(r["kpo_score"]),
                   r["total_sub"], r["total_pass"], _pts_text(r["rate"])]
            )
            for col, v in enumerate(values, start=1):
                c = ws.cell(row=row, column=col, value=v)
                c.alignment = LEFT_ALIGN if 1 <= col <= 13 else CENTER_ALIGN
            lines = max(t.count("\n") + 1 for t in month_texts)
            ws.row_dimensions[row].height = max(20, 15 * lines + 6)
            row += 1
        row += 1  # 公司之間空一列

    # ── Sheet 2：月明細（只列有資料的期別，不補空白列） ──
    ws2 = wb.create_sheet("月明細")
    ws2.append(["公司", "部門", "期別", "來源模組", "來源表單編號", "子項數（選定）", "達標數（符合）", "原模組分數", "原模組顯示"])
    for c in ws2[1]:
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
    ws2.freeze_panes = "A2"
    for blk in data["blocks"]:
        for r in blk["rows"]:
            for m in r["monthly"]:
                score = m["module_score"]
                if m["source"] == "稽核檢查" and score is not None:
                    score_cell = _pts(score)
                elif m["source"] == "KPO" and score is not None:
                    score_cell = int(score)
                else:
                    score_cell = "本月無"
                ws2.append([xlsx_safe(v) for v in [
                    blk["company_name"], r["department"], m["period"], m["source"],
                    m["source_sheet_id"], m["sub"], m["pass"], score_cell, m["module_label"],
                ]])
    for col, w in zip("ABCDEFGHI", [12, 14, 10, 12, 14, 14, 14, 12, 30]):
        ws2.column_dimensions[col].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    stamp = twnow().strftime("%Y%m%d")
    cn = f"稽核檢查統計_{year}_{stamp}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": (
            f'attachment; filename="audit_score_{year}_{stamp}.xlsx"; '
            f"filename*=UTF-8''{quote(cn, safe='')}")},
    )
