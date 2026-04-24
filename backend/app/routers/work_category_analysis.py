"""
★工項類別分析 API Router  (v2 — 主管決策 Dashboard)
Prefix: /api/v1/work-category-analysis

資料來源（三合一）：
  luqun      → LuqunRepairCase      (work_hours = 花費工時 HR；fallback: 工務處理天數×24)
  dazhi      → DazhiRepairCase      (work_hours = 花費工時 HR；fallback: 工務處理天數/維修天數×24)
  hotel_room → RoomMaintenanceDetailRecord (work_hours 單位：分鐘，÷60 轉小時)

端點：
  GET /years          — 有資料的年份清單
  GET /persons        — 人員清單（依總工時降冪）
  GET /stats          — 主統計端點：KPI + 圖表 + 表格全套資料

五大工項類別：
  現場報修 | 上級交辦 | 緊急事件 | 例行維護 | 每日巡檢

  hotel_room 全部歸入「每日巡檢」
  luqun/dazhi 依 title+repair_type 關鍵字分類，預設「現場報修」

篩選參數（/stats）：
  year     : int           年度（必選）
  month    : int = 0       月份（0=全年）
  sources  : str = "all"   all / luqun / dazhi / hotel_room（逗號分隔多選）
  category : str = "all"   all / 現場報修 / 上級交辦 / 緊急事件 / 例行維護 / 每日巡檢
  person   : str = "all"   all / <人員姓名>
"""
from __future__ import annotations

import calendar
import re
from collections import defaultdict
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.luqun_repair import LuqunRepairCase
from app.models.dazhi_repair import DazhiRepairCase
from app.models.room_maintenance_detail import RoomMaintenanceDetailRecord

router = APIRouter()

# ══════════════════════════════════════════════════════════════════════════════
# 常數
# ══════════════════════════════════════════════════════════════════════════════

CATEGORIES = ["現場報修", "上級交辦", "緊急事件", "例行維護", "每日巡檢"]

SOURCE_LABELS = {
    "luqun":      "樂群工務",
    "dazhi":      "大直工務",
    "hotel_room": "房務保養",
}

# 關鍵字 → 工項類別（先匹配者優先；hotel_room 強制「每日巡檢」）
_CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("緊急事件",  ["緊急", "急修", "突發", "漏電緊急", "火警", "停電"]),
    ("每日巡檢",  ["巡檢", "巡視", "例巡", "日巡"]),
    ("例行維護",  ["例行", "定期", "保養", "維護", "定保", "年保", "季保", "月保"]),
    ("上級交辦",  ["交辦", "上級", "主管指示", "主管交辦", "院長", "指示", "指派"]),
]


def _classify(title: str, repair_type: str) -> str:
    text = (title or "") + (repair_type or "")
    for cat, keywords in _CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return cat
    return "現場報修"


def _parse_minutes_to_hours(val: str) -> float:
    """'22.00  分鐘' → 22.0 / 60 → 0.367 hours"""
    if not val:
        return 0.0
    m = re.search(r"[\d.]+", str(val))
    return float(m.group()) / 60.0 if m else 0.0


def _parse_hotel_date(date_str: str) -> tuple[int, int, int] | None:
    """'2026/04/15' or '2026-04-15' → (year, month, day)"""
    if not date_str:
        return None
    for fmt in ("%Y/%m/%d", "%Y-%m/%d", "%Y-%m-%d", "%Y/%m/%d %H:%M"):
        try:
            d = datetime.strptime(date_str.strip()[:10].replace("-", "/"), "%Y/%m/%d")
            return (d.year, d.month, d.day)
        except ValueError:
            pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 資料載入
# ══════════════════════════════════════════════════════════════════════════════

def _stat_dt_for(c) -> Optional[datetime]:
    """
    統計基準時間點（與 luqun/dazhi dashboard 保持一致的 stat-month 規則）：
    - 已完成（有 completed_at）→ completed_at（完工月）
    - 未完成（無 completed_at）→ occurred_at（報修月）
    """
    return c.completed_at if c.completed_at else c.occurred_at


