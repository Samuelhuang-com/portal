"""
稽核檢查 — 單一部門「內部稽核報告」Word 匯出（2026-10-01；2026-10-10 改名＋字級）

格式比照使用者提供的「2026-..._202609-1 內部稽核檢查表.doc」：
  logo（維春商業開發）／標題／填表日期
  受稽單位｜文件編號、受稽人員｜稽核人員、文件名稱
  項次｜內部稽核項目｜稽核紀錄｜稽核結果｜建議
    1.  大項
    1.1 子項 ｜ 評語（判定色） ｜ V / X ｜ 建議（藍字）
    覆核. 8月待補正項目
        待補正內容 ｜ 覆核結果 ｜ V / X
  本次稽核說明：xx分  ＋  缺失表
  本次稽核結果：       ＋  稽核子項數／未達標項數／本期稽核分數（2026-10-10 單獨挪到缺失下方）
  簽核列：人資主管／受稽部門主管／稽核人員（2026-10-10 依範本改為 3 格）

只列出「這個部門有填評語或建議」的子項（沒填 ＝ 本期不查此項）；大項只在底下有子項時出現。
數字一律取 build_sheet_detail() 的系統計算結果，不在這裡重算。

字級（2026-10-10 使用者範本「內部稽核報告」）：標題 16pt、填表日期 14pt，其餘全部 11pt
（BODY_PT）。查核評語在 Web editor 內另設的字級一律不採用，固定 11pt（2026-10-10 裁示）；
顏色、粗斜體等其餘格式仍照欄位設定。字型一律微軟正黑體。
分數以「分」呈現（達標數 ÷ 子項數 × 100，四捨五入），統計列顯示「未達標項數」＝ X 的數量。
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, List, Optional

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

try:
    from app.services.audit_check_html import html_to_runs, html_to_text
except ImportError:   # 單獨測試時
    from audit_check_html import html_to_runs, html_to_text

LOGO_PATH = Path(__file__).parent / "audit_check_assets" / "esse_logo.png"
FONT = "微軟正黑體"
# 顏色一律比照網頁稽核單（SheetEditor.tsx）：
#   缺失 #cf1322、建議 SUGGESTION_COLOR #1677ff、分數 100% 綠 #52c41a／未滿紅 #cf1322；
#   評語與稽核結果 → 判定類型主檔的顏色（使用者在「判定類型設定」自訂）
RED = RGBColor(0xCF, 0x13, 0x22)
GREEN = RGBColor(0x52, 0xC4, 0x1A)
BLUE = RGBColor(0x16, 0x77, 0xFF)


def _score_color(score: Optional[float]) -> Optional[RGBColor]:
    if score is None:
        return None
    return GREEN if score >= 1 else RED
SHADE = "F2F2F2"
TITLE_PT = 16     # 標題「內部稽核報告」
DATE_PT = 14      # 填表日期
BODY_PT = 11      # 其餘所有文字（2026-10-10 依使用者範本統一）

# 主表欄寬（A4 直式，左右邊界 1.5cm → 可用 18cm）
COLS = [Cm(1.5), Cm(4.3), Cm(6.2), Cm(2.2), Cm(3.8)]


# ── 低階小工具 ────────────────────────────────────────────────────────────
def _font(run, size: float = BODY_PT, bold: bool = True, color: Optional[RGBColor] = None) -> None:
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), FONT)
    if color is not None:
        run.font.color.rgb = color


def _write(cell, text: str, size: float = BODY_PT, bold: bool = True,
           align=WD_ALIGN_PARAGRAPH.LEFT, color: Optional[RGBColor] = None) -> None:
    """把文字寫進格子（多行用換行分段），覆蓋原本內容。"""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    first = cell.paragraphs[0]
    for p in cell.paragraphs[1:]:
        p._element.getparent().remove(p._element)
    for r in list(first.runs):
        r._element.getparent().remove(r._element)
    for idx, line in enumerate(lines):
        p = first if idx == 0 else cell.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        _font(p.add_run(line), size, bold, color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


_ALIGN = {
    "center": WD_ALIGN_PARAGRAPH.CENTER, "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "left": WD_ALIGN_PARAGRAPH.LEFT,
}


def _write_html(cell, html_s: Optional[str], size: float = BODY_PT) -> None:
    """
    查核評語（富文字，2026-10-04）→ Word：顏色、粗斜體、底線、刪除線、螢光底色、字級、
    清單、對齊全部照欄位內的設定；沒設定的文字一律黑字、不粗（與判定無關）。
    """
    _write(cell, "", size)
    paras = html_to_runs(html_s)
    first = cell.paragraphs[0]
    for idx, para in enumerate(paras or [{"align": None, "runs": []}]):
        p = first if idx == 0 else cell.add_paragraph()
        p.alignment = _ALIGN.get(para.get("align") or "left", WD_ALIGN_PARAGRAPH.LEFT)
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        for text, f in para["runs"]:
            run = p.add_run(text)
            color = RGBColor.from_string(f["color"]) if f.get("color") else None
            # 2026-10-10：一律 BODY_PT，不採用編輯器內的字級
            _font(run, size, bool(f.get("bold", False)), color)
            run.font.italic = bool(f.get("italic")) or None
            run.font.underline = bool(f.get("underline")) or None
            run.font.strike = bool(f.get("strike")) or None
            if f.get("sub"):
                run.font.subscript = True
            if f.get("sup"):
                run.font.superscript = True
            if f.get("bg"):
                rpr = run._element.get_or_add_rPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:color"), "auto")
                shd.set(qn("w:fill"), str(f["bg"]))
                rpr.append(shd)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def _shade(cell, fill: str = SHADE) -> None:
    tcpr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


def _row_height(row, cm: float) -> None:
    trpr = row._tr.get_or_add_trPr()
    h = OxmlElement("w:trHeight")
    h.set(qn("w:val"), str(int(cm * 567)))
    h.set(qn("w:hRule"), "atLeast")
    trpr.append(h)


def _fix_widths(table, widths) -> None:
    """固定欄寬：tblGrid（LibreOffice／WPS 看這個）＋每格 tcW（Word 看這個）＋ fixed layout。"""
    table.autofit = False
    tblpr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblpr.append(layout)
    grid = table._tbl.tblGrid
    for idx, gc in enumerate(grid.findall(qn("w:gridCol"))):
        if idx < len(widths):
            gc.set(qn("w:w"), str(int(widths[idx].twips)))
    for row in table.rows:
        for idx, w in enumerate(widths):
            if idx < len(row.cells):
                row.cells[idx].width = w


def _merge(row, start: int, end: int):
    return row.cells[start].merge(row.cells[end]) if end > start else row.cells[start]


def _symbol(code: Optional[str], types: Dict[str, dict]) -> str:
    """稽核結果欄：算達標 → V；不算達標 → X（與畫面判定一致）。"""
    if not code:
        return ""
    t = types.get(code)
    if t is None or t.get("counts_as_pass", True):
        return "V"
    return "X"


def _color(code: Optional[str], types: Dict[str, dict]) -> Optional[RGBColor]:
    """判定類型主檔的顏色（使用者在「判定類型設定」自訂，與網頁畫面同一來源）。"""
    if not code:
        return None
    t = types.get(code)
    hexv = (t or {}).get("color") or ""
    hexv = hexv.lstrip("#")
    if len(hexv) != 6:
        return None
    try:
        return RGBColor.from_string(hexv.upper())
    except ValueError:
        return None


def _month_label(period: Optional[str]) -> str:
    """'2026-08' → '8月'"""
    if period and len(period) >= 7 and period[4] == "-":
        try:
            return f"{int(period[5:7])}月"
        except ValueError:
            pass
    return "上期"


def _pct(score: Optional[float]) -> str:
    """分數以「分」呈現（2026-10-10 使用者範本：5 項中 4 項未達標 → 20分）。"""
    if score is None:
        return "本月無"
    return f"{round(score * 100)}分"


def _highlight(run, color: str = "yellow") -> None:
    rpr = run._element.get_or_add_rPr()
    hl = OxmlElement("w:highlight")
    hl.set(qn("w:val"), color)
    rpr.append(hl)


# ── 主函式 ────────────────────────────────────────────────────────────────
def build_inspection_docx(
    detail: dict,
    sheet_department_id: int,
    auditor_name: str,
    fill_date: str,
) -> bytes:
    """
    detail：audit_check_service.build_sheet_detail() 的結果
    fill_date：'YYYY.MM.DD'
    """
    dept = next(d for d in detail["departments"] if d["id"] == sheet_department_id)
    dept_index = [d["id"] for d in detail["departments"]].index(sheet_department_id) + 1
    company = detail.get("company_name") or ""
    period = detail.get("period") or ""
    types = {
        (t["code"] if isinstance(t, dict) else t.code): (
            t if isinstance(t, dict) else {"counts_as_pass": t.counts_as_pass, "color": t.color}
        )
        for t in detail.get("result_types", [])
    }

    cells = {
        c["sheet_item_id"]: c
        for c in detail["cells"]
        if c["sheet_department_id"] == sheet_department_id
        and (html_to_text(c.get("comment")) or (c.get("suggestion") or "").strip())
    }
    items: List[dict] = detail["items"]
    minors_by_major: Dict[int, List[dict]] = {}
    for it in items:
        if it["parent_sheet_item_id"] is not None and it["id"] in cells:
            minors_by_major.setdefault(it["parent_sheet_item_id"], []).append(it)
    majors = [it for it in items if it["parent_sheet_item_id"] is None and it["id"] in minors_by_major]

    review = next((r for r in detail.get("reviews", []) if r["sheet_department_id"] == sheet_department_id), None)
    score = next((s for s in detail.get("scores", []) if s["sheet_department_id"] == sheet_department_id), None)

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(1.5)
    sec.top_margin = Cm(1.0)
    sec.bottom_margin = Cm(0.75)   # 2026-10-10 依範本
    sec.header_distance = Cm(0.5)

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.paragraph_format.space_after = Pt(0)

    # ── 頁首：logo ──
    hp = sec.header.paragraphs[0]
    if LOGO_PATH.exists():
        hp.add_run().add_picture(str(LOGO_PATH), width=Cm(4.2))

    # ── 標題 / 填表日期 ──
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(p.add_run("內部稽核報告"), TITLE_PT)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _font(p.add_run(f"填表日期：{fill_date}"), DATE_PT)

    # ── 主表 ──
    t = doc.add_table(rows=0, cols=5)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER

    def add_row(height: float = 0.75):
        r = t.add_row()
        _row_height(r, height)
        return r

    r = add_row(0.9)
    _write(_merge(r, 0, 2), f"受稽單位：{company}", BODY_PT)
    _write(_merge(r, 3, 4), f"文件編號：{period.replace('-', '')}-{dept_index}", BODY_PT)

    r = add_row()
    _write(_merge(r, 0, 2), f"受稽人員：{dept['name']}", BODY_PT)
    _write(_merge(r, 3, 4), f"稽核人員：{auditor_name}", BODY_PT)

    r = add_row()
    _write(_merge(r, 0, 4), f"文件名稱：{company}系統建置作業-{dept['name']}", BODY_PT)

    r = add_row(1.0)
    for idx, label in enumerate(["項次", "內部稽核項目", "稽核紀錄", "稽核結果", "建議"]):
        _write(r.cells[idx], label, BODY_PT, align=WD_ALIGN_PARAGRAPH.CENTER,
               color=BLUE if label == "建議" else None)   # 比照網頁 Drawer「建議」標籤藍字
        _shade(r.cells[idx])

    def section_row(no: str, title: str):
        rr = add_row(0.9)
        _write(rr.cells[0], no, BODY_PT)
        _write(_merge(rr, 1, 4), title, BODY_PT)
        for c in rr.cells:
            _shade(c)

    for major in majors:
        section_row(f"{major['display_no']}." if major.get("display_no") else "", major["name"])
        for minor in minors_by_major[major["id"]]:
            c = cells[minor["id"]]
            rr = add_row(0.9)
            _write(rr.cells[0], minor.get("display_no") or "", BODY_PT, align=WD_ALIGN_PARAGRAPH.RIGHT)
            _write(rr.cells[1], f"{minor['name']}{minor.get('scope_note') or ''}", BODY_PT)
            code = c.get("result_code") if html_to_text(c.get("comment")) else None
            color = _color(code, types)   # 評語與稽核結果依判定顏色（如扣分紅、建議藍）
            # 評語照欄位內的富文字顏色（2026-10-04）；判定只影響 V／X 的顏色
            _write_html(rr.cells[2], c.get("comment") or "", BODY_PT)
            _write(rr.cells[3], _symbol(code, types), BODY_PT, align=WD_ALIGN_PARAGRAPH.CENTER, color=color)
            # 最右欄「建議」（原範本的「備註」欄，2026-10-03 使用者改名）：
            # 該格的建議，固定藍字 SUGGESTION_COLOR、與判定無關
            _write(rr.cells[4], (c.get("suggestion") or "").strip(), BODY_PT, color=BLUE)

    has_review = review and ((review.get("pending_text") or "").strip() or (review.get("result_text") or "").strip())
    if has_review:
        section_row("覆核.", f"{_month_label(review.get('source_period'))}待補正項目")
        for c_ in t.rows[-1].cells:
            _shade(c_, "F6FFED")   # 2026-10-03：待補正列淺綠底，比照網頁
        rr = add_row(1.2)
        _write(rr.cells[0], "")
        _write(rr.cells[1], review.get("pending_text") or "", BODY_PT)   # 待補正是題目，不判定 → 黑字
        _shade(rr.cells[1], "F6FFED")
        _write(rr.cells[2], review.get("result_text") or "", BODY_PT,
               color=_color(review.get("result_status"), types))
        code = review.get("result_status") if (review.get("result_text") or "").strip() else None   # 只看結果
        _write(rr.cells[3], _symbol(code, types), BODY_PT, align=WD_ALIGN_PARAGRAPH.CENTER, color=_color(code, types))
        _write(rr.cells[4], "")

    # ── 本次稽核說明（缺失）＋ 本次稽核結果（統計，2026-10-10 單獨挪到下方）──
    # 版面比照使用者範本「內部稽核報告」：
    #   本次稽核說明:  xx分
    #   [缺失 | 缺失內容]
    #   本次稽核結果:
    #   [稽核子項數 | n | 未達標項數 | n | 本期稽核分數 | xx分]
    rr = add_row()
    box = _merge(rr, 0, 4)
    _write(box, "")
    p = box.paragraphs[0]
    score_val = score["score"] if score else None
    _font(p.add_run("本次稽核說明:  "), BODY_PT)
    _font(p.add_run(_pct(score_val)), BODY_PT, color=_score_color(score_val))

    deficiency = box.add_table(rows=1, cols=2)
    deficiency.style = "Table Grid"
    deficiency.alignment = WD_TABLE_ALIGNMENT.CENTER
    _write(deficiency.rows[0].cells[0], "缺失", BODY_PT, align=WD_ALIGN_PARAGRAPH.CENTER, color=RED)
    _write(deficiency.rows[0].cells[1], dept.get("deficiency") or "", BODY_PT, color=RED)
    _fix_widths(deficiency, [Cm(2.6), Cm(14.0)])   # 範本 1474／7936 twips
    _row_height(deficiency.rows[0], 0.6)

    box.add_paragraph()
    p = box.add_paragraph()
    _font(p.add_run("本次稽核結果:"), BODY_PT)

    stats = box.add_table(rows=1, cols=6)
    stats.style = "Table Grid"
    stats.alignment = WD_TABLE_ALIGNMENT.CENTER
    sub = score["sub_count"] if score else 0
    passed = score["pass_count"] if score else 0
    failed = max(sub - passed, 0)   # 未達標項數 ＝ 稽核結果為 X 的數量（2026-10-10）
    vals = [("稽核子項數", str(sub)), ("未達標項數", str(failed)), ("本期稽核分數", _pct(score_val))]
    for idx, (label, val) in enumerate(vals):
        if idx == 2:
            val_color = _score_color(score_val)
        elif idx == 1 and failed > 0:
            val_color = RED
        else:
            val_color = None
        _write(stats.rows[0].cells[idx * 2], label, BODY_PT, align=WD_ALIGN_PARAGRAPH.CENTER)
        _write(stats.rows[0].cells[idx * 2 + 1], val, BODY_PT, align=WD_ALIGN_PARAGRAPH.CENTER,
               color=val_color)
        if idx == 1:   # 範本：「未達標項數」與數字黃色螢光
            for c_ in (stats.rows[0].cells[2], stats.rows[0].cells[3]):
                for run in c_.paragraphs[0].runs:
                    _highlight(run)
    # 範本 1874／709／1701／992／2433／1701 twips
    _fix_widths(stats, [Cm(3.3), Cm(1.25), Cm(3.0), Cm(1.75), Cm(4.3), Cm(3.0)])
    _row_height(stats.rows[0], 0.6)
    box.add_paragraph()   # 下方留白，比照原表

    _fix_widths(t, COLS)

    # ── 簽核列 ──
    # 2026-10-10 依範本改為 3 格（欄寬 3260／2976／3969 twips、列高 1423 twips）
    sig = doc.add_table(rows=1, cols=3)
    sig.style = "Table Grid"
    sig.alignment = WD_TABLE_ALIGNMENT.CENTER
    _row_height(sig.rows[0], 2.5)
    for idx, label in enumerate(["人資主管：", "受稽部門主管：", "稽核人員："]):
        cell = sig.rows[0].cells[idx]
        _write(cell, label, BODY_PT)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
        if idx == 2 and auditor_name:
            p = cell.add_paragraph()
            _font(p.add_run(auditor_name), BODY_PT, bold=False)
    _fix_widths(sig, [Cm(5.75), Cm(5.25), Cm(7.0)])

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
