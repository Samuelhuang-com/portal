"""
商場工務每日巡檢表（Excel 版型）建表服務

來源版型：2.2商場-每日巡檢表.xlsx（#2.2商場-每日巡檢表，41 列）
用途：/mall-facility-inspection/dashboard 月曆格點擊「某樓層 × 某日」的下一層，
      以 Excel 原版型呈現該日 5 張 Ragic Sheet 的實際巡檢結果。

⚠️ 為什麼不沿用 mall_daily_inspection_builder.build_mall_daily_inspection_table
   （那支只給已隱藏的「每日巡檢表」TAB 用，刻意不動它）：
   1. 它用「檢查內容 == Ragic 欄位名」＋ contains 模糊比對。Excel 與 Ragic 欄名並非一一對應
      （4F「室內溫度與濕度」在 Ragic 是「室內溫度」「室內濕度」兩欄），模糊比對只會抓到
      其中一欄，濕度直接消失。
   2. 異常說明一律取「第一個」note 欄。4F／B1~B4 各有兩組設備、各自有「異常說明」
      「異常說明2」，第二組設備的異常說明會被第一組蓋掉。
   3. 溫度、濕度、抄表度數這類「填數字」的欄位，經 _normalize_result_status 會被判成
      abnormal（非正常字樣一律算異常）—— 每天都會出現假異常。
   因此這裡改用**明確對應表**（FIELD_MAP / NOTE_FIELD），對不上的列明白標示，不猜。

Ragic 實際欄位（2026-10-01 同步 log「偵測到 N 個巡檢點」）：
  4f      : 電器室門禁、室內溫度、室內濕度、配電盤、電氣設備是否有異常發熱、接地線是否牢固、
            各電表抄表、異常說明、風機系統檢查、空氣過濾系統、控制系統及感測、排水系統檢查、
            皮帶檢查、異常說明2                         （無「預冷盤管及水系統」）
  3f      : 電源與運轉狀態、異常警報燈、集塵箱 / 濾網狀態、排油管路、靜電模組、廠商年度保養、異常說明
  1f-3f   : 基本外觀檢查、濾網檢查、風機/馬達系統、冷/熱盤管、室內溫度、室內溫度2、控制系統、
            異常說明 ……（其後 22 欄為公共區域巡檢，不在 Excel 版型內）
            （無櫃位抄表 —— Excel 備註「25號抄錶 另作表單」）
  1f      : 電源狀態、控制面板、水源管路與接頭、機體外觀、排水功能、傳動皮帶 / 軸承、
            機體震動與噪音、異常說明                   （無「洗劑加注器」）
  b1f-b4f : 風機本體、風管系統檢查、濾網與過濾系統、控制系統檢查、安全與警報系統、現場環境、
            異常說明、外觀檢查、設備外殼、線纜接頭、電源檢查、電源指示燈、UPS供電狀態、
            網路狀態、網路連線狀況、設備運作、溫度狀況、防塵清潔、異常說明2
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from app.services.mall_daily_inspection_template import MALL_DAILY_INSPECTION_TEMPLATE

RAGIC_BASE = "https://ap12.ragic.com/soutlet001"

# ── Sheet（source_tab）→ Ragic 路徑 ／ Excel 樓層文字 ─────────────────────────
SHEET_PATH: dict[str, str] = {
    "4f":      "mall-facility-inspection/2",
    "3f":      "mall-facility-inspection/3",
    "1f-3f":   "mall-facility-inspection/4",
    "1f":      "mall-facility-inspection/5",
    "b1f-b4f": "mall-facility-inspection/7",
}

# Excel A 欄原文（模板裡是「1F ~ 3F」「B1 ~ B4」，畫面照 Excel 寫法）
EXCEL_FLOOR_LABEL: dict[str, str] = {
    "4f": "4F", "3f": "3F", "1f-3f": "1F~3F", "1f": "1F", "b1f-b4f": "B1~B4",
}

SHEET_ORDER = ["4f", "3f", "1f-3f", "1f", "b1f-b4f"]

# ── 檢查內容 → Ragic 欄位（明確對應；未列者預設「同名欄位」）────────────────────
#   kind = status   ：單一選項欄（正常／異常…）
#   kind = reading  ：填數字欄（溫度、濕度、度數），不判正常異常
#   kind = separate ：Excel 註明另作表單，Ragic 本表無資料
#   kind = unmapped ：Ragic 表單沒有這個欄位
FIELD_MAP: dict[tuple[str, str], dict[str, Any]] = {
    ("4f", "室內溫度與濕度"): {
        "kind": "reading",
        "fields": [("室內溫度", "室內度數"), ("室內濕度", "濕度")],
    },
    ("4f", "各電表抄表"): {
        "kind": "reading",
        "fields": [("各電表抄表", "度數")],
    },
    ("4f", "預冷盤管及水系統"): {"kind": "unmapped", "fields": []},
    ("1f-3f", "各櫃位抄水電瓦斯表(25)"): {"kind": "separate", "fields": []},
    # Ragic 欄名為「室內溫度」「室內溫度2」；Excel 選項為「室內度數」「濕度」，依序對應
    ("1f-3f", "溫度與濕度控制"): {
        "kind": "reading",
        "fields": [("室內溫度", "室內度數"), ("室內溫度2", "濕度")],
    },
    ("1f", "洗劑加注器"): {"kind": "unmapped", "fields": []},
}

# ── 設備（項目）→ 該組的異常說明欄 ───────────────────────────────────────────
NOTE_FIELD: dict[tuple[str, str], str] = {
    ("4f", "配電室"):           "異常說明",
    ("4f", "預冷空調箱"):       "異常說明2",
    ("3f", "靜電機"):           "異常說明",
    ("1f-3f", "空調箱"):        "異常說明",
    ("1f", "水洗機"):           "異常說明",
    ("b1f-b4f", "抽排風設備"):  "異常說明",
    ("b1f-b4f", "電信設備"):    "異常說明2",
}

# Excel H／I 欄備註
REMARK: dict[tuple[str, str], str] = {
    ("1f-3f", "各櫃位抄水電瓦斯表(25)"): "25號抄錶　另作表單",
}

# Excel 第 43、46 列
SHIFT_TIMES = [
    {"label": "早班巡檢時間", "range": "08:30~10:00"},
    {"label": "晚班巡檢時間", "range": "18:30~20:00"},
]

NORMAL_WORDS  = {"正常", "乾淨", "OK", "ok", "O", "V", "v", "✓", "良好"}
PENDING_WORDS = {"待處理", "待修", "待修繕"}

_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")
_DATE_RE = re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})")


# ── 輔助 ──────────────────────────────────────────────────────────────────────

def normalize_date(raw: str) -> str:
    """'2026-09-15' / '2026/9/15' → '2026/09/15'；解析不出來回空字串。"""
    m = _DATE_RE.search(raw or "")
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"{y}/{int(mo):02d}/{int(d):02d}"


def _hhmm(raw: str) -> str:
    """取字串中最後一個 HH:MM（'2026/9/1 09:26' → '09:26'）。"""
    found = _TIME_RE.findall(raw or "")
    if not found:
        return ""
    h, m = found[-1]
    return f"{int(h):02d}:{m}"


def _minutes_between(start: str, end: str) -> int:
    s, e = _hhmm(start), _hhmm(end)
    if not s or not e:
        return 0
    sm = int(s[:2]) * 60 + int(s[3:])
    em = int(e[:2]) * 60 + int(e[3:])
    diff = em - sm
    return diff + 24 * 60 if diff < 0 else diff


def judge_status(raw: str) -> str:
    """單一選項欄 → normal / abnormal / pending / unchecked。"""
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
    """batch_ragic_id = '{sheet_key}_{ragic_row_id}' → Ragic 單筆紀錄網址。"""
    path = SHEET_PATH.get(sheet_key, "")
    row_id = batch_ragic_id.rsplit("_", 1)[-1] if batch_ragic_id else ""
    if not path or not row_id:
        return ""
    return f"{RAGIC_BASE}/{path}/{row_id}"


# ── 版型外欄位（2026-10-05）─────────────────────────────────────────────────
# Ragic 表單有些欄位不在 Excel 2.2 版型內（例：1F~3F 後段 22 欄公共區域巡檢）。
# 這些欄位若填了「異常／待處理」，Excel 表上看不到，但月曆格與 Drawer 仍必須提示，
# 不能因為版型沒有就把真的異常藏起來。
# 這些欄位的選項沒有逐一對照過，為避免再出現假異常，只在值**明確寫出**異常字樣時才算
# （異常／待處理／待修／故障／損壞／不良／X）；數字、「已清潔」之類的文字不算。
_NUMERIC_RE = re.compile(r"^[-+]?\d+(?:\.\d+)?\s*(?:°C|℃|°|%|度|kwh|kWh|KWH)?$")
_EXPLICIT_ISSUE_RE = re.compile(r"異常|待處理|待修|故障|損壞|不良|^[Xx]$")


def _referenced_fields() -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {k: set() for k in SHEET_ORDER}
    for t in MALL_DAILY_INSPECTION_TEMPLATE:
        key, content = t["source_tab"], t["check_content"]
        spec = FIELD_MAP.get((key, content), {"kind": "status", "fields": [(content, "")]})
        refs.setdefault(key, set()).update(f for f, _ in spec["fields"])
    for (key, _item), f in NOTE_FIELD.items():
        refs.setdefault(key, set()).add(f)
    return refs


_REFERENCED = _referenced_fields()


def _is_text_field(name: str) -> bool:
    return any(w in name for w in ("說明", "備註", "照片", "拍照"))


def day_issues(sheet: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """
    build_daily_sheet 的結果 → {sheet_key: [異常／待處理項目]}。
    月曆格 ⚠ 與 Drawer 用同一份判定（2026-10-05：月曆格原本用同步時的 result_status，
    溫度、度數這類數字欄位會被算成異常，造成假 ⚠）。
    """
    out: dict[str, list[dict[str, Any]]] = {k: [] for k in SHEET_ORDER}
    for r in sheet["rows"]:
        if r["abnormal"]:
            out.setdefault(r["source_tab"], []).append({
                "source_tab":    r["source_tab"],
                "floor":         r["floor"],
                "item":          r["item"],
                "check_content": r["check_content"],
                "status":        r["status"],
                "note":          r["abnormal_note"],
                "in_template":   True,
            })
    for x in sheet.get("extra_issues", []):
        out.setdefault(x["source_tab"], []).append({
            "source_tab":    x["source_tab"],
            "floor":         x["floor"],
            "item":          "版型外欄位",
            "check_content": x["field"],
            "status":        x["status"],
            "note":          (f"[{x['time_label']}] " if x["time_label"] else "") + x["text"],
            "in_template":   False,
        })
    return out


# ── 單一欄位狀態（樓層 TAB 場次清單／明細 Drawer 用，2026-10-05）──────────────
# 與每日巡檢表、月曆格同一套判定，三個畫面的異常數才會一致：
#   版型內選項欄 → judge_status；溫度／濕度／度數等填數字欄 → measure（記錄值）；
#   版型外欄位   → 正常字樣算 normal、明確異常字樣算 abnormal/pending，其餘算 measure；
#   異常說明、建立日期這類附註欄 → note（不算巡檢項目）。
_READING_FIELDS: dict[str, set[str]] = {}
for (_k, _c), _spec in FIELD_MAP.items():
    if _spec["kind"] == "reading":
        _READING_FIELDS.setdefault(_k, set()).update(f for f, _ in _spec["fields"])


def item_status(sheet_key: str, item_name: str, raw: str, is_note: bool = False) -> str:
    from app.services.inspection_field_rules import is_meta_field

    name = (item_name or "").strip()
    raw  = (raw or "").strip()
    if is_note or is_meta_field(name) or _is_text_field(name):
        return "note"
    if not raw:
        return "unchecked"
    if name in _READING_FIELDS.get(sheet_key, set()) or _NUMERIC_RE.match(raw):
        return "measure"
    st = judge_status(raw)
    if name in _REFERENCED.get(sheet_key, set()) or st == "normal":
        return st
    return st if _EXPLICIT_ISSUE_RE.search(raw) else "measure"


def item_kpi(sheet_key: str, items: Iterable[Any]) -> dict[str, Any]:
    """場次 KPI（排除附註欄）：total／checked／normal／abnormal／pending／unchecked／measure／completion_rate。"""
    sts = [item_status(sheet_key, it.item_name, it.result_raw, bool(getattr(it, "is_note", False))) for it in items]
    sts = [x for x in sts if x != "note"]
    c = {k: sum(1 for x in sts if x == k) for k in ("normal", "abnormal", "pending", "unchecked", "measure")}
    total = len(sts)
    checked = total - c["unchecked"]
    return {
        "total":           total,
        "checked":         checked,
        **c,
        "completion_rate": round(checked / total * 100, 1) if total else 0.0,
    }


# ── 主函式（純資料，不碰 DB，方便測試）────────────────────────────────────────

def build_daily_sheet(
    batches: Iterable[Any],
    items_by_batch: dict[str, list[Any]],
) -> dict[str, Any]:
    """
    batches        ：當日 MallFIBatch（任意 sheet、可多筆 —— 早班／晚班）
    items_by_batch ：{batch_ragic_id: [MallFIItem, ...]}

    回傳 {floors: [...], rows: [...], summary: {...}, extra_issues: [...]}
    """
    # 依 sheet 分組，組內依開始時間排序
    by_sheet: dict[str, list[Any]] = {k: [] for k in SHEET_ORDER}
    for b in batches:
        if b.sheet_key in by_sheet:
            by_sheet[b.sheet_key].append(b)
    for k in by_sheet:
        by_sheet[k].sort(key=lambda b: (_hhmm(b.start_time or "") or "99:99", b.ragic_id))

    # 每個 batch 的 {欄位名: 原始值}
    values: dict[str, dict[str, str]] = {
        bid: {it.item_name: (it.result_raw or "").strip() for it in its}
        for bid, its in items_by_batch.items()
    }

    # ── 樓層（Sheet）層級資訊 ────────────────────────────────────────────────
    floors: list[dict[str, Any]] = []
    floor_info: dict[str, dict[str, Any]] = {}
    for key in SHEET_ORDER:
        bl = by_sheet[key]
        inspectors: list[str] = []
        batch_out = []
        total_min = 0
        for b in bl:
            name = (b.inspector_name or "").strip()
            if name and name not in inspectors:
                inspectors.append(name)
            mins = _minutes_between(b.start_time or "", b.end_time or "")
            total_min += mins
            batch_out.append({
                "ragic_id":       b.ragic_id,
                "ragic_url":      ragic_record_url(key, b.ragic_id),
                "inspector":      name,
                "start_time":     b.start_time or "",
                "end_time":       b.end_time or "",
                "start_hhmm":     _hhmm(b.start_time or ""),
                "end_hhmm":       _hhmm(b.end_time or ""),
                "work_hours":     b.work_hours or "",
                "actual_minutes": mins,
            })
        info = {
            "key":            key,
            "floor":          EXCEL_FLOOR_LABEL[key],
            "sheet_url":      f"{RAGIC_BASE}/{SHEET_PATH[key]}",
            "has_record":     len(bl) > 0,
            "inspectors":     inspectors,
            "batches":        batch_out,
            "actual_minutes": total_min,
        }
        floor_info[key] = info
        floors.append(info)

    multi = {k: len(by_sheet[k]) > 1 for k in SHEET_ORDER}

    # ── 41 列 ────────────────────────────────────────────────────────────────
    rows: list[dict[str, Any]] = []
    cnt = {"normal": 0, "abnormal": 0, "pending": 0, "unchecked": 0, "reading": 0}

    for t in MALL_DAILY_INSPECTION_TEMPLATE:
        key     = t["source_tab"]
        content = t["check_content"]
        spec    = FIELD_MAP.get((key, content), {"kind": "status", "fields": [(content, "")]})
        kind    = spec["kind"]
        bl      = by_sheet.get(key, [])

        results: list[dict[str, Any]] = []
        for b in bl:
            v = values.get(b.ragic_id, {})
            label = _hhmm(b.start_time or "") if multi[key] else ""
            if kind == "status":
                raw = v.get(spec["fields"][0][0], "")
                results.append({
                    "batch_ragic_id": b.ragic_id,
                    "time_label":     label,
                    "status":         judge_status(raw),
                    "text":           raw,
                    "readings":       [],
                })
            elif kind == "reading":
                readings = [
                    {"field": f, "label": lab, "value": v.get(f, "")}
                    for f, lab in spec["fields"]
                ]
                filled = any(r["value"] for r in readings)
                results.append({
                    "batch_ragic_id": b.ragic_id,
                    "time_label":     label,
                    "status":         "reading" if filled else "unchecked",
                    "text":           "",
                    "readings":       readings,
                })

        # 合併狀態（多場次取最嚴重）
        if kind in ("separate", "unmapped"):
            merged = kind
        elif not results:
            merged = "no_record"
        else:
            sts = [r["status"] for r in results]
            merged = next(
                (p for p in ("abnormal", "pending", "unchecked", "reading", "normal") if p in sts),
                "unchecked",
            )
            if merged in cnt:
                cnt[merged] += 1

        # 異常說明（同一設備組共用一欄；多場次加時間前綴）
        note_field = NOTE_FIELD.get((key, t["item"]), "")
        notes: list[str] = []
        if note_field:
            for b in bl:
                txt = values.get(b.ragic_id, {}).get(note_field, "")
                if txt:
                    pre = f"[{_hhmm(b.start_time or '')}] " if multi[key] else ""
                    notes.append(pre + txt)

        rows.append({
            "floor":           EXCEL_FLOOR_LABEL[key],
            "item":            t["item"],
            "check_content":   content,
            "result_options":  t["result_options"],
            "minutes":         t["minutes"],
            "source_tab":      key,
            "item_first_row":  t["item_first_row"],
            "floor_first_row": t["floor_first_row"],
            "floor_row_count": t["floor_row_count"],
            "item_row_count":  t["item_row_count"],
            "kind":            kind,
            "ragic_fields":    [f for f, _ in spec["fields"]],
            "note_field":      note_field,
            "results":         results,
            "status":          merged,
            "abnormal":        merged in ("abnormal", "pending"),
            "abnormal_note":   "\n".join(notes),
            "remark":          REMARK.get((key, content), ""),
        })

    # 版型外欄位的異常／待處理（Excel 表上沒有這些欄位，另外列出）
    extra_issues: list[dict[str, Any]] = []
    for key in SHEET_ORDER:
        refs = _REFERENCED.get(key, set())
        for b in by_sheet[key]:
            label = _hhmm(b.start_time or "") if multi[key] else ""
            for it in items_by_batch.get(b.ragic_id, []):
                name = it.item_name or ""
                if getattr(it, "is_note", False) or name in refs or _is_text_field(name):
                    continue
                raw = (it.result_raw or "").strip()
                if not raw or _NUMERIC_RE.match(raw) or not _EXPLICIT_ISSUE_RE.search(raw):
                    continue
                st = judge_status(raw)
                if st in ("abnormal", "pending"):
                    extra_issues.append({
                        "source_tab": key,
                        "floor":      EXCEL_FLOOR_LABEL[key],
                        "field":      name,
                        "status":     st,
                        "text":       raw,
                        "time_label": label,
                    })

    # Excel G43／G44：一般巡檢合計、含櫃位抄表合計（由模板分鐘數加總，不寫死）
    std_total    = sum(t["minutes"] for t in MALL_DAILY_INSPECTION_TEMPLATE)
    std_separate = sum(
        t["minutes"] for t in MALL_DAILY_INSPECTION_TEMPLATE
        if FIELD_MAP.get((t["source_tab"], t["check_content"]), {}).get("kind") == "separate"
    )

    summary = {
        "floors_total":        len(SHEET_ORDER),
        "floors_logged":       sum(1 for f in floors if f["has_record"]),
        "normal":              cnt["normal"],
        "abnormal":            cnt["abnormal"],
        "pending":             cnt["pending"],
        "unchecked":           cnt["unchecked"],
        "reading":             cnt["reading"],
        "std_minutes_routine": std_total - std_separate,
        "std_minutes_total":   std_total,
        "actual_minutes":      sum(f["actual_minutes"] for f in floors),
        "shift_times":         SHIFT_TIMES,
        "extra_issues":        len(extra_issues),
    }
    return {"floors": floors, "rows": rows, "summary": summary, "extra_issues": extra_issues}