def _load_all(db: Session, sources: set[str]) -> list[dict]:
    """
    合併指定來源資料，每筆回傳 dict：
    { year, month, day, work_hours, category, person, source }

    時間規則：year/month/day 以 stat-month 為準（completed_at 優先，未完成則用 occurred_at），
    與 luqun-repair/dashboard 及 dazhi-repair/dashboard 保持一致。
    """
    rows: list[dict] = []

    # ── 樂群 ──────────────────────────────────────────────────────────────────
    # 人員：responsible_unit（= Ragic「處理工務」）
    # 工時：work_hours（= 花費工時 HR；若無則 工務處理天數×24）
    if "luqun" in sources:
        for c in db.query(LuqunRepairCase).all():
            if not c.occurred_at or not c.work_hours or c.work_hours <= 0:
                continue
            dt = _stat_dt_for(c)
            if not dt:
                continue
            rows.append({
                "year":       dt.year,
                "month":      dt.month,
                "day":        dt.day,
                "work_hours": c.work_hours,
                "category":   _classify(c.title or "", c.repair_type or ""),
                "person":     (c.responsible_unit or "").strip() or "未指定",
                "source":     "luqun",
                "case_id":    c.ragic_id,
            })

    # ── 大直 ──────────────────────────────────────────────────────────────────
    # 人員：closer（= Ragic「維修人員」，執行修繕的人）
    #       ⚠️  不用 responsible_unit（= 反應單位，如「房務部」，是部門不是個人）
    # 工時：work_hours（= 維修天數×24 HR；若無則花費工時 HR）
    if "dazhi" in sources:
        for c in db.query(DazhiRepairCase).all():
            if not c.occurred_at or not c.work_hours or c.work_hours <= 0:
                continue
            dt = _stat_dt_for(c)
            if not dt:
                continue
            rows.append({
                "year":       dt.year,
                "month":      dt.month,
                "day":        dt.day,
                "work_hours": c.work_hours,
                "category":   _classify(c.title or "", c.repair_type or ""),
                "person":     (c.closer or "").strip() or "未指定",
                "source":     "dazhi",
                "case_id":    c.ragic_id,
            })

    # ── 房務保養 ──────────────────────────────────────────────────────────────
    if "hotel_room" in sources:
        for r in db.query(RoomMaintenanceDetailRecord).all():
            hours = _parse_minutes_to_hours(r.work_hours)
            if hours <= 0:
                continue
            yd = _parse_hotel_date(r.maintain_date)
            if not yd:
                continue
            rows.append({
                "year":       yd[0],
                "month":      yd[1],
                "day":        yd[2],
                "work_hours": hours,
                "category":   "每日巡檢",
                "person":     (r.staff_name or "").strip() or "未指定",
                "source":     "hotel_room",
                "case_id":    r.ragic_id,
            })

    return rows


def _parse_sources(sources_str: str) -> set[str]:
    if sources_str.strip().lower() == "all":
        return {"luqun", "dazhi", "hotel_room"}
    return {s.strip() for s in sources_str.split(",") if s.strip()}


def _filter_rows(
    rows: list[dict],
    year: int,
    month: int,
    category: str,
    person: str,
) -> list[dict]:
    result = [r for r in rows if r["year"] == year]
    if month > 0:
        result = [r for r in result if r["month"] == month]
    if category and category.lower() != "all":
        result = [r for r in result if r["category"] == category]
    if person and person.lower() != "all":
        result = [r for r in result if r["person"] == person]
    return result


# ══════════════════════════════════════════════════════════════════════════════
# KPI 計算
# ══════════════════════════════════════════════════════════════════════════════

