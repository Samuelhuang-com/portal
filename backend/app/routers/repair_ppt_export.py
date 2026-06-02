"""
報修模組 PPT 匯出 — 獨立 Router
======================================
路由前綴：/repair/ppt-export
  POST /export  → 觸發匯出，回傳 .pptx StreamingResponse

支援模組：
  module="dazhi"  → 大直工務部
  module="luqun"  → 盧群商場工務報修

投影片順序（固定）：
  0. Cover（封面，更新年月）
  1. 3.1 報修統計
  2. 3.2 結案時間
  3. 3.3 柏拉圖分析（matplotlib 圖）
  4. 3.3 報修類型各類別（表格）
  5. Dashboard 報修類型分布（matplotlib 圓餅）
  6. 3.4 本月客房報修表（≤20 列/頁）
  7. 金額統計
  8. 未完成附表－飯店（≤20 列/頁）
"""

import logging
import os
from datetime import datetime
from io import BytesIO
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger("repair_ppt_export")

router = APIRouter(prefix="/repair/ppt-export", tags=["報修 PPT 匯出"])

TEMPLATE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "static",
                 "pptx_templates", "hotel_report_template.pptx")
)

ROWS_PER_SLIDE = 14   # 每頁最多行數（12pt 字 × 26pt 列高，確保不超出頁面）


# ═══════════════════════════════════════════════════════
# Request schema
# ═══════════════════════════════════════════════════════

class RepairPptBody(BaseModel):
    module: str   # "dazhi" | "luqun"
    year:   int
    month:  int   # 報表月份（客房報修表 / 未完成附表用）


# ═══════════════════════════════════════════════════════
# Internal helpers — matplotlib charts
# ═══════════════════════════════════════════════════════

def _cjk_font() -> Optional[str]:
    """回傳可用的 CJK 字型名稱，找不到回傳 None。"""
    try:
        import matplotlib.font_manager as fm
        _PRIORITY = [
            "Microsoft JhengHei", "Microsoft JhengHei UI",
            "PMingLiU", "MingLiU", "DFKai-SB",
            "Microsoft YaHei", "Microsoft YaHei UI", "SimHei", "SimSun",
            "PingFang TC", "PingFang SC", "Heiti TC",
            "Noto Sans CJK TC", "Noto Sans CJK SC", "WenQuanYi Micro Hei",
        ]
        available = {f.name for f in fm.fontManager.ttflist}
        found = next((fn for fn in _PRIORITY if fn in available), None)
        if found:
            return found
        keywords = ("jhenghei", "mingliu", "dfkai", "yahei", "simhei",
                    "pingfang", "heiti", "noto", "cjk", "wenquanyi",
                    "chinese", "gothic", "mincho")
        return next(
            (f.name for f in fm.fontManager.ttflist
             if any(k in f.name.lower() for k in keywords)),
            None,
        )
    except Exception:
        return None


def _setup_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    font = _cjk_font()
    if font:
        plt.rcParams["font.family"] = font
    plt.rcParams["axes.unicode_minus"] = False
    return plt


def _make_pareto_chart(type_rows: list) -> Optional[BytesIO]:
    """柏拉圖：Bar（深/淺藍）+ 累計折線 + 80% 虛線，回傳 PNG BytesIO。"""
    try:
        plt = _setup_mpl()
        # 排序、過濾 0 件
        rows = sorted([r for r in type_rows if r.get("row_total", 0) > 0],
                      key=lambda r: -r["row_total"])
        if not rows:
            return None
        labels  = [r["type"] for r in rows]
        counts  = [r["row_total"] for r in rows]
        total   = sum(counts)
        running = 0
        cum_pct = []
        for c in counts:
            running += c
            cum_pct.append(round(running / total * 100) if total else 0)

        C_BRAND  = "#1B3A5C"
        C_LIGHT  = "#4BA8E8"
        C_RED    = "#c0392b"

        fig, ax1 = plt.subplots(figsize=(10.5, 3.8), dpi=130)
        fig.patch.set_facecolor("white")

        bar_colors = [C_BRAND if p <= 80 else C_LIGHT for p in cum_pct]
        bars = ax1.bar(range(len(labels)), counts, color=bar_colors, width=0.65)
        ax1.set_xticks(range(len(labels)))
        ax1.set_xticklabels(labels, fontsize=8, rotation=30, ha="right")
        ax1.set_ylabel("件數", fontsize=8, color=C_BRAND)
        ax1.tick_params(axis="y", labelsize=8)
        ax1.set_ylim(0, max(counts) * 1.3)
        # Bar 數字標籤
        for bar, v in zip(bars, counts):
            ax1.text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + max(counts) * 0.02,
                     str(v), ha="center", va="bottom", fontsize=7, color=C_BRAND)

        ax2 = ax1.twinx()
        ax2.plot(range(len(labels)), cum_pct, color=C_RED,
                 marker="o", markersize=4, linewidth=2, zorder=5)
        ax2.set_ylabel("累計 %", fontsize=8, color=C_RED)
        ax2.set_ylim(0, 110)
        ax2.tick_params(axis="y", labelsize=8, colors=C_RED)
        # 折線數字標籤
        for i, p in enumerate(cum_pct):
            ax2.text(i, p + 3, f"{p}%", ha="center", va="bottom",
                     fontsize=7, color=C_RED, fontweight="bold")
        # 80% 虛線
        ax2.axhline(y=80, color=C_RED, linestyle="--", linewidth=1.2, alpha=0.7)
        ax2.text(len(labels) - 0.5, 82, "80%", color=C_RED, fontsize=8)

        ax1.grid(axis="y", linestyle="--", linewidth=0.4, color="#dddddd", zorder=0)
        ax1.set_title("報修類型柏拉圖分析", fontsize=10, fontweight="bold",
                      color=C_BRAND, pad=6)

        # 圖例色塊
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=C_BRAND, label="累計 ≤ 80%（重點）"),
            Patch(facecolor=C_LIGHT, label="累計 > 80%（次要）"),
        ]
        ax1.legend(handles=legend_elements, fontsize=7,
                   loc="upper right", framealpha=0.7)

        fig.tight_layout(pad=0.8)
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)
        return buf
    except Exception as e:
        logger.warning("Pareto chart error: %s", e, exc_info=True)
        return None


