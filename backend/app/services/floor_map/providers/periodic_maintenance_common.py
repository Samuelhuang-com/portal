"""
樓層巡檢圖 Provider — 例行維護類模組共用基底（2026-11-04；2026-11-05 改為母項點位）

適用：商場例行維護（mall_periodic_maintenance）、全棟例行維護（mall_full_building_maintenance）
規格：docs/SPEC_floor_map_periodic_maintenance.md；共用標準 docs/DEV_SPEC_floor_plan_map.md

兩層結構（two_level，Samuel 2026-11-05 裁示）：
  - 點位＝母項（Ragic「項目母項名稱」）：每個母項在子項出現過的每一層各一點。
    母項名稱來源優先序：資料庫 parent_name（Ragic 同步值）→ pm_seed.PM_PARENTS 對照 → 子項名稱。
  - 點母項 → 右側列「該層」的子項（含已停用者，灰色）；點子項才顯示明細與本月每日狀況。
    子項樓層＝點位清單；清單沒有的子項＝其母項目前有點位的各層。該層沒有任何子項時改列全部子項。
  - 母項當日狀態＝該層「未停用」子項的合併狀態；該層子項全部停用 → all_disabled（點位只在編輯模式顯示）。
子項：
  - source_ref＝保養項目名稱（空白正規化）；同一批次內同名者依項次排序加「 #1」「 #2」
    （已知風險：Ragic 排序對調時兩個子項資料會跟著對調）。
  - 停用記在 floor_map_disabled_sources（畫面上切換）；停用子項不計入母項狀態。
判定（DEV_SPEC §5.2 四種狀態）：
  - 只看該月批次；同月份多張批次取 ragic_updated_at 最新者（與模組統計 _latest_batch_ids_per_month 一致）。
  - 排定日不在該月者不列入（以排定月份為主）；排定日在當月但執行月份不含當月者照樣列入（以排定日為準）。
  - 有「結束日期」者，排定日～結束日每一天都列入（2026-11-05；Ragic 欄位加上並同步後生效）。
  - 當天沒有涵蓋的項目＝no_record；任一項異常旗標＝abnormal；任一項未完成（開始＋結束時間未齊）＝unchecked；其餘＝normal。
未對應：所選月份批次中，模組內沒有任何點位紀錄（含已停用）的母項；子項全部停用的母項不列入。
不列入戰情 KPI（in_war_room = False）。
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date
from typing import Any, ClassVar

from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.floor_map import FloorMapDisabledSource, FloorMapPoint
from app.services.floor_map.common import hhmm, merge_group_status, minutes_between, normalize_date
from app.services.floor_map.pm_seed import (
    UNCATEGORIZED, child_category, child_floors, normalize_name, parent_of, static_groups, static_parents,
)
from app.services.floor_map.providers.base import FloorMapProvider

RESULT_OPTIONS = "□已完成□未完成"


def _ym(year: int, month: int) -> str:
    return f"{year}/{month:02d}"


def _parse_ymd(s: str) -> date | None:
    n = normalize_date(s or "")
    if not n:
        return None
    y, m, d = (int(x) for x in n.split("/"))
    try:
        return date(y, m, d)
    except ValueError:
        return None


class _Entry:
    """批次內一個子項：child／parent／item，以及涵蓋期間（排定日～結束日）"""
    __slots__ = ("child", "parent", "item", "start", "end")

    def __init__(self, child: str, parent: str, item: Any, start: date | None, end: date | None):
        self.child, self.parent, self.item, self.start, self.end = child, parent, item, start, end

    def covers(self, d: date) -> bool:
        return self.start is not None and self.start <= d <= (self.end or self.start)


class PeriodicMaintenanceFloorMapProvider(FloorMapProvider):
    """子類別需設定 batch_model／item_model，並實作 _item_url、_full_date。"""

    batch_model:    ClassVar[Any]
    item_model:     ClassVar[Any]
    attr_fields     = ["位置說明"]
    in_war_room     = False
    two_level       = True
    source_label    = "對應保養母項"
    empty_day_text  = "當日無排定保養項目"

    # ── 子類別實作 ───────────────────────────────────────────────────────────
    def _item_url(self, item: Any) -> str:
        raise NotImplementedError

    def _full_date(self, scheduled_date: str, period_month: str) -> date | None:
        raise NotImplementedError

    # ── 對照表 ───────────────────────────────────────────────────────────────
    def groups(self) -> list[dict[str, Any]]:
        return static_groups(self.module)

    # ── 資料讀取 ─────────────────────────────────────────────────────────────
    def _latest_batches(self, db: Session, period_month: str | None = None) -> list[Any]:
        """每個 period_month 只留 ragic_updated_at 最新的一張（依 period_month 由舊到新）"""
        B = self.batch_model
        q = db.query(B)
        if period_month:
            q = q.filter(B.period_month == period_month)
        latest: dict[str, Any] = {}
        for b in q.all():
            cur = latest.get(b.period_month)
            if cur is None or (b.ragic_updated_at or "") > (cur.ragic_updated_at or ""):
                latest[b.period_month] = b
        return [latest[k] for k in sorted(latest)]

    def _entries(self, db: Session, batch: Any) -> list[_Entry]:
        """批次內全部子項（依項次排序；同名加 #n）"""
        I = self.item_model
        items = db.query(I).filter(I.batch_ragic_id == batch.ragic_id).all()
        items.sort(key=lambda it: (it.seq_no or 0, it.ragic_id or ""))
        names = [normalize_name(it.task_name) for it in items]
        total: dict[str, int] = defaultdict(int)
        for n in names:
            total[n] += 1
        seen: dict[str, int] = defaultdict(int)
        out: list[_Entry] = []
        for n, it in zip(names, items):
            if not n:
                continue
            if total[n] > 1:
                seen[n] += 1
                child = f"{n} #{seen[n]}"
            else:
                child = n
            parent = normalize_name(getattr(it, "parent_name", None)) or parent_of(self.module, child) or child
            start = self._full_date(it.scheduled_date or "", batch.period_month or "")
            end = _parse_ymd(getattr(it, "schedule_end_date", None) or "")
            if start is not None and (end is None or end < start):
                end = start
            out.append(_Entry(child, parent, it, start, end))
        return out

    def _month(self, db: Session, year: int, month: int) -> tuple[list[_Entry], list[_Entry]]:
        """該月批次：(全部子項, 排定日落在該月的子項)"""
        batches = self._latest_batches(db, _ym(year, month))
        if not batches:
            return [], []
        allx = self._entries(db, batches[-1])
        inmonth = [x for x in allx if x.start is not None and x.start.year == year and x.start.month == month]
        return allx, inmonth

    def _disabled(self, db: Session) -> set[str]:
        return {r[0] for r in db.query(FloorMapDisabledSource.source_ref)
                .filter(FloorMapDisabledSource.module == self.module).all()}

    def _point_floors(self, db: Session) -> dict[str, set[str]]:
        out: dict[str, set[str]] = defaultdict(set)
        for ref, fk in (db.query(FloorMapPoint.source_ref, FloorMapPoint.floor_key)
                        .filter(FloorMapPoint.module == self.module, FloorMapPoint.is_active.is_(True)).all()):
            out[ref].add(fk)
        return out

    # ── 判定 ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _item_status(it: Any) -> str:
        if it.abnormal_flag:
            return "abnormal"
        return "normal" if (it.start_time and it.end_time) else "unchecked"

    @staticmethod
    def _span_label(x: _Entry) -> str:
        if x.start is None:
            return ""
        s = x.start.strftime("%m/%d")
        return f"{s}～{x.end.strftime('%m/%d')}" if x.end and x.end != x.start else s

    def _row(self, x: _Entry) -> dict[str, Any]:
        it = x.item
        st = self._item_status(it)
        done = bool(it.start_time and it.end_time)
        freq = (it.frequency or "").strip()
        span = self._span_label(x)
        extra = "｜".join(v for v in (freq, f"排定 {span}" if span else "") if v)
        return {
            "check_content":  normalize_name(it.task_name) + (f"（{extra}）" if extra else ""),
            "result_options": RESULT_OPTIONS,
            "kind":           "status",
            "status":         st,
            "results": [{
                "batch_ragic_id": it.ragic_id,
                "time_label":     hhmm(it.start_time or ""),
                "status":         st,
                "text":           "已完成" if done else "未完成",
                "readings":       [],
            }],
            "abnormal":       st == "abnormal",
            "abnormal_note":  (it.abnormal_note or "").strip(),
        }

    def _batch_entry(self, it: Any) -> dict[str, Any]:
        return {
            "ragic_id":       it.ragic_id,
            "ragic_url":      self._item_url(it),
            "inspector":      (it.executor_name or "").strip(),
            "start_hhmm":     hhmm(it.start_time or ""),
            "end_hhmm":       hhmm(it.end_time or ""),
            "actual_minutes": minutes_between(it.start_time or "", it.end_time or ""),
        }

    @staticmethod
    def _inspectors(its: list[Any]) -> list[str]:
        out: list[str] = []
        for it in its:
            for name in (it.executor_name or "").split():
                if name not in out:
                    out.append(name)
        return out

    def _children_of(self, allx: list[_Entry]) -> dict[str, list[str]]:
        """母項 → 子項（點位清單順序在前，批次中新出現的在後）"""
        out: dict[str, list[str]] = {}
        for g in static_parents(self.module):
            out[g["ref"]] = list(g["children"])
        for x in allx:
            kids = out.setdefault(x.parent, [])
            if x.child not in kids:
                kids.append(x.child)
        return out

    def _build(self, db: Session, d: date, floor_key: str | None) -> dict[str, dict[str, Any]]:
        allx, inmonth = self._month(db, d.year, d.month)
        by_child_all = {x.child: x for x in allx}
        covering: dict[str, list[_Entry]] = defaultdict(list)
        for x in inmonth:
            if x.covers(d):
                covering[x.child].append(x)
        disabled = self._disabled(db)
        cfloors = child_floors(self.module)
        ccat = child_category(self.module)
        pfloors = self._point_floors(db) if floor_key else {}
        gmap = self.group_map()
        out: dict[str, dict[str, Any]] = {}
        for parent, kids_all in self._children_of(allx).items():
            def on_floor(c: str) -> bool:
                fl = cfloors.get(c)
                return floor_key in (fl if fl else pfloors.get(parent, set()))
            kids = [c for c in kids_all if on_floor(c)] if floor_key else list(kids_all)
            if floor_key and not kids:
                kids = list(kids_all)
            children, parent_rows, parent_its = [], [], []
            for c in kids:
                xs = covering.get(c, [])
                rows = [self._row(x) for x in xs]
                its = [x.item for x in xs]
                ref_x = by_child_all.get(c)
                it0 = ref_x.item if ref_x else None
                is_disabled = c in disabled
                children.append({
                    "source_ref":     c,
                    "label":          c,
                    "system":         ((it0.category or "").strip() if it0 else "") or ccat.get(c) or UNCATEGORIZED,
                    "frequency":      ((it0.frequency or "").strip() if it0 else ""),
                    "schedule_label": self._span_label(ref_x) if ref_x else "",
                    "in_batch":       ref_x is not None,
                    "disabled":       is_disabled,
                    "status":         merge_group_status(rows, bool(rows)),
                    "rows":           rows,
                    "batches":        [self._batch_entry(it) for it in its],
                    "ragic_url":      self._item_url(it0) if it0 else "",
                    "inspectors":     self._inspectors(its),
                    "actual_minutes": sum(minutes_between(it.start_time or "", it.end_time or "") for it in its),
                })
                if not is_disabled:
                    parent_rows += rows
                    parent_its += its
            meta = gmap.get(parent) or {
                "source_ref": parent, "label": parent,
                "system": children[0]["system"] if children else UNCATEGORIZED, "shared_label": "",
            }
            out[parent] = {
                **meta,
                "status":         merge_group_status(parent_rows, bool(parent_rows)),
                "rows":           parent_rows,
                "batches":        [],     # 母項本身沒有 Ragic 記錄；連結在子項
                "inspectors":     self._inspectors(parent_its),
                "actual_minutes": sum(minutes_between(it.start_time or "", it.end_time or "") for it in parent_its),
                "children":       children,
                "all_disabled":   bool(kids) and all(c in disabled for c in kids),
            }
        return out

    def day_status(self, db: Session, insp_date: str) -> dict[str, dict[str, Any]]:
        d = _parse_ymd(insp_date)
        return self._build(db, d, None) if d else {}

    def day_status_floor(self, db: Session, insp_date: str, floor_key: str) -> dict[str, dict[str, Any]]:
        d = _parse_ymd(insp_date)
        return self._build(db, d, floor_key) if d else {}

    def month_status(self, db: Session, source_ref: str, year: int, month: int) -> list[dict[str, Any]]:
        """source_ref 是子項 → 該子項每日狀況；是母項 → 未停用子項合併（不分樓層）"""
        allx, inmonth = self._month(db, year, month)
        child_keys = {x.child for x in allx} | set(child_floors(self.module))
        if source_ref in child_keys:
            pick = [x for x in inmonth if x.child == source_ref]
        else:
            disabled = self._disabled(db)
            pick = [x for x in inmonth if x.parent == source_ref and x.child not in disabled]
        days = []
        for dd in range(1, calendar.monthrange(year, month)[1] + 1):
            day = date(year, month, dd)
            rows = [self._row(x) for x in pick if x.covers(day)]
            days.append({
                "day": dd, "date": day.strftime("%Y/%m/%d"),
                "status": merge_group_status(rows, bool(rows)),
                "abnormal_rows": sum(1 for r in rows if r["abnormal"]),
            })
        return days

    def data_end(self, db: Session) -> str | None:
        """最新批次月份的最後一天與今天取較早者（保養排程是預先排定的，今天之後的格子會是未填）"""
        batches = self._latest_batches(db)
        if not batches:
            return None
        try:
            y, m = (int(x) for x in batches[-1].period_month.split("/")[:2])
        except Exception:
            return None
        last = date(y, m, calendar.monthrange(y, m)[1])
        return min(last, twnow().date()).strftime("%Y/%m/%d")

    # ── 資料驅動的資料來源／未對應 ────────────────────────────────────────────
    def _all_entries(self, db: Session) -> list[_Entry]:
        out: list[_Entry] = []
        for b in self._latest_batches(db):             # 由舊到新
            out += self._entries(db, b)
        return out

    def dynamic_groups(self, db: Session) -> list[dict[str, Any]]:
        """所有月份最新批次中出現、點位清單沒有的母項（新增點位時可選）"""
        static = {g["source_ref"] for g in self.groups()}
        found: dict[str, str] = {}
        for x in self._all_entries(db):                 # 類別以最新月份為準
            found[x.parent] = (x.item.category or "").strip() or UNCATEGORIZED
        return [
            {"source_ref": ref, "label": ref, "system": cat, "shared_label": ""}
            for ref, cat in sorted(found.items()) if ref not in static
        ]

    def has_detail_source(self, source_ref: str, db: Session) -> bool:
        if source_ref in child_floors(self.module):
            return True
        return any(x.child == source_ref for x in self._all_entries(db))

    def unmapped(self, db: Session, insp_date: str, used_refs: set[str]) -> list[dict[str, Any]]:
        """所選月份批次中，模組內沒有任何點位紀錄（含已停用）的母項；子項全部停用的母項不列入"""
        d = _parse_ymd(insp_date)
        if d is None:
            return []
        allx, _ = self._month(db, d.year, d.month)
        disabled = self._disabled(db)
        kids: dict[str, list[_Entry]] = defaultdict(list)
        for x in allx:
            kids[x.parent].append(x)
        gmap = self.group_map()
        out = []
        for parent, xs in kids.items():
            if parent in used_refs or all(x.child in disabled for x in xs):
                continue
            g = gmap.get(parent) or {}
            out.append({
                "source_ref":   parent,
                "label":        parent,
                "system":       g.get("system") or (xs[0].item.category or "").strip() or UNCATEGORIZED,
                "shared_label": g.get("shared_label", ""),
            })
        return out