def _build_kpi(rows: list[dict], prev_rows: list[dict]) -> dict:
    """主管摘要卡片資料。"""
    if not rows:
        return _empty_kpi()

    total_hours = sum(r["work_hours"] for r in rows)
    total_cases = len(set(r["case_id"] for r in rows))
    persons = {r["person"] for r in rows if r["person"] != "未指定"}
    avg_person_hours = round(total_hours / len(persons), 1) if persons else 0.0

    # 工時最高工項類別
    cat_hours: dict[str, float] = defaultdict(float)
    for r in rows:
        cat_hours[r["category"]] += r["work_hours"]
    top_cat = max(cat_hours, key=lambda c: cat_hours[c]) if cat_hours else "-"

    # 工時最高人員
    person_hours: dict[str, float] = defaultdict(float)
    for r in rows:
        if r["person"] != "未指定":
            person_hours[r["person"]] += r["work_hours"]
    top_person = max(person_hours, key=lambda p: person_hours[p]) if person_hours else "-"

    # 來源占比
    source_hours: dict[str, float] = defaultdict(float)
    for r in rows:
        source_hours[r["source"]] += r["work_hours"]
    source_breakdown = [
        {
            "source": s,
            "label":  SOURCE_LABELS.get(s, s),
            "hours":  round(source_hours.get(s, 0), 1),
            "pct":    round(source_hours.get(s, 0) / total_hours * 100, 1) if total_hours else 0,
        }
        for s in ["luqun", "dazhi", "hotel_room"]
        if source_hours.get(s, 0) > 0
    ]

    # 環比（上月）
    prev_total = sum(r["work_hours"] for r in prev_rows)
    mom_change_pct = None
    if prev_total > 0:
        mom_change_pct = round((total_hours - prev_total) / prev_total * 100, 1)

    return {
        "total_hours":       round(total_hours, 1),
        "total_cases":       total_cases,
        "total_persons":     len(persons),
        "avg_person_hours":  avg_person_hours,
        "top_category":      {
            "name":  top_cat,
            "hours": round(cat_hours.get(top_cat, 0), 1),
            "pct":   round(cat_hours.get(top_cat, 0) / total_hours * 100, 1) if total_hours else 0,
        },
        "top_person":        {
            "name":  top_person,
            "hours": round(person_hours.get(top_person, 0), 1),
            "pct":   round(person_hours.get(top_person, 0) / total_hours * 100, 1) if total_hours else 0,
        },
        "source_breakdown":  source_breakdown,
        "mom_change_pct":    mom_change_pct,
        "prev_month_hours":  round(prev_total, 1),
    }