def _make_pie_chart(type_rows: list) -> Optional[BytesIO]:
    """類型分布圓餅圖：顯示類別名稱（佔比≥5% 才顯示外部標籤），回傳 PNG BytesIO。"""
    try:
        plt = _setup_mpl()
        rows = [r for r in type_rows if r.get("row_total", 0) > 0]
        if not rows:
            return None
        rows.sort(key=lambda r: -r["row_total"])
        labels = [r["type"] for r in rows]
        sizes  = [r["row_total"] for r in rows]
        total  = sum(sizes)
        COLORS = [
            "#1B3A5C", "#4BA8E8", "#F5A623", "#2ECC71", "#E74C3C",
            "#9B59B6", "#1ABC9C", "#E67E22", "#3498DB", "#34495E",
            "#F39C12", "#27AE60", "#8E44AD", "#D35400",
        ]
        colors = [COLORS[i % len(COLORS)] for i in range(len(labels))]

        LABEL_THRESHOLD = 5.0   # 佔比 >= 5% 才顯示類別名稱

        fig, ax = plt.subplots(figsize=(9, 4.5), dpi=130)
        fig.patch.set_facecolor("white")

        # 外部標籤：僅大 slice 顯示類別名稱
        outer_labels = [
            lb if (sz / total * 100) >= LABEL_THRESHOLD else ""
            for lb, sz in zip(labels, sizes)
        ]
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=outer_labels,
            colors=colors,
            autopct=lambda p: f"{p:.1f}%" if p >= LABEL_THRESHOLD else "",
            pctdistance=0.72,
            labeldistance=1.13,
            startangle=90,
            textprops={"fontsize": 7.5},
        )
        for at in autotexts:
            at.set_fontsize(7)
            at.set_color("white")
            at.set_fontweight("bold")
        for txt in texts:
            txt.set_fontsize(7.5)

        ax.legend(
            wedges,
            [f"{lb}（{sz}件）" for lb, sz in zip(labels, sizes)],
            loc="center left",
            bbox_to_anchor=(1.0, 0.5),
            fontsize=7.5,
            framealpha=0.8,
        )
        ax.set_title("報修類型分布", fontsize=10, fontweight="bold",
                     color="#1B3A5C", pad=6)
        ax.axis("equal")
        fig.tight_layout(pad=0.5)
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)
        return buf
    except Exception as e:
        logger.warning("Pie chart error: %s", e, exc_info=True)
        return None


# ═══════════════════════════════════════════════════════
# Internal helpers — slide builders
# ═══════════════════════════════════════════════════════

def _sanitize(val) -> str:
    s = str(val) if val is not None else "—"
    return s.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')


def _fmt_rate(v) -> str:
    return f"{v}%" if v is not None else "—"


def _fmt_money(v) -> str:
    if v is None or v == 0:
        return "—"
    return f"${v:,.0f}"


def _add_chart_slide(prs, template_idx: int,
                     title: str, subtitle: str,
                     chart_buf: Optional[BytesIO],
                     now_str: str, SW: float, SH: float):
    """Clone template, set title, embed chart image."""
    from app.routers.hotel_overview import (
        _clone_template_slide, _set_slide_title, _pptx_txt,
    )
    from pptx.util import Inches
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    C_BLACK = RGBColor(0x00, 0x00, 0x00)
    C_GRAY  = RGBColor(0x88, 0x88, 0x88)

    slide = _clone_template_slide(prs, template_idx)
    _set_slide_title(slide, title, "", now_str, SW, SH)
    if subtitle:
        _pptx_txt(slide, subtitle, 0.35, 0.52, SW - 4.5, 0.22,
                  size=10, bold=True, color=C_BLACK)

    if chart_buf:
        IMG_W = SW - 1.0
        IMG_H = SH - 1.8
        IMG_X = 0.5
        IMG_Y = 1.05
        slide.shapes.add_picture(chart_buf, Inches(IMG_X), Inches(IMG_Y),
                                 Inches(IMG_W), Inches(IMG_H))
    else:
        _pptx_txt(slide, "（本期暫無圖表資料）",
                  2.0, 3.5, 9.0, 1.0, size=14, color=C_GRAY, italic=True)
    return slide


def _set_cell_bottom_border(cell, width_pt: float = 2.5, color_hex: str = "1B3A5C"):
    """在 pptx 表格儲存格底部加粗線（lxml XML 操作）。
    OOXML 規範：a:lnB 必須在 tcPr 內的 fill 元素之前，
    所以用 insert(0, ...) 插到最前面而非 SubElement 追加末尾。
    """
    from lxml import etree
    from pptx.oxml.ns import qn as _qn
    width_emu = int(width_pt * 12700)
    tc = cell._tc

    # 取得或建立 tcPr（必須在 txBody 之後）
    tcPr = tc.find(_qn('a:tcPr'))
    if tcPr is None:
        # 插在 txBody 之後
        txBody = tc.find(_qn('a:txBody'))
        idx = list(tc).index(txBody) + 1 if txBody is not None else len(tc)
        tcPr = etree.Element(_qn('a:tcPr'))
        tc.insert(idx, tcPr)

    # 移除已有 lnB
    for existing in tcPr.findall(_qn('a:lnB')):
        tcPr.remove(existing)

    # 建構 lnB 元素
    lnB = etree.Element(_qn('a:lnB'))
    lnB.set('w', str(width_emu))
    lnB.set('cap', 'flat')
    lnB.set('cmpd', 'sng')
    solidFill = etree.SubElement(lnB, _qn('a:solidFill'))
    srgbClr   = etree.SubElement(solidFill, _qn('a:srgbClr'))
    srgbClr.set('val', color_hex)

    # 插到 tcPr 最前面（border 元素必須先於 fill 元素，符合 OOXML schema 順序）
    tcPr.insert(0, lnB)


