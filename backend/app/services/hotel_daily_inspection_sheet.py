"""
飯店每日巡檢表（Excel 版型）建表服務（2026-11-10，比照 mall_daily_inspection_sheet.py）

來源版型：myDoc/巡檢表_1110/(飯店)每日設備巡檢表_1029(飯店定案版).xlsx
用途：/hotel/daily-inspection Dashboard 月曆格點「某頁籤 × 某日」的下一層 Drawer、
      樓層巡檢圖 Provider、樓層 TAB 場次清單的異常判定 —— 三處同一套規則。

與商場相同的原則：Excel 檢查內容與 Ragic 欄位**明確對應**（FIELD_MAP），對不上的不猜。

Ragic 實際欄位（2026-11-10 以瀏覽器讀新表列表欄位；7 張表當時皆 0 筆）：
  17 RF        : 巡檢人員、開始巡檢時間、巡檢結束時間、工時計算、水位檢查、水泵運作狀態、水位狀態、
                 水質觀察、膨脹水箱水位、3-6F客房熱水回水泵  A泵、3-6F客房熱水回水泵  B泵、
                 11-12F客房熱水回水泵  A泵、11-12F客房熱水回水泵  B泵、鍋爐電源 #1、鍋爐電源#2、
                 熱水儲存桶溫度、熱水儲存桶加熱泵浦開關、變頻加壓泵浦壓力值、外觀與結構、是否有洩漏狀況
                 （欄名中間可能是兩個空白 —— 一律以「去空白後」比對）
  28 5-10F     : 5樓～10樓客房走道空調箱
  29 4F        : 空調箱啟動、BAR-D 飲水機、製冰機、燈光視覺檢查
  30 B1F 高壓  : 11 項（同 Excel）
  31 B1F 晚班  : 燈光視覺檢查、空調送風機、外觀與結構、電壓是否正常、是否有洩漏狀況
  32 B4F 下水塔: 7 項（同 Excel；此表沒有「工時計算」）
  33 B4F 空調  : 13 項，另有填數字欄「進水溫度」「出水溫度」「進出溫差」「壓力值」

舊表（封存來源、rf_legacy）欄位與新表完全不同：
  - 每日巡檢表只顯示新項目（2026-11-10 裁示），版型列只看現行來源的場次。
  - 舊表場次的異常不會消失：以「明確異常字樣」判定後列為版型外異常（標「舊表」）。
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from app.services.hotel_daily_inspection_sources import (
    TAB_LABELS, TABS, is_live_batch, live_source, record_url, sheet_url,
)
from app.services.hotel_daily_inspection_template import HOTEL_DAILY_INSPECTION_TEMPLATE

SHEET_ORDER: list[str] = list(TABS)

# 樓層區塊顯示名稱（Drawer 頁首、月曆格列名）
EXCEL_FLOOR_LABEL: dict[str, str] = {
    "rf":         "RF",
    "5f-10f":     "5-10F",
    "4f":         "4F",
    "b1f-hv":     "B1F 高壓機房",
    "b1f-office": "B1F 辦公室公區、廚房瓦斯",
    "b4f-water":  "B4F 下水塔",
    "b4f-ac":     "B4F 空調機房",
}

# ── 檢查內容 → Ragic 欄位（明確對應；未列者預設「同名欄位」）────────────────────
#   kind = status   ：選項欄（可多欄，取最嚴重者；例：A泵／B泵）
#   kind = reading  ：填數字欄，不判正常異常
#   readings        ：status 列另附的填數字欄（顯示用，不判異常）
FIELD_MAP: dict[tuple[str, str], dict[str, Any]] = {
    ("rf", "3-6F客房熱水回水泵"): {
        "kind": "status",
        "fields": [("3-6F客房熱水回水泵 A泵", "A泵"), ("3-6F客房熱水回水泵 B泵", "B泵")],
    },
    ("rf", "11-12F客房熱水回水泵"): {
        "kind": "status",
        "fields": [("11-12F客房熱水回水泵 A泵", "A泵"), ("11-12F客房熱水回水泵 B泵", "B泵")],
    },
    ("rf", "鍋爐電源"): {
        "kind": "status",
        "fields": [("鍋爐電源 #1", "#1"), ("鍋爐電源#2", "#2")],
    },
    ("b4f-ac", "冰水進水溫度"): {"kind": "status", "fields": [("冰水進水溫度", "")], "readings": [("進水溫度", "度數")]},
    ("b4f-ac", "冰水出水溫度"): {"kind": "status", "fields": [("冰水出水溫度", "")], "readings": [("出水溫度", "度數")]},
    ("b4f-ac", "冰水進出溫差"): {"kind": "status", "fields": [("冰水進出溫差", "")], "readings": [("進出溫差", "度數")]},
    ("b4f-ac", "流量 / 壓力值"): {"kind": "status", "fields": [("流量 / 壓力值", "")], "readings": [("壓力值", "Kg2")]},
}

# 飯店新表沒有「異常說明」欄（2026-11-10 Ragic 欄位確認）；有了再加
NOTE_FIELD: dict[tuple[str, str], str] = {}
REMARK: dict[tuple[str, str], str] = {}
SHIFT_TIMES: list[dict[str, str]] = []   # 早班／晚班不寫進 Portal（2026-11-10 裁示）

# 選項欄的「非異常」選項：開／關、低／中／高 是記錄狀態，不是異常（2026-11-10）
NORMAL_WORDS  = {"正常", "乾淨", "OK", "ok", "O", "V", "v", "✓", "良好",
                 "開", "關", "開啟", "關閉", "低", "中", "高", "A泵", "B泵"}
PENDING_WORDS = {"待處理", "待修", "待修繕"}

_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")
_DATE_RE = re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})")
_WS_RE   = re.compile(r"\s+")


# ── 輔助 ──────────────────────────────────────────────────────────────────────

def norm_name(name: str) -> str:
    """欄位名比對用：去掉所有空白（Ragic 欄名常有兩個空白）。"""
    return _WS_RE.sub("", name or "")


def normalize_date(raw: str) -> str:
    m = _DATE_RE.search(raw or "")
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"{y}/{int(mo):02d}/{int(d):02d}"


def _hhmm(raw: str) -> str:
    found = _TIME_RE.findall(raw or "")
    if not found:
        return ""
    h, m = found[-1]
    return f"{int(h):02d}:{m}"


def _minutes_between(start: str, end: str) -> int:
    s, e = _hhmm(start), _hhmm(end)
    if not s or not e:
        return 0
    diff = (int(e[:2]) * 60 + int(e[3:])) - (int(s[:2]) * 60 + int(s[3:]))
    return diff + 24 * 60 if diff < 0 else diff


def judge_status(raw: str) -> str:
    """選項欄 → normal / abnormal / pending / unchecked。"""
    raw = (raw or "").strip()
    if not raw:
        return "unchecked"
    tokens = [t for t in re.split(r"[\s,、]+", raw) if t]
    if all(t in NORMAL_WORDS for t in tokens):
        return "normal"
    if any(t in PENDING_WORDS for t in tokens):
        return "pending"
    return "abnormal"


def ragic_record_url(sheet_key: str, batch_ragic_id: str) -> str:
    return record_url(batch_ragic_id)


def _spec(key: str, content: str) -> dict[str, Any]:
    return FIELD_MAP.get((key, content), {"kind": "status", "fields": [(content, "")]})


# ── 版型外欄位 ────────────────────────────────────────────────────────────────
_NUMERIC_RE = re.compile(r"^[-+]?\d+(?:\.\d+)?\s*(?:°C|℃|°|%|度|kwh|kWh|KWH|kg|Kg|KG|Kg2|kg/cm2)?$")
_EXPLICIT_ISSUE_RE = re.compile(r"異常|待處理|待修|故障|損壞|不良|破損|洩漏|漏水|^[Xx]$")


def _referenced_fields() -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {k: set() for k in SHEET_ORDER}
    for t in HOTEL_DAILY_INSPECTION_TEMPLATE:
        sp = _spec(t["source_tab"], t["check_content"])
        refs.setdefault(t["source_tab"], set()).update(norm_name(f) for f, _ in sp["fields"])
        refs[t["source_tab"]].update(norm_name(f) for f, _ in sp.get("readings", []))
    return refs


_REFERENCED = _referenced_fields()

_READING_FIELDS: dict[str, set[str]] = {}
for (_k, _c), _sp in FIELD_MAP.items():
    if _sp["kind"] == "reading":
        _READING_FIELDS.setdefault(_k, set()).update(norm_name(f) for f, _ in _sp["fields"])
    _READING_FIELDS.setdefault(_k, set()).update(norm_name(f) for f, _ in _sp.get("readings", []))


def _is_text_field(name: str) -> bool:
    return any(w in name for w in ("說明", "備註", "照片", "拍照"))


def item_status(sheet_key: str, item_name: str, raw: str, is_note: bool = False) -> str:
    """
    單一欄位狀態（同步、樓層 TAB 場次清單、明細 Drawer、月曆格共用）：
      版型內選項欄 → judge_status；填數字欄 → measure；
      版型外欄位（含舊表）→ 正常字樣 normal、明確異常字樣 abnormal/pending，其餘 measure；
      說明／備註／建立日期這類附註欄 → note。
    """
    from app.services.inspection_field_rules import is_meta_field

    name = (item_name or "").strip()
    raw  = (raw or "").strip()
    if is_note or is_meta_field(name) or _is_text_field(name) or "預估時間" in name:
        return "note"
    if not raw:
        return "unchecked"
    nn = norm_name(name)
    if nn in _READING_FIELDS.get(sheet_key, set()) or _NUMERIC_RE.match(raw):
        return "measure"
    st = judge_status(raw)
    if nn in _REFERENCED.get(sheet_key, set()) or st == "normal":
        return st
    return st if _EXPLICIT_ISSUE_RE.search(raw) else "measure"


def item_kpi(sheet_key: str, items: Iterable[Any]) -> dict[str, Any]:
    """場次 KPI（排除附註欄）。"""
    sts = [item_status(sheet_key, it.item_name, it.result_raw, bool(getattr(it, "is_note", False))) for it in items]
    sts = [x for x in sts if x != "note"]
    c = {k: sum(1 for x in sts if x == k) for k in ("normal", "abnormal", "pending", "unchecked", "measure")}
    total = len(sts)
    checked = total - c["unchecked"]
    return {"total": total, "checked": checked, **c,
            "completion_rate": round(checked / total * 100, 1) if total else 0.0}


def day_issues(sheet: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """build_daily_sheet 結果 → {sheet_key: [異常／待處理項目]}（月曆格 ⚠ 與 Drawer 同一份判定）。"""
    out: dict[str, list[dict[str, Any]]] = {k: [] for k in SHEET_ORDER}
    for r in sheet["rows"]:
        if r["abnormal"]:
            out.setdefault(r["source_tab"], []).append({
                "source_tab": r["source_tab"], "floor": r["floor"], "item": r["item"],
                "check_content": r["check_content"], "status": r["status"],
                "note": r["abnormal_note"], "in_template": True,
            })
    for x in sheet.get("extra_issues", []):
        out.setdefault(x["source_tab"], []).append({
            "source_tab": x["source_tab"], "floor": x["floor"],
            "item": "舊表" if x.get("legacy") else "版型外欄位",
            "check_content": x["field"], "status": x["status"],
            "note": (f"[{x['time_label']}] " if x["time_label"] else "") + x["text"],
            "in_template": False,
        })
    return out


# ── 主函式（純資料，不碰 DB）────────────────────────────────────────────────────

def build_daily_sheet(batches: Iterable[Any], items_by_batch: dict[str, list[Any]]) -> dict[str, Any]:
    """
    batches        ：當日 HotelDIBatch（任意頁籤、可多筆、可含舊表場次）
    items_by_batch ：{batch_ragic_id: [HotelDIItem, ...]}
    回傳 {floors, rows, summary, extra_issues}
    """
    all_batches = [b for b in batches if b.sheet_key in SHEET_ORDER]
    live    = [b for b in all_batches if is_live_batch(b.ragic_id)]
    legacy  = [b for b in all_batches if not is_live_batch(b.ragic_id)]

    by_sheet: dict[str, list[Any]] = {k: [] for k in SHEET_ORDER}
    for b in live:
        by_sheet[b.sheet_key].append(b)
    for k in by_sheet:
        by_sheet[k].sort(key=lambda b: (_hhmm(b.start_time or "") or "99:99", b.ragic_id))

    # {batch: {去空白欄名: 原始值}}
    values: dict[str, dict[str, str]] = {
        bid: {norm_name(it.item_name): (it.result_raw or "").strip() for it in its}
        for bid, its in items_by_batch.items()
    }

    floors: list[dict[str, Any]] = []
    for key in SHEET_ORDER:
        bl = by_sheet[key]
        inspectors: list[str] = []
        batch_out = []
        total_min = 0
        est_min = 0
        for b in bl:
            name = (b.inspector_name or "").strip()
            if name and name not in inspectors:
                inspectors.append(name)
            mins = _minutes_between(b.start_time or "", b.end_time or "")
            total_min += mins
            est_min += int(getattr(b, "estimated_minutes", None) or 0)
            batch_out.append({
                "ragic_id": b.ragic_id, "ragic_url": ragic_record_url(key, b.ragic_id),
                "inspector": name, "start_time": b.start_time or "", "end_time": b.end_time or "",
                "start_hhmm": _hhmm(b.start_time or ""), "end_hhmm": _hhmm(b.end_time or ""),
                "work_hours": b.work_hours or "", "actual_minutes": mins,
                "estimated_minutes": getattr(b, "estimated_minutes", None),
            })
        src = live_source(key)
        floors.append({
            "key": key, "floor": EXCEL_FLOOR_LABEL[key], "title": TAB_LABELS[key],
            "sheet_url": sheet_url(src) if src else "",
            "has_record": len(bl) > 0, "inspectors": inspectors, "batches": batch_out,
            "actual_minutes": total_min, "estimated_minutes": est_min,
        })

    multi = {k: len(by_sheet[k]) > 1 for k in SHEET_ORDER}

    rows: list[dict[str, Any]] = []
    cnt = {"normal": 0, "abnormal": 0, "pending": 0, "unchecked": 0, "reading": 0}
    for t in HOTEL_DAILY_INSPECTION_TEMPLATE:
        key, content = t["source_tab"], t["check_content"]
        sp   = _spec(key, content)
        kind = sp["kind"]
        bl   = by_sheet.get(key, [])

        results: list[dict[str, Any]] = []
        for b in bl:
            v = values.get(b.ragic_id, {})
            label = _hhmm(b.start_time or "") if multi[key] else ""
            readings = [{"field": f, "label": lab, "value": v.get(norm_name(f), "")}
                        for f, lab in sp.get("readings", [])]
            if kind == "status":
                parts = [(lab, v.get(norm_name(f), "")) for f, lab in sp["fields"]]
                sts = [judge_status(raw) for _, raw in parts]
                st = next((p for p in ("abnormal", "pending", "unchecked", "normal") if p in sts), "unchecked")
                if len(parts) > 1:
                    text = "　".join(f"{lab}：{raw or '—'}" for lab, raw in parts)
                else:
                    text = parts[0][1]
                results.append({"batch_ragic_id": b.ragic_id, "time_label": label,
                                "status": st, "text": text, "readings": readings})
            else:  # reading
                readings = [{"field": f, "label": lab, "value": v.get(norm_name(f), "")}
                            for f, lab in sp["fields"]]
                filled = any(r["value"] for r in readings)
                results.append({"batch_ragic_id": b.ragic_id, "time_label": label,
                                "status": "reading" if filled else "unchecked",
                                "text": "", "readings": readings})

        if not results:
            merged = "no_record"
        else:
            sts = [r["status"] for r in results]
            merged = next((p for p in ("abnormal", "pending", "unchecked", "reading", "normal") if p in sts),
                          "unchecked")
            if merged in cnt:
                cnt[merged] += 1

        rows.append({
            "floor": t["floor"], "item": t["item"], "check_content": content,
            "result_options": t["result_options"], "minutes": t["minutes"], "source_tab": key,
            "item_first_row": t["item_first_row"], "floor_first_row": t["floor_first_row"],
            "floor_row_count": t["floor_row_count"], "item_row_count": t["item_row_count"],
            "kind": kind,
            "ragic_fields": [f for f, _ in sp["fields"]] + [f for f, _ in sp.get("readings", [])],
            "note_field": "", "results": results, "status": merged,
            "abnormal": merged in ("abnormal", "pending"), "abnormal_note": "",
            "remark": REMARK.get((key, content), ""),
        })

    # 版型外欄位（現行表）＋ 舊表場次：只在明確寫出異常字樣時列出
    extra_issues: list[dict[str, Any]] = []

    def _scan(b: Any, key: str, label: str, is_legacy: bool) -> None:
        refs = _REFERENCED.get(key, set())
        for it in items_by_batch.get(b.ragic_id, []):
            name = it.item_name or ""
            if getattr(it, "is_note", False) or _is_text_field(name):
                continue
            if not is_legacy and norm_name(name) in refs:
                continue
            raw = (it.result_raw or "").strip()
            if not raw or _NUMERIC_RE.match(raw) or not _EXPLICIT_ISSUE_RE.search(raw):
                continue
            st = judge_status(raw)
            if st in ("abnormal", "pending"):
                extra_issues.append({
                    "source_tab": key,
                    "floor": EXCEL_FLOOR_LABEL[key] + ("（舊表）" if is_legacy else ""),
                    "field": name, "status": st, "text": raw, "time_label": label,
                    "legacy": is_legacy,
                })

    for key in SHEET_ORDER:
        for b in by_sheet[key]:
            _scan(b, key, _hhmm(b.start_time or "") if multi[key] else "", False)
    for b in legacy:
        _scan(b, b.sheet_key, _hhmm(b.start_time or ""), True)

    std_total = sum(t["minutes"] for t in HOTEL_DAILY_INSPECTION_TEMPLATE)
    summary = {
        "floors_total": len(SHEET_ORDER),
        "floors_logged": sum(1 for f in floors if f["has_record"]),
        "normal": cnt["normal"], "abnormal": cnt["abnormal"], "pending": cnt["pending"],
        "unchecked": cnt["unchecked"], "reading": cnt["reading"],
        "std_minutes_routine": std_total, "std_minutes_total": std_total,
        "estimated_minutes": sum(f["estimated_minutes"] for f in floors),
        "actual_minutes": sum(f["actual_minutes"] for f in floors),
        "shift_times": SHIFT_TIMES,
        # 表尾時間列（Drawer 有 footer 就照用；飯店沒有早晚班列）
        "footer": [
            {"text": "標準巡檢時間（巡檢表「時間/分」合計）", "minutes": std_total, "note": "飯店定案版"},
            {"text": "Ragic 預估時間合計（當日已登錄場次）",
             "minutes": sum(f["estimated_minutes"] for f in floors), "note": "Ragic「預估時間」欄"},
        ],
        "extra_issues": len(extra_issues),
        "legacy_batches": len(legacy),
    }
    return {"floors": floors, "rows": rows, "summary": summary, "extra_issues": extra_issues}