def _empty_kpi() -> dict:
    return {
        "total_hours": 0, "total_cases": 0, "total_persons": 0,
        "avg_person_hours": 0,
        "top_category": {"name": "-", "hours": 0, "pct": 0},
        "top_person": {"name": "-", "hours": 0, "pct": 0},
        "source_breakdown": [],
        "mom_change_pct": None, "prev_month_hours": 0,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 圖表資料
# ══════════════════════════════════════════════════════════════════════════════

def _build_chart(rows: list[dict], year: int, month: int) -> list[dict]:
    """A. 類別趨勢折線圖（月份 or 日）。"""
    if month == 0:
        bucket: dict[int, dict[str, float]] = {m: {c: 0.0 for c in CATEGORIES} for m in range(1, 13)}
        for r in rows:
            bucket[r["month"]][r["category"]] += r["work_hours"]
        return [{"label": f"{m}月", **{c: round(bucket[m][c], 1) for c in CATEGORIES}} for m in range(1, 13)]
    else:
        _, days_in_month = calendar.monthrange(year, month)
        bucket2: dict[int, dict[str, float]] = {d: {c: 0.0 for c in CATEGORIES} for d in range(1, days_in_month + 1)}
        for r in [x for x in rows if x["month"] == month]:
            if 1 <= r["day"] <= days_in_month:
                bucket2[r["day"]][r["category"]] += r["work_hours"]
        return [{"label": f"{d}日", **{c: round(bucket2[d][c], 1) for c in CATEGORIES}} for d in range(1, days_in_month + 1)]


def _build_category_breakdown(rows: list[dict]) -> list[dict]:
    """B. 類別占比（圓餅圖）。"""
    total = sum(r["work_hours"] for r in rows)
    cat_hours: dict[str, float] = defaultdict(float)
    for r in rows:
        cat_hours[r["category"]] += r["work_hours"]
    return [
        {
            "name":  c,
            "value": round(cat_hours.get(c, 0), 1),
            "pct":   round(cat_hours.get(c, 0) / total * 100, 1) if total else 0,
        }
        for c in CATEGORIES
    ]


def _build_person_ranking(rows: list[dict], top_n: int = 20) -> list[dict]:
    """C. 人員工時排名。"""
    total = sum(r["work_hours"] for r in rows)
    person_hours: dict[str, float] = defaultdict(float)
    person_source: dict[str, set[str]] = defaultdict(set)
    person_cat: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        p = r["person"]
        if p == "未指定":
            continue
        person_hours[p] += r["work_hours"]
        person_source[p].add(r["source"])
        person_cat[p][r["category"]] += r["work_hours"]

    sorted_persons = sorted(person_hours, key=lambda p: -person_hours[p])[:top_n]
    result = []
    for i, p in enumerate(sorted_persons, 1):
        ph = person_hours[p]
        top_cat = max(person_cat[p], key=lambda c: person_cat[p][c]) if person_cat[p] else "-"
        result.append({
            "rank":         i,
            "person":       p,
            "hours":        round(ph, 1),
            "pct":          round(ph / total * 100, 1) if total else 0,
            "sources":      list(person_source[p]),
            "source_labels": [SOURCE_LABELS.get(s, s) for s in person_source[p]],
            "top_category": top_cat,
        })
    return result


def _build_category_person_matrix(rows: list[dict], top_n: int = 12) -> list[dict]:
    """D. 類別×人員交叉（Stacked Bar 用）。前 top_n 人員。"""
    person_hours: dict[str, float] = defaultdict(float)
    for r in rows:
        if r["person"] != "未指定":
            person_hours[r["person"]] += r["work_hours"]
    top_persons = sorted(person_hours, key=lambda p: -person_hours[p])[:top_n]

    matrix: dict[str, dict[str, float]] = {p: {c: 0.0 for c in CATEGORIES} for p in top_persons}
    for r in rows:
        if r["person"] in matrix:
            matrix[r["person"]][r["category"]] += r["work_hours"]

    return [
        {"person": p, **{c: round(matrix[p][c], 1) for c in CATEGORIES}}
        for p in top_persons
    ]


def _build_source_breakdown(rows: list[dict]) -> list[dict]:
    """E. 來源別分析。"""
    total = sum(r["work_hours"] for r in rows)
    data: dict[str, dict] = {
        s: {"hours": 0.0, "cases": set(), "persons": set(), "cat": defaultdict(float)}
        for s in ["luqun", "dazhi", "hotel_room"]
    }
    for r in rows:
        s = r["source"]
        data[s]["hours"] += r["work_hours"]
        data[s]["cases"].add(r["case_id"])
        if r["person"] != "未指定":
            data[s]["persons"].add(r["person"])
        data[s]["cat"][r["category"]] += r["work_hours"]

    result = []
    for s in ["luqun", "dazhi", "hotel_room"]:
        h = data[s]["hours"]
        if h <= 0:
            continue
        top_cat = max(data[s]["cat"], key=lambda c: data[s]["cat"][c]) if data[s]["cat"] else "-"
        result.append({
            "source":       s,
            "label":        SOURCE_LABELS.get(s, s),
            "hours":        round(h, 1),
            "pct":          round(h / total * 100, 1) if total else 0,
            "cases":        len(data[s]["cases"]),
            "persons":      len(data[s]["persons"]),
            "top_category": top_cat,
        })
    return result


def _build_concentration(rows: list[dict]) -> dict:
    """F. 人力負載集中度分析。"""
    total = sum(r["work_hours"] for r in rows)
    person_hours: dict[str, float] = defaultdict(float)
    for r in rows:
        if r["person"] != "未指定":
            person_hours[r["person"]] += r["work_hours"]

    sorted_ph = sorted(person_hours.values(), reverse=True)
    top3 = sum(sorted_ph[:3])
    top5 = sum(sorted_ph[:5])
    top10 = sum(sorted_ph[:10])
    return {
        "total_persons": len(person_hours),
        "top3_pct":  round(top3  / total * 100, 1) if total else 0,
        "top5_pct":  round(top5  / total * 100, 1) if total else 0,
        "top10_pct": round(top10 / total * 100, 1) if total else 0,
        "is_concentrated": (top3 / total * 100 if total else 0) > 70,
    }


def _build_daily(rows: list[dict], year: int, month: int) -> dict:
    """每日累計工時表（B 區）。"""
    if month == 0:
        return {"days": [], "weekdays": [], "rows": []}
    _, days_in_month = calendar.monthrange(year, month)
    days = list(range(1, days_in_month + 1))
    zh = ["一", "二", "三", "四", "五", "六", "日"]
    weekdays = [zh[date(year, month, d).weekday()] for d in days]

    bucket: dict[str, dict[int, float]] = {c: defaultdict(float) for c in CATEGORIES}
    for r in [x for x in rows if x["month"] == month]:
        bucket[r["category"]][r["day"]] += r["work_hours"]

    result_rows = []
    grand_total = 0.0
    grand_day = [0.0] * len(days)
    for cat in CATEGORIES:
        day_h = [round(bucket[cat][d], 1) for d in days]
        total = round(sum(day_h), 1)
        grand_total += total
        for i, h in enumerate(day_h):
            grand_day[i] += h
        result_rows.append({"category": cat, "hours": day_h, "total": total, "pct": 0.0})
    for row in result_rows:
        row["pct"] = round(row["total"] / grand_total * 100, 1) if grand_total else 0.0
    result_rows.append({
        "category": "TOTAL",
        "hours": [round(h, 1) for h in grand_day],
        "total": round(grand_total, 1),
        "pct": 100.0,
    })
    return {"days": days, "weekdays": weekdays, "rows": result_rows}


def _build_monthly(rows: list[dict]) -> dict:
    """每月累計工時表（C 區）。"""
    bucket: dict[str, dict[int, float]] = {c: defaultdict(float) for c in CATEGORIES}
    for r in rows:
        bucket[r["category"]][r["month"]] += r["work_hours"]

    result_rows = []
    grand_total = 0.0
    grand_m = [0.0] * 12
    for cat in CATEGORIES:
        mh = [round(bucket[cat][m], 1) for m in range(1, 13)]
        total = round(sum(mh), 1)
        grand_total += total
        for i, h in enumerate(mh):
            grand_m[i] += h
        result_rows.append({"category": cat, "hours": mh, "total": total, "pct": 0.0})
    for row in result_rows:
        row["pct"] = round(row["total"] / grand_total * 100, 1) if grand_total else 0.0
    result_rows.append({
        "category": "TOTAL",
        "hours": [round(h, 1) for h in grand_m],
        "total": round(grand_total, 1),
        "pct": 100.0,
    })
    return {"months": list(range(1, 13)), "rows": result_rows}


def _build_person_table(rows: list[dict]) -> dict:
    """每月累計工時（人員）表（D 區）。"""
    person_hours: dict[str, float] = defaultdict(float)
    for r in rows:
        if r["person"] != "未指定":
            person_hours[r["person"]] += r["work_hours"]
    persons = sorted(person_hours, key=lambda p: -person_hours[p])[:15]
    if not persons:
        return {"persons": [], "rows": []}

    bucket: dict[str, dict[str, float]] = {c: defaultdict(float) for c in CATEGORIES}
    for r in rows:
        if r["person"] in persons:
            bucket[r["category"]][r["person"]] += r["work_hours"]

    result_rows = []
    for cat in CATEGORIES:
        cat_total = sum(bucket[cat][p] for p in persons)
        result_rows.append({
            "category": cat,
            "pct_by_person": [
                round(bucket[cat][p] / cat_total * 100, 1) if cat_total else 0.0
                for p in persons
            ],
        })
    return {"persons": persons, "rows": result_rows}


# ══════════════════════════════════════════════════════════════════════════════
# 端點
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/years", summary="有資料的年份清單")
def get_years(db: Session = Depends(get_db)):
    rows = _load_all(db, {"luqun", "dazhi", "hotel_room"})
    years = sorted({r["year"] for r in rows}, reverse=True)
    return {"years": years or [datetime.now().year]}


@router.get("/persons", summary="人員清單（依總工時降冪）")
def get_persons(
    year:    Optional[int] = Query(None),
    sources: str           = Query("all"),
    db: Session = Depends(get_db),
):
    src = _parse_sources(sources)
    rows = _load_all(db, src)
    if year:
        rows = [r for r in rows if r["year"] == year]
    ph: dict[str, float] = defaultdict(float)
    for r in rows:
        if r["person"] != "未指定":
            ph[r["person"]] += r["work_hours"]
    persons = sorted(ph, key=lambda p: -ph[p])[:20]
    return {"persons": persons}


@router.get("/stats", summary="工項類別分析主統計（主管 Dashboard）")
def get_stats(
    year:     int = Query(..., description="年度"),
    month:    int = Query(0,     description="月份（0=全年）"),
    sources:  str = Query("all", description="all / luqun / dazhi / hotel_room"),
    category: str = Query("all", description="all / 現場報修 / ..."),
    person:   str = Query("all", description="all / <人員姓名>"),
    db: Session = Depends(get_db),
):
    src = _parse_sources(sources)
    all_src_rows = _load_all(db, src)

    # 當期資料（年 + 可選月）
    year_rows   = _filter_rows(all_src_rows, year, month, "all", "all")
    # 篩選後資料（category + person filter）
    filtered    = _filter_rows(all_src_rows, year, month, category, person)

    # 上月資料（用於環比，不套 category/person filter）
    if month > 0:
        prev_m = month - 1 if month > 1 else 12
        prev_y = year      if month > 1 else year - 1
        prev_rows = _filter_rows(all_src_rows, prev_y, prev_m, "all", "all")
    else:
        # 全年模式：與去年同期比較
        prev_rows = _filter_rows(all_src_rows, year - 1, 0, "all", "all")

    return {
        # ── 第一層：主管 KPI 卡片 ──────────────────────────────────────────
        "kpi":                    _build_kpi(year_rows, prev_rows),

        # ── 第二層：圖表分析 ────────────────────────────────────────────────
        "chart_data":             _build_chart(year_rows, year, month),
        "category_breakdown":     _build_category_breakdown(year_rows),
        "person_ranking":         _build_person_ranking(year_rows, top_n=20),
        "category_person_matrix": _build_category_person_matrix(year_rows, top_n=12),
        "source_breakdown":       _build_source_breakdown(year_rows),
        "concentration":          _build_concentration(year_rows),

        # ── 第三層：表格（支援 category/person filter）─────────────────────
        "daily_hours":  _build_daily(filtered, year, month),
        "monthly_hours": _build_monthly(filtered),
        "person_hours": _build_person_table(filtered),

        # ── Meta ────────────────────────────────────────────────────────────
        "meta": {
            "year":     year,
            "month":    month,
            "sources":  list(src),
            "category": category,
            "person":   person,
            "total_rows": len(year_rows),
        },
    }