def _add_table_slides(prs, template_idx: int,
                      title: str, subtitle: str,
                      columns: list, rows: list,
                      now_str: str, SW: float, SH: float,
                      max_rows: int = ROWS_PER_SLIDE,
                      sep_after_rows: list = None):
    """Clone 1+ slides, build generic table (≤ max_rows per page).
    sep_after_rows: 0-based data row indices (not counting header) that get a thick bottom border.
    """
    from app.routers.hotel_overview import (
        _clone_template_slide, _set_slide_title,
        _pptx_cell, _pptx_header_row, _pptx_txt,
    )
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    C_DARK    = RGBColor(0x1B, 0x3A, 0x5C)
    C_ROW_ALT = RGBColor(0xEE, 0xF5, 0xFB)
    C_GRAY    = RGBColor(0x88, 0x88, 0x88)
    _ALIGN    = {"right": PP_ALIGN.RIGHT, "center": PP_ALIGN.CENTER}

    TABLE_Y = 0.95
    TABLE_H = SH - TABLE_Y - 0.45
    TABLE_W = SW - 0.8

    pages = [rows[i:i + max_rows] for i in range(0, max(len(rows), 1), max_rows)]
    total_pages = len(pages)

    for pg_idx, pg_rows in enumerate(pages):
        slide = _clone_template_slide(prs, template_idx)
        pg_sub = (subtitle
                  if total_pages == 1
                  else f"{subtitle}　第 {pg_idx + 1} 頁／共 {total_pages} 頁　（共 {len(rows)} 筆）")
        _set_slide_title(slide, title, "", now_str, SW, SH)
        if pg_sub:
            _pptx_txt(slide, pg_sub, 0.35, 0.52, SW - 4.5, 0.22,
                      size=10, bold=True, color=RGBColor(0x00, 0x00, 0x00))

        if not pg_rows or not columns:
            _pptx_txt(slide, "（本期暫無資料）",
                      2.0, 3.5, 9.0, 1.0, size=14, color=C_GRAY, italic=True)
            continue

        n_cols = len(columns)
        n_rows = len(pg_rows) + 1
        tbl = slide.shapes.add_table(
            n_rows, n_cols,
            Inches(0.4), Inches(TABLE_Y), Inches(TABLE_W), Inches(TABLE_H)
        ).table

        used = 0.0
        for ci, col in enumerate(columns):
            w = col.get("width", TABLE_W / n_cols)
            if ci == n_cols - 1:
                w = max(TABLE_W - used, 0.3)
            tbl.columns[ci].width = Inches(w)
            used += w

        for ci, col in enumerate(columns):
            _pptx_cell(tbl, 0, ci, col.get("label", col["key"]), bold=True)
        _pptx_header_row(tbl, n_cols, size=12)

        for ri, row in enumerate(pg_rows, 1):
            # 支援列級別顏色覆寫（_row_bg / _row_fg），不覆寫則用預設交替色
            _override_bg = row.get("_row_bg")
            _override_fg = row.get("_row_fg")
            bg  = _override_bg if _override_bg is not None else (C_ROW_ALT if ri % 2 == 0 else None)
            fg  = _override_fg if _override_fg is not None else C_DARK
            for ci, col in enumerate(columns):
                raw = _sanitize(row.get(col["key"], ""))
                align = _ALIGN.get(col.get("align", "left"))
                # 第一欄（統計項目）：使用 bold，其餘正常
                is_first = (ci == 0)
                _pptx_cell(tbl, ri, ci, raw, fg=fg, bg=bg, size=12,
                           align=align, bold=is_first)

        tbl.rows[0].height = Pt(34)
        for ri in range(1, n_rows):
            tbl.rows[ri].height = Pt(26)

        # 分隔粗線：在指定資料列底部加粗線（0-based，不含 header）
        if sep_after_rows:
            # 換算到本頁的區域索引：pg_rows 是整體 rows 的切片
            page_start = pg_idx * max_rows
            for sep_idx in sep_after_rows:
                local_idx = sep_idx - page_start  # 在本頁中的 0-based 位置
                tbl_row_idx = local_idx + 1         # +1 for header row
                if 1 <= tbl_row_idx < n_rows:
                    for ci in range(n_cols):
                        _set_cell_bottom_border(tbl.cell(tbl_row_idx, ci),
                                                width_pt=2.5, color_hex="1B3A5C")


# ═══════════════════════════════════════════════════════
# Annual matrix helpers — 年度計劃表投影片
# ═══════════════════════════════════════════════════════

# 狀態 → (符號, bg RGBColor, fg RGBColor)
_MATRIX_STATUS_STYLE = None   # 延遲初始化（需 pptx 匯入）

def _matrix_status_style():
    """回傳狀態樣式對照表（lazy init）。"""
    global _MATRIX_STATUS_STYLE
    if _MATRIX_STATUS_STYLE is not None:
        return _MATRIX_STATUS_STYLE
    from pptx.dml.color import RGBColor as _R
    _MATRIX_STATUS_STYLE = {
        "completed":    ("✓", _R(0xE8, 0xF5, 0xE9), _R(0x27, 0x7D, 0x27)),  # 綠底綠字
        "in_progress":  ("○", _R(0xFF, 0xFB, 0xE6), _R(0xD4, 0x88, 0x06)),  # 黃底橙字
        "scheduled":    ("○", _R(0xFF, 0xFB, 0xE6), _R(0xD4, 0x88, 0x06)),  # 同上
        "unscheduled":  ("△", _R(0xFF, 0xF4, 0xE6), _R(0xFA, 0x8C, 0x16)),  # 淡橙底橙字
        "overdue":      ("✗", _R(0xFF, 0xF2, 0xF0), _R(0xCF, 0x13, 0x22)),  # 紅底紅字
        "no_data":      ("?", _R(0xFA, 0xFA, 0xFA), _R(0xAA, 0xAA, 0xAA)),  # 灰底灰字
        "non_month":    ("",  None,                  _R(0xDD, 0xDD, 0xDD)),  # 空白
        "no_frequency": ("",  None,                  _R(0xDD, 0xDD, 0xDD)),  # 空白
    }
    return _MATRIX_STATUS_STYLE


