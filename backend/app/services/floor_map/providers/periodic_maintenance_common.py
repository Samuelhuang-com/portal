"""
樓層巡檢圖 Provider — 例行維護類模組共用基底（2026-11-04）

適用：商場例行維護（mall_periodic_maintenance）、全棟例行維護（mall_full_building_maintenance）
規格：docs/SPEC_floor_map_periodic_maintenance.md；共用標準 docs/DEV_SPEC_floor_plan_map.md

與巡檢模組不同的地方：
  - 資料來源是「每月批次的保養項目」，不是巡檢欄位。source_ref＝保養項目名稱（空白正規化）；
    同一批次內同名者依項次排序加「 #1」「 #2」（Samuel 2026-11-04 裁示：同名全部拆開，
    已知風險：Ragic 排序對調時兩點資料會跟著對調）。
  - 對照表（點位清單）寫在 services/floor_map/pm_seed.py；批次中出現、清單沒有的項目
    由 dynamic_groups() 補進可選清單，並由 unmapped() 列為「未對應」，讓使用者在畫面上直接新增點位。
    有點位紀錄（含已停用）的項目不算未對應：停用＝刻意不放在圖上（2026-11-04 裁示）。
  - 「當天」以排定日（scheduled_date）為準；只看該月批次，排定日不在該月者不列入（以排定月份為主）；
    排定日在當月但執行月份不含當月者照樣列入（以排定日為準）。
  - 同月份多張批次取 ragic_updated_at 最新者（與模組現有統計 _latest_batch_ids_per_month 一致）。
  - 狀態（四種，DEV_SPEC §5.2）：當天沒有排定項目＝no_record；任一項異常旗標＝abnormal；
    任一項未完成（開始＋結束時間未齊）＝unchecked；其餘＝normal。
  - 不列入戰情 KPI（in_war_room = False），戰情 KPI 的巡檢截止時間語意不適用保養排程。
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date
from typing import Any, ClassVar

from sqlalchemy.orm import Session

from app.core.time import twnow
from app.services.floor_map.common import hhmm, merge_group_status, minutes_between
from app.services.floor_map.pm_seed import UNCATEGORIZED, normalize_name, static_groups
from app.services.floor_map.providers.base import FloorMapProvider

RESULT_OPTIONS = "□已完成□未完成"


def _ym(year: int, month: int) -> str:
    return f"{year}/{month:02d}"


def _parse_ymd(insp_date: str) -> date | None:
    try:
        y, m, d = (int(x) for x in insp_date.split("/"))
        return date(y, m, d)
    except Exception:
        return None


class PeriodicMaintenanceFloorMapProvider(FloorMapProvider):
    """子類別需設定 batch_model／item_model，並實作 _item_url、_full_date。"""

    batch_model:    ClassVar[Any]
    item_model:     ClassVar[Any]
    attr_fields     = ["位置說明"]
    in_war_room     = False
    source_label    = "對應保養項目"
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

    def _keyed_items(self, db: Session, batch: Any) -> list[tuple[str, Any]]:
        """批次內項目依項次排序，產生 (source_ref, item)；同名者加 #1、#2"""
        I = self.item_model
        items = db.query(I).filter(I.batch_ragic_id == batch.ragic_id).all()
        items.sort(key=lambda it: (it.seq_no or 0, it.ragic_id or ""))
        names = [normalize_name(it.task_name) for it in items]
        total: dict[str, int] = defaultdict(int)
        for n in names:
            total[n] += 1
        seen: dict[str, int] = defaultdict(int)
        out: list[tuple[str, Any]] = []
        for n, it in zip(names, items):
            if not n:
                continue
            if total[n] > 1:
                seen[n] += 1
                out.append((f"{n} #{seen[n]}", it))
            else:
                out.append((n, it))
        return out

    def _month_schedule(self, db: Session, year: int, month: int) -> dict[int, list[tuple[str, Any]]]:
        """該月批次中、排定日落在該月的項目，依日分組：{day: [(source_ref, item)]}"""
        batches = self._latest_batches(db, _ym(year, month))
        out: dict[int, list[tuple[str, Any]]] = defaultdict(list)
        if not batches:
            return out
        batch = batches[-1]
        for ref, it in self._keyed_items(db, batch):
            fd = self._full_date(it.scheduled_date or "", batch.period_month or "")
            if fd is None or fd.year != year or fd.month != month:
                continue
            out[fd.day].append((ref, it))
        return out

    # ── 判定 ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _item_status(it: Any) -> str:
        if it.abnormal_flag:
            return "abnormal"
        return "normal" if (it.start_time and it.end_time) else "unchecked"

    def _row(self, it: Any, fd_label: str) -> dict[str, Any]:
        st = self._item_status(it)
        done = bool(it.start_time and it.end_time)
        freq = (it.frequency or "").strip()
        content = normalize_name(it.task_name)
        content += f"（{freq}｜排定 {fd_label}）" if freq else f"（排定 {fd_label}）"
        return {
            "check_content":  content,
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

    def day_status(self, db: Session, insp_date: str) -> dict[str, dict[str, Any]]:
        d = _parse_ymd(insp_date)
        gmap = self.group_map()
        if d is None:
            return {}
        by_ref: dict[str, list[Any]] = defaultdict(list)
        for ref, it in self._month_schedule(db, d.year, d.month).get(d.day, []):
            by_ref[ref].append(it)
        out: dict[str, dict[str, Any]] = {}
        for ref in set(gmap) | set(by_ref):
            meta = gmap.get(ref) or {"source_ref": ref, "label": ref, "system": UNCATEGORIZED, "shared_label": ""}
            its = by_ref.get(ref, [])
            rows = [self._row(it, d.strftime("%m/%d")) for it in its]
            inspectors: list[str] = []
            for it in its:
                for name in (it.executor_name or "").split():
                    if name not in inspectors:
                        inspectors.append(name)
            out[ref] = {
                **meta,
                "status":         merge_group_status(rows, bool(rows)),
                "rows":           rows,
                "batches":        [self._batch_entry(it) for it in its],
                "inspectors":     inspectors,
                "actual_minutes": sum(minutes_between(it.start_time or "", it.end_time or "") for it in its),
            }
        return out

    def month_status(self, db: Session, source_ref: str, year: int, month: int) -> list[dict[str, Any]]:
        sched = self._month_schedule(db, year, month)
        days = []
        for dd in range(1, calendar.monthrange(year, month)[1] + 1):
            its = [it for ref, it in sched.get(dd, []) if ref == source_ref]
            rows = [self._row(it, f"{month:02d}/{dd:02d}") for it in its]
            days.append({
                "day": dd, "date": f"{year}/{month:02d}/{dd:02d}",
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
        end = min(last, twnow().date())
        return end.strftime("%Y/%m/%d")

    # ── 未對應／資料驅動的資料來源 ─────────────────────────────────────────────
    def dynamic_groups(self, db: Session) -> list[dict[str, Any]]:
        """所有月份最新批次中出現、點位清單沒有的項目（新增點位時可選）"""
        static = {g["source_ref"] for g in self.groups()}
        found: dict[str, str] = {}
        for b in self._latest_batches(db):            # 由舊到新，類別以最新月份為準
            for ref, it in self._keyed_items(db, b):
                found[ref] = (it.category or "").strip() or UNCATEGORIZED
        return [
            {"source_ref": ref, "label": ref, "system": cat, "shared_label": ""}
            for ref, cat in sorted(found.items()) if ref not in static
        ]

    def unmapped(self, db: Session, insp_date: str, used_refs: set[str]) -> list[dict[str, Any]]:
        """所選日期所在月份的批次中，模組內沒有任何點位紀錄（含已停用）的項目（Samuel 2026-11-04：只看所選月份）"""
        d = _parse_ymd(insp_date)
        if d is None:
            return []
        batches = self._latest_batches(db, _ym(d.year, d.month))
        if not batches:
            return []
        gmap = self.group_map()
        out, seen = [], set()
        for ref, it in self._keyed_items(db, batches[-1]):
            if ref in used_refs or ref in seen:
                continue
            seen.add(ref)
            g = gmap.get(ref) or {}
            out.append({
                "source_ref":   ref,
                "label":        ref,
                "system":       g.get("system") or (it.category or "").strip() or UNCATEGORIZED,
                "shared_label": g.get("shared_label", ""),
            })
        return out
