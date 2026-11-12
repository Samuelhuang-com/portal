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


def _pts(v):
    """0~1 的比例 → 0~100 分，四捨五入取整數（與畫面 Math.round 一致）"""
    return int(v * 100 + 0.5)


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
    ws = wb.active
    ws.title = f"{year}年稽核統計"
    headers = ["公司", "部門", "系統檢查子項數", "系統檢查達標數", "現場稽核選定項數", "現場稽核符合項數",
               "合計項數", "合計達標數", "合併分數"]
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1B3A5C")
        c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    for blk in data["blocks"]:
        for r in blk["rows"]:
            ws.append([xlsx_safe(v) for v in [
                blk["company_name"], r["department"], r["audit_sub"], r["audit_pass"],
                r["kpo_sub"], r["kpo_pass"], r["total_sub"], r["total_pass"],
                _pts(r["rate"]) if r["rate"] is not None else "本年無",
            ]])
    for col, w in zip("ABCDEFGHI", [12, 14, 12, 12, 14, 14, 12, 12, 12]):
        ws.column_dimensions[col].width = w
    ws2 = wb.create_sheet("月明細")
    ws2.append(["公司", "部門", "期別", "來源模組", "來源表單編號", "子項數（選定）", "達標數（符合）", "原模組分數", "原模組顯示"])
    for c in ws2[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1B3A5C")
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