def _get_annual_matrix_rows(module: str, year: int, db) -> list:
    """
    依模組取得年度計劃表資料，回傳統一格式的 list。
    每筆: {"source": str, "category": str, "task_name": str,
           "frequency": str, "cells": [{month, status}, ...]}
    dazhi   → hotel periodic-maintenance (PMSchedule)
    luqun   → mall periodic-maintenance (MallPMSchedule)
              + full-building-maintenance (FullBldgPMSchedule)
    """
    results = []

    if module == "dazhi":
        # ── 飯店週期保養 ───────────────────────────────────────────────────
        from app.routers.periodic_maintenance import (
            _get_latest_batch_items, _calc_schedule_status, _should_schedule,
        )
        from app.models.pm_schedule import PMSchedule
        items = _get_latest_batch_items(db)
        year_recs = (
            db.query(PMSchedule)
            .filter(PMSchedule.year_month.like(f"{year}/%"))
            .all()
        )
        smap = {}
        for r in year_recs:
            try:
                m = int(r.year_month.split("/")[1])
                smap[(r.item_ragic_id, m)] = r
            except Exception:
                pass
        for item in items:
            cells = []
            for m in range(1, 13):
                rec = smap.get((item.ragic_id, m))
                if rec:
                    cells.append({"month": m, "status": _calc_schedule_status(rec)})
                elif not (item.frequency or "").strip():
                    cells.append({"month": m, "status": "no_frequency"})
                elif _should_schedule(item, year, m):
                    cells.append({"month": m, "status": "no_data"})
                else:
                    cells.append({"month": m, "status": "non_month"})
            results.append({
                "source":    "飯店週期保養",
                "category":  item.category,
                "task_name": item.task_name,
                "frequency": item.frequency or "",
                "cells":     cells,
            })

    else:  # luqun — 商場週期保養 + 全棟例行維護
        # ── 商場週期保養 ───────────────────────────────────────────────────
        from app.routers.mall_periodic_maintenance import (
            _mall_get_latest_batch_items, _mall_calc_schedule_status,
            _should_schedule as _mall_should_schedule,
        )
        from app.models.mall_pm_schedule import MallPMSchedule
        mall_items = _mall_get_latest_batch_items(db)
        mall_recs = (
            db.query(MallPMSchedule)
            .filter(MallPMSchedule.year_month.like(f"{year}/%"))
            .all()
        )
        mall_smap = {}
        for r in mall_recs:
            try:
                m = int(r.year_month.split("/")[1])
                mall_smap[(r.item_ragic_id, m)] = r
            except Exception:
                pass
        for item in mall_items:
            cells = []
            for m in range(1, 13):
                rec = mall_smap.get((item.ragic_id, m))
                if rec:
                    cells.append({"month": m, "status": _mall_calc_schedule_status(rec)})
                elif not (item.frequency or "").strip():
                    cells.append({"month": m, "status": "no_frequency"})
                elif _mall_should_schedule(item, year, m):
                    cells.append({"month": m, "status": "no_data"})
                else:
                    cells.append({"month": m, "status": "non_month"})
            results.append({
                "source":    "商場週期保養",
                "category":  item.category,
                "task_name": item.task_name,
                "frequency": item.frequency or "",
                "cells":     cells,
            })

        # ── 全棟例行維護 ───────────────────────────────────────────────────
        from app.routers.full_building_maintenance import (
            _fb_get_latest_batch_items, _fb_calc_schedule_status,
            _fb_should_schedule_by_freq,
        )
        from app.models.full_bldg_pm_schedule import FullBldgPMSchedule
        fb_items = _fb_get_latest_batch_items(db)
        fb_recs = (
            db.query(FullBldgPMSchedule)
            .filter(FullBldgPMSchedule.year_month.like(f"{year}/%"))
            .all()
        )
        fb_smap = {}
        for r in fb_recs:
            try:
                m = int(r.year_month.split("/")[1])
                fb_smap[(r.item_ragic_id, m)] = r
            except Exception:
                pass
        for item in fb_items:
            cells = []
            for m in range(1, 13):
                rec = fb_smap.get((item.ragic_id, m))
                if rec:
                    cells.append({"month": m, "status": _fb_calc_schedule_status(rec)})
                elif not (item.frequency or "").strip():
                    cells.append({"month": m, "status": "no_frequency"})
                elif _fb_should_schedule_by_freq(item.frequency or "", m):
                    cells.append({"month": m, "status": "no_data"})
                else:
                    cells.append({"month": m, "status": "non_month"})
            results.append({
                "source":    "全棟例行維護",
                "category":  item.category,
                "task_name": item.task_name,
                "frequency": item.frequency or "",
                "cells":     cells,
            })

    return results


def _add_annual_matrix_slide(prs, template_idx: int,
                              title: str, subtitle: str,
                              matrix_rows: list,
                              now_str: str, SW: float, SH: float):
    """
    年度計劃表矩陣投影片。
    每格依狀態顯示符號（✓/○/✗/△/?）+ 對應底色。
    超過 ROWS_PER_SLIDE 自動分頁。
    """
    from app.routers.hotel_overview import (
        _clone_template_slide, _set_slide_title, _pptx_cell,
        _pptx_header_row, _pptx_txt,
    )
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    C_DARK    = RGBColor(0x1B, 0x3A, 0x5C)
    C_WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
    C_ROW_ALT = RGBColor(0xF7, 0xF9, 0xFC)
    C_GRAY    = RGBColor(0x88, 0x88, 0x88)
    STYLE     = _matrix_status_style()

    CELL_SIZE  = 12   # 字體 pt（與其他內頁一致）
    TABLE_Y    = 0.95
    TABLE_H    = SH - TABLE_Y - 0.45
    TABLE_W    = SW - 0.8

    # 欄位寬度：類別(0.90) + 項目名稱(2.40) + 頻率(0.70) + 12×月份(auto)
    W_CAT   = 0.90
    W_TASK  = 2.40
    W_FREQ  = 0.70
    W_AVAIL = TABLE_W - W_CAT - W_TASK - W_FREQ
    W_MON   = round(W_AVAIL / 12, 3)   # 每月欄寬（最後一欄 auto）

    columns = [
        {"key": "category",  "label": "類別",   "width": W_CAT,  "align": "left"},
        {"key": "task_name", "label": "項目名稱","width": W_TASK, "align": "left"},
        {"key": "frequency", "label": "頻率",    "width": W_FREQ, "align": "center"},
    ]
    for m in range(1, 13):
        columns.append({"key": f"m{m}", "label": f"{m}月", "width": W_MON, "align": "center"})

    pages = [
        matrix_rows[i:i + ROWS_PER_SLIDE]
        for i in range(0, max(len(matrix_rows), 1), ROWS_PER_SLIDE)
    ]
    total_pages = len(pages)

    for pg_idx, pg_rows in enumerate(pages):
        slide = _clone_template_slide(prs, template_idx)
        pg_sub = (subtitle if total_pages == 1
                  else f"{subtitle}　第 {pg_idx + 1} 頁／共 {total_pages} 頁")
        _set_slide_title(slide, title, "", now_str, SW, SH)
        if pg_sub:
            _pptx_txt(slide, pg_sub, 0.35, 0.52, SW - 4.5, 0.22,
                      size=10, bold=True, color=RGBColor(0x00, 0x00, 0x00))

        if not pg_rows:
            _pptx_txt(slide, "（本期暫無保養排程資料）",
                      2.0, 3.5, 9.0, 1.0, size=14, color=C_GRAY, italic=True)
            continue

        n_cols = len(columns)
        n_rows = len(pg_rows) + 1
        tbl = slide.shapes.add_table(
            n_rows, n_cols,
            Inches(0.4), Inches(TABLE_Y), Inches(TABLE_W), Inches(TABLE_H)
        ).table

        used = 0.0
        for ci, col in enumerate(columns):
            w = col.get("width", TABLE_W / n_cols)
            if ci == n_cols - 1:
                w = max(TABLE_W - used, 0.3)
            tbl.columns[ci].width = Inches(w)
            used += w

        # Header row
        for ci, col in enumerate(columns):
            _pptx_cell(tbl, 0, ci, col["label"], bold=True)
        _pptx_header_row(tbl, n_cols, size=CELL_SIZE)

        # Data rows
        _ALIGN_MAP = {"right": PP_ALIGN.RIGHT, "center": PP_ALIGN.CENTER}
        for ri, row in enumerate(pg_rows, 1):
            row_bg = C_ROW_ALT if ri % 2 == 0 else None
            for ci, col in enumerate(columns):
                key = col["key"]
                align = _ALIGN_MAP.get(col.get("align", "left"))

                if key.startswith("m") and key[1:].isdigit():
                    m = int(key[1:])
                    cell_info = next(
                        (c for c in row.get("cells", []) if c["month"] == m), None
                    )
                    status = cell_info["status"] if cell_info else "non_month"
                    sym, s_bg, s_fg = STYLE.get(status, ("", None, C_GRAY))
                    bg = s_bg if s_bg is not None else row_bg
                    _pptx_cell(tbl, ri, ci, sym,
                               fg=s_fg, bg=bg, size=CELL_SIZE,
                               align=PP_ALIGN.CENTER, bold=(status == "completed"))
                else:
                    text = _sanitize(row.get(key, ""))
                    _pptx_cell(tbl, ri, ci, text,
                               fg=C_DARK, bg=row_bg, size=CELL_SIZE,
                               align=align, bold=(ci == 0))

        tbl.rows[0].height = Pt(34)
        for ri in range(1, n_rows):
            tbl.rows[ri].height = Pt(26)


# ═══════════════════════════════════════════════════════
# Core PPT builder
# ═══════════════════════════════════════════════════════

def _build_repair_pptx(module: str, year: int, month: int, db: Session) -> BytesIO:
    from pptx import Presentation
    from app.routers.hotel_overview import (
        _update_cover_date, _clone_template_slide, _delete_slide,
    )

    # ── 載入服務 ──────────────────────────────────────────────────────────────
    if module == "dazhi":
        from app.models.dazhi_repair import DazhiRepairCase as CaseModel
        import app.services.dazhi_repair_service as svc
        module_label = "大直工務部"
    else:
        from app.models.luqun_repair import LuqunRepairCase as CaseModel
        import app.services.luqun_repair_service as svc
        module_label = "盧群商場工務報修"

    from app.services import repair_report_service as rr_svc

    all_cases   = db.query(CaseModel).all()
    now_str     = datetime.now().strftime("%Y-%m-%d %H:%M")
    period_str  = f"{year}年{month:02d}月"

    # ── 載入 Presentation ─────────────────────────────────────────────────────
    prs = Presentation(TEMPLATE_PATH)
    SW  = prs.slide_width.inches
    SH  = prs.slide_height.inches

    # ── Slide 0: Cover ───────────────────────────────────────────────────────
    _update_cover_date(prs.slides[0], year, month)

    # 刪除 TOC slide(index=1)，保留 cover(0) + template(1)
    _delete_slide(prs, 1)
    TMPL = 1   # content template 索引（刪除 TOC 後固定為 1）

    # ══════════════════════════════════════════════════════════════════════════
    # Slide A — 3.1 報修統計（橫向：欄=月份1→12，列=統計項目）
    # ══════════════════════════════════════════════════════════════════════════
    repair_stats = svc.compute_repair_stats(all_cases, year)
    months_data  = repair_stats.get("months", {})
    # 每列為一個統計項目，每欄為一個月份（共 9 項，與 portal 完全一致）
    # kind: "count"=直接取值, "rate"=百分比格式, "sum2"=兩欄相加
    from pptx.dml.color import RGBColor as _RGB
    _C_RED_BG  = _RGB(0xFF, 0xF5, 0xF5)   # 淡紅底（③ 列）
    _C_RED_FG  = _RGB(0xC0, 0x39, 0x2B)   # 深紅字（③⑦ 列）
    _C_RATE_FG = _RGB(0xFA, 0x8C, 0x16)   # 橙色字（④⑧ 完成率列）
    _C_SUM_BG  = _RGB(0xE8, 0xF0, 0xFE)   # 淡藍底（⑨ 合計列）
    _C_DARK    = _RGB(0x1B, 0x3A, 0x5C)   # 品牌深藍（預設）

    # (label, kind, field, _row_bg, _row_fg)
    _stat31_defs = [
        ("① 上月累計未完成項目數",          "count", "prev_uncompleted",          None,      None),
        ("② 上月累計未完成，於本月結案",     "count", "closed_from_prev",           None,      None),
        ("③ 上月累計未完成，於本月仍未完成", "count", "prev_remaining",             _C_RED_BG, _C_RED_FG),
        ("④ 累計項目完成率",                 "rate",  "cum_completion_rate",        None,      _C_RATE_FG),
        ("⑤ 本月報修項目數",                 "count", "this_month_total",           None,      None),
        ("⑥ 本月報修項目完成數",             "count", "this_month_completed",       None,      None),
        ("⑦ 本月報修項目未完成",             "count", "this_month_uncompleted",     None,      _C_RED_FG),
        ("⑧ 本月報修項目完成率",             "rate",  "this_month_completion_rate", None,      _C_RATE_FG),
        ("⑨ 項目完成件數（②＋⑥）",          "sum2",  ("closed_from_prev", "this_month_completed"), _C_SUM_BG, _C_DARK),
    ]
    stats_rows = []
    for label, kind, field, row_bg, row_fg in _stat31_defs:
        row: dict = {"item": label}
        if row_bg is not None:
            row["_row_bg"] = row_bg
        if row_fg is not None:
            row["_row_fg"] = row_fg
        for m in range(1, 13):
            if m > month:          # 未來月份統一顯示 —
                row[f"m{m}"] = "—"
            else:
                md = months_data.get(m, {})
                if kind == "rate":
                    row[f"m{m}"] = _fmt_rate(md.get(field))
                elif kind == "sum2":
                    a, b = field
                    row[f"m{m}"] = _sanitize((md.get(a) or 0) + (md.get(b) or 0))
                else:
                    row[f"m{m}"] = _sanitize(md.get(field, 0))
        stats_rows.append(row)
    stats_cols = [{"key": "item", "label": "統計項目", "width": 2.90, "align": "left"}]
    for m in range(1, 13):
        stats_cols.append({"key": f"m{m}", "label": f"{m}月", "width": 0.80, "align": "center"})
    _add_table_slides(
        prs, TMPL,
        title    = "3.1 報修統計",
        subtitle = f"{period_str}",
        columns  = stats_cols,
        rows     = stats_rows,
        now_str  = now_str,
        SW=SW, SH=SH,
        sep_after_rows = [3, 7],   # ④後（累計完成率↔本月報修）、⑧後（本月完成率↔合計件數）
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Slide B — 3.2 結案時間（橫向：欄=月份1→12，列=統計項目）
    # ══════════════════════════════════════════════════════════════════════════
    closing = svc.compute_closing_time(all_cases, year)
    monthly_closing = closing.get("monthly", {})
    # 6 列：與 portal 完全一致（小型 3 列 + 中大型 3 列）
    # kind: "count"=整數, "days"=小數1位, "avg"=小數2位（None→"—"）
    from pptx.dml.color import RGBColor as _RGB32
    _C_SMALL_BG = _RGB32(0xEE, 0xF5, 0xFB)   # 淡藍（小型組）
    _C_LARGE_BG = _RGB32(0xF0, 0xEB, 0xFF)   # 淡紫（中大型組）
    _C_DARK32   = _RGB32(0x1B, 0x3A, 0x5C)
    _C_PURPLE   = _RGB32(0x5B, 0x2D, 0x8E)   # 中大型深紫字

    _stat32_defs = [
        # (label,            size,    field,         kind,    row_bg,       row_fg)
        ("小型 結案件數",    "small", "closed_count", "count", _C_SMALL_BG,  _C_DARK32),
        ("小型 天數合計",    "small", "total_days",   "days",  _C_SMALL_BG,  _C_DARK32),
        ("小型 平均天數",    "small", "avg_days",     "avg",   _C_SMALL_BG,  _C_DARK32),
        ("中大型 結案件數",  "large", "closed_count", "count", _C_LARGE_BG,  _C_PURPLE),
        ("中大型 天數合計",  "large", "total_days",   "days",  _C_LARGE_BG,  _C_PURPLE),
        ("中大型 平均天數",  "large", "avg_days",     "avg",   _C_LARGE_BG,  _C_PURPLE),
    ]
    closing_rows = []
    for label, size_key, field, kind, row_bg, row_fg in _stat32_defs:
        row: dict = {"item": label, "_row_bg": row_bg, "_row_fg": row_fg}
        for m in range(1, 13):
            if m > month:
                row[f"m{m}"] = "—"
            else:
                mc  = monthly_closing.get(m, {})
                obj = mc.get(size_key, {})
                v   = obj.get(field)
                if kind == "count":
                    row[f"m{m}"] = _sanitize(v or 0)
                elif kind == "days":
                    row[f"m{m}"] = _sanitize(round(v, 1)) if v else "—"
                else:   # avg
                    row[f"m{m}"] = _sanitize(round(v, 2)) if v else "—"
        closing_rows.append(row)
    closing_cols = [{"key": "item", "label": "類別 / 月份", "width": 2.10, "align": "left"}]
    for m in range(1, 13):
        closing_cols.append({"key": f"m{m}", "label": f"{m}月", "width": 0.87, "align": "center"})
    _add_table_slides(
        prs, TMPL,
        title    = "3.2 結案時間統計",
        subtitle = f"{period_str}",
        columns  = closing_cols,
        rows     = closing_rows,
        now_str  = now_str,
        SW=SW, SH=SH,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Slide C — 3.3 柏拉圖分析（圖）
    # ══════════════════════════════════════════════════════════════════════════
    type_stats = svc.compute_type_stats(all_cases, year)
    type_rows  = type_stats.get("rows", [])
    pareto_buf = _make_pareto_chart(type_rows)
    _add_chart_slide(
        prs, TMPL,
        title     = "3.3 報修類型 — 柏拉圖分析",
        subtitle  = f"{period_str}　深藍＝累計≤80%重點類別",
        chart_buf = pareto_buf,
        now_str   = now_str, SW=SW, SH=SH,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Slide D — 3.3 報修類型各類別（表格）
    # ══════════════════════════════════════════════════════════════════════════
    # 年度佔比：直接取 service 計算好的 cum_pct（= row_total / len(year_cases)），
    # 與前端 3.3 TAB「年度佔比」欄位口徑完全一致。
    # 不再自行用 year_total 重算（year_total 只計 REPAIR_TYPE_ORDER 內且 month 非 None 的案件，
    # 分母不同會造成數字差異）。
    sorted_type_rows = sorted(type_rows, key=lambda r: -r.get("row_total", 0))
    type_table_rows = []
    for r in sorted_type_rows:
        if r.get("row_total", 0) == 0:
            continue
        row_d = {
            "type":    r["type"],
            "total":   str(r.get("row_total", 0)),
            "pct":     f"{r.get('cum_pct', 0)}%",
        }
        for m in range(1, 13):
            v = r.get("monthly", {}).get(m, 0)
            row_d[f"m{m}"] = str(v) if v else "—"
        type_table_rows.append(row_d)

    type_cols = [
        {"key": "type",  "label": "類別", "width": 1.30, "align": "left"},
    ]
    for m in range(1, 13):
        type_cols.append({"key": f"m{m}", "label": f"{m}月", "width": 0.72, "align": "center"})
    type_cols += [
        {"key": "total", "label": "合計", "width": 0.80, "align": "center"},
        {"key": "pct",   "label": "佔比%", "width": 0.80, "align": "center"},
    ]

    _add_table_slides(
        prs, TMPL,
        title    = "3.3 報修類型各類別",
        subtitle = f"{period_str}　依件數降序",
        columns  = type_cols,
        rows     = type_table_rows,
        now_str  = now_str,
        SW=SW, SH=SH,
        max_rows = 9999,   # 不分頁，全部類別同一張投影片
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Slide E — Dashboard 報修類型分布（圓餅）
    # ══════════════════════════════════════════════════════════════════════════
    pie_buf = _make_pie_chart(type_rows)
    _add_chart_slide(
        prs, TMPL,
        title     = "Dashboard — 報修類型分布",
        subtitle  = f"{period_str}",
        chart_buf = pie_buf,
        now_str   = now_str, SW=SW, SH=SH,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Slide F — 3.4 本月客房報修表（僅飯店模組，商場不顯示）
    # ══════════════════════════════════════════════════════════════════════════
    if module == "dazhi":
        room_data = svc.compute_room_repair_table(all_cases, year, month)
        room_rows_raw = room_data.get("rows", [])
        room_table_rows = []
        for r in room_rows_raw:
            cats = r.get("categories", {})
            cat_counts = {cat: len(cases) for cat, cases in cats.items()}
            total_cnt  = sum(cat_counts.values())
            involved   = "、".join(c for c, n in cat_counts.items() if n > 0)
            room_table_rows.append({
                "room_no": r.get("room_no", ""),
                "floor":   r.get("floor", ""),
                "total":   str(total_cnt),
                "cats":    involved or "—",
            })
        _add_table_slides(
            prs, TMPL,
            title    = "3.4 本月客房報修表",
            subtitle = f"{period_str}",
            columns  = [
                {"key": "room_no", "label": "房號",   "width": 1.0,  "align": "center"},
                {"key": "floor",   "label": "樓層",   "width": 0.8,  "align": "center"},
                {"key": "total",   "label": "報修件數","width": 1.0,  "align": "center"},
                {"key": "cats",    "label": "涉及類別","width": 9.35, "align": "left"},
            ],
            rows     = room_table_rows,
            now_str  = now_str,
            SW=SW, SH=SH,
            max_rows = ROWS_PER_SLIDE,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # Slide G — 金額統計（橫向：欄=月份1→12+全年合計，列=費用項目）
    # ══════════════════════════════════════════════════════════════════════════
    fee_stats  = svc.compute_fee_stats(all_cases, year)
    monthly_t  = fee_stats.get("monthly_totals", {})
    month_t    = fee_stats.get("month_totals", {})
    ft         = fee_stats.get("fee_totals", {})
    # 動態讀取各費用欄位（dazhi=3項；luqun=4項含扣款專櫃）
    fee_labels = fee_stats.get("fee_labels", {
        "outsource_fee":   "委外費用",
        "maintenance_fee": "維修費用",
        "deduction_fee":   "扣款費用",
    })

    def _fmt_fee_val(fk: str, v) -> str:
        """扣款專櫃為計數（家數），其餘為金額。"""
        if fk == "deduction_counter":
            return str(int(v)) if v else "—"
        return _fmt_money(v)

    fee_rows = []
    for fk, label in fee_labels.items():
        row: dict = {"item": label}
        for m in range(1, 13):
            row[f"m{m}"] = "—" if m > month else _fmt_fee_val(fk, monthly_t.get(m, {}).get(fk, 0))
        row["total"] = _fmt_fee_val(fk, ft.get(fk, 0))
        fee_rows.append(row)
    # 月小計列
    subtotal_row: dict = {"item": "月小計"}
    for m in range(1, 13):
        subtotal_row[f"m{m}"] = "—" if m > month else _fmt_money(month_t.get(m, 0))
    subtotal_row["total"] = _fmt_money(fee_stats.get("grand_total", 0))
    fee_rows.append(subtotal_row)
    # 欄定義：費用項目 + 1~12月 + 全年合計（最後欄自動填滿）
    fee_cols = [{"key": "item", "label": "費用項目", "width": 1.40, "align": "left"}]
    for m in range(1, 13):
        fee_cols.append({"key": f"m{m}", "label": f"{m}月", "width": 0.82, "align": "right"})
    fee_cols.append({"key": "total", "label": "全年合計", "align": "right"})
    _add_table_slides(
        prs, TMPL,
        title    = "金額統計",
        subtitle = f"{period_str}",
        columns  = fee_cols,
        rows     = fee_rows,
        now_str  = now_str,
        SW=SW, SH=SH,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Slide I — 年度計劃表
    #   dazhi → 飯店週期保養年度計劃表（1 張）
    #   luqun → 商場週期保養年度計劃表 + 全棟例行維護年度計劃表（各 1+ 張）
    # ══════════════════════════════════════════════════════════════════════════
    try:
        _matrix_src_map = {
            "dazhi": [("飯店週期保養", "飯店週期保養年度計劃表")],
            "luqun": [("商場週期保養", "商場週期保養年度計劃表"),
                      ("全棟例行維護", "全棟例行維護年度計劃表")],
        }
        all_matrix_rows = _get_annual_matrix_rows(module, year, db)
        for source_label, slide_title in _matrix_src_map.get(module, []):
            src_rows = [r for r in all_matrix_rows if r["source"] == source_label]
            _add_annual_matrix_slide(
                prs, TMPL,
                title    = slide_title,
                subtitle = f"{year}年　狀態：✓已完成 ○已排定 ✗逾期 △未排定 ?待排",
                matrix_rows = src_rows,
                now_str  = now_str, SW=SW, SH=SH,
            )
    except Exception as _e:
        logger.warning("年度計劃表投影片產生失敗（跳過）：%s", _e)

    # ══════════════════════════════════════════════════════════════════════════
    # Slide H — 未完成附表（飯店顯示飯店，商場顯示商場）
    # ══════════════════════════════════════════════════════════════════════════
    _is_hotel = (module == "dazhi")
    unfinished = rr_svc.get_all_unfinished_cases(
        db=db, year=year, month=month,
        include_hotel=_is_hotel,
        include_mall=not _is_hotel,
    )
    uf_title = "未完成附表（飯店）" if _is_hotel else "未完成附表（商場）"
    uf_rows = []
    for c in unfinished:
        uf_rows.append({
            "case_no":   _sanitize(c.get("case_no", "")),
            "occurred":  (_sanitize(c.get("occurred_at", "")) or "")[:10],
            "floor":     _sanitize(c.get("floor", "")),
            "rtype":     _sanitize(c.get("repair_type", "")),
            "title":     _sanitize(c.get("title", "")),
            "status":    _sanitize(c.get("status", "")),
            "days":      _sanitize(c.get("pending_days", "")),
            "unit":      _sanitize(c.get("responsible_unit", "")),
        })
    _add_table_slides(
        prs, TMPL,
        title    = uf_title,
        subtitle = f"{period_str}　每頁最多 {ROWS_PER_SLIDE} 筆",
        columns  = [
            {"key": "case_no",  "label": "案件編號",   "width": 1.40, "align": "center"},
            {"key": "occurred", "label": "報修日期",   "width": 1.05, "align": "center"},
            {"key": "floor",    "label": "發生樓層",   "width": 1.30, "align": "center"},
            {"key": "rtype",    "label": "工項類別",   "width": 1.35, "align": "center"},
            {"key": "title",    "label": "報修內容",    "width": 3.20, "align": "left"},
            {"key": "status",   "label": "狀態",        "width": 1.05, "align": "center"},
            {"key": "days",     "label": "等待天數",    "width": 1.00, "align": "center"},
            {"key": "unit",     "label": "工務處理人員","width": 1.80, "align": "left"},
        ],
        rows     = uf_rows,
        now_str  = now_str,
        SW=SW, SH=SH,
        max_rows = ROWS_PER_SLIDE,
    )

    # ── 刪除最後仍殘留的 content_template（index=1）─────────────────────────
    _delete_slide(prs, TMPL)

    buf = BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════
# Router endpoint
# ═══════════════════════════════════════════════════════

@router.post("/export", summary="觸發報修 PPTX 匯出（大直 / 盧群）")
def export_repair_pptx(
    body:         RepairPptBody = Body(...),
    db:           Session       = Depends(get_db),
    current_user: User          = Depends(get_current_user),
):
    if body.module not in ("dazhi", "luqun"):
        raise HTTPException(status_code=400, detail="module 必須為 dazhi 或 luqun")

    module_prefix = {"dazhi": "飯店工務報修", "luqun": "商場工務報修"}
    try:
        pptx_buf = _build_repair_pptx(body.module, body.year, body.month, db)
    except Exception as e:
        logger.error("repair pptx build error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"PPTX 生成失敗：{e}")

    filename = f"{module_prefix[body.module]}{body.month}月報告.pptx"
    encoded  = quote(filename)
    return StreamingResponse(
        pptx_buf,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
        },
    )


# ═══════════════════════════════════════════════════════
# 診斷端點 — 測試 matplotlib 圖表生成（管理員專用）
# ═══════════════════════════════════════════════════════

@router.get("/diag/chart", summary="測試 matplotlib 圖表生成（免登入診斷用）")
def diag_chart():
    """
    回傳 matplotlib 安裝狀態與測試圖表生成結果。
    若圖表生成失敗，回傳完整 error traceback 供除錯用。
    """
    import sys, traceback as _tb

    result: dict = {}

    # 1. 版本資訊
    try:
        import matplotlib
        result["matplotlib_version"] = matplotlib.__version__
        result["matplotlib_path"]    = matplotlib.__file__
    except Exception as e:
        result["matplotlib_import_error"] = str(e)
        return result

    # 2. 字型偵測
    try:
        font = _cjk_font()
        result["cjk_font"] = font or "（找不到 CJK 字型，將使用預設字型）"
    except Exception as e:
        result["cjk_font_error"] = str(e)

    # 3. Agg backend 測試
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        result["backend"] = matplotlib.get_backend()
    except Exception as e:
        result["backend_error"] = _tb.format_exc()
        return result

    # 4. 簡單圖表生成測試
    try:
        from io import BytesIO
        fig, ax = plt.subplots(figsize=(4, 2), dpi=72)
        ax.bar(["A", "B", "C"], [3, 7, 5])
        ax.set_title("測試圖表")
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=72, bbox_inches="tight")
        buf.seek(0)
        size = len(buf.read())
        plt.close(fig)
        result["simple_chart_ok"]     = True
        result["simple_chart_bytes"]  = size
    except Exception:
        result["simple_chart_ok"]     = False
        result["simple_chart_error"]  = _tb.format_exc()
        return result

    # 5. 柏拉圖測試（使用假資料）
    fake_rows = [
        {"type": "空調", "row_total": 40},
        {"type": "衛廁", "row_total": 25},
        {"type": "機電", "row_total": 15},
        {"type": "建築", "row_total": 10},
        {"type": "消防", "row_total": 5},
        {"type": "其他", "row_total": 5},
    ]
    try:
        buf = _make_pareto_chart(fake_rows)
        result["pareto_chart_ok"]    = buf is not None
        result["pareto_chart_bytes"] = len(buf.read()) if buf else 0
    except Exception:
        result["pareto_chart_ok"]    = False
        result["pareto_chart_error"] = _tb.format_exc()

    try:
        buf = _make_pie_chart(fake_rows)
        result["pie_chart_ok"]    = buf is not None
        result["pie_chart_bytes"] = len(buf.read()) if buf else 0
    except Exception:
        result["pie_chart_ok"]    = False
        result["pie_chart_error"] = _tb.format_exc()

    result["python_version"] = sys.version
    return result
